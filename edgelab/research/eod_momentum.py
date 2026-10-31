"""EOD-MOM (2026-10-31): momentum intradía hacia la última media hora del horario regular (15:30–16:00 ET).

Fuente: Gao, Han, Li y Zhou (2018), "Market Intraday Momentum", Journal of Financial Economics: el retorno de la primera media hora
y el de la penúltima predicen el de la última en el S&P 500 (citado por @davidtrades_model, post #27, en las estrategias guardadas);
flujo de cobertura de opciones 0DTE al cierre (@wisefoxtraders, posts #4, #13 y #20). Pre-registro:
docs/research/paquete_20261031/SPEC_EOD_MOM.md. Es la única ventana del día que EdgeLab no cubre: las reglas actuales operan en la
apertura o en Asia, así que, si existe, diversifica la canasta.

Hipótesis económica: los rebalanceos forzados del cierre (fondos apalancados y ETF que replican un múltiplo diario, coberturas de
gamma de los vendedores de opciones) compran lo que ya subió en el día y venden lo que bajó, y lo ejecutan en la última media hora;
los operadores informados que llegan tarde lo hacen en la penúltima. Si el efecto es de flujo y no de información, el signo se
mantiene con el tamaño del movimiento y depende del régimen de volatilidad.

Construcción (causal; horario de Nueva York con verano): r1 = cierre de la vela que cierra a las 10:00 − apertura de la vela de las
09:30; rp = cierre a las 15:30 − cierre a las 15:00. Decisión al cierre de la vela de las 15:30, entrada en el primer tick de la
siguiente, salida forzada en la apertura de la vela de las 15:59 (por la salida por línea del simulador) o antes por stop.
Perillas: regla de dirección (signo de r1, signo de rp, ambas de acuerdo), magnitud del retorno usado relativa al rango del día
(terciles), régimen de volatilidad (terciles de RV 30 / RV 390, `regimen_sesion.rv_relativa`) y eficiencia del día 09:30–15:30.
Ejecuciones: stop a 1 o 2 rangos de la media hora 15:00–15:30, o sólo el de catástrofe (5 rangos).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny, rv_relativa

NOMBRE = "EOD-MOM"
INDICADORES = ["EOD-MOM"]
M_ABRE, M_R1, M_PEN0, M_DEC, M_SALE = 571, 600, 900, 930, 959       # minutos NY de CIERRE de cada vela clave

VARIABLES = [
    Variable("regla", "regla", "grupo", categoria=3),                       # 0 signo r1 · 1 signo rp · 2 ambas de acuerdo
    Variable("magnitud", "mag", "extremos", cuantiles=3),
    Variable("regimen_vol", "rv_rel", "extremos", cuantiles=3),
    Variable("eficiencia_dia", "er_dia", "ge", cortes=(0.25, 0.42)),
]
EJES_ORDINALES = (3,)
EJECUCIONES = [("STOP", 1.0), ("STOP", 2.0), ("STOP", 5.0)]
BASE = {"regla": 0, "magnitud": 2, "regimen_vol": 2, "eficiencia_dia": 0, "ejecución": 1}


def _por_sesion(ctx):
    m = minuto_ny(np.asarray(ctx["t"], np.int64)); ses = np.asarray(ctx["ses"], np.int64)
    return m, ses


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    m, ses = _por_sesion(ctx); rv = rv_relativa(c, ses, 30, 390)
    filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mm = m[idx]
        pos = {int(x): int(i) for x, i in zip(mm, idx)}
        if not all(x in pos for x in (M_ABRE, M_R1, M_PEN0, M_DEC)): continue
        a, b, p0, k = pos[M_ABRE], pos[M_R1], pos[M_PEN0], pos[M_DEC]
        if not a < b < p0 < k: continue
        r1 = c[b] - o[a]; rp = c[k] - c[p0]
        dia = slice(a, k + 1); rango = h[dia].max() - l[dia].min(); mov = np.abs(np.diff(c[a:k + 1])).sum()
        er = abs(c[k] - o[a]) / mov if mov > 0 else 0.0
        rpen = h[p0 + 1:k + 1].max() - l[p0 + 1:k + 1].min()
        for regla, r in ((0, r1), (1, rp), (2, r1 if np.sign(r1) == np.sign(rp) else 0.0)):
            if r == 0 or not rango > 0: continue
            filas.append((k, int(sg), regla, int(np.sign(r)), abs(r) / rango, float(rv[k]), er, rpen))
    return pd.DataFrame(filas, columns=["k", "ses", "regla", "lado", "mag", "rv_rel", "er_dia", "rpen"])


def lineas_salida(ctx) -> np.ndarray:
    """Fila 0 (compras) = +inf y fila 1 (ventas) = −inf en las velas que cierran entre 15:59 y 17:00 NY: fuerzan la salida."""
    m, _ = _por_sesion(ctx); f = (m >= M_SALE) & (m < 1020)
    return np.vstack([np.where(f, np.inf, np.nan), np.where(f, -np.inf, np.nan)])


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); c = np.asarray(ctx["c"], float)
    k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = c[k]
    d = np.maximum(ej[1] * D["rpen"].to_numpy(float), 2 * tick)
    st = np.where(s == 1, np.floor((e - d) / tick) * tick, np.ceil((e + d) / tick) * tick)
    return k, s, e, st, e + s * 1000.0 * tick, (s == -1).astype(np.int64)


def niveles(d, ej: tuple, ctx: dict):
    k, s, e, st, tp, kl = _lote(pd.DataFrame([d]), ej, ctx)
    return (int(k[0]), 2, int(s[0]), float(e[0]), float(st[0]), float(tp[0]), 0, int(kl[0]), 0.0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    out = np.full((len(D), 9), np.nan)
    if not len(D): return out
    k, s, e, st, tp, kl = _lote(D, ej, ctx)
    return np.column_stack([k, np.full(len(D), 2), s, e, st, tp, np.zeros(len(D)), kl, np.zeros(len(D))]).astype(float)
