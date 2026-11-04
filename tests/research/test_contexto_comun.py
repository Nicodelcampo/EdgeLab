"""Tests de `edgelab.research.contexto_comun` (2026-11-04):
  1. Invariancia estricta al truncado (`por_vela` y `etiquetar_operaciones` bit a bit).
  2. `atr_sesion` y `vwap_sesion` reinician en cada cambio de sesión (el gap overnight no contamina el ATR).
  3. `minuto_ny` y `ctx_hora_ny` ajustan por horario de verano (EDT vs EST).
  4. Orientación según el lado `s` (`+1` largo vs `-1` corto) en `ctx_tendencia_favor`, `ctx_vwap_favor`, `ctx_eficiencia_contra` y `veto_huida`.
  5. `onh`/`onl` cerrados sin look-ahead (expuestos sólo desde `09:30 ET`) y `veto_muro` / `veto_horizonte` / `veto_liquidez_macro`.
  6. `ctx["calentamiento"]` puebla los cuantiles móviles de 20 sesiones desde el día 1 de la ventana evaluada, dando exactamente el mismo
     resultado que correr la serie continua desde el inicio del calentamiento.
"""
from __future__ import annotations

import numpy as np
import pytest

from edgelab.research import contexto_comun as CC, regimen_sesion as RS

T0_VERANO = 1754344800    # 2025-08-04 22:00 UTC = 18:00 EDT (apertura CME verano)
T0_INVIERNO = 1764630000  # 2025-12-01 23:00 UTC = 18:00 EST (apertura CME invierno)


def _ctx_sintetico(dias: int = 26, n_por_dia: int = 120, seed: int = 7, t0: int = T0_VERANO) -> dict:
    rng = np.random.default_rng(seed)
    partes = []
    p = 20000.0
    for d in range(dias):
        # Espaciamos las 120 velas a lo largo de la sesión (cada 10 minutos) para cubrir overnight, Londres, NY mañana, tarde y cierre
        t = t0 + d * 86400 + 600 * np.arange(1, n_por_dia + 1, dtype=np.int64)
        pasos = rng.normal(0.0, 2.0 + 0.5 * (d % 4), n_por_dia)
        c = np.round((p + np.cumsum(pasos)) * 4.0) / 4.0
        o = np.r_[p, c[:-1]]
        h = np.maximum(o, c) + 0.25 * rng.integers(1, 6, n_por_dia)
        l = np.minimum(o, c) - 0.25 * rng.integers(1, 6, n_por_dia)
        v = rng.integers(50, 400, n_por_dia).astype(float)
        ses = np.full(n_por_dia, 20250805 + d, dtype=np.int64)
        partes.append((t, o, h, l, c, v, ses))
        p = float(c[-1]) + rng.choice([-40.0, 40.0])  # salto entre sesiones para verificar que no contamina
    t, o, h, l, c, v, ses = (np.concatenate(x) for x in zip(*partes))
    return dict(t=t, o=o, h=h, l=l, c=c, v=v, ses=ses, tick=0.25)


def _cortar_ctx(ctx: dict, n: int) -> dict:
    claves = ("t", "o", "h", "l", "c", "v", "ses")
    out = {k: (v[:n].copy() if k in claves else v) for k, v in ctx.items()}
    return out


def test_por_vela_y_etiquetar_invariantes_al_truncado():
    ctx = _ctx_sintetico(dias=26, n_por_dia=120, seed=11)
    full = CC.por_vela(ctx)
    n_total = len(ctx["c"])
    # Probamos cortes a mitad de sesión y en bordes de sesión, antes y después de tener 20 sesiones cerradas
    for corte in (150, 720, 2650, n_total - 37):
        sub = _cortar_ctx(ctx, corte)
        parcial = CC.por_vela(sub)
        for k, arr in full.items():
            assert np.array_equal(arr[:corte], parcial[k], equal_nan=True), f"diferencia de truncado en {k} (corte={corte})"

    # Etiquetado de operaciones cuyos disparos ocurren antes de `corte`
    rng = np.random.default_rng(19)
    corte_op = 2800
    ks = rng.integers(600, corte_op - 5, size=80)
    lados = rng.choice([-1.0, 1.0], size=80)
    e = ctx["c"][ks]
    st = e - lados * 10.0
    tp = e + lados * 25.0
    O = np.column_stack([
        np.arange(80),
        np.zeros(80),
        ks,
        np.zeros(80),
        lados,
        e,
        st,
        tp,
        np.zeros(80),
    ])
    etq_full = CC.etiquetar_operaciones(ctx, O, desfase_vela=1)
    etq_sub = CC.etiquetar_operaciones(_cortar_ctx(ctx, corte_op), O, desfase_vela=1)
    for k in CC.ETIQUETAS_CONTEXTO:
        assert np.array_equal(etq_full[k], etq_sub[k]), f"etiquetar_operaciones cambió al truncar en {k}"


def test_atr_sesion_y_vwap_sesion_no_cruzan_sesiones():
    # Sesión 0 cierra en 100; Sesión 1 abre en 500 (salto overnight de 400 puntos), pero cada vela intra-sesión tiene rango 2.0
    n0, n1 = 20, 20
    ses = np.r_[np.full(n0, 20250805, np.int64), np.full(n1, 20250806, np.int64)]
    c = np.r_[np.full(n0, 100.0), np.full(n1, 500.0)]
    h = c + 1.0
    l = c - 1.0
    v = np.ones(n0 + n1, dtype=float) * 10.0

    atr = CC.atr_sesion(h, l, c, ses, w=14)
    # Primeras 13 velas de cada sesión son NaN; desde la vela 14 (índice 13 y 33), ATR debe valer exactamente 2.0 (sin el gap de 400)
    assert np.isnan(atr[:13]).all()
    assert np.allclose(atr[13:n0], 2.0)
    assert np.isnan(atr[n0:n0 + 13]).all()
    assert np.allclose(atr[n0 + 13:], 2.0)

    vw = CC.vwap_sesion(h, l, c, v, ses)
    assert np.allclose(vw[:n0], 100.0)
    assert np.allclose(vw[n0:], 500.0)


def test_minuto_ny_y_hora_ny_ajustan_dst():
    # 13:45 UTC en agosto (EDT, UTC-4) = 09:45 NY -> bloque 2 (ny_manana_0930_12)
    # 13:45 UTC en diciembre (EST, UTC-5) = 08:45 NY -> bloque 1 (londres_03_0930)
    t_ago = np.array([1754401500], dtype=np.int64)   # 2025-08-05 13:45:00 UTC
    t_dic = np.array([1764683100], dtype=np.int64)   # 2025-12-02 13:45:00 UTC
    assert RS.minuto_ny(t_ago)[0] == 9 * 60 + 45     # minuto NY del cierre de la vela M1 (09:45 EDT)
    assert RS.minuto_ny(t_dic)[0] == 8 * 60 + 45     # minuto NY del cierre de la vela M1 (08:45 EST)

    ctx = dict(
        t=np.r_[t_ago, t_dic],
        o=np.array([100.0, 100.0]),
        h=np.array([101.0, 101.0]),
        l=np.array([99.0, 99.0]),
        c=np.array([100.0, 100.0]),
        v=np.array([10.0, 10.0]),
        ses=np.array([20250805, 20251202], dtype=np.int64),
        tick=0.25,
    )
    V = CC.por_vela(ctx)
    assert int(V["hora_ny"][0]) == 2  # 09:44 ET -> ny_manana_0930_12
    assert int(V["hora_ny"][1]) == 1  # 08:44 ET -> londres_03_0930


def test_orientacion_segun_lado_s_y_veto_huida():
    ctx = _ctx_sintetico(dias=25, n_por_dia=100, seed=31)
    # En la última sesión imponemos una subida limpia y monotónica de 80 velas para que:
    # - c > open_ses y c > vwap
    # - delta60 > 0 y er60 == 1.0 > q90_er
    ini_ult = 24 * 100
    subida = 20500.0 + np.arange(100, dtype=float) * 3.0
    ctx["o"][ini_ult:] = subida - 1.5
    ctx["c"][ini_ult:] = subida
    ctx["h"][ini_ult:] = subida + 0.5
    ctx["l"][ini_ult:] = subida - 2.0

    k_test = ini_ult + 75
    e = float(ctx["c"][k_test])
    # Dos operaciones en la misma vela k_test: fila 0 = COMPRA (s=+1), fila 1 = VENTA (s=-1)
    O = np.array([
        [0, 0, k_test, 0, +1.0, e, e - 10.0, e + 20.0, 0],
        [1, 0, k_test, 0, -1.0, e, e + 10.0, e - 20.0, 0],
    ], dtype=float)

    etq = CC.etiquetar_operaciones(ctx, O, desfase_vela=0)
    # Tendencia del día: alcista -> a favor para compra (2 = favor_fuerte), en contra para venta (0 = contra_fuerte)
    assert etq["ctx_tendencia_favor"][0] == 2
    assert etq["ctx_tendencia_favor"][1] == 0
    # VWAP: precio por encima del VWAP -> a favor para compra (1), en contra para venta (0)
    assert etq["ctx_vwap_favor"][0] == 1
    assert etq["ctx_vwap_favor"][1] == 0
    # Impulso alcista con ER60=1.0 (> P90): la compra va a favor (eficiencia_contra=0, veto_huida=0);
    # la venta va contra el tren (eficiencia_contra=2, veto_huida=1)
    assert etq["ctx_eficiencia_contra"][0] == 0
    assert etq["ctx_eficiencia_contra"][1] == 2
    assert etq["veto_huida"][0] == 0
    assert etq["veto_huida"][1] == 1


def test_overnight_hl_sin_lookahead_y_veto_muro():
    ctx = _ctx_sintetico(dias=6, n_por_dia=120, seed=42)
    V = CC.por_vela(ctx)
    min_ny = V["min_ny"]
    en_overnight = (min_ny >= 18 * 60) | (min_ny < 9 * 60 + 30)
    en_rth = (min_ny >= 9 * 60 + 30) & (min_ny < 18 * 60)
    # Durante el overnight (antes de 09:30 ET), onh y onl son siempre NaN (no se exponen mientras siguen formándose)
    assert np.isnan(V["onh"][en_overnight]).all()
    assert np.isnan(V["onl"][en_overnight]).all()
    assert np.isfinite(V["onh"][en_rth]).all()
    assert np.isfinite(V["onl"][en_rth]).all()

    # Elegimos una vela en horario RTH de la sesión 4 donde conocemos PDH
    k = int(np.flatnonzero(en_rth & (ctx["ses"] == 20250809))[10])
    pdh = float(V["pdh"][k])
    assert np.isfinite(pdh)
    # Operación 0: compra desde pdh - 10 hasta pdh + 10 (atraviesa el muro PDH -> vetada = 1)
    # Operación 1: compra muy lejos de todos los muros (pasa = 0)
    techo_libre = max(pdh, float(V["onh"][k]), float(V["vwap"][k])) + 500.0
    O = np.array([
        [0, 0, k, 0, +1.0, pdh - 10.0, pdh - 20.0, pdh + 10.0, 0],
        [1, 0, k, 0, +1.0, techo_libre, techo_libre - 10.0, techo_libre + 15.0, 0],
    ], dtype=float)
    etq = CC.etiquetar_operaciones(ctx, O)
    assert etq["veto_muro"][0] == 1
    assert etq["veto_muro"][1] == 0


def test_calentamiento_equivale_a_serie_continua():
    ctx_total = _ctx_sintetico(dias=28, n_por_dia=80, seed=55)
    corte_cal = 22 * 80  # 22 sesiones de calentamiento, 6 sesiones evaluadas
    cal = _cortar_ctx(ctx_total, corte_cal)
    claves = ("t", "o", "h", "l", "c", "v", "ses")
    ctx_eval = {k: (ctx_total[k][corte_cal:].copy() if k in claves else ctx_total[k]) for k in ctx_total}
    ctx_eval["calentamiento"] = cal

    v_total = CC.por_vela(ctx_total)
    v_eval = CC.por_vela(ctx_eval)
    for k in v_total:
        assert np.array_equal(v_total[k][corte_cal:], v_eval[k], equal_nan=True), f"calentamiento difiere en {k}"
    # Y desde la primera vela de ctx_eval los cuantiles de 20 sesiones ya están poblados
    assert np.isfinite(v_eval["q33_vol_d"][0])
    assert np.isfinite(v_eval["q90_er"][0])


def test_etapa_marginales_incluye_contexto_comun_y_vetos():
    from pathlib import Path
    from edgelab.research import etapas as ET, grilla_generica as GG, rango_preapertura as RP, sintetico
    ctx = GG.contexto_m1(sintetico.bloques(dias=30, planta=False, seed=9), tick=0.25)
    cortes = GG.cortes_e0(RP.disparos(ctx), RP.VARIABLES)
    r = ET.ejecutar("MARGINALES", RP, ctx, friccion=0.5, extra_adverso=0.25, params=dict(cortes=cortes, estadistico="R"), log=lambda s: None)
    mg = r["marginales_globales"]
    for k in CC.ETIQUETAS_CONTEXTO:
        assert k in mg and (k + ".etiquetas") in mg, f"falta {k} en marginales_globales"

    # Verificar que JForex EdgeLabU1Cruzado.java tiene tope de 240 min y cierreNY 16:59 igualados con Python
    java_src = (Path(__file__).resolve().parents[2] / "nt8_tools/jforex/EdgeLabU1Cruzado.java").read_text(encoding="utf-8")
    assert 'public String cierreNY = "16:59";' in java_src
    assert "public int maxDuracionMin = 240;" in java_src
    assert "proximoCierreMs(" in java_src



def test_marginales_bruto_en_R_y_fallo_no_tumba(monkeypatch):
    """2026-11-04: `correr` guarda los marginales del bruto (sin fricción) junto a los del neto; con fricción > 0 el bruto suma más.
    Si el contexto común falla, la corrida sigue y deja el error en el resultado."""
    from edgelab.research import cvgap2 as X, grilla_generica as GG, sintetico, contexto_comun as CC
    ctx = GG.contexto_m1(sintetico.bloques(dias=40, planta=False, seed=19), tick=0.25)
    monkeypatch.setattr(X, "NORMALIZAR", "riesgo", raising=False)
    res, _ = GG.correr(X, ctx, modo="MARG", friccion=1.0, extra_adverso=0.0, log=lambda *a: None)
    assert "marginales_globales_bruto" in res and "contexto_comun_error" not in res
    neto = sum(f["suma"] for f in res["marginales_globales"]["ctx_hora_ny"])
    bruto = sum(f["suma"] for f in res["marginales_globales_bruto"]["ctx_hora_ny"])
    assert bruto > neto
    monkeypatch.setattr(CC, "marginales_contexto", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    res2, _ = GG.correr(X, ctx, modo="MARG", friccion=1.0, extra_adverso=0.0, log=lambda *a: None)
    assert res2["contexto_comun_error"].startswith("RuntimeError") and res2["marginales_globales"]
