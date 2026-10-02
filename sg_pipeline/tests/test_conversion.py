import json
from pathlib import Path
import pytest
from sg_pipeline.convert import load_tree,validate,facts,kind
from sg_pipeline.trace_graph import observed_trace
ROOT=Path(__file__).resolve().parents[2]
TREE=load_tree(ROOT/'dialogue_demo/BehaviorTree.json')
ACCESS=json.loads((ROOT/'sg_pipeline/access_map.json').read_text())

def test_full_tree_conservation():
    validate(TREE)
    fact_text=facts(TREE,ACCESS)
    assert fact_text.count('bt_node(')==len(TREE['nodes'])==26
    assert fact_text.count('bt_child(')==25
    assert 'repeat_until_failure' in fact_text

def test_voice_branch_not_dropped():
    result=facts(TREE, ACCESS)
    assert "bt_node('n4',condition,'Is Voice?')" in result and "bt_node('n7',condition,'Is Text?')" in result
    assert "bt_child('n2',0,'n3')" in result
    assert "bt_child('n2',1,'n6')" in result

def test_annotations_are_explicit_not_guessed():
    original=facts(TREE,{})
    assert 'access(' not in original
    annotated=facts(TREE,ACCESS)
    assert "access('n8',write,'normalized_input')" in annotated
    assert "access('n10',read,'normalized_input')" in annotated

def test_cycle_rejected():
    import copy
    bad=copy.deepcopy(TREE)
    bad['nodes']['n3']['children'].append('n0')
    with pytest.raises(ValueError):validate(bad)

def test_trace_disclaimer():
    assert observed_trace(None)['status']=='NO_EXECUTION'
    class Runner:
        steps=[{'event':{'node_id':'n8','status':'SUCCESS','detail':'normalized'},'working_blackboard':{'normalized_input':'test?'}}]
    assert observed_trace(Runner())['status']=='DEMO_TRACE_PARTIAL'
