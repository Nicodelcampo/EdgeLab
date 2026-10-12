"""Explicit, signed-review-gated LOCAL technical delivery to canonical Brain.
No live ledger path/key is configured. Uses canonical APIs; no scientific text.
Locks outbox through destination append+ack. Retry verifies destination payloads
and ancestor anchors; a torn canonical tail is quarantined, never overwritten.
"""
import json
from dataclasses import asdict
from pathlib import Path
from .learning_outbox import _json, _draft, _observation
from .post_run import _id, _sha
from .store import digest, ZERO
from .signed_authority import verify_signed

REVIEW_FIELDS = {'schema', 'principal', 'proposer', 'review_id', 'issued_at',
                 'expires_at', 'destination_id', 'draft_key', 'draft_sha256',
                 'envelope_sha256', 'custody_receipt_sha256',
                 'anchor_records', 'anchor_tip', 'decision'}


def deliver_reviewed(outbox, ledger_path, signed_review, *, trusted_keys,
                     destination_id, expected_outbox_tip, expected_ledger_tip,
                     expected_proposer, now, after_destination=None):
    """after_destination is a failure-injection hook for tests, not a retry loop.
    Local host must externally map destination_id/path and supply a fresh witness
    tip after a crash. A valid old prefix alone never establishes latestness.
    """
    _id(destination_id); _id(expected_proposer); _sha(expected_outbox_tip); _sha(expected_ledger_tip)
    v = verify_signed(signed_review, trusted_keys=trusted_keys, role='TECHNICAL_REVIEW', now=now)
    p = v['payload']
    if set(p) != REVIEW_FIELDS or p['schema'] != 'research_ops_technical_review_v1':
        raise ValueError('closed technical-only review required')
    for k in ('principal', 'proposer', 'review_id', 'destination_id'): _id(p[k])
    for k in ('draft_key', 'draft_sha256', 'envelope_sha256', 'custody_receipt_sha256', 'anchor_tip'): _sha(p[k])
    if p['proposer']!=expected_proposer or p['principal'] == expected_proposer or p['decision'] != 'APPROVE_TECHNICAL_RECORD_ONLY':
        raise ValueError('independent technical-only review required')
    if p['destination_id'] != destination_id or type(p['anchor_records']) is not int or p['anchor_records'] < 0:
        raise ValueError('destination/ancestor binding required')
    path = Path(ledger_path)
    if path.is_symlink() or not path.parent.is_dir() or path.resolve() == outbox.path.resolve():
        raise ValueError('trusted separate canonical ledger path required')
    # A cooperative delivery lock serializes adapters. Core locks additionally
    # reject stale views when a different canonical writer appends concurrently.
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus, _exclusive_lock, ledger_record_hashes
    from edgelab.edge_brain.hippocampus import AnalysisEpisode, StepExecution, LessonCandidate
    with outbox.transaction() as db, _exclusive_lock(path.with_name(path.name+'.delivery')):
        outbox._verify(db, expected_outbox_tip)
        row = db.execute('SELECT * FROM outbox_drafts WHERE key=?', (p['draft_key'],)).fetchone()
        if row is None or row['status'] not in ('REVIEW_PENDING', 'DELIVERED'):
            raise ValueError('pending/delivered non-invalidated draft required')
        draft = _json(row['body'])
        if row['hash'] != p['draft_sha256'] or draft['envelope_sha256'] != p['envelope_sha256']:
            raise ValueError('review does not bind this exact draft')
        obs = _observation(draft['observation'])
        key, raw, pin = _draft(draft['provider'], obs, draft['envelope_sha256'])
        if key != p['draft_key'] or raw != row['body'] or pin != row['hash']:
            raise ValueError('draft reconstruction mismatch')
        brain = DurableHippocampus(path, expected_tip_hash=expected_ledger_tip)
        hashes = ledger_record_hashes(path) if path.exists() else []
        n = p['anchor_records']
        if n > len(hashes) or (hashes[n-1] if n else ZERO) != p['anchor_tip']:
            raise ValueError('external ancestor anchor does not hold')
        if row['status']=='DELIVERED':
            prior = [_json(x[0])['payload'] for x in db.execute(
                'SELECT body FROM outbox_events ORDER BY seq')
                if _json(x[0])['kind']=='DELIVERED' and _json(x[0])['key']==key]
            if len(prior)!=1 or prior[0]['review_sha256']!=v['receipt_sha256']:
                raise ValueError('delivery review conflict')
            if prior[0]['destination_id']!=destination_id or prior[0]['ledger_tip'] not in hashes:
                raise ValueError('acknowledged destination history is absent; no reconstruction after ack')
        # No outcome rates, candidates, source text or instructions are accepted.
        eid, sid, lid = ('ROE_'+key, 'ROS_'+key, 'ROL_'+key)
        if any(x in brain.invalidations for x in (eid, sid, lid, obs.receipt_sha256)):
            raise ValueError('invalidated canonical delivery/source cannot be reused')
        episode = AnalysisEpisode(eid, 'Reviewed target-free technical closeout',
                                  status='COMPLETED_UNADJUDICATED',
                                  recorded_by='research_ops_signed_delivery',
                                  outcomes_inspected=False)
        metrics = {k:asdict(obs)[k] for k in (
            'state', 'failure', 'integrity', 'wall_seconds', 'peak_rss_bytes',
            'expected_units', 'completed_units', 'source_sha256', 'selection_sha256',
            'scientific_protocol_sha256', 'engine_build_sha256', 'manifest_sha256',
            'receipt_sha256')}
        metrics.update(draft_sha256=pin, envelope_sha256=draft['envelope_sha256'],
                       custody_receipt_sha256=p['custody_receipt_sha256'])
        metrics['stages'] = [list(x) for x in obs.stages]
        step = StepExecution(sid, eid, 0, 'REGISTER_TECHNICAL_CLOSEOUT', 'reviewed_closeout',
                             status='COMPLETED', input_params=metrics,
                             output_summary='Technical record only; no edge or optimization adoption.')
        lesson = LessonCandidate(lid, eid,
            'Review technical costs and failures before proposing one bounded parity-preserving benchmark; retain baseline until separately authorized.',
            evidence_record_ids=[sid], confidence='LOW', status='PROPOSED', scope='OPERATIONAL')
        # Prefix-idempotent destination protocol. Every existing partial payload
        # must equal generated bytes; conflicting same-ID records fail closed.
        old = brain.memory.episodes.get(eid)
        if old is not None:
            if any(x!=sid for x in old.step_ids):
                raise ValueError('unexpected records in reserved delivery episode')
            actual = asdict(old); actual['step_ids'] = []
            if actual != asdict(episode): raise ValueError('destination episode conflict')
        else:
            brain.register_episode(episode)
        for obj, collection, method in (
            (step, brain.memory.steps[eid], brain.record_step),
            (lesson, brain.memory.lessons[eid], brain.record_lesson)):
            ident = getattr(obj, 'step_id', None) or obj.lesson_id
            if any((getattr(x,'step_id',None) or getattr(x,'lesson_id',None))!=ident for x in collection):
                raise ValueError('unexpected record in reserved delivery namespace')
            matches = [x for x in collection if (getattr(x, 'step_id', None) or getattr(x, 'lesson_id', None)) == ident]
            if len(matches) > 1 or (matches and asdict(matches[0]) != asdict(obj)):
                raise ValueError('destination payload conflict')
            if not matches: method(obj)
        dependency=dict(source_id=lid,target_id=obs.receipt_sha256,relation='DEPENDS_ON')
        if dependency not in brain.dependencies:
            brain.record_dependency(**dependency)
        # Verify durable replay before the local ack. Crash here leaves pending;
        # a signed retry with fresh external witness can recover without duplicates.
        tip = brain.verify()
        ack = dict(destination_id=destination_id, episode_id=eid, lesson_id=lid,
                   draft_sha256=pin, review_sha256=v['receipt_sha256'],
                   ledger_tip=tip)
        if after_destination is not None: after_destination()
        if row['status'] == 'REVIEW_PENDING':
            db.execute("UPDATE outbox_drafts SET status='DELIVERED' WHERE key=?", (key,))
            outbox._event(db, 'DELIVERED', key, ack)
        return dict(status='DELIVERED_LOCAL_TECHNICAL_PROPOSED_LOW',ack=ack,
                    outbox=outbox._verify(db),source_certified=False,
                    scientific_outcomes_written=False,activation_allowed=False,
                    execution_allowed=False,remote_durability_attested=False)