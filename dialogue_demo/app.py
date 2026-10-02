"""Single-page, high-contrast trace UI around the original BehaviorTree.json."""
import copy
import html
import json
from pathlib import Path

import streamlit as st
from engine import Runner, to_dot, INTENT_DESCRIPTIONS, INTENT_EXAMPLES, SLOT_SPECS, prefix_path
from slots import SLOT_LABELS, SLOT_EXAMPLES

st.set_page_config(page_title="Dialogue BT · Execution Studio V10",page_icon="🌳",layout="wide",initial_sidebar_state="collapsed")
st.markdown('''<style>
:root,html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],
[data-testid="stHeader"],[data-testid="stSidebar"],[data-testid="stSidebarContent"],
[data-testid="stBottom"],.stChatFloatingInputContainer {background:#FFFFFF!important;color:#101010!important;color-scheme:light!important;}
.stApp *:not(.stButton button):not(.stDownloadButton button):not(.stFormSubmitButton button):not(svg):not(path) {color:#111111;}
.stApp h1,.stApp h2,.stApp h3,.stApp p,.stApp label,.stApp span,.stApp strong,.stApp small,
.stApp [data-testid="stMarkdownContainer"],.stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stMetricValue"],.stApp [data-testid="stMetricLabel"] {color:#101010!important;}
.stApp input,.stApp textarea,.stApp input:focus,.stApp textarea:focus,.stApp input:disabled,.stApp textarea:disabled,
.stApp [data-baseweb="input"],.stApp [data-baseweb="textarea"],.stApp [data-baseweb="select"]>div,
.stApp [data-testid="stChatInput"] textarea,.stApp [data-testid="stChatInput"] textarea:focus {
 background:#FFFFFF!important;background-color:#FFFFFF!important;color:#111111!important;
 -webkit-text-fill-color:#111111!important;opacity:1!important;border-color:#64748B!important;caret-color:#111111!important;}
.stApp input::placeholder,.stApp textarea::placeholder {color:#535353!important;opacity:1!important;}
.stApp [data-testid="stSelectbox"] *,[role="listbox"],[role="option"],[data-baseweb="menu"] {
 background-color:#FFFFFF!important;color:#111111!important;}
[role="option"]:hover,[role="option"][aria-selected="true"] {background-color:#E8F0FB!important;color:#111111!important;}
.stApp .stButton button,.stApp .stButton button:hover,.stApp .stButton button:active,.stApp .stButton button:focus,
.stApp .stDownloadButton button,.stApp .stDownloadButton button:hover,.stApp .stDownloadButton button:focus,
.stApp .stFormSubmitButton button,.stApp .stFormSubmitButton button:hover,.stApp .stFormSubmitButton button:focus {
 background:#1458A2!important;background-color:#1458A2!important;border:2px solid #1458A2!important;color:#FFFFFF!important;
 opacity:1!important;box-shadow:none!important;}
.stApp .stButton button *,.stApp .stDownloadButton button *,.stApp .stFormSubmitButton button *,
.stApp .stButton button:hover *,.stApp .stButton button:active * {color:#FFFFFF!important;}
.stApp button:focus-visible,.stApp input:focus-visible,.stApp textarea:focus-visible {outline:3px solid #4D8BD5!important;outline-offset:2px!important;}
.stApp [data-testid="stAlert"],.stApp [data-testid="stExpander"],.stApp [data-testid="stFileUploader"],
.stApp [data-testid="stChatMessage"],.stApp [data-testid="stDataFrame"] {background:#FFFFFF!important;border-color:#B9C9D8!important;color:#111111!important;}
.stApp [data-testid="stAlert"] *,.stApp [data-testid="stExpander"] *,.stApp [data-testid="stChatMessage"] * {color:#111111!important;}
.stApp [data-testid="stCodeBlock"] pre,.stApp [data-testid="stCodeBlock"] code,
.stApp [data-testid="stJson"] {background:#F5F7FA!important;color:#111111!important;}
.stApp [data-testid="stDataFrame"] iframe {color-scheme:light!important;}
.stApp hr {border-color:#B9C9D8!important;}
.btbox{background:#FFFFFF;border:1px solid #99A9B9;border-radius:10px;padding:15px;margin:8px 0;color:#111111!important;}
.btbox b,.btbox span,.btbox div{color:#111111!important;}
.section-heading{background:#F4F7FA;border-left:4px solid #1458A2;border-radius:5px;padding:10px;margin:10px 0;font-weight:700;color:#111111!important;}
/* Charts and built-in table header use the same fixed neutral palette. */
.stApp table,.stApp th,.stApp td {background:#FFFFFF!important;color:#111111!important;border-color:#D4DCE4!important;}
</style>''',unsafe_allow_html=True)

st.markdown('''<style>
/* Explicit colors for all stable control states, including mobile and active tabs. */
html,body,.stApp,.stAppViewContainer,section[data-testid="stSidebar"],
[data-testid="stMainBlockContainer"], [data-testid="stVerticalBlock"] { background-color:#fff!important;color:#111!important; }
.stApp button,.stApp button:focus,.stApp button:hover,.stApp button:active {
  background:#1458A2!important;color:#fff!important;border-color:#1458A2!important;
}
.stApp button :is(p,span,svg){color:#fff!important;fill:currentColor;}
.stApp [data-baseweb="tab-list"] button {background:#f0f5fa!important;color:#111!important;border:1px solid #9eaec1!important;}
.stApp [data-baseweb="tab-list"] button *{color:#111!important;}
.stApp [data-baseweb="tab-list"] button[aria-selected="true"]{background:#1458A2!important;color:#fff!important;}
.stApp [data-baseweb="tab-list"] button[aria-selected="true"] *{color:#fff!important;}
.stApp [data-testid="stChatMessage"],.stApp [data-testid="stChatMessage"] *{background-color:#fff!important;color:#111!important;}
.stApp [data-testid="stDataFrame"],.stApp div[data-testid="stMetric"] {border:1px solid #a9bcd0;border-radius:10px;}
.stApp p,.stApp label,.stApp textarea,.stApp input,.stApp code {opacity:1!important;}
/* Controlled white code areas; dark text regardless of OS theme. */
.stApp pre,.stApp code,.stApp [data-testid="stCodeBlock"] *{background:#f5f8fc!important;color:#111!important;}
</style>''',unsafe_allow_html=True)
ROOT=Path(__file__).resolve().parent
@st.cache_data
def parse_tree(payload):
    obj=json.loads(payload); ts=obj['trees']; selected=obj.get('selectedTree')
    t=next((a for a in ts if a.get('id')==selected),ts[0]);prefix_path(t);return t

with st.sidebar:
    st.header('Execution Studio')
    st.caption('White background · black text · fixed blue buttons')
    uploaded=st.file_uploader('Replace original tree JSON (optional)',type=['json'])
    payload=uploaded.getvalue().decode('utf-8') if uploaded else (ROOT/'BehaviorTree.json').read_text(encoding='utf-8')
    try: tree=parse_tree(payload)
    except Exception as exc: st.error(f'Cannot read tree: {exc}');st.stop()
    st.markdown('**Tree:** '+tree['title'])
    st.markdown('**Demo scope:** Text → Normalization → Topic → Intent → Slot Filling')
    st.caption('Neo4j retrieval and full py_trees runtime are not executed in this version.')
    st.markdown('**Node colors**')
    st.markdown('🟢 SUCCESS · 🔴 FAILURE · 🔵 RUNNING · 🟡 NEXT')
    if st.button('Clear session / new conversation',use_container_width=True):
        for k in ('runner','messages','draft','tree_key'): st.session_state.pop(k,None)
        st.rerun()

if 'runner' not in st.session_state: st.session_state.runner=None
if 'messages' not in st.session_state: st.session_state.messages=[]
if 'draft' not in st.session_state: st.session_state.draft=''
if 'tree_key' not in st.session_state: st.session_state.tree_key=payload
if payload!=st.session_state.tree_key:
    st.session_state.runner=None;st.session_state.messages=[];st.session_state.tree_key=payload

r=st.session_state.runner
st.title('Dialogue Behavior Tree · Execution Studio V10')
st.markdown('**Execution:** original JSON tree → audited text preprocessing → topic → intent → three mandatory slots → visible loop back or exit')
st.caption('Same original JSON tree · live clarification directly in the chat · full loop and Blackboard audit')
# Main diagram and chat share the upper viewport; no disconnected clarification form at page bottom.
graph_col,chat_col=st.columns([1.4,1],gap='large')
with chat_col:
    st.subheader('Conversation · input and clarification')
    st.caption('The assistant asks missing-slot questions here, directly beneath the main conversation.')
    for m in st.session_state.messages:
        with st.chat_message(m['role']): st.write(m['content'])
    if r and r.runtime.get('slot_state')=='COMPLETE':
        st.success('All mandatory slots filled. The loop has EXITED; Neo4j is the next (inactive) stage.')
    if r and r.runtime.get('slot_state')=='WAITING_USER':
        st.markdown('<div class="section-heading">Clarification required · reply in this same chat</div>',unsafe_allow_html=True)
        st.write('**Missing now:** '+', '.join(r.runtime['missing_slots']))
        st.write('**Next question:** '+r.runtime['clarifying_question'])
        outstanding=r.runtime['missing_slots']; key=outstanding[0]
        st.markdown('**How to answer**')
        st.write('Option A — answer only the current question, for example:')
        st.code(SLOT_EXAMPLES.get(key,'Your answer'),language=None)
        if len(outstanding)>1:
            st.write('Option B — fill several or all remaining slots in ONE reply (recommended if you know them):')
            st.code('; '.join(f'{field}={SLOT_EXAMPLES.get(field,"your value")}' for field in outstanding),language=None)
        st.caption('Use `slot_name=value; slot_name=value` for a multi-answer reply. The program checks each field independently, then loops back on the SAME original tree. Only unanswered slots are asked next.')
    if r and r.runtime.get('slot_state') not in ('WAITING_USER','COMPLETE'):
        st.info('Use Next BT step or Run to Slot Filling to reach the next decision.')
    with st.form('main_chat',clear_on_submit=True):
        reply=st.text_area('Your message',height=95,placeholder='Enter a music/art question, or answer the current clarification question.',key='chat_entry')
        submitted=st.form_submit_button('Send message',use_container_width=True)
    if submitted:
        if not reply.strip(): st.warning('Type a message before sending.')
        elif r and r.runtime['slot_state']=='WAITING_USER':
            try:
                st.session_state.messages.append({'role':'user','content':reply.strip()})
                r.answer_slot(reply)
                if r.runtime['slot_state']=='WAITING_USER':
                    st.session_state.messages.append({'role':'assistant','content':r.runtime['clarifying_question']})
                else:
                    st.session_state.messages.append({'role':'assistant','content':'All mandatory slots are filled. The BT exits the clarification loop; retrieval is not executed in this demo.'})
                st.rerun()
            except ValueError as exc:
                st.session_state.messages.append({'role':'assistant','content':'Invalid value: '+str(exc)+' Please answer the current question again.'});st.rerun()
        elif r and r.runtime['slot_state']!='COMPLETE':
            st.warning('Finish the current BT run first; your question was not replaced.')
        else:
            st.session_state.runner=Runner(tree,reply)
            st.session_state.messages=[{'role':'user','content':reply}]
            st.rerun()
    c1,c2=st.columns(2)
    if c1.button('Next BT step',use_container_width=True):
        if not r: st.warning('First send a question in the chat.')
        elif r.cursor<len(r.path):
            r.next()
            if r.cursor==len(r.path):
                if r.runtime['slot_state']=='WAITING_USER':st.session_state.messages.append({'role':'assistant','content':r.runtime['clarifying_question']})
                elif r.runtime['slot_state']=='COMPLETE':st.session_state.messages.append({'role':'assistant','content':'All mandatory slots are filled. Loop exit.'})
            st.rerun()
    if c2.button('Run to Slot Filling',use_container_width=True):
        if not r: st.warning('First send a question in the chat.')
        else:
            old_state=r.runtime['slot_state'];r.run_all()
            if old_state=='NOT_STARTED':
                if r.runtime['slot_state']=='WAITING_USER':st.session_state.messages.append({'role':'assistant','content':r.runtime['clarifying_question']})
                elif r.runtime['slot_state']=='COMPLETE':st.session_state.messages.append({'role':'assistant','content':'All mandatory slots are filled. Loop exit.'})
            st.rerun()

with graph_col:
    st.subheader('Original Behavior Tree · full runtime trace')
    st.caption('Dashed orange arrow: ask → recheck same decorator. Dashed green: loop exits. Neither arrow changes the source JSON.')
    slot_state=r.runtime['slot_state'] if r else None
    iteration=r.runtime['slot_iteration'] if r else 0
    current=(r.path[r.cursor]['id'] if r and r.cursor<len(r.path) and not r.error else None)
    viewed_steps=r.steps if r else []
    viewed_loop_state=slot_state
    viewed_iteration=iteration
    if r and r.steps:
        review=st.toggle('Replay a saved step on the original tree',value=False,key='graph_replay')
        if review:
            selected=st.select_slider('Executed event',options=list(range(len(r.steps))),value=len(r.steps)-1,
                format_func=lambda i:f'{i+1:02d} · {r.steps[i]["event"]["node"]} · {r.steps[i]["event"]["status"]}',key='tree_step')
            viewed_steps=r.steps[:selected+1]
            viewed_loop_state=r.steps[selected]['blackboard']['slot_state']
            viewed_iteration=r.steps[selected]['blackboard']['slot_iteration']
            current=r.steps[selected]['event']['node_id']
            st.caption('Event: '+r.steps[selected]['event']['detail'])
    st.graphviz_chart(to_dot(tree,viewed_steps,current,viewed_loop_state,viewed_iteration),use_container_width=True)
    if r and slot_state=='WAITING_USER':
        st.warning(f'↩ LOOP ACTIVE · iteration {iteration}: Ask Clarifying Question → Repeat Until Failure → Slots Not Filled?')
    elif r and slot_state=='COMPLETE':
        st.success(f'✓ EXIT on check iteration {iteration}: Slots Not Filled? = FAILURE → Repeat Until Failure = SUCCESS → Select Database (not executed).')
    else:st.info('Feedback arrow is drawn ON the full tree when Slot Filling starts.')

st.divider()
from learning_lab import render_lab
render_lab(st,tree,r,ROOT.parent)
st.divider()
s1,s2,s3=st.tabs(['Required slots & live loop','Execution steps & Blackboard','Normalization & model diagnostics'])
with s1:
    st.subheader('Every defined intent and its exact mandatory slots')
    catalogue=[{'Topic':topic,'Intent':intent,'Mandatory slot':SLOT_LABELS.get(key,key),'Technical key':key,'Example':SLOT_EXAMPLES.get(key,'—'),'Question if missing':q}
               for topic,ints in SLOT_SPECS.items() for intent,slots in ints.items() for key,q in slots.items()]
    st.dataframe(catalogue,use_container_width=True,hide_index=True)
    if r and r.runtime.get('intent'):
        bb=r.runtime; req=SLOT_SPECS[bb['topic']][bb['intent']]
        st.markdown(f'<div class="section-heading">Active intent: {html.escape(bb["topic"])} / {html.escape(bb["intent"])} · Loop state: {html.escape(bb["slot_state"])} · iteration: {bb["slot_iteration"]}</div>',unsafe_allow_html=True)
        st.dataframe([{'Required slot':SLOT_LABELS.get(s,s), 'Technical key':s, 'Example answer':SLOT_EXAMPLES.get(s,'—'), 'Value in Blackboard':bb['slots'].get(s,'—'),
                       'State':'FILLED' if bb['slots'].get(s) else 'MISSING',
                       'Question if missing':question} for s,question in req.items()],use_container_width=True,hide_index=True)
        completed=sum(bool(bb['slots'].get(s)) for s in req)
        st.progress(completed/len(req),text=f'{completed} / {len(req)} mandatory slots filled')
        st.markdown('**Exactly what will happen next**')
        if bb['slot_state']=='WAITING_USER':
            st.write(f'Iteration {bb["slot_iteration"]}: **Slots Not Filled? = SUCCESS** → Ask Clarifying Question ({bb["missing_slots"][0]}) → wait → write to Blackboard → arrow returns to Repeat Until Failure.')
        elif bb['slot_state']=='COMPLETE':
            st.write(f'Iteration {bb["slot_iteration"]}: **Slots Not Filled? = FAILURE** → Repeat Until Failure = SUCCESS → exit (Neo4j is NOT queried yet).')
        st.markdown('**Explicit loop decision**')
        if bb['slot_state']=='WAITING_USER':
            st.write('Check → at least one missing slot → ask the first missing-slot question → wait for the answer → save it → loop back to check.')
        elif bb['slot_state']=='COMPLETE':
            st.write('Check → no missing slots → Slots Not Filled? returns FAILURE → repeat decorator returns SUCCESS → EXIT.')
        else:st.write('Waiting for initial slot extraction.')
        st.markdown('**Slot values and exact origin**')
        history=bb['slot_history']
        origin={x.get('slot'):f'clarification round {x.get("iteration")}' for x in history if x.get('source')=='clarification'}
        st.dataframe([{'slot':slot,'value':bb['slots'].get(slot,'—'),'status':'FILLED' if bb['slots'].get(slot) else 'MISSING',
                       'source':origin.get(slot,'initial utterance' if bb['slots'].get(slot) else 'awaiting reply')}
                      for slot in req],hide_index=True,use_container_width=True)
        st.markdown('**Previous questions, values and check iterations**')
        st.dataframe(bb['slot_history'] or [{'source':'waiting'}],use_container_width=True,hide_index=True)
    else:st.info('Run through Detect Intent to see the exact required slots for the current question.')
with s2:
    st.subheader('Compact Blackboard and execution timeline')
    if r:
        st.markdown('**Operational Blackboard — only data needed by the next BT stage**')
        st.json(r.blackboard,expanded=True)
        if r.steps:
            choices=list(range(len(r.steps)))
            index=st.select_slider('Select a saved BT event to inspect',options=choices,value=choices[-1],
                format_func=lambda i:f'{i+1:02d} · {r.steps[i]["event"]["node"]} · {r.steps[i]["event"]["status"]}')
            step=r.steps[index];event=step['event'];before=r.steps[index-1]['blackboard'] if index else {}
            st.markdown(f'**Step {index+1} · {event["node"]} · {event["status"]}**')
            st.write(event['detail'])
            prev=r.steps[index-1]['working_blackboard'] if index else {}
            after=step['working_blackboard']
            changed={k:{'before':prev.get(k),'after':v} for k,v in after.items() if prev.get(k)!=v}
            c1,c2=st.columns(2)
            with c1:st.markdown('**Exactly what changed during this event**');st.json(changed or {'changes':'No Blackboard value changed'},expanded=True)
            with c2:st.markdown('**Operational Blackboard AFTER this event**');st.json(after,expanded=True)
            st.caption('Model explanations, normalization steps, loop counters and execution logs are diagnostics, not Blackboard fields.')
            st.markdown('**Event timeline, including every loop-back and termination**')
            st.dataframe([{'Step':i+1,'Node':x['event']['node'],'Status':x['event']['status'],'What happened':x['event']['detail']} for i,x in enumerate(r.steps)],use_container_width=True,hide_index=True)
            st.download_button('Export compact Blackboard & execution trace JSON',json.dumps({'events':[{'event':s['event'],'blackboard':s['working_blackboard']} for s in r.steps],'final_blackboard':r.blackboard},ensure_ascii=False,indent=2),file_name='bt_execution_full_trace.json',mime='application/json')
    else:st.info('Send a question first to start recording snapshots.')
with s3:
    st.subheader('Visual Normalization · every transformation')
    st.caption('All Unicode letters and digits are retained. Other symbols become separators; whitespace is collapsed; exactly one final ? is added. No spelling or grammar correction.')
    if r and r.runtime['normalization']['steps']:
        norm=r.runtime['normalization']
        st.markdown("""<style>
        .normcard {background:#FFFFFF!important;border:2px solid #B7C7D8!important;
          padding:15px 18px!important;border-radius:12px!important;margin:6px 0!important;}
        .normcard strong,.normcard p,.normcard span,.normcard code{color:#101010!important;}
        .normcard code {display:block;white-space:pre-wrap;overflow-wrap:anywhere;background:#F3F7FC!important;
          border-radius:6px;padding:10px;font-size:15px;}
        .normarrow {text-align:center;color:#1458A2!important;font-size:25px;font-weight:900;}
        .normchip {background:#EAF2FC!important;border:1px solid #477AAE!important;
           border-radius:18px;display:inline-block;padding:7px 11px;margin:4px;color:#101010!important;}
        </style>""",unsafe_allow_html=True)
        st.markdown('<div class="normcard"><strong>Original user input</strong><code>'+html.escape(norm['original'])+'</code></div>', unsafe_allow_html=True)
        for idx,stage in enumerate(norm['steps'][:4], start=1):
            flag='CHANGED' if stage['changed'] else 'UNCHANGED'
            stage_markup=(f'<div class="normarrow">↓</div><div class="normcard">'
             f'<strong>{idx}. {html.escape(stage["operation"])} — {flag}</strong>'
             f'<p>{html.escape(stage["reason"])}</p><code>{html.escape(stage["after"])}</code></div>')
            st.markdown(stage_markup,unsafe_allow_html=True)
        st.markdown('**Individual numbered tokens**')
        chips=''.join(f'<span class="normchip">{i+1}. {html.escape(t)}</span>' for i,t in enumerate(norm['tokens']))
        st.markdown('<div class="normcard">'+chips+'</div>',unsafe_allow_html=True)
        st.markdown('**Final classifier input**')
        st.code(norm['normalized'],language=None)
        with st.expander('Compare before and after for every operation'):
            st.dataframe([{'Rule':x['operation'],'Changed':x['changed'],'Before':x['before'],'After':x['after'],'Reason':x['reason']} for x in norm['steps']],use_container_width=True,hide_index=True)
    else:
        st.info('Send a question, then advance the Behavior Tree to Normalize Input.')
    st.divider()
    st.subheader('Why the Intent classifier selected this intent')
    if r and r.runtime.get('intent_explanation'):
        d=r.runtime['intent_explanation']
        st.write('Topic read from Blackboard:',d['topic_from_blackboard'],'· Model:',d['selected_model'])
        st.dataframe(d['recognized_features'] or [{'term':'None recognized','tfidf':0}],hide_index=True,use_container_width=True)
        st.dataframe([{'Candidate intent':x['intent'],'Uncalibrated model score':x['model_score'],'Explanation':x['description']} for x in d['ranking']],hide_index=True,use_container_width=True)
        selected=st.selectbox('Inspect intent evidence',[x['intent'] for x in d['ranking']],key='intent_why')
        row=next(x for x in d['ranking'] if x['intent']==selected)
        a,b=st.columns(2)
        with a:st.markdown('**Supporting features**');st.dataframe(row['positive_features'] or [{'term':'None','contribution':0}],hide_index=True)
        with b:st.markdown('**Contradicting features**');st.dataframe(row['negative_features'] or [{'term':'None','contribution':0}],hide_index=True)
        st.warning('Small synthetic training set. These scores are not calibrated confidence or validated accuracy.')
    else:st.info('Advance to Detect Intent to reveal model evidence.')
st.caption('The full diagram is derived from the supplied tree; the dashed loop arrow is a runtime visualization. Knowledge graph retrieval and BT→SG Prolog integration are future phases.')


# Graph analysis is deliberately separate from dialogue execution state.
st.divider()
st.header('BT → Prolog → Service Graph → Neo4j')
st.caption('Static graph: potential structural/data links. Partial runtime trace is a different result; no unsupported placement inference.')
import sys
if str(ROOT.parent) not in sys.path:sys.path.insert(0,str(ROOT.parent))
from sg_pipeline.convert import convert as convert_sg
from sg_pipeline.graphviz_view import dot as service_dot
from sg_pipeline.trace_graph import observed_trace
with st.expander('Prolog conversion & Neo4j visualization',expanded=False):
    if st.button('Run actual SWI-Prolog conversion',key='run_swipl'):
        try:
            graph=convert_sg(ROOT/'BehaviorTree.json',ROOT.parent/'outputs/service_graph.json')
            st.session_state['static_sg']=graph
        except Exception as exc:st.error(f'Conversion unavailable: {exc}')
    if 'static_sg' in st.session_state:
        graph=st.session_state['static_sg']
        st.write(f"{len(graph['nodes'])} nodes · {len(graph['control_edges'])} control edges · {len(graph['ordered_edges'])} sibling gates · {len(graph['potential_data_edges'])} potential data edges")
        show_data=st.checkbox('Show potential Blackboard data edges (not guaranteed)',value=False)
        st.graphviz_chart(service_dot(graph,show_data),use_container_width=True)
        st.download_button('Download Prolog Service Graph JSON',json.dumps(graph,indent=2,ensure_ascii=False),file_name='service_graph.json',mime='application/json')
        with st.expander('Neo4j upload (requires running database)'):
            st.warning('This replaces only nodes with graph_id=dialogue-tree-v1, not the entire database.')
            import os
            uri=st.text_input('Bolt URI',os.environ.get('NEO4J_URI','bolt://localhost:7687'))
            user=st.text_input('Neo4j username',os.environ.get('NEO4J_USER','neo4j'))
            password=st.text_input('Neo4j password',type='password')
            if st.button('Upload static graph to Neo4j',key='upload_neo4j'):
                try:
                    from sg_pipeline.neo4j_store import upload_graph
                    upload_graph(graph,uri=uri,user=user,password=password)
                    st.success('Graph uploaded. Open Neo4j Browser and run the query in sg_pipeline/README.md')
                except Exception as exc:st.error(f'Neo4j upload failed: {exc}')
    st.subheader('Observed demo trace (not full py_trees runtime)')
    st.json(observed_trace(r),expanded=False)
