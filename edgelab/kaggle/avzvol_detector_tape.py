"""Pinned legacy detector replay with immutable creation/block observation tape.

Mathematical replay of DECLARED arrays; not a reader, census or quality authority.
Independent lineage, campaign and data gates must precede ANY market-derived input.
The bundled smoke uses invented data only. No outcomes, final zone states or match.
"""
from __future__ import annotations
import ast
from collections import defaultdict
from datetime import date
import hashlib
import math
from importlib.resources import files
from types import SimpleNamespace

SOURCE_NOTEBOOK_SHA256 = '58e81f5cf440921a88f164ae3e974709f7296d130f22ecb9271c06fb369ad310'
FIXTURE_SHA256 = '93ef7966589c278c1880d3f89365f63de23484be9147cdba8aa4d19eafdd7b0a'
CREATION_KEYS = ('bar', 'end_ns', 'low_tick', 'high_tick', 'levels', 'score', 'thresh', 'samples')

class DetectorTapeError(ValueError):
    pass


def _source():
    raw = files('edgelab.kaggle').joinpath('_avzvol_legacy_detector.py.txt').read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise DetectorTapeError('bundled pure source pin mismatch')
    tree = ast.parse(raw.decode())
    functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if functions != {'run', '_pct', '_racimo'}:
        raise DetectorTapeError('unexpected pure source functions')
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            continue
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'DEFAULTS'):
            raise DetectorTapeError('unexpected pure source top-level node')
    if any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)):
        raise DetectorTapeError('pure source cannot import loaders or outcomes')
    return tree


def _namespace(instrumented=False, emit_zone=None, emit_block=None):
    # Optional math dependencies imported only when the replay is requested.
    import numpy as np
    import pandas as pd
    tree = _source()
    if instrumented:
        class Hooks(ast.NodeTransformer):
            hits_zone = 0
            hits_block = 0
            def visit_Expr(self, node):
                call = node.value
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                        and call.func.attr == 'append' and isinstance(call.func.value, ast.Name)):
                    name = call.func.value.id
                    if name == 'zones':
                        self.hits_zone += 1
                        return [node, ast.parse('_emit_zone(z)').body[0]]
                    if name == 'blocks':
                        self.hits_block += 1
                        return [node, ast.parse('_emit_block(b, nl, best, bk, sess_idx, p, hist)').body[0]]
                return node
        hooks = Hooks()
        tree = hooks.visit(tree)
        if (hooks.hits_zone, hooks.hits_block) != (1, 1):
            raise DetectorTapeError('pinned hook locations changed')
        ast.fix_missing_locations(tree)
    env = {'np': np, 'pd': pd, 'defaultdict': defaultdict,
           '_emit_zone': emit_zone, '_emit_block': emit_block}
    exec(compile(tree, 'pinned-avzvol-pure-detector', 'exec'), env)
    return env


def legacy_parameters():
    """Exact historical defaults plus ZP2 overrides, NOT scientific approval."""
    env = _namespace()
    return {**env['DEFAULTS'], 'ob_away_heights': 6.0, 'ob_max_inside_pct': 4.0,
            'racimo_min': 0, 'racimo_bars': 500, 'racimo_altura_ticks': 30}


def replay_declared_detector(bars, footprints, sessions, *, params,
                             holdout_start, utc_cutoff_ns):
    """Instrument the exact pure run; never pass its mutable final states onward.

    Params must equal the historical full ZP2 parameter set. Sessions and clocks
    are caller declarations, not independent truth. Prior calibration is recorded
    for every complete block; <3 levels retains an UNKNOWN actual threshold,
    without changing the historical detection/control flow/cache. Incomplete
    tails are explicit, not padded. A label cannot disappear then recur.
    UTC and date bounds are metadata guards, not authority to bypass raw gates.
    """
    import numpy as np
    import pandas as pd
    expected_params = legacy_parameters()
    if (not isinstance(params, dict) or params != expected_params
            or any(type(params[k]) is not type(v) for k, v in expected_params.items())):
        raise DetectorTapeError('exact historical ZP2 parameters required')
    try:
        reserved = date.fromisoformat(holdout_start)
    except (ValueError, TypeError) as exc:
        raise DetectorTapeError('explicit ISO holdout required') from exc
    if holdout_start != reserved.isoformat():
        raise DetectorTapeError('noncanonical holdout date')
    if type(utc_cutoff_ns) is not int or utc_cutoff_ns <= 0:
        raise DetectorTapeError('explicit positive UTC cutoff required')
    names = ('close_t', 'low_t', 'high_t', 'end_ns')
    arrays = {k: np.asarray(getattr(bars, k)) for k in names}
    n = len(arrays['close_t'])
    if n == 0 or any(a.ndim != 1 or len(a) != n or a.dtype.kind not in 'iu' for a in arrays.values()):
        raise DetectorTapeError('nonempty aligned integer bar declarations required')
    end = arrays['end_ns']
    if np.any(end[1:] < end[:-1]) or np.any(end >= utc_cutoff_ns):
        raise DetectorTapeError('retrograde or reserved UTC bar declarations')
    if (np.any(arrays['high_t'] < arrays['low_t'])
            or np.any(arrays['close_t'] < arrays['low_t'])
            or np.any(arrays['close_t'] > arrays['high_t'])):
        raise DetectorTapeError('inverted bar geometry')
    if len(sessions) != n:
        raise DetectorTapeError('aligned session declarations required')
    labels, seen, spans = [], set(), []
    for i, value in enumerate(sessions):
        try:
            d = date.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise DetectorTapeError('canonical session date required') from exc
        if value != d.isoformat() or d >= reserved:
            raise DetectorTapeError('noncanonical or reserved session')
        if i == 0 or value != sessions[i-1]:
            if value in seen or (labels and value <= labels[-1]):
                raise DetectorTapeError('recurrent or unordered declared session')
            seen.add(value); labels.append(value); spans.append([i, i])
        spans[-1][1] = i
    offsets = np.asarray(footprints.offsets)
    ticks = np.asarray(footprints.ticks)
    vols = np.asarray(footprints.vols)
    if (offsets.ndim != 1 or offsets.dtype.kind not in 'iu' or len(offsets) != n+1
            or offsets[0] != 0 or np.any(offsets[1:] < offsets[:-1])
            or offsets[-1] != len(ticks) or len(ticks) != len(vols)
            or ticks.ndim != 1 or vols.ndim != 1 or ticks.dtype.kind not in 'iu'
            or vols.dtype.kind not in 'iuf' or np.any(~np.isfinite(vols)) or np.any(vols < 0)):
        raise DetectorTapeError('invalid declared footprint CSR')
    for i in range(n):
        t = ticks[offsets[i]:offsets[i+1]]
        if np.any(t < arrays['low_t'][i]) or np.any(t > arrays['high_t'][i]):
            raise DetectorTapeError('footprint outside declared bar range')
    # Geometry/schema checking is not source/bar-building parity certification.
    creations, tape = [], []
    counts = defaultdict(int)
    env = None
    def emit_zone(z):
        snapshot = {k: z[k] for k in CREATION_KEYS}
        if any(not math.isfinite(float(snapshot[k])) for k in ['score', 'thresh']):
            raise DetectorTapeError('nonfinite detector creation score/threshold')
        snapshot['session'] = sessions[z['bar']]
        snapshot['available_bar'] = z['bar']
        creations.append(snapshot)
        counts[z['bar']] += 1
    def emit_block(b, nl, best, bucket, idx, p, hist):
        prior = hist.get(bucket, [])
        scores = np.sort(np.array([x for _s, x in prior], dtype=float))
        threshold = env['_pct'](scores, p['detection_percentile']/100.0) if len(scores) >= p['min_samples'] else -1.0
        if not math.isfinite(threshold) or not math.isfinite(float(best)):
            raise DetectorTapeError('nonfinite detector calibration/score')
        derived_threshold = float(threshold)
        # Do not pretend the original threshold branch ran with <3 levels.
        observed_threshold = derived_threshold if int(nl) >= 3 else None
        baseline = labels[max(s for s, _x in prior)] if prior else None
        row = {'session': sessions[b], 'block_end_bar': int(b), 'available_bar': int(b),
            'threshold': observed_threshold, 'calibration_samples': len(scores),
            'baseline_last_session': baseline, 'detected_zone_count': counts[b]}
        tape.append({'observation': row, 'session_first_bar': spans[idx][0],
            'block_first_bar': int(b)-p['window_bars']+1,
            'first_bar_end_ns': int(end[b-p['window_bars']+1]),
            'block_end_ns': int(end[b]),
            'full_block_wall_duration_verified': False,
            'bucket': int(bucket), 'distinct_price_levels': int(nl),
            'historical_best_score': float(best),
            'derived_prior_threshold': derived_threshold,
            'historical_threshold_branch_executed': int(nl) >= 3,
            'detector_ready_as_declared': int(nl) >= 3 and len(scores) >= p['min_samples'] and derived_threshold > 0})
    env = _namespace(True, emit_zone, emit_block)
    # The returned final states/clusters deliberately stay local and unused.
    legacy = env['run'](bars, footprints, np.asarray(sessions), params)
    if len(legacy['blocks']) != len(tape):
        raise DetectorTapeError('instrumentation dropped a complete block')
    tails = []
    width = params['window_bars']
    for label, (first, last) in zip(labels, spans):
        remainder = (last-first+1) % width
        if remainder:
            tails.append({'session': label, 'first_bar': last-remainder+1,
                          'last_bar': last, 'bar_count': remainder,
                          'status': 'INCOMPLETE_DETECTOR_BLOCK_NOT_PADDED'})
    return {'schema': 'edgelab_avzvol_declared_detector_tape_v1',
        'source_notebook_sha256': SOURCE_NOTEBOOK_SHA256, 'fixture_sha256': FIXTURE_SHA256,
        'parameter_snapshot': dict(params), 'observations': tape,
        'zone_creation_snapshots': creations, 'incomplete_session_tails': tails,
        'scope': 'DECLARED_ARRAY_REPLAY_NOT_MARKET_CENSUS',
        'source_quality_certified': False, 'historical_consumption_verified': False,
        'census_completeness_verified': False, 'scientific_rule_approved': False,
        'research_authorized': False, 'outcomes_computed': False,
        'original_outputs_modified': False}


def synthetic_fixture(session_count=22, final_tail_bars=0):
    """Invented sessions, prints and footprints; not a trading calendar."""
    import numpy as np
    import pandas as pd
    if type(session_count) is not int or not 1 <= session_count <= 25:
        raise DetectorTapeError('bounded invented fixture required')
    if type(final_tail_bars) is not int or not 0 <= final_tail_bars < 10:
        raise DetectorTapeError('bounded invented tail required')
    n = session_count*10 + final_tail_bars
    end, sessions, ticks, vols = [], [], [], []
    for i in range(n):
        day = min(i//10, session_count-1)
        label = f'2026-09-{day+1:02d}'
        stamp = pd.Timestamp(label+'T15:00:00Z').value + (i-day*10)*1_000_000_000
        sessions.append(label);end.append(stamp)
        ticks.extend([100,101,102,103,104])
        hot = 100 if day < 20 else 10000
        vols.extend([10,10,hot,hot,10])
    bars = SimpleNamespace(close_t=np.full(n,102,dtype=np.int64),
        low_t=np.full(n,100,dtype=np.int64), high_t=np.full(n,104,dtype=np.int64),
        end_ns=np.array(end,dtype=np.int64))
    fp = SimpleNamespace(offsets=np.arange(n+1,dtype=np.int64)*5,
        ticks=np.array(ticks,dtype=np.int64),vols=np.array(vols,dtype=np.int64))
    return bars, fp, sessions
