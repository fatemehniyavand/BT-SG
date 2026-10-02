def dot(graph, show_data=False):
    import json
    def q(v):return json.dumps(str(v))
    lines=['digraph G {','rankdir=LR;','graph [bgcolor="white",splines=true,overlap=false];',
           'node [shape=box,style="rounded,filled",fillcolor="#F3F7FD",color="#5D87B5",fontcolor="#111111",fontsize=10];']
    for n in graph['nodes']:
        lines.append(f'{q(n["id"])} [label={q(n["label"]+chr(10)+n["kind"])}];')
    for e in graph['control_edges']:
        lines.append(f'{q(e["source"])} -> {q(e["target"])} [color="#718096",label={q(str(e["index"]))}];')
    for e in graph['ordered_edges']:
        lines.append(f'{q(e["source"])} -> {q(e["target"])} [style=dashed,color="#C27D24",constraint=false,label={q(e["gate"])}];')
    if show_data:
        for e in graph['potential_data_edges']:
            lines.append(f'{q(e["source"])} -> {q(e["target"])} [style=dotted,color="#2B8B68",constraint=false,label={q(e["key"])}];')
    return '\n'.join(lines+['}'])
