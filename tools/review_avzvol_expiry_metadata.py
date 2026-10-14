#!/usr/bin/env python3
"""Metadata-only comparison of pinned MNQ summaries to loaded official expiry table."""
from pathlib import Path
from collections import Counter
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ['MNQ_09-25', 'MNQ_12-25', 'MNQ_03-26', 'MNQ_06-26', 'MNQ_09-26', 'MNQ_12-26']
RESOLVER_SHA = '9b21eeff751d4397465fcc6831ea615b7dd401a5605a5997f52c8bfd9248117c'
CME_URL = 'https://www.cmegroup.com/trading/equity-index/rolldates.html'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def parse_cme_reference(document):
    require(document.get('url') == CME_URL, 'wrong official source URL')
    text = document['text']
    found = {}
    for line in text.splitlines():
        match = re.fullmatch(r'\|(2025|2026) \|(\d+) \|(\d+/\d+) \|(\d+/\d+) \|\d+/\d+ \|\d+/\d+ \|', line.strip())
        if match:
            year, month, expiry, roll = match.groups()
            key = f'MNQ_{int(month):02d}-{year[2:]}'
            require(key not in found, 'ambiguous official expiry row')
            e_month, e_day = map(int, expiry.split('/')); r_month, r_day = map(int, roll.split('/'))
            require(e_month == r_month == int(month), 'official expiry month mismatch')
            found[key] = {'expiry': date(int(year), e_month, e_day).isoformat(),
                          'customary_roll': date(int(year), r_month, r_day).isoformat()}
    require(set(CONTRACTS) <= set(found), 'incomplete official reference')
    return {c: found[c] for c in CONTRACTS}

def third_friday(year, month):
    d = date(year, month, 1)
    return date(year, month, 1 + (4 - d.weekday()) % 7 + 14)

def summarize(contract, records, official, selected):
    require(isinstance(records, dict) and records, 'empty/nonobject source summary')
    expiry = date.fromisoformat(official['expiry'])
    flagged = []
    count = 0
    for label, record in records.items():
        dt = datetime.strptime(label, '%Y%m%d').date()
        require(dt.isoformat() < '2026-10-01', 'reserved summary date')
        n = record['ticks']
        require(type(n) is int and n > 0 and type(record['first']) is int and type(record['last']) is int,
                'unknown metadata count or timestamp')
        require(record['first'] <= record['last'] < 1790805600000000000, 'unknown/reserved UTC endpoint')
        count += n
        if dt > expiry:
            endpoints = []
            for field in ['first', 'last']:
                # integer seconds plus explicit nanosecond remainder, never float-rounding ns
                seconds, ns = divmod(record[field], 1_000_000_000)
                ct = datetime.fromtimestamp(seconds, timezone.utc).astimezone(ZoneInfo('America/Chicago'))
                endpoints.append(ct.strftime('%Y-%m-%dT%H:%M:%S') + f'.{ns:09d}' + ct.strftime('%z'))
            flagged.append({'contract': contract, 'declared_date': dt.isoformat(), 'declared_ticks': n,
                            'official_expiry_date': expiry.isoformat(), 'first_ct': endpoints[0],
                            'last_ct': endpoints[1], 'approved_in_resolver_for_this_contract':
                            (dt.isoformat(), contract) in selected,
                            'cause': 'UNKNOWN_NEEDS_UPSTREAM_EXPORT_TRACE', 'excluded': False})
    # Independent count selection via comprehension (not loop accumulator).
    independent = sum(record['ticks'] for label, record in records.items()
                      if datetime.strptime(label, '%Y%m%d').date() > expiry)
    require(independent == sum(x['declared_ticks'] for x in flagged), 'post-expiry count mismatch')
    generic = third_friday(expiry.year, expiry.month)
    return {'contract': contract, 'source_date_records': len(records), 'declared_ticks_total': count,
            'official_reference': official, 'generic_third_friday': generic.isoformat(),
            'generic_rule_agrees': generic == expiry, 'flagged_date_records': flagged}

def run(inventory, resolver, cme_source, out_dir):
    require(digest(resolver) == RESOLVER_SHA, 'resolver pin mismatch')
    pins = json.loads((ROOT / 'config/research/avzvol_mnq_metadata_review_20261010.json').read_text())['source_summary_metadata_pins']
    pins = {p['contract']: p for p in pins}
    inv = json.loads(Path(inventory).read_text());paths = {x['contract']: Path(x['file']) for x in inv}
    require(len(inv) == len(paths) == 6 and set(paths) == set(CONTRACTS), 'exact six-summary universe required')
    for c, p in paths.items():
        require(digest(p) == pins[c]['measured_sha256'] and p.stat().st_size == pins[c]['downloaded_bytes'], 'summary pin mismatch')
    official = parse_cme_reference(json.loads(Path(cme_source).read_text()))
    data = json.loads(Path(resolver).read_text())['instruments']['MNQ']
    sessions = data['sessions']
    selected = {(s['date'], s['contract']) for s in sessions if s['approved']}
    require(len(selected) == data['approved_sessions'] == 261, 'selected declaration count mismatch')
    files = [summarize(c, json.loads(paths[c].read_text()), official[c], selected) for c in CONTRACTS]
    raw_review = json.loads((ROOT / 'config/research/avzvol_mnq_raw_quality_review_20261010.json').read_text())
    prior_counts = {f['candidate_contract']: f['structural_audit']['rows'] for f in raw_review['files']}
    require(all(f['declared_ticks_total'] == prior_counts[f['contract']] for f in files), 'summary vs prior raw QA row count mismatch')
    flagged = [x for f in files for x in f['flagged_date_records']]
    direct = Counter()
    for f in files:
        for x in f['flagged_date_records']:
            direct[x['contract']] += x['declared_ticks']
    require(sum(direct.values()) == sum(x['declared_ticks'] for x in flagged), 'independent accounting mismatch')
    approved = sorted((s for s in sessions if s['approved']), key=lambda s: s['date'])
    rolls = []
    for previous, current in zip(approved, approved[1:]):
        if previous['contract'] != current['contract']:
            ref = official[previous['contract']]['customary_roll']
            rolls.append({'from': previous['contract'], 'to': current['contract'],
                          'last_approved_old_date': previous['date'], 'first_approved_new_date': current['date'],
                          'official_customary_roll_date': ref,
                          'calendar_days_later_than_customary': (date.fromisoformat(current['date']) - date.fromisoformat(ref)).days,
                          'difference_alone_establishes_selection_error': False, 'd1_liquidity_proven': False})
    require(len(rolls) == 5, 'unexpected declared roll universe')
    totals = {'summary_files': 6, 'source_date_records': sum(f['source_date_records'] for f in files),
              'declared_ticks': sum(f['declared_ticks_total'] for f in files),
              'post_expiry_date_records': len(flagged), 'post_expiry_declared_ticks': sum(direct.values()),
              'post_expiry_date_records_selected_by_resolver': sum(x['approved_in_resolver_for_this_contract'] for x in flagged),
              'post_expiry_selected_declared_ticks': sum(x['declared_ticks'] for x in flagged if x['approved_in_resolver_for_this_contract']),
              'generic_expiry_exceptions': sum(not f['generic_rule_agrees'] for f in files)}
    evidence = {'schema': 'edgelab_avzvol_official_expiry_metadata_review_v1',
                'status': 'PARTIAL_EXTERNAL_REFERENCE_REVIEW_SOURCE_CERTIFICATION_OPEN',
                'source_ref': CME_URL, 'official_loaded_source_sha256': digest(cme_source),
                'source_is_current_not_historical_available_at_attestation': True,
                'resolver_sha256': RESOLVER_SHA, 'recipe_sha256': digest(__file__),
                'metadata_pin_reference_sha256': digest(ROOT / 'config/research/avzvol_mnq_metadata_review_20261010.json'),
                'prior_raw_qa_reference_sha256': digest(ROOT / 'config/research/avzvol_mnq_raw_quality_review_20261010.json'),
                'source_metadata_pins': [{k:p[k] for k in ['contract','artifact','measured_sha256','downloaded_bytes']} for p in pins.values()],
                'totals': totals, 'files': files, 'resolver_rolls': rolls,
                'independent_count_checks_completed': True,
                **{k:False for k in ['raw_tick_payload_read','price_payload_read','outcome_exports_read','new_market_outcomes_computed',
                 'economic_outcomes_computed','holdout_payload_read','source_quality_certified','full_exchange_calendar_certified',
                 'source_clock_certified','liquidity_selection_certified','research_release_authorized','source_rows_excluded','historical_outputs_modified']}}
    out = Path(out_dir);out.mkdir(parents=True, exist_ok=False)
    (out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return evidence

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ['inventory','resolver','cme-source','out-dir']: p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--allow-pinned-metadata-expiry-review',action='store_true',required=True)
    a=p.parse_args()
    try:
        e=run(a.inventory,a.resolver,a.cme_source,a.out_dir);print(json.dumps(e['totals']))
        for f in e['files']:
            for x in f['flagged_date_records']:print(json.dumps(x))
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'STOP','reason':str(exc)}));raise SystemExit(2)

if __name__=='__main__':main()
