"""Offline readable learning report for the actual whole-tree Prolog conversion.

Run: python -m sg_pipeline.learning_report
This command uses REAL SWI-Prolog and writes inspectable source facts and results.
"""
from __future__ import annotations
import json
import argparse
from pathlib import Path
from .convert import convert,load_tree,facts
from .service_view import project


def report(base: Path, output: Path) -> str:
    tree_file=base/'dialogue_demo/BehaviorTree.json'
    access_file=base/'sg_pipeline/access_map.json'
    tree=load_tree(tree_file)
    access=json.loads(access_file.read_text(encoding='utf8'))
    graph=convert(tree_file,output,access_file)
    view=project(graph,tree,access)
    lines=[
        'BT → SWI-Prolog → STATIC GRAPH: complete Music + Art tree (no user question)',
        '='*74,
        '1. Python reads and validates the selected BehaviorTree.json.',
        f"   Root ID: {tree['root']}  |  source nodes: {len(tree['nodes'])}",
        '2. Python emits bt_node/bt_child/bt_root and declared access/3 facts.',
        f"   Saved source facts: {output.with_suffix('.facts.pl')}",
        '3. Real SWI-Prolog converter.pl infers the structural and possible-data layers.',
        f"   Full BT nodes: {len(graph['nodes'])}",
        f"   Parent/child control edges: {len(graph['control_edges'])}",
        f"   Ordered sibling gates: {len(graph['ordered_edges'])}",
        f"   Loop annotations: {len(graph['loop_edges'])}",
        f"   All candidate data edges: {len(graph['potential_data_edges'])}",
        f"   Action-only possible data edges: {len(graph['service_data_edges'])}",
        '4. Separate Python architectural view adds annotated conditional routes.',
        f"   Services: {len(view['services'])}, keys: {len(view['blackboard_keys'])}, gateways: {len(view['gateways'])}.",
        '   IMPORTANT: conditional_flow is curated in Python, not proved by Prolog.',
        '5. Inspect exactly what the project defined for Blackboard:',
    ]
    for entry in view['access']:
        source=next(x['name'] for x in view['services'] if x['id']==entry['service'])
        lines.append(f"   {source}: {entry['direction'].upper()} {entry['key']}")
    lines += ['', '6. Main presentation path (not a per-question runtime trace):']
    by_id={n['id']:n['name'] for n in view['services'] + view['gateways']}
    for link in view['conditional_flow']:
        lines.append(f"   {by_id[link['source']]} --[{link['guard']}]--> {by_id[link['target']]}")
    lines += ['', 'WARNING: potential_data does not establish path feasibility, execution order,',
              'or CPU/RAM requirements. The current text demo is not full py_trees runtime.',
              f'Graph JSON: {output}',
              f'Facts file: {output.with_suffix(".facts.pl")}']
    text='\n'.join(lines)+'\n'
    (output.parent/'learning_report.txt').write_text(text,encoding='utf8')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default='outputs/service_graph.json')
    args=p.parse_args()
    base=Path(__file__).resolve().parent.parent
    out=Path(args.output)
    if not out.is_absolute():out=base/out
    out.parent.mkdir(parents=True,exist_ok=True)
    print(report(base,out))

if __name__=='__main__':main()
