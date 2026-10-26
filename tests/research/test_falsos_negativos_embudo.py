"""Falsos negativos del embudo (2026-10-24, pedido de Nico: «que el embudo no descarte candidatas reales, manteniendo el control
del error»). Cada corrección con un control de efecto PLANTADO (tiene que pasar) y uno de RUIDO puro (no tiene que pasar).
Informe: docs/research/revision_20261024/FALSOS_NEGATIVOS_EMBUDO_20261024.md."""
import json

import numpy as np
import pytest

from edgelab.funnel import escalera as E
from edgelab.funnel.libro_lord import LibroLord
from edgelab.research import embudo as EM, grilla_generica as GG, grilla_masiva as GM, linaje as LN


class Reg:
    def __init__(self): self.filas = []
    def ensure(self, cid, fam, n, nota=""): self.filas.append((cid, fam, n)); return True


class Fijo:
    def __init__(self, res): self.res, self.lanzadas = res, []
    def lanzar(self, spec, etapa, params, periodo): self.lanzadas.append((etapa, params, periodo)); return f"h{len(self.lanzadas)}"
    def estado(self, h): return "complete"
    def traer(self, h): return self.res[int(h[1:]) - 1]


def _ops(media, n_ses=60, por=3, sd=1.0, seed=0):
    rng = np.random.default_rng(seed); s = np.repeat(np.arange(n_ses), por)
    return rng.normal(media, sd, len(s)), s


def _fila(x, s, celda, nivel=None, m=1):
    rs = E.resumen_resuelto(x, s, nivel=nivel, m=m)
    return dict(celda=celda, n=len(x), media_neta=float(x.mean()), ic90=rs["ic"], p_sesiones=rs["p_unilateral"], sesiones=rs["n_sesiones"],
                n_boot=rs["n_boot"], metodo_p=rs["metodo_p"])


def _pista(celda, ic0, media=5.0, t_rw=2.0, nom=False, meseta=True):
    return dict(celda=celda, n=60, media_neta=media, sesiones=40, ic90=[ic0, ic0 + 8.0], p_sesiones=0.01, meseta=meseta, ratio_mov_friccion=10.0,
                t_rw=t_rw, nominada_fdr=nom, q_fdr=0.01 if nom else 0.5, pi0_fdr=1.0, m_fdr=1000)


SPEC = dict(cid="FN", familia="FNF", experimento="tests.research.exp_u1_sin_be", sensor="DK:X", desc=[20250101, 20250601],
            oos=[20250701, 20250901], justificacion_economica="j", como_podria_refutarse="r", embudo=True, n_celdas_por_canal=10,
            pistas_replica=dict(k=4))


def _em(tmp_path, runner=None, registro=None, n_heredado=0):
    lib = tmp_path / "lin.jsonl"
    if LN.declaracion(SPEC["familia"], lib) is None:
        if n_heredado:
            (tmp_path / "reg.jsonl").write_text(json.dumps(dict(family_id="PADRE", n_trials=n_heredado)) + "\n", encoding="utf-8")
        LN.declarar(SPEC["familia"], ["PADRE"] if n_heredado else [], "bruto" if n_heredado else 0, "t", libro=lib)
    return EM.Embudo(tmp_path / "e", dict(kaggle=runner, local=runner), registro=registro or Reg(),
                     libro=LibroLord(tmp_path / "lord.json", permitir_otra_ruta=True), ahora=lambda: 1.0, log=lambda s: None,
                     ventanas=tmp_path / "v.jsonl", linajes=lib, registro_pruebas=tmp_path / "reg.jsonl")


def _st(em, spec=SPEC, como="informacion", **kw):
    reglas = {k: EM._cfg(spec, k) for k in EM.DEFECTOS}
    reglas["pistas_replica"]["ventana"] = EM.ventana_pistas(spec, reglas["pistas_replica"])
    st = dict(etapa="DESC", fase="PENDIENTE", historial=[], spec=spec, reglas=dict(reglas, linaje=dict(em._multiplicidad(spec), como=como)),
              decisiones_20261024=dict(ts=0))
    st.update(kw); em._guardar(spec, st); return st


def _desc(pistas):
    return dict(celdas=10, E0=dict(cortes={}), canales=dict(total=dict(pistas=pistas, nominadas_fdr=0, evaluables=10)))


# ------------------------------------------------------------------------------------------- 1. pistas a réplica (ATJ-25)
def _hasta_pistas(tmp_path, efecto):
    """DESC sin nominadas -> PISTAS (congeladas, registradas, réplica en la ventana) -> decisión del lote con UN paso de LORD++."""
    pistas = [_pista([i, i, 0], ic0=10.0 - i, t_rw=1.0 + i) for i in range(6)]
    rep = []
    for j in range(4):                                                       # la réplica: celda 0 y 1 con efecto plantado (o todo ruido)
        x, s = _ops(efecto if j < 2 else 0.0, seed=100 + j)
        rep.append(_fila(x, s, [j, j, 0], nivel=0.0109, m=4))
    reg = Reg(); run = Fijo([_desc(pistas), dict(replica=rep)])
    em = _em(tmp_path, run, reg); _st(em)
    st = em.avanzar(SPEC); st = em.avanzar(SPEC)                            # lanza DESC; trae DESC -> PISTAS
    assert st["etapa"] == "PISTAS" and st["pistas_replica"]["celdas"] == [[0, 0, 0], [1, 1, 0], [2, 2, 0], [3, 3, 0]]   # por cota inferior, k = 4
    st = em.avanzar(SPEC)                                                    # lanza PISTAS: registrada ANTES de correr
    assert ("embudo/FN/pistas", "FNF", 4) in reg.filas
    etapa, params, periodo = run.lanzadas[-1]
    assert etapa == "REP" and periodo == SPEC["oos"] and params["resolucion"]["m"] == 4
    st = em.avanzar(SPEC)
    return st, em


def test_pistas_efecto_plantado_se_confirma_y_sigue_a_indaga(tmp_path):
    st, em = _hasta_pistas(tmp_path, efecto=0.8)
    assert st["etapa"] == "INDAGA" and st["candidatas"] == [[0, 0, 0], [1, 1, 0]], st.get("motivo")
    fam = em.libro.estado["familias"]["FNF"]
    assert fam["t"] == 1 and fam["rechazos"] == [1]                           # el lote entero gastó UN paso
    assert all(p.get("nominada_replica") for p in st["desc"]["pistas"][:2]) and not st["desc"]["pistas"][2].get("nominada_replica")
    assert st["oos_cubierto_por_pistas"]                                      # la ventana fue el OOS: no se reusa
    assert EM.nominada(st["desc"]["pistas"][0], 10**9, "compuerta")[0]        # cuenta como nominada aguas abajo (revalidación)


def test_pistas_ruido_puro_no_confirma(tmp_path):
    st, em = _hasta_pistas(tmp_path, efecto=0.0)
    assert st["etapa"] == "FIN" and st["fase"] == "SIN_CANDIDATAS" and "pistas a réplica" in st["motivo"]
    assert em.libro.estado["familias"]["FNF"]["t"] == 1


def test_oos_cubierto_por_pistas_no_se_reusa(tmp_path):
    em = _em(tmp_path, Fijo([])); st = _st(em, etapa="OOS", candidatas=[[0]], oos_cubierto_por_pistas=True)
    st = em.avanzar(SPEC)
    assert st["etapa"] == "ATRAS" and st["historial"][-1]["nota"].startswith("el OOS es la ventana")


def test_elegir_pistas_ordena_por_cota_inferior_nunca_por_media():
    ps = [_pista([0, 0], ic0=1.0, media=99.0), _pista([1, 1], ic0=5.0, media=6.0), _pista([1, 2], ic0=4.0, media=7.0), _pista([2, 2], ic0=3.0, media=-1.0)]
    out = E.elegir_pistas_replica(ps, k=3, min_dif=2)
    assert [p["celda"] for p in out] == [[1, 1], [0, 0]]                      # [1,2] difiere en 1 perilla de [1,1]; media <= 0 fuera


def test_escalera_confirma_pista_replicada_y_no_el_ruido():
    x, s = _ops(0.4, seed=1); d = E.resumen_sesiones(x, s)
    r = E.resumen_sesiones(*_ops(0.4, seed=2))
    v = E.evaluar(descubrimiento=d, nominada=False, pista_replicada=True, n_pruebas_familia=10, replica=r, alfa_replica=0.01)
    assert v.estado == "CONFIRMADA_REPLICA" and v.numeros["via"] == "pista_replicada"
    rn = E.resumen_sesiones(*_ops(0.0, seed=3))
    vn = E.evaluar(descubrimiento=d, nominada=False, pista_replicada=True, n_pruebas_familia=10, replica=rn, alfa_replica=0.01)
    assert vn.estado in ("SIN_POTENCIA", "REFUTADA")
    assert E.evaluar(descubrimiento=d, nominada=False, n_pruebas_familia=10, replica=r, alfa_replica=0.01).estado == "SIN_POTENCIA"
    assert "pistas a réplica" in E.evaluar(descubrimiento=d, nominada=False, n_pruebas_familia=10).siguiente_paso


def test_problemas_de_la_ventana_de_pistas():
    ok = dict(SPEC); assert EM._problemas_pistas(ok) == []
    assert any("posterior al DESC" in e for e in EM._problemas_pistas(dict(SPEC, pistas_replica=dict(ventana=[20250501, 20250630]))))
    assert any("holdout" in e for e in EM._problemas_pistas(dict(SPEC, oos=None, pistas_replica=dict(ventana=[20260901, 20261015]))))
    assert any("superpone" in e for e in EM._problemas_pistas(dict(SPEC, pistas_replica=dict(ventana=[20250801, 20250930]))))
    nq = dict(SPEC, sensor="NQ", oos=None, desc=[20250801, 20260331])
    assert EM.ventana_pistas(nq) == list(EM.A3_REPLICA) and EM._problemas_pistas(nq) == []
    assert any("HOLDOUT-A3" in e for e in EM._problemas_pistas(dict(nq, desc=[20250801, 20260131], pistas_replica=dict(ventana=[20260201, 20260930]))))


# ------------------------------------------------------------------------------------------- 2. linaje: información, no compuerta
def test_linaje_como_informacion_nomina_y_compuerta_no(tmp_path):
    em = _em(tmp_path, n_heredado=10_000_000)
    p = [_pista([0, 1], ic0=2.0, nom=True)]
    st = em._fin_desc(SPEC, _st(em, como="informacion"), _desc(p))
    assert st["etapa"] == "INDAGA" and st["desc"]["pistas"][0]["q_linaje"] == 1.0  # el cobro queda publicado, no decide
    st = em._fin_desc(SPEC, _st(em, como="compuerta"), _desc([_pista([0, 1], ic0=2.0, nom=True)]))
    assert st["etapa"] != "INDAGA"
    assert EM.problemas_campana(dict(SPEC, linaje_como="otra"))[0].startswith("linaje_como")
    # ruido: sin nominación FDR el linaje como información no nomina nada
    assert not EM.nominada(_pista([0], ic0=1.0, nom=False), 0, "informacion")[0]


# ------------------------------------------------------------------------------------------- 3. número efectivo (Li-Ji)
def test_li_ji_con_matriz_y_bruto_con_aviso(tmp_path):
    rng = np.random.default_rng(0); base = rng.normal(size=(200, 1))
    M = np.hstack([base + 1e-3 * rng.normal(size=(200, 1)) for _ in range(10)])   # 10 variantes casi iguales
    r = E.n_efectivo_o_bruto(10, M); assert r["n"] < 3 and r["aviso"] is None
    rr = E.n_efectivo_o_bruto(10, rng.normal(size=(200, 10))); assert rr["n"] > 6     # ruido independiente: casi todas cuentan
    assert E.n_efectivo_o_bruto(10)["aviso"] and E.n_efectivo_o_bruto(10)["n"] == 10
    assert E.n_efectivo_o_bruto(1000, M)["n"] == 1000                                # matriz parcial: no se extrapola
    reg = tmp_path / "reg.jsonl"; lib = tmp_path / "lin.jsonl"; np.save(tmp_path / "m.npy", M)
    reg.write_text(json.dumps(dict(family_id="A", n_trials=10)) + "\n", encoding="utf-8")
    with lib.open("w", encoding="utf-8") as f:
        f.write(json.dumps(dict(familia="B", padres=["A"], n_efectivo_heredado="bruto", matriz_pnl=str(tmp_path / "m.npy"))) + "\n")
    m = LN.multiplicidad("B", lib, reg); assert m["n_heredado"] < 3 and m["metodo_n"].startswith("Li-Ji") and m["bruto_heredado"] == 10


def test_rep_usa_li_ji_entre_celdas_congeladas():
    rng = np.random.default_rng(1); n = 600; ses = np.repeat(np.arange(60), 10)
    a = rng.integers(0, 2, n); P = [GM.Perilla("a", 2, "eq_any")]
    cx = dict(perillas=P, indices=[a], net=rng.normal(size=n), ses=ses)
    M = GG.matriz_sesiones(cx, [(0,), (2,)])
    assert M.shape == (60, 2) and np.allclose(M.sum(), cx["net"][a == 0].sum() + cx["net"].sum())


# ------------------------------------------------------------------------------------------- 4. m del FDR = evaluables
def _grilla(efecto, seed=0):
    rng = np.random.default_rng(seed); n = 3000
    a = rng.integers(0, 6, n); b = np.where(rng.random(n) < 0.9, rng.integers(0, 3, n), rng.integers(3, 200, n))
    v = rng.normal(0, 1, n) + efecto * ((a == 0) & (b == 0))
    P = [GM.Perilla("a", 6, "grupo"), GM.Perilla("b", 200, "grupo")]
    return GM.estadisticas(*GM.tensor(P, [a, b], v))


def test_m_fdr_son_las_evaluables_plantado_y_ruido():
    st = _grilla(0.2)                                                          # p ~ 4e-4: entre q/1200 y q/18
    cr = GM.criba(st); viejo = GM.criba(st, m_sobre="celdas")
    assert cr["m"] == cr["evaluables"] == 18 and cr["celdas"] == 1200 and viejo["m"] == 1200
    assert (0, 0) in cr["nominadas"] and (0, 0) not in viejo["nominadas"]      # m inflado por celdas que nunca podían rechazar
    assert np.all(cr["q_valores"][~st["evaluable"]] == 1.0)
    # ruido puro: con m = evaluables el FDR sigue controlado (bajo la nula global, P(alguna nominación) <= q)
    falsas = np.mean([len(GM.criba(_grilla(0.0, seed=sd))["nominadas"]) > 0 for sd in range(200)])
    assert falsas <= 0.15, falsas


# ------------------------------------------------------------------------------------------- 5. meseta: ordena, no mata
def test_meseta_ordena_y_no_descarta(tmp_path):
    em = _em(tmp_path)
    p = [_pista([0, 1], ic0=9.0, nom=True, meseta=False), _pista([2, 3], ic0=2.0, nom=True, meseta=True)]
    st = em._fin_desc(SPEC, _st(em), _desc(p))
    assert st["etapa"] == "INDAGA" and st["candidatas"] == [[2, 3], [0, 1]]   # antes [0, 1] se descartaba (4 de 5 celdas de U1)


# ------------------------------------------------------------------------------------------- 6. resolución del bootstrap
def test_resolucion_sube_b_o_usa_analitico():
    assert E.n_boot_para(None) == 2000 and E.n_boot_para(0.01, m=20) == 20000 and E.n_boot_para(1e-6) == E.N_BOOT_MAX
    x, s = _ops(0.6, n_ses=80, seed=4)
    rs = E.resumen_resuelto(x, s, nivel=2e-5, m=40)
    assert rs["metodo_p"].startswith("analítico") and rs["p_unilateral"] < 2e-5 / 40     # plantado: rechaza al umbral de U1
    assert E.resumen_sesiones(x, s, n_boot=2000)["p_unilateral"] >= 1 / 2001           # con B = 2000 era imposible
    rn = E.resumen_resuelto(*_ops(0.0, n_ses=80, seed=5), nivel=2e-5, m=40); assert rn["p_unilateral"] > 0.01   # ruido: no
    rb = E.resumen_resuelto(x, s, nivel=0.01, m=5); assert rb["n_boot"] == 5000 and rb["metodo_p"].startswith("bootstrap")
    assert EM.sin_resolucion(2e-5, 2000, 40) and EM.sin_resolucion(2e-5, 2000, 40, rs["metodo_p"]) is None
    assert EM.sin_resolucion(0.0109, 20000, 4) is None


def test_t_de_student_contra_valores_conocidos():
    assert E.t_cola_superior(0.0, 7) == pytest.approx(0.5)
    assert E.t_cola_superior(2.0, 10) == pytest.approx(0.036694, abs=1e-6)
    assert E.t_cola_superior(4.26, 30) == pytest.approx(9.3025e-05, rel=1e-4)
    assert E.t_cola_superior(-2.0, 10) == pytest.approx(1 - 0.036694, abs=1e-6)


def test_resumen_sesiones_por_bloques_igual_al_directo(monkeypatch):
    x, s = _ops(0.1, seed=6)
    a = E.resumen_sesiones(x, s, n_boot=3000)
    monkeypatch.setattr(E, "_BLOQUE_BOOT", 1000)
    b = E.resumen_sesiones(x, s, n_boot=3000)
    assert a["p_unilateral"] == b["p_unilateral"] and a["ic"] == b["ic"]


# ------------------------------------------------------------------------------------------- 7. todas las nominadas se evalúan
def _canal(monkeypatch, efecto_si):
    monkeypatch.setattr(GG, "K_PISTAS", 1); monkeypatch.setattr(GG, "B_RW", 50); monkeypatch.setattr(GG, "MIN_SESIONES", 5)
    rng = np.random.default_rng(7); n_ses, por = 60, 40; ses = np.repeat(np.arange(n_ses), por); n = len(ses)
    a = rng.integers(0, 12, n); net = rng.normal(0, 1, n) + np.where(a < efecto_si, 1.0, 0.0)
    P = [GM.Perilla("a", 12, "grupo"), GM.Perilla("ejecución", 1, "grupo")]; idx = [a, np.zeros(n, int)]
    st = GM.estadisticas(*GM.tensor(P, idx, net))
    cx = dict(perillas=P, indices=idx, net=net, st=st, ses=ses, mes=np.where(ses < 30, "202501", "202502"), dist=np.full(n, 50.0), ejes=(0,))
    return GG.canales(None, cx, friccion=1.0, extra_adverso=0.0, log=lambda s: None)["total"]


def test_canales_ruido_no_nomina(monkeypatch):
    out = _canal(monkeypatch, efecto_si=0)
    assert out["nominadas_fdr"] == 0 and not any(p["nominada_fdr"] for p in out["pistas"])


def test_canales_evalua_todas_las_nominadas(monkeypatch):
    out = _canal(monkeypatch, efecto_si=8)                                         # 8 celdas con efecto real, 4 ruido
    nom = [p for p in out["pistas"] if p["nominada_fdr"]]
    assert out["k_evaluadas"]["por_romano_wolf"] <= 3 and out["k_evaluadas"]["nominadas_fdr"] == out["nominadas_fdr"] >= 8
    assert len(nom) >= 8 and sorted(p["celda"][0] for p in nom)[:8] == list(range(8))  # antes: sólo las 3 primeras por t de RW
    assert out["m_fdr"] == out["evaluables"] == 12 and out["celdas"] == 12
    assert sum(p["nominada_fdr"] and p["celda"][0] >= 8 for p in out["pistas"]) <= 1   # FDR: a lo sumo una falsa entre ~9


def test_celda_chica_de_la_replica_tambien_resuelve_el_umbral():
    """2026-10-25 (EXPZ-CFD): una pista con < 30 operaciones entraba al lote de LORD++ con un p de B=500 (piso 0,002) contra un
    umbral nivel/m de 1,8e-4: no podía confirmarse nunca. Ahora usa la misma resolución que las demás filas del lote."""
    import numpy as np
    from edgelab.research import grilla_generica as GG
    rng = np.random.default_rng(0); n = 26
    cx = dict(net=rng.normal(5, 1, n), ses=np.arange(n))
    r = GG._evaluar_mascara(np.ones(n, bool), cx, resolucion=dict(nivel=0.0036, m=20))
    assert r["chica"] and r["piso_p"] <= 0.0036 / 20 / 10 and r["p_sesiones"] <= 0.0036 / 20
    viejo = GG._evaluar_mascara(np.ones(n, bool), cx)
    assert viejo["n_boot"] == 500                                     # sin lote (marginales): igual que antes


def test_linaje_hereda_las_celdas_evaluables_no_las_registradas(tmp_path):
    """2026-10-25: el 96-98 % de las celdas de las grillas finas no llega a 30 operaciones; registradas antes de correr (cota), sólo
    las evaluables heredan multiplicidad. Sin dato de evaluables se sigue cobrando lo registrado."""
    import json
    from edgelab.research import linaje as LN
    reg = tmp_path / "reg.jsonl"; ev = tmp_path / "EVALUABLES.jsonl"
    reg.write_text("".join(json.dumps(r) + "\n" for r in (dict(campaign_id="a/desc", family_id="P", n_trials=1000), dict(campaign_id="b/desc", family_id="P", n_trials=50))))
    assert LN.pruebas_propias(reg, ev)["P"] == 1050
    LN.registrar_evaluables("a/desc", "P", 1000, 30, "test", ev)
    assert LN.pruebas_propias(reg, ev)["P"] == 80
    import pytest
    with pytest.raises(ValueError): LN.registrar_evaluables("a/desc", "P", 10, 30, "test", ev)
