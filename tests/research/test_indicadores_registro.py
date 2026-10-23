"""Registro de indicadores para barridos y prueba de causalidad de indicadores propios."""
import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from edgelab.research import indicadores as I

ROOT = Path(__file__).resolve().parents[2]


def test_registro_apunta_a_modulos_y_documentos_que_existen():
    for r in I.registro().values():
        assert (ROOT / r["modulo"].split(" ")[0]).exists(), r["id"]
        if r["estado"] == "NATIVO_AGENTE": assert (ROOT / r["test_causal"].split("::")[0]).exists(), r["id"]
        assert r["estado"] in ("PASS", "PASS_CON_CAVEAT", "PARCIAL", "VERIFICAR", "PENDIENTE", "NATIVO_AGENTE")
        if r["estado"].startswith("PASS"):
            assert r["doc"] and all((ROOT / d.strip()).exists() for d in r["doc"].split(";")), r["id"]


def test_exigir_frena_lo_no_validado():
    assert I.exigir(["LUX-IMB"]) == []
    assert I.exigir(["BigTrap2"])                                            # PASS_CON_CAVEAT: devuelve el caveat a citar
    with pytest.raises(I.IndicadorNoUsable): I.exigir(["aVolCellPOI2"])
    with pytest.raises(I.IndicadorNoUsable): I.exigir(["NO_EXISTE"])


# experimentos que no viven en el perímetro del agente: declaración acá (los del agente la declaran en el módulo)
EXPERIMENTOS = {"edgelab.research.u1_indaga": ["LUX-IMB"]}


def test_experimentos_usan_indicadores_validados():
    mods = dict(EXPERIMENTOS)
    for p in (ROOT / "edgelab/research/agente").glob("*.py"):
        if p.name == "__init__.py" or "def disparos(" not in p.read_text(encoding="utf-8"): continue
        m = importlib.import_module(f"edgelab.research.agente.{p.stem}")
        assert hasattr(m, "INDICADORES"), f"{p.name} no declara INDICADORES"
        mods[m.__name__] = m.INDICADORES
    for _, ids in mods.items(): I.exigir(ids)


def _ctx(n=3000, seed=0):
    rng = np.random.default_rng(seed); c = 100 + np.cumsum(rng.normal(0, 1, n))
    return dict(c=c, h=c + 0.5, l=c - 0.5, t=np.arange(n) * 60.0)


def test_causal_detecta_look_ahead():
    def ok(ctx):
        c = ctx["c"]; m = pd.Series(c).rolling(20).mean().to_numpy()
        k = np.flatnonzero(c > m); return pd.DataFrame(dict(k=k, x=(c - m)[k]))
    def mira(ctx):
        c = ctx["c"]; m = pd.Series(c).rolling(20, center=True).mean().to_numpy()       # usa el futuro
        k = np.flatnonzero(np.isfinite(m) & (c > m)); return pd.DataFrame(dict(k=k, x=(c - m)[k]))
    assert I.causal(ok, _ctx()) == []
    assert I.causal(mira, _ctx())


def test_registro_del_agente_solo_admite_nativo(tmp_path):
    import json
    ra = tmp_path / "ag.json"
    ra.write_text(json.dumps(dict(indicadores=[dict(id="MIO", modulo="edgelab/research/agente/mio.py", estado="NATIVO_AGENTE", test_causal="tests/agente/test_mio.py::test_causal")])))
    assert "MIO" in I.registro(ruta_agente=ra) and I.exigir(["MIO"], ruta_agente=ra)                # usable, con nota
    for malo in (dict(id="X", modulo="m", estado="PASS", test_causal="t"), dict(id="LUX-IMB", modulo="m", estado="NATIVO_AGENTE", test_causal="t"),
                 dict(id="Y", modulo="m", estado="NATIVO_AGENTE")):
        ra.write_text(json.dumps(dict(indicadores=[malo])))
        with pytest.raises(I.IndicadorNoUsable): I.registro(ruta_agente=ra)
