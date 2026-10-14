'AVZVOL exposed-export descriptive review, not a market/certification runner.'
from pathlib import Path
import argparse
import hashlib, json, math
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyarrow.compute as pc


class ExposedReviewError(ValueError):
    """Declared output contract failed; no correction or research permission."""


def require(condition, message):
    if not condition:
        raise ExposedReviewError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-reference', type=Path, required=True)
    parser.add_argument('--audit-reference-sha256', required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--allow-exposed-o5-review', action='store_true', required=True)
    args = parser.parse_args()
    require(hashlib.sha256(args.audit_reference.read_bytes()).hexdigest() == args.audit_reference_sha256, 'STOP: hashlib.sha256(args.audit_reference.read_bytes()).hexdigest() == args.audit_reference_sha256')
    audit = json.loads(args.audit_reference.read_text())
    inventory = json.loads(args.inventory.read_text())
    require(isinstance(inventory, list) and len(inventory) == 6, 'STOP: isinstance(inventory, list) and len(inventory) == 6')
    require(len({Path(r['file']).name for r in inventory}) == 6, "STOP: len({Path(r['file']).name for r in inventory}) == 6")
    paths = {Path(r['file']).name: Path(r['file']) for r in inventory}
    OUT = args.out_dir
    OUT.mkdir(parents=True, exist_ok=False)
    pins = audit['covariate_audit']['files']
    contracts = ['MNQ_09-25', 'MNQ_12-25', 'MNQ_03-26', 'MNQ_06-26', 'MNQ_09-26', 'MNQ_12-26']
    cells = [f'{m}_{w}_{a}' for m in (4, 5, 6, 8) for w in (250, 500, 1000) for a in (20, 30, 45)]
    plan = {'study_id': 'AVZVOL-EXPOSED-DESC-1', 'scope': 'user-authorized exposed O5 descriptive reuse with declared limitations; not certified market research', 'preregistered_or_blind': False, 'chart_exception_selected_after_inspection': True, 'cell_universe': cells, 'columns': ['contract', 'cell', 'kind', 'session', 't0', 'te', 'o5'], 'estimand': 'Within contract/session/cell mean(real finite O5) minus mean(legacy pseudo finite O5); equal weight of common-support sessions within each contract/cell', 'missing_policy': 'no imputation; all rows counted; no-exit vs other unknown reasons; unsupported session-cells retained in accounting', 'cell_summary': 'equal mean of six contract/cell deltas where computable; retain all 36 cells including nulls', 'plot_summary': 'equal mean of cell deltas in intersection of computable cells across all six contracts, separately per contract', 'no_p_values_or_CIs': True, 'no_matching_or_calipers': True, 'no_new_endpoints': True, 'no_raw_ticks': True, 'no_economic_outcomes': True, 'raw_quality_certified': False, 'zone_free_control_verified': False, 'independent_confirmation': False, 'pair_reconstruction_attempted': False}
    (OUT / 'analysis-plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    files = []
    require({p['file'] for p in pins} == {c + '_avzp2racgrid.parquet' for c in contracts}, "STOP: {p['file'] for p in pins} == {c + '_avzp2racgrid.parquet' for c in contracts}")
    require(set(paths) == {p['file'] for p in pins}, "STOP: set(paths) == {p['file'] for p in pins}")
    for pin in pins:
        require(pin['file'] in paths, "STOP: pin['file'] in paths")
        p = paths[pin['file']]
        pf = pq.ParquetFile(p)
        require(pf.metadata.num_rows == pin['rows'], "STOP: pf.metadata.num_rows == pin['rows']")
        require(set(plan['columns']) <= set(pf.schema_arrow.names), "STOP: set(plan['columns']) <= set(pf.schema_arrow.names)")
        i = pf.schema_arrow.names.index('session')
        for g in range(pf.num_row_groups):
            s = pf.metadata.row_group(g).column(i).statistics
            require(s and s.has_min_max and (s.null_count == 0) and (int(s.max) < 20261001), 'STOP: s and s.has_min_max and (s.null_count == 0) and (int(s.max) < 20261001)')
        files.append((p, pf, pin))
    for p, pf, pin in files:
        with p.open('rb') as stream:
            require(hashlib.file_digest(stream, 'sha256').hexdigest() == pin['sha256'], "STOP: hashlib.file_digest(stream, 'sha256').hexdigest() == pin['sha256']")
    preflight = [{'file': p.name, 'rows': pf.metadata.num_rows, 'sha256': pin['sha256'], 'all_session_groups_preholdout': True} for p, pf, pin in files]
    tables = []
    for p, pf, pin in files:
        d = pf.read(columns=plan['columns']).to_pandas()
        require(set(d.contract) == {p.name.removesuffix('_avzp2racgrid.parquet')}, "STOP: set(d.contract) == {p.name.removesuffix('_avzp2racgrid.parquet')}")
        require(set(d.kind) <= {'real', 'pseudo'} and d[plan['columns'][:-1]].notna().all().all(), "STOP: set(d.kind) <= {'real', 'pseudo'} and d[plan['columns'][:-1]].notna().all().all()")
        require(set(d.cell) <= set(cells) and (not np.isinf(d.o5).any()), 'STOP: set(d.cell) <= set(cells) and (not np.isinf(d.o5).any())')
        require((d.o5.notna() & (d.te < 0)).sum() == 0, 'STOP: (d.o5.notna() & (d.te < 0)).sum() == 0')
        tables.append(d)
    d = pd.concat(tables, ignore_index=True)
    d['finite_o5'] = np.isfinite(d.o5)
    d['missing_no_exit'] = ~d.finite_o5 & (d.te < 0)
    d['missing_other_unknown'] = ~d.finite_o5 & (d.te >= 0)
    keys = ['contract', 'session', 'cell']
    counts = d.groupby(keys + ['kind'], sort=True).agg(rows=('o5', 'size'), finite=('finite_o5', 'sum'), no_exit=('missing_no_exit', 'sum'), other_unknown=('missing_other_unknown', 'sum'))
    means = d[d.finite_o5].groupby(keys + ['kind'], sort=True).o5.mean().unstack('kind').reindex(columns=['real', 'pseudo'])
    all_groups = counts.reset_index()[keys].drop_duplicates().set_index(keys).index
    means = means.reindex(all_groups)
    means['common_support'] = means.real.notna() & means.pseudo.notna()
    means['delta'] = means.real - means.pseudo
    means.reset_index().to_csv(OUT / 'private-session-cell-means.csv', index=False)
    cell_records = []
    contract_cell = []
    for c in contracts:
        for cell in cells:
            x = means.loc[(means.index.get_level_values('contract') == c) & (means.index.get_level_values('cell') == cell)]
            z = x[x.common_support]
            contract_cell.append({'contract': c, 'cell': cell, 'session_cell_groups': len(x), 'supported_sessions': len(z), 'unsupported_sessions': len(x) - len(z), 'delta_equal_session_mean': float(z.delta.mean()) if len(z) else None, 'median_session_delta': float(z.delta.median()) if len(z) else None, 'negative_session_count': int((z.delta < 0).sum()), 'positive_session_count': int((z.delta > 0).sum())})
    cc = pd.DataFrame(contract_cell)
    common_cells = [cell for cell in cells if cc.loc[cc.cell == cell, 'delta_equal_session_mean'].notna().all()]
    for cell in cells:
        x = cc[cc.cell == cell]
        v = x.delta_equal_session_mean.dropna()
        cell_records.append({'cell': cell, 'contracts_computable': len(v), 'equal_contract_mean_delta': float(v.mean()) if len(v) else None, 'min_contract_delta': float(v.min()) if len(v) else None, 'max_contract_delta': float(v.max()) if len(v) else None, 'negative_contracts': int((v < 0).sum()), 'positive_contracts': int((v > 0).sum()), 'common_six_contract_plot_cell': cell in common_cells})
    contract_records = []
    for c in contracts:
        x = d[d.contract == c]
        q = cc[(cc.contract == c) & cc.cell.isin(common_cells)]
        typ = {}
        for kind in ['real', 'pseudo']:
            k = x[x.kind == kind]
            typ[kind] = {'rows': len(k), 'finite_o5': int(k.finite_o5.sum()), 'missing_no_exit': int(k.missing_no_exit.sum()), 'missing_other_unknown': int(k.missing_other_unknown.sum()), 'missing_share': float((~k.finite_o5).mean())}
        contract_records.append({'contract': c, 'rows': len(x), 'session_labels_observed': int(x.session.nunique()), 'kind_accounting': typ, 'plot_common_cell_count': len(common_cells), 'plot_equal_cell_mean_delta': float(q.delta_equal_session_mean.mean()) if len(q) else None, 'common_cell_min_delta': float(q.delta_equal_session_mean.min()) if len(q) else None, 'common_cell_max_delta': float(q.delta_equal_session_mean.max()) if len(q) else None})
    verified = 0
    max_error = 0.0
    for rec in contract_cell:
        if rec['delta_equal_session_mean'] is None:
            continue
        subset = d.loc[(d.contract == rec['contract']) & (d.cell == rec['cell']), ['session', 'kind', 'o5']]
        ss = subset.session.to_numpy()
        kk = subset.kind.to_numpy()
        oo = subset.o5.to_numpy()
        sessions = np.unique(ss)
        vals = []
        for s in sessions:
            a = oo[(ss == s) & (kk == 'real')]
            b = oo[(ss == s) & (kk == 'pseudo')]
            a = a[np.isfinite(a)]
            b = b[np.isfinite(b)]
            if len(a) and len(b):
                vals.append(math.fsum(map(float, a)) / len(a) - math.fsum(map(float, b)) / len(b))
        alt = math.fsum(vals) / len(vals)
        err = abs(alt - rec['delta_equal_session_mean'])
        require(err < 1e-12, 'STOP: err < 1e-12')
        max_error = max(max_error, err)
        verified += 1
    arrow_counts = {k: 0 for k in ('rows', 'real', 'pseudo', 'finite_o5')}
    for p, pf, pin in files:
        t = pf.read(columns=['kind', 'o5'])
        arrow_counts['rows'] += len(t)
        for k in ['real', 'pseudo']:
            arrow_counts[k] += pc.sum(pc.equal(t['kind'], k)).as_py()
        arrow_counts['finite_o5'] += pc.sum(pc.fill_null(pc.is_finite(t['o5']), False)).as_py()
    require(arrow_counts == {'rows': len(d), 'real': int((d.kind == 'real').sum()), 'pseudo': int((d.kind == 'pseudo').sum()), 'finite_o5': int(d.finite_o5.sum())}, "STOP: arrow_counts == {'rows': len(d), 'real': int((d.kind == 'real').sum()), 'pseudo': int((d.kind == 'pseudo').sum()), 'finite_o5': int(d.finite_o5.sum())}")
    finite_cells = [x for x in cell_records if x['equal_contract_mean_delta'] is not None]
    summary = {'export_rows': len(d), 'real_rows': int((d.kind == 'real').sum()), 'pseudo_rows': int((d.kind == 'pseudo').sum()), 'finite_o5_rows': int(d.finite_o5.sum()), 'missing_o5_rows': int((~d.finite_o5).sum()), 'missing_no_exit_rows': int(d.missing_no_exit.sum()), 'missing_other_unknown_rows': int(d.missing_other_unknown.sum()), 'candidate_cells': len(cells), 'cells_descriptively_computable': len(finite_cells), 'negative_cell_means': sum((x['equal_contract_mean_delta'] < 0 for x in finite_cells)), 'positive_cell_means': sum((x['equal_contract_mean_delta'] > 0 for x in finite_cells)), 'common_six_contract_cells': len(common_cells), 'supported_session_cell_groups': int(means.common_support.sum()), 'unsupported_session_cell_groups': int((~means.common_support).sum()), 'finite_real_only_session_cell_groups': int((means.real.notna() & means.pseudo.isna()).sum()), 'finite_pseudo_only_session_cell_groups': int((means.pseudo.notna() & means.real.isna()).sum()), 'neither_finite_session_cell_groups': int((means.real.isna() & means.pseudo.isna()).sum()), 'independently_verified_contract_cell_deltas': verified, 'maximum_numeric_crosscheck_error': max_error, 'export_first_session_label': int(d.session.min()), 'export_last_session_label': int(d.session.max()), 'overall_delta_not_reported': 'overlapping events across cells, unequal support and unresolved pair identities; no combined independent-N inference'}
    evidence = {'schema': 'edgelab_avzvol_exposed_o5_descriptive_review_v1', 'status': 'EXPLORATORY_EXPOSED_EXPORTS_NOT_ZONE_INCREMENTAL_PROOF', 'study_plan': plan, 'audit_reference_sha256': args.audit_reference_sha256, 'computation_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'files': preflight, 'summary': summary, 'contracts': contract_records, 'cells': cell_records, 'contract_cells': contract_cell, 'independent_arrow_counts': arrow_counts, 'research_release_authorized': False, 'raw_quality_certified': False, 'historical_bias_adjudicated': False, 'own_census_outcome_benchmark_implemented': False, 'exported_outcomes_read': True, 'prior_confirmation_exports_reused_as_exposed_development': True, 'new_outcomes_constructed_from_prices': False, 'inferential_tests_executed': 0, 'economic_outcomes_computed': False, 'market_kernel_launched': False, 'original_outputs_modified': False, 'comparison_plan': [{'grain': 'contract, equal cells over common six-contract cell intersection', 'population': 'exported finite O5 real/legacy pseudo within common support sessions', 'unit': 'log range-ratio gap', 'finding': 'determined in computed contracts below; neutral sign, not favorable economic outcome', 'derivation': plan['plot_summary'], 'disposition': 'chart', 'reason': 'show common-landscape mean and disclose opposite-sign 8_1000_30 cell selected for sign exception, NOT as winner; full 36-cell table retained'}, {'grain': 'all 36 prespecified cells', 'population': 'all input rows and computable contract deltas', 'unit': 'log gap/count', 'finding': 'complete landscape including missing cells', 'disposition': 'table', 'reason': 'full cell lookup; not 36 bars or 36 independent replications'}, {'grain': 'contract and kind', 'population': 'all exported rows including missing O5', 'unit': 'count/share', 'finding': 'missingness can differ between real and pseudo', 'disposition': 'prose', 'reason': 'explicit attrition accounting; complete details in report'}]}
    (OUT / 'evidence.json').write_text(json.dumps(evidence, indent=2, allow_nan=False) + '\n')
    pd.DataFrame(cell_records).to_csv(OUT / 'all-cells.csv', index=False)
    cc.to_csv(OUT / 'contract-cells.csv', index=False)
    print(json.dumps(summary, indent=2))
    print('CONTRACTS', [(r['contract'], r['plot_equal_cell_mean_delta'], r['kind_accounting']['real']['missing_share'], r['kind_accounting']['pseudo']['missing_share']) for r in contract_records])


if __name__ == '__main__':
    try:
        main()
    except (ExposedReviewError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'STOP_EXPOSED_O5_REVIEW', 'error': str(exc),
                          'research_release_authorized': False}))
        raise SystemExit(2)
