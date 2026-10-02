# BT → Prolog → Service Graph → Neo4j

Two non-equivalent outputs: (1) Prolog-generated static **possible** control/data graph, (2) observed **partial demo** trace from Streamlit. No false guarantee that potential data edges execute, and no CPU/memory/Kafka/Solver implementation.

## Setup macOS
```bash
brew install swi-prolog
python3 -m venv .venv
source .venv/bin/activate
pip install -r dialogue_demo/requirements.txt -r sg_pipeline/requirements.txt
python -m sg_pipeline.convert
python -m streamlit run dialogue_demo/app.py
```

## Neo4j local
`docker compose up -d` (Docker Desktop must be installed). Set `NEO4J_PASSWORD` to match `docker-compose.yml`, using a secure local value. Alternatively use an existing Neo4j instance and set `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`.

```bash
python -m sg_pipeline.neo4j_store outputs/service_graph.json
```

Browser: http://localhost:7474 ; query:
```cypher
MATCH (a:BTNode {graph_id:'dialogue-tree-v1'})-[r]->(b:BTNode {graph_id:'dialogue-tree-v1'})
RETURN a,r,b LIMIT 250;
```

**Semantics:** `CONTROL_CHILD` is structural parent-child. `SIBLING_GATE` is next-sibling order with required prior success (Sequence) or failure (Fallback). Decorator `RepeatUntilFailure` is preserved structurally, not reduced to a cyclic resource dependency. `POTENTIAL_DATA` uses explicit *design assumptions* in `access_map.json`; potential edges across exclusive branches must be filtered with a runtime path before planning. The original JSON contains legacy names `ConditionTopicIsTelecom` and `ConditionTopicIsAI` despite Music/Art titles; these remain preserved by ID. Clarification order in this JSON is `Ask` then `Slots Not Filled`, which requires runtime correction in the dialogue demo, not silent change to source facts. This code produces a graph for visualization, not an edge/cloud placement-ready execution DAG.

Python writes full-fidelity Prolog facts (node IDs, children, index, decorator child, access map) and **SWI-Prolog produces the graph JSON**. No Python fallback is silently substituted for Prolog.

## Layers in the actual Prolog output
- `nodes`, `control_edges`: lossless BT skeleton, conditions and decorator included.
- `ordered_edges`: annotated sibling gates; these are control ordering constraints, not independent service-to-service data flows.
- `potential_data_edges`: all key-level producer-consumer pairs under explicit *design-assumed* `access_map.json`. No path feasibility analysis.
- `service_nodes`, `service_data_edges`: projection onto Action nodes to distinguish service tasks from control nodes. They remain possible rather than guaranteed dependencies.

The default Neo4j upload labels all nodes `BTNode` and Action nodes additionally `ServiceTask`. Avoid interpreting unobserved candidate edges as a realized service execution graph.

## IMPORTANT original vs dashboard JSON
`original_uploaded/BehaviorTree.json` is the user's **unchanged uploaded original**.
`dialogue_demo/BehaviorTree.json` is the V10 dashboard-corrected tree; it reorders `Slots Not Filled` before `Ask clarifying question` and adds explanation text to two nodes. Both trees contain 26 nodes / 25 parent-child edges. The CLI defaults to the corrected dashboard tree for consistency with V10; to convert the exact original instead:

```bash
python -m sg_pipeline.convert --tree original_uploaded/BehaviorTree.json --output outputs/original_service_graph.json
```

`access_map.json` is an **explicit proposed contract** for reads/writes rather than metadata in either provided JSON. Revise this map against actual node implementations before using candidate data dependencies for an infrastructure solver.

- `loop_edges`: explicit annotated back-edge child → repeat decorator when the child succeeds; the decorator exits on child failure. Neo4j relationship `LOOP_BACK` is NOT a cyclic deployment dependency.
- STT is transient text, not a producer of the four-key compact Blackboard `normalized_input`; access contract reflects that distinction.
