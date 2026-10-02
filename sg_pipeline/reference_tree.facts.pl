% Auto-generated from user BehaviorTree.json. Do not hand edit.
bt_root('n0').
bt_node('n0',sequence,'GENERAL DIALOGUE MANAGER').
bt_child('n0',0,'n1').
bt_child('n0',1,'n2').
bt_child('n0',2,'n8').
bt_child('n0',3,'n9').
bt_child('n0',4,'1211aae4-2979-4751-8e7e-e7c436fe4205').
bt_child('n0',5,'c9c27d46-fadc-4ef0-8829-88430f6599a6').
bt_child('n0',6,'n11').
bt_child('n0',7,'5153d237-e535-48af-9269-4ee876a818c6').
bt_node('n1',condition,'New Input Available?').
bt_node('n2',fallback,'Resolve Input Modality').
bt_child('n2',0,'n3').
bt_child('n2',1,'n6').
bt_node('n3',sequence,'Voice Input').
bt_child('n3',0,'n4').
bt_child('n3',1,'n5').
bt_node('n4',condition,'Is Voice?').
bt_node('n5',action,'Speech To Text').
bt_node('n6',sequence,'Text Input').
bt_child('n6',0,'n7').
bt_node('n7',condition,'Is Text?').
bt_node('n8',action,'Normalize Input').
access('n8',write,'normalized_input').
bt_node('n9',sequence,'Detect Topic').
bt_child('n9',0,'n10').
bt_node('n10',action,'Naive Bayes Topic Classifier').
access('n10',read,'normalized_input').
access('n10',write,'topic').
bt_node('n11',fallback,'Select Database').
bt_child('n11',0,'n12').
bt_child('n11',1,'n15').
bt_node('n12',sequence,'Music').
bt_child('n12',0,'n13').
bt_child('n12',1,'d0440585-6d67-4509-948d-0d4a892917cc').
bt_node('n13',condition,'Topic == Music').
access('n13',read,'topic').
bt_node('n15',sequence,'Art').
bt_child('n15',0,'n16').
bt_child('n15',1,'886b1a32-96f3-483e-a77c-5551f1934510').
bt_node('n16',condition,'Topic == Art').
access('n16',read,'topic').
bt_node('n32',action,'Build Answer Context').
access('n32',read,'topic').
access('n32',read,'intent').
access('n32',read,'slots').
bt_node('n33',action,'Shared LLM — Final Answer Only').
access('n33',read,'topic').
access('n33',read,'intent').
access('n33',read,'slots').
bt_node('5153d237-e535-48af-9269-4ee876a818c6',sequence,'Generate Answer').
bt_child('5153d237-e535-48af-9269-4ee876a818c6',0,'n32').
bt_child('5153d237-e535-48af-9269-4ee876a818c6',1,'n33').
bt_node('0151c83d-eed2-4d4c-adf9-4921399fbe0c',sequence,'Slot Filling').
bt_child('0151c83d-eed2-4d4c-adf9-4921399fbe0c',0,'902d98f0-a3ec-48ff-bf88-9dd365f78b7c').
bt_child('0151c83d-eed2-4d4c-adf9-4921399fbe0c',1,'00cc8681-30d6-43df-8e3a-dd33f55d67dd').
bt_node('1211aae4-2979-4751-8e7e-e7c436fe4205',action,'DetectInetent').
access('1211aae4-2979-4751-8e7e-e7c436fe4205',read,'normalized_input').
access('1211aae4-2979-4751-8e7e-e7c436fe4205',read,'topic').
access('1211aae4-2979-4751-8e7e-e7c436fe4205',write,'intent').
bt_node('902d98f0-a3ec-48ff-bf88-9dd365f78b7c',condition,'Slots Not Filled').
access('902d98f0-a3ec-48ff-bf88-9dd365f78b7c',read,'slots').
access('902d98f0-a3ec-48ff-bf88-9dd365f78b7c',read,'intent').
bt_node('00cc8681-30d6-43df-8e3a-dd33f55d67dd',action,'Ask clarifying question').
access('00cc8681-30d6-43df-8e3a-dd33f55d67dd',read,'slots').
access('00cc8681-30d6-43df-8e3a-dd33f55d67dd',read,'intent').
access('00cc8681-30d6-43df-8e3a-dd33f55d67dd',write,'slots').
bt_node('c9c27d46-fadc-4ef0-8829-88430f6599a6',repeat_until_failure,'Repeat Until Failure').
bt_child('c9c27d46-fadc-4ef0-8829-88430f6599a6',0,'0151c83d-eed2-4d4c-adf9-4921399fbe0c').
bt_node('d0440585-6d67-4509-948d-0d4a892917cc',action,'ActionQueryMusic').
access('d0440585-6d67-4509-948d-0d4a892917cc',read,'topic').
access('d0440585-6d67-4509-948d-0d4a892917cc',read,'intent').
access('d0440585-6d67-4509-948d-0d4a892917cc',read,'slots').
bt_node('886b1a32-96f3-483e-a77c-5551f1934510',action,'ActionQueryArt').
access('886b1a32-96f3-483e-a77c-5551f1934510',read,'topic').
access('886b1a32-96f3-483e-a77c-5551f1934510',read,'intent').
access('886b1a32-96f3-483e-a77c-5551f1934510',read,'slots').
