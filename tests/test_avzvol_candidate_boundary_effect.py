"""Invented exposed log values only; no prices, raw source or scientific claim."""
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
import subprocess,sys
import numpy as np
import pandas as pd
import pytest
spec=spec_from_file_location('boundary_effect',Path(__file__).resolve().parents[1]/'tools/review_avzvol_candidate_boundary_effect.py')
mod=module_from_spec(spec);spec.loader.exec_module(mod)

def frame():
    rows=[]
    for c in mod.CONTRACTS:
        rows.extend([(c,1,'4_250_20','real',.1),(c,1,'4_250_20','pseudo',.2),
                     (c,2,'4_250_20','real',.1),(c,2,'4_250_20','pseudo',.4)])
    return pd.DataFrame(rows,columns=mod.KEYS+['kind','o5'])

def test_session_weights_and_independent_means():
    d=frame();g=mod.groups(d);m=mod.panel(g,['4_250_20'])
    assert mod.value(m)==pytest.approx(-.2)
    direct=mod.direct_groups(d)
    assert direct[(mod.CONTRACTS[0],1,'4_250_20')]==pytest.approx(-.1)
    assert direct[(mod.CONTRACTS[0],2,'4_250_20')]==pytest.approx(-.3)

def test_missing_support_preserved_not_zero_or_shrunken():
    d=frame();d=d[~((d.contract==mod.CONTRACTS[-1])&d.kind.eq('pseudo'))]
    p=mod.panel(mod.groups(d),['4_250_20']);assert p.isna().sum()==1 and mod.value(p) is None

def test_duplicate_replacement_and_missing_preserved():
    d=frame();extra=d.iloc[[1]].copy();extra['o5']=.6
    missing=d.iloc[[1]].copy();missing['o5']=np.nan
    d=pd.concat([d,extra,missing],ignore_index=True)
    assert mod.groups(d).loc[(mod.CONTRACTS[0],1,'4_250_20'),'delta']==pytest.approx(-.3)
    assert mod.direct_groups(d)[(mod.CONTRACTS[0],1,'4_250_20')]==pytest.approx(-.3)

def test_geometric_ratio_not_absolute_volatility_and_unknown():
    assert mod.interpret(-.1)['relative_geometric_gap_percent']==pytest.approx(100*np.expm1(-.1))
    assert mod.interpret(None)=={'log_gap':None,'relative_geometric_gap_percent':None}

@pytest.mark.parametrize('flag',[False,True])
def test_optin_or_evidence_pin_stops_before_any_payload(tmp_path,flag):
    ev=tmp_path/'evidence';ev.write_text('{}')
    cmd=[sys.executable,'-O',str(Path(mod.__file__)),'--map-evidence',str(ev),'--map-evidence-sha256','0'*64,
         '--map-dir',str(tmp_path/'missing-map'),'--export-inventory',str(tmp_path/'missing-export'),'--out-dir',str(tmp_path/'out')]
    if flag:cmd.append('--allow-exposed-o5-review')
    p=subprocess.run(cmd,capture_output=True,text=True)
    assert p.returncode==2 and not (tmp_path/'out').exists()
    if flag:assert 'candidate evidence pin mismatch' in p.stdout
