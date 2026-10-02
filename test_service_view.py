"""Run with python test_service_view.py from project root after copying service_view.py."""
import json
from sg_pipeline.convert import load_tree,kind
from sg_pipeline.service_view import project

def run():
    tree=load_tree('dialogue_demo/BehaviorTree.json')
    access=json.load(open('sg_pipeline/access_map.json'))
    nodes=[{'id':id,'kind':kind(node),'label':node.get('title') or node['name']}
           for id,node in tree['nodes'].items()]
    services=[{'id':x['id'],'label':x['label']} for x in nodes if x['kind']=='action']
    possible=[{'source':a['id'],'target':b['id'],'key':key} for a in services for b in services
              if a['id'] != b['id'] for key in access.get(tree['nodes'][a['id']]['name'],{}).get('writes',[])
              if key in access.get(tree['nodes'][b['id']]['name'],{}).get('reads',[])]
    result=project({'nodes':nodes,'service_nodes':services,'service_data_edges':possible},tree,access)
    ids={x['id'] for x in result['services']} | {x['id'] for x in result['gateways']}
    assert len(result['services'])==9
    assert set(result['blackboard_keys'])=={'normalized_input','topic','intent','slots'}
    assert all(x['source'] in ids and x['target'] in ids for x in result['conditional_flow'])
    assert any(x['guard']=='repeat_after_reply' for x in result['conditional_flow'])
    print('PASS: service view projection and loop')

if __name__=='__main__':run()
