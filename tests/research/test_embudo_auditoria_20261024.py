"""Arreglos de la auditoría del embudo del 2026-10-24 (docs/research/auditoria_kaggle_20261024/): cada uno con el caso que fallaba."""
import json

import pandas as pd
import pytest

from edgelab.research import embudo as EM, embudo_runners as R, etapas as ET, holdout_ventanas as HV

SPEC = dict(cid="AUD-1", familia="AUD", experimento="tests.research.exp_u1_sin_be", sensor="DK:X", ejecucion="Y", desc=[20250801, 20250930],
            justificacion_economica="j", como_podria_refutarse="r", embudo=True, preflight_dinamico=False)


class Reg:
    def __init__(self): self.filas = []
    def ensure(self, cid, fam, n, nota=""): self.filas.append((cid, fam, n)); return True


class Runner:
    """Runner de juguete: estado y resultado configurables por etapa."""
    def __init__(self, estado="complete", res=None, falla_traer=False): self.est, self.res, self.falla, self.lanzadas = estado, res or {}, falla_traer, []
    def lanzar(self, spec, etapa, params, periodo): self.lanzadas.append((etapa, params)); return f"h{len(self.lanzadas)}"
    def estado(self, h): return self.est
    def traer(self, h):
        if self.falla: raise FileNotFoundError("RESULTADO.json")
        return self.res


def _embudo(tmp_path, run, registro="reg"):
    return EM.Embudo(tmp_path / "e", dict(kaggle=run, local=run), registro=Reg() if registro == "reg" else registro, libro=None,
                     ahora=lambda: 1_792_900_000, log=lambda s: None, ventanas=tmp_path / "v.jsonl")


def test_por_celda_conserva_orden_y_celdas_sin_operaciones():
    ops = pd.DataFrame(dict(celda=[1] * 6 + [2] * 6, t=range(12), ses=[1, 1, 2, 2, 3, 3] * 2, k=range(12), neto=[1.0, 2, 3, 1, 2, 3, -1, -2, -3, -1, -2, -3]))
    r = ET._por_celda(ops, 3, ET._riesgo)
    assert len(r) == 3 and r[0] == dict(n=0) and r[1]["media"] == pytest.approx(2.0) and r[2]["media"] == pytest.approx(-2.0)
    m = ET._por_celda(ops, 3, ET._mitades)
    assert m[0]["por_mitad"] == [dict(n=0), dict(n=0)] and len(m[1]["por_mitad"]) == 2
    assert ET._por_celda(pd.DataFrame(), 2, ET._riesgo) == [dict(n=0), dict(n=0)]


def test_resultado_ilegible_cuenta_como_falla_y_bloquea_a_la_tercera(tmp_path):
    run = Runner(falla_traer=True); em = _embudo(tmp_path, run)
    st = em.estado(SPEC); st.update(etapa="DESC", fase="PENDIENTE", reglas={k: EM._cfg(SPEC, k) for k in EM.DEFECTOS}); em._guardar(SPEC, st)
    for _ in range(6):
        st = em.avanzar(SPEC)
        if st["etapa"] == "FIN": break
    assert st["fase"] == "BLOQUEADA" and "sin resultado legible" in st["motivo"]


def test_sin_registro_no_se_lanza_una_etapa_con_desenlaces(tmp_path):
    run = Runner(); em = _embudo(tmp_path, run, registro=None)
    st = em.estado(SPEC); st.update(etapa="DESC", fase="PENDIENTE", reglas={k: EM._cfg(SPEC, k) for k in EM.DEFECTOS}); em._guardar(SPEC, st)
    with pytest.raises(RuntimeError, match="sin registro"): em.avanzar(SPEC)
    assert run.lanzadas == []


def test_topes_registra_los_topes_que_corren():
    reg = Reg(); em = EM.Embudo("x", {}, registro=reg)
    em._registrar(SPEC, "TOPES", dict(celdas=[[0], [1]], topes=[None, ["pts", 20.0], ["mult", 3.0]]))
    em._registrar(dict(SPEC, cid="AUD-2"), "TOPES", dict(celdas=[[0]], topes=None))
    assert reg.filas == [("embudo/AUD-1/topes", "AUD", 4), ("embudo/AUD-2/topes", "AUD", len(ET.TOPES_ESTANDAR) - 1)]


def test_reglas_congeladas_y_holdout_solo_hacia_adelante():
    st = dict(reglas=dict(seleccion=dict(max_candidatas=3), holdout=dict(desde=20261023, n_fijo=150, conteo_cada_s=86400)))
    vivo = dict(SPEC, seleccion=dict(max_candidatas=50), holdout=dict(desde=20261001, n_fijo=20))
    assert EM._cfg(vivo, "seleccion", st) == dict(max_candidatas=3)
    assert EM._cfg(vivo, "holdout", st) == dict(desde=20261023, n_fijo=150, conteo_cada_s=86400)                   # no vuelve atrás
    assert EM._cfg(dict(SPEC, holdout=dict(desde=20261101)), "holdout", st)["desde"] == 20261101                   # adelante, sí


def test_cambio_de_identidad_despues_de_arrancar_bloquea(tmp_path):
    em = _embudo(tmp_path, Runner())
    st = em.estado(SPEC); st.update(etapa="DESC", fase="PENDIENTE", reglas={k: EM._cfg(SPEC, k) for k in EM.DEFECTOS}); em._guardar(SPEC, st)
    st = em.avanzar(dict(SPEC, familia="OTRA"))
    assert st["fase"] == "BLOQUEADA" and "familia" in st["motivo"]


def test_campana_a3_y_holdout():
    assert EM.verificar_campana(SPEC) == []
    assert any("HOLDOUT-A3" in e for e in EM.verificar_campana(dict(SPEC, sensor="DK:USATECHIDXUSD", ejecucion="NQ", desc=[20250805, 20260930])))
    assert any("HOLDOUT-A3" in e for e in EM.verificar_campana(dict(SPEC, sensor="ES", ejecucion=None, desc=[20250805, 20260601])))
    assert any("toca el holdout" in e for e in EM.verificar_campana(dict(SPEC, oos=[20260401, 20261005])))
    assert any("frontera" in e for e in EM.verificar_campana(dict(SPEC, holdout=dict(desde=20260915))))


def test_campanas_del_repo_pasan_el_chequeo_de_campana_y_declaran_conductor():
    from pathlib import Path
    for f in sorted((Path(__file__).resolve().parents[2] / "config/autopilot/grillas/campanas").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if not d.get("embudo"): continue
        assert d.get("conductor") in EM.CONDUCTORES, f.name
        if d.get("activa", True): assert EM.verificar_campana(d) == [], f.name


def test_un_solo_conductor(tmp_path):
    c = tmp_path / "c"; c.mkdir()
    (c / "a.json").write_text(json.dumps(dict(SPEC, cid="A", conductor="local"))); (c / "b.json").write_text(json.dumps(dict(SPEC, cid="B")))
    run = Runner(); out = EM.avanzar_todas(c, _embudo(tmp_path, run), conductor="debian")
    assert {o["cid"] for o in out if "omitida" in o} == {"A", "B"} and run.lanzadas == []


def test_slug_sin_guion_bajo(tmp_path):
    k = R.KaggleRunner(carpeta=tmp_path, dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado")
    spec = dict(cid="X_3", experimento="tests.research.exp_u1_sin_be", sensor="DK:USATECHIDXUSD", ejecucion="NQ")
    a = k.argumentos(spec, "HOLDOUT_CONTEO", dict(celdas=[[0]], acta=dict(cid="X_3")), [20261023, 20261101])
    slug = a[a.index("--slug") + 1]
    assert "_" not in slug and slug == "nicolasbuttaro/embudo-x-3-holdout-conteo-20261023"


def test_libro_de_ventanas_del_estado_se_une_al_del_repo(tmp_path):
    repo, est = tmp_path / "repo.jsonl", tmp_path / "estado.jsonl"
    repo.write_text(json.dumps(dict(tipo="consumida", familia="A", desde=20261001, hasta=20261022, relacionadas=[])) + "\n")
    HV.registrar_apertura("B", "c1", 20261023, 150, est)
    assert HV.sincronizar(repo, est) == 1 and HV.sincronizar(repo, est) == 0
    assert {r["tipo"] for r in HV.leer(est)} == {"consumida", "apertura"} and HV.problemas("A", 20261010, "c9", est)
