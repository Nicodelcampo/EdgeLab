"""Contrato de calidad de la línea SQX/MT5 (2026-11-14, pedido de Nico: «que todas las estrategias que se lancen estén confirmadas como
que valen la pena»). Una estrategia sólo pasa a cartera si cumple TODO lo de `REQ`; los umbrales salen de las lecciones de EdgeLab
(docs/research/FACTORES_CON_VENTAJA.md, docs/infra/SQX_MT5_EDGELAB_INFRA.md) y se fijan ANTES de ver resultados: cambiarlos es una
decisión humana registrada, nunca un ajuste después de mirar.

Entrada: trades de SQX (`tools/sqx_corrida.py exportar`, riesgo fijo por operación → R = P/L / riesgo) y el contexto de la corrida
(nulo de la búsqueda, total generado, otros mercados, cartera viva). Salida: checklist con el motivo de cada fallo y veredicto
VALE / NO_VALE / PENDIENTE (falta un dato: nulo, tramo reciente, paridad MT5)."""
from __future__ import annotations

import numpy as np
import pandas as pd

REQ = dict(
    r_neto_min=0.10,             # R neto medio por operación (después de spread, comisión y swap): lo que queda para pagar el desafío
    t_min_sobre_nulo=True,       # t de la estrategia > p95 del máximo t del nulo de la búsqueda (Builder sobre serie sintética, mismo K)
    ops_min=200,                 # potencia: con < 200 operaciones el error de la media en R es ≥ 0,1
    ops_por_anio=(12, 400),      # frecuencia: macro pero operable (≥ 1 por mes); el techo evita scalping disfrazado
    bloques_min=4,               # de 5 bloques cronológicos con R > 0 (estabilidad; regla global de evidencia, DECISIONES_20261108)
    reciente_positivo=True,      # 2024-01 → 2025-07 (tramo sin usar para construir), mirado UNA vez
    otros_mercados_min=0.6,      # fracción de los activos de su clase (re-test sin re-optimizar) con R > 0
    dd_max_r=20.0,               # máximo drawdown en R (con riesgo 0,5 % por operación ≈ 10 %: entra en las reglas de las props)
    racha_perdedora_max=12,      # operaciones perdedoras seguidas
    top5_max=0.5,                # las 5 mejores operaciones no pueden explicar más de la mitad del resultado
    corr_cartera_max=0.3,        # correlación del P&L diario con cada estrategia ya en cartera
    por_idea_activo_max=2,       # diversificación: a lo sumo 2 estrategias por (idea, activo)
    peor_op_min_r=-3.0,          # gaps (domingo, noticias): con llenado realista una pérdida puede pasar de −1 R; más allá de −3 R no
    gap_r_max=0.3,               # R perdido por encima de −1 R (gaps) como fracción del resultado total
)


def r_de_trades(T: pd.DataFrame, riesgo: float) -> pd.Series:
    return T["pl"].astype(float) / float(riesgo)


def evaluar(T: pd.DataFrame, riesgo: float, *, t_nulo_p95: float | None = None, reciente_r: float | None = None,
            otros_mercados: list | None = None, cartera_diaria: dict | None = None, ya_en_cartera: int = 0) -> dict:
    """Checklist del contrato. T: trades con openTime, closeTime, pl. Lo que falta → PENDIENTE (nunca pasa por omisión)."""
    T = T.sort_values("closeTime").reset_index(drop=True); r = r_de_trades(T, riesgo).to_numpy(); n = len(r)
    t0, t1 = pd.to_datetime(T.openTime.iloc[0], format="%Y.%m.%d %H:%M:%S"), pd.to_datetime(T.closeTime.iloc[-1], format="%Y.%m.%d %H:%M:%S")
    anios = max((t1 - t0).days / 365.25, 1e-9); m = r.mean() if n else np.nan; se = r.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    eq = np.cumsum(r); dd = float(np.max(np.maximum.accumulate(eq) - eq)) if n else np.nan
    racha = max((len(x) for x in "".join("p" if v <= 0 else "g" for v in r).split("g")), default=0)
    bl = [b.mean() > 0 for b in np.array_split(r, 5)] if n >= 5 else []
    top5 = float(np.sort(r)[-5:].sum() / eq[-1]) if n >= 5 and eq[-1] > 0 else np.inf
    C = {}
    C["r_neto"] = (m >= REQ["r_neto_min"], f"{m:+.3f} R (mín {REQ['r_neto_min']})")
    C["ops"] = (n >= REQ["ops_min"], f"{n} (mín {REQ['ops_min']})")
    C["frecuencia"] = (REQ["ops_por_anio"][0] <= n / anios <= REQ["ops_por_anio"][1], f"{n / anios:.1f}/año")
    C["bloques"] = (sum(bl) >= REQ["bloques_min"], f"{sum(bl)}/5")
    C["drawdown"] = (dd <= REQ["dd_max_r"], f"{dd:.1f} R")
    C["racha"] = (racha <= REQ["racha_perdedora_max"], f"{racha}")
    C["concentracion"] = (top5 <= REQ["top5_max"], f"top5 = {top5:.0%} del total")
    exceso = float(np.clip(-r - 1.0, 0, None).sum()); peor = float(r.min()) if n else np.nan
    C["peor_operacion"] = (peor >= REQ["peor_op_min_r"], f"{peor:+.2f} R")
    C["gaps"] = (exceso <= REQ["gap_r_max"] * max(eq[-1], 1e-9) if n else False, f"{exceso:.1f} R perdidos más allá de −1 R")
    tt = m / se if se and se > 0 else np.nan
    C["nulo_busqueda"] = (None, "falta el nulo") if t_nulo_p95 is None else (tt > t_nulo_p95, f"t {tt:.2f} vs p95 nulo {t_nulo_p95:.2f}")
    C["reciente"] = (None, "falta el tramo reciente") if reciente_r is None else (reciente_r > 0, f"{reciente_r:+.3f} R")
    C["otros_mercados"] = ((None, "falta el re-test en otros mercados") if not otros_mercados else
                           (np.mean([x > 0 for x in otros_mercados]) >= REQ["otros_mercados_min"], f"{sum(x > 0 for x in otros_mercados)}/{len(otros_mercados)} > 0"))
    if cartera_diaria:
        d = pd.Series(r, index=pd.to_datetime(T.closeTime, format="%Y.%m.%d %H:%M:%S").dt.normalize()).groupby(level=0).sum()
        cm = max((abs(d.corr(s.reindex(d.index.union(s.index), fill_value=0).reindex(d.index))) for s in cartera_diaria.values()), default=0.0)
        C["correlacion"] = (cm <= REQ["corr_cartera_max"], f"máx |ρ| {cm:.2f}")
    C["diversificacion"] = (ya_en_cartera < REQ["por_idea_activo_max"], f"{ya_en_cartera} ya en cartera de esta idea y activo")
    fallos = [k for k, (ok, _) in C.items() if ok is False]; pend = [k for k, (ok, _) in C.items() if ok is None]
    return dict(veredicto="NO_VALE" if fallos else ("PENDIENTE" if pend else "VALE"), fallos=fallos, pendientes=pend,
                checks={k: dict(ok=ok, detalle=d) for k, (ok, d) in C.items()})
