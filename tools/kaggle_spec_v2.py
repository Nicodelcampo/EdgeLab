#!/usr/bin/env python3
"""Offline, catalog-gated aggregate jobs. No research outcomes or economic verdicts."""
from __future__ import annotations
import argparse
from datetime import date, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import traceback
import zipfile

SCHEMA = 'edgelab_kaggle_spec_v2'
HOLDOUT = '2026-10-01'
BASE_COMMIT = '617064e0b86fd2490f2834b5da731cd26aaa23ea'
SAFE = re.compile(r'^[A-Za-z0-9_-]+$')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n')


def validate(spec):
    if spec.get('schema') != SCHEMA or spec.get('mode') not in ('preflight', 'aggregate'):
        raise ValueError('unsupported schema/mode; outcomes are not implemented')
    if not SAFE.fullmatch(spec.get('run_id', '')):
        raise ValueError('unsafe run_id')
    if not isinstance(spec.get('hypothesis'), str) or not spec['hypothesis'].strip():
        raise ValueError('hypothesis required')
    if spec.get('metrics') != ['input_integrity', 'bar_conservation']:
        raise ValueError('only target-free integrity metrics supported')
    if spec.get('verdict_rule') != 'PASS_INTEGRITY_NOT_EDGE':
        raise ValueError('economic verdicts forbidden')
    if spec.get('holdout_first_trade_date') != HOLDOUT:
        raise ValueError('HOLDOUT-A3 required')
    if spec.get('frequencies_seconds') != [1, 30, 60]:
        raise ValueError('v2 requires 1s, 30s, 60s')
    if type(spec.get('max_shards')) is not int or not 1 <= spec['max_shards'] <= 32:
        raise ValueError('invalid max_shards')
    requests = spec.get('requests', [])
    if not requests:
        raise ValueError('requests required')
    for r in requests:
        a, b = date.fromisoformat(r['start']), date.fromisoformat(r['end'])
        if a > b or r['end'] >= HOLDOUT or not SAFE.fullmatch(r['instrument']):
            raise ValueError('invalid window or holdout requested')
    for name in ('edgelab_data.py', 'RESOLVER.json'):
        if not re.fullmatch('[0-9a-f]{64}', spec['catalog']['sha256'].get(name, '')):
            raise ValueError('catalog hashes required')
    for slug, ref in spec['dataset_versions'].items():
        parts = ref.split('/')
        if len(parts) != 3 or parts[1] != slug or not parts[2].isdigit() or int(parts[2]) < 1:
            raise ValueError('each dataset must have owner/slug/version pin')
    return spec


def load_catalog(spec, directory):
    validate(spec)
    d = Path(directory)
    for n, expected in spec['catalog']['sha256'].items():
        if n not in ('edgelab_data.py', 'RESOLVER.json') or digest(d / n) != expected:
            raise ValueError('catalog identity mismatch: ' + n)
    if json.loads((d / 'RESOLVER.json').read_text())['holdout_first_trade_date'] != HOLDOUT:
        raise ValueError('catalog holdout mismatch')
    modspec = importlib.util.spec_from_file_location('edgelab_data', d / 'edgelab_data.py')
    ed = importlib.util.module_from_spec(modspec)
    modspec.loader.exec_module(ed)
    return ed


def make_plan(spec, ed):
    validate(spec)
    chosen = {}
    for req in spec['requests']:
        inst = req['instrument']
        # Only the public approved-session selector; no include_rejected or alternatives.
        for row in ed.sessions(inst, req['start'], req['end']).to_dict('records'):
            key = (inst, row['date'])
            item = {k: row[k] for k in ('date', 'contract', 'dataset', 'file')}
            item['instrument'] = inst
            if row['dataset'] not in spec['dataset_versions']:
                raise ValueError('missing immutable version pin: ' + row['dataset'])
            if key in chosen and chosen[key] != item:
                raise ValueError('conflicting selection')
            chosen[key] = item
    if not chosen:
        raise ValueError('no approved sessions')
    groups = {}
    for row in chosen.values():
        groups.setdefault((row['instrument'], row['contract']), []).append(row)
    # Contract is indivisible; deterministic longest-bin assignment, then fixed ID order.
    bins = [[] for _ in range(min(spec['max_shards'], len(groups)))]
    for key in sorted(groups, key=lambda k: (-len(groups[k]), k)):
        i = min(range(len(bins)), key=lambda j: (len(bins[j]), j))
        bins[i].extend(groups[key])
    shards = [{'id': f'k{i + 1:02d}', 'sessions': sorted(rows, key=lambda r: (r['instrument'], r['contract'], r['date']))}
              for i, rows in enumerate(bins)]
    return {'schema': SCHEMA, 'spec': spec, 'base_commit': BASE_COMMIT, 'shards': shards,
            'selected_sessions': len(chosen)}


def exact_path(root, dataset, filename):
    base = Path(root).resolve() / dataset
    candidate = (base / filename).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError('unsafe data path')
    if candidate.is_file():
        return candidate
    # New Kaggle mount layout: /kaggle/input/datasets/<owner>/<slug>/...
    matches = [p for p in Path(root).rglob(Path(filename).name)
               if dataset in p.parts and p.is_file() and tuple(Path(filename).parts) == p.parts[-len(Path(filename).parts):]]
    if len(matches) != 1:
        raise FileNotFoundError(f'expected exactly one {dataset}/{filename}, got {len(matches)}')
    return matches[0]


def aggregate_frame(t, seconds):
    """Aggregate only already-selected ticks; no synthetic ticks or future fill."""
    import numpy as np
    import pandas as pd
    required = ['ts_utc_ns', 'price_ticks', 'volume', 'aggressor', 'contract', 'session_date']
    if any(c not in t for c in required) or t[required].isna().any().any():
        raise ValueError('missing/null tick fields')
    if not set(t.aggressor).issubset({'buy', 'sell', 'unclassified', 'neutral'}):
        raise ValueError('unknown aggressor label')
    if (t.volume < 0).any() or (t.ts_utc_ns.diff().dropna() < 0).any():
        raise ValueError('negative volume or unsorted ticks')
    t = t.copy()
    t['bucket_utc_ns'] = t.ts_utc_ns // (seconds * 10**9) * (seconds * 10**9)
    t['buy_volume'] = np.where(t.aggressor == 'buy', t.volume, 0)
    t['sell_volume'] = np.where(t.aggressor == 'sell', t.volume, 0)
    t['unknown_volume'] = np.where(~t.aggressor.isin(['buy', 'sell']), t.volume, 0)
    aggs = {n: (c, op) for n, c, op in [
        ('open', 'price_ticks', 'first'), ('high', 'price_ticks', 'max'),
        ('low', 'price_ticks', 'min'), ('close', 'price_ticks', 'last'),
        ('volume', 'volume', 'sum'), ('trades', 'price_ticks', 'size'),
        ('buy_volume', 'buy_volume', 'sum'), ('sell_volume', 'sell_volume', 'sum'),
        ('unknown_volume', 'unknown_volume', 'sum'),
        ('first_ts_utc_ns', 'ts_utc_ns', 'first'), ('last_ts_utc_ns', 'ts_utc_ns', 'last')]}
    # Nulls stay null: pandas GroupBy.last would silently replace a missing last quote.
    for q in ('bid_ticks', 'ask_ticks'):
        t[q] = t[q] if q in t else np.nan
        # Quote selection is vectorized below; GroupBy.last would lose nulls.
    bars = t.groupby(['session_date', 'contract', 'bucket_utc_ns'], sort=True).agg(**aggs).reset_index()
    keys = ['session_date', 'contract', 'bucket_utc_ns']
    quotes = t.groupby(keys, sort=False).tail(1)[keys + ['bid_ticks', 'ask_ticks']]
    bars = bars.merge(quotes, on=keys, how='left', validate='one_to_one')
    bars['signed_volume'] = bars.buy_volume - bars.sell_volume
    bars['available_utc_ns'] = bars.bucket_utc_ns + seconds * 10**9
    return bars


def combine_partials(frames, seconds):
    import pandas as pd
    t = pd.concat(frames, ignore_index=True)
    keys = ['session_date', 'contract', 'bucket_utc_ns']
    t = t.sort_values(keys + ['first_ts_utc_ns'], kind='stable')
    agg = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last',
           'first_ts_utc_ns': 'first', 'last_ts_utc_ns': 'last'}
    for col in ('volume', 'trades', 'buy_volume', 'sell_volume', 'unknown_volume', 'signed_volume'):
        agg[col] = 'sum'
    b = t.groupby(keys, sort=True).agg(agg).reset_index()
    quotes = t.groupby(keys, sort=False).tail(1)[keys + ['bid_ticks', 'ask_ticks']]
    b = b.merge(quotes, on=keys, how='left', validate='one_to_one')
    b['available_utc_ns'] = b.bucket_utc_ns + seconds * 10**9
    return b


def run_shard(plan, shard_id, ed, root, out):
    import pandas as pd
    import pyarrow.parquet as pq
    spec = validate(plan['spec'])
    # Refuse altered shard contents even if dates are individually legal.
    if make_plan(spec, ed) != plan:
        raise ValueError('plan differs from pinned resolver/spec')
    shard = next(s for s in plan['shards'] if s['id'] == shard_id)
    groups = {}
    for row in shard['sessions']:
        groups.setdefault((row['instrument'], row['dataset'], row['file']), []).append(row)
    # Resolve EVERY mount before reading ticks; alternatives/missing mode prohibited.
    paths = {key: exact_path(root, key[1], key[2]) for key in groups}
    results = {'status': 'PASS_INTEGRITY_NOT_EDGE', 'shard_id': shard_id, 'sources': [], 'bars': []}
    if spec['mode'] == 'preflight':
        results['sources'] = [{'dataset': k[1], 'file': k[2]} for k in paths]
        return results
    cutoff = pd.Timestamp('2026-09-30 17:00', tz='America/Chicago').tz_convert('UTC').value
    for (inst, ds, fn), selected in sorted(groups.items()):
        path = paths[(inst, ds, fn)]
        pf = pq.ParquetFile(path)
        cols = ['ts_utc_ns', 'price_ticks', 'volume', 'aggressor', 'contract']
        cols += [c for c in ('bid_ticks', 'ask_ticks') if c in pf.schema_arrow.names]
        if any(c not in pf.schema_arrow.names for c in cols):
            raise ValueError('unsupported parquet schema')
        column = pf.schema_arrow.get_field_index('ts_utc_ns')
        expected = {r['date']: r['contract'] for r in selected}
        lo = pd.Timestamp(str(date.fromisoformat(min(expected)) - timedelta(days=1)) + ' 17:00', tz='America/Chicago').value
        hi = pd.Timestamp(max(expected) + ' 17:00', tz='America/Chicago').value
        partials = {s: [] for s in spec['frequencies_seconds']}
        counts = {}; last_ts = None; accessed = []
        for i in range(pf.num_row_groups):
            st = pf.metadata.row_group(i).column(column).statistics
            # Metadata-only firewall. Never deserialize mixed/unknown holdout row groups.
            if st is None or not st.has_min_max:
                raise ValueError('timestamp statistics required for holdout firewall')
            if st.max < lo or st.min >= hi:
                continue
            if st.max >= cutoff:
                raise ValueError('row group overlaps sealed holdout; create preholdout source first')
            t = pf.read_row_group(i, columns=cols).to_pandas()
            if len(t) and ((t.ts_utc_ns.diff().dropna() < 0).any() or
                           (last_ts is not None and int(t.ts_utc_ns.iloc[0]) < last_ts)):
                raise ValueError('source ordering invalid')
            if len(t):
                last_ts = int(t.ts_utc_ns.iloc[-1])
            accessed.append(i)
            t['session_date'] = ed._session_date(t.ts_utc_ns.to_numpy())
            t = t[t.session_date.isin(expected)].copy()
            if t.empty:
                continue
            t['contract'] = t.contract.astype(str).str.replace(' ', '_', regex=False)
            if not (t.contract == t.session_date.map(expected)).all():
                raise ValueError('contract differs from approved resolver selection')
            for d, g in t.groupby('session_date'):
                n, v = counts.get(d, (0, 0))
                counts[d] = (n + len(g), v + int(g.volume.sum()))
            for seconds in partials:
                partials[seconds].append(aggregate_frame(t, seconds))
        if set(counts) != set(expected):
            raise ValueError('approved sessions missing from source')
        catalog_rows = {r['date']: r for r in ed.sessions(inst, min(expected), max(expected)).to_dict('records')}
        for day, (n, v) in counts.items():
            row = catalog_rows[day]
            if n != row.get('trades') or v != row.get('volume'):
                raise ValueError('source totals differ from pinned catalog: ' + day)
        for seconds, frames in partials.items():
            bars = combine_partials(frames, seconds)
            totals = bars.groupby('session_date')[['trades', 'volume']].sum()
            for d, nv in counts.items():
                if tuple(totals.loc[d]) != nv:
                    raise ValueError('conservation failure')
            if not (bars.volume == bars.buy_volume + bars.sell_volume + bars.unknown_volume).all():
                raise ValueError('aggressor conservation failure')
            name = f'{inst}__{ds}__{Path(fn).stem}__{seconds}s.parquet'
            bars.to_parquet(Path(out) / name, index=False)
            results['bars'].append({'file': name, 'instrument': inst, 'seconds': seconds,
                                    'rows': len(bars), 'sessions': sorted(counts), 'units': 'price_ticks',
                                    'tick_size': ed.RESOLVER['instruments'][inst]['tick_size']})
        results['sources'].append({'dataset': ds, 'version_ref': spec['dataset_versions'][ds], 'file': fn,
                                  'bytes': path.stat().st_size, 'read_row_groups': accessed,
                                  'identity': 'dataset_version_pin; raw_file_sha256_not_computed',
                                  'selected_totals': {d: {'trades': n, 'volume': v} for d, (n, v) in counts.items()}})
    return results


def package(out):
    out = Path(out)
    files = sorted(p for p in out.rglob('*') if p.is_file() and p.name not in ('manifest.json', 'output.zip', 'output.zip.sha256'))
    write_json(out / 'manifest.json', {'files': [{'path': p.relative_to(out).as_posix(), 'sha256': digest(p), 'bytes': p.stat().st_size} for p in files]})
    with zipfile.ZipFile(out / 'output.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files + [out / 'manifest.json']:
            info = zipfile.ZipInfo(p.relative_to(out).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes())
    (out / 'output.zip.sha256').write_text(digest(out / 'output.zip') + '  output.zip\n')


def execute(plan, shard_id, catalog_dir, root, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('output directory must be empty')
    write_json(out / 'plan.json', plan)
    attest = {'schema': SCHEMA, 'scope': 'infrastructure_only', 'holdout_touched': None,
              'future_price_path_accessed': False, 'first_touch_accessed': False, 'pnl_accessed': False,
              'measurement_started': False, 'runner_sha256': digest(__file__), 'base_commit': BASE_COMMIT}
    result = {'status': 'ABSTAIN', 'shard_id': shard_id}
    code = 2
    try:
        ed = load_catalog(plan['spec'], catalog_dir)
        attest['measurement_started'] = plan['spec']['mode'] == 'aggregate'
        result = run_shard(plan, shard_id, ed, root, out)
        attest['holdout_touched'] = False
        code = 0
    except Exception as exc:
        result['error'] = str(exc)
        (out / 'error.log').write_text(traceback.format_exc())
    write_json(out / 'results.json', result)
    write_json(out / 'attestation.json', attest)
    package(out)
    return code


def generate(plan, directory):
    dest = Path(directory); dest.mkdir(parents=True, exist_ok=True)
    code = Path(__file__).read_text()
    code_sha = hashlib.sha256(code.encode()).hexdigest()
    for shard in plan['shards']:
        d = dest / shard['id']; d.mkdir(exist_ok=True)
        name = plan['spec']['run_id'] + '-' + shard['id']
        refs = sorted({plan['spec']['catalog']['ref']} | {plan['spec']['dataset_versions'][r['dataset']] for r in shard['sessions']})
        # Embed actual runner bytes, not clone-at-runtime; hashes capture exactly what ran.
        entry = 'from pathlib import Path\nimport json,runpy\n'
        entry += 'Path("/kaggle/working/kaggle_spec_v2.py").write_text(' + repr(code) + ')\n'
        entry += 'api=runpy.run_path("/kaggle/working/kaggle_spec_v2.py",run_name="edgelab_embedded")\n'
        entry += 'plan=json.loads(' + repr(json.dumps(plan)) + ')\n'
        entry += 'catalogs=list(Path("/kaggle/input").rglob("edgelab_data.py"))\n'
        entry += 'catalog_dir=catalogs[0].parent if len(catalogs)==1 else Path("/missing_catalog")\n'
        entry += f'raise SystemExit(api["execute"](plan,{shard["id"]!r},catalog_dir,"/kaggle/input","/kaggle/working/evidence"))\n'
        (d / 'entry.py').write_text(entry)
        write_json(d / 'kernel-metadata.json', {'id': plan['spec']['catalog']['ref'].split('/')[0] + '/' + name,
                 'title': name, 'code_file': 'entry.py', 'language': 'python', 'kernel_type': 'script',
                 'is_private': True, 'enable_gpu': False, 'enable_internet': False, 'dataset_sources': refs})
    write_json(dest / 'generation.json', {'runner_sha256': code_sha, 'plan': plan})


def merge(plan, directories, out):
    """Verify identities/hashes/completeness BEFORE concatenating in fixed shard order."""
    import pandas as pd
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('merge output must be empty')
    by_id = {}
    for directory in directories:
        d = Path(directory)
        if json.loads((d / 'plan.json').read_text()) != plan:
            raise ValueError('different plan')
        manifest = json.loads((d / 'manifest.json').read_text())
        names = [f['path'] for f in manifest['files']]
        if not {'plan.json', 'results.json', 'attestation.json'} <= set(names):
            raise ValueError('incomplete evidence manifest')
        for f in manifest['files']:
            p = (d / f['path']).resolve()
            if not p.is_relative_to(d.resolve()) or digest(p) != f['sha256']:
                raise ValueError('artifact identity mismatch')
        result = json.loads((d / 'results.json').read_text())
        if result['status'] != 'PASS_INTEGRITY_NOT_EDGE' or result['shard_id'] in by_id:
            raise ValueError('failed/duplicate shard')
        attest = json.loads((d / 'attestation.json').read_text())
        if attest['holdout_touched'] is not False or any(attest[x] is not False for x in ('future_price_path_accessed', 'first_touch_accessed', 'pnl_accessed')):
            raise ValueError('invalid firewall attestation')
        if any(b['file'] not in names for b in result['bars']):
            raise ValueError('bar missing from manifest')
        by_id[result['shard_id']] = (d, result, attest)
    if set(by_id) != {s['id'] for s in plan['shards']}:
        raise ValueError('missing/extra shards')
    if len({a['runner_sha256'] for _, _, a in by_id.values()}) != 1:
        raise ValueError('different runner identities')
    merged = []
    for inst in sorted({r['instrument'] for s in plan['shards'] for r in s['sessions']}):
        for sec in plan['spec']['frequencies_seconds']:
            frames = []
            for sid in sorted(by_id):
                d, r, _ = by_id[sid]
                frames += [pd.read_parquet(d / b['file']) for b in r['bars'] if b['instrument'] == inst and b['seconds'] == sec]
            if not frames and plan['spec']['mode'] == 'preflight':
                continue
            t = pd.concat(frames, ignore_index=True).sort_values(['session_date', 'contract', 'bucket_utc_ns'], kind='stable')
            if t.duplicated(['session_date', 'contract', 'bucket_utc_ns']).any():
                raise ValueError('overlapping bars')
            expected = {(r['date'], r['contract']) for s in plan['shards'] for r in s['sessions'] if r['instrument'] == inst}
            if set(zip(t.session_date, t.contract)) != expected:
                raise ValueError('aggregate session coverage differs from plan')
            name = f'{inst}__{sec}s.parquet'; t.to_parquet(out / name, index=False)
            merged.append({'file': name, 'rows': len(t)})
    write_json(out / 'plan.json', plan)
    write_json(out / 'results.json', {'status': 'PASS_INTEGRITY_NOT_EDGE', 'shards': sorted(by_id), 'bars': merged})
    write_json(out / 'attestation.json', {'scope': 'infrastructure_only', 'holdout_touched': False,
               'future_price_path_accessed': False, 'first_touch_accessed': False, 'pnl_accessed': False,
               'runner_sha256': next(iter(by_id.values()))[2]['runner_sha256']})
    package(out)



def load_bars(store, instrument, start, end, seconds):
    """Read a verified merged store. Missing sessions fail instead of shrinking a sample."""
    import pandas as pd
    if date.fromisoformat(start) > date.fromisoformat(end) or end >= HOLDOUT:
        raise ValueError('invalid window/holdout')
    if seconds not in (1, 30, 60) or not SAFE.fullmatch(instrument):
        raise ValueError('invalid frequency/instrument')
    d = Path(store)
    manifest = json.loads((d / 'manifest.json').read_text())
    hashes = {x['path']: x['sha256'] for x in manifest['files']}
    name = f'{instrument}__{seconds}s.parquet'
    for n in ('plan.json', 'results.json', name):
        if n not in hashes or digest(d / n) != hashes[n]:
            raise ValueError('store artifact mismatch: ' + n)
    plan = json.loads((d / 'plan.json').read_text())
    spec = validate(plan['spec'])
    if json.loads((d / 'results.json').read_text())['status'] != 'PASS_INTEGRITY_NOT_EDGE':
        raise ValueError('store did not pass integrity')
    requests = [r for r in spec['requests'] if r['instrument'] == instrument and r['start'] <= start and r['end'] >= end]
    if not requests:
        raise ValueError('window outside materialized request; build coverage first')
    want = {(r['date'], r['contract']) for s in plan['shards'] for r in s['sessions']
            if r['instrument'] == instrument and start <= r['date'] <= end}
    t = pd.read_parquet(d / name)
    t = t[(t.session_date >= start) & (t.session_date <= end)].copy()
    if set(zip(t.session_date, t.contract)) != want or not want:
        raise ValueError('missing approved sessions in store')
    t.attrs.update(instrument=instrument, units='price_ticks', frequency_seconds=seconds,
                   catalog_identity=spec['catalog'], availability='bucket end, no within-bucket access')
    return t.reset_index(drop=True)


def main():
    p = argparse.ArgumentParser(__doc__); sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('generate'); a.add_argument('--spec', required=True); a.add_argument('--catalog', required=True); a.add_argument('--out', required=True)
    a = sub.add_parser('run'); a.add_argument('--plan', required=True); a.add_argument('--shard', required=True); a.add_argument('--catalog', required=True); a.add_argument('--root', required=True); a.add_argument('--out', required=True)
    a = sub.add_parser('merge'); a.add_argument('--plan', required=True); a.add_argument('--inputs', nargs='+', required=True); a.add_argument('--out', required=True); a.add_argument('--ledger')
    a = p.parse_args()
    if a.command == 'generate':
        spec = json.loads(Path(a.spec).read_text()); generate(make_plan(spec, load_catalog(spec, a.catalog)), a.out)
    elif a.command == 'run':
        return execute(json.loads(Path(a.plan).read_text()), a.shard, a.catalog, a.root, a.out)
    else:
        merge(json.loads(Path(a.plan).read_text()), a.inputs, a.out)
        if a.ledger:
            from kaggle_hippocampus_ingest import ingest
            receipt = ingest(a.out, a.ledger)
            write_json(Path(a.ledger).with_suffix('.receipt.json'), receipt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
