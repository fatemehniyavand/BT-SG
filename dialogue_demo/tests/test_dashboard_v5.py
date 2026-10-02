from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from engine import Runner,load_tree,to_dot

TREE=load_tree(Path(__file__).parents[1]/'BehaviorTree.json')
def test_loop_back_on_full_original_tree_and_snapshot():
    r=Runner(TREE,'When was Thriller released?');r.run_all()
    assert r.runtime['missing_slots']==['work_type','release_edition']
    assert r.runtime['slot_iteration']==1
    dot=to_dot(TREE,r.steps,None,r.runtime['slot_state'],r.runtime['slot_iteration'])
    assert 'LOOP BACK' in dot and 'Repeat Until Failure' in dot and 'Select Database' in dot
    old=len(r.steps);r.answer_slot('song')
    assert len(r.steps)>old and r.runtime['slot_iteration']==2
    assert r.runtime['slot_state']=='WAITING_USER'
    r.answer_slot('first release')
    assert r.runtime['slot_state']=='COMPLETE'
    assert any('LOOP BACK' in s['event']['detail'] for s in r.steps[old:])
    dot=to_dot(TREE,r.steps,None,'COMPLETE',3)
    assert 'EXIT' in dot and 'LOOP BACK' not in dot
    assert r.steps[-1]['blackboard']['slots']['work_type']=='song'

def test_invalid_reply_does_not_advance_loop():
    r=Runner(TREE,'When was Thriller released?');r.run_all();prev=len(r.steps)
    try:r.answer_slot('possibly')
    except ValueError:pass
    assert len(r.steps)==prev+1  # rejected reply is now an auditable event
    assert r.runtime['slot_iteration']==1
