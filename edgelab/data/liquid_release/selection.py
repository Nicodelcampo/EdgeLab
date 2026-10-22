"""Selección causal del contrato líquido por sesión (D04, D05, D07, D19).

Para cada sesión S de un activo:
  1. D-1 = sesión anterior del calendario (no se resta un día ni se usa la última fecha presente en un archivo).
  2. Se enumeran los contratos del activo que podían competir en D-1 con información de D-1 o anterior: los vistos en el
     censo con fecha <= D-1, cuyo vencimiento nominal (fin del mes de entrega, conocido de antemano) no pasó, y con rank >=
     el líder previo (el roll es monótono). La ausencia en D-1 NO se infiere de datos posteriores (LRA-01).
  3. Cada candidato se mide en D-1 con la fuente adjudicada: volumen negociado en horario regular, ticks y spread típico (mediana en ticks).
     Un candidato con cobertura desconocida en D-1 que pudiera ser elegido bloquea la decisión (UNDETERMINED): no se
     elige "el que sí tiene datos" porque falte el archivo de un competidor.
  4. Elegible = cobertura verificada y volumen/ticks/spread dentro de los límites absolutos de la política. Un spread
     desconocido NO es elegible salvo excepción explícita de la política (LRA-02). UNKNOWN y MISSING bloquean por igual (LRA-03).
  5. Gana el mayor volumen de D-1; empate -> vencimiento más cercano. Si no hay elegible: NO_ELIGIBLE (sin fallback).
Nada de S ni posterior interviene en la decisión de S: se verifica con tests de invariancia por prefijos y por
agregado de filas futuras (valores Y disponibilidad), no sólo por mutación de valores.
"""
from __future__ import annotations

import json
import math
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
    # Un spread típico desconocido no demuestra liquidez. Sólo una excepción EXPLÍCITA (y aprobada) lo vuelve elegible.
    allow_unknown_spread: bool = False

    def __post_init__(self):
        for name in ("min_prev_volume", "min_prev_ticks", "max_prev_spread_p50_ticks", "noncompetitive_frac"):
            v = getattr(self, name)
            if not isinstance(v, (int, float)) or not math.isfinite(float(v)) or float(v) < 0:
                raise ValueError(f"política inválida: {name}={v!r} debe ser un número finito >= 0")


def contract_rank(contract: str) -> tuple[int, int]:
    """'ES 12-25' -> (2025, 12). Orden de vencimiento."""
    mm, yy = contract.split()[-1].split("-")
    return 2000 + int(yy), int(mm)


def delivery_month_end(contract: str) -> int:
    """Último día del mes de entrega, yyyymmdd. Cota superior CONOCIDA DE ANTEMANO del vencimiento (todos los contratos
    listados vencen antes de fin de su mes de entrega): sirve para saber si una ausencia puede ser una laguna de captura
    sin mirar datos posteriores."""
    y, m = contract_rank(contract)
    nxt = pd.Timestamp(year=y + (m == 12), month=1 if m == 12 else m + 1, day=1)
    return int((nxt - pd.Timedelta(days=1)).strftime("%Y%m%d"))


def select_sessions(census: pd.DataFrame, calendar: list[int], policy: LiquidityPolicy) -> pd.DataFrame:
    """census: columnas contract, trade_date, vol, n, spread_p50, coverage (OK/UNKNOWN/MISSING) — un activo.
    calendar: lista ORDENADA de fechas de trading del activo (enteros yyyymmdd).
    Devuelve una fila por sesión (desde la 2.ª del calendario: la 1.ª no tiene D-1)."""
    c = census.copy()
    c["rank"] = c["contract"].map(contract_rank)
    idx = {(r.contract, r.trade_date): r for r in c.itertuples()}
    contracts = sorted(c["contract"].unique(), key=contract_rank)
    first_seen = c.groupby("contract")["trade_date"].min().to_dict()    # <= D-1 equivale a "visto con datos de D-1 o anteriores"
    c = c.sort_values(["contract", "trade_date"]).reset_index(drop=True)
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
                # sin fila en D-1: laguna de captura posible si el contrato ya se había visto (fecha <= D-1) y su vencimiento
                # nominal (fin del mes de entrega, calendario público) no pasó. NO se usa ninguna fecha posterior a D-1.
                if first_seen[k] <= D1 <= delivery_month_end(k):
                    cands.append(dict(contract=k, coverage=UNKNOWN, vol=None, n=None, spread_p50=None))
                continue
            cands.append(dict(contract=k, coverage=r.coverage, vol=float(r.vol), n=int(r.n), spread_p50=r.spread_p50))
        blocked = [x for x in cands if x["coverage"] != OK]
        def spread_ok(sp):
            if sp is None or pd.isna(sp):
                return policy.allow_unknown_spread
            return sp <= policy.max_prev_spread_p50_ticks

        elig = [x for x in cands if x["coverage"] == OK and x["vol"] >= policy.min_prev_volume and x["n"] >= policy.min_prev_ticks
                and spread_ok(x["spread_p50"])]
        row = dict(trade_date=S, prev_trade_date=D1, decision_as_of_trade_date=D1, policy_version=policy.version,
                   candidates=json.dumps(cands, default=str))
        unk = list(blocked)                    # UNKNOWN y MISSING bloquean por igual (LRA-03)
        assumptions = []
        if unk and elig:
            lead_vol = max(x["vol"] for x in elig)
            still = []
            for x in unk:
                recent = c[(c["contract"] == x["contract"]) & (c["trade_date"] < D1)].sort_values("trade_date").tail(policy.noncompetitive_lookback_sessions)
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
