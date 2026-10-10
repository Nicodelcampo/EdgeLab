"""Installed wheel functional smoke: invented timestamps only, no network/prices."""
import json
import tempfile
from pathlib import Path
import pandas as pd
from edgelab.kaggle.aggregate_audit import digest
from edgelab.kaggle.coverage_inventory import audit_coverage
from edgelab.kaggle.raw_tick_audit import audit_canonical_tick_file
from edgelab.kaggle.research_access import require_requested_coverage
from edgelab.data.research_data_gate import DataEligibilityError


def main():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td);ns=pd.Timestamp('2026-01-05 12:00',tz='UTC').value
        raw=p/'raw.parquet'
        pd.DataFrame({'ts_utc_ns':[ns,ns],'ts_local_ns':[ns,ns],'sequence':[0,1],
            'price_ticks':[100,100],'bid_ticks':[99,99],'ask_ticks':[101,101],
            'volume':[1,1],'aggressor':['buy','sell'],'tick_type':['trade','trade'],
            'instrument':['ES','ES'],'contract':['ES 03-26','ES 03-26'],
            'source_file':['invented','invented'],'source_row':[0,1]}).to_parquet(raw,index=False)
        report,_=audit_canonical_tick_file(path=raw,expected_sha256=digest(raw),
            expected_bytes=raw.stat().st_size,expected_rows=2,instrument='ES',contract='ES 03-26',include_clock_diagnostics=True)
        assert report['status']=='PASS_RAW_STRUCTURE_ONLY' and report['research_allowed'] is False
        assert report['clock_band_16_to_17_CT_trade_rows']==0
        assert report['errors']['duplicate_source_identity']==0 and report['warnings']['repeated_timestamps_legitimate']==1
        row={'instrument':'ES','date':'2026-01-05','contract':'ES_03-26','dataset':'SYNTHETIC','file':'raw.parquet','approved':True}
        plan={'spec':{'holdout_first_trade_date':'2026-10-01','requests':[{'instrument':'ES','start':'2026-01-04','end':'2026-01-05'}]},'shards':[{'sessions':[row]}]}
        resolver={'holdout_first_trade_date':'2026-10-01','instruments':{'ES':{'sessions':[row]}}}
        catalog={'holdout_first_trade_date':'2026-10-01','instruments':{'ES':{'first_date':'2026-01-05','last_date':'2026-01-05'}}}
        for name,value in [('plan.json',plan),('RESOLVER.json',resolver),('catalog.json',catalog)]:
            (p/name).write_text(json.dumps(value))
        pd.DataFrame({'session_date':['2026-01-05'],'contract':['ES_03-26'],
            'bucket_utc_ns':[ns],'first_ts_utc_ns':[ns],'last_ts_utc_ns':[ns]}).to_parquet(p/'ES__1s.parquet',index=False)
        (p/'manifest.json').write_text(json.dumps({'files':[{'path':name,'sha256':digest(p/name),'bytes':(p/name).stat().st_size} for name in ['plan.json','ES__1s.parquet']]}))
        summary,daily=audit_coverage(store=p,resolver=p/'RESOLVER.json',catalog=p/'catalog.json',
            expected_manifest_sha256=digest(p/'manifest.json'),expected_resolver_sha256=digest(p/'RESOLVER.json'),expected_catalog_sha256=digest(p/'catalog.json'))
        assert len(daily)==2 and daily[0]['minutes_with_observations'] is None
        assert daily[1]['minutes_with_observations']==1 and daily[1]['minutes_without_observations']==1439
        assert summary['research_allowed'] is False
        try:
            require_requested_coverage(certificate={},instrument='ES',start='2026-01-04',end='2026-01-05',materialized_dates={'2026-01-05'})
        except DataEligibilityError:pass
        else:raise AssertionError('missing coverage did not fail closed')
    print(json.dumps({'status':'PASS_INSTALLED_SYNTHETIC_KAGGLE_QA','raw_identity_and_coverage_functional':True,'research_authorized':False}))


if __name__=='__main__':main()
