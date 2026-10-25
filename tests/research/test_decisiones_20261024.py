"""Las cuatro decisiones de validación del 2026-10-24 (docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md):
1) nominación FDR q 0,10 como gate duro de DESC; 2) OOS por régimen con potencia (NO_CONCLUYENTE / EN_CONTRA_OTRO_REGIMEN);
3) α reservado por acta, libro único con lock y p de Romano-Wolf (k+1)/(B+1); 4) herencia de multiplicidad del linaje."""
import json
import multiprocessing as mp
import shutil
from pathlib import Path

import numpy as np
import pytest

from edgelab.funnel import escalera as E
from edgelab.funnel.libro_lord import RUTA_CANONICA, LibroLord
from edgelab.research import embudo as EM, linaje as LN

REPO = Path(__file__).resolve().parents[2]


def _libro(tmp_path):
    return LibroLord(tmp_path / "lord.json", permitir_otra_ruta=True)


# ----------------------------------------------------------------------------------------------- 3. libro de LORD++
def test_libro_unico_rechaza_otra_ruta(tmp_path):
    with pytest.raises(ValueError, match="uno solo"):
        LibroLord(tmp_path / "otro.json")
    assert LibroLord().ruta == RUTA_CANONICA


def test_reserva_consume_el_paso_y_resuelve_a_su_nivel(tmp_path):
    L = _libro(tmp_path)
    n1 = L.nivel("F"); r = L.reservar("F", "A/holdout")
    assert r["nivel"] == n1 and r["t"] == 1 and L.nivel("F") < n1                  # el α del acta ya no está disponible
    assert L.reservar("F", "A/holdout") == r                                          # idempotente: no gasta dos veces
    o = L.probar("F", "B/oos", [("x", 0.9)]); assert o["t"] == 2                     # un OOS en el medio toma el paso siguiente
    d = L.resolver("F", "A/holdout", [("regla", n1 / 2)])
    assert d["rechazo"] and d["nivel"] == n1 and d["t"] == 1
    assert L.resolver("F", "A/holdout", [("regla", 0.99)]) == d                      # una reserva se resuelve una sola vez
    assert L.estado["familias"]["F"]["rechazos"] == [1]
    with pytest.raises(KeyError):
        L.resolver("F", "C/holdout", [("regla", 0.0)])


def test_dos_actas_no_comparten_alfa(tmp_path):
    L = _libro(tmp_path)
    a = L.reservar("F", "A/holdout"); b = L.reservar("F", "B/holdout")
    assert (a["t"], b["t"]) == (1, 2) and b["nivel"] < a["nivel"]


def test_rechazo_tardio_queda_ordenado(tmp_path):
    L = _libro(tmp_path)
    L.reservar("F", "A"); L.probar("F", "B", [("x", 1e-9)])                          # t=2 rechaza antes de resolver t=1
    L.resolver("F", "A", [("y", 1e-9)])
    assert L.estado["familias"]["F"]["rechazos"] == [1, 2]


def _gastar(ruta, i):
    LibroLord(Path(ruta), permitir_otra_ruta=True).probar("F", f"r{i}", [("x", 0.5)])


def test_lock_dos_procesos_no_se_pisan(tmp_path):
    ruta = tmp_path / "lord.json"
    ctx = mp.get_context("spawn")
    ps = [ctx.Process(target=_gastar, args=(str(ruta), i)) for i in range(6)]
    for p in ps: p.start()
    for p in ps: p.join(30)
    est = json.loads(ruta.read_text(encoding="utf-8"))
    assert est["familias"]["F"]["t"] == 6 and len(est["corridas"]) == 6               # sin lock se perdían pasos


# ----------------------------------------------------------------------------------------------- 3. Romano-Wolf
def test_p_romano_wolf_nunca_cero():
    from edgelab.research import grilla_masiva as GM
    rng = np.random.default_rng(0); n = 400
    a = rng.integers(0, 3, n); ses = np.repeat(np.arange(40), 10)
    P = [GM.Perilla("a", 3, "grupo")]
    v = rng.normal(0, 1, n) + (a == 0) * 5.0                                         # efecto enorme: ningún remuestreo supera el máximo
    st = GM.estadisticas(*GM.tensor(P, [a], v))
    rw = GM.romano_wolf(P, [a], v, ses, st, B=50, seed=1)
    assert rw["B"] == 50 and rw["p_rw_del_maximo"] == pytest.approx(1 / 51)


def test_b_por_defecto_grande():
    import inspect
    from edgelab.research import grilla_generica as GG, grilla_masiva as GM
    assert inspect.signature(GM.romano_wolf).parameters["B"].default >= 1000 and GG.B_RW >= 1000


# ----------------------------------------------------------------------------------------------- 4. linaje
def test_linaje_bruto_recursivo_y_solo_endurece(tmp_path):
    reg = tmp_path / "reg.jsonl"; lib = tmp_path / "lin.jsonl"
    reg.write_text("\n".join(json.dumps(dict(family_id=f, n_trials=n)) for f, n in [("A", 1000), ("B", 50), ("C", 7)]), encoding="utf-8")
    LN.declarar("B", ["A"], "bruto", "x", libro=lib); LN.declarar("C", ["B"], "bruto", "y", libro=lib)
    m = LN.multiplicidad("C", lib, reg)
    assert m["n_heredado"] == 1050 and m["total"] == 1057                             # B y lo que B hereda de A
    with pytest.raises(ValueError): LN.declarar("C", ["B"], 10, "baja", libro=lib, registro=reg)
    with pytest.raises(ValueError): LN.declarar("C", [], "bruto", "quita padres", libro=lib, registro=reg)
    assert LN.problemas("Z", lib) and "no declaró" in LN.problemas("Z", lib)[0]


def test_linaje_exige_los_padres_del_libro_de_ventanas(tmp_path):
    ven = tmp_path / "v.jsonl"; lib = tmp_path / "lin.jsonl"
    ven.write_text(json.dumps(dict(tipo="consumida", familia="P", desde=1, hasta=2, relacionadas=["H"])) + "\n", encoding="utf-8")
    LN.declarar("H", [], 0, "dice ser raíz", libro=lib)
    assert any("incompleto" in e for e in LN.problemas("H", lib, ven))


def test_q_con_linaje():
    assert LN.q_con_linaje(0.05, 1.0, 1000, 0) == 0.05
    assert LN.q_con_linaje(0.05, 0.5, 1000, 1000) == pytest.approx(0.05 / 0.5 * 2)
    assert LN.q_con_linaje(1e-4, 1.0, 1000, 19_000_000) == 1.0                         # U1: con 19 M heredadas no hay nominación


def test_linajes_del_repo_coherentes():
    for f in ("AREAS_EXP_1_CRUZADO", "EXPANSION_ZONAS"):
        assert LN.problemas(f) == [], f
    assert LN.multiplicidad("AREAS_EXP_1_CRUZADO")["n_heredado"] >= 19_000_000


# ----------------------------------------------------------------------------------------------- 1. FDR en DESC
def _pista(celda, nom=True, q=0.01, m=1000, media=5.0, ic=(1.0, 9.0)):
    return dict(celda=celda, n=200, media_neta=media, sesiones=60, ic90=list(ic), p_sesiones=0.001, meseta=True, ratio_mov_friccion=10.0,
                nominada_fdr=nom, q_fdr=q, pi0_fdr=1.0, m_fdr=m)


SPEC = dict(cid="T", familia="TF", experimento="x", sensor="S", desc=[20250101, 20250601], oos=[20250701, 20250901],
            justificacion_economica="j", como_podria_refutarse="r", embudo=True)


def _em(tmp_path, linaje_n=0):
    lib = tmp_path / "lin.jsonl"
    if not lib.exists(): LN.declarar("TF", ["PADRE"] if linaje_n else [], linaje_n, "t", libro=lib)
    return EM.Embudo(tmp_path / "e", {}, libro=_libro(tmp_path), ahora=lambda: 1.0, log=lambda s: None, ventanas=tmp_path / "v.jsonl",
                     linajes=lib, registro_pruebas=tmp_path / "reg.jsonl")


def _st(em, **kw):
    st = dict(etapa="DESC", fase="CORRIENDO", historial=[], spec=SPEC, reglas={k: EM._cfg(SPEC, k) for k in EM.DEFECTOS},
              decisiones_20261024=dict(ts=0))
    st["reglas"]["linaje"] = em._multiplicidad(SPEC); st.update(kw); return st


def _res(pistas):
    return dict(E0=dict(cortes={}), canales=dict(total=dict(pistas=pistas, nominadas_fdr=sum(p["nominada_fdr"] for p in pistas))))


def test_desc_sin_nominacion_fdr_no_pasa(tmp_path):
    """El caso EXPZ-NQ: 0 nominadas, antes pasaban 3. Ninguna llega a candidata en DESC; desde el 2026-10-24 (falsos negativos)
    van a PISTAS (réplica en lote con LORD++) en vez de cerrar, y con la etapa apagada se cierra como antes."""
    em = _em(tmp_path)
    st = em._fin_desc(SPEC, _st(em), _res([_pista([0, 1], nom=False, q=0.4), _pista([2, 3], nom=False, q=0.3)]))
    assert st["etapa"] == "PISTAS" and "candidatas" not in st and st["pistas_replica"]["celdas"]
    spec = dict(SPEC, cid="T2"); st0 = _st(em, spec=spec); st0["reglas"]["pistas_replica"] = dict(activa=False)
    st = em._fin_desc(spec, st0, _res([_pista([0, 1], nom=False, q=0.4)]))
    assert st["etapa"] == "FIN" and st["fase"] == "SIN_CANDIDATAS"


def test_desc_nominada_pasa(tmp_path):
    em = _em(tmp_path)
    st = em._fin_desc(SPEC, _st(em), _res([_pista([0, 1]), _pista([2, 3], nom=False, q=0.4)]))
    assert st["etapa"] == "INDAGA" and st["candidatas"] == [[0, 1]]


def test_desc_linaje_le_quita_la_nominacion(tmp_path):
    reg = tmp_path / "reg.jsonl"; reg.write_text(json.dumps(dict(family_id="PADRE", n_trials=10_000_000)) + "\n", encoding="utf-8")
    em = _em(tmp_path, linaje_n="bruto")
    st = em._fin_desc(SPEC, _st(em), _res([_pista([0, 1], q=0.01, m=1000)]))
    assert st["etapa"] != "INDAGA" and "candidatas" not in st                          # estado congelado sin `como`: compuerta


def test_evaluar_sin_nominacion_no_confirma_aunque_replique():
    rng = np.random.default_rng(3); s = np.repeat(np.arange(200), 3); x = rng.normal(0.25, 1.0, len(s))
    d = E.resumen_sesiones(x, s); r = E.resumen_sesiones(rng.normal(0.25, 1.0, len(s)), s)
    v = E.evaluar(descubrimiento=d, nominada=False, n_pruebas_familia=10, replica=r, alfa_replica=0.05)
    assert v.estado == "SIN_POTENCIA" and "FDR" in v.motivos[0]


# ----------------------------------------------------------------------------------------------- 2. OOS por régimen
class _NoLibro:
    def probar(self, *a, **k): return dict(rechazo=False, confirmadas=[], nivel=0.05)


def _oos(tmp_path, ic, regimen=None, oos=(20250701, 20250901)):
    em = _em(tmp_path); em.libro = _NoLibro()
    spec = dict(SPEC, oos=list(oos), **({"regimen": regimen} if regimen else {}))
    st = _st(em, etapa="OOS", candidatas=[[0, 1]], desc=dict(pistas=[_pista([0, 1], media=5.0)]))
    st["reglas"]["regimen"] = EM._cfg(spec, "regimen")
    return em._fin_oos(spec, st, dict(replica=[dict(celda=[0, 1], media_neta=sum(ic) / 2, ic90=list(ic), p_sesiones=0.99)]))


def test_oos_con_potencia_en_contra_y_mismo_regimen_mata(tmp_path):
    st = _oos(tmp_path, (-3.0, -1.0))
    assert st["fase"] == "REFUTADA_OOS" and st["oos"]["veredictos"][0]["veredicto"] == "REFUTADA_OOS"


def test_oos_en_contra_en_otro_regimen_no_mata(tmp_path):
    st = _oos(tmp_path, (-3.0, -1.0), regimen=dict(definicion="volatilidad alta desde ago-2025", actual_desde=20250801), oos=(20230101, 20250731))
    assert st["etapa"] == "TOPES" and st["oos"]["veredictos"][0]["veredicto"] == "EN_CONTRA_OTRO_REGIMEN"


def test_oos_sin_potencia_es_no_concluyente(tmp_path):
    st = _oos(tmp_path, (-40.0, -1.0))                                                # IC enorme: no tiene potencia para 2,5 pts
    assert st["etapa"] == "TOPES" and st["oos"]["veredictos"][0]["veredicto"] == "NO_CONCLUYENTE"


def test_regimen_no_puede_definirse_con_el_holdout():
    assert EM._problemas_regimen(dict(definicion="x", actual_desde=20261005))
    assert EM._problemas_regimen(dict(definicion=None, actual_desde=20250801))
    assert EM._problemas_regimen(dict(definicion="x", actual_desde=None)) == []


# ----------------------------------------------------------------------------------------------- campañas en curso
@pytest.mark.parametrize("cid", ["EXPZ-NQ", "EXPZ-CFD"])
def test_expz_en_curso_queda_sin_candidatas(tmp_path, cid):
    """Consecuencia declarada de la decisión 1: las dos EXPZ pasaron DESC con 0 nominadas por FDR; al aplicar la regla se cierran.
    Usa el estado tal como estaba el 2026-10-24 (commit 92843801): el vivo se relanzó el 25 desde PREFLIGHT con el código vigente."""
    src = Path(__file__).parent / "fixtures" / "expz_20261024" / f"{cid}.json"
    (tmp_path / "e" / cid).mkdir(parents=True); shutil.copy(src, tmp_path / "e" / cid / "estado.json")
    spec = json.loads((REPO / f"config/autopilot/grillas/campanas/{cid}.json").read_text(encoding="utf-8"))
    em = EM.Embudo(tmp_path / "e", {}, libro=_libro(tmp_path), ahora=lambda: 1.0, log=lambda s: None)
    st = em.avanzar(spec)
    assert st["etapa"] == "FIN" and st["fase"] == "SIN_CANDIDATAS" and "2026-10-24" in st["motivo"]
