from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from engine import Runner,load_tree,normalization_pipeline,tokenize
from slots import SLOT_SPECS,missing_slots,extract_slots,validate_slot
T=load_tree(Path(__file__).parents[1]/'BehaviorTree.json')

def test_non_destructive_normalization_and_tokens():
    steps=normalization_pipeline('  WHO  sings  The  Artist’s   Song,,  ')
    assert steps[-2]['after']=='WHO sings The Artist s Song?'
    assert steps[-1]['after']=='who sings the artist s song?'
    assert 'artist' in [t.casefold() for t in tokenize(steps[-2]['after'])]
    assert 'not' in tokenize('do not change this')
    assert normalize2('C++ is a language...')=='c is a language?'

def normalize2(t):return normalization_pipeline(t)[-1]['after']

def test_missing_title_exits_after_answer():
    r=Runner(T,'Who sings?');r.run_all()
    assert r.runtime['topic']=='music'
    assert r.runtime['intent']=='artist'
    assert r.runtime['slot_state']=='WAITING_USER'
    assert r.runtime['missing_slots']==['song_title','recording_version']
    r.answer_slot('Bohemian Rhapsody')
    assert r.runtime['slot_state']=='WAITING_USER'
    r.answer_slot('original')
    assert r.runtime['slot_state']=='COMPLETE'
    assert r.steps[-1]['event']['node']=='Repeat Until Failure'
    assert r.runtime['slots']['song_title']=='Bohemian Rhapsody'

def test_multi_slot_loop_year():
    r=Runner(T,'When was Thriller released?');r.run_all()
    assert r.runtime['slots']['work_title'].lower()=='thriller'
    assert r.runtime['missing_slots']==['work_type','release_edition']
    try:r.answer_slot('perhaps');assert False
    except ValueError: pass
    assert r.runtime['slot_state']=='WAITING_USER'
    r.answer_slot('song');assert r.runtime['slot_state']=='WAITING_USER'
    r.answer_slot('first release');assert r.runtime['slot_state']=='COMPLETE'
    assert r.runtime['slots']['work_type']=='song'

def test_catalogue_and_art_extraction():
    assert len(SLOT_SPECS['music'])==4 and len(SLOT_SPECS['art'])==4
    assert extract_slots('art','creator','Who painted The Starry Night?')=={'artwork_title':'The Starry Night','medium':'painting'}
    assert validate_slot('work_type','random') is None
