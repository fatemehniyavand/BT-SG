from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from engine import intent_diagnostics, Runner, load_tree, normalize, INTENT_DESCRIPTIONS
TREE=load_tree(Path(__file__).parents[1]/'BehaviorTree.json')

def test_full_catalogue():
    assert set(INTENT_DESCRIPTIONS)=={'music','art'}
    assert all(len(items)==4 for items in INTENT_DESCRIPTIONS.values())

def test_diagnostic_ranking_and_logits():
    d=intent_diagnostics('music',normalize('Who sings Bohemian Rhapsody?'))
    assert d['chosen_intent']=='artist'
    assert len(d['ranking'])==4
    assert abs(sum(x['model_score'] for x in d['ranking'])-1)<1e-4
    for x in d['ranking']:
        parts=sum(f['contribution'] for f in x['positive_features']+x['negative_features'])
        assert abs(x['linear_logit']-x['intercept']-parts)<1e-4

def test_blackboard_contains_explanation_and_history():
    r=Runner(TREE,'Which museum houses Mona Lisa?')
    r.run_all()
    d=r.runtime['intent_explanation']
    assert r.runtime['topic']=='art'
    assert r.runtime['intent']=='location'
    assert d['topic_from_blackboard']=='art'
    assert d['chosen_intent']=='location'
    assert r.steps[-1]['blackboard']['intent_explanation']==d
    assert r.steps[9]['blackboard']['intent_explanation'] is None
