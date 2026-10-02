"""Inspectable text-only BT prefix. Original repository code is deliberately unchanged.
The JSON is the source of truth for ordering and node IDs; only the path ending at
DetectInetent is executable in this milestone. No Neo4j/LLM calls occur here.
"""
from __future__ import annotations
import copy
import json
import re
import unicodedata
from slots import SLOT_SPECS, extract_slots, missing_slots, slot_question, validate_slot, parse_clarification, SLOT_LABELS, SLOT_EXAMPLES
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from functools import lru_cache
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression

TOPIC_EXAMPLES = {
    'music': [
        'who sings bohemian rhapsody', 'who is the singer of hello', 'who performed shape of you',
        'who is the artist behind imagine', 'which band released yellow', 'tell me about jazz music',
        'what is the genre of smells like teen spirit', 'which album includes bad romance',
        'when was thriller released', 'what year did abbey road come out',
        'who composed the four seasons', 'who is the musician behind this song',
        'find the release date of the single', 'what genre is this album',
        'who is the vocalist on this track', 'which record features this song',
        'identify the singer of yesterday', 'find the album containing halo',
        'what year was despacito released', 'what music style is take five',
    ],
    'art': [
        'who painted the starry night', 'who created the mona lisa', 'who is the painter of guernica',
        'who sculpted david', 'tell me about renaissance painting',
        'what art movement is the persistence of memory', 'where is the last supper displayed',
        'which museum houses the scream', 'what year was the kiss painted',
        'when was girl with a pearl earring created', 'who is the creator of this artwork',
        'what artistic style is impressionism', 'where is this sculpture kept',
        'identify the artist of the birth of venus', 'which museum has the night watch',
        'which movement does this painting belong to', 'what year was this artwork made',
        'find the location of this painting', 'who made this sculpture',
        'who painted the water lilies',
    ],
}
INTENT_EXAMPLES = {
 'music': {
  'artist': ['who sings {e}','who sang {e}','who is the singer of {e}','who performed {e}', 'who composed {e}', 'who is the artist of {e}'],
  'release_year': ['when was {e} released','what year did {e} come out','what is the release date of {e}','when did {e} come out'],
  'album': ['which album includes {e}', 'what album is {e} on', 'which record contains {e}', 'name the album featuring {e}'],
  'genre': ['what genre is {e}','what is the musical style of {e}', 'which kind of music is {e}', 'what music genre does {e} belong to'],
 },
 'art': {
  'creator': ['who painted {e}','who created {e}', 'who made {e}', 'who sculpted {e}', 'who is the artist behind {e}'],
  'creation_year': ['when was {e} painted','what year was {e} created','when was {e} made','what is the creation date of {e}'],
  'movement': ['what art movement is {e}','what artistic style is {e}','which movement does {e} belong to','is {e} impressionist or surrealist'],
  'location': ['where is {e} displayed','which museum houses {e}','where can i see {e}','what museum keeps {e}'],
 }
}
ENTITIES = {'music':['bohemian rhapsody','hello','thriller','yesterday','shape of you','imagine'], 'art':['the starry night','guernica','mona lisa','the scream','david','the kiss']}


def tokenize(text: str) -> list[str]:
    """Space-delimited Unicode alphanumeric tokens; keep title digits intact."""
    return [part for part in re.split(r'\s+', text.strip(' ?')) if part]


def normalization_pipeline(text: str) -> list[dict]:
    """Preserve ALL Unicode letters and digits, remove other symbols as separators.

    Exactly one question mark is appended to nonempty text. No guessing of
    spelling, grammar, or whether an alphanumeric string is a title.
    """
    value = text
    stages = []

    def apply(operation: str, reason: str, fn):
        nonlocal value
        after = fn(value)
        stages.append(dict(operation=operation, reason=reason,
                           before=value, after=after, changed=after != value))
        value = after

    apply('Unicode NFC', 'Standardize equivalent Unicode characters without dropping letters or digits.',
          lambda t: unicodedata.normalize('NFC', t))
    apply('Remove extra symbols',
          'Preserve letters and numbers in every language. Replace all punctuation/symbols with spaces so neighboring words never merge.',
          lambda t: ''.join(c if c.isalnum() else ' ' for c in t))
    apply('Collapse whitespace', 'Combine consecutive spaces and trim both ends.',
          lambda t: ' '.join(t.split()))
    apply('Exactly one question mark', 'End nonempty text with one English question mark; remove all others.',
          lambda t: t + '?' if t else t)
    stages.append(dict(operation='Tokenization (diagnostic)',
                       reason='Display every retained letter/number token.', before=value,
                       after=value, changed=False, tokens=tokenize(value)))
    stages.append(dict(operation='Classifier casefold (separate view)',
                       reason='Casefold for the models without changing the human-readable version.',
                       before=value, after=value.casefold(), changed=value != value.casefold()))
    return stages


def normalize(text: str) -> str:
    return normalization_pipeline(text)[-1]['after']


@lru_cache(maxsize=1)
def models():
    topic = make_pipeline(TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True), MultinomialNB(alpha=0.6))
    xt = []; yt = []
    for label, phrases in TOPIC_EXAMPLES.items():
        xt.extend(normalize(x) for x in phrases); yt.extend([label]*len(phrases))
    # Supplement topic training with distinct intent utterances; labels remain separate.
    for topic_name, intents in INTENT_EXAMPLES.items():
        for templates in intents.values():
            for template in templates:
                for ent in ENTITIES[topic_name]:
                    xt.append(normalize(template.format(e=ent))); yt.append(topic_name)
    topic.fit(xt, yt)
    intent_models = {}
    for topic_name, intents in INTENT_EXAMPLES.items():
        x=[]; y=[]
        for intent, templates in intents.items():
            for template in templates:
                for ent in ENTITIES[topic_name]:
                    x.append(normalize(template.format(e=ent))); y.append(intent)
        model=make_pipeline(TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True), LogisticRegression(max_iter=1500, class_weight='balanced'))
        model.fit(x,y); intent_models[topic_name]=model
    return topic, intent_models


def classify(model, text):
    prob = model.predict_proba([text])[0]
    labels = model.classes_
    ranked = sorted(zip(labels, (float(x) for x in prob)), key=lambda p:-p[1])
    return ranked[0][0], round(ranked[0][1], 4), {k:round(v,4) for k,v in ranked}


INTENT_DESCRIPTIONS = {
    'music': {
        'artist': ('Performer / singer', 'Who sings or performs a song?', 'who sings bohemian rhapsody'),
        'release_year': ('Release date / year', 'When was a song or album released?', 'when was thriller released'),
        'album': ('Containing album', 'Which album includes a song?', 'which album includes yesterday'),
        'genre': ('Music genre', 'What genre or music style is it?', 'what genre is imagine'),
    },
    'art': {
        'creator': ('Artwork creator', 'Who painted or created an artwork?', 'who painted the starry night'),
        'creation_year': ('Creation year', 'When was the artwork made?', 'when was mona lisa painted'),
        'movement': ('Art movement', 'Which movement or style does it belong to?', 'what art movement is guernica'),
        'location': ('Museum / location', 'Where is the artwork displayed?', 'which museum houses mona lisa'),
    },
}


def intent_diagnostics(topic: str, normalized_text: str) -> dict:
    """Exact linear-model trace: TF-IDF input, per-class logit and weighted features.

    Terms explain this trained classifier only, NOT verified linguistic reasons.
    Probabilities are uncalibrated model scores, not measured accuracy.
    """
    if topic not in INTENT_EXAMPLES:
        raise ValueError(f'Unsupported topic for intent: {topic}')
    _, intent_models = models()
    pipe = intent_models[topic]
    vec = pipe.named_steps['tfidfvectorizer']
    clf = pipe.named_steps['logisticregression']
    X = vec.transform([normalized_text]); features = vec.get_feature_names_out()
    classes = list(clf.classes_)
    # All current tasks have four classes; this assertion prevents silently
    # reporting wrong coefficients for binary classifier conventions.
    if len(classes) < 3:
        raise ValueError('This explanation currently requires >=3 intent classes.')
    probabilities = clf.predict_proba(X)[0]
    logits = clf.decision_function(X)[0]
    active = X.nonzero()[1].tolist()
    vocabulary = [{'term':str(features[j]),'tfidf':round(float(X[0,j]),6)} for j in active]
    vocabulary.sort(key=lambda x:(-x['tfidf'],x['term']))
    results=[]
    for i,label in enumerate(classes):
        weighted=[{'term':str(features[j]), 'tfidf':round(float(X[0,j]),6),
                   'coefficient':round(float(clf.coef_[i,j]),6),
                   'contribution':round(float(X[0,j]*clf.coef_[i,j]),6)} for j in active]
        weighted.sort(key=lambda x:(-x['contribution'],x['term']))
        results.append({'intent':str(label), 'description':INTENT_DESCRIPTIONS[topic][label][1],
                        'model_score':round(float(probabilities[i]),6),
                        'intercept':round(float(clf.intercept_[i]),6),
                        'linear_logit':round(float(logits[i]),6),
                        'positive_features':[v for v in weighted if v['contribution']>0],
                        'negative_features':[v for v in sorted(weighted,key=lambda x:x['contribution']) if v['contribution']<0]})
    results.sort(key=lambda x:-x['model_score'])
    return {'input_text':normalized_text,'topic_from_blackboard':topic,
            'selected_model':f'{topic} / TF-IDF 1–2 grams + Logistic Regression',
            'decision_rule':'Highest softmax model score among intents of the chosen topic',
            'scores_calibrated':False, 'recognized_features':vocabulary,
            'unknown_token_note':'Only word unigrams/bigrams in the fitted vocabulary contribute. OOV terms contribute zero.',
            'ranking':results, 'chosen_intent':results[0]['intent'],
            'training_templates':{key:list(value) for key,value in INTENT_EXAMPLES[topic].items()}}


def load_tree(path: Path):
    data=json.loads(path.read_text(encoding='utf-8'))
    selected=data.get('selectedTree'); trees=data['trees']; tree=next((t for t in trees if t.get('id')==selected),trees[0])
    nodes=tree['nodes']; root=tree['root']; assert root in nodes
    for node in nodes.values():
        for c in node.get('children', [])+([node['child']] if 'child' in node else []):
            if c not in nodes: raise ValueError(f'Missing child {c}')
    return tree


def prefix_path(tree):
    """Find actual nodes by name on the JSON tree, not hardcoded ID positions."""
    nodes=tree['nodes']; root=nodes[tree['root']]
    names=['ConditionNewInputAvailable','Fallback','ActionNormalizeInput','ActionNaiveBayesTopicClassifier','Detect Intern']
    # Prefix is supported only for this exact meaningful root ordering.
    children=[nodes[k] for k in root['children']]
    assert [children[i]['name'] for i in [0,1,2,3,4]] == ['ConditionNewInputAvailable','Fallback','ActionNormalizeInput','Sequence','Detect Intern']
    modality=children[1]; text_branch=nodes[modality['children'][1]]
    topic_seq=children[3]; topic_leaf=nodes[topic_seq['children'][0]]
    assert nodes[text_branch['children'][0]]['name']=='ConditionIsText'
    assert topic_leaf['name']==names[3]
    voice_branch=nodes[modality['children'][0]]
    assert nodes[voice_branch['children'][0]]['name']=='ConditionIsVoice'
    return [root,children[0],modality,voice_branch,nodes[voice_branch['children'][0]],text_branch,nodes[text_branch['children'][0]],children[2],topic_seq,topic_leaf,children[4]]

@dataclass
class Runner:
    tree: dict
    raw_input: str
    steps: list = field(default_factory=list)
    runtime: dict = field(default_factory=dict)
    cursor: int = 0
    error: str = ''

    def __post_init__(self):
        self.path = prefix_path(self.tree)
        self.runtime = {
            'request': {'modality': 'text', 'raw_input': self.raw_input,
                        'received': bool(self.raw_input.strip())},
            'modality': {'voice_checked': False, 'voice_result': 'NOT_VISITED',
                         'text_checked': False, 'text_result': 'NOT_VISITED', 'selected': None},
            'normalization': {'original': self.raw_input, 'steps': [],
                              'normalized': None, 'display_text': None, 'tokens': [], 'changed': None, 'corrections': [], 'token_details': []},
            'classification': {'topic': None, 'topic_scores': {}, 'intent': None,
                               'intent_scores': {}, 'intent_explanation': None, 'active_agent': None,
                               'scores_are_calibrated': False},
            # Flat interface retained for subsequent Neo4j implementation.
            'input_modality': 'text', 'raw_input': self.raw_input, 'normalized_input': None, 'normalization_mode': 'letters-and-numbers',
            'topic': None, 'topic_confidence': None, 'topic_scores': {},
            'intent': None, 'intent_confidence': None, 'intent_scores': {}, 'intent_explanation': None,
            'active_agent': None, 'slots': {}, 'required_slots': {}, 'slot_history': [], 'clarification_replies': [], 'slot_state':'NOT_STARTED', 'slot_iteration':0, 'missing_slots':[], 'clarifying_question':None, 'event_log': []
        }

    @property
    def blackboard(self) -> dict:
        """Operational BT blackboard only. Diagnostic data lives separately in runtime and steps."""
        return {
            'normalized_input': self.runtime['normalized_input'],
            'topic': self.runtime['topic'],
            'intent': self.runtime['intent'],
            'slots': copy.deepcopy(self.runtime['slots']),
        }

    def next(self):
        if self.cursor >= len(self.path) or self.error: return False
        node = self.path[self.cursor]
        name, title = node['name'], node['title']
        status, detail = 'SUCCESS', ''
        before = copy.deepcopy(self.runtime)
        try:
            if node['id'] == self.tree['root']:
                status = 'RUNNING'
                detail = 'Root Sequence starts; children execute in the original JSON order.'
            elif name == 'ConditionNewInputAvailable':
                if not self.raw_input.strip():
                    raise ValueError('Text input is empty. Enter a question.')
                detail = 'A non-empty user message was received.'
            elif title == 'Resolve Input Modality':
                status = 'RUNNING'
                detail = 'Fallback evaluates Voice Input first; on FAILURE tries Text Input.'
            elif title == 'Voice Input':
                status = 'RUNNING'
                detail = 'Enter Voice Sequence. Next, evaluate Is Voice?'
            elif name == 'ConditionIsVoice':
                status = 'FAILURE'
                self.runtime['modality'].update(voice_checked=True,voice_result='FAILURE')
                detail = 'Input is TEXT, not VOICE: FAILURE; Voice Sequence also fails; Fallback proceeds to Text.'
            elif title == 'Text Input':
                status = 'RUNNING'
                detail = 'Try the second Fallback branch: Text Input Sequence.'
            elif name == 'ConditionIsText':
                self.runtime['modality'].update(text_checked=True, text_result='SUCCESS',selected='text')
                detail = 'Input is TEXT: SUCCESS. Text Sequence and Resolve Input Modality Fallback succeed.'
            elif name == 'ActionNormalizeInput':
                pipeline = normalization_pipeline(self.raw_input)
                clean = pipeline[-1]['after']
                if not clean: raise ValueError('No usable text after normalization.')
                self.runtime['normalization'].update(original=self.raw_input,
                    steps=pipeline,normalized=clean,display_text=pipeline[-2]['after'],tokens=pipeline[-2]['tokens'],token_details=[{'position':i+1,'token':t,'casefolded':t.casefold()} for i,t in enumerate(pipeline[-2]['tokens'])],corrections=[],changed=clean != self.raw_input)
                self.runtime['normalized_input'] = clean
                detail = f'Normalize Input: {sum(x["changed"] for x in pipeline)} of {len(pipeline)} transformations changed the text. Before: {self.raw_input!r}; After: {clean!r}'
            elif title == 'Detect Topic':
                status = 'RUNNING'
                detail = 'Topic Sequence starts; classifier reads normalized_input from Blackboard.'
            elif name == 'ActionNaiveBayesTopicClassifier':
                m, _ = models()
                label, score, scores = classify(m,self.runtime['normalized_input'])
                self.runtime.update(topic=label,topic_confidence=score,topic_scores=scores)
                self.runtime['classification'].update(topic=label,topic_scores=scores)
                detail = f'Naive Bayes chose {label} with raw model score {score:.1%} (not calibrated confidence).'
            elif name == 'Detect Intern':
                topic = self.runtime['topic']
                _, intent_models = models()
                explanation = intent_diagnostics(topic, self.runtime['normalized_input'])
                label, score, scores = classify(intent_models[topic],self.runtime['normalized_input'])
                assert label == explanation['chosen_intent']
                self.runtime.update(intent=label,intent_confidence=score,intent_scores=scores,
                                       intent_explanation=explanation,active_agent=topic)
                self.runtime['classification'].update(intent=label,intent_scores=scores,
                                                        intent_explanation=explanation,active_agent=topic)
                detail = (f'Blackboard topic={topic!r} selected the {topic} model. '
                          f'TF-IDF produced {len(explanation["recognized_features"])} recognized features; '
                          f'the highest uncalibrated model score selected intent={label!r} ({score:.1%}). '
                          'See the Detect Intent analysis panel for per-intent evidence.')
            else:
                status = 'RUNNING'; detail = 'Traverse composite.'
        except Exception as exc:
            status = 'FAILURE'; detail = str(exc); self.error = detail
        # Record implied composite transitions from real selector/sequence semantics.
        effects = []
        if name == 'ConditionIsVoice' and status == 'FAILURE':
            effects = [{'node_id': self.path[3]['id'], 'status': 'FAILURE', 'reason':'Voice Sequence child failed'}]
        if name == 'ConditionIsText' and status == 'SUCCESS':
            effects = [{'node_id':self.path[5]['id'],'status':'SUCCESS','reason':'Text Sequence succeeded'},
                       {'node_id':self.path[2]['id'],'status':'SUCCESS','reason':'Fallback selected Text'}]
        if name == 'ActionNaiveBayesTopicClassifier' and status == 'SUCCESS':
            effects = [{'node_id':self.path[8]['id'],'status':'SUCCESS','reason':'Detect Topic Sequence succeeded'}]
        if name == 'Detect Intern' and status == 'SUCCESS':
            effects = [{'node_id':self.path[0]['id'],'status':'RUNNING','reason':'The demonstrated prefix finished; remaining original tree nodes are unexecuted'}]
        delta = {key:copy.deepcopy(value) for key,value in self.runtime.items()
                 if key != 'event_log' and value != before.get(key)}
        event = {'step':self.cursor+1, 'node_id':node['id'], 'node':title,
                 'status':status, 'detail':detail, 'effects':effects, 'blackboard_delta':delta}
        self.runtime['event_log'].append(copy.deepcopy(event))
        self.steps.append({'event':event,'blackboard':copy.deepcopy(self.runtime),'working_blackboard':self.blackboard})
        self.cursor += 1
        if name == 'Detect Intern' and status == 'SUCCESS':
            self.begin_slots()
        return True

    def _slot_event(self, node_id: str, status: str, detail: str, changes: dict | None = None):
        node=self.tree['nodes'][node_id]
        event={'step':len(self.steps)+1,'node_id':node_id,'node':node['title'],
               'status':status,'detail':detail,'effects':[], 'blackboard_delta':changes or {}}
        self.runtime['event_log'].append(copy.deepcopy(event))
        self.steps.append({'event':event,'blackboard':copy.deepcopy(self.runtime),'working_blackboard':self.blackboard})

    def begin_slots(self):
        if self.runtime.get('slot_state') not in ('NOT_STARTED',): return
        topic=self.runtime['topic']; intent=self.runtime['intent']
        if not topic or not intent: return
        self.runtime['slot_state']='RUNNING'
        self.runtime['slot_iteration']=1
        self.runtime['slots']=extract_slots(topic,intent,self.runtime['normalization']['display_text'])
        self.runtime['required_slots']={key:{'question':q,'value':self.runtime['slots'].get(key),'status':'FILLED' if self.runtime['slots'].get(key) else 'MISSING'} for key,q in SLOT_SPECS[topic][intent].items()}
        self.runtime['slot_history'].append({'source':'initial_question','slots':copy.deepcopy(self.runtime['slots'])})
        self._slot_event('c9c27d46-fadc-4ef0-8829-88430f6599a6','RUNNING','Enter the slot filling decorator. Waiting for all mandatory slots.',{'slots':copy.deepcopy(self.runtime['slots']),'slot_state':'RUNNING','required_slots':copy.deepcopy(self.runtime['required_slots'])})
        self.evaluate_slots()

    def evaluate_slots(self):
        missing=missing_slots(self.runtime['topic'],self.runtime['intent'],self.runtime['slots'])
        for key,record in self.runtime['required_slots'].items():
            record['value']=self.runtime['slots'].get(key)
            record['status']='FILLED' if record['value'] else 'MISSING'
        check_id='902d98f0-a3ec-48ff-bf88-9dd365f78b7c'
        if missing:
            self.runtime['slot_state']='WAITING_USER'
            self.runtime['missing_slots']=missing
            self.runtime['clarifying_question']=slot_question(self.runtime['topic'],self.runtime['intent'],missing[0])
            self._slot_event(check_id,'SUCCESS','Mandatory slots missing: '+', '.join(missing), {'missing_slots':missing,'slot_state':'WAITING_USER','required_slots':copy.deepcopy(self.runtime['required_slots'])})
            self._slot_event('00cc8681-30d6-43df-8e3a-dd33f55d67dd','RUNNING',self.runtime['clarifying_question'], {'clarifying_question':self.runtime['clarifying_question']})
        else:
            self.runtime['slot_state']='COMPLETE';self.runtime['missing_slots']=[];self.runtime['clarifying_question']=None
            # "Slots Not Filled?" returns FAILURE, terminating RepeatUntilFailure.
            self._slot_event(check_id,'FAILURE','All required slots are present; no more clarification needed.',{'slot_state':'COMPLETE','missing_slots':[],'required_slots':copy.deepcopy(self.runtime['required_slots'])})
            self._slot_event('c9c27d46-fadc-4ef0-8829-88430f6599a6','SUCCESS','EXITS clarification loop: all required slots filled.',{'slot_state':'COMPLETE'})

    def answer_slot(self, value: str):
        if self.runtime.get('slot_state') != 'WAITING_USER':
            raise ValueError('No outstanding slot question.')
        topic=self.runtime['topic']; intent=self.runtime['intent']
        missing=self.runtime['missing_slots'][:]
        updates,rejected,mode=parse_clarification(topic,intent,value,missing)
        # An invalid/empty response is still an auditable event. Never advance.
        self.runtime.setdefault('clarification_replies',[]).append(
            {'round':self.runtime['slot_iteration'],'raw_reply':value,'mode':mode,
             'accepted':copy.deepcopy(updates),'rejected':rejected})
        if not updates:
            self._slot_event('00cc8681-30d6-43df-8e3a-dd33f55d67dd','RUNNING',
                'No valid missing slot supplied. Same clarification is still pending.',
                {'clarification_replies':copy.deepcopy(self.runtime['clarification_replies'])})
            raise ValueError('Use the current slot answer or the labeled example below. Your answer was preserved.')
        for slot,good in updates.items():
            self.runtime['slots'][slot]=good
            self.runtime['required_slots'][slot].update(value=good,status='FILLED')
            self.runtime['slot_history'].append({'source':'clarification','slot':slot,'value':good,
                                                     'iteration':self.runtime['slot_iteration'],
                                                     'reply_mode':mode})
        self._slot_event('00cc8681-30d6-43df-8e3a-dd33f55d67dd','SUCCESS',
            f'Accepted {len(updates)} slot(s): '+', '.join(f'{k}={v}' for k,v in updates.items()),
            {'slots':copy.deepcopy(self.runtime['slots']),
             'slot_history':copy.deepcopy(self.runtime['slot_history']),
             'clarification_replies':copy.deepcopy(self.runtime['clarification_replies']),
             'required_slots':copy.deepcopy(self.runtime['required_slots'])})
        self.runtime['slot_iteration']+=1
        self._slot_event('c9c27d46-fadc-4ef0-8829-88430f6599a6','RUNNING',
            f'LOOP BACK: accepted {len(updates)} slots; recheck remaining slots on iteration {self.runtime["slot_iteration"]}.',
            {'slot_iteration':self.runtime['slot_iteration']})
        self.evaluate_slots()

    def run_all(self):
        while self.next(): pass


def to_dot(tree, steps=None, active=None, loop_state=None, loop_iteration=0):
    nodes=tree['nodes']; statuses={}
    for step in steps or []:
        event=step['event']; statuses[event['node_id']]=event['status']
        for effect in event.get('effects',[]): statuses[effect['node_id']]=effect['status']
    lines=['digraph BT {','graph [rankdir=LR, bgcolor="transparent", nodesep=0.20, ranksep=0.48, splines=polyline];','node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, margin="0.12,0.08", color="#B5C7DB", fillcolor="#F5F8FC", fontcolor="#192C43"];','edge [color="#8497AB", arrowsize=0.55];']
    visited=set()
    def add(nid):
        if nid in visited: return
        visited.add(nid); node=nodes[nid]; fill='#E2EDF9'; border='#91AECF'
        if nid in statuses: fill={'SUCCESS':'#C9EFDF','FAILURE':'#FFD2D2','RUNNING':'#D8E8FA'}.get(statuses[nid],'#E2EDF9');border={'SUCCESS':'#4B9C79','FAILURE':'#D66B6B','RUNNING':'#5A8CC1'}.get(statuses[nid],'#91AECF')
        if nid==active: fill='#FFE6A2'; border='#D49B16'
        title=node['title'].replace('"','\\"'); lines.append(f'{json.dumps(nid)} [label="{title}",fillcolor="{fill}",color="{border}",penwidth={2.3 if nid==active else 1.0}];')
        for cid in node.get('children', [])+([node['child']] if 'child' in node else []):
            lines.append(f'{json.dumps(nid)} -> {json.dumps(cid)};');add(cid)
    add(tree['root'])
    # Dashed feedback is a *runtime annotation*, not a new child edge in the source JSON.
    if loop_state and loop_state != 'NOT_STARTED':
        repeat='c9c27d46-fadc-4ef0-8829-88430f6599a6'
        ask='00cc8681-30d6-43df-8e3a-dd33f55d67dd'
        color='#C28318' if loop_state!='COMPLETE' else '#268455'
        if loop_state == 'COMPLETE':
            label='EXIT → Select Database (next phase)'
            lines.append(f'{json.dumps(repeat)} -> {json.dumps("n11")} [style=dashed,color="#268455",penwidth=2.2,fontsize=12,fontcolor="#16683F",label={json.dumps(label)},constraint=false];')
        else:
            lines.append(f'{json.dumps(ask)} -> {json.dumps(repeat)} [style=dashed,color="#C28318",penwidth=2.4,fontsize=12,fontcolor="#754900",label={json.dumps("LOOP BACK / recheck · iteration " + str(loop_iteration))},constraint=false];')
    lines.append('}');return '\n'.join(lines)
