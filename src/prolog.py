import re
import json
from pathlib import Path
from pyswip import Prolog

SCRIPT_DIR = Path(__file__).resolve().parent
prolog_file = SCRIPT_DIR / "btsg.pl"
relative_to_root = SCRIPT_DIR / ".." / "config.json"

COMPOSITE_NODES = [
    "Sequence",
    "ReactiveSequence",
    "Subtree",
    "Selector",
    "Priority",
    "Fallback",
]


def camel_to_snake(text: str) -> str:
    text = text.replace(" ", "")
    # Insert an underscore before any capital letter preceded by a lowercase letter/digit
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    # Insert an underscore between consecutive capital letters followed by a lowercase letter
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    return text.lower()


def is_node_skipped(node):
    name = node["name"].lower()
    return name.startswith("condition") or name.startswith("repeat")


def traverse_node(tree, node):
    res = ""
    bb_keys = set()

    if node["name"] in ["Sequence", "ReactiveSequence", "Subtree"]:
        res = "seq(["
    elif node["name"] in ["Selector", "Priority", "Fallback"]:
        res = "sel(["
    elif is_node_skipped(node):
        return res, bb_keys
    else:
        properties = node["properties"]
        params = []
        if "bbread" in properties:
            params.extend(
                [
                    f"param({key.strip()}, read({key.strip()}))"
                    for key in properties["bbread"].split(",")
                ]
            )
            for key in properties["bbread"].split(","):
                bb_keys.add(key.strip())
        if "bbwrite" in properties:
            params.extend(
                [
                    f"param({key.strip()}, write({key.strip()}))"
                    for key in properties["bbwrite"].split(",")
                ]
            )
            for key in properties["bbwrite"].split(","):
                bb_keys.add(key.strip())
        res = f"task({camel_to_snake(node['name'])}, [{str.join(',', params)}])"

    if "children" in node:
        for index, item in enumerate(node["children"]):
            definition, new_keys = traverse_node(tree, tree["nodes"][item])
            res += definition
            if index != len(node["children"]) - 1 and len(definition) > 0:
                res += ","
            bb_keys = bb_keys.union(new_keys)

    if node["name"] in COMPOSITE_NODES:
        res += "])"

    return res, bb_keys


def parse_json_tree(data):
    tree = data["trees"][0]
    root_node_name = tree["root"]
    root_node = tree["nodes"][root_node_name]

    tree_root, bb_keys = traverse_node(tree, root_node)

    bb_definition = f"newBlackboard([{str.join(',', [f'bbkey({key}, string)' for key in bb_keys])}])"
    tree_definition = f"newTree(bt(Root, BB)) :- newBlackboard(BB), Root = {tree_root}"
    return tree_definition, bb_definition


def get_prolog_result(json_tree: str):
    json_data = json.loads(json_tree)
    tree_definition, bb_definition = parse_json_tree(json_data)
    prolog = Prolog()

    prolog.consult(prolog_file)
    prolog.assertz(bb_definition)
    prolog.assertz(tree_definition)

    for result in prolog.query("demo(Deps)"):
        return result["Deps"]
