"""Preserve full source BT and invoke SWI-Prolog for graph derivation."""
from __future__ import annotations
import argparse, json, shutil, subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent
def atom(value):
    return "'" + str(value).replace("'","''").replace(chr(10)," ") + "'"
def load_tree(path):
    doc=json.loads(Path(path).read_text(encoding='utf8'))
    return next((t for t in doc['trees'] if t['id']==doc.get('selectedTree')),doc['trees'][0])
def validate(tree):
    nodes=tree['nodes'];root=tree['root'];assert root in nodes
    parents={k:0 for k in nodes}
    for k,n in nodes.items():
        children=n.get('children',[])+([n['child']] if n.get('child') else [])
        for c in children:
            if c not in nodes:raise ValueError(f'Undefined child {c} in {k}')
            parents[c]+=1
    if parents[root]:raise ValueError('Root has parent')
    if any(v>1 for v in parents.values()):raise ValueError('Multiple parents: not a tree')
    seen=set();active=set()
    def walk(k):
        if k in active:raise ValueError('Cycle in source tree')
        if k in seen:return
        active.add(k)
        n=nodes[k]
        for c in n.get('children',[])+([n['child']] if n.get('child') else []):walk(c)
        active.remove(k);seen.add(k)
    walk(root)
    if len(seen)!=len(nodes):raise ValueError('Orphan nodes')
def kind(n):
    name=n['name'].casefold()
    if name=='sequence':return 'sequence'
    if name in ('selector','fallback'):return 'fallback'
    if name=='repeatuntilfailure':return 'repeat_until_failure'
    if n.get('children') or n.get('child'):return 'other_composite'
    if name.startswith('condition') or name=='slots not filled':return 'condition'
    return 'action'
def facts(tree,access):
    validate(tree);lines=['% Auto-generated from user BehaviorTree.json. Do not hand edit.',f'bt_root({atom(tree["root"])}).']
    for nodeid,n in tree['nodes'].items():
        lines.append(f'bt_node({atom(nodeid)},{kind(n)},{atom(n.get("title") or n["name"])}).')
        for i,ch in enumerate(n.get('children',[])+([n['child']] if n.get('child') else [])):
            lines.append(f'bt_child({atom(nodeid)},{i},{atom(ch)}).')
        for direction,pldir in (('reads','read'),('writes','write')):
            for key in access.get(n['name'],{}).get(direction,[]):
                lines.append(f'access({atom(nodeid)},{pldir},{atom(key)}).')
    return '\n'.join(lines)+'\n'
def convert(tree_path,output,access_path=None):
    if not shutil.which('swipl'):raise RuntimeError('SWI-Prolog executable swipl not found. Install it before conversion.')
    tree=load_tree(tree_path)
    access=json.loads(Path(access_path or BASE/'access_map.json').read_text(encoding='utf8'))
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    facts_path=output.with_suffix('.facts.pl');facts_path.write_text(facts(tree,access),encoding='utf8')
    proc=subprocess.run(['swipl','-q','-s',str(BASE/'converter.pl'),'--',str(facts_path),str(output)],capture_output=True,text=True)
    if proc.returncode:raise RuntimeError(f'Prolog conversion failed: {proc.stderr}')
    graph=json.loads(output.read_text(encoding='utf8'))
    if len(graph['nodes'])!=len(tree['nodes']):raise RuntimeError('Node conservation failed')
    return graph
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tree',default=str(BASE.parent/'dialogue_demo/BehaviorTree.json'))
    p.add_argument('--output',default=str(BASE.parent/'outputs/service_graph.json'))
    p.add_argument('--access');a=p.parse_args()
    g=convert(a.tree,a.output,a.access)
    print('Converted with SWI-Prolog:',len(g['nodes']),'nodes;',len(g['control_edges']),'control edges;',len(g['ordered_edges']),'sibling gates;',len(g['potential_data_edges']),'potential data edges')
