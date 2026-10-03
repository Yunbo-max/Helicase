"""Execute the archived Q4 evaluator unchanged with a recorded replacement LLM.

This is a historical-behavior reproduction, including known counting defects.
It is deliberately separate from the corrected answer-semantic evaluator.
"""
import builtins
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import sys
import types
import uuid
from .common import digest


def replay_record(source_path, record, reference, client):
    source = Path(source_path).read_bytes()
    name = '_legacy_q4_' + uuid.uuid4().hex
    module = types.ModuleType(name)
    module.__file__ = str(Path(source_path).resolve())
    original_import = builtins.__import__

    def dependency_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'veritrace.agent.core.llm_adapter':
            return types.SimpleNamespace(Message=types.SimpleNamespace)
        if name == 'dotenv':
            # Reproduction uses an explicit replacement client, never implicit env keys.
            return types.SimpleNamespace(load_dotenv=lambda: None)
        return original_import(name, globals, locals, fromlist, level)

    module.__dict__['__builtins__'] = dict(vars(builtins), __import__=dependency_import)
    sys.modules[name] = module
    calls=[];failures=[];captured={}

    class Adapter:
        def chat(self, messages, temperature):
            prompt=messages[0].content
            call={'prompt':prompt,'legacy_requested_temperature':temperature,
                  'replacement_temperature':'not exposed by Codex CLI'}
            calls.append(call)
            try:
                raw,usage,returned=client.chat_legacy(prompt)
                call.update(response=raw,usage=usage,returned_model=returned)
                return types.SimpleNamespace(content=raw)
            except Exception as exc:
                call['error']=str(exc);failures.append(str(exc));raise

    try:
        exec(compile(source,str(source_path),'exec'),module.__dict__)
        original_extract=module.extract_answer_from_report
        original_match=module.llm_set_match
        def extract(*args,**kwargs):
            value=original_extract(*args,**kwargs);captured['predicted_answer']=value;return value
        def match(pred,ref,llm):
            value=original_match(pred,ref,llm)
            captured.update(sent_predicted=pred,sent_reference=ref,matches=value)
            return value
        module.extract_answer_from_report=extract;module.llm_set_match=match
        adapter=Adapter();module._extract_llm=adapter
        result=module.evaluate_q4([record],{record['id']:{'answer':reference}},adapter)
        if failures:raise RuntimeError('Legacy transport failed; silent fallback not accepted: '+failures[0])
        pred=module.extract_entities_from_answer(captured['predicted_answer'])
        ref=module.extract_entities_from_answer(reference)
        pairs=captured.get('matches',[])
        ep=len({a for a,b in pairs})/len(pred) if pred else 0
        er=len({b for a,b in pairs})/len(ref) if ref else 0
        ef=2*ep*er/(ep+er) if ep+er else 0
        nodes=module.extract_kg_entities(record);edges=module.extract_kg_relations(record)
        density=min(1,len(edges)/len(nodes)) if nodes and edges else None
        rp,rr=(ef*(.8+.2*density),er*(.8+.2*density)) if density is not None else (.85*ep,.85*er)
        rf=2*rp*rr/(rp+rr) if rp+rr else 0
        composite=.6*ef+.4*rf
        assert result.per_question[0]['graph_f1']==round(composite,3)
        return {'source_sha256':digest(source),'original_result':asdict(result),'calls':calls,
                'predicted_answer':captured['predicted_answer'],'predicted_items':pred,'reference_items':ref,
                'sent_predicted':captured.get('sent_predicted',[]),'sent_reference':captured.get('sent_reference',[]),
                'matches':pairs,'components':{'answer_precision':ep,'answer_recall':er,'answer_f1':ef,
                'relation_proxy_precision':rp,'relation_proxy_recall':rr,'relation_proxy_f1':rf,
                'legacy_composite':composite,'structure_delta':composite-ef,'native_nodes':len(nodes),
                'native_edges':len(edges),'density':density},
                'audit':{'unknown_predicted':sorted({a for a,b in pairs}-set(pred[:30])),
                'unknown_reference':sorted({b for a,b in pairs}-set(ref[:30])),
                'many_predictions_to_one_reference':any(n>1 for n in Counter(b for a,b in set(pairs)).values()),
                'one_prediction_to_many_references':any(n>1 for n in Counter(a for a,b in set(pairs)).values()),
                'report_truncated':len(record.get('report',''))>8000,
                'predicted_items_truncated':len(pred)>30,'reference_items_truncated':len(ref)>30,
                'out_of_range':any(v<0 or v>1 for v in [ep,er,ef,rf,composite])}}
    finally:
        sys.modules.pop(name,None)
