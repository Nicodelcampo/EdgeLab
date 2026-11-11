"""LUXIMB-HFT: las zonas HFT entran a la vela correcta (sin mirar el futuro) y la condición «≥ n zonas en el 25 % inicial» marca."""
import numpy as np
import pandas as pd

from edgelab.research import grilla_generica as GG, luximb_hft as M, sintetico


def _ctx():
    return GG.contexto_m1(list(sintetico.bloques(dias=40, planta=False, seed=11)), tick=0.25)


def test_zonas_en_velas_causal():
    ctx = _ctx(); t = np.asarray(ctx["t"], float); n = len(t)
    ctx["por_bloque"] = pd.DataFrame(dict(t_ns=[int((t[10] - 30) * 1e9), int(t[10] * 1e9), int((t[-1] + 60) * 1e9)], lo=[1.0, 2.0, 3.0], hi=[1.5, 2.5, 3.5]))
    Z = M._zonas_en_velas(ctx, 0, n)
    assert Z["zi"].tolist() == [10, 10] and Z["zlo"].tolist() == [1.0, 2.0]       # la posterior a la última vela no entra


def test_zonas_densas_marcan_definiciones_con_zonas():
    ctx = _ctx(); t = np.asarray(ctx["t"], float); c = np.asarray(ctx["c"]); rng = np.random.default_rng(0)
    i = rng.integers(0, len(t), 20000)                                          # zonas finas en todos lados (como un mercado activo)
    ctx["por_bloque"] = pd.DataFrame(dict(t_ns=(t[i] * 1e9).astype(np.int64), lo=c[i] - 0.25, hi=c[i]))
    E = M.eventos(ctx)
    assert len(E) and E["D3_20_a0_z0"].any() and E["D3_20_a0_z1"].any()
    assert (E[[d for d in M.DEFINICIONES if d.endswith("_z1")]].sum().sum() >= E[[d for d in M.DEFINICIONES if d.endswith("_z5")]].sum().sum())
    assert (np.sign(E.ref - E.ext) == E.lado).all()
