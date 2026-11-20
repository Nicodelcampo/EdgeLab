"""Régimen de reglas de papel sobre el largo (enmienda 1 de docs/research/papel_m1_20261115/PREREGISTRO.md, 2026-11-15).
Variables (fijadas antes de mirar; causales, con lo conocido al cierre del día previo): vol20 (tercil de la volatilidad realizada de 20 días
contra sus 250 días previos), tend60 (signo del retorno de 60 días), noche (tercil del rango nocturno relativo, 18:00→09:30 NY, contra sus
250 previos) y dst (horario de verano de NY). Mapa: media por sesión en cada estado. Encendido walk-forward: trimestre a trimestre, operar
sólo en los estados con media > 0 en los 12 meses previos; se compara con operar siempre y con estados al azar (mismo número)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def variables(D1: pd.DataFrame, H1: pd.DataFrame) -> pd.DataFrame:
    """D1/H1 con hora del servidor (EST+07). Índice = día de sesión (fecha NY de la sesión regular)."""
    c = D1.close; r = np.log(c).diff()
    vol = r.rolling(20).std(); vol_rank = vol.rolling(250).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    tend = np.sign(c / c.shift(60) - 1)
    ny = H1.index - pd.Timedelta(hours=7); X = H1.set_axis(ny)
    ses = (X.index + pd.Timedelta(hours=6)).normalize()                     # 18:00 NY → sesión del día siguiente
    noche_m = (X.index.hour >= 18) | (X.index.hour < 9)
    rn = (X.high[noche_m].groupby(ses[noche_m]).max() - X.low[noche_m].groupby(ses[noche_m]).min()) / X.close.groupby(ses).last().shift(1)
    # 2026-11-18: el ranking se calcula sobre las sesiones CON dato. Con una sola sesión sin barras nocturnas (feriado), rolling(250)
    # devolvía NaN las 250 sesiones siguientes y la mitad de algunos años quedaba sin estado.
    rn = rn.replace([np.inf, -np.inf], np.nan).dropna()
    rn_rank = rn.rolling(250).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    V = pd.DataFrame(dict(vol20=pd.cut(vol_rank.shift(1), [-.01, 1/3, 2/3, 1.01], labels=[0, 1, 2]),
                          tend60=tend.shift(1)), index=D1.index)
    V.index = pd.to_datetime(V.index).normalize()
    V = V.join(pd.DataFrame(dict(noche=pd.cut(rn_rank, [-.01, 1/3, 2/3, 1.01], labels=[0, 1, 2]))), how="left")
    V["dst"] = [int(bool(pd.Timestamp(d).tz_localize("America/New_York").dst())) for d in V.index]
    return V


# K48 (2026-11-18): hora en que se conoce cada variable, en horas desde el inicio de la sesión CME (18:00 NY del día anterior).
# `noche` (18:00→09:00 de la misma sesión) se conoce recién a las 09:00 = 15 h: para ASIA, que entra entre las 18:00 y las 09:00, miraba
# el futuro y fabricó la «noche movida». vol20, tend60 y noche_previa salen del día anterior (0 h); dst se conoce siempre.
CONOCIDA_H = {"vol20": 0.0, "tend60": 0.0, "noche": 15.0, "noche_previa": 0.0, "dst": 0.0}


def horas_de_sesion(t_unix) -> np.ndarray:
    """Horas desde el inicio de la sesión CME (18:00 NY) de cada entrada (segundos unix)."""
    ny = pd.to_datetime(np.asarray(t_unix, float), unit="s", utc=True).tz_convert("America/New_York")
    return ((ny.hour + ny.minute / 60 - 18) % 24).to_numpy(float)


def causales(t_entradas, variables=("vol20", "tend60", "noche", "dst")) -> dict:
    """{variable: True si se conoce antes de TODAS las entradas}. Una variable no causal no se usa para mapa ni encendido."""
    h = horas_de_sesion(t_entradas)
    return {v: bool(len(h) and (h >= CONOCIDA_H[v]).all()) for v in variables}


def mapa(ses_pnl: pd.Series, V: pd.DataFrame, *, t_entradas) -> dict:
    """K48: `t_entradas` (segundos unix de las entradas) es obligatorio; las variables que se conocen después de alguna entrada
    salen como NO_CAUSAL en vez de medirse."""
    X = V.reindex(ses_pnl.index).assign(p=ses_pnl.values); out = {}; ok = causales(t_entradas)
    for v in ("vol20", "tend60", "noche", "dst"):
        if not ok[v]: out[v] = "NO_CAUSAL"; continue
        g = X.groupby(v, observed=True).p
        out[v] = {str(k): dict(n=int(x.count()), media=round(float(x.mean()), 2), ee=round(float(x.std(ddof=1) / np.sqrt(max(x.count(), 1))), 2)) for k, x in g}
    q = X.p.groupby(X.index.to_period("Q")).agg(["count", "mean"]).round(2)
    out["trimestres_positivos"] = f"{int((q['mean'] > 0).sum())}/{len(q)}"
    return out


def encendido(ses_pnl: pd.Series, V: pd.DataFrame, n_azar: int = 2000, semilla: int = 0, *, t_entradas) -> dict:
    rng = np.random.default_rng(semilla); X = V.reindex(ses_pnl.index).assign(p=ses_pnl.values)
    Q = X.index.to_period("Q"); trims = sorted(Q.unique()); out = {}; ok = causales(t_entradas)
    for v in ("vol20", "tend60", "noche", "dst"):
        if not ok[v]: out[v] = "NO_CAUSAL"; continue
        tot_on, tot_all, azar = [], [], []
        estados = [s for s in X[v].dropna().unique()]
        for qi in trims[4:]:
            prev = X[(Q >= qi - 4) & (Q < qi)]; cur = X[Q == qi]
            m = prev.groupby(v, observed=True).p.mean(); on = [s for s in m.index if m[s] > 0]
            tot_on.append(cur.p[cur[v].isin(on)].sum()); tot_all.append(cur.p.sum())
            azar.append([cur.p[cur[v].isin(rng.choice(estados, size=len(on), replace=False))].sum() if on else 0.0 for _ in range(n_azar)])
        A = np.array(azar).sum(axis=0); on_t = float(np.sum(tot_on))
        out[v] = dict(encendido=round(on_t, 1), siempre=round(float(np.sum(tot_all)), 1), azar_media=round(float(A.mean()), 1),
                      p_vs_azar=round(float((A >= on_t).mean()), 3), trimestres=len(tot_on))
    return out
