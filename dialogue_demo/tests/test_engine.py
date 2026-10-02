from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from engine import normalize, load_tree, prefix_path, Runner, to_dot, models
TREE=load_tree(Path(__file__).parents[1]/'BehaviorTree.json')
def test_tree_prefix():
    assert len(prefix_path(TREE))==11
    assert len(TREE['nodes'])==26

def test_normalization_keeps_punctuation_and_entities():
    assert normalize('  WHO   painted  Mona Lisa?!  ')=='who painted mona lisa?'

def test_music_and_art():
    for question,topic,intent in [('Who sings Bohemian Rhapsody?','music','artist'),('When was Thriller released?','music','release_year'),('Who painted The Starry Night?','art','creator'),('Which museum houses the Mona Lisa?','art','location')]:
        r=Runner(TREE,question);r.run_all()
        assert not r.error,(question,r.error)
        assert r.runtime['topic']==topic,(question,r.runtime)
        assert r.runtime['intent']==intent,(question,r.runtime)
        assert r.runtime['active_agent']==topic
        assert len(r.steps)>=14
        assert r.steps[7]['blackboard']['normalized_input']
        assert r.steps[9]['blackboard']['topic']==topic
        assert r.steps[10]['blackboard']['intent']==intent

def test_empty_fails():
    r=Runner(TREE,'  ');r.run_all();assert r.error and r.runtime['intent'] is None

def test_full_dot_includes_downstream():
    s=to_dot(TREE);assert 'ActionQueryArt' in s and 'Repeat Until Failure' in s

from engine import normalization_pipeline

def test_real_normalization_audit():
    raw='  WHO   sings   Bohemian Rhapsody  '
    pipeline=normalization_pipeline(raw)
    assert pipeline[-1]['after']=='who sings bohemian rhapsody?'
    assert len(pipeline)==6
    assert pipeline[2]['changed'] and pipeline[3]['changed'] and pipeline[-1]['changed']
    assert normalize('Who painted Mona Lisa.')=='who painted mona lisa?'
    assert normalize('Who painted Mona Lisa?!')=='who painted mona lisa?'
    assert normalize('Do not erase the album name')=='do not erase the album name?'
    assert normalize("Where's  Guernica?")=='where s guernica?'
    assert normalize('Do you know C++?')=='do you know c?'

def test_fallback_and_blackboard_history():
    r=Runner(TREE,'  WHO  sings  Bohemian Rhapsody ')
    for _ in range(5): assert r.next()
    assert r.steps[-1]['event']['status']=='FAILURE'
    assert r.steps[-1]['event']['effects'][0]['status']=='FAILURE'
    assert r.runtime['modality']['voice_result']=='FAILURE'
    assert r.runtime['normalized_input'] is None
    assert r.next() and r.next()
    assert r.steps[-1]['event']['status']=='SUCCESS'
    assert len(r.steps[-1]['event']['effects'])==2
    assert r.runtime['modality']['selected']=='text'
    assert r.next()
    assert r.runtime['normalized_input']=='who sings bohemian rhapsody?'
    assert r.steps[0]['blackboard']['normalized_input'] is None
    assert r.steps[-1]['blackboard']['normalization']['changed']
    assert 'normalization' in r.steps[-1]['event']['blackboard_delta']
    r.run_all()
    assert r.runtime['topic']=='music' and r.runtime['intent']=='artist'
    assert 'topic' in r.steps[9]['event']['blackboard_delta']
    assert 'intent' in r.steps[10]['event']['blackboard_delta']
    dot=to_dot(TREE,r.steps)
    assert '"n4"' in dot and '#FFD2D2' in dot
