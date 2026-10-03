"""Synthetic contract tests; these rows are never research observations."""
import unittest
import tempfile
import json
from pathlib import Path
try:
    from reviewer_analysis.revision_v2 import answer_units as au
except ImportError:
    au = None


def unit(text='A supplies B', modality='asserted', canonical='a supplies b'):
    return {'claim_text':text,'canonical_claim':canonical,'subject':'A','predicate':'supplies',
            'object':'B','assertion_modality':modality,
            'scope':{'time':None,'market':None,'product':None,'facility':None},
            'quote':text,'start':0,'end':len(text)}


class AnswerContractTests(unittest.TestCase):
    def setUp(self):
        if au is None:self.fail('answer_units adapter is not implemented')

    def test_long_report_tail_and_full_coverage(self):
        text='x'*22000+' LAST ANSWER'
        chunks=au.chunk_text(text,1000,80)
        covered=set()
        for c in chunks:
            self.assertEqual(text[c['start']:c['end']],c['text'])
            covered.update(range(c['start'],c['end']))
        self.assertEqual(len(covered),len(text))
        self.assertIn('LAST ANSWER',chunks[-1]['text'])

    def test_offsets_reject_fabricated_quote(self):
        with self.assertRaises(ValueError):au.validate_units({'units':[unit()]},'Only the question exists',0)

    def test_offsets_preserve_late_chunk_location(self):
        text='prefix A supplies B';u=unit();u['start']=7;u['end']=len(text)
        got=au.validate_units({'units':[u]},text[7:],7)
        self.assertEqual(got[0]['quotes'][0]['start'],7)

    def test_canonical_aliases_and_repeated_mentions_count_once(self):
        first=au.validate_units({'units':[unit()]},'A supplies B',0)
        other=unit('Company A supplies B',canonical='a supplies b')
        second=au.validate_units({'units':[other]},other['quote'],0)
        got=au.merge_units(first+second+first)
        self.assertEqual(len(got),1);self.assertEqual(len(got[0]['quotes']),2)

    def test_different_scope_not_deduplicated(self):
        a=unit();b=unit();b['scope']['market']='Japan'
        self.assertEqual(len(au.validate_units({'units':[a,b]},a['quote'],0)),2)

    def test_question_not_in_report_cannot_supply_quote(self):
        u=unit('Which products use A?')
        with self.assertRaises(ValueError):au.validate_units({'units':[u]},'No answer available.',0)

    def test_negative_answer_remains_a_unit(self):
        u=unit('No models use these batteries',modality='negated',canonical='no models use these batteries')
        self.assertEqual(len(au.validate_units({'units':[u]},u['quote'],0)),1)

    def test_unknown_and_duplicate_candidate_ids_rejected(self):
        us=au.validate_units({'units':[unit()]},'A supplies B',0)
        with self.assertRaises(ValueError):au.select_matches(us,us,[{'predicted_id':'invented','reference_id':us[0]['id'],'reason':'same'}])
        pair={'predicted_id':us[0]['id'],'reference_id':us[0]['id'],'reason':'same'}
        with self.assertRaises(ValueError):au.select_matches(us,us,[pair,pair])

    def test_negation_and_plans_cannot_match_actual_supply(self):
        a=au.validate_units({'units':[unit()]},'A supplies B',0)
        for modality in ['negated','planned','capability','candidate','cancelled']:
            b=au.validate_units({'units':[unit(modality=modality)]},'A supplies B',0)
            with self.assertRaises(ValueError):au.select_matches(a,b,[{'predicted_id':a[0]['id'],'reference_id':b[0]['id'],'reason':'ignored modality'}])

    def test_maximum_matching_not_greedy_and_order_invariant(self):
        ps=[dict(unit(),id='p1'),dict(unit(),id='p2')];rs=[dict(unit(),id='r1'),dict(unit(),id='r2')]
        pairs=[{'predicted_id':p,'reference_id':r,'reason':'equivalent'} for p,r in [('p1','r1'),('p1','r2'),('p2','r1')]]
        self.assertEqual(len(au.select_matches(ps,rs,pairs)),2)
        self.assertEqual(au.select_matches(ps,rs,pairs),au.select_matches(ps,rs,list(reversed(pairs))))

    def test_empty_prediction_zero_but_empty_reference_blocked(self):
        result=au.score_answer([],['r1'],[],0,0)
        self.assertEqual(result['answer_f1'],0);self.assertEqual(result['answer_status'],'abstention')
        with self.assertRaises(ValueError):au.score_answer([],[],[],0,0)

    def test_structure_does_not_relabel_answer_score(self):
        no=au.score_answer(['p'],['r'],[['p','r']],0,0)
        yes=au.score_answer(['p'],['r'],[['p','r']],2,2)
        self.assertEqual(no['answer_f1'],1);self.assertAlmostEqual(no['legacy_composite'],.94)
        self.assertEqual(yes['answer_f1'],1);self.assertAlmostEqual(yes['legacy_composite'],1)

    def test_score_rejects_duplicate_matches_and_unknown_ids(self):
        for pairs in [[['p','r'],['p','r']],[['other','r']]]:
            with self.assertRaises(ValueError):au.score_answer(['p'],['r'],pairs,1,1)

    def test_model_payload_excludes_method_reference_and_scores(self):
        record={'method':'Helicase','run_id':'archived_single_run','query_id':'Q64','question':'Who supplies B?',
                'report':'A supplies B','graph_f1':.9,'reference':'C supplies B'}
        tasks=au.extraction_tasks([record],[],1000,80)
        self.assertEqual(set(tasks[0]['payload']),{'question','text','start','end','chunk_index','chunk_count'})
        self.assertNotIn('Helicase',str(tasks[0]['payload']))

    def test_collection_requires_every_chunk_and_rechecks_raw_quotes(self):
        record={'method':'M','run_id':'r','query_id':'Q1','question':'Who supplies B?','report':'A supplies B'}
        tasks=au.extraction_tasks([record],[])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):au.collect(tasks,directory)
            task=tasks[0];raw={'units':[unit()]}
            result={'source_key':task['source_key'],'units':au.validate_units(raw,record['report'],0)}
            path=Path(directory)/'item.json';path.write_text(json.dumps({'task':task,'raw_response':json.dumps(raw),'result':result}))
            self.assertEqual(len(au.collect(tasks,directory)),1)
            result['units'][0]['claim_text']='tampered'
            path.write_text(json.dumps({'task':task,'raw_response':json.dumps(raw),'result':result}))
            with self.assertRaises(ValueError):au.collect(tasks,directory)

    def test_unreviewed_reference_blocks_matching(self):
        u=au.validate_units({'units':[unit()]},'A supplies B',0)
        groups=[{'source_key':['reference','Q1'],'units':u,'units_sha256':au.digest(u)},
                {'source_key':['prediction','M','r','Q1'],'units':u,'units_sha256':au.digest(u)}]
        records=[{'method':'M','run_id':'r','query_id':'Q1','question':'Who supplies B?'}]
        with self.assertRaises(ValueError):au.matching_tasks(groups,records,{})
        with self.assertRaises(ValueError):au.matching_tasks(groups,records,{'dataset_selection_confirmed':True,'reviewer':'SYNTHETIC_TEST','reference_units_sha256':{'Q1':'wrong'}})

    def test_altered_adapter_cannot_reuse_old_tasks(self):
        task=au.extraction_tasks([{'method':'M','run_id':'r','query_id':'Q1','question':'Who?','report':'A supplies B'}],[])[0]
        task['adapter_sha256']='old-code'
        with self.assertRaises(ValueError):au.validate_tasks([task])

    def test_unique_exact_quote_offset_recovery_is_logged(self):
        u=unit();obj={'units':[u]};text='xx'+u['quote']
        fixed,ledger=au.resolve_exact_offsets(obj,text,0)
        self.assertEqual(obj['units'][0]['start'],0)
        self.assertEqual(fixed['units'][0]['start'],2)
        self.assertEqual(len(ledger),1)
        self.assertEqual(len(au.validate_units(fixed,text,0)),1)

    def test_ambiguous_or_absent_quote_is_not_repaired(self):
        u=unit();u['start']=1;u['end']=2
        for text in ['A supplies B / A supplies B','No evidence here']:
            with self.assertRaises(ValueError):au.resolve_exact_offsets({'units':[u]},text,0)


if __name__=='__main__':unittest.main()
