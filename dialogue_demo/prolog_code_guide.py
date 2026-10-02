"""Detailed, source-checked English walkthrough of this project's REAL Prolog rules.
Never substitute a claimed execution trace for a static proof of possible relations.
"""
from __future__ import annotations

import json
from pathlib import Path

# Every code excerpt is extracted from the installed converter.pl, never copied
# from these explanations. The walkthrough uses the actual selected tree's IDs.
RULES = [
    {
        'title': '01 · Prolog input declarations', 'prefix': ':- dynamic',
        'purpose': 'Tell SWI-Prolog that the input predicates can receive facts when a generated file is loaded.',
        'english': [
            'bt_node/3 means a node has three arguments: ID, type, and display label.',
            'bt_child/3 describes parent, child position, and child ID.',
            'bt_root/1 identifies the original root. access/3 declares a node, READ or WRITE, and a Blackboard key.',
            'These are declarations, NOT automatically discovered facts. Python supplies the facts from your JSON and access_map.json.'
        ],
        'example': 'bt_node(n8, action, "Normalize Input").  % shown conceptually; actual generated facts use quoted atoms',
        'result': 'Prolog knows which types of facts will describe your tree.',
        'nodes': [('JSON tree + access map','Python-generated facts','These declarations make the predicates available')]
    },
    {
        'title': '02 · Sequence child order', 'prefix': 'child_order(A,B,sequence)',
        'purpose': 'Find consecutive children belonging to the SAME Sequence parent.',
        'english': [
            'P is a Sequence node. bt_child(P,I,A) finds a child A at position I.',
            'J is I+1 calculates the NEXT index. In Prolog, is performs arithmetic; = does not.',
            'bt_child(P,J,B) succeeds only if child B exists at that next position.',
            'It discovers adjacency, not that B has actually executed.'
        ],
        'example': 'For the root Sequence, child 2 = Normalize Input and child 3 = Detect Topic. Prolog infers they are consecutive siblings.',
        'result': 'child_order(NormalizeID, DetectTopicID, sequence)',
        'nodes': [('Sequence P','Child A at I','Find next index'),('Child A at I','Child B at I+1','Ordered siblings')]
    },
    {
        'title': '03 · Fallback child order', 'prefix': 'child_order(A,B,fallback)',
        'purpose': 'Find consecutive branches of the same Fallback / Selector.',
        'english': [
            'This rule has the same adjacency pattern as Sequence, but looks only for a Fallback parent.',
            'For your modality Fallback, Voice Input is checked first, then Text Input if Voice fails.',
            'This rule does NOT perform speech recognition or decide the active input. It only describes static sibling order.'
        ],
        'example': 'Resolve Input Modality: Voice Input (position 0), Text Input (position 1).',
        'result': 'child_order(VoiceID, TextID, fallback)',
        'nodes': [('Fallback','Voice branch','Try first'),('Voice branch','Text branch','Next if previous fails')]
    },
    {
        'title': '04 · Preserve parent/child control edges', 'prefix': 'control_edge(P,C,sequence_child',
        'related': ['control_edge(P,C,fallback_child', 'control_edge(P,C,repeat_child', 'control_edge(P,C,contains'],
        'purpose': 'Keep the original tree structure, including its different composite/decorator types.',
        'english': [
            'The first rule matches every direct child C of a Sequence parent P.',
            'Related rules separately match Fallback, RepeatUntilFailure, and other composite nodes.',
            'The original child index I is retained, so no child order is lost.',
            'These are structural CONTROL_CHILD relations, NOT proven data dependencies.'
        ],
        'example': 'The root Sequence contains Normalize Input, Detect Topic, Detect Intent, Repeat, Select Database, etc.',
        'result': 'An edge with source=P, target=C, relation=sequence_child (or another composite type), index=I.',
        'nodes': [('Original BT parent P','Original BT child C','Preserve control tree')]
    },
    {
        'title': '05 · Infer potential Blackboard data links', 'prefix': 'potential_data(W,R,K)',
        'purpose': 'Find declared writer/reader pairs sharing EXACTLY the same Blackboard key.',
        'english': [
            'access(W,write,K) searches for any writer W that writes key K.',
            'access(R,read,K) searches for any reader R using that same K.',
            'W \\= R excludes links from a node back to itself.',
            'This is a candidate dependency. It does NOT check branch exclusivity, feasible runtime order, or whether the writer truly produced a value.'
        ],
        'example': 'Normalize Input writes normalized_input. Naive Bayes reads normalized_input. Therefore the pair is a candidate data edge.',
        'result': 'potential_data(NormalizeID, NaiveBayesID, normalized_input)',
        'nodes': [('Normalize Input','normalized_input','WRITES'),('normalized_input','Naive Bayes','READS / possible dependency')]
    },
    {
        'title': '06 · Turn ALL source BT nodes into JSON nodes', 'prefix': 'node_dict(D)',
        'purpose': 'Represent every source BT node (not just actions) in the static graph.',
        'english': [
            'bt_node(Id,Kind,Label) matches each declared BT node.',
            'D = _{...} creates a SWI-Prolog dictionary with the node ID, display label, and node type.',
            'The dictionary is later added to the nodes JSON array by findall.'
        ],
        'example': 'A Condition such as Slots Not Filled remains in the full control graph even though it is not an action service.',
        'result': '{"id":"...", "label":"Slots Not Filled", "kind":"condition"}',
        'nodes': [('bt_node/3 facts','node_dict/1','Create dictionary'),('node_dict/1','nodes[]','Retain all BT nodes')]
    },
    {
        'title': '07 · Select action nodes as candidate services', 'prefix': 'service_dict(D)',
        'purpose': 'Make a separate list containing ONLY source nodes classified as actions.',
        'english': [
            'bt_node(Id,action,Label) will not match Sequence, Fallback, Condition, or Repeat nodes.',
            'The resulting dictionary contains the source node ID and label.',
            'This list is a modeling input for a later service view. It does NOT prove every action is separately deployable.'
        ],
        'example': 'Normalize Input and Ask clarifying question are action nodes. Slot Filling Controller itself is not selected here.',
        'result': '{"id":"...", "label":"Normalize Input"}',
        'nodes': [('All BT nodes','action filter','Exclude conditions/decorators'),('action filter','service_nodes[]','Candidate services')]
    },
    {
        'title': '08 · Filter data links to action-to-action pairs', 'prefix': 'service_data_dict(D)',
        'purpose': 'Reuse potential_data/3, but include only pairs whose BOTH endpoints are actions.',
        'english': [
            'potential_data(W,R,K) first finds candidate writer/reader pairs.',
            'bt_node(W,action,_) keeps only a writer classified as an action.',
            'bt_node(R,action,_) keeps only a reader classified as an action.',
            'The output relation is called potential_service_data. The word potential still matters.'
        ],
        'example': 'Normalize Input → Naive Bayes qualifies because both are action nodes. A Condition reading topic is excluded from this ACTION-ONLY list.',
        'result': '{"source":"writer-id", "target":"reader-id", "key":"normalized_input", "relation":"potential_service_data"}',
        'nodes': [('potential_data/3','Action-node filter','Both endpoints are actions'),('Action-node filter','service_data_edges[]','Retain key label')]
    },
    {
        'title': '09 · Serialize parent/child edges', 'prefix': 'control_dict(D)',
        'purpose': 'Turn every structural control_edge/4 solution into a JSON dictionary.',
        'english': [
            'control_edge(P,C,Relation,I) tries the previously defined composite-specific rules.',
            'The JSON dictionary records parent source, child target, relation, original position and control layer.',
            'This is the full BT control layer, not the simplified Neo4j CONDITIONAL_FLOW presentation.'
        ],
        'example': 'If a parent is a Sequence, its children receive a sequence_child control relation.',
        'result': 'One entry per original BT parent/child relationship in control_edges[].',
        'nodes': [('control_edge/4','control_dict/1','Add ID + relation + index'),('control_dict/1','control_edges[]','Preserve tree structure')]
    },
    {
        'title': '10 · Convert sibling order into success/failure gates', 'prefix': 'gate_dict(D)',
        'purpose': 'Describe WHEN the next sibling is eligible to run.',
        'english': [
            'child_order(A,B,Kind) returns a pair of consecutive siblings.',
            'Kind=sequence -> Gate=previous_success: in a Sequence, success is needed before trying the next sibling.',
            'Otherwise, Gate=previous_failure: for this rule the other Kind is fallback, which tries the next branch after failure.',
            'These are static eligibility annotations, not a runtime executor.'
        ],
        'example': 'Normalize Input → Detect Topic needs previous_success. Voice Input → Text Input needs previous_failure.',
        'result': 'An ordered_edges[] entry with a gate label: previous_success or previous_failure.',
        'nodes': [('Adjacent siblings','Check composite kind','Sequence or Fallback'),('Check composite kind','Gate annotation','Success or failure')]
    },
    {
        'title': '11 · Serialize all candidate data dependencies', 'prefix': 'data_dict(D)',
        'purpose': 'Store every declared writer/reader candidate link, including links involving conditions.',
        'english': [
            'Unlike service_data_dict, this rule does not filter to action-only endpoints.',
            'potential_data(W,R,K) searches all declared read/write contracts.',
            'The result includes writer ID, reader ID, key, and the data layer.',
            'Independent candidate pairs can exist between mutually exclusive Music and Art branches; do not treat this as a validated execution DAG.'
        ],
        'example': 'The topic written by Naive Bayes is read by multiple later actions and topic conditions.',
        'result': 'An entry in potential_data_edges[] for each candidate pair.',
        'nodes': [('potential_data/3','data_dict/1','All matching endpoints'),('data_dict/1','potential_data_edges[]','Not path-validated')]
    },
    {
        'title': '12 · Annotate the Slot Filling Repeat loop', 'prefix': 'loop_dict(D)',
        'purpose': 'Represent the original RepeatUntilFailure decorator without pretending the SG itself executes the loop.',
        'english': [
            'bt_node(P,repeat_until_failure,_) finds the Repeat decorator.',
            'bt_child(P,_,C) identifies its decorated child, Slot Filling.',
            'When the child returns SUCCESS, this decorator can repeat the child.',
            'When the child returns FAILURE, this decorator exits the loop. This is a static annotation of the source behavior.'
        ],
        'example': 'Slot Filling: if required slots are still missing, ask and repeat; when they are complete, exit the loop (subject to actual BT return statuses).',
        'result': 'loop_edges[] with repeat_on_child_success and exit_gate=child_failure.',
        'nodes': [('Repeat Until Failure','Slot Filling child','RUN'),('Slot Filling child','Repeat Until Failure','SUCCESS: loop back'),('Slot Filling child','Exit decorator','FAILURE: stop')]
    },
    {
        'title': '13 · Collect EVERY inferred answer', 'prefix': 'build_graph(Graph)',
        'purpose': 'Build one dictionary with the complete static graph by collecting all solutions.',
        'english': [
            'findall(D,node_dict(D),Nodes) gathers every node_dict solution into one list.',
            'Further findall calls gather service nodes, data links, control edges, sibling gates, and loop annotations.',
            'root_dict(Root) preserves the root ID.',
            'Graph=_{...} assembles the output fields and explicitly sets mode=static_possible.',
            'Prolog never replaces the source BT with one selected Music/Art execution path.'
        ],
        'example': 'The output still includes BOTH Music and Art branches and the input/slot conditions.',
        'result': 'Graph dictionary, later serialized as outputs/service_graph.json.',
        'nodes': [('node_dict etc.','findall/3','Collect all matching results'),('findall/3','Graph dictionary','Full static graph')]
    },
    {
        'title': '14 · Load generated facts and write JSON', 'prefix': 'main :-',
        'purpose': 'Execute the full Prolog conversion when Python launches SWI-Prolog.',
        'english': [
            'current_prolog_flag(argv,[Facts,Output|_]) reads the input facts path and output JSON path passed by Python.',
            'consult(Facts) loads all automatically generated bt_root, bt_node, bt_child and access facts.',
            'build_graph(G) executes the collection rules.',
            'setup_call_cleanup opens the output, writes UTF-8 JSON, then ALWAYS closes the file.',
            'halt(0) exits successfully. On conversion error, Python raises an exception; do not fabricate a graph.'
        ],
        'example': 'Python launches swipl -q -s sg_pipeline/converter.pl -- outputs/service_graph.facts.pl outputs/service_graph.json',
        'result': 'A real SWI-Prolog-generated JSON file on disk.',
        'nodes': [('Python subprocess','consult(Facts)','Load input'),('consult(Facts)','build_graph(G)','Infer all layers'),('build_graph(G)','JSON file','Write output')]
    },
]


def exact_source(text: str, start: str) -> str:
    lines = text.splitlines()
    pos = next((i for i, line in enumerate(lines) if line.startswith(start)), None)
    if pos is None:
        return f'Rule {start!r} is not present in the currently installed converter.pl.'
    out = []
    for ln in lines[pos:]:
        out.append(ln)
        if ln.rstrip().endswith('.'):
            break
    return '\n'.join(out)


def rule_dot(rule: dict) -> str:
    lines = ['digraph guide {','graph [rankdir=LR,bgcolor="white",splines=true,nodesep=0.45,ranksep=0.55];',
             'node [shape=box,style="rounded,filled",fillcolor="#E7F2FB",color="#6F9ABE",fontcolor="#142D46",fontname="Helvetica"];',
             'edge [color="#4383B1",fontname="Helvetica",fontsize=10];']
    for idx, (source,target,label) in enumerate(rule['nodes']):
        sid='s'+str(idx); tid='t'+str(idx)
        lines.append(f'{sid} [label={json.dumps(source)}];')
        lines.append(f'{tid} [label={json.dumps(target)}];')
        lines.append(f'{sid} -> {tid} [label={json.dumps(label)}];')
    lines.append('}')
    return '\n'.join(lines)


def render_prolog_code_guide(st, root: Path, tree: dict, access: dict) -> None:
    pl=(root/'sg_pipeline/converter.pl').read_text(encoding='utf8')
    st.info('These are the REAL rules from your installed converter.pl. The diagrams explain the rules; they are not runtime traces.')
    title=st.selectbox('Select a Prolog rule and study it line by line',
                       [r['title'] for r in RULES], key='lab_detailed_prolog_rule')
    rule=next(r for r in RULES if r['title']==title)
    st.subheader(rule['title'])
    st.markdown('**WHY do we have this rule?**')
    st.write(rule['purpose'])
    st.markdown('**Exact code from YOUR converter.pl:**')
    st.code(exact_source(pl, rule['prefix']),language='prolog')
    if rule.get('related'):
        with st.expander('Related rules in the same file'):
            for prefix in rule['related']:
                st.code(exact_source(pl,prefix),language='prolog')
    st.markdown('**LINE-BY-LINE EXPLANATION · Simple English**')
    for i, line in enumerate(rule['english'],1):
        st.markdown(f'**{i}.** {line}')
    st.markdown('**How this rule fits YOUR tree**')
    st.write(rule['example'])
    st.graphviz_chart(rule_dot(rule),use_container_width=True)
    st.markdown('**What does it produce?**')
    st.code(rule['result'],language='text')
    if rule['prefix']=='potential_data(W,R,K)':
        from sg_pipeline.convert import facts
        generated=facts(tree,access)
        lines=generated.splitlines()
        def match_named(label: str) -> str | None:
            import re
            for line in lines:
                m=re.search(r"^bt_node\('([^']+)',action,'([^']+)'\)\.$",line)
                if m and m.group(2)==label:return m.group(1)
            return None
        writer=match_named('Normalize Input');reader=match_named('Naive Bayes Topic Classifier')
        if writer and reader:
            st.markdown('**A grounded example from the EXACT selected tree facts:**')
            for snippet in (f"access('{writer}',write,'normalized_input').",f"access('{reader}',read,'normalized_input').",
                            f"potential_data('{writer}','{reader}','normalized_input')."):
                st.code(snippet,language='prolog')
            st.caption('The third line is an example of the rule answer; it is not a saved input fact or an observed execution.')
    st.warning('Remember: Prolog infers the full static BT and POTENTIAL data relations. The Python service_view.py later adds a human-designed CONDITIONAL_FLOW architecture for Neo4j. They are not identical.')
