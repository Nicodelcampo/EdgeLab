"""Build a deterministic candidate pilot roster, without opening market data.

This is preparation, not a notebook runner or authority gate. Configurations
are selected from PARAMETER levels only, never from outcomes/density results.
The 96-config roster covers branches to profile before the full atlas.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import random
from itertools import product


def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def build_roster(design):
    cat=design['catalog'];out=[]
    for fam in ('avolzonepoi2','bigtrap2','bigtrap2absorption'):
        axes=cat['axes'][fam];fixed=cat['fixed_parameters'][fam]
        columns={};rng=random.Random({'avolzonepoi2':2026101101,'bigtrap2':2026101102,'bigtrap2absorption':2026101103}[fam])
        for axis,levels in axes.items():
            values=(levels*32)[:32];rng.shuffle(values);columns[axis]=values
        cells=[]
        for i in range(32):
            c={k:v[i] for k,v in columns.items()};bar=c.pop('bar_spec',None);p={**fixed,**c}
            if 'wick_policy' in p:
                wick=p.pop('wick_policy');mapping=cat['wick_mapping'][wick]
                if fam=='bigtrap2':p.update(use_wick_filter=mapping['enabled'],wick_zone_pct=mapping['percent'])
                else:p.update(UseWickFilter=mapping['enabled'],WickZonePct=mapping['percent'])
            rec={'indicator':fam,'bar_spec':bar,'params':p};rec['config_sha256']=digest(rec);rec['role']='DETERMINISTIC_BRANCH_COVERAGE';cells.append(rec)
        # Keep reference and dense probes intentionally; do not claim every
        # marginal level remains exactly balanced after these replacements.
        if fam=='avolzonepoi2':
            ref={'window_bars':10,'median_multiplier':2.0,'max_gap_ticks':1,'min_cluster_ticks':2,'score_mode':'Suma','detection_percentile':95.0}
            dense={**ref,'window_bars':5,'median_multiplier':1.25,'max_gap_ticks':2,'detection_percentile':70.0}
            configs=[('tick:25',ref,'LEGACY_DETECTION_REFERENCE'),('tick:200',ref,'LEGACY_DETECTION_REFERENCE'),('tick:25',dense,'PROPOSED_DENSE_NOT_MEASURED')]
        elif fam=='bigtrap2':
            ref={'ticks_per_row':1,'imbalance_mode':'Diagonal','trap_volume_source':'AggressiveSide','imbalance_ratio':3.0,'use_wick_filter':True,'wick_zone_pct':30.0,'min_trap_volume':30.0}
            dense={**ref,'imbalance_ratio':1.5,'use_wick_filter':False,'min_trap_volume':1.0}
            configs=[('time:1',ref,'HISTORICAL_TIME_REFERENCE_NOT_CURRENT_CERTIFICATE'),('tick:25',ref,'TICK_REFERENCE_PARITY_APPROXIMATION_ACCEPTED'),('tick:25',dense,'PROPOSED_DENSE_NOT_MEASURED')]
        else:
            ref={'TapeWindowTicks':25,'ScoreMode':'AbsMagnitude','AbsorptionPct':90.0,'TicksPerRow':1,'ImbalanceMode':'Diagonal','ImbalanceRatio':3.0,'MinStackedRows':2,'MinTrapFrac':.2,'RequireFlowSideMatch':True,'UseWickFilter':True,'WickZonePct':30.0}
            dense={**ref,'AbsorptionPct':50.0,'ImbalanceRatio':1.5,'MinStackedRows':1,'MinTrapFrac':0.0,'UseWickFilter':False}
            configs=[(None,ref,'HEADLINE_REFERENCE_CURRENT_BUILD'),(None,{**ref,'ScoreMode':'AbsDirectional'},'DIRECTIONAL_REFERENCE_CURRENT_BUILD'),(None,dense,'PROPOSED_DENSE_NOT_MEASURED')]
        for i,(bar,p,role) in enumerate(configs):
            rec={'indicator':fam,'bar_spec':bar,'params':{**fixed,**p}};rec['config_sha256']=digest(rec);rec['role']=role;cells[i]=rec
        # Coverage is transparent and measured on the final roster below.
        unique=[];seen=set();duplicates=[]
        for rec in cells:
            if rec['config_sha256'] in seen:duplicates.append(rec['config_sha256']);continue
            unique.append(rec);seen.add(rec['config_sha256'])
        # Pure-parameter deterministic fill, no rerunning seeds based on data.
        if len(unique)<32:
            for values in product(*axes.values()):
                c=dict(zip(axes,values));bar=c.pop('bar_spec',None);p={**fixed,**c}
                if 'wick_policy' in p:
                    m=cat['wick_mapping'][p.pop('wick_policy')]
                    if fam=='bigtrap2':p.update(use_wick_filter=m['enabled'],wick_zone_pct=m['percent'])
                    else:p.update(UseWickFilter=m['enabled'],WickZonePct=m['percent'])
                rec={'indicator':fam,'bar_spec':bar,'params':p};rec['config_sha256']=digest(rec);rec['role']='DETERMINISTIC_DUPLICATE_REPLACEMENT'
                if rec['config_sha256'] not in seen:unique.append(rec);seen.add(rec['config_sha256'])
                if len(unique)==32:break
        if len(unique)!=32:raise ValueError('insufficient distinct parameter configurations')
        for rec in unique:rec['nominal_duplicate_ids_removed_for_compute_only']=duplicates
        out.extend(unique)
    coverage={}
    for fam in ('avolzonepoi2','bigtrap2','bigtrap2absorption'):
        cs=[c for c in out if c['indicator']==fam];cov={}
        for axis,levels in cat['axes'][fam].items():
            if axis=='wick_policy':
                on='use_wick_filter' if fam=='bigtrap2' else 'UseWickFilter';pct='wick_zone_pct' if fam=='bigtrap2' else 'WickZonePct'
                observed={'OFF' if not c['params'][on] else f"ON_{int(c['params'][pct])}" for c in cs}
            else:observed={c['bar_spec'] if axis=='bar_spec' else c['params'][axis] for c in cs}
            cov[axis]={'covered':[v for v in levels if v in observed],'not_covered':[v for v in levels if v not in observed]}
        coverage[fam]=cov
    if any(v['not_covered'] for cov in coverage.values() for v in cov.values()):raise ValueError('pilot lost parameter marginal coverage')
    return {'schema':'mnq_confluence_target_free_pilot_roster_v1','status':'PREPARED_NOT_LAUNCHED','config_selection':'PARAMETER_ONLY_FIXED_SEEDS_NO_OUTCOMES','configs':out,'n_configs':len(out),'coverage':coverage,'racimo_configs':[{'racimo_min':3,'racimo_bars':250,'racimo_altura_ticks':20},{'racimo_min':4,'racimo_bars':500,'racimo_altura_ticks':30},{'racimo_min':6,'racimo_bars':500,'racimo_altura_ticks':30},{'racimo_min':8,'racimo_bars':1000,'racimo_altura_ticks':60}],
        'firewall':{'market_data_read':False,'outcomes_read':False,'pnl_computed':False,'holdout_opened':False},
        'source_manifest':None,'selected_sessions':None,'hardware_budget':None,
        'parity_policy':{'indicator_parity_perfection_required':False,'near_100_percent_is_user_estimate_not_measurement':True,'approximate_identity_risk_accepted_for_exploration':True,'fast_reference_output_equivalence_still_required':True},
        'tasks':['pin eligible sources and warmup/session roster','wire immutable detector births and lifecycle events into scoped snapshots','profile detector generation, racimo reference scan, as-of interval joins, features and IO','compare exact output of reference/optimized implementation (not NT8 perfection)','export only sanitized counts/coverage/cost receipts'],
        'not_implemented':['market detector adapters','triples and price-arrival anchors','eligibility-bound Kaggle execution','end-to-end resource measurement','scientific labels/inference'],
        'launch_ready':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--design',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('new output path required')
    s=json.loads(a.design.read_bytes());r=build_roster(s);r['design_sha256']=hashlib.sha256(a.design.read_bytes()).hexdigest();r['roster_sha256']=digest(r)
    a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('Prepared',r['n_configs'],'configs; market reads=0; not launched')
if __name__=='__main__':main()
