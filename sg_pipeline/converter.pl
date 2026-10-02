% BT-SG structural + explicitly annotated potential data-dependency graph.
% This is a *static possibility graph*, NOT an execution trace or placement DAG.
% Input facts are generated from the exact BehaviorTree.json, including decorators.
:- use_module(library(lists)).
:- use_module(library(http/json)).
:- dynamic bt_node/3, bt_child/3, bt_root/1, access/3.

child_order(A,B,sequence) :- bt_node(P,sequence,_), bt_child(P,I,A), J is I+1, bt_child(P,J,B).
child_order(A,B,fallback) :- bt_node(P,fallback,_), bt_child(P,I,A), J is I+1, bt_child(P,J,B).
% Node control tree is retained as own graph layer; sequence and fallback
% ordering have DIFFERENT success/failure gates.
control_edge(P,C,sequence_child,I) :- bt_node(P,sequence,_), bt_child(P,I,C).
control_edge(P,C,fallback_child,I) :- bt_node(P,fallback,_), bt_child(P,I,C).
control_edge(P,C,repeat_child,I) :- bt_node(P,repeat_until_failure,_), bt_child(P,I,C).
control_edge(P,C,contains,I) :- bt_node(P,other_composite,_), bt_child(P,I,C).

% Candidate data edges: no unjustified claim of guaranteed producer -> reader
% or precedence. Include all explicitly annotated producer/consumer pairs.
potential_data(W,R,K) :- access(W,write,K), access(R,read,K), W \= R.

node_dict(D) :- bt_node(Id,Kind,Label), D=_{id:Id,label:Label,kind:Kind}.
service_dict(D) :- bt_node(Id,action,Label), D=_{id:Id,label:Label}.
service_data_dict(D) :- potential_data(W,R,K), bt_node(W,action,_),bt_node(R,action,_),
  D=_{source:W,target:R,key:K,relation:potential_service_data}.
control_dict(D) :- control_edge(P,C,Relation,I),D=_{source:P,target:C,relation:Relation,index:I,layer:control}.
gate_dict(D) :- child_order(A,B,Kind),
   (Kind=sequence -> Gate='previous_success'; Gate='previous_failure'),
   D=_{source:A,target:B,relation:Kind,gate:Gate,layer:ordered_siblings}.
data_dict(D) :- potential_data(W,R,K), D=_{source:W,target:R,relation:potential_data,key:K,layer:data}.
loop_dict(D) :- bt_node(P,repeat_until_failure,_), bt_child(P,_,C),
   D=_{source:C,target:P,relation:repeat_on_child_success,
       exit_gate:child_failure,layer:loop_annotation}.
root_dict(D) :- bt_root(R), D=R.
build_graph(Graph) :- findall(D,node_dict(D),Nodes),
   findall(D,service_dict(D),Services),
   findall(D,service_data_dict(D),ServiceEdges),
   findall(D,control_dict(D),Controls),
   findall(D,gate_dict(D),Gates),
   findall(D,data_dict(D),DataEdges),
   findall(D,loop_dict(D),LoopEdges),
   root_dict(Root),
   Graph=_{root:Root,nodes:Nodes,service_nodes:Services,service_data_edges:ServiceEdges,loop_edges:LoopEdges,control_edges:Controls,ordered_edges:Gates,
           potential_data_edges:DataEdges,mode:'static_possible',
           note:'Potential data edges can cross exclusive branches; runtime validation is separate.'}.
main :- current_prolog_flag(argv,[Facts,Output|_]),
  consult(Facts), build_graph(G), setup_call_cleanup(open(Output,write,S,[encoding(utf8)]),
  json_write_dict(S,G,[width(0)]),close(S)),halt(0).
:- initialization(main,main).
