"""Synthetic tests only: these are not SCQA experimental results."""
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

class SuiteTests(unittest.TestCase):
    def suite(self, module):
        import importlib
        try:
            return importlib.import_module('reviewer_analysis.revision_v2.' + module)
        except ImportError as exc:
            self.fail('Revision suite not implemented: ' + str(exc))

    def test_brier_known_value(self):
        self.assertAlmostEqual(self.suite('metrics').calibration([0.9,0.2],[1,0])['brier'], .025)

    def test_ece_known_value(self):
        self.assertAlmostEqual(self.suite('metrics').calibration([0.9,0.2],[1,0])['ece'], .15)

    def test_invalid_score_is_not_clipped(self):
        with self.assertRaises(ValueError): self.suite('metrics').calibration([1.07],[1])

    def test_nonbinary_label_rejected(self):
        with self.assertRaises(ValueError): self.suite('metrics').calibration([.4],[.4])

    def test_nan_rejected(self):
        with self.assertRaises(ValueError): self.suite('metrics').calibration([math.nan],[1])

    def test_empty_calibration_rejected(self):
        with self.assertRaises(ValueError): self.suite('metrics').calibration([],[])

    def test_adaptive_bins_do_not_split_ties(self):
        out=self.suite('metrics').calibration([.5]*20,[0,1]*10)
        self.assertEqual(len(out['adaptive_bins']),1)
        self.assertEqual(out['adaptive_ece'],0.)

    def test_edges_and_nodes_separate(self):
        m=self.suite('metrics')
        f=[{'fact_id':'a','query_id':'Q1','method':'x','run_id':'r1','fact_type':'edge','confidence':.8},
           {'fact_id':'b','query_id':'Q2','method':'x','run_id':'r1','fact_type':'node','confidence':.2}]
        y=[{'fact_id':'a','truth_status':'supported','assessor':'expert','assessor_type':'human'},
           {'fact_id':'b','truth_status':'contradicted','assessor':'expert','assessor_type':'human'}]
        r=m.analyse_labels(f,y,n_boot=50)
        self.assertEqual({g['fact_type'] for g in r['groups']},{'edge','node'})

    def test_unresolved_not_false(self):
        m=self.suite('metrics')
        f=[{'fact_id':str(i),'query_id':'Q1','method':'x','run_id':'r1','fact_type':'edge','confidence':.8} for i in range(2)]
        y=[{'fact_id':'0','truth_status':'supported','assessor':'expert','assessor_type':'human'},
           {'fact_id':'1','truth_status':'unresolved','assessor':'expert','assessor_type':'human'}]
        r=m.analyse_labels(f,y,n_boot=50)['groups'][0]
        self.assertEqual(r['n_labelled_binary'],1)
        self.assertEqual(r['n_unresolved'],1)
        self.assertAlmostEqual(r['metrics']['brier'], .04)
        self.assertAlmostEqual(r['label_coverage'],.5)
        self.assertAlmostEqual(r['brier_all_fact_bounds'][1], .34)

    def test_multiple_judges_not_pooled(self):
        m=self.suite('metrics')
        f=[{'fact_id':'a','query_id':'Q1','method':'x','run_id':'r','fact_type':'edge','confidence':.8}]
        y=[{'fact_id':'a','truth_status':s,'assessor':a,'assessor_type':'llm'} for a,s in [('A','supported'),('B','contradicted')]]
        self.assertEqual(len(m.analyse_labels(f,y,n_boot=20)['groups']),2)

    def test_unknown_label_id_rejected(self):
        with self.assertRaises(ValueError): self.suite('metrics').analyse_labels([], [{'fact_id':'ghost','truth_status':'supported','assessor':'a','assessor_type':'human'}])

    def test_graph_matching_bounded(self):
        m=self.suite('metrics')
        g={'nodes':[{'id':'1','name':'A','node_type':'company'},{'id':'2','name':'B','node_type':'company'}],
           'edges':[{'id':'e','source_id':'1','target_id':'2','relation_type':'supplies_to'}]}
        r=m.score_graph(g,g,[['1','1'],['2','2']],[['e','e']])
        self.assertEqual(r['graph_f1'],1)

    def test_many_to_one_matches_rejected(self):
        m=self.suite('metrics');g={'nodes':[{'id':'1'},{'id':'2'}], 'edges':[]}
        with self.assertRaises(ValueError): m.score_graph(g,g,[['1','1'],['2','1']],[])

    def test_reversed_relation_match_rejected(self):
        m=self.suite('metrics'); p={'nodes':[{'id':'1'},{'id':'2'}], 'edges':[{'id':'e','source_id':'1','target_id':'2','relation_type':'supplies_to'}]}
        g={'nodes':p['nodes'], 'edges':[{'id':'f','source_id':'2','target_id':'1','relation_type':'supplies_to'}]}
        with self.assertRaises(ValueError):m.score_graph(p,g,[['1','1'],['2','2']],[['e','f']])

    def test_empty_empty_graph_not_perfect(self):
        r=self.suite('metrics').score_graph({'nodes':[],'edges':[]},{'nodes':[],'edges':[]},[],[])
        self.assertIsNone(r['graph_f1'])

    def test_import_excludes_unrequested_files_and_iran(self):
        a=self.suite('archive')
        row={'id':1,'quadrant':'Q1','question':'test','knowledge_graph':{'nodes':{},'edges':{}},'status':'success'}
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/'x.zip'
            with zipfile.ZipFile(z,'w') as f:
                f.writestr('results/scpqa_qwen3.jsonl',json.dumps(row)+'\n')
                f.writestr('results/iran.json','BAD')
                f.writestr('../../oops','BAD')
            audit=a.prepare(z,Path(d)/'out')
            self.assertEqual(audit['record_counts']['Helicase'],1)
            self.assertFalse((Path(d)/'oops').exists())

    def test_missing_uncertainty_not_zero(self):
        f=self.suite('archive').native_facts({'query_id':'Q64','quadrant':'Q4','question':'q','method':'H','run_id':'r','knowledge_graph':{'nodes':{'n':{'id':'n','name':'A','node_type':'company'}},'edges':{}},'ref2url':{}})
        self.assertIsNone(f[0]['confidence'])

    def test_hash_cached_once_not_per_fact(self):
        a=self.suite('archive')
        r={'record_hash':'already_hashed','query_id':'Q1','quadrant':'Q1','question':'q','method':'H','run_id':'r',
           'knowledge_graph':{'nodes':{'n':{'id':'n','name':'A','uncertainty':.1}},'edges':{}},'ref2url':{}}
        with patch.object(a,'digest',wraps=a.digest) as h:
            a.native_facts(r)
            self.assertFalse(any(call.args[0] is r for call in h.call_args_list))

    def test_citation_mapping_local_to_record(self):
        a=self.suite('archive'); r={'query_id':'Q64','quadrant':'Q4','question':'q','method':'H','run_id':'r','knowledge_graph':{'nodes':{'n':{'id':'n','name':'A','sources':[0,7],'uncertainty':.1}},'edges':{}},'ref2url':{'0':{'url':'https://example.com','snippet':'x'}}}
        f=a.native_facts(r)[0]
        self.assertEqual(f['citation_urls'],['https://example.com'])
        self.assertEqual(f['unresolved_reference_ids'],['7'])

    def test_duplicate_query_rows_rejected(self):
        a=self.suite('archive');row={'id':1,'quadrant':'Q1','question':'q','knowledge_graph':{}}
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/'x.zip'
            with zipfile.ZipFile(z,'w') as f:f.writestr('results/scpqa_qwen3.jsonl',(json.dumps(row)+'\n')*2)
            with self.assertRaises(ValueError):a.prepare(z,Path(d)/'out')

    def test_no_evidence_judgment_is_unresolved(self):
        j=self.suite('judging')
        r=j.validate_judgment({'truth_status':'supported','citation_status':'entails','quotes':[],'reason':'guess'}, {})
        self.assertEqual(r['truth_status'],'unresolved')
        self.assertIn('invalid',r['validation_status'])

    def test_fake_quote_invalidates_judgment(self):
        r=self.suite('judging').validate_judgment({'truth_status':'supported','citation_status':'entails','quotes':[{'source_id':'s1','text':'invented'}]}, {'s1':'real source'})
        self.assertEqual(r['truth_status'],'unresolved')

    def test_real_quote_accepted_but_not_human_truth(self):
        r=self.suite('judging').validate_judgment({'truth_status':'supported','citation_status':'entails','quotes':[{'source_id':'s1','text':'A supplies B'}]}, {'s1':'The contract says A supplies B.'})
        self.assertEqual(r['truth_status'],'supported')
        self.assertEqual(r['validation_status'],'quote_verified_not_truth_verified')

    def test_judge_prompt_is_blinded(self):
        p=self.suite('judging').build_claim_payload({'fact_id':'secret','confidence':.999,'method':'Helicase','query_id':'Q1','question':'q','claim':'A supplies B','fact_type':'edge','scope':{}}, [])
        t=json.dumps(p)
        self.assertNotIn('Helicase',t);self.assertNotIn('.999',t);self.assertNotIn('secret',t)

    def test_private_url_rejected(self):
        with self.assertRaises(ValueError):self.suite('common').validate_public_url('http://127.0.0.1/a')

    def test_url_credentials_rejected(self):
        with self.assertRaises(ValueError):self.suite('common').validate_public_url('https://user:pass@example.com')

    def test_env_redaction(self):
        with patch.dict('os.environ',{'SILICONFLOW_API_KEY':'supersecretvalue'}):
            self.assertNotIn('supersecretvalue',self.suite('common').redact('token=supersecretvalue'))

    def test_no_gold_in_repeat_query(self):
        q=self.suite('runner').validate_queries([{'query_id':'Q64','quadrant':'Q4','question':'q','gold':'answer'}])
        self.assertEqual(set(q[0]), {'query_id','quadrant','question'})

    def test_runner_no_core_edits(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'helicase').mkdir(); (p/'helicase'/'__init__.py').write_text('#unchanged')
            a=self.suite('runner').source_fingerprint([p/'helicase'])
            self.assertEqual((p/'helicase'/'__init__.py').read_text(),'#unchanged')
            self.assertTrue(a)

    def test_agreement_pre_adjudication(self):
        h=self.suite('human')
        a=[{'item_id':'a','truth_status':'supported','citation_status':'entails'}, {'item_id':'b','truth_status':'contradicted','citation_status':'contradicts'}]
        r=h.agreement(a,a)
        self.assertEqual(r['truth_status']['raw_agreement'],1)
        self.assertEqual(r['truth_status']['cohen_kappa'],1)

    def test_missing_rating_reported(self):
        r=self.suite('human').agreement([{'item_id':'a','truth_status':''}], [{'item_id':'a','truth_status':'supported'}])
        self.assertEqual(r['truth_status']['n_paired'],0)

class EvaluationTests(unittest.TestCase):
    suite = SuiteTests.suite
    def test_extraction_quotes_must_exist(self):
        e=self.suite('evaluation')
        with self.assertRaises(ValueError):e.validate_extraction({'nodes':[{'id':'n','name':'A','node_type':'company','quote':'made up'}], 'edges':[]},'A is present.')

    def test_extraction_has_no_invented_confidence(self):
        e=self.suite('evaluation')
        g=e.validate_extraction({'nodes':[{'id':'n','name':'A','node_type':'company','quote':'A is present','uncertainty':0.01}], 'edges':[]},'A is present.')
        self.assertNotIn('uncertainty',g['nodes'][0])

    def test_report_extraction_keeps_edge_inference_status(self):
        e=self.suite('evaluation')
        g={'nodes':[{'id':'a','name':'A','quote':'A may supply B','node_type':'company'}, {'id':'b','name':'B','quote':'A may supply B','node_type':'company'}],
           'edges':[{'id':'e','source_id':'a','target_id':'b','relation_type':'supplies_to','evidence_status':'candidate','quote':'A may supply B'}]}
        self.assertEqual(e.validate_extraction(g,'A may supply B.')['edges'][0]['evidence_status'],'candidate')

    def test_unknown_edge_status_rejected(self):
        e=self.suite('evaluation')
        g={'nodes':[{'id':'a','name':'A','quote':'A supplies A','node_type':'company'}],
           'edges':[{'id':'e','source_id':'a','target_id':'a','relation_type':'supplies_to','quote':'A supplies A'}]}
        with self.assertRaises(ValueError):e.validate_extraction(g,'A supplies A.')

    def test_same_record_ids_with_changed_report_have_different_hash(self):
        a=self.suite('archive')
        r={'id':1,'quadrant':'Q1','question':'q','report':'one'}
        self.assertNotEqual(a.normalize_record(r,'H')['record_hash'],a.normalize_record(dict(r,report='two'),'H')['record_hash'])


class ExecutionTests(unittest.TestCase):
    suite = SuiteTests.suite

    def test_repeat_dry_run_does_not_require_key_or_create_files(self):
        r=self.suite('runner')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'never_created'
            plan=r.repeat([{'query_id':'Q81','quadrant':'Q4','question':'synthetic'}],out,d,runs=3,execute=False)
            self.assertEqual(plan['total_executions'],3)
            self.assertFalse(out.exists())
            self.assertFalse(plan['matched_budget'])

    def test_native_worker_supervisor_with_synthetic_runtime(self):
        r=self.suite('runner')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'runtime'
            for name in ('helicase','helix_core'):
                (root/name).mkdir(parents=True);(root/name/'__init__.py').write_text('')
            (root/'helicase'/'agent.py').write_text('''from dataclasses import dataclass
@dataclass
class Config:
    max_iterations: int = 10
    secret_key: str = 'DO_NOT_EXPORT'
class Orchestrator:
    config=Config()
    def run(self,query):
        return {'report':'synthetic fixture only','knowledge_graph':{'nodes':{},'edges':{}},'actions':[],'iterations':1}
def init_helicase(**kwargs): return Orchestrator()
''')
            env={'SILICON_MODEL':'Qwen/unit-test','SILICONFLOW_API_KEY':'dummykey','SERPER_API_KEY':'dummykey','SEARCH_ENGINE':'serper'}
            with patch.dict('os.environ',env):
                result=r.repeat([{'query_id':'Q1','quadrant':'Q1','question':'synthetic'}],Path(d)/'out',root,
                                runs=1,execute=True,max_jobs=1)
            self.assertEqual(result['status_counts']['returned'],1)
            cfg=json.loads((Path(d)/'out/full/run_01/Q1/resolved_config.json').read_text())
            self.assertNotIn('secret_key',cfg)
            self.assertEqual((root/'helicase'/'__init__.py').read_text(),'')

    def test_judge_http_calls_mocked_and_resume_does_not_rebill(self):
        j=self.suite('judging');fake=type('Client',(),{'public_config':{'model':'mock'},'chat':lambda self,s,p: (json.dumps({'truth_status':'supported','citation_status':'entails','quotes':[{'source_id':'s','text':'A supplies B'}]}),{'total_tokens':10},'mock')})
        f=[{'fact_id':'f','query_id':'Q1','quadrant':'Q1','method':'H','run_id':'r','fact_type':'edge','confidence':.8,'question':'q','claim':'A supplies B','scope':{},'citation_urls':['https://example.com'],'structural_validity':True}]
        pages=[{'url':'https://example.com','source_id':'s','text':'A supplies B.','status':'ok','captured_at':'test','basis':'synthetic'}]
        with tempfile.TemporaryDirectory() as d,patch.object(j,'CompatibleClient',fake):
            one=j.judge_facts(f,pages,d,'mock',execute=True)
            two=j.judge_facts(f,pages,d,'mock',execute=True)
            self.assertEqual(one['requests_made'],1);self.assertEqual(two['requests_made'],0)
            self.assertEqual(one['n_labels'],1)

    def test_judge_changed_evidence_cannot_use_old_cache(self):
        j=self.suite('judging');fake=type('Client',(),{'public_config':{'model':'mock'}})
        f=[{'fact_id':'f','query_id':'Q1','method':'H','fact_type':'edge','question':'q','claim':'A','citation_urls':[]}]
        with tempfile.TemporaryDirectory() as d,patch.object(j,'CompatibleClient',fake):
            j.judge_facts(f,[],d,'mock',execute=True)
            with self.assertRaises(ValueError):j.judge_facts([dict(f[0],claim='B')],[],d,'mock',execute=True)

    def test_human_forms_are_blind_and_blank(self):
        h=self.suite('human');facts=[{'fact_id':str(i),'query_id':'Q65','quadrant':'Q4','method':'Helicase','confidence':.8,'fact_type':'edge','question':'q','claim':f'claim{i}','scope':{},'citation_urls':[]} for i in range(5)]
        with tempfile.TemporaryDirectory() as d:
            h.make_forms(facts,Path(d)/'forms',sample=3,required_queries=())
            rows=h.read_csv(Path(d)/'forms/rater_a.csv')
            self.assertEqual(len(rows),3)
            self.assertTrue(all(not r['truth_status'] for r in rows))
            self.assertNotIn('method',rows[0]);self.assertNotIn('confidence',rows[0])

class SafetyTests(unittest.TestCase):
    suite=SuiteTests.suite

    def test_empty_labels_do_not_produce_successful_empty_calibration(self):
        with self.assertRaises(ValueError):self.suite('metrics').analyse_labels([],[])

    def test_stop_child_kills_process_group(self):
        r=self.suite('runner')
        from unittest.mock import Mock
        p=Mock();p.pid=123;p.poll.return_value=None;p.communicate.return_value=('cancelled',None)
        with patch.object(r.os,'killpg') as kill:
            r.stop_child(p)
            if r.os.name=='posix':kill.assert_called_once_with(123,r.signal.SIGTERM)
            else:p.terminate.assert_called_once()

    def test_key_env_name_is_not_itself_redacted(self):
        with patch.dict('os.environ',{'REVIEW_JUDGE_KEY_ENV':'SILICONFLOW_API_KEY','SILICONFLOW_API_KEY':'abcsecret'}):
            self.assertEqual(self.suite('common').redact('missing SILICONFLOW_API_KEY'),'missing SILICONFLOW_API_KEY')

class PairedTests(unittest.TestCase):
    suite=SuiteTests.suite
    def test_null_performance_cannot_be_silently_excluded(self):
        rows=[{'method':m,'query_id':f'Q{i}','graph_f1':(.5 if i<3 else None)} for m in ['A','B'] for i in [1,2,3]]
        with self.assertRaises(ValueError):self.suite('metrics').paired_query_statistics(rows,'A','B')
    def test_expected_queries_detect_joint_missingness(self):
        rows=[{'method':m,'query_id':f'Q{i}','graph_f1':.5} for m in ['A','B'] for i in [1,2]]
        with self.assertRaises(ValueError):self.suite('metrics').paired_query_statistics(rows,'A','B',expected_query_ids=['Q1','Q2','Q3'])

if __name__=='__main__':unittest.main()
