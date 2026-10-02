"""Independent native executions. No core edits; no claim of hard token/tool matching."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import random
import signal
import subprocess
import sys
import time
from pathlib import Path
from .common import digest, file_hash, qid, redact, utcnow, write_json, write_jsonl

ROLE_VARS=('SILICON_MODEL','READER_MODEL','PREFILTER_MODEL','CODING_MODEL',
           'QUERY_VARIANT_MODEL','UQ_SUMMARIZER_MODEL','UQ_CONSENSUS_MODEL')
CONFIG_VARS=ROLE_VARS+('SEARCH_ENGINE','SEARCH_MAX_RESULTS','SEARCH_MAX_TURN',
        'ENABLE_THREE_STAGE','SEARCH_MULTILINGUAL','UNCERTAINTY_THRESHOLD',
        'UNCERTAINTY_HIGH_THRESHOLD','ACTION_MAX_WORKERS','CODING_AGENT_TIMEOUT',
        'READER_MAX_WORKERS','PREFILTER_BATCH_SIZE','PREFILTER_MAX_WORKERS','EMBEDDING_MODEL',
        'WEB_SEARCH_MIN_PARALLEL_QUERIES','WEB_SEARCH_MAX_PARALLEL_QUERIES','KG_GROWTH_THRESHOLD')


def source_fingerprint(roots):
    files={}
    for root in roots:
        root=Path(root)
        if root.exists():
            for p in sorted(root.rglob('*.py')):
                if '.venv' not in p.parts and '__pycache__' not in p.parts:
                    files[f'{root.name}/{p.relative_to(root)}']=file_hash(p)
    return files


def validate_queries(rows):
    queries=[];seen=set()
    for r in rows:
        ident=qid(r.get('query_id',r.get('id')))
        if ident in seen:raise ValueError('Duplicate query ID')
        seen.add(ident);q=r.get('question',r.get('query'))
        if not isinstance(q,str) or not q.strip() or r.get('quadrant') not in ('Q1','Q2','Q3','Q4'):
            raise ValueError('Question and quadrant required')
        # Only these fields can reach the model. Never pass references/labels to agent.
        queries.append({'query_id':ident,'quadrant':r['quadrant'],'question':q})
    if not queries:raise ValueError('No queries selected')
    return queries


def doctor(runtime_root=None,backend_root=None,purpose='agent'):
    paths=[Path(p).resolve() for p in (runtime_root,backend_root) if p]
    package_paths={}
    for name in ('helicase','helix_core'):
        found=next((p/name for p in paths if (p/name/'__init__.py').is_file()),None)
        if found is None:
            spec=importlib.util.find_spec(name)
            if spec and spec.origin:found=Path(spec.origin).parent
        package_paths[name]=str(found) if found else None
    required=[]
    if purpose=='agent':
        main=os.getenv('SILICON_MODEL','')
        if not main:required.append('SILICON_MODEL')
        models=[os.getenv(k,'') for k in ROLE_VARS]
        providers=set()
        for m in models:
            if not m:continue
            provider=m.split(':',1)[0] if ':' in m and '/' not in m.split(':',1)[0] else ('siliconflow' if '/' in m else 'dashscope')
            providers.add(provider)
        for p in providers:
            key={'siliconflow':'SILICONFLOW_API_KEY','dashscope':'DASHSCOPE_API_KEY'}.get(p)
            if key and not os.getenv(key):required.append(key)
            if not key:required.append('UNVERIFIED_PROVIDER_'+p)
        if os.getenv('SEARCH_ENGINE','serper')!='serper':required.append('SEARCH_ENGINE_MUST_BE_SERPER_FOR_THIS_PROTOCOL')
        if not os.getenv('SERPER_API_KEY'):required.append('SERPER_API_KEY')
        required.extend(n+' source package' for n,p in package_paths.items() if p is None)
    elif purpose=='judge':
        for k in ('REVIEW_JUDGE_BASE_URL','REVIEW_JUDGE_MODEL'):
            if not os.getenv(k):required.append(k)
        env=os.getenv('REVIEW_JUDGE_KEY_ENV','SILICONFLOW_API_KEY')
        if not os.getenv(env):required.append(env)
    return {'purpose':purpose,'source_packages':package_paths,'missing':required,
            'jina_key_present':bool(os.getenv('JINA_API_KEY')),
            'checks':'Presence/path checks only. No network, no key validity or model availability check.',
            'no_api_calls_made':True}


def stop_child(proc):
    """Ctrl-C must not leave a paid API worker running in its new process group."""
    if proc.poll() is None:
        if os.name=='posix':os.killpg(proc.pid,signal.SIGTERM)
        else:proc.terminate()
    try:return proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name=='posix':os.killpg(proc.pid,signal.SIGKILL)
        else:proc.kill()
        return proc.communicate()


def repeat(questions,out,runtime_root,backend_root=None,runs=3,variants=('full',),ids=None,
           execute=False,max_jobs=1,wall_seconds=3600,seed=268226721,dataset_role='existing_scqa',single_model=False):
    if runs<1 or max_jobs<1 or wall_seconds<1:raise ValueError('Positive run/job/time caps required')
    if set(variants)-{'full','search_n1'}:raise ValueError('Only full and search_n1 are verified native config controls. No fake no-UQ baseline.')
    queries=validate_queries(questions)
    if ids:
        wanted={qid(x) for x in ids};queries=[q for q in queries if q['query_id'] in wanted]
        if wanted!={q['query_id'] for q in queries}:raise ValueError('Some requested query IDs are absent')
    jobs=[];rng=random.Random(seed)
    for rep in range(runs):
        order=queries.copy();rng.shuffle(order)
        for q in order:
            vs=list(variants);rng.shuffle(vs)
            for v in vs:jobs.append({'query':q,'variant':v,'run_id':f'run_{rep+1:02d}',
                                    'seed':seed+rep,'dataset_role':dataset_role})
    check=doctor(runtime_root,backend_root)
    plan={'total_executions':len(jobs),'max_new_executions_this_invocation':max_jobs,'execute':execute,
          'dataset_role':dataset_role,'variants':list(variants),'doctor':check,
          'matched_budget':False,'note':'Iteration and wall-clock limits only. Native backend token and actual API-call accounting remain unverified.'}
    if not execute:return plan
    if check['missing']:raise ValueError('Preflight missing: '+', '.join(check['missing']))
    if not Path(runtime_root).is_dir():raise ValueError('Runtime source root missing')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    roots=[Path(p) for p in check['source_packages'].values()]
    fingerprint=source_fingerprint(roots)
    config={'queries_sha256':digest(queries),'runtime_sha256':digest(fingerprint),
            'runtime_files':fingerprint,'roles_and_config':{k:os.getenv(k) for k in CONFIG_VARS},
            'runs':runs,'variants':list(variants),'seed':seed,'dataset_role':dataset_role,
            'single_model':single_model,'wall_seconds':wall_seconds,'neo4j_enabled':False,
            'suite_sha256':digest(source_fingerprint([Path(__file__).parent]))}
    mf=out/'freeze.json'
    if mf.exists() and json.loads(mf.read_text())!=config:raise ValueError('Frozen inputs/code/config changed; use a new run directory')
    write_json(mf,config);write_json(out/'schedule.json',jobs)
    count=0
    for job in jobs:
        directory=out/job['variant']/job['run_id']/job['query']['query_id']
        status=directory/'status.json'
        if status.exists():continue  # Failures also retained; no automatic cherry-picked reruns.
        if count>=max_jobs:break
        directory.mkdir(parents=True,exist_ok=True)
        job.update(runtime_root=str(Path(runtime_root).resolve()),backend_root=str(Path(backend_root).resolve()) if backend_root else None,
                   output_dir=str(directory),single_model=single_model,freeze_sha256=digest(config))
        write_json(directory/'job.json',job)
        env=dict(os.environ);env['PYTHONHASHSEED']=str(job['seed']);env['NEO4J_ENABLED']='false'
        args=[sys.executable,'-m','reviewer_analysis.revision_v2.runner','--worker',str(directory/'job.json')]
        start=time.monotonic();count+=1
        write_json(status,{'status':'running','started_at':utcnow()})
        proc=None
        try:
            proc=subprocess.Popen(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                   text=True,start_new_session=(os.name=='posix'))
            try: output,_=proc.communicate(timeout=wall_seconds)
            except subprocess.TimeoutExpired:
                if os.name=='posix':os.killpg(proc.pid,signal.SIGKILL)
                else:proc.kill()
                output,_=proc.communicate();raise TimeoutError('Native query exceeded wall-clock cap')
            (directory/'worker.log').write_text(redact(output),encoding='utf8')
            ok=proc.returncode==0 and (directory/'result.json').is_file()
            markers=('rate limit exhausted','Φ_gen failed','no actions completed this iteration','all search queries failed')
            flags=[m for m in markers if m.lower() in output.lower()]
            state=('needs_review' if flags else 'returned') if ok else 'error'
            write_json(status,{'status':state,'detected_failure_markers':flags,'returncode':proc.returncode,
                               'elapsed_seconds':time.monotonic()-start,'ended_at':utcnow()})
            if not ok or flags:break  # Do not burn the full batch on failed or partial calls.
        except KeyboardInterrupt:
            if proc is not None:
                text,_=stop_child(proc)
                (directory/'worker.log').write_text(redact(text or ''),encoding='utf8')
            write_json(status,{'status':'interrupted','ended_at':utcnow()})
            raise
        except Exception as exc:
            write_json(status,{'status':'error','error':redact(str(exc)),
                               'elapsed_seconds':time.monotonic()-start,'ended_at':utcnow()})
            break
    all_status=[json.loads(p.read_text()) for p in out.glob('*/*/Q*/status.json')]
    records=[]
    for p in out.glob('*/*/Q*/result.json'): records.append(json.loads(p.read_text()))
    write_jsonl(out/'records.jsonl',records)
    return dict(plan,new_executions=count,status_counts={k:sum(r['status']==k for r in all_status) for k in ('returned','error','running','needs_review','interrupted')},
                n_unstarted=len(jobs)-len(all_status))


def native_worker(job_path):
    job=json.loads(Path(job_path).read_text());out=Path(job['output_dir'])
    for p in (job.get('backend_root'),job['runtime_root']):
        if p:sys.path.insert(0,p)
    random.seed(job['seed'])
    try:
        import numpy as np
        np.random.seed(job['seed'])
    except ImportError:pass
    os.environ['NEO4J_ENABLED']='false'
    if job['single_model']:
        for k in ROLE_VARS:os.environ[k]=os.environ['SILICON_MODEL']
    if job['variant']=='search_n1':
        os.environ['WEB_SEARCH_MIN_PARALLEL_QUERIES']='1'
        os.environ['WEB_SEARCH_MAX_PARALLEL_QUERIES']='1'
    os.environ['MAX_HELIX_ITERATIONS']='20' if job['query']['quadrant']=='Q4' else '10'
    import helicase
    expected=Path(job['runtime_root'])/'helicase'
    if Path(helicase.__file__).resolve().parent!=expected.resolve():raise ValueError('Imported a different Helicase source root')
    import logging
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    from helicase.agent import init_helicase
    from dataclasses import asdict
    orchestrator=init_helicase(lang='en',llm_model=os.environ['SILICON_MODEL'],search_engine='serper')
    # Do not save API keys/password fields from config, even when the backend defines them.
    cfg={k:v for k,v in asdict(orchestrator.config).items() if not any(s in k.lower() for s in ('key','password','secret','token'))}
    write_json(out/'resolved_config.json',cfg)
    t=time.monotonic();raw=orchestrator.run(job['query']['question'])
    write_json(out/'native_output.json',raw)
    from .archive import normalize_record
    raw=dict(raw,id=job['query']['query_id'],quadrant=job['query']['quadrant'],question=job['query']['question'],
             status='native_returned',elapsed_seconds=time.monotonic()-t)
    record=normalize_record(raw,'Helicase' if job['variant']=='full' else 'Helicase-search_n1',job['run_id'])
    record['execution']={'freeze_sha256':job['freeze_sha256'],'seed':job['seed'],
        'dataset_role':job['dataset_role'],'token_count':None,'tool_calls':None,
        'matched_token_tool_budget':False,'native_termination_reason':'not_exposed_by_backend',
        'warning':'A native return can include incomplete actions; inspect worker.log and actions. Not a factual-success assertion.'}
    write_json(out/'result.json',record)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker',required=True);args=parser.parse_args()
    try:native_worker(args.worker)
    except Exception as exc:
        print(redact(f'{type(exc).__name__}: {exc}'),file=sys.stderr);sys.exit(1)
