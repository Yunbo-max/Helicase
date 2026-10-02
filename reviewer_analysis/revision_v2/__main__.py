"""CLI. Network operations require --execute; all outputs are versioned/private."""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path
from .common import load_env, read_jsonl, redact, qid, write_json, write_jsonl, new_directory


def filters(parser,default_quadrants='Q4'):
    parser.add_argument('--methods',help='Comma-separated method names, as stored')
    parser.add_argument('--quadrants',default=default_quadrants,help='Comma-separated quadrants; all for every quadrant')
    parser.add_argument('--ids',help='Comma-separated query IDs, e.g. 61,64')
    parser.add_argument('--fact-type',choices=['node','edge','all'],default='edge')


def select(rows,args):
    methods=set(args.methods.split(',')) if getattr(args,'methods',None) else None
    quads=set(args.quadrants.split(',')) if getattr(args,'quadrants','all')!='all' else None
    ids={qid(x) for x in args.ids.split(',')} if getattr(args,'ids',None) else None
    kind=getattr(args,'fact_type','all')
    return [r for r in rows if (not methods or r.get('method') in methods)
            and (not quads or r.get('quadrant') in quads) and (not ids or r.get('query_id') in ids)
            and (kind=='all' or 'fact_type' not in r or r['fact_type']==kind)]


def write_analysis(out,result):
    out=new_directory(out);write_json(out/'calibration.json',result)
    rows=[]
    for g in result['groups']:
        r={k:g[k] for k in ('method','fact_type','assessor','assessor_type','n_facts','n_with_confidence',
                            'n_labelled_binary','n_unresolved','n_missing_labels','label_coverage','n_queries_assessed')}
        for k in ('brier','ece','adaptive_ece'):
            r[k]=g['metrics'][k] if g['metrics'] else None
        rows.append(r)
    with (out/'calibration.csv').open('w',newline='',encoding='utf8') as f:
        if rows:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    def tex(s):
        for a,b in [('&',r'\&'),('_',r'\_'),('%',r'\%'),('#',r'\#')]:s=str(s).replace(a,b)
        return s
    lines=[r'\begin{tabular}{lllrrrr}',r'\toprule',r'Method & Type & Assessor & $N$ & Coverage & ECE & Brier \\',r'\midrule']
    for r in rows:
        v=lambda k:'--' if r[k] is None else f'{r[k]:.3f}'
        lines.append(f"{tex(r['method'])} & {tex(r['fact_type'])} & {tex(r['assessor'])} & {r['n_labelled_binary']} & {v('label_coverage')} & {v('ece')} & {v('brier')} \\\\")
    lines.extend([r'\bottomrule',r'\end{tabular}',
        '% Binary-assessed subset only. Report unresolved/missing coverage. LLM assessors are not human ground truth.'])
    (out/'calibration_table.tex').write_text('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for i,g in enumerate(result['groups']):
        if not g['metrics']:continue
        bs=g['metrics']['bins']
        fig,ax=plt.subplots(figsize=(6,6))
        ax.plot([0,1],[0,1],linestyle='--',label='Perfect calibration')
        ax.scatter([b['confidence'] for b in bs],[b['accuracy'] for b in bs],
                   s=[min(250,20+b['n']) for b in bs],label='Observed bins')
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Stored confidence',ylabel='Assessed support / correctness rate',
               title=f"{g['method']} / {g['fact_type']} / {g['assessor']}")
        ax.legend();fig.tight_layout()
        fig.savefig(out/f'reliability_{i:02d}.png',dpi=180)
        with matplotlib.rc_context({'svg.fonttype':'none'}):fig.savefig(out/f'reliability_{i:02d}.svg')
        plt.close(fig)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',help='Local private .env file; never printed or uploaded')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--archive',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('doctor');p.add_argument('--runtime-root');p.add_argument('--backend-root');p.add_argument('--purpose',choices=['agent','judge','offline'],default='agent')
    p=sub.add_parser('facts');p.add_argument('--records',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('pages');p.add_argument('--facts',required=True);p.add_argument('--out',required=True);p.add_argument('--max-pages',type=int,default=10);p.add_argument('--execute',action='store_true');filters(p)
    p=sub.add_parser('judge');p.add_argument('--facts',required=True);p.add_argument('--pages',required=True);p.add_argument('--out',required=True);p.add_argument('--assessor',required=True);p.add_argument('--max-calls',type=int,default=10);p.add_argument('--execute',action='store_true');p.add_argument('--max-sources',type=int,default=4);p.add_argument('--chars-per-source',type=int,default=8000);filters(p)
    p=sub.add_parser('extract');p.add_argument('--records',required=True);p.add_argument('--out',required=True);p.add_argument('--max-calls',type=int,default=10);p.add_argument('--execute',action='store_true');filters(p)
    p=sub.add_parser('match');p.add_argument('--predictions',required=True);p.add_argument('--reference',required=True);p.add_argument('--out',required=True);p.add_argument('--max-calls',type=int,default=10);p.add_argument('--execute',action='store_true')
    p=sub.add_parser('analyse');p.add_argument('--facts',required=True);p.add_argument('--labels',required=True,nargs='+');p.add_argument('--out',required=True);p.add_argument('--bootstrap',type=int,default=2000);filters(p)
    p=sub.add_parser('human-forms');p.add_argument('--facts',required=True);p.add_argument('--out',required=True);p.add_argument('--sample',type=int,default=400);p.add_argument('--case-ids',default='61,64');p.add_argument('--seed',type=int,default=268226721)
    p=sub.add_parser('agreement');p.add_argument('--rater-a',required=True);p.add_argument('--rater-b',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('human-labels');p.add_argument('--ratings',required=True);p.add_argument('--mapping',required=True);p.add_argument('--assessor',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('paired');p.add_argument('--scores',required=True);p.add_argument('--method-a',required=True);p.add_argument('--method-b',required=True);p.add_argument('--expected-queries',required=True);p.add_argument('--metric',default='graph_f1');p.add_argument('--out',required=True)
    p=sub.add_parser('repeat');p.add_argument('--questions',required=True);p.add_argument('--out',required=True);p.add_argument('--runtime-root',required=True);p.add_argument('--backend-root');p.add_argument('--runs',type=int,default=3);p.add_argument('--variants',default='full');p.add_argument('--ids');p.add_argument('--max-jobs',type=int,default=1);p.add_argument('--wall-seconds',type=int,default=3600);p.add_argument('--execute',action='store_true');p.add_argument('--single-model',action='store_true');p.add_argument('--dataset-role',choices=['existing_scqa','pilot','new_holdout'],default='existing_scqa')
    args=parser.parse_args(argv);load_env(args.env_file)
    if args.command=='prepare':
        from .archive import prepare
        r=prepare(args.archive,args.out)
        r={k:r[k] for k in ('record_counts','helicase_q4_edges','limits')}  # Full audit on disk.
    elif args.command=='doctor':
        from .runner import doctor
        r=doctor(args.runtime_root,args.backend_root,args.purpose)
    elif args.command=='facts':
        from .archive import native_facts
        rows=read_jsonl(args.records);facts=[f for r0 in rows for f in native_facts(r0)]
        if Path(args.out).exists():raise ValueError('Facts output exists: use a new name')
        write_jsonl(args.out,facts);r={'n_facts':len(facts)}
    elif args.command=='pages':
        from .judging import collect_pages
        r=collect_pages(select(read_jsonl(args.facts),args),args.out,args.max_pages,args.execute)
    elif args.command=='judge':
        from .judging import judge_facts
        r=judge_facts(select(read_jsonl(args.facts),args),read_jsonl(args.pages),args.out,args.assessor,args.max_calls,args.execute,args.max_sources,args.chars_per_source)
    elif args.command=='extract':
        from .evaluation import extract_reports
        r=extract_reports(select(read_jsonl(args.records),args),args.out,args.max_calls,args.execute)
    elif args.command=='match':
        from .evaluation import match_graphs
        r=match_graphs(read_jsonl(args.predictions),read_jsonl(args.reference),args.out,args.max_calls,args.execute)
    elif args.command=='analyse':
        from .metrics import analyse_labels
        fs=select(read_jsonl(args.facts),args);ids={f['fact_id'] for f in fs};all_ids={f['fact_id'] for f in read_jsonl(args.facts)}
        ys=[y for path in args.labels for y in read_jsonl(path)]
        if any(y['fact_id'] not in all_ids for y in ys):raise ValueError('Labels contain stale/unknown fact IDs')
        r=analyse_labels(fs,[y for y in ys if y['fact_id'] in ids],args.bootstrap);write_analysis(args.out,r)
        r={'groups':len(r['groups']),'output':args.out,'warning':r['warning']}
    elif args.command=='human-forms':
        from .human import make_forms
        r={'n_sampled':make_forms(read_jsonl(args.facts),args.out,args.sample,args.seed,tuple(qid(x) for x in args.case_ids.split(',') if x))}
    elif args.command=='agreement':
        from .human import agreement,read_csv
        r=agreement(read_csv(args.rater_a),read_csv(args.rater_b));write_json(args.out,r)
    elif args.command=='human-labels':
        from .human import read_csv,ratings_to_labels
        labels=ratings_to_labels(read_csv(args.ratings),read_jsonl(args.mapping),args.assessor);write_jsonl(args.out,labels);r={'n_labels':len(labels)}
    elif args.command=='paired':
        from .metrics import paired_query_statistics
        r=paired_query_statistics(read_jsonl(args.scores),args.method_a,args.method_b,args.metric,expected_query_ids=[r['query_id'] for r in read_jsonl(args.expected_queries)]);write_json(args.out,r)
    elif args.command=='repeat':
        from .runner import repeat
        r=repeat(read_jsonl(args.questions),args.out,args.runtime_root,args.backend_root,args.runs,
                 tuple(args.variants.split(',')),args.ids.split(',') if args.ids else None,
                 args.execute,args.max_jobs,args.wall_seconds,dataset_role=args.dataset_role,single_model=args.single_model)
    print(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False))
    if r.get('n_failed',0) or (args.command=='doctor' and r.get('missing')) or any(r.get('status_counts',{}).get(k,0) for k in ('error','needs_review','interrupted')):return 2
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print(redact(f'{type(exc).__name__}: {exc}'),file=sys.stderr);sys.exit(2)
