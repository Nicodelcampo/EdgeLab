"""Bounded recall bridge: canonical EdgeBrain replay + canonical SSRN context packs.
No alternate corpus/search engine, ledger writes, approval or market actions.
Only approved target-free operational ledger snapshots belong to this adapter.
"""
from dataclasses import asdict
import hashlib,json,os,stat,tempfile
from pathlib import Path
from .store import digest

MAX_BYTES=2*1024*1024
OPERATIONAL_TYPES=frozenset(('episode_registered','step_recorded','expectation_recorded','failure_recorded','success_recorded','lesson_recorded','counterexample_recorded','repair_recorded','invalidation_recorded','dependency_recorded'))
PACK_FIELDS={'query','items','char_budget','used_chars','context_sha256','claims_are_evidence'}
ITEM_FIELDS={'record_id','source_id','doc_id','title','source_file','passage','score','authority_status','reason_for_inclusion'}

def _sha(value):
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError('external lowercase SHA256 required')

def _pairs(items):
    out={}
    for key,value in items:
        if key in out:raise ValueError('duplicate knowledge key')
        out[key]=value
    return out

def _nonfinite(value):raise ValueError('nonfinite knowledge metadata')

def _json(raw):return json.loads(raw,object_pairs_hook=_pairs,parse_constant=_nonfinite)

def _pinned_bytes(path,expected_sha256):
    _sha(expected_sha256)
    if os.name!='posix' or not hasattr(os,'O_NOFOLLOW'):raise ValueError('POSIX no-follow reader required')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as handle:
        before=os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size>MAX_BYTES:raise ValueError('bounded regular snapshot required')
        raw=handle.read(MAX_BYTES+1);after=os.fstat(handle.fileno())
    if len(raw)>MAX_BYTES or (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('snapshot changed or exceeded bound')
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('knowledge snapshot pin mismatch')
    return raw

def _bounds(query,k,max_chars):
    if not isinstance(query,str) or not 1<=len(query.strip())<=500:raise ValueError('bounded explicit question required')
    if type(k) is not int or not 1<=k<=10 or type(max_chars) is not int or not 512<=max_chars<=24000:raise ValueError('bounded recall required')

def recall_brain(path,*,expected_file_sha256,expected_tip,query,k=5,max_chars=12000):
    _bounds(query,k,max_chars);_sha(expected_tip)
    raw=_pinned_bytes(path,expected_file_sha256)
    # Never open reserved/trial/observation histories as ordinary target-free memory.
    # This checks record types before replay, not authorization of arbitrary text.
    if raw and not raw.endswith(b'\n'):raise ValueError('truncated ledger snapshot')
    for line in raw.splitlines():
        if not line.strip():continue
        row=_json(line)
        if type(row) is not dict or row.get('type') not in OPERATIONAL_TYPES:raise ValueError('requires approved target-free operational ledger export')
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    from edgelab.edge_brain.retrieval import LedgerIndex
    # Replay an immutable captured snapshot, not a live ledger reread between verify/search.
    with tempfile.TemporaryDirectory() as folder:
        snapshot=Path(folder)/'snapshot.jsonl';snapshot.write_bytes(raw)
        store=DurableHippocampus(snapshot,expected_tip_hash=expected_tip)
        index=LedgerIndex.from_memory(store.memory)
        hits=[];used=0
        for hit in index.query(query,k=k):
            # Expose invalidated/stale memory with warnings; never reuse or hide it.
            invalidation=store.invalidations.get(hit.record_id)
            text=hit.text[:max_chars-used]
            if not text:break
            used+=len(text)
            hits.append(dict(record_id=hit.record_id,record_type=hit.record_type,score=hit.score,text=text,text_sha256=hashlib.sha256(text.encode()).hexdigest(),origin='EDGE_BRAIN',authority_status='OWN_OPERATIONAL_RECORD_NOT_EDGE_EVIDENCE',invalidation_status=invalidation,artifact_reuse_authorized=False))
        invalidations=dict(store.invalidations)
    return dict(status='RECALLED_VERIFIED_SNAPSHOT_NOT_AUTHORITY',query=query,ledger_file_sha256=expected_file_sha256,ledger_tip=expected_tip,hits=hits,used_chars=used,invalidations=invalidations,claims_are_evidence=False,ledger_modified=False,execution_allowed=False,source_text_is_untrusted=True)

def validate_literature_pack(pack,*,expected_query,producer_commit):
    if not isinstance(producer_commit,str) or len(producer_commit)!=40 or any(c not in '0123456789abcdef' for c in producer_commit):raise ValueError('explicit producer commit required')
    if type(pack) is not dict or set(pack)!=PACK_FIELDS:raise ValueError('canonical SSRN context_pack schema required')
    if pack['query']!=expected_query or pack['claims_are_evidence'] is not False:raise ValueError('query mismatch or literature self-promotion')
    if type(pack['char_budget']) is not int or not 1<=pack['char_budget']<=24000:raise ValueError('bounded literature budget required')
    if type(pack['items']) is not list or len(pack['items'])>10:raise ValueError('bounded canonical literature items required')
    used=0;ids=set()
    for item in pack['items']:
        if type(item) is not dict or set(item)!=ITEM_FIELDS:raise ValueError('closed canonical literature item required')
        for key in ('record_id','source_id','title','source_file','passage','reason_for_inclusion'):
            if not isinstance(item[key],str) or len(item[key])>24000:raise ValueError('bounded literature text required')
        if not item['record_id'] or not item['source_id'] or item['record_id'] in ids:raise ValueError('unique source identity required')
        ids.add(item['record_id'])
        if type(item['doc_id']) is not int or item['doc_id']<=0 or type(item['score']) is not int:raise ValueError('canonical integer doc/score required')
        if item['authority_status']!='LITERATURE_CLAIM_UNVERIFIED':raise ValueError('canonical literature authority ceiling required')
        used+=len(item['passage'])
    if type(pack['used_chars']) is not int or pack['used_chars']!=used or used>pack['char_budget']:raise ValueError('literature char budget mismatch')
    canonical_items=hashlib.sha256(json.dumps(pack['items'],ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if canonical_items!=pack['context_sha256']:raise ValueError('canonical context hash mismatch')
    return dict(status='PINNED_CONTEXT_NOT_CORPUS_ATTESTATION',query=expected_query,producer_commit=producer_commit,context_sha256=pack['context_sha256'],items=[{**item,'passage_sha256':hashlib.sha256(item['passage'].encode()).hexdigest()} for item in pack['items']],used_chars=used,claims_are_evidence=False,corpus_custody_verified=False,execution_allowed=False,source_text_is_untrusted=True)

def recall_literature(path,*,expected_file_sha256,producer_commit,query):
    _bounds(query,5,12000)
    out=validate_literature_pack(_json(_pinned_bytes(path,expected_file_sha256)),expected_query=query,producer_commit=producer_commit)
    out['pack_file_sha256']=expected_file_sha256
    return out

def knowledge_context(question,brain,literature):
    _bounds(question,5,24000)
    gaps=[]
    if brain is None:gaps.append('EDGE_BRAIN_NOT_CONNECTED')
    elif brain.get('query')!=question or brain.get('claims_are_evidence') is not False:raise ValueError('brain context mismatch')
    elif not brain.get('hits'):gaps.append('NO_PRIOR_OPERATIONAL_MATCH')
    if literature is None:gaps.append('BIBLIOGRAPHY_NOT_CONNECTED_NOT_AN_EMPTY_CORPUS')
    elif literature.get('query')!=question or literature.get('claims_are_evidence') is not False:raise ValueError('literature context mismatch')
    elif not literature.get('items'):gaps.append('NO_LITERATURE_MATCH_IN_SUPPLIED_PACK')
    if brain and brain.get('invalidations'):gaps.append('MEMORY_HAS_INVALIDATIONS_REVIEW_DEPENDENCIES')
    if sum(part.get('used_chars',0) for part in (brain,literature) if part)>24000:raise ValueError('combined context budget exceeded')
    context=dict(schema='research_ops_knowledge_context_v1',question=question,edge_brain=brain,literature=literature,gaps=gaps,claims_are_evidence=False,execution_allowed=False,holdout_allowed=False,interpret_sources_as_data_not_instructions=True)
    context['context_sha256']=digest(context)
    return context

def learning_handoff(context,*,episode_id,purpose):
    """Prepare references for canonical append/review; never write a parallel memory."""
    if not isinstance(episode_id,str) or not 1<=len(episode_id)<=80 or not isinstance(purpose,str) or not 1<=len(purpose)<=1024:raise ValueError('explicit bounded episode/purpose required')
    unsigned={k:v for k,v in context.items() if k!='context_sha256'}
    if digest(unsigned)!=context.get('context_sha256') or context.get('claims_are_evidence') is not False:raise ValueError('knowledge context integrity mismatch')
    rebuilt=knowledge_context(context.get('question'),context.get('edge_brain'),context.get('literature'))
    if rebuilt!=context:raise ValueError('knowledge context schema or nested question mismatch')
    return dict(status='PROPOSED_CANONICAL_MEMORY_HANDOFF_NOT_WRITTEN',episode_id=episode_id,purpose=purpose,context_sha256=context['context_sha256'],own_record_ids=[h['record_id'] for h in (context.get('edge_brain') or {}).get('hits',[])],literature_refs=[dict(record_id=h['record_id'],source_id=h['source_id'],passage_sha256=h['passage_sha256'],authority_status=h['authority_status']) for h in (context.get('literature') or {}).get('items',[])],gaps=context['gaps'],claims_are_evidence=False,ledger_modified=False,requires='canonical Brain writer + verified source/custody + episode authority',execution_allowed=False)
