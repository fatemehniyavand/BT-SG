"""Fast tests for educational diagrams and source-grounded converter walkthrough."""
import json
import subprocess
from pathlib import Path

from learning_lab import (
    PHASES, PROLOG_STEPS, lesson_dot, prolog_dot, source_for_step,
    preview_facts, service_view_dot,
)
from sg_pipeline.convert import load_tree, kind
from sg_pipeline.service_view import project
from slots import SLOT_SPECS

ROOT=Path(__file__).resolve().parents[2]
T=load_tree(ROOT/'dialogue_demo/BehaviorTree.json')
ACCESS=json.loads((ROOT/'sg_pipeline/access_map.json').read_text())
PL=(ROOT/'sg_pipeline/converter.pl').read_text()


def test_five_lessons_reflect_actual_names_and_algorithms():
    assert len(PHASES)==5
    assert {'input','normalize','topic','intent','slots'}=={p['id'] for p in PHASES}
    assert 'Multinomial Naive Bayes' in PHASES[2]['method']
    assert 'Logistic Regression' in PHASES[3]['method']
    assert 'regex' not in PHASES[4]['method'].lower() or 'regular-expression' in PHASES[4]['method']
    for phase in PHASES:
        assert any(node['name'] in phase['node_names'] for node in T['nodes'].values())
    assert all(len(spec)==3 for topics in SLOT_SPECS.values() for spec in topics.values())


def test_facts_are_generated_from_same_source_tree_and_access_map():
    facts=preview_facts(T, ACCESS)
    assert "bt_root('n0')." in facts
    assert "access('n8',write,'normalized_input')." in facts
    assert "access('n10',read,'normalized_input')." in facts
    assert sum(line.startswith('bt_node(') for line in facts.splitlines())==len(T['nodes'])==26
    assert sum(line.startswith('bt_child(') for line in facts.splitlines())==25


def test_displayed_prolog_rules_are_verbatim_current_file():
    facts=preview_facts(T, ACCESS)
    assert len(PROLOG_STEPS)==7
    for i in range(7):
        title, snippet=source_for_step(i,PL,facts)
        assert title and snippet
        if i in (3,4,5):
            assert snippet.splitlines()[0] in PL
    assert 'potential_data(W,R,K)' in source_for_step(4,PL,facts)[1]


def test_educational_diagrams_are_valid_graphviz():
    for dot in [*(lesson_dot(x['id']) for x in PHASES),*(prolog_dot(i) for i in range(7))]:
        subprocess.run(['dot','-Tsvg'],input=dot,text=True,capture_output=True,check=True)


def test_service_projection_diagrams_are_valid():
    nodes=[{'id':id,'kind':kind(node),'label':node.get('title') or node['name']}
           for id,node in T['nodes'].items()]
    services=[{'id':x['id'],'label':x['label']} for x in nodes if x['kind']=='action']
    # Fixture intentionally emulates edges for graph rendering; this is NOT a
    # substitution for actual SWI-Prolog execution, which happens separately.
    candidates=[{'source':a['id'],'target':b['id'],'key':key}
                for a in services for b in services if a['id']!=b['id']
                for key in ACCESS.get(T['nodes'][a['id']]['name'],{}).get('writes',[])
                if key in ACCESS.get(T['nodes'][b['id']]['name'],{}).get('reads',[])]
    view=project({'nodes':nodes,'service_nodes':services,'service_data_edges':candidates},T,ACCESS)
    assert len(view['services'])==9 and len(view['blackboard_keys'])==4
    for layer in ('control','blackboard','possible'):
        dot=service_view_dot(view,layer)
        subprocess.run(['dot','-Tsvg'],input=dot,text=True,capture_output=True,check=True)
    assert 'repeat_after_reply' in service_view_dot(view,'control')
    assert 'normalized_input' in service_view_dot(view,'blackboard')
    assert 'POSSIBLE' not in service_view_dot(view,'control')
