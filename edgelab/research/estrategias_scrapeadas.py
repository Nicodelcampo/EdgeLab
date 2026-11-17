"""Estrategias de reels que juntó Nico (2026-11-08), medidas con las reglas tal como se ven, en R y con costos canónicos.
Pre-registro: `docs/research/estrategias_scrapeadas_20261108/PREREGISTRO.md`. Kemet (gaps) va aparte: `gap_continuacion.py`.

Tres familias, cada una devuelve operaciones (fecha, celda, lado, riesgo, bruto) desde un contexto M1 (`grilla_generica.contexto_m1`):
- ORO_RANGO (Italian Founder «Channel breakout GOLD»): rango de las 6 horas 03:00–09:00 Bucharest; desde las 09:00 stop de compra en el
  máximo y de venta en el mínimo (OCO); stop al otro lado del rango o a medio rango; salida 21:00 Bucharest o 4 h después.
  Más «martes débil» (SPX500): el martes a las 15:59 ET, si el martes cerró bajo su apertura y bajo la media de 40 cierres, compra;
  stop 1 ATR diario; salida al cierre del miércoles o del viernes.
- EMA_VWAP (AlphaZone): velas de 3 min en RTH, VWAP anclado a las 09:30 ET (volumen = volumen de tick del feed). Mecha que cruza el
  VWAP y cierre del otro lado (rechazo) → entrada en contra del cruce a la apertura de la vela siguiente; salida cuando una vela de
  3 min cierra del otro lado de la EMA9; stop en la mecha, a 1 o 2 ATR(14) de 3 min.
- ORB_EMA20 (FlexingJoe): rango 09:30–10:00 ET; primera vela de 10 min que cierra fuera → dirección; después, en velas de 2 min, primer
  toque de la EMA20 → entrada al nivel de la EMA20 (límite) en esa vela; stop al otro extremo del rango o a mitad del rango; objetivo
  1R, 2R o cierre del día. Una por día, entradas hasta las 15:00.

Simulación por velas (`_sim_velas`): el stop se revisa antes que el objetivo dentro de la vela (conservador); salidas por cierre al
precio de cierre de la vela. Es una aproximación declarada: no usa el orden de ticks dentro de la vela.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ORO_CELDAS = [(s, x) for s in ("rango", "medio") for x in ("21h", "4h")]
MARTES_CELDAS = [("miercoles",), ("viernes",)]
EV_CELDAS = [(s, f) for s in ("mecha", "atr1", "atr2") for f in ("rth", "2h")]
ORB_CELDAS = [(s, t) for s in ("opuesto", "medio") for t in (1.0, 2.0, 0.0)]          # objetivo 0 = cierre del día


def ctx_de_m1(D: pd.DataFrame) -> dict:
    """Contexto (t = fin de la vela en epoch UTC, o, h, l, c, v) desde un M1 con índice en hora de NY sin zona (m1_intradia.leer_m1)."""
    t = D.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT"); ok = ~t.isna(); D = D[ok]; t = t[ok].tz_convert("UTC")
    v = D.v.to_numpy(float) if "v" in D else np.ones(len(D))
    return dict(t=np.asarray((t - pd.Timestamp(0, tz="UTC")) // pd.Timedelta("1s"), dtype=np.int64) + 60, o=D.o.to_numpy(float),
                h=D.h.to_numpy(float), l=D.l.to_numpy(float), c=D.c.to_numpy(float), v=v)


def _hora(ctx, tz):
    lt = pd.to_datetime(ctx["t"] - 60, unit="s", utc=True).tz_convert(tz)
    return (lt.hour * 60 + lt.minute).to_numpy(), np.asarray(lt.strftime("%Y%m%d"), dtype=np.int64), lt.dayofweek.to_numpy()


def _agregar(o, h, l, c, v, grupos):
    """Velas agregadas por etiqueta de grupo consecutiva: (o, h, l, c, v, índice M1 de la última)."""
    corte = np.flatnonzero(np.r_[True, grupos[1:] != grupos[:-1]])
    fin = np.r_[corte[1:], len(grupos)] - 1
    return (o[corte], np.maximum.reduceat(h, corte), np.minimum.reduceat(l, corte), c[fin], np.add.reduceat(v, corte), fin)


def _ema(x, n):
    return pd.Series(np.asarray(x, float)).ewm(span=n, adjust=False).mean().to_numpy()


def _sim_velas(o, h, l, c, i0, entrada, d, sl, tp, salida_ok, ult):
    """Desde la vela i0 (inclusive) con entrada al precio `entrada`. Devuelve (bruto, motivo 1 stop / 2 objetivo / 3 regla o tiempo)."""
    st = entrada - d * sl; ob = entrada + d * tp if tp > 0 else None
    for i in range(i0, ult + 1):
        if (o[i] <= st) if d == 1 else (o[i] >= st): return d * (o[i] - entrada), 1        # auditoría 2026-11-16: gap más allá del stop → apertura
        if (l[i] <= st) if d == 1 else (h[i] >= st): return d * (st - entrada), 1
        if ob is not None and ((h[i] >= ob) if d == 1 else (l[i] <= ob)): return d * (ob - entrada), 2
        if i == ult or (salida_ok is not None and salida_ok(i)): return d * (c[i] - entrada), 3
    return d * (c[ult] - entrada), 3


def oro_rango(ctx) -> pd.DataFrame:
    o, h, l, c = ctx["o"], ctx["h"], ctx["l"], ctx["c"]; m, f, _ = _hora(ctx, "Europe/Bucharest"); filas = []
    for dia in np.unique(f):
        ix = np.flatnonzero(f == dia); mm = m[ix]
        r = ix[(mm >= 180) & (mm < 540)]; post = ix[mm >= 540]
        if len(r) < 300 or not len(post): continue
        hi, lo = h[r].max(), l[r].min(); w = hi - lo
        if w <= 0: continue
        k = next((j for j in post if h[j] >= hi or l[j] <= lo), None)
        if k is None or (h[k] >= hi and l[k] <= lo): continue                       # ambos en la misma vela: ambiguo, se descarta
        d = 1 if h[k] >= hi else -1; ent = max(o[k], hi) if d == 1 else min(o[k], lo)
        for celda in ORO_CELDAS:
            s, x = celda; sl = w if s == "rango" else w / 2
            lim = post[m[post] < 1260] if x == "21h" else post[(m[post] < m[k] + 240) & (m[post] < 1260)]
            if not len(lim) or lim[-1] < k: continue
            b, mot = _sim_velas(o, h, l, c, k, ent, d, sl, 0.0, None, int(lim[-1]))
            filas.append(dict(fecha=int(dia), celda=celda, lado=d, riesgo=float(sl), bruto=float(b), motivo=mot))
    return pd.DataFrame(filas)


def _diarias_rth(ctx):
    m, f, dw = _hora(ctx, "America/New_York"); rth = (m >= 570) & (m < 960); filas = []
    for dia in np.unique(f[rth]):
        ix = np.flatnonzero(rth & (f == dia))
        filas.append(dict(fecha=int(dia), dow=int(dw[ix[0]]), o=float(ctx["o"][ix[0]]), c=float(ctx["c"][ix[-1]]),
                          rango=float(ctx["h"][ix].max() - ctx["l"][ix].min()), lo=float(ctx["l"][ix].min()), n=len(ix)))
    D = pd.DataFrame(filas)
    if len(D): D["sma40"] = D.c.rolling(40).mean(); D["atr"] = D.rango.rolling(14).mean().shift(1)
    return D


def martes_debil(ctx) -> pd.DataFrame:
    D = _diarias_rth(ctx); filas = []
    for i in range(len(D) - 1):
        r = D.iloc[i]
        if r.dow != 1 or r.n < 380 or not (r.c < r.o and r.c < r.sma40 and r.atr > 0): continue
        for celda in MARTES_CELDAS:
            fin = i + 1 if celda[0] == "miercoles" else next((j for j in range(i + 1, min(i + 5, len(D))) if D.dow.iloc[j] == 4), None)
            if fin is None or fin >= len(D): continue
            st = r.c - r.atr; seg = D.iloc[i + 1: fin + 1]
            hit = seg.index[seg.lo <= st]
            b = (st - r.c) if len(hit) else (D.c.iloc[fin] - r.c)
            filas.append(dict(fecha=int(r.fecha), celda=celda, lado=1, riesgo=float(r.atr), bruto=float(b), motivo=1 if len(hit) else 3))
    return pd.DataFrame(filas)


def ema_vwap(ctx) -> pd.DataFrame:
    m, f, _ = _hora(ctx, "America/New_York"); rth = np.flatnonzero((m >= 570) & (m < 960)); filas = []
    if not len(rth): return pd.DataFrame()
    g = f[rth] * 1000 + (m[rth] - 570) // 3
    O, H, L, C, V, _ = _agregar(ctx["o"][rth], ctx["h"][rth], ctx["l"][rth], ctx["c"][rth], np.maximum(ctx["v"][rth], 1.0), g)
    dia = (g[np.r_[np.flatnonzero(np.r_[True, g[1:] != g[:-1]])]] // 1000)
    slot = g[np.r_[np.flatnonzero(np.r_[True, g[1:] != g[:-1]])]] % 1000
    tr = np.maximum(H - L, np.abs(H - np.r_[C[0], C[:-1]])); atr = pd.Series(tr).rolling(14).mean().shift(1).to_numpy()
    for d0 in np.unique(dia):
        ix = np.flatnonzero(dia == d0)
        if len(ix) < 100: continue
        tp = (H[ix] + L[ix] + C[ix]) / 3; vw = np.cumsum(tp * V[ix]) / np.cumsum(V[ix]); em = _ema(C[ix], 9)
        ocupado = -1
        for j in range(1, len(ix) - 1):
            if j <= ocupado: continue
            i = ix[j]; prev = vw[j - 1]
            if H[i] > prev and C[i] < prev and O[i] < prev: d = -1
            elif L[i] < prev and C[i] > prev and O[i] > prev: d = 1
            else: continue
            ent = O[ix[j + 1]]; ult = ix[-1]; fin_j = len(ix) - 1
            for celda in EV_CELDAS:
                s, fl = celda
                if fl == "2h" and slot[i] >= 40: continue
                sl = (d * (ent - L[i]) if d == 1 else d * (ent - H[i])) if s == "mecha" else (1 if s == "atr1" else 2) * atr[i]
                if not (np.isfinite(sl) and sl > 0): continue
                sal = lambda q, d=d: (C[q] < em[q - ix[0]] if d == 1 else C[q] > em[q - ix[0]])
                b, mot = _sim_velas(O, H, L, C, ix[j + 1], ent, d, sl, 0.0, sal, ult)
                filas.append(dict(fecha=int(d0), celda=celda, lado=d, riesgo=float(sl), bruto=float(b), motivo=mot))
            # una posición a la vez (por la celda base mecha/rth): la siguiente señal espera la salida por EMA
            k = next((q for q in range(j + 1, fin_j + 1) if (C[ix[q]] < em[q] if d == 1 else C[ix[q]] > em[q])), fin_j)
            ocupado = k
    return pd.DataFrame(filas)


def orb_ema20(ctx) -> pd.DataFrame:
    """Corregida 2026-11-08 (antes de mirar resultados): EMA20 continua sobre todas las velas de 2 min del feed (no sembrada a las
    09:30, que con 20 velas de historia no es la EMA del gráfico) y, en la vela de entrada, sólo cuenta el stop (el máximo de esa vela
    pudo ocurrir antes del toque: contar el objetivo ahí era optimista)."""
    o, h, l, c = ctx["o"], ctx["h"], ctx["l"], ctx["c"]; m, f, _ = _hora(ctx, "America/New_York"); filas = []
    tmin = (np.asarray(ctx["t"]) - 60) // 60                                          # minuto de inicio; 09:30 ET cae en minuto par
    O2, H2, L2, C2, _, fin2 = _agregar(o, h, l, c, np.ones(len(c)), tmin // 2)
    em_prev = np.r_[np.nan, _ema(C2, 20)[:-1]]                                       # EMA20 conocida al abrir cada vela de 2 min
    vela2 = np.repeat(np.arange(len(fin2)), np.diff(np.r_[-1, fin2]))                # vela de 2 min de cada M1
    for dia in np.unique(f):
        ix = np.flatnonzero(f == dia); mm = m[ix]
        orr = ix[(mm >= 570) & (mm < 600)]; post = ix[(mm >= 600) & (mm < 960)]
        if len(orr) < 25 or len(post) < 300: continue
        hi, lo = h[orr].max(), l[orr].min(); w = hi - lo
        if w <= 0: continue
        g10 = (m[post] - 600) // 10; d = 0; k10 = None
        for q in np.unique(g10):
            u = post[g10 == q][-1]
            if c[u] > hi: d, k10 = 1, u; break
            if c[u] < lo: d, k10 = -1, u; break
        if not d: continue
        rest = ix[(ix > k10) & (mm < 960)]
        if len(rest) < 2: continue
        v = np.unique(vela2[rest]); v = v[fin2[v] <= rest[-1]]
        hora = m[fin2[v]]
        j = next((q for q in v if m[fin2[q]] < 900 and np.isfinite(em_prev[q]) and ((L2[q] <= em_prev[q]) if d == 1 else (H2[q] >= em_prev[q]))), None)
        if j is None: continue
        ent = min(O2[j], em_prev[j]) if d == 1 else max(O2[j], em_prev[j]); ult = int(v[-1])
        for celda in ORB_CELDAS:
            s, rr = celda
            sl = d * (ent - (lo if d == 1 else hi)) if s == "opuesto" else d * (ent - (lo + w / 2))
            if not sl > 0: continue
            st = ent - d * sl
            if (L2[j] <= st) if d == 1 else (H2[j] >= st): b, mot = -sl, 1
            elif j == ult: b, mot = d * (C2[j] - ent), 3
            else: b, mot = _sim_velas(O2, H2, L2, C2, j + 1, ent, d, sl, rr * sl, None, ult)
            filas.append(dict(fecha=int(dia), celda=celda, lado=d, riesgo=float(sl), bruto=float(b), motivo=mot))
    return pd.DataFrame(filas)


FAMILIAS = {"ORO_RANGO": (oro_rango, ORO_CELDAS), "MARTES_DEBIL": (martes_debil, MARTES_CELDAS),
            "EMA_VWAP": (ema_vwap, EV_CELDAS), "ORB_EMA20": (orb_ema20, ORB_CELDAS)}

# ---------------------------------------------------------------- reels del 2026-11-16 (PREREGISTRO docs/research/reels_20261116/PREREGISTRO.md)
VL_CELDAS = [("vie_lun",), ("mie_jue",)]
DV_CELDAS = [("11h",), ("16h",)]
FR_CELDAS = [("cierre",), ("2R",)]


def _dias_rth(ctx):
    """Índices M1 de la RTH (09:30–16:00 NY) por fecha, con máximo, mínimo, apertura y día de la semana; sólo días con ≥ 380 velas."""
    m, f, dw = _hora(ctx, "America/New_York"); rth = (m >= 570) & (m < 960); out = []
    for dia in np.unique(f[rth]):
        ix = np.flatnonzero(rth & (f == dia))
        if len(ix) < 380 or m[ix[0]] > 574: continue
        out.append(dict(fecha=int(dia), dow=int(dw[ix[0]]), ix=ix, h=float(ctx["h"][ix].max()), l=float(ctx["l"][ix].min()), o=float(ctx["o"][ix[0]])))
    return out, m, f


def _pares_semana(D, dow_ref, dow_cmp, salto_cmp):
    """(ref, cmp, sig): día de referencia de semana `dow_ref`, el que se compara (`salto_cmp` días hábiles antes, con semana `dow_cmp`)
    y el día hábil siguiente; todos consecutivos en el calendario de datos (sin feriados en el medio)."""
    for i in range(salto_cmp, len(D) - 1):
        r, c, s = D[i], D[i - salto_cmp], D[i + 1]
        if r["dow"] != dow_ref or c["dow"] != dow_cmp: continue
        if (r["dow"] - c["dow"]) != salto_cmp or (s["dow"] - r["dow"]) % 7 not in (1, 3): continue
        if dow_ref == 4 and s["dow"] != 0: continue
        if dow_ref != 4 and s["dow"] != r["dow"] + 1: continue
        yield r, c, s


def viernes_lunes(ctx) -> pd.DataFrame:
    """Hougaard / AlphaZone: si el máximo RTH del viernes < el del jueves (o el del miércoles < el del lunes) y el lunes (jueves) abre
    DENTRO del rango del día de referencia → venta a la apertura 09:30, objetivo el mínimo de referencia, stop el máximo de referencia,
    salida al cierre 16:00. Velas M1; stop antes que objetivo dentro de la vela."""
    D, _, _ = _dias_rth(ctx); o, h, l, c = ctx["o"], ctx["h"], ctx["l"], ctx["c"]; filas = []
    for celda, (dr, dc, k) in (("vie_lun", (4, 3, 1)), ("mie_jue", (2, 0, 2))):
        for r, cmp_, s in _pares_semana(D, dr, dc, k):
            if not r["h"] < cmp_["h"]: continue
            ent = s["o"]
            if not (r["l"] < ent < r["h"]): continue
            sl = r["h"] - ent; tp = ent - r["l"]
            b, mot = _sim_velas(o, h, l, c, int(s["ix"][0]), ent, -1, sl, tp, None, int(s["ix"][-1]))
            filas.append(dict(fecha=int(s["fecha"]), celda=(celda,), lado=-1, riesgo=float(sl), bruto=float(b), motivo=mot))
    return pd.DataFrame(filas)


def visitas_hougaard(ctx) -> pd.DataFrame:
    """E0 (sin P&L): para cada par de días hábiles consecutivos, si el día de referencia hizo máximo menor que el comparado (día previo,
    o dos antes en mie/lun) y si el día siguiente visitó en RTH el mínimo de referencia; con apertura dentro o fuera del rango."""
    D, _, _ = _dias_rth(ctx); filas = []
    for i in range(2, len(D) - 1):
        r, s = D[i], D[i + 1]
        for k in (1, 2):
            c_ = D[i - k]
            filas.append(dict(fecha=int(s["fecha"]), dow_ref=r["dow"], dow_cmp=c_["dow"], salto=k, menor=bool(r["h"] < c_["h"]),
                              dentro=bool(r["l"] < s["o"] < r["h"]), visita=bool(s["l"] <= r["l"])))
    return pd.DataFrame(filas)


def dos_velas(ctx) -> pd.DataFrame:
    """Juan José Olave: velas de 5 min desde la de las 09:35; la primera pareja de velas seguidas del mismo color (cierre > apertura las
    dos = compra; < = venta; un doji corta) → entrada al cierre de la segunda; stop en el mínimo (compra) / máximo (venta) desde las
    09:00; objetivo 1:1; una por día; salida al cierre 16:00. Celda = hora límite del cierre de la segunda vela (11:00 o 15:55)."""
    o, h, l, c = ctx["o"], ctx["h"], ctx["l"], ctx["c"]; m, f, _ = _hora(ctx, "America/New_York"); filas = []
    for dia in np.unique(f):
        ix = np.flatnonzero(f == dia); mm = m[ix]
        rth = ix[(mm >= 570) & (mm < 960)]
        if len(rth) < 380 or m[rth[0]] > 574: continue
        g = (m[rth] - 570) // 5
        O5, H5, L5, C5, _, fin = _agregar(o[rth], h[rth], l[rth], c[rth], np.ones(len(rth)), g)
        slot = g[fin]; col = np.sign(C5 - O5)
        j = next((q for q in range(1, len(slot)) if slot[q - 1] >= 1 and col[q] != 0 and col[q] == col[q - 1]), None)
        if j is None: continue
        d = int(col[j]); ent = float(C5[j]); i_fin = int(rth[fin[j]]); fin_min = int(m[i_fin]) + 1
        pre = ix[(mm >= 540) & (ix <= i_fin)]
        st = float(l[pre].min()) if d == 1 else float(h[pre].max()); sl = d * (ent - st)
        if not sl > 0 or i_fin >= rth[-1]: continue
        b, mot = _sim_velas(o, h, l, c, i_fin + 1, ent, d, sl, sl, None, int(rth[-1]))
        for celda in DV_CELDAS:
            if celda[0] == "11h" and fin_min > 660: continue
            filas.append(dict(fecha=int(dia), celda=celda, lado=d, riesgo=sl, bruto=float(b), motivo=mot))
    return pd.DataFrame(filas)


def _sesgo_franklin(ctx):
    """Por minuto: VWAP de la sesión (ancla 18:00 NY, volumen de tick, precio típico) y máximo/mínimo de Londres (03:00–09:30 NY) de la
    fecha; NaN fuera de lo conocido. Causal: el VWAP de la vela i incluye la vela i (se usa con su cierre)."""
    m, f, _ = _hora(ctx, "America/New_York")
    lt = pd.to_datetime(ctx["t"] - 60, unit="s", utc=True).tz_convert("America/New_York")
    ses = np.asarray((lt + pd.Timedelta(hours=6)).strftime("%Y%m%d"), dtype=np.int64)
    tp = (ctx["h"] + ctx["l"] + ctx["c"]) / 3; v = np.maximum(np.asarray(ctx["v"], float), 1e-9)
    df = pd.DataFrame(dict(ses=ses, pv=tp * v, v=v)); g = df.groupby("ses")
    vwap = (g.pv.cumsum() / g.v.cumsum()).to_numpy()
    lon = (m >= 180) & (m < 570); L = pd.DataFrame(dict(f=f[lon], h=ctx["h"][lon], l=ctx["l"][lon])).groupby("f")
    lh = np.array(pd.Series(f).map(L.h.max()), dtype=float); ll = np.array(pd.Series(f).map(L.l.min()), dtype=float)
    lh[m < 570] = np.nan; ll[m < 570] = np.nan
    return vwap, lh, ll


def franklin(ctx) -> pd.DataFrame:
    """Franklin (Traders Hub): a las 10:00 NY, con el cierre de la vela 09:59: arriba del máximo de Londres y del VWAP → compra; abajo del
    mínimo de Londres y del VWAP → venta. Stop en el mínimo (compra) / máximo (venta) de las dos velas de 15 min de NY (09:30–10:00);
    salida al cierre 16:00 o objetivo 2R. Una por día."""
    o, h, l, c = ctx["o"], ctx["h"], ctx["l"], ctx["c"]; m, f, _ = _hora(ctx, "America/New_York"); vw, lh, ll = _sesgo_franklin(ctx); filas = []
    for dia in np.unique(f):
        ix = np.flatnonzero(f == dia); mm = m[ix]
        rth = ix[(mm >= 570) & (mm < 960)]
        if len(rth) < 380 or m[rth[0]] > 574: continue
        k = ix[mm == 599]
        if not len(k): continue
        k = int(k[0]); p = float(c[k]); orr = rth[m[rth] < 600]
        if not (np.isfinite(lh[k]) and np.isfinite(vw[k])): continue
        d = 1 if (p > lh[k] and p > vw[k]) else -1 if (p < ll[k] and p < vw[k]) else 0
        if not d: continue
        st = float(l[orr].min()) if d == 1 else float(h[orr].max()); sl = d * (p - st)
        if not sl > 0: continue
        for celda in FR_CELDAS:
            b, mot = _sim_velas(o, h, l, c, k + 1, p, d, sl, 2 * sl if celda[0] == "2R" else 0.0, None, int(rth[-1]))
            filas.append(dict(fecha=int(dia), celda=celda, lado=d, riesgo=sl, bruto=float(b), motivo=mot))
    return pd.DataFrame(filas)


FAMILIAS.update({"VIERNES_LUNES": (viernes_lunes, VL_CELDAS), "DOS_VELAS": (dos_velas, DV_CELDAS), "FRANKLIN": (franklin, FR_CELDAS)})


# ---------------------------------------------------------------- FRANKLIN: variantes (PREREGISTRO docs/research/reels_20261116/PREREGISTRO_FRANKLIN_MEJORAS.md)
FRV_HORAS = ("0945", "1000", "1030", "primera")            # primera = el primer cierre alineado de 09:59, 10:29, 10:59, 11:29
FRV_STOPS = ("rango", "atr")                               # extremo opuesto 09:30 → decisión | 0,5 × ATR20 diario (RTH) desde la entrada
FRV_FILTROS = ("ninguno", "vwap_ny", "sin_gap", "vwap_ny+sin_gap")
FRV_CELDAS = [(h, s, f) for h in FRV_HORAS for s in FRV_STOPS for f in FRV_FILTROS]
_FRV_MIN = {"0945": (584,), "1000": (599,), "1030": (629,), "primera": (599, 629, 659, 689)}


def franklin_variantes(ctx, celdas=None) -> pd.DataFrame:
    """Franklin con hora de decisión, stop y filtro variables; salida siempre al cierre 16:00. Filtros: `vwap_ny` exige además el lado
    correcto del VWAP anclado a las 09:30 (dos VWAP, RobotEdge); `sin_gap` excluye días con |apertura 09:30 − cierre RTH previo| ≥ 0,5 ×
    ATR20 (el sesgo puede ser sólo el gap, Kemet). Causal: todo con datos hasta el cierre de la vela de decisión; ATR20 y gap del día previo."""
    celdas = celdas or FRV_CELDAS
    o, h, l, c = ctx["o"], ctx["h"], ctx["l"], ctx["c"]; m, f, _ = _hora(ctx, "America/New_York"); vw, lh, ll = _sesgo_franklin(ctx)
    v = np.maximum(np.asarray(ctx["v"], float), 1e-9); tp = (h + l + c) / 3
    D, _, _ = _dias_rth(ctx); filas = []; prev = None; rangos = []
    for d in D:
        ix = d["ix"]; atr = np.mean(rangos[-20:]) if len(rangos) >= 20 else np.nan
        gap = abs(d["o"] - prev) / atr if (prev is not None and np.isfinite(atr) and atr > 0) else np.nan
        prev = float(c[ix[-1]]); rangos.append(d["h"] - d["l"])
        if not np.isfinite(atr): continue
        mm = m[ix]; vwny = np.cumsum(tp[ix] * v[ix]) / np.cumsum(v[ix]); ult = int(ix[-1]); hecho = {}
        for celda in celdas:
            hora, stop, filtro = celda
            if "sin_gap" in filtro and not (np.isfinite(gap) and gap < 0.5): continue
            for mdec in _FRV_MIN[hora]:
                q = np.flatnonzero(mm == mdec)
                if not len(q): continue
                q = int(q[0]); k = int(ix[q]); p = float(c[k])
                if not (np.isfinite(lh[k]) and np.isfinite(vw[k])): continue
                dd = 1 if (p > lh[k] and p > vw[k]) else -1 if (p < ll[k] and p < vw[k]) else 0
                if dd and "vwap_ny" in filtro and not (dd * (p - vwny[q]) > 0): dd = 0
                if not dd: continue
                if k >= ult: break
                clave = (mdec, stop, dd)
                if clave not in hecho:                                   # salida al cierre con stop: primer toque del stop (vectorizado)
                    orr = ix[: q + 1]
                    sl = dd * (p - (float(l[orr].min()) if dd == 1 else float(h[orr].max()))) if stop == "rango" else 0.5 * atr
                    if not sl > 0: hecho[clave] = None
                    else:
                        st = p - dd * sl; seg = (l[k + 1: ult + 1] <= st) if dd == 1 else (h[k + 1: ult + 1] >= st)
                        if seg.any():                                            # auditoría 2026-11-16: con gap, a la apertura
                            j = k + 1 + int(np.argmax(seg)); px = min(float(o[j]), st) if dd == 1 else max(float(o[j]), st)
                            hecho[clave] = (sl, dd * (px - p), 1)
                        else: hecho[clave] = (sl, dd * (float(c[ult]) - p), 3)
                if hecho[clave] is None: break
                sl, b, mot = hecho[clave]
                filas.append(dict(fecha=int(d["fecha"]), celda=celda, lado=dd, riesgo=float(sl), bruto=float(b), motivo=mot, minuto=int(mdec)))
                break
    return pd.DataFrame(filas)

