"""EXPANSION-ZONAS: definición de las dos variantes con un caso armado, causalidad, y control plantado (CONTRA gana con reversión)."""
import numpy as np
import pandas as pd

from edgelab.research import expansion_zonas as E, grilla_generica as GG, indicadores as I, sintetico


def test_variantes_dentro_y_antes_caso_armado(monkeypatch):
    # 60 velas planas en 100, luego subida fuerte. Zonas: una vieja justo debajo de A (ANTES), una creada en el 25 % inicial (DENTRO),
    # una creada arriba del 25 % (no cuenta) y una vieja lejos debajo (no cuenta).
    n = 80; c = np.full(n, 100.0); c[60:70] = np.linspace(101, 140, 10); c[70:] = 140
    h, l, o = c + 2, c - 2, c.copy(); t = np.arange(n) * 60.0 + 60           # ATR ~4: R = 8·ATR ~ 32 pts; se marca en c >= 130
    Z = dict(zi=np.array([30, 62, 66, 10]), zlo=np.array([92.0, 103.0, 130.0, 70.0]), zhi=np.array([96.0, 104.0, 131.0, 71.0]),
             zfin=np.array([200, 200, 200, 200]), og=np.array([True, False, True, False]))
    monkeypatch.setattr(E.AX, "zonas", lambda *a: Z)
    ctx = dict(o=o, h=h, l=l, c=c, v=np.ones(n), t=t, ses=np.zeros(n, int), seg=np.zeros(n, int))
    D = E.disparos(ctx)
    d = D[(D.d == 1)].sort_values("k").groupby("var").first()
    assert d.loc[0, "nz"] == 1 and d.loc[0, "ogvi"] == 0                       # DENTRO: sólo la zona VI creada en el 25 % inicial
    assert d.loc[1, "nz"] == 1 and d.loc[1, "ogvi"] == 2                       # ANTES: sólo la OG vieja pegada a A, por fuera


def test_causal():
    ctx = GG.contexto_m1(sintetico.bloques(dias=30, planta=False, seed=5), tick=0.25)
    assert I.causal(E.disparos, ctx, columnas=["k", "A", "d", "ri", "var", "nz", "vel", "ogvi", "pos", "tam"]) == []


def test_control_plantado_contra_gana():
    ctx = GG.contexto_m1(sintetico.bloques(dias=80, planta=True, seed=3), tick=0.25)
    D = E.disparos(ctx).reset_index(drop=True); di, ei, pnl, _, _ = GG.simular_ops(E, D, ctx)
    contra = [i for i, e in enumerate(E.EJECUCIONES) if e[0] == "CONTRA"]; favor = [i for i, e in enumerate(E.EJECUCIONES) if e[0] == "FAVOR"]
    assert np.nanmean(pnl[np.isin(ei, contra)]) > np.nanmean(pnl[np.isin(ei, favor)])


def test_control_ruido():
    from edgelab.research.preflight import dinamico
    err, _ = dinamico(E, dias=150)
    assert err == [], err
