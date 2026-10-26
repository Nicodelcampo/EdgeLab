"""Analizador de estrategias (2026-10-26, pedido de Nico: «un módulo donde solamente se mandan estrategias a backtestear, como el
Strategy Analyzer de NT8»). Es un FRENTE: no tiene motor propio.

  - Ejecución: `edgelab/research/sim.py` (simulador sellado por `docs/execution_simulator_spec.md`: entrada en el step siguiente a la
    señal, gana el adverso si target y stop caen en la misma barra, cierre de sesión, firewall del holdout). Corre en escenario
    «ideal» con bid = ask = cierre de la barra y el costo se cobra UNA vez con la fricción canónica (`edgelab/costos.py`: spread medido +
    comisión + slippage), igual que la grilla y el embudo. Un instrumento sin costo medido no corre.
  - Datos: barras M1 de `fuentes_ticks` (futuro del release o Dukascopy `DK:...`) vía `grilla_generica.contexto_m1`, recortadas en la
    frontera del holdout (`edgelab/holdout.py`); pedir una ventana que la toque es un error, no un recorte silencioso.
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


def barras_de_contexto(ctx: dict) -> pd.DataFrame:
    return pd.DataFrame(dict(ts=np.asarray(ctx["t"], np.int64) * 1000, o=ctx["o"], h=ctx["h"], l=ctx["l"], c=ctx["c"],
                             v=ctx.get("v", np.zeros(len(ctx["c"]))), ses=ctx["ses"]))


def costo(instrumento: str) -> float:
    """Fricción canónica por operación en puntos (la del futuro de referencia para un CFD)."""
    from edgelab.research.embudo_runners import friccion
    return float(friccion(instrumento)[0])


# --- ejecución -----------------------------------------------------------------------------------------------------------
def simular(B: pd.DataFrame, senales: list, tick: float, friccion_pts: float) -> pd.DataFrame:
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


def reporte(T: pd.DataFrame) -> dict:
    """Lo del Strategy Analyzer, en puntos netos de fricción canónica, más el IC por sesiones (ATJ-11)."""
    if not len(T): return dict(n=0)
    x = T.neto_pts.to_numpy(); eq = np.cumsum(x); dd = float((eq - np.maximum.accumulate(eq)).min())
    gan, per = x[x > 0].sum(), -x[x < 0].sum()
    from edgelab.funnel.escalera import resumen_sesiones
    rs = resumen_sesiones(x, T.ses.to_numpy(), n_boot=2000) if len(x) >= 5 else {}
    return dict(n=int(len(x)), neto_total=float(x.sum()), media=float(x.mean()), ic90_sesiones=rs.get("ic"), p_sesiones=rs.get("p_unilateral"),
                acierto=float((x > 0).mean()), profit_factor=float(gan / per) if per > 0 else None, mejor=float(x.max()), peor=float(x.min()),
                drawdown_max=dd, mae_media=float(T.mae_pts.mean()), mfe_media=float(T.mfe_pts.mean()),
                salidas=T.exit_reason.value_counts().to_dict(), por_mes=T.groupby("mes").neto_pts.agg(["count", "sum", "mean"]).round(3).to_dict("index"),
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
             tick: float | None = None, friccion_pts: float | None = None) -> dict:
    """Corre la estrategia (y su barrido) y devuelve el reporte. `registro`: TrialRegistry (obligatorio salvo en tests con `B`)."""
    for k in ("NOMBRE", "FAMILIA", "INSTRUMENTO", "senales"):
        if not hasattr(estrategia, k): raise ValueError(f"la estrategia no declara {k}")
    if int(hasta) >= HOLDOUT_PRIMERA_SESION_INT: raise ValueError("toca el holdout: el analizador sólo trabaja con desarrollo")
    fr = costo(estrategia.INSTRUMENTO) if friccion_pts is None else float(friccion_pts)   # en Kaggle la pasa el lanzador (costos canónicos)
    if B is None: B, tick = barras(estrategia.INSTRUMENTO, desde, hasta, entrada)
    vs = variantes(estrategia); h = huella(estrategia)
    if registro is None: raise ValueError("sin registro de pruebas no se corre (cada variante cuenta)")
    registro.ensure(f"analizador/{estrategia.FAMILIA}/{h}/{desde}-{hasta}", estrategia.FAMILIA, len(vs),
                    f"analizador {estrategia.NOMBRE} {estrategia.INSTRUMENTO} {desde}-{hasta}, {len(vs)} variantes")
    if (err := causal(estrategia, B, vs[0])): return dict(estrategia=estrategia.NOMBRE, error="NO CAUSAL", detalle=err)
    filas = []
    for p in vs:
        T = simular(B, estrategia.senales(B, **p), tick, fr)
        filas.append(dict(parametros=p, **reporte(T), operaciones=T.to_dict("list") if len(vs) == 1 else None))
    return dict(estrategia=estrategia.NOMBRE, familia=estrategia.FAMILIA, instrumento=estrategia.INSTRUMENTO, periodo=[desde, hasta],
                friccion_pts=fr, huella=h, variantes=len(vs), resultados=filas,
                aviso=("EXPLORATORIO: nada sale promovido del analizador. Con muchas variantes la mejor está inflada por selección; "
                       "lo prometedor se pre-registra y va al embudo (réplica no mirada y holdout)."),
                pruebas_acumuladas_familia=pruebas_de_familia(estrategia.FAMILIA, getattr(registro, "path", REGISTRO)))
