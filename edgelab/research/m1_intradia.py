"""Intradía sobre M1 de Dukascopy (2012–2026, exportadas de SQX) en índices: ORB y pre-rango 08:12–09:12 (2026-11-14). Pre-registro:
docs/research/m1_intradia_20261114/PREREGISTRO.md. Motor propio M1 conservador (ver `_simular`): entrada por stop/límite/mercado, stop
atravesado por gap → sale a la apertura, stop y objetivo en la misma barra → stop, objetivo sólo si lo atraviesa; cierre 15:55 NY. R bruto
(sin spread) y neto (spread de Dukascopy por ida y vuelta / riesgo). Hora: servidor de datos EST+07 → Nueva York = servidor − 7 h."""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

SERVIDOR_MENOS_NY = 7
PERIODOS = [("DESC", "2000-01-01", "2019-12-31"), ("OOS", "2020-01-01", "2023-12-31"), ("RECIENTE", "2024-01-01", "2025-07-31"),
            ("PSEUDO", "2025-08-01", "2026-09-29")]
ORB_MIN = (15, 30, 60)
ORB_ENTRADA = ("BRK", "EMA20")
ORB_STOP = ("OPUESTO", "MITAD")
ORB_OBJ = (1.0, 2.0, 0.0)                     # 0 = sin objetivo (sale al cierre)


# 2026-11-16 (auditoría de zona horaria, docs/research/auditoria_corridas_20261116/): en edgelab-sqx-m1 sólo los `*_M1_dukas` vienen en hora del
# servidor (NY + 7); Russell, DAX, EuroStoxx, FTSE, Nikkei y petróleo vienen en UTC (aperturas de cada mercado en UTC, invierno y verano).
# Igual en edgelab/research/fuentes_ticks.py::M1_EN_UTC (test). Un archivo que no esté en ninguna de las dos listas no se lee.
EN_UTC = ("USSC2000IDXUSD", "DEUIDXEUR", "EUSIDXEUR", "GBRIDXGBP", "JPNIDXJPY", "LIGHTCMDUSD",
          "AUDUSD", "BRENTCMDUSD", "BUNDTREUR", "COPPERCMDUSD", "DOLLARIDXUSD", "GASCMDUSD", "NZDUSD", "UKGILTTRGBP", "USDCAD",
          "USTBONDTRUSD", "XAGUSD")      # 2026-11-17: confirmado en SQX (list_data) por Antigravity


def zona_m1(nombre: str) -> str:
    """'UTC' o 'SERVIDOR' según el nombre del CSV; error si no se conoce (no se adivina la zona horaria)."""
    if nombre.startswith(EN_UTC): return "UTC"
    if "_M1_dukas" in nombre: return "SERVIDOR"
    raise ValueError(f"{nombre}: zona horaria del M1 no declarada (agregarla a m1_intradia.EN_UTC o usar el nombre *_M1_dukas)")


def leer_m1(path) -> pd.DataFrame:
    """M1 de Dukascopy → índice en hora de NY sin zona. Los CSV `*_M1_dukas` vienen en hora del servidor (NY + 7); los de `EN_UTC`, en UTC."""
    from pathlib import Path
    D = pd.read_csv(path)
    D.columns = [c.strip().lower() for c in D.columns]
    t = pd.to_datetime(D["date"].astype(str) + " " + D["time"].astype(str), format="%Y%m%d %H:%M:%S")
    if zona_m1(Path(str(path)).name) == "UTC": t = t.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.tz_localize(None)
    else: t = t - pd.Timedelta(hours=SERVIDOR_MENOS_NY)
    return pd.DataFrame(dict(o=D.open.to_numpy(float), h=D.high.to_numpy(float), l=D.low.to_numpy(float), c=D.close.to_numpy(float),
                             v=D.volume.to_numpy(float) if "volume" in D else np.ones(len(D))), index=t)


def leer_m1nt8(path) -> pd.DataFrame:
    """M1 REAL de futuros de NT8 (`edgelab-nt8-m1-futuros`, índice = apertura de la vela en UTC) → índice en hora de NY sin zona, como
    `leer_m1`. Corta en la frontera del holdout (nunca devuelve velas desde su apertura)."""
    from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS
    D = pd.read_parquet(path)
    t = pd.DatetimeIndex(D.index if "datetime" not in D else D["datetime"]).astype("datetime64[ns]")
    ok = t.asi8 < HOLDOUT_APERTURA_UTC_NS; D, t = D[ok], t[ok]
    ny = t.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    return pd.DataFrame(dict(o=D.open.to_numpy(float), h=D.high.to_numpy(float), l=D.low.to_numpy(float), c=D.close.to_numpy(float),
                             v=D.volume.to_numpy(float)), index=ny)


@njit(cache=False)
def _simular(o, h, l, c, i0, lado, tipo, precio, stop, obj, i_fin):
    """tipo 0 = mercado a la apertura de i0; 1 = stop en `precio` desde i0; 2 = límite en `precio` desde i0 (llena si atraviesa).
    Devuelve (entrada, salida, i_entrada) o (nan, nan, -1) si no llena antes de i_fin."""
    n = len(o); ie = -1; pe = np.nan
    for i in range(i0, min(i_fin, n)):
        if tipo == 0: ie = i; pe = o[i]; break
        if tipo == 1:
            if lado == 1 and h[i] >= precio: ie = i; pe = max(o[i], precio); break
            if lado == -1 and l[i] <= precio: ie = i; pe = min(o[i], precio); break
        if tipo == 2:
            if lado == 1 and l[i] < precio: ie = i; pe = min(o[i], precio); break
            if lado == -1 and h[i] > precio: ie = i; pe = max(o[i], precio); break
    if ie < 0: return np.nan, np.nan, -1
    for i in range(ie, min(i_fin, n)):
        if i > ie:
            if lado == 1 and o[i] <= stop: return pe, o[i], ie
            if lado == -1 and o[i] >= stop: return pe, o[i], ie
        if lado == 1 and l[i] <= stop: return pe, stop, ie
        if lado == -1 and h[i] >= stop: return pe, stop, ie
        if obj > 0 and (i > ie or tipo == 0):           # en la barra de un llenado por stop/límite no se sabe el orden: sólo el stop
            if lado == 1 and h[i] > obj: return pe, obj, ie
            if lado == -1 and l[i] < obj: return pe, obj, ie
    j = min(i_fin, n) - 1
    return pe, c[j], ie


def _dias(D: pd.DataFrame):
    m = (D.index.time >= pd.Timestamp("08:00").time()) & (D.index.time < pd.Timestamp("16:00").time())
    X = D[m]
    for d, g in X.groupby(X.index.normalize()):
        if d.dayofweek < 5 and len(g) > 300: yield d, g


from edgelab.research.ema_zones import ema as _ema  # noqa: E402  (reutilizada, no copiada)


def orb(D: pd.DataFrame, spread: float) -> pd.DataFrame:
    filas = []
    for d, g in _dias(D):
        t = g.index; mins = (t.hour * 60 + t.minute).to_numpy(); o, h, l, c = (g[k].to_numpy() for k in "ohlc")
        ia = np.searchsorted(mins, 9 * 60 + 30); i_fin = np.searchsorted(mins, 15 * 60 + 55)
        if ia >= len(mins) or mins[ia] != 570: continue
        c2 = g.c.resample("2min").last().dropna(); e2 = pd.Series(_ema(c2.to_numpy(), 20), index=c2.index).reindex(t, method="ffill").to_numpy()
        for N in ORB_MIN:
            ib = np.searchsorted(mins, 570 + N)
            if ib >= i_fin: continue
            hi, lo = h[ia:ib].max(), l[ia:ib].min(); rg = hi - lo
            if rg <= 0: continue
            # primera ruptura (cierre fuera del rango) define el lado
            fuera = np.flatnonzero((c[ib:i_fin] > hi) | (c[ib:i_fin] < lo))
            if not len(fuera): continue
            k = ib + fuera[0]; lado = 1 if c[k] > hi else -1
            for ent in ORB_ENTRADA:
                if ent == "BRK": tipo, i0, px = 0, k + 1, np.nan
                else:
                    if not np.isfinite(e2[k]): continue
                    tipo, i0, px = 2, k + 1, e2[k]                  # límite en la EMA20 (2 min) del momento de la ruptura
                    if lado * (px - (lo if lado == 1 else hi)) <= 0: continue
                for st in ORB_STOP:
                    stop = (lo if lado == 1 else hi) if st == "OPUESTO" else (lo + hi) / 2
                    for ob in ORB_OBJ:
                        ref = c[k] if tipo == 0 else px; R0 = lado * (ref - stop)
                        if R0 <= 0: continue
                        obj = ref + lado * ob * R0 if ob > 0 else 0.0
                        pe, ps, ie = _simular(o, h, l, c, i0, lado, tipo, px if tipo else 0.0, stop, obj if ob > 0 else 0.0, i_fin)
                        if ie < 0: continue
                        riesgo = lado * (pe - stop)
                        if riesgo < 0.2 * rg: continue                     # piso de riesgo: un stop pegado a la entrada infla R
                        rb = lado * (ps - pe) / riesgo
                        filas.append((d, N, ent, st, ob, rb, rb - spread / riesgo, riesgo, rg))
    return pd.DataFrame(filas, columns=["dia", "min", "entrada", "stop", "obj", "r_bruto", "r_neto", "riesgo", "rango"])


def prerango(D: pd.DataFrame, spread: float) -> pd.DataFrame:
    """Rango 08:12–09:12 NY. Desde 09:30: primer extremo tocado (por un máximo/mínimo de barra) y vuelta adentro (cierre dentro del
    rango) → entrada a mercado hacia el extremo opuesto; stop = extremo tocado ± 0,25·rango; objetivo = extremo opuesto. Además la medida
    de información (hasta 15:55): ¿toca el opuesto después del primero? (doble toque)."""
    filas = []
    for d, g in _dias(D):
        t = g.index; mins = (t.hour * 60 + t.minute).to_numpy(); o, h, l, c = (g[k].to_numpy() for k in "ohlc")
        i0r, i1r = np.searchsorted(mins, 8 * 60 + 12), np.searchsorted(mins, 9 * 60 + 12)
        ia, i_fin = np.searchsorted(mins, 570), np.searchsorted(mins, 15 * 60 + 55)
        if i1r - i0r < 50 or ia >= i_fin: continue
        hi, lo = h[i0r:i1r].max(), l[i0r:i1r].min(); rg = hi - lo
        if rg <= 0: continue
        toca = np.flatnonzero((h[ia:i_fin] >= hi) | (l[ia:i_fin] <= lo))
        if not len(toca): filas.append((d, 0, np.nan, np.nan, np.nan, rg)); continue
        k = ia + toca[0]; primero = 1 if h[k] >= hi else -1
        if h[k] >= hi and l[k] <= lo: filas.append((d, 3, np.nan, np.nan, np.nan, rg)); continue
        doble = bool(((l[k + 1:i_fin] <= lo) if primero == 1 else (h[k + 1:i_fin] >= hi)).any())
        vuelta = np.flatnonzero((c[k:i_fin] < hi) & (c[k:i_fin] > lo))
        if not len(vuelta): filas.append((d, 1 + int(doble), np.nan, np.nan, np.nan, rg)); continue
        j = k + vuelta[0]; lado = -primero
        stop = (hi + 0.25 * rg) if primero == 1 else (lo - 0.25 * rg); obj = lo if primero == 1 else hi
        pe, ps, ie = _simular(o, h, l, c, j + 1, lado, 0, 0.0, stop, obj, i_fin)
        if ie < 0: filas.append((d, 1 + int(doble), np.nan, np.nan, np.nan, rg)); continue
        riesgo = lado * (pe - stop)
        rb = lado * (ps - pe) / riesgo if riesgo > 0 else np.nan
        filas.append((d, 1 + int(doble), rb, rb - spread / riesgo if riesgo > 0 else np.nan, riesgo, rg))
    return pd.DataFrame(filas, columns=["dia", "toques", "r_bruto", "r_neto", "riesgo", "rango"])


VB_K = (2.0, 3.0)                              # banda del VWAP (desvíos); 2 = control de dosis-respuesta de la 3


def vwap_banda(D: pd.DataFrame, spread: float) -> pd.DataFrame:
    """VWAP anclado a las 09:30 NY (volumen de ticks de Dukascopy) y su desvío ponderado. Desde las 10:00, el PRIMER cierre del día fuera
    de ±K desvíos (K = 2, 3) dispara:
      REV  reversión a mercado (barra siguiente) hacia el VWAP: objetivo VWAP o banda 1; stop en la banda K+1 o en el extremo del
           día + 0,5 desvío;
      CONT continuación a favor: objetivo 1 R o 2 R; stop en la banda K−1.
    Bandas y VWAP se congelan al momento del disparo (causal). Cierre 15:55 NY."""
    filas = []
    for d, g in _dias(D):
        t = g.index; mins = (t.hour * 60 + t.minute).to_numpy(); o, h, l, c = (g[k].to_numpy() for k in "ohlc")
        v = g["v"].to_numpy() if "v" in g else np.ones(len(g)); v = np.where(v > 0, v, 1.0)
        ia, i10, i_fin = np.searchsorted(mins, 570), np.searchsorted(mins, 600), np.searchsorted(mins, 15 * 60 + 55)
        if ia >= i10 or i10 >= i_fin: continue
        tp = (h + l + c) / 3; w = np.cumsum(v[ia:]); vw = np.cumsum(tp[ia:] * v[ia:]) / w
        sd = np.sqrt(np.maximum(np.cumsum(v[ia:] * tp[ia:] ** 2) / w - vw ** 2, 0))
        for K in VB_K:
            z = (c[ia:] - vw) / np.where(sd > 0, sd, np.nan)
            cand = np.flatnonzero(np.abs(z[i10 - ia:i_fin - ia]) >= K)
            if not len(cand): continue
            j = i10 + cand[0]; q = j - ia; s_ = 1 if z[q] > 0 else -1; VW, SD = vw[q], sd[q]
            ext = h[ia:j + 1].max() if s_ == 1 else l[ia:j + 1].min()
            for modo, obj_n, stop_n, lado, stop, obj in (
                    ("REV", "VWAP", "K+1", -s_, VW + s_ * (K + 1) * SD, VW), ("REV", "VWAP", "EXT", -s_, ext + s_ * 0.5 * SD, VW),
                    ("REV", "B1", "K+1", -s_, VW + s_ * (K + 1) * SD, VW + s_ * SD), ("REV", "B1", "EXT", -s_, ext + s_ * 0.5 * SD, VW + s_ * SD),
                    ("CONT", "1R", "K-1", s_, VW + s_ * (K - 1) * SD, None), ("CONT", "2R", "K-1", s_, VW + s_ * (K - 1) * SD, None)):
                ref = c[j]; R0 = lado * (ref - stop)
                if R0 <= 0: continue
                if obj is None: obj = ref + lado * (1.0 if obj_n == "1R" else 2.0) * R0
                if lado * (obj - ref) <= 0: continue
                pe, ps, ie = _simular(o, h, l, c, j + 1, lado, 0, 0.0, stop, obj, i_fin)
                if ie < 0: continue
                riesgo = lado * (pe - stop)
                if riesgo <= 0.5 * SD: continue                 # piso de riesgo
                rb = lado * (ps - pe) / riesgo
                filas.append((d, K, modo, obj_n, stop_n, rb, rb - spread / riesgo))
    return pd.DataFrame(filas, columns=["dia", "k", "modo", "obj", "stop", "r_bruto", "r_neto"])


def por_periodo(dias: pd.Series, r: pd.Series) -> dict:
    out = {}
    for nom, a, b in PERIODOS:
        m = (dias >= a) & (dias <= b) & r.notna(); x = r[m]
        out[nom] = dict(n=int(len(x)), r=float(x.mean()) if len(x) else None,
                        t=float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else None)
    return out


def sintetica_m1(D: pd.DataFrame, semilla: int) -> pd.DataFrame:
    """Nulo intradía: cada minuto de cada día toma la barra RELATIVA (al cierre previo) del MISMO minuto del día de otro día al azar.
    Conserva la volatilidad por hora del día (apertura, almuerzo, cierre) y destruye la dependencia dentro del día (la que explotan ORB
    y el pre-rango)."""
    rng = np.random.default_rng(semilla); prev = np.r_[D.o.iloc[0], D.c.to_numpy()[:-1]]
    rel = np.column_stack([D[k].to_numpy() / prev for k in "ohlc"]); dia = D.index.normalize(); minuto = (D.index.hour * 60 + D.index.minute).to_numpy()
    out = np.empty_like(rel); pos = {}
    for m in np.unique(minuto): pos[m] = np.flatnonzero(minuto == m)
    for m, ix in pos.items(): out[ix] = rel[rng.choice(ix, size=len(ix))]
    c = D.o.iloc[0] * np.cumprod(out[:, 3]); p0 = np.r_[D.o.iloc[0], c[:-1]]
    S = pd.DataFrame(dict(o=p0 * out[:, 0], h=p0 * out[:, 1], l=p0 * out[:, 2], c=c), index=D.index)
    S["h"] = S[["o", "h", "l", "c"]].max(axis=1); S["l"] = S[["o", "h", "l", "c"]].min(axis=1)
    return S


def familia(DD: dict, spreads: dict) -> dict:
    """{variante: DataFrame(dia, r_bruto, r_neto)} por índice y canasta (todas las operaciones de los índices juntas)."""
    F = {}
    for s, D in DD.items():
        O = orb(D, spreads.get(s, 0.0))
        for (N, e, st, ob), g in O.groupby(["min", "entrada", "stop", "obj"]): F[f"ORB|{s}|{N}|{e}|{st}|{ob:g}"] = g[["dia", "r_bruto", "r_neto"]]
        P = prerango(D, spreads.get(s, 0.0)); F[f"PRERANGO|{s}"] = P[["dia", "r_bruto", "r_neto"]].dropna()
        F[f"PRERANGO_INFO|{s}"] = P[["dia", "toques"]]
        V = vwap_banda(D, spreads.get(s, 0.0))
        for (K, mo, ob, st), g in V.groupby(["k", "modo", "obj", "stop"]): F[f"VWAPB|{s}|{K:g}|{mo}|{ob}|{st}"] = g[["dia", "r_bruto", "r_neto"]]
    out = dict(F)
    for clave in {"|".join([k.split("|")[0]] + k.split("|")[2:]) for k in F if not k.startswith("PRERANGO_INFO")}:
        reg, *par = clave.split("|")
        miembros = [v for k, v in F.items() if k.split("|")[0] == reg and k.split("|")[2:] == par]
        out[f"CANASTA|{clave}"] = pd.concat(miembros, ignore_index=True)
    return out


# ---------------------------------------------------------------------------------------------------------- lote 2 (2026-11-15)
GAP_TAM = ((0.1, 0.3), (0.3, 0.6), (0.6, 9.9))          # |gap| / ATR20 diario (rango RTH), causal


def _rth(D: pd.DataFrame):
    """Por día: índices de la barra 09:30 y de la 15:59 (NY), máximo, mínimo y cierre RTH."""
    out = []
    for d, g in _dias(D):
        mins = (g.index.hour * 60 + g.index.minute).to_numpy()
        ia, ic = np.searchsorted(mins, 570), np.searchsorted(mins, 959)
        if ia >= len(mins) or mins[ia] != 570 or ic >= len(mins): continue
        out.append((d, g, ia, ic, g.h.to_numpy()[ia:ic + 1].max(), g.l.to_numpy()[ia:ic + 1].min(), g.c.to_numpy()[ic]))
    return out


def gap_apertura(D: pd.DataFrame, spread: float) -> pd.DataFrame:
    """Gap = apertura 09:30 − cierre RTH previo; tamaño en ATR20 (rango RTH de los 20 días previos). Entrada a mercado 09:31.
    FILL: hacia el cierre previo (objetivo), stop 0,5·|gap| más allá de la apertura. CONT: a favor del gap, objetivo 1 R, stop en el cierre
    previo… acotado a 0,5·|gap| detrás de la apertura (mismo riesgo que FILL). Cierre 15:55."""
    R = _rth(D); filas = []; rangos = []
    for i, (d, g, ia, ic, hi, lo, cl) in enumerate(R):
        rangos.append(hi - lo)
        if i < 21: continue
        atr = float(np.mean(rangos[-21:-1])); prev_c = R[i - 1][6]
        o, h, l, c = (g[k].to_numpy() for k in "ohlc"); gap = o[ia] - prev_c; tam = abs(gap) / atr if atr > 0 else 0
        b = next((j for j, (a, z) in enumerate(GAP_TAM) if a <= tam < z), None)
        if b is None: continue
        s = 1 if gap > 0 else -1; i_fin = int(np.searchsorted((g.index.hour * 60 + g.index.minute).to_numpy(), 955))
        for modo, lado, stop, obj in (("FILL", -s, o[ia] + s * 0.5 * abs(gap), prev_c), ("CONT", s, o[ia] - s * 0.5 * abs(gap), o[ia] + s * 0.5 * abs(gap))):
            pe, ps, ie = _simular(o, h, l, c, ia + 1, lado, 0, 0.0, stop, obj, i_fin)
            if ie < 0: continue
            riesgo = lado * (pe - stop)
            if riesgo <= 0.05 * atr: continue
            rb = lado * (ps - pe) / riesgo
            filas.append((d, b, modo, rb, rb - spread / riesgo))
    return pd.DataFrame(filas, columns=["dia", "tam", "modo", "r_bruto", "r_neto"])


def ruptura_previo(D: pd.DataFrame, spread: float) -> pd.DataFrame:
    """Máximo/mínimo RTH del día previo (PDH/PDL). Desde las 10:00, primer cierre fuera: CONT a mercado (barra siguiente), stop en la mitad
    del rango previo, objetivo 1 R o 2 R; FALSA: si dentro de los 15 min siguientes cierra de vuelta adentro, entrada en contra con stop
    detrás del extremo de la ruptura y objetivo la mitad del rango previo. Cierre 15:55."""
    R = _rth(D); filas = []
    for i in range(1, len(R)):
        d, g, ia, ic, *_ = R[i]; pdh, pdl = R[i - 1][4], R[i - 1][5]; mid = (pdh + pdl) / 2
        o, h, l, c = (g[k].to_numpy() for k in "ohlc"); mins = (g.index.hour * 60 + g.index.minute).to_numpy()
        i10, i_fin = np.searchsorted(mins, 600), np.searchsorted(mins, 955)
        fuera = np.flatnonzero((c[i10:i_fin] > pdh) | (c[i10:i_fin] < pdl))
        if not len(fuera): continue
        k = i10 + fuera[0]; s = 1 if c[k] > pdh else -1
        for nom, ob in (("CONT1R", 1.0), ("CONT2R", 2.0)):
            R0 = s * (c[k] - mid)
            if R0 <= 0: continue
            pe, ps, ie = _simular(o, h, l, c, k + 1, s, 0, 0.0, mid, c[k] + s * ob * R0, i_fin)
            if ie < 0: continue
            rs = s * (pe - mid)
            if rs > 0: filas.append((d, nom, s * (ps - pe) / rs, s * (ps - pe) / rs - spread / rs))
        vuelta = np.flatnonzero((c[k + 1:min(k + 16, i_fin)] <= pdh) & (c[k + 1:min(k + 16, i_fin)] >= pdl))
        if len(vuelta):
            j = k + 1 + vuelta[0]; ext = h[k:j + 1].max() if s == 1 else l[k:j + 1].min(); lado = -s
            pe, ps, ie = _simular(o, h, l, c, j + 1, lado, 0, 0.0, ext + s * 0.0001, mid, i_fin)
            if ie >= 0:
                rs = lado * (pe - ext)
                if rs > 0: filas.append((d, "FALSA", lado * (ps - pe) / rs, lado * (ps - pe) / rs - spread / rs))
    return pd.DataFrame(filas, columns=["dia", "modo", "r_bruto", "r_neto"])


def familia2(DD: dict, spreads: dict) -> dict:
    F = {}
    for s, D in DD.items():
        G = gap_apertura(D, spreads.get(s, 0.0))
        for (b, mo), g in G.groupby(["tam", "modo"]): F[f"GAP|{s}|t{b}|{mo}"] = g[["dia", "r_bruto", "r_neto"]]
        P = ruptura_previo(D, spreads.get(s, 0.0))
        for mo, g in P.groupby("modo"): F[f"PREVIO|{s}|{mo}"] = g[["dia", "r_bruto", "r_neto"]]
    out = dict(F)
    for clave in {"|".join([k.split("|")[0]] + k.split("|")[2:]) for k in F}:
        reg, *par = clave.split("|"); miembros = [v for k, v in F.items() if k.split("|")[0] == reg and k.split("|")[2:] == par]
        out[f"CANASTA|{clave}"] = pd.concat(miembros, ignore_index=True)
    return out
