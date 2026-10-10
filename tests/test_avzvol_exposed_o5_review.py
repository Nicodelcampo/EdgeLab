"""Only tiny invented exports, never market outcomes or private files."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
import pytest
pq=pytest.importorskip('pyarrow.parquet')
pa=pytest.importorskip('pyarrow')
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools/review_avzvol_exposed_o5.py'
CONTRACTS=['MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26','MNQ_12-26']

def fixture(tmp_path, reserved=False,bad_hash=False):
    inventory=[];pins=[]
    for i,c in enumerate(CONTRACTS):
        p=tmp_path/(c+'_avzp2racgrid.parquet')
        s=20261001 if reserved and i==5 else 20260105
        t=pa.table({'contract':[c]*4,'cell':['4_250_20']*4,'kind':['real','real','pseudo','pseudo'],
                    'session':[s]*4,'t0':[10,20,30,40],'te':[11,-1,31,41],'o5':[.1,None,.2,.2]})
        pq.write_table(t,p);sha=hashlib.sha256(p.read_bytes()).hexdigest()
        pins.append({'file':p.name,'sha256':'0'*64 if bad_hash and i==5 else sha,'rows':4})
        inventory.append({'file':str(p)})
    ref=tmp_path/'reference.json';ref.write_text(json.dumps({'covariate_audit':{'files':pins}}))
    idx=tmp_path/'inventory.json';idx.write_text(json.dumps(inventory))
    return ref,idx

def run(tmp_path,ref,idx,optimized=False,flag=True):
    args=[sys.executable]+(['-O'] if optimized else [])+[str(TOOL),'--audit-reference',str(ref),
          '--audit-reference-sha256',hashlib.sha256(ref.read_bytes()).hexdigest(),
          '--inventory',str(idx),'--out-dir',str(tmp_path/'out')]
    if flag:args+=['--allow-exposed-o5-review']
    return subprocess.run(args,capture_output=True,text=True,cwd=tmp_path)

def test_missing_kept_and_weights_are_descriptive(tmp_path):
    ref,idx=fixture(tmp_path);p=run(tmp_path,ref,idx);assert p.returncode==0,p.stdout+p.stderr
    j=json.loads((tmp_path/'out/evidence.json').read_text());s=j['summary']
    assert s['export_rows']==24 and s['finite_o5_rows']==18 and s['missing_o5_rows']==6
    assert s['missing_no_exit_rows']==6 and s['missing_other_unknown_rows']==0
    assert s['cells_descriptively_computable']==1 and s['common_six_contract_cells']==1
    assert all(c['plot_equal_cell_mean_delta']==pytest.approx(-.1) for c in j['contracts'])
    assert all(j[k] is False for k in ['research_release_authorized','raw_quality_certified',
        'historical_bias_adjudicated','own_census_outcome_benchmark_implemented','economic_outcomes_computed',
        'market_kernel_launched','original_outputs_modified','new_outcomes_constructed_from_prices'])
    assert j['study_plan']['preregistered_or_blind'] is False
    assert j['exported_outcomes_read'] is True and j['inferential_tests_executed']==0

@pytest.mark.parametrize('optimized',[False,True])
def test_reserved_last_file_stops_before_any_review_payload(tmp_path,optimized):
    ref,idx=fixture(tmp_path,reserved=True);p=run(tmp_path,ref,idx,optimized)
    assert p.returncode==2 and not (tmp_path/'out/evidence.json').exists()
    assert 's.max' in p.stdout

@pytest.mark.parametrize('optimized',[False,True])
def test_bad_last_hash_stops_even_optimized(tmp_path,optimized):
    ref,idx=fixture(tmp_path,bad_hash=True);p=run(tmp_path,ref,idx,optimized)
    assert p.returncode==2 and not (tmp_path/'out/evidence.json').exists()
    assert 'file_digest' in p.stdout

def test_no_explicit_outcome_permission_stops_before_files(tmp_path):
    ref=tmp_path/'missing';idx=tmp_path/'missing-index'
    p=subprocess.run([sys.executable,str(TOOL),'--audit-reference',str(ref),
        '--audit-reference-sha256','0'*64,'--inventory',str(idx),'--out-dir',str(tmp_path/'out')],
        capture_output=True,text=True)
    assert p.returncode==2 and not (tmp_path/'out').exists()

def test_report_directory_never_overwritten(tmp_path):
    ref,idx=fixture(tmp_path);(tmp_path/'out').mkdir();(tmp_path/'out/original').write_text('preserve')
    p=run(tmp_path,ref,idx);assert p.returncode==2
    assert (tmp_path/'out/original').read_text()=='preserve' and not (tmp_path/'out/evidence.json').exists()
