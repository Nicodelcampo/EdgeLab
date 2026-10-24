"""Auditoría del embudo para el Debian (2026-10-24): cada test fija un error encontrado que hacía fallar, contar de menos o
decidir sobre la celda equivocada en una campaña real. Informe: docs/research/AUDITORIA_EMBUDO_DEBIAN_20261024.md."""
import json

import numpy as np
import pandas as pd
import pytest

from edgelab.research import embudo as EM, embudo_runners as ER, etapas as ET, grilla_generica as GG, u1_indaga as U


class Reg:
    def __init__(self): self.filas = []
    def ensure(self, cid, fam, n, nota=""): self.filas.append((cid, fam, n)); return True


class Fijo:
    """Runner que devuelve resultados armados a mano, por etapa."""
    def __init__(self, res, estado="complete"): self.res, self.est, self.lanzadas = res, estado, []
    def lanzar(self, spec, etapa, params, periodo): self.lanzadas.append((etapa, params)); return etapa
    def estado(self, h): return self.est
    def traer(self, h): return self.res[h]


def spec(**k):
    d = dict(cid="T", familia="F", experimento="tests.research.exp_u1_sin_be", sensor="NQ", desc=[20250801, 20250930],
             justificacion_economica="j", como_podria_refutarse="r", embudo=True, preflight_dinamico=False, n_celdas_por_canal=1492992)
    d.update(k); return d


def embudo(tmp_path, runner, **k):
    from edgelab.research import linaje as LN
    if LN.declaracion("F", tmp_path / "lin.jsonl") is None: LN.declarar("F", [], 0, "raíz de prueba", libro=tmp_path / "lin.jsonl")
    return EM.Embudo(tmp_path / "e", dict(kaggle=runner, local=runner), registro=k.pop("registro", Reg()), libro=None,
                     ahora=k.pop("ahora", lambda: 1_792_900_000), log=lambda s: None, ventanas=tmp_path / "v.jsonl",
                     linajes=tmp_path / "lin.jsonl", registro_pruebas=tmp_path / "reg.jsonl")


# --- 1. una celda sin operaciones corría la lista de las demás ------------------------------------------------------------
def test_por_celda_conserva_el_indice_aunque_una_celda_no_opere():
    ops = pd.DataFrame(dict(celda=[0, 0, 2, 2, 2], neto=[1.0, 2, 3, 4, 5], ses=[1, 1, 2, 2, 2]))
    r = ET.por_celda(ops, 3, lambda g: dict(n=len(g), suma=float(g.neto.sum())))
    assert [x["n"] for x in r] == [2, 0, 3] and r[2]["suma"] == 12.0                 # antes: [2, 3] y la celda 1 leía la 2


def test_integridad_con_celda_vacia_devuelve_una_entrada_por_celda():
    ctx = GG.contexto_m1(__import__("edgelab.research.sintetico", fromlist=["x"]).bloques(dias=40, planta=True, seed=21), tick=0.25)
    cortes = GG.cortes_e0(U.disparos(ctx), U.VARIABLES)
    buena = [0, 1, 0, 2, 2, 2, 3, 3, 3, U.EJECUCIONES.index(("E1A", "T1", "S3", 0))]
    vacia = list(buena); vacia[0] = 99                                                # nivel inexistente: cero operaciones
    r = ET.ejecutar("INTEGRIDAD", U, ctx, friccion=1.0, extra_adverso=0.5, params=dict(celdas=[vacia, buena], cortes=cortes), log=lambda s: None)
    for ret in (0, 1, 2, 5):
        assert len(r["latencia"][ret]) == 2 and r["latencia"][ret][0] == dict(n=0)
    assert r["latencia"][0][1]["n"] > 0 and all(np.isnan(r["placebo"][0]))


def test_fin_integridad_relanza_un_resultado_desalineado_del_kernel_viejo(tmp_path):
    em = embudo(tmp_path, Fijo({}))
    st = dict(etapa="INTEGRIDAD", fase="CORRIENDO", historial=[], spec=spec(), candidatas=[[0], [1]], reglas={})
    viejo = dict(latencia={"0": [dict(media=1.0)], "1": [dict(media=1.0)]}, placebo={"0": [0.0] * 5, "1": [0.0] * 5})   # 1 entrada para 2 celdas
    st = em._fin_integridad(spec(), st, viejo)
    assert st["etapa"] == "INTEGRIDAD" and st["fase"] == "PENDIENTE" and st["fallas"] == 1


# --- 2. el ciclo del Debian arma un LocalRunner nuevo por vuelta ---------------------------------------------------------
def test_local_runner_persiste_entre_instancias(tmp_path, monkeypatch):
    monkeypatch.setattr(ET, "ejecutar", lambda *a, **k: dict(conteo=[7]))
    monkeypatch.setattr(GG, "contexto_m1", lambda b, t: {})
    monkeypatch.setattr(ER, "friccion", lambda i: (1.0, 0.5))
    lec = {"NQ": lambda d0, d1, s: []}
    r1 = ER.LocalRunner(lec, {"NQ": 0.25}, carpeta=tmp_path / "_local")
    h = r1.lanzar(dict(cid="T", experimento="tests.research.exp_u1_sin_be", sensor="NQ"), "HOLDOUT_CONTEO", {}, [20261023, 20261101])
    r2 = ER.LocalRunner(lec, {"NQ": 0.25}, carpeta=tmp_path / "_local")              # la vuelta siguiente del ciclo
    assert r2.estado(h) == "complete" and r2.traer(h) == dict(conteo=[7])
    assert ER.LocalRunner(lec, {"NQ": 0.25}).estado(h) == "error"                    # sin carpeta: el comportamiento viejo
    h2 = r2.lanzar(dict(cid="T", experimento="tests.research.exp_u1_sin_be", sensor="NQ"), "HOLDOUT_CONTEO", {}, [20261023, 20261101])
    assert h2 != h                                                                    # nunca pisa un resultado anterior


# --- 3. multiplicidad: el contador no puede quedar corto ------------------------------------------------------------------
def test_campana_sin_n_celdas_o_con_n_distinto_se_bloquea_en_preflight(tmp_path):
    assert EM.problemas_campana(spec()) == []
    assert any("falta n_celdas_por_canal" in e for e in EM.problemas_campana(spec(n_celdas_por_canal=None)))
    assert any("!=" in e for e in EM.problemas_campana(spec(n_celdas_por_canal=1000)))
    st = embudo(tmp_path, Fijo({})).avanzar(spec(n_celdas_por_canal=None))
    assert st["fase"] == "BLOQUEADA" and "n_celdas_por_canal" in st["motivo"]


def test_periodos_que_tocan_el_holdout_se_bloquean_antes_de_lanzar():
    assert any("desc" in e for e in EM.problemas_campana(spec(desc=[20250801, 20261005])))
    assert any("oos" in e for e in EM.problemas_campana(spec(oos=[20260401, 20261001])))
    assert any("holdout.desde" in e for e in EM.problemas_campana(spec(holdout=dict(desde=20260915))))


def test_desc_registra_dos_canales_y_rechaza_celdas_distintas_a_lo_registrado(tmp_path):
    reg = Reg(); run = Fijo({"DESC": dict(celdas=5, E0=dict(cortes={}), canales={})})
    em = embudo(tmp_path, run, registro=reg); s = spec()
    em.avanzar(s); em.avanzar(s)                                                      # PREFLIGHT, lanza DESC
    assert reg.filas == [("embudo/T/desc", "F", 2 * 1492992)]
    st = em.avanzar(s)
    assert st["fase"] == "BLOQUEADA" and "multiplicidad" in st["motivo"]


def test_topes_registra_las_variantes_que_corren_de_verdad(tmp_path):
    reg = Reg(); em = embudo(tmp_path, Fijo({}), registro=reg)
    em._registrar(spec(), "TOPES", dict(celdas=[[0], [1]], topes=[None, ["pts", 20.0]]))
    em._registrar(spec(cid="U"), "TOPES", dict(celdas=[[0]], topes=None))
    assert reg.filas == [("embudo/T/topes", "F", 2), ("embudo/U/topes", "F", len(ET.TOPES_ESTANDAR) - 1)]


# --- 4. reglas congeladas y campaña inmutable -----------------------------------------------------------------------------
def test_campana_editada_despues_del_preflight_se_bloquea(tmp_path):
    em = embudo(tmp_path, Fijo({})); s = spec(); em.avanzar(s)
    assert em.estado(s)["etapa"] == "DESC"
    st = em.avanzar(spec(desc=[20250801, 20250915]))
    assert st["fase"] == "BLOQUEADA" and "desc" in st["motivo"]


def test_adelantar_el_holdout_se_permite_y_atrasarlo_no(tmp_path):
    em = embudo(tmp_path, Fijo({}, estado="running")); em.avanzar(spec(holdout=dict(desde=20261023)))
    assert em._cambios(spec(holdout=dict(desde=20261101)), em.estado(spec())) == []
    assert em._cambios(spec(holdout=dict(desde=20261005)), em.estado(spec())) == ["holdout.desde hacia atrás"]


def test_las_compuertas_usan_las_reglas_congeladas(tmp_path):
    st = dict(reglas=dict(seleccion=dict(max_candidatas=1)))
    assert EM._reglas(spec(seleccion=dict(max_candidatas=50)), st, "seleccion")["max_candidatas"] == 1
    assert EM._reglas(spec(seleccion=dict(max_candidatas=50)), {}, "seleccion")["max_candidatas"] == 50   # estado viejo sin reglas


# --- 5. una etapa caída no espera para siempre; las fallas se cuentan por etapa -----------------------------------------
def test_kaggle_colgado_cuenta_como_falla_y_las_fallas_son_por_etapa(tmp_path):
    t = [1_792_900_000.0]; run = Fijo({}, estado="running"); em = embudo(tmp_path, run, ahora=lambda: t[0]); s = spec()
    em.avanzar(s); em.avanzar(s)                                                      # PREFLIGHT, lanza DESC
    t[0] += 3600; assert em.avanzar(s)["fase"] == "CORRIENDO"
    t[0] += EM.MAX_HORAS_KAGGLE * 3600; st = em.avanzar(s)
    assert st["fase"] == "PENDIENTE" and st["fallas"] == 1
    st["fallas"] = 2; st = em._siguiente(s, st, "INDAGA")
    assert st["fallas"] == 0


def test_traer_que_falla_no_rompe_el_ciclo(tmp_path):
    class Roto(Fijo):
        def traer(self, h): raise FileNotFoundError("sin RESULTADO.json")
    em = embudo(tmp_path, Roto({})); s = spec(); em.avanzar(s); em.avanzar(s)
    st = em.avanzar(s)
    assert st["fase"] == "PENDIENTE" and st["fallas"] == 1


# --- 6. TOPES: una variante sin drawdown no se excluye -------------------------------------------------------------------
def test_tope_sin_drawdown_es_elegible(tmp_path):
    mitad = [dict(media=2.0), dict(media=2.0)]
    res = dict(por_tope={"sin tope": [dict(media=2.0, total=10.0, drawdown_max=-5.0, por_mitad=mitad)],
                         "pts:50": [dict(media=2.0, total=10.0, drawdown_max=0.0, por_mitad=mitad)]})
    st = dict(etapa="TOPES", fase="CORRIENDO", historial=[], candidatas=[[0]], reglas={})
    st = embudo(tmp_path, Fijo({}))._fin_topes(spec(), st, res)
    assert st["etapa"] == "ACTA" and st["regla"]["tope"] == ["pts", 50.0]


# --- 7. el p del bootstrap tiene piso: se avisa cuando el nivel lo hace inalcanzable --------------------------------------
def test_aviso_de_sin_resolucion():
    assert EM.sin_resolucion(0.01, 2000) is None
    assert "sin resolución" in EM.sin_resolucion(1e-4, 2000)


def test_campanas_del_repo_pasan_el_chequeo_de_campana():
    from pathlib import Path
    for f in sorted((Path(__file__).resolve().parents[2] / "config/autopilot/grillas/campanas").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if not d.get("embudo"): continue
        err = EM.problemas_campana(d)
        if not d.get("activa", True):                       # U1_CRUZADO (apagada) reproduce la corrida a mano: su desc usó la réplica
            err = [e for e in err if "HOLDOUT-A3" not in e]   # de NQ y el PREFLIGHT la frena si alguien la enciende (auditoría 2026-10-24)
        assert err == [], f.name


def test_resultado_con_codigo_cambiado_queda_avisado(tmp_path):
    res = dict(celdas=1492992, E0=dict(cortes={}), canales={}, modulos={"edgelab/research/etapas.py": "0" * 64})
    em = embudo(tmp_path, Fijo({"DESC": res})); s = spec(); em.avanzar(s); em.avanzar(s)
    st = em.avanzar(s)
    assert st["codigo_cambiado"][0]["modulos"] == ["edgelab/research/etapas.py"]
    assert "AVISO DESC" in (tmp_path / "e" / "T" / "MEDIDO.md").read_text(encoding="utf-8")
