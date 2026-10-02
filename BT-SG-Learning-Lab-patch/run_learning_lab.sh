#!/usr/bin/env bash
# Run from any location. No Neo4j password is saved or requested here.
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -r dialogue_demo/requirements.txt -r sg_pipeline/requirements.txt
if command -v swipl >/dev/null 2>&1; then
  python -m sg_pipeline.learning_report
else
  printf '\nSWI-Prolog is missing. On macOS: brew install swi-prolog\n'
  printf 'The Learning Lab can still show the exact generated facts and source lessons.\n'
fi
python -m streamlit run dialogue_demo/app.py
