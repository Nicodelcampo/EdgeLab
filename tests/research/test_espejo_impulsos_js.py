"""Paridad Python ↔ JS del kernel EspejoImpulsos: el visor dibuja exactamente los eventos del censo."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from edgelab.bridge.indicators import espejo_impulsos as K

from test_espejo_impulsos import P, _serie_larga

JS = Path(__file__).resolve().parents[2] / "viewer" / "nt8_bridge" / "espejo_impulsos.js"


def _norm(e):
    out = {}
    for k, v in e.items():
        if isinstance(v, (bool, np.bool_)) or v is None or isinstance(v, str):
            out[k] = v if not isinstance(v, np.bool_) else bool(v)
        elif isinstance(v, float) and v != v:
            out[k] = "nan"
        else:
            out[k] = round(float(v), 6)
    return out


@pytest.mark.parametrize("prm", [P, dict(P, atr_k=3, max_bars=12)])
def test_paridad_js(tmp_path, prm):
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    t, O, H, L, C, V, S = _serie_larga(seed=11, n_ses=5, n=500)
    res = K.run(t, O, H, L, C, V, S, params=prm)
    data = dict(t=t.tolist(), O=O.tolist(), H=H.tolist(), L=L.tolist(), C=C.tolist(), V=V.tolist(), S=S.tolist(), p=prm)
    (tmp_path / "in.json").write_text(json.dumps(data))
    script = (f"const K=require({json.dumps(str(JS))});const d=require({json.dumps(str(tmp_path / 'in.json'))});"
              "const r=K.run(d.t,d.O,d.H,d.L,d.C,d.V,d.S,null,d.p);"
              "process.stdout.write(JSON.stringify(r.events,(k,v)=>typeof v==='number'&&isNaN(v)?'nan':v));")
    out = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True).stdout
    js = json.loads(out)
    assert len(res["events"]) > 20
    assert [_norm(e) for e in res["events"]] == [_norm(e) for e in js]
