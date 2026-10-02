from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from engine import Runner, load_tree, normalization_pipeline, to_dot
from slots import SLOT_SPECS,CHOICES

TREE=load_tree(Path(__file__).parents[1]/'BehaviorTree.json')

def test_every_intent_has_three_slots_and_every_choice_has_valid_values():
 assert sum(len(x) for x in SLOT_SPECS.values())==8
 for topic,intents in SLOT_SPECS.items():
  for intent,slots in intents.items():
   assert len(slots)>=3,(topic,intent)
   for key,q in slots.items():
    assert q.endswith('?')
    assert key in CHOICES or key.endswith('_title') or key=='performer_name'


def test_loop_three_slots_complete_and_history_immutable():
 r=Runner(TREE,'When was Thriller released?');r.run_all()
 assert list(r.runtime['required_slots'])==['work_title','work_type','release_edition']
 first=r.steps[-1]['blackboard']
 assert first['required_slots']['work_title']['status']=='FILLED'
 assert first['required_slots']['release_edition']['status']=='MISSING'
 r.answer_slot('song')
 assert r.runtime['slot_state']=='WAITING_USER'
 assert first['required_slots']['work_type']['status']=='MISSING'
 r.answer_slot('first release')
 assert r.runtime['slot_state']=='COMPLETE'
 assert r.runtime['slot_iteration']==3
 assert len([x for x in r.steps if 'LOOP BACK' in x['event']['detail']])==2
 assert 'EXIT' in to_dot(TREE,r.steps,None,'COMPLETE',3)

def test_all_intent_slot_flows():
 inputs={
  ('music','artist'):'Who sings Bohemian Rhapsody?',
  ('music','release_year'):'When was Thriller released?',
  ('music','album'):'Which album contains Billie Jean?',
  ('music','genre'):'What genre is Thriller?',
  ('art','creator'):'Who painted The Starry Night?',
  ('art','creation_year'):'When was Mona Lisa painted?',
  ('art','movement'):'What art movement is Guernica?',
  ('art','location'):'Which museum houses Mona Lisa?',
 }
 replies={'song_title':'Billie Jean','work_title':'Thriller','work_type':'song',
  'performer_role':'lead singer','recording_version':'original','release_edition':'first release',
  'performer_name':'Michael Jackson','genre_scope':'main genre','artwork_title':'Mona Lisa',
  'medium':'painting','creator_role':'artist','date_type':'finished',
  'genre_scope':'main genre','location_type':'current'}
 for (topic,intent),q in inputs.items():
  r=Runner(TREE,q);r.run_all()
  assert (r.runtime['topic'],r.runtime['intent'])==(topic,intent),(q,r.runtime['topic'],r.runtime['intent'])
  count=0
  while r.runtime['slot_state']=='WAITING_USER':
   name=r.runtime['missing_slots'][0];r.answer_slot(replies[name]);count+=1
   assert count<=3
  assert r.runtime['slot_state']=='COMPLETE'
  assert len(r.runtime['slots'])==3
