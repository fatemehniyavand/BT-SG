"""Ensure interactive code explanations stay in sync with REAL converter.pl."""
import json
import subprocess
from pathlib import Path

from prolog_code_guide import RULES, exact_source, rule_dot
from sg_pipeline.convert import load_tree,facts

ROOT=Path(__file__).resolve().parents[2]
PL=(ROOT/'sg_pipeline/converter.pl').read_text(encoding='utf8')


def test_explainer_uses_all_actual_source_rules():
    assert len(RULES)==14
    for rule in RULES:
        source=exact_source(PL,rule['prefix'])
        assert not source.startswith('Rule '), rule['title']
        assert source.splitlines()[0].startswith(rule['prefix'])
        for other in rule.get('related',[]):
            assert not exact_source(PL,other).startswith('Rule ')
        assert len(rule['english'])>=3


def test_every_illustration_is_valid_graphviz():
    for rule in RULES:
        proc=subprocess.run(['dot','-Tsvg'],input=rule_dot(rule),text=True,capture_output=True,check=True)
        assert '<svg' in proc.stdout


def test_live_fact_example_is_in_actual_selected_tree():
    t=load_tree(ROOT/'dialogue_demo/BehaviorTree.json')
    a=json.loads((ROOT/'sg_pipeline/access_map.json').read_text())
    text=facts(t,a)
    assert "access('n8',write,'normalized_input')." in text
    assert "access('n10',read,'normalized_input')." in text
