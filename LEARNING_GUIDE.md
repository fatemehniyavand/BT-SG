# Learning Lab — Source-Grounded Guide (Simple English)

This add-on preserves the existing V10 dashboard, 26-node Music/Art Behavior Tree,
original upstream source (`src/`), SWI-Prolog rules, Neo4j upload tools, and working
4-key compact Blackboard. Nothing is automatically uploaded to a database.

## One command in VS Code (macOS)

Open this **extracted folder** in VS Code, then run:

```bash
bash run_learning_lab.sh
```

On your first use, it creates `.venv`, installs the required packages, executes
SWI-Prolog (if installed), prints a complete static-graph explanation in your
terminal, saves `outputs/learning_report.txt` and launches Streamlit. Install
SWI-Prolog if needed: `brew install swi-prolog`.

Alternatively, use these explicit commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r dialogue_demo/requirements.txt -r sg_pipeline/requirements.txt
python -m sg_pipeline.learning_report
python -m streamlit run dialogue_demo/app.py
```

## What appears in the new Learning Lab

**Learn the Behavior Tree:** Select one of five stages, each anchored to the
actual node names and available demo algorithms: input routing (Fallback),
normalization (NFC + filtering + whitespace + question mark + tokenization),
TF-IDF/Naive Bayes topic detection, topic-specific TF-IDF/Logistic Regression
intent detection, and rule-based slot filling with 3 project-defined required
slots per intent. Each page shows WHY, reads/writes, important limitations,
matched original node IDs, available execution events, and compact Blackboard.
The slot page has a loop diagram and exact question for every required slot.

**Learn Prolog conversion:** Step through the full static tree conversion:
JSON and validation → generated facts → actual SWI-Prolog call → structural
rules → possible producer/reader matches → graph JSON → Python architectural
projection. The source-code panels show exact rules from the currently packaged
`converter.pl`. All generated facts for the **selected tree** can be downloaded.
Click **Run full tree → SWI-Prolog → static SG** to see *real* conversion output
and inspect structural, ordered, potential-data and repeat layers separately.
The project does NOT pretend to run Prolog when it is unavailable.

**Two separate graph meanings:** Prolog infers static BT structure and possible
writer-reader pairs based on `sg_pipeline/access_map.json`. A second Python
function (`sg_pipeline/service_view.py`) adds a human-audited graphical
presentation containing gateways and `CONDITIONAL_FLOW`. This second view is
NOT a Prolog proof and does NOT describe a particular user question. Both
Music and Art are represented. Real runtime paths and placement requirements
must be validated separately.

## Blackboard and Neo4j

Runtime Blackboard keys remain ONLY: `normalized_input`, `topic`, `intent`,
`slots`. All history and model diagnostics remain separate in the dashboard.
The static `SGBlackboardKey` nodes in Neo4j are *schema keys*, not values from
any specific user conversation.

To regenerate the 26-node static Prolog graph and the readable second view
WITHOUT uploading:

```bash
python -m sg_pipeline.convert
python -m sg_pipeline.service_view
```

To upload the second view when your Neo4j Aura credentials are already set in
your own terminal (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`):

```bash
python -m sg_pipeline.service_view --upload
```

Neo4j Aura Query for readable control + read/write contracts:

```cypher
MATCH (a {graph_id:'dialogue-service-v1'})
      -[r:CONDITIONAL_FLOW|READS|WRITES]->
      (b {graph_id:'dialogue-service-v1'})
RETURN a,r,b;
```

**Limitations:** The demo implements only the text execution prefix through
Slot Filling, not real voice transcription, live knowledge graph querying,
LLM verbalization, complete py_trees execution, or CPU/RAM-aware edge-cloud
placement. Training templates are small and synthetic; scores are not measured
accuracy. The original uploaded JSON and corrected demo JSON are BOTH kept.
