"""Invented assertions for tests ONLY; never build real review or market approval."""
from datetime import datetime, timezone
from edgelab.data.research_data_gate import seal


def add_selection_review(certificate, manifest, root, quantities=None):
    meta = [c for c in manifest['contracts'] if c['root'] == root]
    review = {'schema': 'edgelab_reviewed_prior_challengers_v1', 'root': root,
        'calendar_evidence_sha256': 'a'*64, 'universe_evidence_sha256': 'b'*64,
        'contract_metadata_sha256': seal(sorted(meta, key=lambda c: c['contract'])),
        'universe_review': 'PASS', 'calendar_review': 'PASS', 'asof_review': 'PASS',
        'decisions': {}}
    calendar = manifest['calendar_trade_dates']
    for i, day in enumerate(calendar[1:], 1):
        prior = calendar[i-1]
        def at(d, hour):
            return datetime.strptime(str(d), '%Y%m%d').replace(hour=hour, tzinfo=timezone.utc).isoformat()
        close, opened = at(prior, 16), at(day, 0)
        covered = [c for c in meta if c['first_trade_date'] <= prior <= c['last_trade_date']]
        review['decisions'][f'{root}|{day}'] = {'evidence_sha256': 'c'*64,
            'cutoff_review': 'PASS', 'trade_date': day, 'signal_trade_date': prior,
            'previous_session_close_utc': close, 'target_session_open_utc': opened,
            'decision_cutoff_utc': opened, 'contract_metadata_available_at_utc': close, 'candidate_contracts': [c['contract'] for c in covered]}
        for c in covered:
            key = f"{root}|{c['contract']}|{prior}"
            s = certificate['sessions'].setdefault(key, {})
            s.update(status='PASS', complete_session=True, available_at_utc=close, evidence_sha256='d'*64)
            if quantities is not None: s['trade_quantity'] = quantities[(c['contract'], prior)]
    certificate['selection_review'] = review
