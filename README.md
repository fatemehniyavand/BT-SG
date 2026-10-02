# BT-SG Orchestration — V10 (Alphanumeric visual normalization)

Based on V9. Original `src/` preserved. The dashboard displays every normalization transformation as a card with arrows, numbered tokens, and a compact operational Blackboard.

Normalization: preserve all Unicode letters and digits, replace every other character (including punctuation and extra question marks) with a separator, collapse spaces, add exactly one final `?` if nonempty, casefold **only** the classifier view. Numbers in titles are retained. No spelling/grammar models or Java.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r dialogue_demo/requirements.txt
python -m streamlit run dialogue_demo/app.py
```

The original-tree visualization, topic/intent detection, slot filling, loop trace and four-field Blackboard are unchanged. Neo4j integration remains a future phase.

## NEW: Prolog and Neo4j
See [sg_pipeline/README.md](sg_pipeline/README.md) for formal semantics, macOS setup, runnable commands, graph query, and known limitations. Existing src/ remains unchanged.
