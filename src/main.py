import os
from time import sleep
import argparse
import sys
import py_trees
import eventlet
import socketio
from prolog import get_prolog_result
from graphdb import upload_to_neo4j
from btree import parse_json_tree

sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)


@sio.event
def connect(sid, environ):
    print(f"[WebSocket] Client connected: {sid}")


@sio.event
def disconnect(sid):
    print(f"[WebSocket] Client disconnected: {sid}")


def serialize_tree(node):
    """Recursively extracts node topology and current runtime status."""
    return {
        "id": str(node.id),
        "name": node.name,
        "type": node.__class__.__name__,
        "status": str(
            node.status.value
        ),  # e.g., 'RUNNING', 'SUCCESS', 'FAILURE', 'INVALID'
        "children": [serialize_tree(child) for child in node.children],
    }


def render_live_tree(tree):
    # Clear terminal screen (cls for Windows, clear for Unix)
    os.system("cls" if os.name == "nt" else "clear")

    # Print highlighted active execution path
    print(
        py_trees.display.unicode_tree(
            root=tree.root,
            show_status=True,  # Shows SUCCESS, RUNNING, FAILURE badges
        )
    )


def main():
    parser = argparse.ArgumentParser(description="Read path to behavior tree JSON.")
    parser.add_argument("file_path", help="Path to the Behavior Tree JSON file")
    args = parser.parse_args()

    try:
        with open(args.file_path, "r", encoding="utf-8") as f:
            json_raw = f.read()

            bt = parse_json_tree(json_raw)
            bt.add_post_tick_handler(render_live_tree)
            bt.setup(timeout=15)

            def run_bt_loop():
                try:
                    while True:
                        bt.tick()
                        tree_data = serialize_tree(bt.root)
                        sio.emit("tree_update", tree_data)

                        # Check root status if you want to stop on SUCCESS or FAILURE
                        if bt.root.status != py_trees.common.Status.RUNNING:
                            print(f"Tree finished with status: {bt.root.status}")
                            break

                        eventlet.sleep(0.5)
                    eventlet.kill(eventlet.getcurrent(), SystemExit)
                except KeyboardInterrupt:
                    print("Execution interrupted.")

            eventlet.spawn(run_bt_loop)

            print("[Server] Starting WebSocket server on http://localhost:5500")
            eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5500)), app)

            # Render ASCII representation to terminal
            print(py_trees.display.ascii_tree(bt.root))
            print(py_trees.display.unicode_blackboard())

            print("Prolog conversion...")
            prolog_res = get_prolog_result(json_raw)
            print("Done.")

            print("Uploading to Neo4j...")
            upload_to_neo4j(
                prolog_res,
                os.getenv("NEO4J_URI"),
                (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
            )
            print("Done.")
    except FileNotFoundError:
        print(f"Error: File '{args.file_path}' not found.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
