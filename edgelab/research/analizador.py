"""Analizador de estrategias (2026-10-26, pedido de Nico: «un módulo donde solamente se mandan estrategias a backtestear, como el
Strategy Analyzer de NT8»). Es un FRENTE: no tiene motor propio.

  - Ejecución: `edgelab/research/sim.py` (simulador sellado por `docs/execution_simulator_spec.md`: entrada en el step siguiente a la
    señal, gana el adverso si target y stop caen en la misma barra, cierre de sesión, firewall del holdout). Corre en escenario
    «ideal» con bid = ask = cierre de la barra y el costo se cobra UNA vez con la fricción canónica (`edgelab/costos.py`: spread medido +
    comisión + slippage), igual que la grilla y el embudo. Un instrumento sin costo medido no corre.
  - Datos: ticks de `fuentes_ticks` (futuro del release: precio de cada operación; Dukascopy `DK:...`: mid) recortados en la frontera
    del holdout (`edgelab/holdout.py`); pedir una ventana que la toque es un error, no un recorte silencioso. Las señales se calculan
    sobre barras M1 hechas con esos ticks; la EJECUCIÓN es tick a tick por defecto (`resolucion="ticks"`: entrada en el primer tick
    posterior a la señal, objetivo/stop/time stop en el tick en que se tocan) o, si se pide, sobre las barras (`resolucion="m1"`,
    más rápido; si objetivo y stop caen en la misma barra gana el adverso).
  - Multiplicidad: CADA corrida se registra en el contador global ANTES de simular (familia de la estrategia, número de variantes del
    barrido). El reporte dice EXPLORATORIO y cuántas pruebas lleva la familia. Nada sale promovido de acá: lo serio va al embudo.

Una estrategia es un módulo (o un objeto) con:
    NOMBRE, FAMILIA, INSTRUMENTO (p. ej. "NQ" o "DK:USATECHIDXUSD"; el costo es el del futuro de referencia)
    PARAMETROS = {"nombre": [valores, ...]}           # opcional: barrido (producto cartesiano); sin él, una variante
    senales(barras: pd.DataFrame, **params) -> list[dict]   # cada señal: available_at (ms UTC, cierre de la barra que la decide),
                                                            # dir (+1/-1), target_pts, stop_pts, time_stop_min (opcional)
`barras` tiene columnas ts (ms de cierre), o, h, l, c, v, ses. La señal sólo puede usar barras con ts <= available_at: el simulador
entra en la barra siguiente, así que mirar adelante no se puede llenar, pero sí se puede CALCULAR mal; `causal()` lo verifica.
"""
from __future__ import annotations

import hashlib
import inspect
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT

ROOT = Path(__file__).resolve().parents[2]
REGISTRO = ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"


# --- datos ---------------------------------------------------------------------------------------------------------------
def barras(instrumento: str, desde: int, hasta: int, entrada: str) -> tuple[pd.DataFrame, float]:
    if int(hasta) >= HOLDOUT_PRIMERA_SESION_INT:
        raise ValueError(f"{hasta} toca el holdout (desde {HOLDOUT_PRIMERA_SESION_INT}): el analizador sólo trabaja con desarrollo")
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG
    lector, tick = F.resolver(instrumento)
    ctx = GG.contexto_m1(lector(int(desde), int(hasta), entrada), tick)
    return barras_de_contexto(ctx), tick


def barras_de_ticks(ts_ns, px, vol, ses) -> pd.DataFrame:
    """Barras M1 vectorizadas (= `contexto_m1`: o/h/l/c/v por minuto, marca de cierre, sesión de la última operación del minuto)."""
    clave = np.asarray(ts_ns, np.int64) // 60_000_000_000 + 1
    if len(clave) > 1 and (np.diff(clave) < 0).any():
        o = np.argsort(clave, kind="stable"); clave, px, vol, ses = clave[o], np.asarray(px)[o], np.asarray(vol)[o], np.asarray(ses)[o]
    ini = np.flatnonzero(np.r_[True, clave[1:] != clave[:-1]]); fin = np.r_[ini[1:], len(clave)] - 1
    px = np.asarray(px, float)
    return pd.DataFrame(dict(ts=clave[ini] * 60_000, o=px[ini], h=np.maximum.reduceat(px, ini), l=np.minimum.reduceat(px, ini), c=px[fin],
                             v=np.add.reduceat(np.asarray(vol, float), ini), ses=np.asarray(ses, np.int64)[fin]))


def barras_de_contexto(ctx: dict) -> pd.DataFrame:
    return pd.DataFrame(dict(ts=np.asarray(ctx["t"], np.int64) * 1000, o=ctx["o"], h=ctx["h"], l=ctx["l"], c=ctx["c"],
                             v=ctx.get("v", np.zeros(len(ctx["c"]))), ses=ctx["ses"]))


def bloques(instrumento: str, desde: int, hasta: int, entrada: str):
    from edgelab.research import fuentes_ticks as F
    lector, tick = F.resolver(instrumento)
    return lector(int(desde), int(hasta), entrada), tick


def costo(instrumento: str) -> float:
    """Fricción canónica por operación en puntos (la del futuro de referencia para un CFD)."""
    from edgelab.research.embudo_runners import friccion
    return float(friccion(instrumento)[0])


# --- ejecución -----------------------------------------------------------------------------------------------------------
def simular(B: pd.DataFrame, senales: list, tick: float, friccion_pts: float) -> pd.DataFrame:
    """ORÁCULO lento (sim.simulate directo, steps = barras). El analizador usa `Mercado.simular`; los tests comparan los dos."""
    from edgelab.research import sim
    steps = [dict(ts=int(t), last=c, bid=c, ask=c, low=l, high=h, session_id=int(s)) for t, c, l, h, s in
             zip(B.ts.to_numpy(), B.c.to_numpy(), B.l.to_numpy(), B.h.to_numpy(), B.ses.to_numpy())]
    sig = [dict(signal_id=f"s{i}", available_at=int(s["available_at"]), dir=int(s["dir"]),
                target_ticks=max(1, int(round(float(s["target_pts"]) / tick))), stop_ticks=max(1, int(round(float(s["stop_pts"]) / tick))),
                time_stop_ms=int(float(s.get("time_stop_min") or 0) * 60_000)) for i, s in enumerate(senales)]
    r = sim.simulate(sig, steps, scenario="ideal", tick_size=tick, tick_value=1.0, guard_caller="analizador")
    T = pd.DataFrame(r.trades)
    if not len(T): return T
    T["bruto_pts"] = T.bruto_ticks * tick; T["neto_pts"] = T.bruto_pts - friccion_pts
    T["mae_pts"] = T.mae_ticks * tick; T["mfe_pts"] = T.mfe_ticks * tick
    T["ses"] = B.set_index("ts").ses.reindex(T.entry_ts).to_numpy()
    T["mes"] = pd.to_datetime(T.entry_ts, unit="ms", utc=True).dt.strftime("%Y-%m")
    return T


RAZONES = np.array(["target", "stop", "stop_ambiguous", "time_stop", "data_edge", "session_close"])


def _nucleo():
    """Núcleo compilado (numba) con la semántica EXACTA de `sim.simulate` para steps con bid = ask = last y escenario «ideal»:
    entrada en el primer step con ts > available_at, rechazo si cambia la sesión o hay una posición abierta, la barra/tick de entrada
    puede salir, gana el adverso si objetivo y stop se tocan en el mismo step, después time stop > fin de datos > cierre de sesión.
    El oráculo es `sim.simulate` (tests/research/test_analizador.py lo compara operación por operación)."""
    from numba import njit

    @njit(cache=True)
    def correr(ts, last, lo, hi, fin_ses, ses, avail, d, tgt_t, stp_t, tstop):
        n = len(ts); m = len(avail)
        e_i = np.full(m, -1, np.int64); x_i = np.full(m, -1, np.int64); raz = np.full(m, -1, np.int8)
        bruto = np.full(m, np.nan); xpx = np.full(m, np.nan); mae = np.zeros(m); mfe = np.zeros(m)
        abierta = -1
        for k in range(m):
            i = np.searchsorted(ts, avail[k], side="right")
            if i >= n: continue
            if i > 0 and ses[i] != ses[i - 1]: continue
            if i <= abierta: continue
            dk = d[k]; ent = last[i]
            tgt = ent + dk * tgt_t[k]; stp = ent - dk * stp_t[k]
            dl = ts[i] + tstop[k] if tstop[k] > 0 else -1
            a = 0.0; f = 0.0; j = i; r = -1; ref = 0.0
            while j < n:
                fav = hi[j] if dk == 1 else lo[j]; adv = lo[j] if dk == 1 else hi[j]
                f = max(f, dk * (fav - ent)); a = max(a, dk * (ent - adv))
                ht = hi[j] >= tgt if dk == 1 else lo[j] <= tgt
                hs = lo[j] <= stp if dk == 1 else hi[j] >= stp
                if ht and hs: r = 2; ref = stp; break
                if ht: r = 0; ref = tgt; break
                if hs: r = 1; ref = stp; break
                if dl >= 0 and ts[j] >= dl: r = 3; break
                if j == n - 1: r = 4; break
                if fin_ses[j]: r = 5; break
                j += 1
            if r < 0: continue
            e_i[k] = i; x_i[k] = j; raz[k] = r; mae[k] = a; mfe[k] = f
            if r <= 2: xpx[k] = ref; bruto[k] = dk * (ref - ent)
            else: xpx[k] = last[j]; bruto[k] = dk * (last[j] - ent)
            abierta = j
        return e_i, x_i, raz, bruto, xpx, mae, mfe
    return correr


_CORRER = None


class Mercado:
    """Steps en memoria (unidades de tick, como `sim._norm_steps`), cargados UNA vez para todas las variantes del barrido."""
    def __init__(self, ts, last, lo, hi, ses, tick):
        self.ts = np.asarray(ts, np.int64); self.tick = float(tick); self.ses = np.asarray(ses, np.int64)
        k = lambda x: np.round(np.asarray(x, float) / self.tick, 6)
        self.last = k(last)
        self.lo = self.last if lo is last else k(lo); self.hi = self.last if hi is last else k(hi)   # ticks: un solo redondeo
        self.fin_ses = np.r_[self.ses[1:] != self.ses[:-1], True] if len(self.ses) else np.zeros(0, bool)
        if len(self.ts):                                                         # firewall del holdout, una vez para todo el rango
            from edgelab.research.holdout_guard import check_holdout
            from edgelab.research.sim import _iso
            check_holdout(_iso(int(self.ts[0])), _iso(int(self.ts[-1]) + 1), purpose="development", caller="analizador")

    @classmethod
    def de_ticks(cls, bloques, tick, con_barras: bool = False):
        """Ticks concatenados (una lectura). Con `con_barras` devuelve también las barras M1 de las señales, hechas con los MISMOS
        ticks y la misma convención que `grilla_generica.contexto_m1` (marca de cierre del minuto; test de igualdad), sin el perfil de
        volumen que el analizador no usa."""
        ts, px, vol, ses = [], [], [], []
        for b in bloques:
            if not len(b): continue
            ts.append(b.ts_ns.to_numpy(np.int64)); px.append(b.px.to_numpy(float)); vol.append(b.vol.to_numpy(float)); ses.append(b.sesion.to_numpy(np.int64))
        if not ts:
            m = cls([], [], [], [], [], tick); return (m, pd.DataFrame(columns=["ts", "o", "h", "l", "c", "v", "ses"])) if con_barras else m
        tns, p, s_ = np.concatenate(ts), np.concatenate(px), np.concatenate(ses)
        m = cls(tns // 10**6, p, p, p, s_, tick)
        return (m, barras_de_ticks(tns, p, np.concatenate(vol), s_)) if con_barras else m

    @classmethod
    def de_barras(cls, B, tick):
        return cls(B.ts.to_numpy(), B.c.to_numpy(), B.l.to_numpy(), B.h.to_numpy(), B.ses.to_numpy(), tick)

    def simular(self, senales: list, friccion_pts: float) -> pd.DataFrame:
        global _CORRER
        if not senales or not len(self.ts): return pd.DataFrame()
        if _CORRER is None: _CORRER = _nucleo()
        orden = sorted(range(len(senales)), key=lambda i: (int(senales[i]["available_at"]), f"s{i}"))   # = sim: (available_at, signal_id)
        S = [senales[i] for i in orden]
        av = np.array([int(x["available_at"]) for x in S], np.int64); d = np.array([int(x["dir"]) for x in S], np.int64)
        if not np.isin(d, (1, -1)).all(): raise ValueError("dir debe ser +1 o -1")
        tg = np.array([max(1, int(round(float(x["target_pts"]) / self.tick))) for x in S], float)
        sp = np.array([max(1, int(round(float(x["stop_pts"]) / self.tick))) for x in S], float)
        tm = np.array([int(float(x.get("time_stop_min") or 0) * 60_000) for x in S], np.int64)
        e_i, x_i, raz, bruto, xpx, mae, mfe = _CORRER(self.ts, self.last, self.lo, self.hi, self.fin_ses, self.ses, av, d, tg, sp, tm)
        ok = e_i >= 0
        if not ok.any(): return pd.DataFrame()
        ei, xi = e_i[ok], x_i[ok]
        T = pd.DataFrame(dict(signal_id=[f"s{orden[k]}" for k in np.flatnonzero(ok)], dir=d[ok], entry_ts=self.ts[ei],
                              entry_px=self.last[ei] * self.tick, exit_ts=self.ts[xi], exit_px=xpx[ok] * self.tick,
                              exit_reason=RAZONES[raz[ok]], bruto_ticks=bruto[ok], mae_ticks=mae[ok], mfe_ticks=mfe[ok],
                              bars_held=xi - ei, ses=self.ses[ei]))
        T["bruto_pts"] = T.bruto_ticks * self.tick; T["neto_pts"] = T.bruto_pts - friccion_pts
        T["mae_pts"] = T.mae_ticks * self.tick; T["mfe_pts"] = T.mfe_ticks * self.tick
        T["mes"] = pd.to_datetime(T.entry_ts, unit="ms", utc=True).dt.strftime("%Y-%m")
        return T


def simular_ticks(fuente_bloques, senales: list, tick: float, friccion_pts: float) -> pd.DataFrame:
    """Ejecución tick a tick con el núcleo compilado (todas las sesiones en un solo stream, como `sim.simulate`)."""
    return Mercado.de_ticks(fuente_bloques, tick).simular(senales, friccion_pts)


def _con_sesion(B: pd.DataFrame, senales: list) -> list:
    """Sesión de cada señal = la de la última barra con ts <= available_at (la que la decidió)."""
    ts = B.ts.to_numpy(); ses = B.ses.to_numpy()
    out = []
    for s_ in senales:
        i = int(np.searchsorted(ts, int(s_["available_at"]), side="right")) - 1
        if i >= 0: out.append(dict(s_, ses=int(ses[i])))
    return out


def reporte(T: pd.DataFrame) -> dict:
    """Lo del Strategy Analyzer, en puntos netos de fricción canónica, más el IC por sesiones (ATJ-11)."""
    if not len(T): return dict(n=0)
    x = T.neto_pts.to_numpy(); eq = np.cumsum(x); dd = float((eq - np.maximum.accumulate(eq)).min())
    gan, per = x[x > 0].sum(), -x[x < 0].sum()
    from edgelab.funnel.escalera import resumen_sesiones
    rs = resumen_sesiones(x, T.ses.to_numpy(), n_boot=2000) if len(x) >= 5 else {}
    return dict(n=int(len(x)), neto_total=float(x.sum()), media=float(x.mean()), ic90_sesiones=rs.get("ic"), p_sesiones=rs.get("p_unilateral"),
                acierto=float((x > 0).mean()), profit_factor=float(gan / per) if per > 0 else None, mejor=float(x.max()), peor=float(x.min()),
                drawdown_max=dd, mae_media=float(T.mae_pts.mean()) if "mae_pts" in T else None, mfe_media=float(T.mfe_pts.mean()) if "mfe_pts" in T else None,
                salidas=T.exit_reason.value_counts().to_dict() if "exit_reason" in T else None,
                por_mes=T.groupby("mes").neto_pts.agg(["count", "sum", "mean"]).round(3).to_dict("index"),
                sin_las_5_mejores=float(np.sort(x)[:-5].sum()) if len(x) > 5 else None)


# --- causalidad y registro ------------------------------------------------------------------------------------------------
def causal(estrategia, B: pd.DataFrame, params: dict, cortes: int = 3) -> list:
    """Las señales hasta un corte no pueden cambiar si se borran las barras posteriores al corte (look-ahead)."""
    todas = estrategia.senales(B, **params); err = []
    for q in np.linspace(0.3, 0.9, cortes):
        tc = int(B.ts.iloc[int(len(B) * q)])
        parcial = estrategia.senales(B[B.ts <= tc].reset_index(drop=True), **params)
        a = sorted((int(s["available_at"]), int(s["dir"])) for s in todas if int(s["available_at"]) <= tc)
        b = sorted((int(s["available_at"]), int(s["dir"])) for s in parcial)
        if a != b: err.append(f"las señales hasta {tc} cambian al ver datos posteriores ({len(a)} vs {len(b)})")
    return err


def variantes(estrategia) -> list:
    p = getattr(estrategia, "PARAMETROS", None) or {}
    return [dict(zip(p, v)) for v in itertools.product(*p.values())] if p else [{}]


def huella(estrategia) -> str:
    try: src = inspect.getsource(estrategia)
    except (OSError, TypeError): src = repr(estrategia)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:12]


def pruebas_de_familia(familia: str, registro: Path = REGISTRO) -> int:
    if not Path(registro).exists(): return 0
    n = 0
    for linea in Path(registro).read_text(encoding="utf-8").splitlines():
        try: r = json.loads(linea)
        except ValueError: continue
        if r.get("family_id") == familia: n += int(r.get("n_trials") or 0)
    return n


def analizar(estrategia, desde: int, hasta: int, *, entrada: str = "/kaggle/input", registro=None, B: pd.DataFrame | None = None,
             tick: float | None = None, friccion_pts: float | None = None, resolucion: str = "ticks", fuente_ticks=None) -> dict:
    """`resolucion` "ticks" (por defecto) o "m1". `fuente_ticks`: función () -> iterable de bloques por sesión (tests y kernel); si no
    se da, se leen de `entrada`. Las señales siempre se calculan sobre barras M1 (columna `ses` = sesión del bloque de ticks)."""
    """Corre la estrategia (y su barrido) y devuelve el reporte. `registro`: TrialRegistry (obligatorio salvo en tests con `B`)."""
    for k in ("NOMBRE", "FAMILIA", "INSTRUMENTO", "senales"):
        if not hasattr(estrategia, k): raise ValueError(f"la estrategia no declara {k}")
    if int(hasta) >= HOLDOUT_PRIMERA_SESION_INT: raise ValueError("toca el holdout: el analizador sólo trabaja con desarrollo")
    fr = costo(estrategia.INSTRUMENTO) if friccion_pts is None else float(friccion_pts)   # en Kaggle la pasa el lanzador (costos canónicos)
    if resolucion not in ("ticks", "m1"): raise ValueError("resolucion: 'ticks' o 'm1'")
    if B is None and resolucion == "ticks" and fuente_ticks is None:              # una sola lectura de ticks: barras y ejecución
        if int(hasta) >= HOLDOUT_PRIMERA_SESION_INT: raise ValueError("toca el holdout")
        gen, tick = bloques(estrategia.INSTRUMENTO, desde, hasta, entrada)
        mercado, B = Mercado.de_ticks(gen, tick, con_barras=True)
    if B is None: B, tick = barras(estrategia.INSTRUMENTO, desde, hasta, entrada)
    if resolucion == "ticks" and fuente_ticks is None:
        fuente_ticks = lambda: bloques(estrategia.INSTRUMENTO, desde, hasta, entrada)[0]
    vs = variantes(estrategia); h = huella(estrategia)
    if registro is None: raise ValueError("sin registro de pruebas no se corre (cada variante cuenta)")
    registro.ensure(f"analizador/{estrategia.FAMILIA}/{h}/{desde}-{hasta}", estrategia.FAMILIA, len(vs),
                    f"analizador {estrategia.NOMBRE} {estrategia.INSTRUMENTO} {desde}-{hasta}, {len(vs)} variantes")
    if (err := causal(estrategia, B, vs[0])): return dict(estrategia=estrategia.NOMBRE, error="NO CAUSAL", detalle=err)
    if "mercado" not in locals():                                                  # una sola lectura de ticks para todo el barrido
        mercado = Mercado.de_ticks(fuente_ticks(), tick) if resolucion == "ticks" else Mercado.de_barras(B, tick)
    filas = []
    for p in vs:
        T = mercado.simular(estrategia.senales(B, **p), fr)
        filas.append(dict(parametros=p, **reporte(T), operaciones=T.to_dict("list") if len(vs) == 1 else None))
    return dict(estrategia=estrategia.NOMBRE, familia=estrategia.FAMILIA, instrumento=estrategia.INSTRUMENTO, periodo=[desde, hasta], resolucion=resolucion,
                friccion_pts=fr, huella=h, variantes=len(vs), resultados=filas,
                aviso=("EXPLORATORIO: nada sale promovido del analizador. Con muchas variantes la mejor está inflada por selección; "
                       "lo prometedor se pre-registra y va al embudo (réplica no mirada y holdout)."),
                pruebas_acumuladas_familia=pruebas_de_familia(estrategia.FAMILIA, getattr(registro, "path", REGISTRO)))


def reporte_de_regla(cx, celdas) -> list:
    """2026-10-26 (Nico: «corré en la herramienta nueva las que dan positivo en el backtest aunque no den señal»): el reporte del
    analizador para celdas CONGELADAS del embudo, con las operaciones que simuló el motor de la grilla que las eligió (entradas límite,
    tope y ejecución tick a tick: `grilla_generica.correr` en modo REP). Mismas cifras que un backtest del Strategy Analyzer."""
    from edgelab.research.grilla_generica import operaciones_de
    O = operaciones_de(cx, celdas); out = []
    for i, c in enumerate(celdas):
        T = O[O.celda == i]
        T = pd.DataFrame(dict(neto_pts=T.neto.to_numpy(float), ses=T.ses.to_numpy(),
                              mes=pd.to_datetime(T.t.to_numpy(), unit="s", utc=True).strftime("%Y%m")))
        out.append(dict(celda=list(c), **reporte(T)))
    return out
