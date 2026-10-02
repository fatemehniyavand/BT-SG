import re
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any
import py_trees
from py_trees.behaviours import CheckBlackboardVariableValue
import json
import requests

EXECUTOR = ThreadPoolExecutor(max_workers=5)


def camel_to_snake(text: str) -> str:
    # Insert an underscore before any capital letter preceded by a lowercase letter/digit
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    # Insert an underscore between consecutive capital letters followed by a lowercase letter
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    return text.lower()


# Example task handler
def fetch_user_data(node):
    # Simulates network request delay
    response = requests.get(
        f"https://jsonplaceholder.typicode.com/users/{1}", timeout=5
    )
    response.raise_for_status()
    return response.json()


TASK_HANDLERS = {
    "ActionExtractConstraints": fetch_user_data,
    "ActionUpdateCurrentState": fetch_user_data,
}


class GenericAPINode(py_trees.behaviour.Behaviour):
    def __init__(
        self,
        name: str,
        api_func: Callable[..., Any],
        bb_read=None,
        bb_write=None,
        *args,
        **kwargs,
    ):
        """
        :param name: Behavior name
        :param api_func: Function/method that performs the blocking API request
        :param args, kwargs: Arguments passed to api_func
        """
        super().__init__(name)
        self.name = name
        self.api_func = api_func
        self.args = args
        self.kwargs = kwargs

        self.future: Future | None = None

        self.blackboard = self.attach_blackboard_client(name=self.name)

        self.bb_read = bb_read or []
        self.bb_write = bb_write or []

        for key in self.bb_read:
            self.blackboard.register_key(key=key, access=py_trees.common.Access.READ)
        for key in self.bb_write:
            self.blackboard.register_key(key=key, access=py_trees.common.Access.WRITE)
        self.blackboard.register_key(
            key=f"{camel_to_snake(name)}_api_response",
            access=py_trees.common.Access.WRITE,
        )

    def initialise(self):
        """Dispatched when node state transitions from INVALID/FAILURE/SUCCESS to RUNNING."""
        self.logger.debug(f"[{self.name}] Dispatching API request...")
        # Dispatch blocking API function to thread pool
        self.future = EXECUTOR.submit(self.api_func, self, *self.args, **self.kwargs)

    def update(self) -> py_trees.common.Status:
        """Evaluated on every tree tick."""
        if self.future is None:
            return py_trees.common.Status.FAILURE

        # Check if background thread finished without blocking main tick loop
        if not self.future.done():
            return py_trees.common.Status.RUNNING

        try:
            # Retrieve result (raises exception if api_func failed)
            result = self.future.result()
            self.logger.debug(f"[{self.name}] API Call Succeeded: {result}")

            # Optionally store response on blackboard
            self.blackboard.set(f"{camel_to_snake(self.name)}_api_response", result)
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            self.logger.error(f"[{self.name}] API Call Failed: {e}")
            return py_trees.common.Status.FAILURE

    def terminate(self, new_status: py_trees.common.Status):
        """Cleanup when node completes or gets preempted by a Selector/Decorator."""
        if self.future and not self.future.done():
            # Note: Running requests cannot be forcibly stopped in standard Threads,
            # but we discard reference to prevent race conditions.
            self.future.cancel()
        self.future = None


class GenericTask(py_trees.behaviour.Behaviour):
    """A generic py_trees Behaviour that handles blackboard key access."""

    def __init__(self, name, bb_read=None, bb_write=None):
        super().__init__(name=name)
        # Register blackboard clients if keys are specified
        self.name = name
        self.blackboard = self.attach_blackboard_client(name=name)

        self.bb_read = bb_read or []
        self.bb_write = bb_write or []

        for key in self.bb_read:
            self.blackboard.register_key(key=key, access=py_trees.common.Access.READ)
        for key in self.bb_write:
            self.blackboard.register_key(key=key, access=py_trees.common.Access.WRITE)

    def update(self):
        # Default execution behavior
        return py_trees.common.Status.SUCCESS


def build_node(nodes_map, node_id):
    node = nodes_map[node_id]
    node_name = node["name"]
    properties = node.get("properties", {})

    # 1. Composite Nodes
    if node_name in ["Sequence", "ReactiveSequence", "Subtree"]:
        parent = py_trees.composites.Sequence(name="Sequence", memory=True)
    elif node_name in ["Selector", "Priority", "Fallback"]:
        parent = py_trees.composites.Selector(name=node_name, memory=True)
    elif node_name.lower().startswith("condition"):
        if "key" not in properties or "value" not in properties:
            raise Exception(f"Not fully specified condition: {node_name}")
        return CheckBlackboardVariableValue(
            name=node_name,
            check=py_trees.common.ComparisonExpression(
                variable=camel_to_snake(properties["key"]),
                value=properties["value"],
                operator=operator.eq,
            ),
        )
    # 2. Leaf / Action Nodes
    else:
        bb_read = (
            [k.strip() for k in properties["bbread"].split(",") if k.strip()]
            if "bbread" in properties
            else []
        )
        bb_write = (
            [k.strip() for k in properties["bbwrite"].split(",") if k.strip()]
            if "bbwrite" in properties
            else []
        )

        if node_name in TASK_HANDLERS:
            return GenericAPINode(
                name=node_name,
                bb_read=bb_read,
                bb_write=bb_write,
                api_func=TASK_HANDLERS[node_name],
            )
        return GenericTask(
            name=node_name,
            bb_read=bb_read,
            bb_write=bb_write,
        )

    # 3. Recursively attach children to composites
    for child_id in node.get("children", []):
        child_node = build_node(nodes_map, child_id)
        parent.add_child(child_node)

    return parent


def parse_json_tree(data):
    """Parses JSON data and returns an executable py_trees.trees.BehaviourTree object."""
    data = json.loads(data)
    tree_data = data["trees"][0]
    root_id = tree_data["root"]
    nodes_map = tree_data["nodes"]

    # Recursively build the tree hierarchy
    root_behaviour = build_node(nodes_map, root_id)

    # Wrap in a py_trees BehaviourTree container
    bt = py_trees.trees.BehaviourTree(root=root_behaviour)
    return bt
