# Dialogue Behavior Tree — Dashboard V7

This folder is an isolated extension of the downloaded BT-SG-Orchestration archive. Original source under `src/` is unchanged. The executable text-input prefix reads `BehaviorTree.json` through Detect Intent; slot-loop events are traced over its existing node IDs, not executed by the original Prolog / `py_trees` runtime. Neo4j retrieval is not yet connected.

## Run on macOS

From the `BT-SG-Orchestration-v7` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r dialogue_demo/requirements.txt
streamlit run dialogue_demo/app.py
```

No Java, LanguageTool or grammar correction is required.

## Recommended slot dialogue policy

A user can reply naturally **one answer at a time**; after each answer, the loop rechecks remaining slots and asks only the next unanswered question. When the user already knows multiple answers, they can fill them in a **single reply** using explicit `key=value; key=value` formatting, shown dynamically directly below the main chat. Each field is validated independently. Invalid fields do not erase valid fields or advance a missing slot; invalid raw replies remain in the event log. See `slots.py` for human-readable labels, examples, validations and all 8 intents with exactly 3 required slots each.

Example: `When was Thriller released?` → initial `work_title=Thriller`, missing `work_type`, `release_edition`.

Reply `work_type=album; release_edition=first release`, and both slots are populated in one interaction. The full original tree diagram annotates each repeat/check/exit event, and the event replay shows the Blackboard snapshot for the selected historical step.

## Text preparation

- Keep the raw utterance unchanged in Blackboard.
- Apply Unicode NFC, consistent apostrophes and question marks, remove invisible control characters, collapse whitespace, limit duplicate stray punctuation and fix punctuation spacing.
- Add a trailing `?` to recognizable question forms without altering word choices.
- Expose numbered tokens and a separate casefolded ML view; preserve capitalization for entity extraction.
- No automatic spelling correction, grammatical rewriting or Java/LanguageTool integration.

## Tests

```bash
python -m pytest dialogue_demo/tests -q
```

## Scope

Current application: text only → normalization → topic Naive Bayes → intent-specific Logistic Regression → interactive 3-slot dialogue and visual loop trace. It is a project demonstrator with a small synthetic ML dataset, not a validated production classifier. Voice input, Neo4j queries and original Prolog pipeline are **not** yet implemented in this dashboard.

### Letters-only normalization (v9)

The user-requested mode retains **Unicode alphabetic characters only** inside the
question, replaces each number/punctuation/symbol with a word separator, collapses
spaces, then appends a **single `?`**. Tokens are displayed separately. No Java,
spelling correction or grammar model is used. Example: `  WHO, sings  99  HI?!`
becomes `who sings hi?` as classifier input. The title `Song 2` becomes `Song`,
so this deliberately lossy rule may affect named-entity extraction or identification.
All other dashboard and Blackboard behavior is unchanged.
