"""Campañas de grilla como datos: JSON -> candidata -> RunSpec + pre-registro que pasan las guardas reales."""
import json

import pytest

from edgelab.autopilot import generate as GEN, guard
from edgelab.autopilot.spec import RunSpec

CAMP = dict(cid="GRILLA-X-REP-NQ", titulo="réplica X", experimento="edgelab.research.u1_indaga", kernel="tools/kaggle_grilla/kernel_u1_indaga.py",
            fuente="NQ", modo="REP", desde="20260401", hasta="20260930", needs=["NQ:2026-04-01:2026-09-30"], n_trials=3, family="GRILLA_U1",
            spec="docs/research/areas_expansion_20261022/SPEC_U1_INDAGA.md", justificacion_economica="j", como_podria_refutarse="r",
            celdas=[[0, 1, 1, 2, 2, 2, 3, 3, 3, 0]], cortes={"vol_vuelta/ida": [0.7, 1.2]})


def test_campana_genera_runspec_y_prereg_que_pasan_las_guardas(tmp_path, monkeypatch):
    d = tmp_path / "config/autopilot/grillas/campanas"; d.mkdir(parents=True)
    (d / "x.json").write_text(json.dumps(CAMP)); (d / "apagada.json").write_text(json.dumps(dict(CAMP, cid="OFF", activa=False)))
    monkeypatch.setattr(GEN, "REPO", tmp_path)
    cs = GEN.campanas_grilla()
    assert [c.cid for c in cs] == ["GRILLA-X-REP-NQ"] and cs[0].template == "grilla"
    rs = GEN.to_runspec(cs[0]); spec = RunSpec.from_dict(rs)
    assert spec.validate_shape() == [] and guard.check_holdout(spec) == [] and rs["kind"] == "replication"
    assert rs["env"]["CELDAS"] == json.dumps(CAMP["celdas"]) and rs["decision_rule"] == "escalera_v1"
    texto = GEN.draft_prereg(cs[0], dict(leads=[]))
    (tmp_path / "pre.md").write_text(texto, encoding="utf-8")
    assert guard.check_env_in_prereg(RunSpec.from_dict(dict(rs, prereg="pre.md")), tmp_path) == []
    assert "Holm" not in texto.split("## Grilla y decisión")[1]


def test_campana_incompleta_falla(tmp_path, monkeypatch):
    d = tmp_path / "config/autopilot/grillas/campanas"; d.mkdir(parents=True)
    (d / "x.json").write_text(json.dumps({k: v for k, v in CAMP.items() if k != "como_podria_refutarse"}))
    monkeypatch.setattr(GEN, "REPO", tmp_path)
    with pytest.raises(ValueError): GEN.campanas_grilla()


def test_holdout_en_campana_lo_frena_la_guarda(tmp_path, monkeypatch):
    d = tmp_path / "config/autopilot/grillas/campanas"; d.mkdir(parents=True)
    (d / "x.json").write_text(json.dumps(dict(CAMP, needs=["NQ:2026-09-01:2026-10-15"])))
    monkeypatch.setattr(GEN, "REPO", tmp_path)
    assert guard.check_holdout(RunSpec.from_dict(GEN.to_runspec(GEN.campanas_grilla()[0])))
