"""Read-only, source-grounded learning lab for the current BT and Prolog converter.

Do not treat this tutorial's illustrative diagrams as an execution trace or a
proved deployment graph. Conversion is delegated to the EXISTING SWI-Prolog path.
"""
from __future__ import annotations

import json
from pathlib import Path

from slots import SLOT_SPECS, SLOT_EXAMPLES

PHASES = [
    {
        'id': 'input', 'title': 'New Input + Input Modality',
        'node_names': ('ConditionNewInputAvailable', 'Fallback', 'ConditionIsVoice', 'ConditionIsText', 'ActionSpeechToText'),
        'method': 'Rule-based conditions and an ordered Fallback (Selector); Speech-to-Text is a declared action.',
        'why': 'The same dialogue tree should accept text and voice. A Fallback tries Voice first; when Is Voice fails it tries Text. The selected branch then feeds one text representation to Normalize Input.',
        'inputs': 'Input type + raw user input', 'reads': 'External input; no compact Blackboard key.',
        'writes': 'Text for the next action; this is transient before normalization.',
        'limitations': 'The current V10 demo runs the TEXT branch; the actual speech recognition backend is NOT implemented in this demo.',
        'node_flow': 'New Input? → Fallback → [Is Voice? → Speech To Text] OR [Is Text?] → Normalize Input',
    },
    {
        'id': 'normalize', 'title': 'Normalize Input',
        'node_names': ('ActionNormalizeInput',),
        'method': 'Deterministic Unicode NFC + character filtering + whitespace collapse + one final question mark + whitespace tokenization + separate casefold view.',
        'why': 'Provides a reproducible input for TF-IDF. Keeping Unicode letters AND digits preserves numeric song/artwork titles. Normalization is not a language understanding model.',
        'inputs': 'Raw or transcribed text', 'reads': 'Text from selected input branch.',
        'writes': 'normalized_input',
        'limitations': 'All internal punctuation is removed as separators. Spelling/grammar are NOT corrected; punctuation inside a proper name can be lost.',
        'node_flow': 'raw text → NFC → retain letters/digits → collapse spaces → ? → tokenize → casefold for classifier',
    },
    {
        'id': 'topic', 'title': 'Detect Topic',
        'node_names': ('Sequence', 'ActionNaiveBayesTopicClassifier'),
        'method': 'TF-IDF word 1–2 grams (sublinear_tf=True) → Multinomial Naive Bayes (alpha=0.6).',
        'why': 'This baseline classifies short, sparse text into the two defined topics (Music and Art). It is fast, simple, and inspectable.',
        'inputs': 'normalized_input', 'reads': 'normalized_input', 'writes': 'topic',
        'limitations': 'Training examples are small and synthetic. Scores are not measured generalization accuracy, and no calibrated out-of-domain rejection is implemented.',
        'node_flow': 'normalized_input → TF-IDF → Naive Bayes → {music | art} → Blackboard.topic',
    },
    {
        'id': 'intent', 'title': 'Detect Intent',
        'node_names': ('Detect Intern',),
        'method': 'Read topic from Blackboard → select topic-specific TF-IDF (1–2 grams) + multinomial Logistic Regression (max_iter=1500; class_weight=balanced).',
        'why': 'Music and Art have distinct intent sets. A topic-specific linear classifier lets the dashboard inspect vocabulary, feature weights, and per-intent scores.',
        'inputs': 'normalized_input + topic', 'reads': 'normalized_input, topic', 'writes': 'intent',
        'limitations': 'Model scores are uncalibrated and example-trained. Named entities outside the template vocabulary may be poorly represented; confidence is not a validated accuracy measure.',
        'node_flow': 'Blackboard.topic → choose Music/Art classifier; normalized_input → TF-IDF → Logistic Regression → Blackboard.intent',
    },
    {
        'id': 'slots', 'title': 'Slot Filling / Clarification Loop',
        'node_names': ('RepeatUntilFailure', 'Slots Not Filled', 'Ask clarifying question'),
        'method': 'Intent-specific three-slot schema; regular-expression initial extraction; explicit choice validation; missing-slot check; single or labeled multi-slot clarification.',
        'why': 'Avoid querying the knowledge base with missing or ambiguous arguments. Ask only for missing information and keep valid answers between clarification turns.',
        'inputs': 'topic + intent + corrected-display question + user clarification replies',
        'reads': 'intent, slots', 'writes': 'slots',
        'limitations': 'Rules and regular expressions are heuristic. Three required slots are project design choices, not universal scientific requirements; the active demo shows a semantic loop but is not a full py_trees runtime.',
        'node_flow': 'extract slots → missing? YES: ask → validate reply → update slots → RECHECK; NO: exit to Select Database (not run in demo)',
    },
]

PROLOG_STEPS = [
    ('1. Read the actual tree', 'Python reads the selected BehaviorTree.json, validates the root, child IDs, unique parents, no cycles, and reachability. No user question is needed.', 'python'),
    ('2. Generate Prolog facts', 'Python generates bt_root/1, bt_node/3, bt_child/3. It also generates access/3 from a separately maintained, proposed Blackboard access_map.json.', 'facts'),
    ('3. Run SWI-Prolog', 'Python invokes swipl with converter.pl and those generated facts. No Python substitute is silently used if SWI-Prolog is missing.', 'call'),
    ('4. Infer structure', 'Prolog extracts all parent/child edges, sibling ordering for Sequence and Fallback, and explicit Repeat annotations. The original 26-node tree is preserved.', 'control'),
    ('5. Infer candidate data links', 'potential_data/3 matches declared writers and readers of the SAME Blackboard key. These are possible links; exclusive branches and runtime order are not proved.', 'data'),
    ('6. Collect graph JSON', 'build_graph/1 collects structural edges, ordered gates, loops, candidate data dependencies and action nodes. Python checks node conservation.', 'output'),
    ('7. Project + upload separately', 'Python service_view.py creates the readable 9-service / 4-key / 3-gateway architectural view. CONDITIONAL_FLOW is a Python design projection, NOT a result inferred by Prolog.', 'projection'),
]


def phase_for_node(name: str) -> str | None:
    """Tie the teaching flow to actual custom-node names, not fabricated IDs."""
    if name in ('ConditionNewInputAvailable', 'Fallback', 'ConditionIsVoice', 'ConditionIsText', 'ActionSpeechToText'):
        return 'input'
    if name == 'ActionNormalizeInput': return 'normalize'
    if name in ('ActionNaiveBayesTopicClassifier',): return 'topic'
    if name in ('Detect Intern',): return 'intent'
    if name in ('RepeatUntilFailure', 'Slots Not Filled', 'Ask clarifying question'):
        return 'slots'
    return None


def phase_execution(steps: list[dict]) -> dict[str, list[dict]]:
    evidence = {p['id']: [] for p in PHASES}
    for record in steps:
        event = record['event']
        # The event is sourced from the actual chosen tree's node ID/name in the Runner.
        phase = phase_for_node(event.get('node_name', ''))
        if phase is not None: evidence[phase].append(event)
    return evidence


def preview_facts(tree: dict, access: dict) -> str:
    from sg_pipeline.convert import facts
    return facts(tree, access)


def lesson_dot(selected: str) -> str:
    """Illustrative educational process diagram; original tree remains in main view."""
    stages = [('input', 'Input check\\nVoice/Text'), ('normalize', 'Normalize\\nInput'),
              ('topic', 'Detect Topic\\nNaive Bayes'), ('intent', 'Detect Intent\\nLogistic Regression'),
              ('slots', 'Slot Filling\\nRepeat / Clarify')]
    result = ['digraph lesson {', 'graph [rankdir=LR,bgcolor="white",pad=0.35,nodesep=0.32,ranksep=0.60];',
              'node [shape=box,style="rounded,filled",fontname="Helvetica",fontsize=12,margin="0.16,0.12",color="#7096BB",fontcolor="#132941"];',
              'edge [color="#6E8BAA",penwidth=1.6,arrowsize=0.7];']
    for name, label in stages:
        fill = '#D4EAFD' if selected == name else '#F4F8FC'
        outline = '#1460A9' if selected == name else '#A9BECE'
        result.append(f'{name} [label="{label}",fillcolor="{fill}",color="{outline}",penwidth={2.5 if selected == name else 1}];')
    for a, b in zip(stages, stages[1:]):result.append(f'{a[0]} -> {b[0]};')
    result.extend(['slots -> slots [label="missing → ask → recheck",color="#B77B24",fontcolor="#8E5708",constraint=false];',
                   'slots -> next [label="all filled",color="#24815B",fontcolor="#24815B"];',
                   'next [label="Select Database\\nNEXT PHASE: NOT RUN",fillcolor="#F4F8FC",style="rounded,dashed",color="#A9BECE"];','}'])
    return '\n'.join(result)


def service_view_dot(view: dict, layer: str) -> str:
    """Separate readable control and Blackboard diagrams of the SAME static SG view."""
    if layer not in ('control', 'blackboard', 'possible'):
        raise ValueError('Unsupported SG presentation layer')
    q = lambda x: json.dumps(str(x))
    all_names = {s['id']: s['name'] for s in view['services']}
    all_names.update({g['id']: g['name'] for g in view['gateways']})
    lines = ['digraph sg {', 'graph [bgcolor="white",rankdir=LR,ranksep=0.55,nodesep=0.40,splines=polyline];',
             'node [shape=box,style="rounded,filled",fontname="Helvetica",fontsize=11,fontcolor="#14283D",color="#6E96B6"];',
             'edge [arrowsize=0.6,fontname="Helvetica",fontsize=9];']
    if layer == 'control':
        for nid, title in all_names.items():
            control = nid.startswith('gate:')
            lines.append(f'{q(nid)} [label={q(title)},fillcolor={q("#F2EAF8" if control else "#E7F2FB")},color={q("#9A79B8" if control else "#568BB6")}];')
        for e in view['conditional_flow']:
            back = e['guard'] == 'repeat_after_reply'
            lines.append(f'{q(e["source"])} -> {q(e["target"])} [label={q(e["guard"])},color={q("#C18A30" if back else "#497DA6")},fontcolor="#435C74",constraint={"false" if back else "true"}];')
    elif layer == 'blackboard':
        live_ids = {e['service'] for e in view['access']}
        for s in view['services']:
            if s['id'] in live_ids:
                lines.append(f'{q(s["id"])} [label={q(s["name"])},fillcolor="#E7F2FB"];')
        for key in view['blackboard_keys']:
            lines.append(f'{q("bb:" + key)} [label={q("Blackboard: " + key)},shape=ellipse,fillcolor="#FFF1BF",color="#AE9049"];')
        for e in view['access']:
            clr = '#17834F' if e['direction'] == 'writes' else '#A56C26'
            lines.append(f'{q(e["service"])} -> {q("bb:"+e["key"])} [label={q(e["direction"].upper())},color={q(clr)},constraint=false];')
    else:
        included = {e[x] for e in view['potential_service_data'] for x in ('source', 'target')}
        for s in view['services']:
            if s['id'] in included:
                lines.append(f'{q(s["id"])} [label={q(s["name"])},fillcolor="#E7F2FB"];')
        for e in view['potential_service_data']:
            lines.append(f'{q(e["source"])} -> {q(e["target"])} [label={q(e["key"])},color="#9F8451",style=dotted,constraint=false];')
    return '\n'.join(lines + ['}'])


def prolog_dot(selected: int) -> str:
    labels = ['JSON Tree', 'Python Facts', 'SWI-Prolog', 'Control / Data', 'Graph JSON', 'Python SG View', 'Neo4j (optional)']
    result = ['digraph convert {','graph [rankdir=LR,bgcolor="white",ranksep=0.36,nodesep=0.3];',
              'node [shape=box,style="rounded,filled",fontname="Helvetica",fontsize=11,margin="0.11,0.09",fontcolor="#172D44"];',
              'edge [color="#647D97",arrowsize=0.7];']
    for i, label in enumerate(labels):
        result.append(f'p{i} [label={json.dumps(label)},fillcolor={json.dumps("#D8EBFD" if i==selected else "#F1F5F9")},color={json.dumps("#155BA0" if i==selected else "#A4B4C4")},penwidth={2.3 if i==selected else 1}];')
        if i: result.append(f'p{i-1} -> p{i};')
    result.append('}')
    return '\n'.join(result)


def source_extract(src: str, prefix: str) -> str:
    """Show exact lines from the current converter.pl, not a rewritten 'equivalent'."""
    lines = src.splitlines()
    pos = next((i for i, line in enumerate(lines) if line.startswith(prefix)), None)
    if pos is None: return f'Predicate {prefix} not found in this converter.pl.'
    chosen = []
    for line in lines[pos:]:
        chosen.append(line)
        if line.rstrip().endswith('.'):
            break
    return '\n'.join(chosen)


def source_for_step(index: int, pl: str, generated: str) -> tuple[str, str]:
    if index == 0:
        import inspect
        from sg_pipeline.convert import load_tree, validate
        return 'Actual Python: sg_pipeline/convert.py', inspect.getsource(load_tree)+'\n'+inspect.getsource(validate)
    if index == 1: return 'Automatically generated *.facts.pl (excerpt)', '\n'.join(generated.splitlines()[:34])
    if index == 2:
        import inspect
        from sg_pipeline.convert import convert
        return 'Actual Python call: sg_pipeline/convert.py', inspect.getsource(convert)
    if index == 3:
        return 'Actual converter.pl predicates', '\n\n'.join(source_extract(pl, x) for x in ('control_edge(P,C,sequence_child', 'control_edge(P,C,fallback_child', 'child_order(A,B,sequence)', 'loop_dict(D)'))
    if index == 4: return 'Actual converter.pl rule', source_extract(pl, 'potential_data(W,R,K)')
    if index == 5: return 'Actual converter.pl rule', source_extract(pl, 'build_graph(Graph)')
    import inspect
    from sg_pipeline.service_view import project
    return 'Actual Python: sg_pipeline/service_view.py', inspect.getsource(project)


def render_lab(st, tree: dict, runner, root: Path) -> None:
    """Embed as an additive section in the existing single-page dashboard."""
    import sys
    if str(root) not in sys.path: sys.path.insert(0, str(root))
    from sg_pipeline.convert import convert as actual_convert
    from sg_pipeline.convert import load_tree
    from sg_pipeline.graphviz_view import dot as original_graph_dot
    from sg_pipeline.service_view import project

    st.markdown('<div class="section-heading">Learning Lab · actual algorithms + BT → Prolog → SG</div>', unsafe_allow_html=True)
    st.caption('Source-grounded English lessons. Blue = selected explanation. Example diagrams teach the method; the large tree above is the actual JSON.')
    learning, translating, code_tutorial = st.tabs(['Learn the Behavior Tree · through Slot Filling', 'Learn Prolog conversion · all steps', 'Prolog CODE explained · every rule'])
    with learning:
        stage = st.selectbox('Choose an actual BT stage', options=[x['id'] for x in PHASES],
                             format_func=lambda k: next(p['title'] for p in PHASES if p['id']==k),key='lab_stage')
        info = next(p for p in PHASES if p['id']==stage)
        st.graphviz_chart(lesson_dot(stage), use_container_width=True)
        st.subheader(info['title'])
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('**Which method does the code really use?**')
            st.write(info['method'])
            st.markdown('**Why use it here?**')
            st.write(info['why'])
        with c2:
            st.markdown('**Input**'); st.write(info['inputs'])
            st.markdown('**Blackboard access**')
            st.write(f"Reads: {info['reads']}")
            st.write(f"Writes: {info['writes']}")
            st.markdown('**Limitations you should mention in a presentation**')
            st.write(info['limitations'])
        st.markdown('**Flow in simple English**')
        st.code(info['node_flow'], language='text')
        matched = [{'Original JSON ID': nid, 'Actual JSON title': n['title'], 'Node name': n['name']}
                   for nid, n in tree['nodes'].items() if n['name'] in info['node_names']]
        if stage == 'topic':
            matched = [x for x in matched if x['Node name'] == 'ActionNaiveBayesTopicClassifier']
        st.dataframe(matched, use_container_width=True, hide_index=True)
        if runner is not None:
            live = [event for record in runner.steps for event in [record['event']]
                    if tree['nodes'][event['node_id']]['name'] in info['node_names']]
            st.markdown('**Observed events in the current text demo**')
            if live:
                st.dataframe([{'Step': e['step'], 'Node': e['node'], 'Status': e['status'], 'Reason':e['detail']}
                              for e in live],use_container_width=True,hide_index=True)
            else: st.info('This stage has not run yet, or is not supported by the text demo.')
            st.markdown('**Compact operational Blackboard (current state)**')
            st.json(runner.blackboard, expanded=True)
            if stage == 'normalize' and runner.runtime.get('normalization'):
                trace = runner.runtime['normalization']
                if isinstance(trace, dict):
                    rows = trace.get('stages') or trace.get('steps') or []
                    if rows: st.dataframe(rows,use_container_width=True,hide_index=True)
            if stage == 'topic' and runner.runtime.get('topic_scores'):
                st.write('Raw model scores from this small trained demo, NOT measured accuracy.')
                st.bar_chart(runner.runtime['topic_scores'])
            if stage == 'intent' and runner.runtime.get('intent_scores'):
                st.write('Model scores for the selected topic (not calibrated accuracy).')
                st.bar_chart(runner.runtime['intent_scores'])
        if stage == 'slots':
            st.markdown('**Every intent: its three required slots and exact clarification questions**')
            st.dataframe([{'Topic': topic, 'Intent': intent, 'Mandatory slot': key,
                           'Question': question, 'Answer example': SLOT_EXAMPLES.get(key,'')}
                          for topic, intents in SLOT_SPECS.items() for intent, slots in intents.items()
                          for key, question in slots.items()],use_container_width=True,hide_index=True)
            st.graphviz_chart('''digraph loop {graph [rankdir=LR,bgcolor="white"];
 node [shape=box,style="rounded,filled",fillcolor="#ECF5FD",fontcolor="#172D44"];
 check [label="Check required slots?"];
 ask [label="Ask missing slot\\nin main chat"];
 save [label="Validate + update\\nBlackboard.slots"];
 exit [label="All filled → EXIT",fillcolor="#DDF4E7"];
 check -> ask [label="YES: missing"];
 ask -> save [label="user reply"];
 save -> check [label="REPEAT",color="#C08325",fontcolor="#9A6219"];
 check -> exit [label="NO: complete",color="#2D9064",fontcolor="#2D9064"]; }''',use_container_width=True)
    with translating:
        st.info('This is the STATIC whole-tree conversion, including BOTH Music and Art. It does NOT select a sample question.')
        step = st.select_slider('Walk through the actual conversion',options=list(range(len(PROLOG_STEPS))),
                                value=0,format_func=lambda i: PROLOG_STEPS[i][0],key='prolog_walk')
        st.graphviz_chart(prolog_dot(step),use_container_width=True)
        heading, desc, _ = PROLOG_STEPS[step]
        st.subheader(heading);st.write(desc)
        access=json.loads((root/'sg_pipeline/access_map.json').read_text(encoding='utf8'))
        pl=(root/'sg_pipeline/converter.pl').read_text(encoding='utf8')
        generated=preview_facts(tree,access)
        source_title, source_code = source_for_step(step,pl,generated)
        st.markdown(f'**Actual source: {source_title}**')
        st.code(source_code,language='prolog' if step in (1,3,4,5) else 'python')
        with st.expander('Show FULL generated facts for this actual selected tree'):
            st.code(generated,language='prolog')
            st.download_button('Download generated Prolog facts',generated,file_name='bt_learning.facts.pl',mime='text/plain',key='facts_download')
        if step == 4:
            st.markdown('**Actual proposed reads/writes from access_map.json (not asserted by the source BT JSON)**')
            st.dataframe([{'Source node name': node, 'Reads': ', '.join(ops.get('reads',[])),
                           'Writes': ', '.join(ops.get('writes',[]))} for node,ops in access.items()
                          if ops.get('reads') or ops.get('writes')],hide_index=True,use_container_width=True)
        st.divider()
        st.subheader('Execute the real Prolog converter and inspect each graph layer')
        st.caption('No question needed. This button invokes the existing SWI-Prolog executable; it never guesses graph results.')
        if st.button('Run full tree → SWI-Prolog → static SG',key='lab_real_convert'):
            try:
                # Convert the JSON selected in the dashboard, including uploads.
                # The current selection is written to an isolated dashboard input file.
                selected_doc = {'selectedTree':tree['id'],'trees':[tree]}
                out_dir=root/'outputs';out_dir.mkdir(exist_ok=True)
                chosen_path=out_dir/'learning_lab_selected_tree.json'
                chosen_path.write_text(json.dumps(selected_doc,indent=2,ensure_ascii=False),encoding='utf8')
                actual=actual_convert(chosen_path,out_dir/'learning_lab_service_graph.json')
                st.session_state['learning_lab_graph']=actual
                # Link cached results to exact input to avoid rendering stale data.
                st.session_state['learning_lab_tree']=generated
                st.success('Real SWI-Prolog finished and node count was checked.')
            except Exception as exc: st.error(f'Conversion failed (no fabricated fallback): {exc}')
        graph=st.session_state.get('learning_lab_graph') if st.session_state.get('learning_lab_tree')==generated else None
        if graph is None:
            st.warning('No verified Prolog output for this tree in this session. Click Run above (requires swipl).')
        else:
            a,b,c,d=st.columns(4)
            a.metric('All original nodes',len(graph['nodes']))
            b.metric('Control edges',len(graph['control_edges']))
            c.metric('Sibling gates',len(graph['ordered_edges']))
            d.metric('Candidate data links',len(graph['potential_data_edges']))
            show_layer=st.selectbox('Inspect this Prolog-derived layer',
                                    ['BT control + gates','BT control only','Candidate Blackboard links (not guaranteed)','Loops'],key='learning_layer')
            if show_layer in ('BT control + gates','BT control only','Candidate Blackboard links (not guaranteed)'):
                # The existing renderer always includes ordered edges, so remove
                # them explicitly when the user chooses CONTROL ONLY.
                render_graph = dict(graph)
                if show_layer == 'BT control only': render_graph['ordered_edges'] = []
                st.caption('Solid = parent/child; dashed = sibling ordering; dotted green = possible data. The chosen filter controls which are visible.')
                st.graphviz_chart(original_graph_dot(render_graph,show_layer=='Candidate Blackboard links (not guaranteed)'),use_container_width=True)
            else:
                names={n['id']:n['label'] for n in graph['nodes']}
                loop=['digraph loops {', 'graph [bgcolor="white",rankdir=LR];',
                      'node [shape=box,style="rounded,filled",fillcolor="#E7F2FB",fontcolor="#14283D"];']
                for e in graph['loop_edges']:
                    source,target=e['source'],e['target']
                    loop.extend([f'{json.dumps(source)} [label={json.dumps(names[source])}];',
                                 f'{json.dumps(target)} [label={json.dumps(names[target])}];',
                                 f'{json.dumps(source)} -> {json.dumps(target)} [label="child SUCCESS → repeat",color="#B47D29"];'])
                loop.append('}')
                st.graphviz_chart('\n'.join(loop),use_container_width=True)
                st.json(graph['loop_edges'],expanded=True)
                st.caption('RepeatUntilFailure exits when its child fails. This is a static decorator annotation, NOT a cyclic service-placement dependency.')
            with st.expander('Exact results as returned by SWI-Prolog'):
                st.json(graph,expanded=False)
            st.download_button('Download Prolog graph JSON',json.dumps(graph,indent=2,ensure_ascii=False),
                               file_name='learning_lab_service_graph.json',mime='application/json',key='prolog_result_download')
            st.markdown('**The readable Service + Blackboard view (Python architectural projection)**')
            view=project(graph,tree,access)
            kind=st.radio('Choose ONE readable Service Graph layer',
                          ['Main conditional path', 'Service ↔ Blackboard contracts',
                           'Prolog candidate service links'],horizontal=True,key='lab_sg_layer')
            layer={'Main conditional path':'control',
                   'Service ↔ Blackboard contracts':'blackboard',
                   'Prolog candidate service links':'possible'}[kind]
            st.caption('The arrow for READS points from the SERVICE to the KEY in the saved Neo4j model. Interpret meaning by edge LABEL, not arrow direction.')
            st.graphviz_chart(service_view_dot(view,layer),use_container_width=True)
            if layer=='possible':
                st.warning('Candidate edges may cross exclusive branches. They are NOT a validated execution or placement DAG.')
            st.dataframe([{'Service':s['name'],'ID':s['id']} for s in view['services']],hide_index=True,use_container_width=True)
            st.dataframe([{'Action node':next(s['name'] for s in view['services'] if s['id']==x['service']),
                           'Access':x['direction'],'Blackboard key':x['key']} for x in view['access']],
                         hide_index=True,use_container_width=True)
            st.code("MATCH (a {graph_id:'dialogue-service-v1'})-"+
                    "[r:CONDITIONAL_FLOW|READS|WRITES]->"+
                    "(b {graph_id:'dialogue-service-v1'}) RETURN a,r,b;",language='cypher')
            st.caption('The Neo4j upload is intentionally NOT automatic. Use: python -m sg_pipeline.service_view --upload from a terminal with credentials.')

    with code_tutorial:
        from prolog_code_guide import render_prolog_code_guide
        access = json.loads((root/'sg_pipeline/access_map.json').read_text(encoding='utf8'))
        render_prolog_code_guide(st, root, tree, access)
