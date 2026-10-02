from pathlib import Path
from sg_pipeline.convert import load_tree,validate
ROOT=Path(__file__).resolve().parents[2]
def test_original_and_runtime_variants():
    a=load_tree(ROOT/'original_uploaded/BehaviorTree.json')
    b=load_tree(ROOT/'dialogue_demo/BehaviorTree.json')
    validate(a);validate(b)
    assert set(a['nodes'])==set(b['nodes'])
    sid='0151c83d-eed2-4d4c-adf9-4921399fbe0c'
    assert a['nodes'][sid]['children']==list(reversed(b['nodes'][sid]['children']))
