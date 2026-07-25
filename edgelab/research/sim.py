"""Simulador de ejecución mínimo — implementación de `docs/execution_simulator_spec.md`.

La spec está SELLADA: es contrato. Este módulo la implementa literalmente; los
golden tests de §9 deben reproducirse con números IDÉNTICOS.

Decisión de Nico: simulador propio mínimo. `edgelab/engine.py` (legacy) NO se usa
para evidencia formal. **Prohibido importar kernels**: las señales entran ya
materializadas desde el store (`edgelab.bridge.features`).

Aritmética: internamente TODO se computa en **unidades de tick** (precio /
tick_size). Los precios reales viven en la grilla de ticks, así que en esas
unidades los valores son enteros (y los mid, semienteros) — eso elimina el ruido
de punto flotante en las comparaciones de disparo y hace exacta la identidad
aditiva de costos.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..bridge.identity import canonical_json
from .costs import CostScenario, get_scenario

EXIT_REASONS = ("target", "stop", "stop_ambiguous", "time_stop",
                "session_close", "data_edge")
REJECT_REASONS = ("no_execution_step", "session_boundary_no_fill", "position_open")


@dataclass
class SimResult:
    trades: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    digest: str = ""


def _tk(price, tick_size):
    """Precio -> unidades de tick, sin ruido de fp (los precios están en grilla)."""
    return round(price / tick_size, 6)


def _iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S")


def _norm_steps(steps, tick_size):
    """Normaliza los steps a unidades de tick y precomputa fin-de-sesión."""
    out = []
    for i, s in enumerate(steps):
        last = _tk(s["last"], tick_size)
        out.append(dict(
            i=i, ts=int(s["ts"]),
            last=last,
            bid=_tk(s["bid"], tick_size), ask=_tk(s["ask"], tick_size),
            # steps de tick: low = high = last (punto). De barra: rango real.
            low=_tk(s["low"], tick_size) if s.get("low") is not None else last,
            high=_tk(s["high"], tick_size) if s.get("high") is not None else last,
            session_id=s.get("session_id"),
        ))
    for i, s in enumerate(out):
        s["last_of_session"] = (i == len(out) - 1
                                or out[i + 1]["session_id"] != s["session_id"])
    return out


def simulate(signals, steps, *, scenario="base", tick_size=None, tick_value=None,
             close_at_session_end=True, guard_purpose="development",
             guard_caller="sim.simulate", guard_log_path=None, check_guard=True):
    """Simula señales sobre un stream de steps. Ver la spec para la semántica.

    `scenario`: nombre (`ideal|base|adverso|severo`) o `CostScenario`.
    `close_at_session_end`: CAMP-001 E4 lo fija en True.
    """
    sc = scenario if isinstance(scenario, CostScenario) else get_scenario(scenario)
    if tick_size is None or tick_value is None:
        raise ValueError("tick_size y tick_value son obligatorios (del catálogo de instrumento)")

    st = _norm_steps(steps, tick_size)

    # --- firewall del holdout: el simulador declara su propia ventana ---
    if check_guard and st:
        from .holdout_guard import check_holdout
        check_holdout(_iso(st[0]["ts"]), _iso(st[-1]["ts"] + 1),
                      purpose=guard_purpose, caller=guard_caller,
                      log_path=guard_log_path)

    sigs = sorted(signals, key=lambda s: (int(s["available_at"]), str(s["signal_id"])))
    trades, rejected = [], []
    open_until_idx = -1          # índice del step en que se cerró el último trade

    for sig in sigs:
        av = int(sig["available_at"])
        d = int(sig["dir"])
        if d not in (1, -1):
            raise ValueError("dir debe ser +1 o -1, no %r" % (d,))

        # --- entrada: primer step con ts ESTRICTAMENTE > available_at ---
        e = None
        for s in st:
            if s["ts"] > av:
                e = s
                break
        if e is None:
            rejected.append(dict(signal_id=sig["signal_id"], reason="no_execution_step"))
            continue

        # sesión de la señal = la del último step con ts <= available_at
        sig_session = None
        for s in st:
            if s["ts"] <= av:
                sig_session = s["session_id"]
            else:
                break
        if sig_session is not None and e["session_id"] != sig_session:
            rejected.append(dict(signal_id=sig["signal_id"],
                                 reason="session_boundary_no_fill"))
            continue

        # una sola posición simultánea
        if e["i"] <= open_until_idx:
            rejected.append(dict(signal_id=sig["signal_id"], reason="position_open"))
            continue

        # --- fill de entrada (market: cruza el book + slippage adverso) ---
        entry_book = e["ask"] if d == 1 else e["bid"]
        entry_mid = (e["bid"] + e["ask"]) / 2.0
        entry_fill = entry_book + d * sc.slip_entry

        tgt = entry_fill + d * int(sig["target_ticks"])
        stp = entry_fill - d * int(sig["stop_ticks"])
        tstop_ms = int(sig.get("time_stop_ms") or 0)
        deadline = e["ts"] + tstop_ms if tstop_ms > 0 else None

        exit_ref = exit_kind = exit_reason = None
        x = None
        mfe = mae = 0.0
        for s in st[e["i"]:]:                     # la barra de entrada TAMBIÉN puede salir
            fav = s["high"] if d == 1 else s["low"]
            adv = s["low"] if d == 1 else s["high"]
            mfe = max(mfe, d * (fav - entry_fill))
            mae = max(mae, d * (entry_fill - adv))

            hit_t = (s["high"] >= tgt) if d == 1 else (s["low"] <= tgt)
            hit_s = (s["low"] <= stp) if d == 1 else (s["high"] >= stp)
            if hit_t and hit_s:                   # §6.3 GANA EL ADVERSO
                x, exit_ref, exit_kind, exit_reason = s, stp, "level_stop", "stop_ambiguous"
                break
            if hit_t:
                x, exit_ref, exit_kind, exit_reason = s, tgt, "level_target", "target"
                break
            if hit_s:
                x, exit_ref, exit_kind, exit_reason = s, stp, "level_stop", "stop"
                break
            # Sin salida por nivel, precedencia de salidas market (fijada por los
            # goldens G4 y G7, que se solapan en el último step):
            #   1) time_stop  — condición propia del trade (habría salido igual)
            #   2) data_edge  — se acabaron los datos (más informativo: marca
            #                   truncamiento por disponibilidad, se cuenta aparte)
            #   3) session_close — solo si HAY más datos y la sesión terminó
            if deadline is not None and s["ts"] >= deadline:
                x, exit_kind, exit_reason = s, "market", "time_stop"
                break
            if s["i"] == len(st) - 1:             # último step del dataset
                x, exit_kind, exit_reason = s, "market", "data_edge"
                break
            if close_at_session_end and s["last_of_session"]:
                x, exit_kind, exit_reason = s, "market", "session_close"
                break

        # --- fill de salida + descomposición de costos (§7) ---
        if exit_kind == "market":
            exit_book = x["bid"] if d == 1 else x["ask"]
            exit_mid = (x["bid"] + x["ask"]) / 2.0
            slip_x = sc.slip_exit
            exit_fill = exit_book - d * slip_x
            bruto = d * (exit_mid - entry_mid)
            spread = d * (entry_book - entry_mid) + d * (exit_mid - exit_book)
        else:
            slip_x = sc.slip_target if exit_kind == "level_target" else sc.slip_stop
            exit_fill = exit_ref - d * slip_x
            bruto = d * (exit_ref - entry_mid)
            spread = d * (entry_book - entry_mid)
        slippage = sc.slip_entry + slip_x
        neto = bruto - spread - slippage

        # identidad exacta (§7): neto == dir*(exit_fill - entry_fill)
        from_fills = d * (exit_fill - entry_fill)
        if abs(neto - from_fills) > 1e-9:
            raise AssertionError(
                "descomposición de costos rota en %s: neto=%r vs fills=%r"
                % (sig["signal_id"], neto, from_fills))

        com = 2 * sc.commission_per_side_usd
        trades.append(dict(
            signal_id=str(sig["signal_id"]), dir=d,
            entry_ts=e["ts"], entry_px=round(entry_fill * tick_size, 10),
            exit_ts=x["ts"], exit_px=round(exit_fill * tick_size, 10),
            exit_reason=exit_reason,
            bruto_ticks=bruto, spread_ticks=spread, slippage_ticks=float(slippage),
            comision_usd=com, neto_ticks=neto,
            neto_usd=round(neto * tick_value - com, 10),
            mae_ticks=mae, mfe_ticks=mfe, bars_held=x["i"] - e["i"]))
        open_until_idx = x["i"]

    # --- resumen + digest determinista ---
    by_reason = {}
    for t in trades:
        by_reason[t["exit_reason"]] = by_reason.get(t["exit_reason"], 0) + 1
    by_rej = {}
    for r in rejected:
        by_rej[r["reason"]] = by_rej.get(r["reason"], 0) + 1
    n = len(trades)
    summary = dict(
        scenario=sc.name, n_trades=n, n_rejected=len(rejected),
        exit_reasons=by_reason, reject_reasons=by_rej,
        gross_ticks=sum(t["bruto_ticks"] for t in trades),
        spread_ticks=sum(t["spread_ticks"] for t in trades),
        slippage_ticks=sum(t["slippage_ticks"] for t in trades),
        commission_usd=sum(t["comision_usd"] for t in trades),
        net_ticks=sum(t["neto_ticks"] for t in trades),
        net_usd=sum(t["neto_usd"] for t in trades),
        expectancy_net_usd=(sum(t["neto_usd"] for t in trades) / n) if n else None,
        expectancy_net_ticks=(sum(t["neto_ticks"] for t in trades) / n) if n else None,
        close_at_session_end=close_at_session_end)
    digest = hashlib.sha256(canonical_json(trades).encode("utf-8")).hexdigest()[:16]
    return SimResult(trades=trades, rejected=rejected, summary=summary, digest=digest)
