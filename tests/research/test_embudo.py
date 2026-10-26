"""Embudo de punta a punta con un runner local sobre sintéticos: avanza solo por todas las etapas hasta una decisión final,
registra pruebas, consume el libro de LORD++, escribe acta antes del holdout y CONTEO nunca expone P&L."""
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

from edgelab.funnel.libro_lord import LibroLord
from edgelab.research import embudo as EM, etapas as ET, grilla_generica as GG, sintetico, u1_indaga as U


class Reg:
    def __init__(self): self.filas = []
    def ensure(self, cid, fam, n, nota=""): self.filas.append((cid, fam, n)); return True


class RunnerLocal:
    """Corre las etapas en el momento sobre sintéticos: desarrollo = semilla 21, holdout = semilla 22 (datos distintos)."""
    _cache = {}
    def __init__(self): self.h = {}; self.vistos = []
    def lanzar(self, spec, etapa, params, periodo):
        seed = 22 if periodo[0] >= 20261001 else 21
        if seed not in self._cache:
            ctx = GG.contexto_m1(sintetico.bloques(dias=150, planta=True, seed=seed, prob_salto=0.02, fuerza=0.05), tick=0.25); ej = dict(ctx)
            for k in ("o", "h", "l", "c", "tpx"): ej[k] = ctx[k] + 25.0
            self._cache[seed] = (ctx, ej)
        ctx, ej = self._cache[seed]
        r = ET.ejecutar(etapa, importlib.import_module(spec["experimento"]), ctx, friccion=1.0, extra_adverso=0.5, cx_ej=ej, params=params, log=lambda s: None)
        hid = f"h{len(self.h)}"; self.h[hid] = json.loads(json.dumps(r, default=float)); self.vistos.append(etapa); return hid
    def estado(self, h): return "complete"
    def traer(self, h): return self.h[h]


SPEC = dict(cid="TEST-U1", familia="TEST", experimento="edgelab.research.u1_indaga", sensor="DK:X", ejecucion="Y", desc=[20250801, 20250930],
            justificacion_economica="j", como_podria_refutarse="r", embudo=True, preflight_dinamico=False,
            seleccion=dict(exigir_meseta=False, min_sesiones=5, ratio_mov_friccion=0.0, max_candidatas=2),
            holdout=dict(desde=20261001, n_fijo=10, conteo_cada_s=0), n_celdas_por_canal=GG.n_celdas(U))


def test_embudo_de_punta_a_punta(tmp_path, monkeypatch):
    monkeypatch.setattr(GG, "B_RW", 30)
    monkeypatch.setattr(U, "INDICADORES", ["LUX-IMB"], raising=False)       # el runner corre la spec de verdad (U1-INDAGA completo)
    reg, libro, run = Reg(), LibroLord(tmp_path / "lord.json", permitir_otra_ruta=True), RunnerLocal()
    from edgelab.research import linaje as LN
    LN.declarar("TEST", [], 0, "familia raíz de prueba", libro=tmp_path / "linajes.jsonl")
    em = EM.Embudo(tmp_path / "estado", dict(kaggle=run, local=run), registro=reg, libro=libro, ahora=lambda: 1_792_900_000, log=lambda s: None,
                   ventanas=tmp_path / "ventanas.jsonl", linajes=tmp_path / "linajes.jsonl", registro_pruebas=tmp_path / "registro.jsonl")
    for _ in range(40):
        st = em.avanzar(SPEC)
        if st["etapa"] == "FIN": break
    assert st["etapa"] == "FIN" and st["fase"] in ("CONFIRMADA", "REFUTADA", "SIN_POTENCIA"), (st["fase"], st.get("motivo"), run.vistos)
    assert run.vistos[:4] == ["DESC", "INDAGA", "INTEGRIDAD", "TOPES"] and run.vistos[-1] == "REP"            # recorrió todo el embudo
    d = tmp_path / "estado" / "TEST-U1"
    assert (d / "MEDIDO.md").exists() and any(c.startswith("embudo/TEST-U1/desc") for c, _, _ in reg.filas)
    if True:
        acta = json.loads((d / "ACTA_HOLDOUT.json").read_text(encoding="utf-8"))
        assert acta["registrada"] and "HOLDOUT_CONTEO" in run.vistos and run.vistos.index("HOLDOUT_CONTEO") < len(run.vistos) - 1
        assert "TEST" in libro.estado["familias"]
    assert em.avanzar(SPEC)["etapa"] == "FIN"                                        # terminada: no hace nada más


def test_campanas_de_embudo_del_repo_son_validas():
    import importlib
    from edgelab.research.preflight import estatico
    for f in sorted((Path(__file__).resolve().parents[2] / "config/autopilot/grillas/campanas").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if not d.get("embudo"): continue
        assert all(k in d for k in EM.CAMPOS), f.name
        assert estatico(importlib.import_module(d["experimento"])) == [], f.name


def test_descarga_diaria_lee_la_config(tmp_path, monkeypatch):
    import datetime as dt, importlib.util
    sp = importlib.util.spec_from_file_location("dd", Path(__file__).resolve().parents[2] / "tools/dukascopy_diario.py"); D = importlib.util.module_from_spec(sp); sp.loader.exec_module(D)
    vistos = []
    monkeypatch.setattr(D.DK, "bajar_dia", lambda s, d, p: vistos.append((s, d)) or None)
    (tmp_path / "c.json").write_text(json.dumps(dict(dukascopy=dict(simbolos=["USATECHIDXUSD"], salida_sellada=str(tmp_path), desde="2026-10-01"))))
    D.main(str(tmp_path / "c.json"), hoy=dt.date(2026, 10, 6))
    assert [d.isoformat() for _, d in vistos] == ["2026-10-01", "2026-10-02", "2026-10-04", "2026-10-05"]       # sin el sábado 3


def test_meses():
    assert EM._meses([20240102, 20260331]) == 27 and EM._meses([20260401, 20260930]) == 6 and EM._meses(None) == 0


def test_candidata_rara_no_se_elige_si_no_puede_confirmarse_en_el_oos(tmp_path, monkeypatch):
    """2026-10-25: U1-ES-GRILLA eligió celdas con ~1 operación por mes; en un OOS de 6 meses dieron 6, 1 y 0 operaciones."""
    monkeypatch.setattr(EM, "nominada", lambda p, nh, como: (True, 0.01))
    em = EM.Embudo(tmp_path / "estado", dict(kaggle=None, local=None), registro=Reg(), log=lambda s: None,
                   ventanas=tmp_path / "v.jsonl", linajes=tmp_path / "l.jsonl", registro_pruebas=tmp_path / "r.jsonl")
    spec = dict(SPEC, cid="T-FREC", desc=[20240101, 20260331], oos=[20260401, 20260930])
    base = dict(sesiones=40, ratio_mov_friccion=5.0, ic90=[1.0, 3.0], media_neta=2.0, meseta=True)
    rara, frecuente = dict(base, celda=[0, 0, 0], n=35), dict(base, celda=[1, 1, 1], n=300)
    res = dict(celdas=spec["n_celdas_por_canal"], E0=dict(cortes={}), canales=dict(total=dict(meses=[f"{m}" for m in range(27)], pistas=[rara, frecuente],
                                                                                              evaluables=2, nominadas_fdr=2)))
    st = em._fin_desc(spec, dict(etapa="DESC", reglas={}, historial=[]), res)
    assert st["candidatas"] == [[1, 1, 1]]                                           # 35/27*6 ≈ 8 < 30; 300/27*6 ≈ 67


def test_atras_informativa_nunca_mata(tmp_path):
    """ATRAS (2026-10-26): el pasado en contra con potencia queda publicado como EN_CONTRA_PASADO y la candidata sigue viva."""
    em = EM.Embudo(tmp_path, {}, log=lambda s: None, ahora=lambda: 1.0)
    spec = dict(SPEC, atras=[20230101, 20231231])
    st = dict(etapa="ATRAS", fase="CORRIENDO", historial=[], candidatas=[[1], [2], [3]],
              desc=dict(pistas=[dict(celda=[1], media_neta=5.0), dict(celda=[2], media_neta=5.0), dict(celda=[3], media_neta=5.0)]))
    res = dict(replica=[dict(n=150, media_neta=-1.0, ic90=[-1.5, -0.5]), dict(n=150, media_neta=3.0, ic90=[2.5, 3.5]),
                        dict(n=8, media_neta=-9.0, ic90=[-60.0, 40.0])])
    st = em._fin_atras(spec, st, res)
    assert st["etapa"] == "TOPES" and st["candidatas"] == [[1], [2], [3]]
    assert [v["veredicto"] for v in st["atras"]["veredictos"]] == ["EN_CONTRA_PASADO", "A_FAVOR", "NO_CONCLUYENTE"]


def test_atras_tiene_que_ser_anterior_al_desc():
    assert any("atras" in e for e in EM.problemas_campana(dict(SPEC, atras=[20250701, 20250901])))
    assert not any("atras" in e for e in EM.problemas_campana(dict(SPEC, atras=[20230101, 20231231])))
