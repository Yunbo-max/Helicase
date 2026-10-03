import pytest


def test_extraction_payload_cannot_contain_reference_or_other_methods():
    from reviewer_analysis.revision_v2.answer_blind import extraction_task
    record={'method':'secret_method','query_id':'Q61','question':'Which products?',
            'report':'A and B qualify.','reference':'never expose me','run_id':'one'}
    t=extraction_task([record])
    assert set(t['payload'])=={'reports'}
    assert t['payload']['reports']==[{'source_id':t['payload']['reports'][0]['source_id'],
                                    'question':'Which products?','text':'A and B qualify.'}]
    with pytest.raises(ValueError):extraction_task([record,dict(record,method='other')])


def test_blind_units_preserve_relation_and_exclusions_without_scoring():
    from reviewer_analysis.revision_v2.answer_blind import extraction_task, extract_transform
    task=extraction_task([{'method':'x','query_id':'Q61','question':'Who supplies B?',
                          'report':'A supplies B. C is excluded.','run_id':'one'}])
    sid=task['payload']['reports'][0]['source_id']
    obj={'reports':[{'source_id':sid,'answers':[{'label':'A','claim':'A supplies B.',
            'status':'actual','quotes':['A supplies B.']}],
            'excluded':[{'label':'C','quote':'C is excluded.','reason':'explicit rejection'}]}]}
    result=extract_transform(obj,task)
    assert result['groups'][0]['units'][0]['claim']=='A supplies B.'
    assert len(result['groups'][0]['units'])==1
    assert 'reference_id' not in result['groups'][0]['units'][0]
    obj['reports'][0]['answers'][0]['quotes']=['A supplies D.']
    with pytest.raises(ValueError):extract_transform(obj,task)


def test_matching_cannot_change_denominator_and_is_one_to_one():
    from reviewer_analysis.revision_v2.answer_blind import match_transform
    task={'key':['Q61'],'payload':{'predicted_units':[{'id':'p1'},{'id':'p2'}],
          'reference_targets':[{'id':'r1'}]},'source_map':{'s':{
          'method':'x','run_id':'one','ids':['p1','p2'],'native_counts':[0,0]}}}
    obj={'candidates':[{'predicted_id':'p1','reference_id':'r1','reason':'equivalent'},
                       {'predicted_id':'p2','reference_id':'r1','reason':'equivalent'}],
         'unmatched':[]}
    s=match_transform(obj,task)['scores'][0]
    assert s['n_pred_units']==2 and s['n_reference_units']==1 and s['matched_units']==1
    assert s['answer_f1']==pytest.approx(2/3)
    obj['candidates'][0]['predicted_id']='invented'
    with pytest.raises(ValueError):match_transform(obj,task)


def test_all_other_exclusion_is_not_a_third_positive_answer():
    from reviewer_analysis.revision_v2.answer_blind import extraction_task,extract_transform
    t=extraction_task([{'method':'x','query_id':'Q62','run_id':'one','question':'Which drinks?',
                       'report':'A qualifies. All other drinks do not qualify.'}])
    sid=t['payload']['reports'][0]['source_id']
    obj={'reports':[{'source_id':sid,'answers':[
        {'label':'A','claim':'A qualifies.','status':'actual','quotes':['A qualifies.']},
        {'label':'All other drinks','claim':'All other drinks do not qualify.','status':'negative',
         'quotes':['All other drinks do not qualify.']}],'excluded':[]}]}
    g=extract_transform(obj,t)['groups'][0]
    assert len(g['units'])==1
    assert g['excluded'][-1]['label']=='All other drinks'
    t['payload']['reports'][0]['text']='No drinks qualify.'
    obj['reports'][0]['answers']=[{'label':'No drinks','claim':'No drinks qualify.',
        'status':'negative','quotes':['No drinks qualify.']}]
    assert len(extract_transform(obj,t)['groups'][0]['units'])==1


def test_normalization_preserves_every_source_unit_and_cannot_borrow():
    from reviewer_analysis.revision_v2.answer_blind import normalize_transform
    source={'source_id':'s1','method':'a','query_id':'Q1','units':[
        {'id':'p1','quotes':['A lemon']},{'id':'p2','quotes':['A orange']}]}
    task={'groups':[source]}
    obj={'groups':[{'source_id':'s1','units':[{'label':'A','claim':'A drinks',
        'status':'actual','input_ids':['p1','p2']}]}]}
    g=normalize_transform(obj,task)['groups'][0]
    assert len(g['units'])==1 and g['units'][0]['quotes']==['A lemon','A orange']
    obj['groups'][0]['units'][0]['input_ids']=['p1']
    with pytest.raises(ValueError):normalize_transform(obj,task)
    obj['groups'][0]['units'][0]['input_ids']=['p1','other_source_id']
    with pytest.raises(ValueError):normalize_transform(obj,task)
