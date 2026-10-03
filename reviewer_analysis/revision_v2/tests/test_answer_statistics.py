import unittest
from reviewer_analysis.revision_v2 import answer_statistics as stats
from reviewer_analysis.revision_v2.answer_units import score_answer


def observations():
    rows=[]
    for method in stats.METHODS:
        for q in stats.QUERIES:
            value=score_answer(['p'],['r'],[['p','r']],2,2) if method=='Helicase' else score_answer(['p'],['r'],[],0,0)
            rows.append(dict(value,method=method,query_id=q,run_id='synthetic',input_hash='synthetic'))
    return rows


class StatisticsTests(unittest.TestCase):
    def test_all_methods_queries_and_weights_included(self):
        got=stats.analyse(observations(),n_boot=50)
        self.assertEqual(len(got['paired']),84)
        self.assertEqual(len(got['weight_rows']),560)
        self.assertEqual(len(got['weight_pairs']),84)
        first=next(x for x in got['paired'] if x['method_a']=='Helicase')
        self.assertEqual(first['query_bootstrap_95ci'],[1.0,1.0])

    def test_missing_duplicate_and_out_of_range_rejected(self):
        rows=observations()
        for bad in [rows[:-1],rows+[rows[0]]]:
            with self.assertRaises(ValueError):stats.analyse(bad,n_boot=50)
        rows[0]['answer_precision']=1.01
        with self.assertRaises(ValueError):stats.analyse(rows,n_boot=50)

    def test_formula_is_recomputed_not_trusted(self):
        rows=observations();rows[0]['legacy_composite']=.95
        with self.assertRaises(ValueError):stats.analyse(rows,n_boot=50)
