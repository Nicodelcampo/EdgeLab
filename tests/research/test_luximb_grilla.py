"""LUXIMB-GRILLA: oráculos contra el código congelado del visor, casos de resultado conocido, causalidad y controles de punta a punta.

- detector y tabla de cruces (numba) contra `tools/luximb_parity/luximb_impulsos.py` (detect_act, crossed) con empates;
- la celda del visor reproduce, sobre un fixture sintético, las marcas y los niveles del script congelado
  (`luximb_impulsos.py --modo inicio ...` + la contabilidad de `escalera_candidatos_20261022.lux_trades`);
- ruido puro -> 0 nominadas (preflight); efecto plantado (reversión) -> lo encuentra y elige FADE.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from edgelab.research import areas_expansion as AX, grilla_generica as GG, indicadores as I, luximb_grilla as E, sintetico

REPO = Path(__file__).resolve().parents[2]
LUX = REPO / "tools/luximb_parity"


def _original():
    sys.path.insert(0, str(REPO))
    sp = importlib.util.spec_from_file_location("luximb_impulsos_orig", LUX / "luximb_impulsos.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def _ctx(dias, seed, planta=False):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=planta, seed=seed), tick=0.25)


def _ohlc_con_empates(n, seed):
    """Velas en una grilla gruesa de ticks: muchos empates de máximos, mínimos y cierres (lo que rompe un port descuidado)."""
    rng = np.random.default_rng(seed)
    c = 1000 + np.cumsum(rng.choice([-2, -1, 0, 0, 1, 2], n) + np.where(rng.random(n) < 0.03, rng.choice([-1, 1], n) * 12, 0)).astype(float)
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.integers(0, 2, n); l = np.minimum(o, c) - rng.integers(0, 2, n)
    t = np.arange(n) * 60.0; t[rng.random(n) < 0.004] += 4000                                        # algún hueco > 30 min
    return np.cumsum(np.r_[0.0, np.diff(t)]) + 60.0, o, h.astype(float), l.astype(float), c


# ----------------------------------------------------------------------------------------------- oráculos
def test_detector_igual_al_original():
    O = _original(); from edgelab.bridge.indicators import espejo_impulsos as EI
    for seed in range(4):
        t, o, h, l, c = _ohlc_con_empates(3000, seed)
        thr = E.ATR_K * E.atr_prev(h, l, c)
        assert np.array_equal(thr, E.ATR_K * EI.atr_prev(h, l, c, 14))
        ref = O.detect_act(t, h, l, c, np.ones(len(c)), thr, EI.params_of(dict(max_bars=E.MAX_BARS, atr_k=E.ATR_K)))
        T = E.detectar(t, h, l, c, 1.0)
        mio = [dict(d=int(T["d"][i]), a=float(T["a"][i]), ext=float(T["ext"][i]), i0=int(T["i0"][i]), iext=int(T["iext"][i]),
                    jconf=int(T["jconf"][i]), why=int(T["why"][i]), jact=int(T["jact"][i])) for i in range(len(T["d"]))]
        assert len(ref) > 20 and mio == ref


def test_tabla_igual_a_crossed():
    O = _original()
    for seed in range(3):                                   # precios en la grilla de 0,25: máximos, mínimos y bordes de zona empatan
        cx = _ctx(4, seed=seed + 10); t, o, h, l, c = (cx[x] for x in ("t", "o", "h", "l", "c"))
        Z = AX.zonas(t, o, h, l, c); oz = np.argsort(Z["zi"], kind="mergesort")
        zi, zlo, zhi = Z["zi"][oz], Z["zlo"][oz], Z["zhi"][oz]
        T = E.detectar(t, h, l, c, 0.25); d, i0, ja, ic = T["d"], T["i0"], T["jact"], T["jconf"]; pa = T["a"] * 0.25
        p0c = np.where(d == 1, l[i0], h[i0])
        zs = np.searchsorted(zi, i0 - E.VIDA, "left"); ze = np.searchsorted(zi, ic, "left")
        g, kb, ext, iext, rg, nz, nini = E._tabla_nb(d, i0, ja, ic, pa, p0c, zs, ze, zi, zlo, zhi, h, l, E.VIDA, np.array(E.FRACS))
        assert len(g) > 100 and nz.max() > 0
        for r in range(0, len(g), 7):
            gg = g[r]; ids = O.crossed(i0[gg], kb[r], d[gg] == 1, h, l, zi, zhi, zlo, E.VIDA, p1=ext[r])
            assert nz[r] == len(ids)
            pos = np.array([abs((zhi[z] + zlo[z]) / 2 - pa[gg]) / rg[r] for z in ids])
            assert [int((pos < f).sum()) for f in E.FRACS] == list(nini[r])


def _bundle(ctx, ruta):
    """Bundle mínimo con el formato que lee el script congelado: velas M1 (marca = apertura), una vela de 25t por minuto
    (así la rapidez en 25t y en M1 es la misma cuenta) y las zonas del mismo detector LUX-IMB."""
    t_open = (ctx["t"] - 60).astype(int)
    velas = [dict(time=int(t_open[i]), open=float(ctx["o"][i]), high=float(ctx["h"][i]), low=float(ctx["l"][i]), close=float(ctx["c"][i]),
                  volume=float(ctx["v"][i])) for i in range(len(t_open))]
    Z = AX.zonas(ctx["t"], ctx["o"], ctx["h"], ctx["l"], ctx["c"])
    zonas = [dict(id=f"z{i}", available_ts=int(t_open[Z["zi"][i]]) + 60, top=float(Z["zhi"][i]), bottom=float(Z["zlo"][i]),
                  kind=("OG" if Z["og"][i] else "VI")) for i in range(len(Z["zi"]))]
    B = dict(meta=dict(id="FIXTURE", tick_size=0.25, contract="FIX"), runs=[dict(zones=zonas)],
             bar_series=dict(time_1m=dict(candles=velas), tick_25=dict(candles=velas)))
    ruta.write_text(json.dumps(B), encoding="utf-8")


@pytest.mark.parametrize("zon", [E.VISOR_ZON, 1, 4])
def test_celda_visor_reproduce_el_script_congelado(tmp_path, monkeypatch, zon):
    """Estructura (no datos reales): mismas marcas (vela, dirección, A) y mismos niveles de entrada/TP/SL que el script congelado.
    El piso de 60 pts del visor se baja a 10 pts en los dos lados (el sintético no tiene impulsos de 60 pts)."""
    piso = 10.0
    monkeypatch.setattr(E, "AMP", tuple((p, piso if i == E.VISOR_AMP else f) for i, (p, f) in enumerate(E.AMP)))
    ctx = _ctx(14, seed=21); _bundle(ctx, tmp_path / "b.json")
    frac, mini = E.ZON[zon]
    args = ["--modo", "inicio", "--p-rango", "60", "--rango-min-abs", str(piso)] + \
           (["--min-ini", str(mini), "--share-ini", "0.5", "--frac-ini", str(frac)] if mini else ["--min-ini", "0", "--share-ini", "0"])
    subprocess.run([sys.executable, "-X", "utf8", str(LUX / "luximb_impulsos.py"), str(tmp_path / "b.json"), str(tmp_path / "i.json")] + args,
                   check=True, cwd=REPO, capture_output=True)
    ref = json.loads((tmp_path / "i.json").read_text(encoding="utf-8"))["impulsos"]
    D = E.disparos(ctx); V = D[(D.amp == E.VISOR_AMP) & (D.zon == zon)].sort_values("k").reset_index(drop=True)
    assert len(ref) >= 10, "el fixture no tiene marcas suficientes para comparar"
    assert [(r["ic"], 1 if r["dir"] == "up" else -1, r["p0"], r["i0"]) for r in sorted(ref, key=lambda r: r["ic"])] == \
           [(int(k), int(d), float(a), int(i)) for k, d, a, i in zip(V.k, V.d, V.pa, V.i0)]
    # niveles de la ejecución del visor = contabilidad de lux_trades: E_ = cierre - s·tick, TP = E_ - s·D, SL = E_ + s·0,2·D
    cl = ctx["c"]; ej = E.VISOR_EJ
    for r, (_, fila) in zip(sorted(ref, key=lambda r: r["ic"]), V.iterrows()):
        s = 1 if r["dir"] == "up" else -1; E_ = cl[r["ic"]] - s * 0.25; Dd = s * (E_ - r["p0"])
        nv = E.niveles(fila, ej, ctx)
        if Dd <= 0: assert nv is None; continue
        k, lim, lado, ent, st, tp, be = nv
        assert (k, lim, lado, be) == (r["ic"], 0, -s, 0) and ent == cl[r["ic"]]
        assert tp == pytest.approx(E_ - s * 1.0 * Dd, abs=1e-9) and tp == pytest.approx(r["p0"], abs=1e-9)
        assert st == pytest.approx(E_ + s * 0.2 * Dd, abs=1e-9)


def test_percentil_vectorial_igual_al_escalar():
    x = np.random.default_rng(3).choice(np.arange(0, 80, 0.25), 2000)
    assert list(np.percentile(x, [60.0, 80.0, 90.0])) == [float(np.percentile(x, p)) for p in (60.0, 80.0, 90.0)]


# ----------------------------------------------------------------------------------------------- casos armados a mano
def test_niveles_caso_armado():
    ctx = dict(c=np.array([100.0, 130.0]), tick=0.25)
    r = dict(k=1, d=1, pa=100.0)                                                    # impulso alcista de A = 100 a cierre 130
    assert E.niveles(r, ("FADE", "CIERRE", 1.0, 0.2, 0), ctx) == (1, 0, -1, 130.0, 129.75 + 0.2 * 29.75, 100.0, 0)
    assert E.niveles(r, ("CONT", "CIERRE", 0.5, 0.2, 1), ctx) == (1, 0, 1, 130.0, 129.75 - 0.2 * 29.75, 129.75 + 0.5 * 29.75, 1)
    k, lim, s, e, st, tp, be = E.niveles(r, ("FADE", "LIM25", 1.0, 0.2, 0), ctx)    # vender 25 % de D más arriba: 130 + 7,5
    assert (lim, s, e) == (1, -1, 137.5) and tp == 137.5 - 37.5 and st == 137.5 + 0.2 * 37.5
    k, lim, s, e, st, tp, be = E.niveles(r, ("CONT", "LIM10", 1.0, 0.5, 0), ctx)    # comprar el retroceso del 10 %: 130 - 3
    assert (lim, s, e) == (1, 1, 127.0) and tp == 127.0 + 27.0 and st == 127.0 - 13.5
    assert E.niveles(dict(k=1, d=1, pa=129.9), ("FADE", "CIERRE", 1.0, 0.2, 0), ctx) is None      # D <= 0 tras el tick en contra


def test_grilla_declarada():
    assert len(E.EJECUCIONES) == 112 and len(set(E.EJECUCIONES)) == 112
    assert all(tp >= 2 * sl for _, _, tp, sl, be in E.EJECUCIONES if be)            # ningún BE que no pueda armarse
    assert GG.n_celdas(E) == 907200
    c = E.celda_visor(); nombres = [p.nombre for p in GG.perillas(E, {})]
    assert c[nombres.index("amplitud")] == 1 and c[nombres.index("zonas")] == 2 and E.EJECUCIONES[c[-1]] == E.VISOR_EJ
    assert E.AMP[E.VISOR_AMP] == (60.0, 60.0) and E.ZON[E.VISOR_ZON] == (0.25, 3)


def test_faltante_no_cae_en_un_nivel():
    ctx = _ctx(12, seed=4); D = E.disparos(ctx)
    D.loc[D.index[:5], "vrel"] = np.nan
    idx = GG.discretizar(D, E.VARIABLES, GG.cortes_e0(D, E.VARIABLES))
    col = [v.nombre for v in E.VARIABLES].index("actividad")
    assert (idx[col][:5] == -1).all()


# ----------------------------------------------------------------------------------------------- causalidad y controles
def test_causal():
    ctx = _ctx(25, seed=5)
    assert I.causal(E.disparos, ctx, columnas=["k", "d", "i0", "pa", "amp", "zon", "vel", "vrel", "dirc", "nz", "nini25"]) == []


def test_control_plantado_fade_gana():
    ctx = _ctx(80, seed=3, planta=True)
    D = E.disparos(ctx).reset_index(drop=True); di, ei, pnl, _, _ = GG.simular_ops(E, D, ctx)
    fade = [i for i, e in enumerate(E.EJECUCIONES) if e[0] == "FADE"]; cont = [i for i, e in enumerate(E.EJECUCIONES) if e[0] == "CONT"]
    assert np.nanmean(pnl[np.isin(ei, fade)]) > np.nanmean(pnl[np.isin(ei, cont)])
    cierre = lambda lado: [i for i, e in enumerate(E.EJECUCIONES) if e[0] == lado and e[1] == "CIERRE"]
    assert np.nanmean(pnl[np.isin(ei, cierre("FADE"))]) > 0 > np.nanmean(pnl[np.isin(ei, cierre("CONT"))])


def test_control_plantado_el_embudo_elige_fade(monkeypatch):
    monkeypatch.setattr(GG, "B_RW", 40)
    ctx = _ctx(80, seed=3, planta=True)
    res, _ = GG.correr(E, ctx, modo="DESC", friccion=0.5, extra_adverso=0.25, log=lambda s: None)
    tot = res["canales"]["total"]
    assert tot["nominadas_fdr"] > 0
    lados = [E.EJECUCIONES[c[-1]][0] for c in tot["nominadas"]]
    assert lados.count("FADE") >= 0.8 * len(lados)
    # las pocas CONT nominadas son la propia reversión plantada, que el detector ve como un impulso en sentido contrario y
    # continuarla gana: es la misma dirección correcta. Las pistas (mejor t por sesiones) son todas FADE.
    assert all(E.EJECUCIONES[p["celda"][-1]][0] == "FADE" for p in tot["pistas"][:5])


def test_control_ruido():
    from edgelab.research.preflight import dinamico
    err, _ = dinamico(E, dias=150)
    assert err == [], err


def test_kernel_e0_al_dia(tmp_path):
    """El kernel committeado del E0 (SPEC §10) es el que sale de reconstruirlo con los módulos actuales. Si falla:
    python tools/kaggle_grilla/construir_kernel_experimento.py edgelab/research/luximb_grilla.py tools/kaggle_grilla/kernel_luximb_grilla.py --extra edgelab/research/agente/regimen.py --extra edgelab/regimes/state.py"""
    sys.path.insert(0, str(REPO / "tools/kaggle_grilla"))
    from construir_kernel_experimento import construir_experimento
    out = tmp_path / "k.py"
    construir_experimento("edgelab/research/luximb_grilla.py", str(out), ["edgelab/research/agente/regimen.py", "edgelab/regimes/state.py"])
    assert out.read_bytes() == (REPO / "tools/kaggle_grilla/kernel_luximb_grilla.py").read_bytes(), "kernel_luximb_grilla.py desactualizado: reconstruirlo"
