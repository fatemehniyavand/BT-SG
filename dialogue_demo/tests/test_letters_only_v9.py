from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from engine import normalize, normalization_pipeline, Runner, load_tree

def test_letters_only_and_single_question():
    assert normalize(' WHO!! \t sings  123 Bohemian---Rhapsody؟؟?? ') == 'who sings 123 bohemian rhapsody?'
    assert normalize('abc@@@def') == 'abc def?'
    assert normalize('¿Quién canta?') == 'quién canta?'
    assert normalize('123#?!') == '123?'
    assert normalize('Song 2 (Live)') == 'song 2 live?'

def test_tokens_and_compact_blackboard():
    stages=normalization_pipeline('  WHO  sings 99 Bohemian?! ')
    assert stages[-2]['tokens']==['WHO','sings','99','Bohemian']
    tree=load_tree(Path(__file__).parents[1]/'BehaviorTree.json')
    run=Runner(tree,'Who sings Bohemian Rhapsody?!')
    run.run_all()
    assert set(run.blackboard)=={'normalized_input','topic','intent','slots'}
    assert run.blackboard['normalized_input']=='who sings bohemian rhapsody?'
