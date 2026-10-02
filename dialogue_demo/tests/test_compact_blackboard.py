from engine import Runner
from pathlib import Path
import json
TREE=json.loads((Path(__file__).resolve().parents[1]/'BehaviorTree.json').read_text())['trees'][0]

def test_compact_blackboard_and_snapshots():
    r=Runner(TREE,'When was Thriller released?');r.run_all()
    assert set(r.blackboard)=={'normalized_input','topic','intent','slots'}
    assert r.blackboard['topic']=='music'
    assert r.blackboard['intent']=='release_year'
    assert r.blackboard['slots']['work_title'].lower()=='thriller'
    assert 'normalization' not in r.blackboard and 'event_log' not in r.blackboard
    assert all(set(s['working_blackboard'])==set(r.blackboard) for s in r.steps)
    r.answer_slot('album')
    assert r.blackboard['slots']['work_type']=='album'
    assert 'slot_iteration' not in r.blackboard
