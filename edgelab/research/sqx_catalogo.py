"""Candidatas del catálogo de StrategyQuant X (docs/research/sqx_catalogo_20261117/): reglas tal como las fichas, motor de barras común.

Pre-registro: docs/research/sqx_catalogo_20261117/PREREGISTRO_MEDICION.md. Corrida: tools/sqx_catalogo_medir.py.

Motor (`simular`): una posición a la vez. Las señales se calculan con la barra i CERRADA y dan una orden que vive desde la barra i+1:
mercado (apertura de i+1), stop o límite (válidas `valida` barras; con hueco más allá del precio llenan a la apertura). En cada barra con
posición: primero el hueco de apertura contra stop/objetivo (sale a la apertura), después stop antes que objetivo dentro de la barra
(conservador); al cierre: salida por condición, por tope de barras o por viernes (variante `viernes`), y recién después se mueven break even y
trailing (valen desde la barra siguiente). Barras en hora de NY; el día de trading empieza a las 18:00 (sesión CME).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------------------------------------------- datos
def barras_desde_m1(D: pd.DataFrame, tf: str) -> pd.DataFrame:
    """M1 (índice NY sin zona) → barras `tf` ('M15', 'H1', 'H4', 'D1') con fecha de trading (18:00 NY → día siguiente). Columnas o h l c v,
    `fecha` (int AAAAMMDD de la sesión), `dow` (día de la semana de la sesión) y `fin` (minuto NY de cierre de la barra)."""
    td = (D.index + pd.Timedelta(hours=6))
    if tf == "D1": clave = td.normalize()
    else:
        mins = {"M15": 15, "H1": 60, "H4": 240}[tf]; clave = td.floor(f"{mins}min")
    g = D.groupby(clave)
    B = pd.DataFrame(dict(o=g.o.first(), h=g.h.max(), l=g.l.min(), c=g.c.last(), v=g.v.sum()))
    B["fecha"] = np.asarray(B.index.normalize().strftime("%Y%m%d"), dtype=np.int64); B["dow"] = B.index.dayofweek
    B = B[B.dow < 5].copy(); B.index = B.index - pd.Timedelta(hours=6)          # hora NY de apertura de la barra
    return B


def barras_d1_csv(path) -> pd.DataFrame:
    """Barras D1 exportadas de SQX (`data/sqx_barras`): la fecha de la barra se toma como fecha de sesión."""
    D = pd.read_csv(path); t = pd.to_datetime(D.fecha, format="%Y.%m.%d %H:%M:%S")
    B = pd.DataFrame(dict(o=D.open.values, h=D.high.values, l=D.low.values, c=D.close.values, v=D.volume.values), index=t.dt.normalize())
    B = B[~B.index.duplicated()]; B["fecha"] = np.asarray(B.index.strftime("%Y%m%d"), dtype=np.int64); B["dow"] = B.index.dayofweek
    return B[B.dow < 5].copy()


# ----------------------------------------------------------------------------------------------------------------- indicadores (causales)
def sma(x, n): return pd.Series(x).rolling(n).mean().to_numpy()
def ema(x, n): return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def atr(h, l, c, n):
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))); return pd.Series(tr).rolling(n).mean().to_numpy()


def rsi(c, n):
    d = np.diff(c, prepend=c[0]); up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False).mean(); dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()


def roll_max(x, n): return pd.Series(x).rolling(n).max().to_numpy()
def roll_min(x, n): return pd.Series(x).rolling(n).min().to_numpy()
def sh(x, k=1): return np.r_[np.full(k, np.nan), np.asarray(x, float)[:-k]]


def dmi_plus(h, l, c, n):
    up = np.r_[0, np.diff(h)]; dn = np.r_[0, -np.diff(l)]; pdm = np.where((up > dn) & (up > 0), up, 0.0)
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    a = 1 / n; trs = pd.Series(tr).ewm(alpha=a, adjust=False).mean(); ps = pd.Series(pdm).ewm(alpha=a, adjust=False).mean()
    return (100 * ps / trs.replace(0, np.nan)).to_numpy()


def dmi_minus(h, l, c, n):
    return dmi_plus(-l, -h, -c, n)


# ----------------------------------------------------------------------------------------------------------------- motor
def simular(B: pd.DataFrame, sig: dict, viernes: bool, max_barras: int = 10_000) -> pd.DataFrame:
    """`sig` (arrays por barra i, evaluados al cierre de i): `lado` (+1/−1/0, o `lado_l`/`lado_s` para pares OCO), `tipo` ('mkt', 'stop',
    'limit'), `px` (precio de la orden; pares: `px_l`/`px_s`), `valida` (barras), `sl`/`tp` (distancias en precio; tp NaN = sin objetivo),
    opcionales: `be` (distancia a favor que activa break even), `trail` (función (i, lado, stop) → nuevo stop o NaN), `salida` (función (i, lado)
    → bool al cierre), `tope` (barras). Devuelve operaciones: fecha, lado, entrada, stop0, salida, motivo, barras."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); dow = B.dow.to_numpy(); fecha = B.fecha.to_numpy(); n = len(c)
    ult_viernes = np.zeros(n, bool)
    if viernes:
        f = pd.Series(fecha); ult_viernes = ((dow == 4) & (f.shift(-1).to_numpy() != fecha)).astype(bool)
    tope = int(sig.get("tope", max_barras)); be = sig.get("be"); trail = sig.get("trail"); salida = sig.get("salida")
    ops = []; pos = None; orden = None
    for i in range(1, n):
        # 1) órdenes pendientes (puestas al cierre de alguna barra anterior)
        if pos is None and orden is not None:
            k0, cand = orden; vivas = []
            for (lado, tipo, px, sl, tp) in cand:
                if tipo == "mkt": fill = o[i]
                elif tipo == "stop":
                    fill = (max(o[i], px) if h[i] >= px else np.nan) if lado == 1 else (min(o[i], px) if l[i] <= px else np.nan)
                else:
                    fill = (min(o[i], px) if l[i] <= px else np.nan) if lado == 1 else (max(o[i], px) if h[i] >= px else np.nan)
                if np.isfinite(fill): vivas.append((lado, fill, sl, tp))
            if vivas:
                lado, fill, sl, tp = vivas[0] if len(vivas) == 1 else min(vivas, key=lambda x: abs(x[1] - o[i]))
                pos = dict(lado=lado, e=fill, st=fill - lado * sl, st0=fill - lado * sl, tp=(fill + lado * tp) if np.isfinite(tp) else np.nan, i0=i, be_ok=False)
                orden = None
                if (l[i] <= pos["st"]) if lado == 1 else (h[i] >= pos["st"]):              # stop en la barra de entrada (objetivo no: orden incierto)
                    ops.append((fecha[i], lado, fill, pos["st0"], pos["st"], "STOP", 1)); pos = None; continue
            elif i - k0 >= int(sig_val(sig, "valida", k0, 1)): orden = None
        # 2) posición abierta
        if pos is not None and i > pos["i0"]:
            lado, st, tp = pos["lado"], pos["st"], pos["tp"]; sal = None
            if (o[i] <= st) if lado == 1 else (o[i] >= st): sal = (o[i], "STOP_GAP")
            elif np.isfinite(tp) and ((o[i] >= tp) if lado == 1 else (o[i] <= tp)): sal = (o[i], "OBJ_GAP")
            elif (l[i] <= st) if lado == 1 else (h[i] >= st): sal = (st, "STOP")
            elif np.isfinite(tp) and ((h[i] >= tp) if lado == 1 else (l[i] <= tp)): sal = (tp, "OBJ")
            elif salida is not None and salida(i, lado): sal = (c[i], "REGLA")
            elif i - pos["i0"] + 1 >= tope: sal = (c[i], "TOPE")
            elif ult_viernes[i]: sal = (c[i], "VIERNES")
            if sal is not None:
                ops.append((fecha[pos["i0"]], lado, pos["e"], pos["st0"], sal[0], sal[1], i - pos["i0"] + 1)); pos = None
            else:
                if be is not None and not pos["be_ok"] and np.isfinite(be[pos["i0"] - 1]) and lado * (c[i] - pos["e"]) >= be[pos["i0"] - 1]:
                    pos["st"] = max(pos["st"], pos["e"]) if lado == 1 else min(pos["st"], pos["e"]); pos["be_ok"] = True
                if trail is not None:
                    nv = trail(i, lado, pos)
                    if np.isfinite(nv): pos["st"] = max(pos["st"], nv) if lado == 1 else min(pos["st"], nv)
        # 3) señal al cierre de i (sólo sin posición ni orden)
        if pos is not None and pos["i0"] == i and ult_viernes[i]:                     # entró el viernes: también sale al cierre del viernes
            ops.append((fecha[i], pos["lado"], pos["e"], pos["st0"], c[i], "VIERNES", 1)); pos = None
        if pos is None and orden is None and i < n - 1:
            cand = []
            for suf in ("", "_l", "_s"):
                if "lado" + suf not in sig: continue
                lado = int(sig["lado" + suf][i]) if np.isfinite(sig["lado" + suf][i]) else 0
                if not lado: continue
                px = sig_val(sig, "px" + suf, i, np.nan); sl = sig_val(sig, "sl", i, np.nan); tp = sig_val(sig, "tp", i, np.nan)
                if not (np.isfinite(sl) and sl > 0): continue
                cand.append((lado, sig.get("tipo" + suf, sig.get("tipo", "mkt")), px, sl, tp))
            if cand: orden = (i, cand)
    if pos is not None:
        ops.append((fecha[pos["i0"]], pos["lado"], pos["e"], pos["st0"], c[n - 1], "FIN", n - pos["i0"]))
    return pd.DataFrame(ops, columns=["fecha", "lado", "entrada", "stop0", "salida_px", "motivo", "barras"])


def sig_val(sig, k, i, defecto):
    v = sig.get(k)
    if v is None: return defecto
    return float(v[i]) if np.ndim(v) else float(v)


# ----------------------------------------------------------------------------------------------------------------- COT
def cot_indices(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy COT → índice 0..1 de especuladores (no comerciales) y coberturistas (comerciales) en 52 y 156 semanas, publicado el viernes
    (fecha del reporte + 3 días) y usable desde la sesión siguiente (lunes)."""
    d = df.sort_values("fecha").copy()
    for nom, a, b in (("spec", "noncomm_positions_long_all", "noncomm_positions_short_all"), ("hedg", "comm_positions_long_all", "comm_positions_short_all")):
        net = d[a].astype(float) - d[b].astype(float)
        for w in (52, 156):
            lo, hi = net.rolling(w).min(), net.rolling(w).max(); d[f"{nom}{w}"] = ((net - lo) / (hi - lo)).where(hi > lo)
    d["usable_desde"] = pd.to_datetime(d.fecha) + pd.Timedelta(days=6)               # martes + 6 = lunes siguiente a la publicación
    return d


def cot_por_barra(B: pd.DataFrame, cot: pd.DataFrame, invertir: bool = False) -> pd.DataFrame:
    """Último reporte usable en cada barra (asof por fecha de sesión), con su historia de reportes (rep 1 y rep 4 atrás)."""
    c = cot.dropna(subset=["spec52"]).reset_index(drop=True).copy()
    cols = ["spec52", "spec156", "hedg52", "hedg156"]
    if invertir: c[cols] = 1 - c[cols]          # COT del yen frente a operar USDJPY: largo yen = corto USDJPY
    for k in cols: c[k + "_r1"] = c[k].shift(1); c[k + "_r4"] = c[k].shift(4)
    f = pd.to_datetime(B.fecha.astype(str)).values
    idx = np.searchsorted(c.usable_desde.values, f, side="right") - 1
    out = c.iloc[np.clip(idx, 0, len(c) - 1)].reset_index(drop=True); out.loc[idx < 0, :] = np.nan
    return out


# ----------------------------------------------------------------------------------------------------------------- estrategias (fichas)
def _cross_up(x, t): return (sh(x) < t) & (x >= t)


def cot1(B, ctx):
    """#1 COT Crowding Unwind + ATR + SMA20 (D1)."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); C = ctx["cot"]; a14 = atr(h, l, c, 14); s20 = sma(c, 20)
    v = lambda k: C[k].to_numpy(float)
    calma = a14 < sh(a14, 5)
    lo = (v("spec52_r1") < 0.10) & (v("spec156") < 0.20) & (v("hedg52") > 0.75) & (v("spec52") > v("spec52_r1")) & calma & (c > s20) & (sh(c) <= sh(s20))
    so = (v("spec52_r1") > 0.90) & (v("spec156") > 0.80) & (v("hedg52") < 0.25) & (v("spec52") < v("spec52_r1")) & calma & (c < s20) & (sh(c) >= sh(s20))
    return dict(lado=np.where(lo, 1, np.where(so, -1, 0)), tipo="mkt", sl=2 * a14, tp=4 * a14)


def cot2(B, ctx):
    """#2 COT Hedger−Spec spread + ROC 4 reportes + ruptura de 20 (D1)."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); C = ctx["cot"]; a14 = atr(h, l, c, 14)
    sp = C.hedg52.to_numpy(float) - C.spec52.to_numpy(float); roc = sp - (C.hedg52_r4.to_numpy(float) - C.spec52_r4.to_numpy(float))
    lo = (sp > 0.65) & (roc > 0.15) & (c > sh(roll_max(h, 20))); so = (sp < -0.65) & (roc < -0.15) & (c < sh(roll_min(l, 20)))
    return dict(lado=np.where(lo, 1, np.where(so, -1, 0)), tipo="mkt", sl=2 * a14, tp=4 * a14)


def cot3(B, ctx):
    """#3 COT especuladores en tendencia sana + retroceso (D1)."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); C = ctx["cot"]; a14 = atr(h, l, c, 14); s200 = sma(c, 200); s20 = sma(c, 20); r14 = rsi(c, 14)
    s52, s156, s52r4 = (C[k].to_numpy(float) for k in ("spec52", "spec156", "spec52_r4"))
    lo = (c > s200) & (s52 > 0.60) & (s52 < 0.85) & (s156 > 0.55) & (s52 > s52r4) & ((sh(r14) < 40) | (sh(c) < sh(s20))) & (c > s20) & (c > sh(c))
    so = (c < s200) & (s52 < 0.40) & (s52 > 0.15) & (s156 < 0.45) & (s52 < s52r4) & ((sh(r14) > 60) | (sh(c) > sh(s20))) & (c < s20) & (c < sh(c))
    return dict(lado=np.where(lo, 1, np.where(so, -1, 0)), tipo="mkt", sl=2 * a14, tp=4 * a14)


def vp_poc(B, ctx):
    """#4 USDJPY: POC (perfil de volumen del día previo, 150 niveles) de la barra previa > el de 25 barras H1 atrás → compra; SL 100 pips, TP 200."""
    poc = ctx["poc_dia_previo"]                                                         # por barra (constante dentro de la sesión)
    prev = np.r_[np.full(24, np.nan), poc[:-24]]                                      # al abrir i+1: POC[1] = poc[i], POC[25] = poc[i−24]
    lo = np.nan_to_num(poc > prev, nan=0).astype(bool)
    return dict(lado=lo.astype(int), tipo="mkt", sl=ctx["pip"] * 100, tp=ctx["pip"] * 200)


def turtle(n_in, n_out, filtro_atr):
    def f(B, ctx):
        o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); a20 = atr(h, l, c, 20)
        tend = sh(ema(c, 20)) > sh(ema(c, 350)); quieto = (sh(atr(h, l, c, 10)) < sh(atr(h, l, c, 200))) if filtro_atr else np.ones(len(c), bool)
        lo = (c > sh(roll_max(h, n_in))) & tend & quieto; so = (c < sh(roll_min(l, n_in))) & ~tend & quieto
        mn, mx = sh(roll_min(l, n_out)), sh(roll_max(h, n_out))
        return dict(lado=np.where(lo, 1, np.where(so, -1, 0)), tipo="mkt", sl=2 * a20, tp=np.nan,
                    salida=lambda i, lado: (c[i] < mn[i]) if lado == 1 else (c[i] > mx[i]))
    return f


def range_1300(B, ctx):
    """#6 Ruptura del rango de 50 velas que cierra a las 13:00 servidor (06:00 NY + 15 min en M15): OCO a ±10 pips del máximo/mínimo de
    cierres; SL = TP = rango máximo de vela de las 50; BE a 20 pips; vigencia 90 velas."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); pip = ctx["pip"]
    ini = (B.index.hour * 60 + B.index.minute).to_numpy() == 360                       # vela que abre a las 06:00 NY (13:00 servidor)
    hi, lo_, big = roll_max(c, 50), roll_min(c, 50), roll_max(h - l, 50)
    on = ini & np.isfinite(big)
    return dict(lado_l=np.where(on, 1, 0), lado_s=np.where(on, -1, 0), tipo_l="stop", tipo_s="stop", px_l=hi + 10 * pip, px_s=lo_ - 10 * pip,
                sl=big, tp=big, valida=90, be=np.full(len(c), 20 * pip))


def adx_trail(B, ctx):
    """#7 +DI(20) cruza 15 hacia arriba → compra (−DI → venta); SL 2 ATR14, BE a 1,5 ATR, trailing al mínimo de 25 cierres − 0,25 ATR con
    ganancia abierta (pips del original pasados a ATR, como pide la ficha)."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); a14 = atr(h, l, c, 14)
    lo = _cross_up(dmi_plus(h, l, c, 20), 15); so = _cross_up(dmi_minus(h, l, c, 20), 15) & ~lo
    mn25, mx25 = roll_min(c, 25), roll_max(c, 25)
    def tr(i, lado, pos):
        if lado * (c[i] - pos["e"]) <= 0: return np.nan
        return mn25[i] - 0.25 * a14[i] if lado == 1 else mx25[i] + 0.25 * a14[i]
    return dict(lado=np.where(lo, 1, np.where(so, -1, 0)), tipo="mkt", sl=2 * a14, tp=np.nan, be=1.5 * a14, trail=tr)


def mr_a(B, ctx):
    """#8 A: largo si cierre > SMA200 y vela de pánico (cierre < apertura − ATR5) → límite a cierre − 1,2 ATR5 (1 vela); sale con vela verde o a
    las 4; objetivo 10 %; stop protector 3 ATR14 (ficha)."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); a5 = sh(atr(h, l, c, 5)); a14 = atr(h, l, c, 14)
    lo = (c > sh(sma(c, 200))) & (c < o - a5)
    return dict(lado=lo.astype(int), tipo="limit", px=c - 1.2 * a5, valida=1, sl=3 * a14, tp=0.10 * c, tope=4,
                salida=lambda i, lado: c[i] > o[i])


def mr_b(B, ctx):
    """#8 B (MeanRev.sqx): pánico −3 % bajo el mínimo de 3 sobre EMA200 → límite −0,5 ATR5; euforia +3 % sobre el máximo de 3 → venta límite
    +0,5 ATR5; sale con vela de color contrario o a las 5; stop 3 ATR14."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); a5 = sh(atr(h, l, c, 5)); a14 = atr(h, l, c, 14); e200 = sh(ema(c, 200))
    lo = (c < o * 0.97) & (c < sh(roll_min(l, 3))) & (c > e200); so = (c > o * 1.03) & (c > sh(roll_max(h, 3))) & (c > e200) & ~lo
    return dict(lado=np.where(lo, 1, np.where(so, -1, 0)), tipo="limit", px=np.where(lo, c - 0.5 * a5, c + 0.5 * a5), valida=1, sl=3 * a14, tp=np.nan,
                tope=5, salida=lambda i, lado: (c[i] > o[i]) if lado == 1 else (c[i] < o[i]))


def inside_bar(B, ctx):
    """#9 Vela interior → OCO a ±0,15 ATR14 del máximo/mínimo; SL 0,5 rango (piso 12 × fricción), TP 2 rangos; vigencia 20; BE apagado."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); a14 = atr(h, l, c, 14); rg = h - l
    ins = (h < sh(h)) & (l > sh(l)) & np.isfinite(a14)
    return dict(lado_l=np.where(ins, 1, 0), lado_s=np.where(ins, -1, 0), tipo_l="stop", tipo_s="stop", px_l=h + 0.15 * a14, px_s=l - 0.15 * a14,
                sl=np.maximum(0.5 * rg, 12 * ctx["fric"]), tp=2 * rg, valida=20)


def buy_dips(B, ctx):
    """#10 buy_dips.sqx: apertura > SMA250 y RSI5 < 30 → límite cierre − 0,5 ATR14 (2 velas); sale si apertura > EMA7 de aperturas o a las 20; stop 3 ATR14."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); a14 = atr(h, l, c, 14); eo7 = ema(o, 7)
    lo = (o > sma(c, 250)) & (rsi(c, 5) < 30)
    return dict(lado=lo.astype(int), tipo="limit", px=c - 0.5 * sh(a14), valida=2, sl=3 * a14, tp=np.nan, tope=20, salida=lambda i, lado: o[i] > eo7[i])


def price_dip(B, ctx):
    """#10 PriceDip_SP500: −5 % en 3 días sobre SMA200 (y el S&P sobre su SMA200 en índices) → mercado; sale si cierra > máximo previo o a las 10; stop 3 ATR14."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); a14 = atr(h, l, c, 14)
    lo = (c < 0.95 * sh(c, 3)) & (c > sh(sma(c, 200))) & ctx.get("filtro_mercado", np.ones(len(c), bool))
    return dict(lado=lo.astype(int), tipo="mkt", sl=3 * a14, tp=np.nan, tope=10, salida=lambda i, lado: c[i] > h[i - 1])


def double7(B, ctx):
    """#10 Double 7 (Connors): cierre > SMA200 y mínimo de 7 cierres → mercado; sale con máximo de 7 cierres; stop 3 ATR14."""
    o, h, l, c = (B[k].to_numpy(float) for k in "ohlc"); a14 = atr(h, l, c, 14)
    lo = (c > sma(c, 200)) & (c <= roll_min(c, 7)); mx7 = roll_max(c, 7)
    return dict(lado=lo.astype(int), tipo="mkt", sl=3 * a14, tp=np.nan, salida=lambda i, lado: c[i] >= mx7[i])


ESTRATEGIAS = {      # nombre: (función, timeframe, instrumentos)
    "COT1_CROWDING": (cot1, "D1", ("GC", "CL", "HG", "ZB", "6E", "6J")),
    "COT2_SPREAD": (cot2, "D1", ("CL", "GC", "HG", "6E")),
    "COT3_TREND": (cot3, "D1", ("6E", "6B", "6J", "CL", "GC")),
    "VP_POC_USDJPY": (vp_poc, "H1", ("6J",)),
    "TURTLE_55_20": (turtle(55, 20, True), "D1", ("GC", "CL", "6E", "6J", "ZB")),
    "TURTLE_20_10": (turtle(20, 10, False), "D1", ("GC", "CL", "6E", "6J", "ZB")),
    "RANGE_1300": (range_1300, "M15", ("6E", "CL")),
    "ADX_TRAIL": (adx_trail, "H4", ("GC", "CL", "6E", "6J")),
    "MR_A": (mr_a, "D1", ("ES", "NQ", "YM", "RTY", "GC", "ZB", "6E")),
    "MR_B": (mr_b, "D1", ("ES", "NQ", "YM", "RTY", "GC", "ZB", "6E")),
    "INSIDE_BAR": (inside_bar, "H4", ("GC", "CL", "6E", "6J")),
    "BUY_DIPS": (buy_dips, "D1", ("ES", "NQ", "YM", "RTY", "GC", "ZB")),
    "PRICE_DIP": (price_dip, "D1", ("ES", "NQ", "YM", "RTY", "GC", "ZB")),
    "DOUBLE7": (double7, "D1", ("ES", "NQ", "YM", "RTY", "GC", "ZB")),
}


def poc_dia_previo(D: pd.DataFrame, B: pd.DataFrame, bins: int = 150) -> np.ndarray:
    """POC del perfil de volumen (precio típico de M1 ponderado por volumen de tick, `bins` niveles entre mínimo y máximo) de la SESIÓN PREVIA,
    asignado a cada barra de `B`."""
    ses = np.asarray((D.index + pd.Timedelta(hours=6)).strftime("%Y%m%d"), dtype=np.int64); tp = ((D.h + D.l + D.c) / 3).to_numpy(); v = np.maximum(D.v.to_numpy(float), 1e-9)
    poc = {}
    for s_, ix in pd.Series(np.arange(len(ses))).groupby(ses):
        x = tp[ix.values]; lo, hi = x.min(), x.max()
        if hi <= lo: poc[s_] = lo; continue
        k = np.minimum(((x - lo) / (hi - lo) * bins).astype(int), bins - 1); vol = np.bincount(k, v[ix.values], bins); j = int(vol.argmax())
        poc[s_] = lo + (j + 0.5) * (hi - lo) / bins
    dias = np.array(sorted(poc)); vals = np.array([poc[d] for d in dias])
    j = np.searchsorted(dias, B.fecha.to_numpy(), side="left") - 1                     # sesión previa estricta
    return np.where(j >= 0, vals[np.clip(j, 0, len(vals) - 1)], np.nan)
