from pathlib import Path
from engine import normalize, tokenize, normalization_pipeline, Runner, load_tree

def test_letters_numbers_and_one_question():
    assert normalize('  WHAT?? is  Song 2 !!! ') == 'what is song 2?'
    assert normalize('  2001: A Space Odyssey؟؟ ') == '2001 a space odyssey?'
    assert normalize('  ¿Qué  año 2020??? ') == 'qué año 2020?'
    assert normalize('abc***123') == 'abc 123?'
    assert normalize('?!') == ''

def test_graphic_pipeline_and_blackboard():
    pipe=normalization_pipeline(' WHO!! sings Song 2 ?')
    assert pipe[-2]['tokens'] == ['WHO','sings','Song','2']
    assert [s['operation'] for s in pipe[:4]] == ['Unicode NFC','Remove extra symbols','Collapse whitespace','Exactly one question mark']
    r=Runner(load_tree(Path(__file__).parents[1]/'BehaviorTree.json'),'Who sings Bohemian Rhapsody?')
    r.run_all()
    assert set(r.blackboard) == {'normalized_input','topic','intent','slots'}
