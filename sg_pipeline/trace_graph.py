"""Observed V10 demo events ONLY; never claim complete BT execution."""
def observed_trace(runner):
    if runner is None:return {'status':'NO_EXECUTION','events':[],'edges':[]}
    events=[];edges=[]
    for i,s in enumerate(runner.steps):
        event=s['event']; node=event.get('node_id')
        events.append({'step':i,'node_id':node,'status':event.get('status'),'detail':event.get('detail'),
                      'blackboard':s.get('working_blackboard',{})})
        if i:edges.append({'source':f'step-{i-1}','target':f'step-{i}','relation':'next_observed_event'})
    return {'status':'DEMO_TRACE_PARTIAL','events':events,'edges':edges,
            'note':'Events from the Streamlit demonstration runner; not a Prolog proof or full py_trees execution.'}
