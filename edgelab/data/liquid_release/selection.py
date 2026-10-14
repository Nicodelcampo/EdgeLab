"""Selección causal del contrato líquido por sesión (D04, D05, D07, D19).

Para cada sesión S de un activo:
  1. D-1 = sesión anterior del calendario (no se resta un día ni se usa la última fecha presente en un archivo).
  2. Se enumeran TODOS los contratos del activo que podían competir antes de S (los presentes en el censo con rank >= el
     líder previo: el roll es monótono).
  3. Cada candidato se mide en D-1 con la fuente adjudicada: volumen negociado en horario regular, ticks y spread típico (mediana en ticks).
     Un candidato con cobertura desconocida en D-1 que pudiera ser elegido bloquea la decisión (UNDETERMINED): no se
     elige "el que sí tiene datos" porque falte el archivo de un competidor.
  4. Elegible = cobertura verificada y volumen/ticks/spread dentro de los límites absolutos de la política.
  5. Gana el mayor volumen de D-1; empate -> vencimiento más cercano. Si no hay elegible: NO_ELIGIBLE (sin fallback).
Nada de S ni posterior interviene en la decisión de S (se verifica en tests por mutación del futuro).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pandas as pd

OK, UNKNOWN, MISSING = "OK", "UNKNOWN", "MISSING"
SELECTED, NO_ELIGIBLE, UNDETERMINED = "SELECTED", "NO_ELIGIBLE", "UNDETERMINED"


@dataclass(frozen=True)
class LiquidityPolicy:
    """Límites ABSOLUTOS por activo, congelados antes de cualquier outcome. `approved_by=None` => PROPUESTA."""
    version: str
    min_prev_volume: float
    min_prev_ticks: int
    max_prev_spread_p50_ticks: float
    approved_by: str | None = None
    notes: str = ""
    # Competidor sin dato en D-1: sólo deja de bloquear si su volumen reciente observado es <= noncompetitive_frac del líder
    # (tendría que multiplicarse > 1/frac veces de un día al otro). Es una SUPOSICIÓN y queda escrita en la decisión.
    noncompetitive_frac: float = 0.01
    noncompetitive_lookback_sessions: int = 20


def contract_rank(contract: str) -> tuple[int, int]:
    """'ES 12-25' -> (2025, 12). Orden de vencimiento."""
    mm, yy = contract.split()[-1].split("-")
    return 2000 + int(yy), int(mm)


def select_sessions(census: pd.DataFrame, calendar: list[int], policy: LiquidityPolicy) -> pd.DataFrame:
    """census: columnas contract, trade_date, vol, n, spread_p50, coverage (OK/UNKNOWN/MISSING) — un activo.
    calendar: lista ORDENADA de fechas de trading del activo (enteros yyyymmdd).
    Devuelve una fila por sesión (desde la 2.ª del calendario: la 1.ª no tiene D-1)."""
    c = census.copy()
    c["rank"] = c["contract"].map(contract_rank)
    idx = {(r.contract, r.trade_date): r for r in c.itertuples()}
    contracts = sorted(c["contract"].unique(), key=contract_rank)
    prev_rank = (0, 0)
    prev_choice = None
    out = []
    for i in range(1, len(calendar)):
        S, D1 = calendar[i], calendar[i - 1]
        cands = []
        for k in contracts:
            if contract_rank(k) < prev_rank:
                continue                       # roll monótono: no se vuelve a un vencimiento anterior
            r = idx.get((k, D1))
            if r is None:
                # sin fila en D-1: si existe el contrato en alguna fecha cercana, la ausencia es cobertura desconocida
                lo = c.loc[c.contract == k, "trade_date"]
                if len(lo) and lo.min() <= D1 <= lo.max():
                    cands.append(dict(contract=k, coverage=UNKNOWN, vol=None, n=None, spread_p50=None))
                continue
            cands.append(dict(contract=k, coverage=r.coverage, vol=float(r.vol), n=int(r.n), spread_p50=r.spread_p50))
        blocked = [x for x in cands if x["coverage"] != OK]
        elig = [x for x in cands if x["coverage"] == OK and x["vol"] >= policy.min_prev_volume and x["n"] >= policy.min_prev_ticks
                and (x["spread_p50"] is None or pd.isna(x["spread_p50"]) or x["spread_p50"] <= policy.max_prev_spread_p50_ticks)]
        row = dict(trade_date=S, prev_trade_date=D1, decision_as_of_trade_date=D1, policy_version=policy.version,
                   candidates=json.dumps(cands, default=str))
        unk = [x for x in blocked if x["coverage"] == UNKNOWN]
        assumptions = []
        if unk and elig:
            lead_vol = max(x["vol"] for x in elig)
            still = []
            for x in unk:
                recent = c[(c["contract"] == x["contract"]) & (c["trade_date"] < D1)].tail(policy.noncompetitive_lookback_sessions)
                last_vol = float(recent["vol"].max()) if len(recent) else 0.0
                if last_vol <= policy.noncompetitive_frac * lead_vol:
                    assumptions.append(f"{x['contract']}: sin dato en D-1, volumen reciente máx {last_vol:.0f} <= {policy.noncompetitive_frac:.0%} del líder {lead_vol:.0f}")
                else:
                    still.append(x)
            unk = still
        row["assumptions"] = "; ".join(assumptions)
        if unk:
            row.update(status=UNDETERMINED, contract=None,
                       reason="cobertura desconocida en D-1 de: " + ",".join(x["contract"] for x in unk))
        elif not elig:
            row.update(status=NO_ELIGIBLE, contract=None, reason="ningún candidato cumple la política en D-1")
        else:
            best = sorted(elig, key=lambda x: (-x["vol"], contract_rank(x["contract"])))[0]
            row.update(status=SELECTED, contract=best["contract"], reason="mayor volumen elegible en D-1")
            prev_rank = contract_rank(best["contract"])
            prev_choice = best["contract"]
        row["regime_contract"] = prev_choice
        out.append(row)
    return pd.DataFrame(out)
