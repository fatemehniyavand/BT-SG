from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from engine import Runner, load_tree,normalization_pipeline,to_dot
from slots import SLOT_SPECS,parse_clarification
T=load_tree(Path(__file__).parents[1]/'BehaviorTree.json')

def test_three_concrete_slots_each():
 assert len(SLOT_SPECS['music'])==len(SLOT_SPECS['art'])==4
 assert all(len(slots)==3 for topic in SLOT_SPECS.values() for slots in topic.values())

def test_multi_answer_skips_extra_questions_and_exits():
 r=Runner(T,'When was Thriller released?');r.run_all()
 assert r.runtime['missing_slots']==['work_type','release_edition']
 old=r.steps[-1]['blackboard'];r.answer_slot('work_type=album; release_edition=first release')
 assert r.runtime['slot_state']=='COMPLETE'
 assert r.runtime['slot_iteration']==2
 assert old['slots'].get('work_type') is None
 assert len(r.runtime['clarification_replies'][-1]['accepted'])==2
 assert 'EXIT' in to_dot(T,r.steps,None,'COMPLETE',2)

def test_multi_answer_partial_validation():
 r=Runner(T,'When was Thriller released?');r.run_all()
 r.answer_slot('work_type=album; release_edition=unknown')
 assert r.runtime['slot_state']=='WAITING_USER'
 assert r.runtime['missing_slots']==['release_edition']
 assert r.runtime['clarification_replies'][-1]['rejected']
 r.answer_slot('first release')
 assert r.runtime['slot_state']=='COMPLETE'


def test_key_value_parser_prevents_wrong_slot_updates():
 accepted,rejected,mode=parse_clarification('music','artist','recording_version=live; artist_id=42',['recording_version'])
 assert accepted=={'recording_version':'live'} and len(rejected)==1 and mode=='labeled-multi'
