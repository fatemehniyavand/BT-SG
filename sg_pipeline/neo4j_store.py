"""Isolated BT analysis database. No destructive whole-DB deletes."""
from __future__ import annotations
import json,os
def upload_graph(graph,uri=None,user=None,password=None,graph_id='dialogue-tree-v1'):
    from neo4j import GraphDatabase
    uri=uri or os.environ.get('NEO4J_URI','bolt://localhost:7687')
    user=user or os.environ.get('NEO4J_USER','neo4j')
    password=password or os.environ.get('NEO4J_PASSWORD')
    if not password:raise ValueError('Set NEO4J_PASSWORD')
    with GraphDatabase.driver(uri,auth=(user,password)) as driver:
        driver.verify_connectivity()
        def txfn(tx):
            tx.run('MATCH (n:BTNode {graph_id:$gid}) DETACH DELETE n',gid=graph_id).consume()
            tx.run('UNWIND $rows AS row CREATE (n:BTNode {graph_id:$gid,id:row.id,label:row.label,kind:row.kind})',rows=graph['nodes'],gid=graph_id).consume()
            tx.run('UNWIND $rows AS row MATCH (n:BTNode {graph_id:$gid,id:row.id}) SET n:ServiceTask',rows=graph['service_nodes'],gid=graph_id).consume()
            for field,reltype in [('loop_edges','LOOP_BACK'),('service_data_edges','POTENTIAL_SERVICE_DATA'),('control_edges','CONTROL_CHILD'),('ordered_edges','SIBLING_GATE'),('potential_data_edges','POTENTIAL_DATA')]:
                tx.run(f"""UNWIND $rows AS row
                    MATCH (a:BTNode {{graph_id:$gid,id:row.source}}),(b:BTNode {{graph_id:$gid,id:row.target}})
                    CREATE (a)-[r:{reltype}]->(b)
                    SET r.relation=row.relation,r.layer=row.layer,r.index=coalesce(row.index,-1),
                        r.gate=coalesce(row.gate,''),r.key=coalesce(row.key,''),r.exit_gate=coalesce(row.exit_gate,'')""",rows=graph[field],gid=graph_id).consume()
        with driver.session() as session:session.execute_write(txfn)
    return graph_id
if __name__=='__main__':
    import sys
    graph=json.load(open(sys.argv[1],encoding='utf8'))
    print('Graph uploaded:',upload_graph(graph))
