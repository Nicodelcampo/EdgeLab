"""aVolClusterPOI 60t -- reintenta la paridad NT8<->Python con historial real.

Antigravity reporto 126/180 (70,0%) de coincidencia exacta comparando el
oraculo NT8 (E:\\DatosNT8\\avolcluster_gc0426_60t_oracle.csv, GC 04-26, ventana
2026-01-30..2026-03-26) contra un Python que arrancaba el SessionProfile en
frio justo al inicio de esa ventana. Atribuyeron el resto a que el historial
de muestras por bucket horario crece a velocidad distinta segun la hora del
dia en barras de ticks.

Esta corrida prueba esa hipotesis en vez de darla por buena: usa la cinta
COMPLETA de GC 04-26 (arranca 2025-10-10, ~75 sesiones antes de la ventana
exportada), corre el SessionProfile en orden cronologico desde el principio
de la cinta -- el FIFO de lookback_sessions=20 se estabiliza solo antes de
llegar a la ventana comparada -- y SOLO compara zonas creadas en
2026-01-30..2026-03-26 contra el oraculo. Mismo patron que ya resolvio un
mismatch identico en VolTicksPOC2 (docs/parity_coverage/VolTicksPOC2.md):
"con warmup real ... las 23 zonas coinciden exactamente ... la causa era el
arnes, que no le daba historia al kernel -- no el kernel".

Target-free: compara geometria/timestamps de creacion, no outcomes. La
columna 'oracle' en la comparacion trae mfe_ticks/mae_ticks/outcome del CSV
NT8 pero SIEMPRE vacios/cero en este export (reaction_horizon no se activo) --
se ignoran, no se leen.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.bars import build_tick_bars  # noqa: E402
from edgelab.bridge.sessions import session_begin_ns as nominal_session_begin_ns  # noqa: E402
from edgelab.bridge.indicators.avolclusterpoi import (  # noqa: E402
    SessionProfile, detect_block, session_relative_bucket, RESEARCH_DEFAULTS,
)
from tools.bt2_absorption_param_sweep import session_dates_from_ns  # noqa: E402
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks  # noqa: E402
from diag.tasa_senales.avolcluster_plateau_placebo import (  # noqa: E402
    slice_session, block_cells_and_meta,
)

DATA_DIR = Path(r"E:\DatosNT8")
ORACLE_PATH = DATA_DIR / "avolcluster_gc0426_60t_oracle.csv"
CONTRACT = "GC 04-26"
TICK_SIZE_GC = 0.10
WINDOW_BARS = 10
TICKS_PER_BAR = 60
VENTANA_COMPARADA = ("20260130", "20260326")  # inclusive, ambos extremos
TOLERANCIA_SEGUNDOS = 2.0


def parse_oracle_zone_created(path: Path) -> list[dict[str, Any]]:
    """Lee ZONE_CREATED (OFF_PRICE) del CSV NT8. Ignora mfe/mae/outcome (vacios)."""
    out = []
    with open(path, encoding="utf-8") as f:
        next(f)  # linea "# meta,..."
        for row in csv.DictReader(f):
            if row["event_type"] != "ZONE_CREATED":
                continue
            out.append({
                "bar_close_time": row["bar_close_time"],
                "lower_tick": int(row["lower_tick"]),
                "upper_tick": int(row["upper_tick"]),
                "score": float(row["score"]),
            })
    return out


ART_TO_UTC_HOURS = 3  # docs/research/BIGTRAP2_PARIDAD_IMPOSIBLE_2026-08-21.md #7.1:
# "los timestamps del oraculo estan en hora local ART: +3h da coincidencia
# exacta al nanosegundo. Mismo hallazgo que en los exports de ES." Mismo
# pipeline de export (misma maquina, mismo NT8) que genero este oraculo.


def _to_epoch_seconds(iso_ts: str) -> float:
    """bar_close_time del CSV NT8 esta en hora LOCAL ART, no UTC -- se suma
    el offset antes de convertir. Los ts_epoch del lado Python salen de
    ticks.ts_ns, que load_canonical_ticks ya deja en UTC real."""
    dt = datetime.fromisoformat(iso_ts).replace(tzinfo=timezone.utc)
    return dt.timestamp() + ART_TO_UTC_HOURS * 3600


def match_zones(python_zones: list[dict[str, Any]], oracle_zones: list[dict[str, Any]],
                 tol_seconds: float = TOLERANCIA_SEGUNDOS) -> dict[str, Any]:
    """Empareja por (lower_tick, upper_tick) exacto + |dt| <= tol, sin reemplazo,
    greedy por orden temporal (mismo patron de matching que el resto del repo:
    exacto en geometria, tolerancia acotada y declarada en tiempo)."""
    oracle_by_key: dict[tuple, list[int]] = {}
    for i, z in enumerate(oracle_zones):
        oracle_by_key.setdefault((z["lower_tick"], z["upper_tick"]), []).append(i)
    used_oracle = set()
    matched, deltas = [], []
    unmatched_python = []
    for pz in python_zones:
        cands = oracle_by_key.get((pz["lower_tick"], pz["upper_tick"]), [])
        best_i, best_dt = None, None
        for i in cands:
            if i in used_oracle:
                continue
            dt = abs(pz["ts_epoch"] - oracle_zones[i]["ts_epoch"])
            if dt <= tol_seconds and (best_dt is None or dt < best_dt):
                best_i, best_dt = i, dt
        if best_i is not None:
            used_oracle.add(best_i)
            matched.append((pz, oracle_zones[best_i], best_dt))
            deltas.append(best_dt)
        else:
            unmatched_python.append(pz)
    unmatched_oracle = [oracle_zones[i] for i in range(len(oracle_zones)) if i not in used_oracle]

    def _date_of(z: dict[str, Any]) -> str:
        if z.get("trade_date"):
            return z["trade_date"]
        bct = z.get("bar_close_time")
        return bct[:10].replace("-", "") if bct else "?"

    por_sesion: dict[str, dict[str, int]] = {}
    for pz in python_zones:
        d = _date_of(pz)
        por_sesion.setdefault(d, {"n_oracle": 0, "n_python": 0, "n_matched": 0})["n_python"] += 1
    for oz in oracle_zones:
        d = _date_of(oz)
        por_sesion.setdefault(d, {"n_oracle": 0, "n_python": 0, "n_matched": 0})["n_oracle"] += 1
    for pz, oz, _dt in matched:
        d = _date_of(pz)
        por_sesion[d]["n_matched"] += 1

    return {
        "n_oracle": len(oracle_zones),
        "n_python": len(python_zones),
        "n_matched": len(matched),
        "match_rate_vs_oracle": len(matched) / len(oracle_zones) if oracle_zones else None,
        "delta_seconds_mediana": float(np.median(deltas)) if deltas else None,
        "delta_seconds_max": float(np.max(deltas)) if deltas else None,
        "n_unmatched_oracle": len(unmatched_oracle),
        "n_unmatched_python": len(unmatched_python),
        "por_sesion": dict(sorted(por_sesion.items())),
        "unmatched_oracle_full": unmatched_oracle,
        "unmatched_python_full": unmatched_python,
    }


def main() -> int:
    oracle_raw = parse_oracle_zone_created(ORACLE_PATH)
    for z in oracle_raw:
        z["ts_epoch"] = _to_epoch_seconds(z["bar_close_time"])

    path = DATA_DIR / f"{CONTRACT}.Last.txt"
    ticks, *_ = load_canonical_ticks(path, tick_size=TICK_SIZE_GC, max_ticks=None)
    session_labels = session_dates_from_ns(ticks.ts_ns)
    all_dates = sorted(set(session_labels.tolist()))
    print(f"[*] {CONTRACT}: {len(all_dates)} sesiones totales en la cinta, "
          f"{all_dates[0]} .. {all_dates[-1]}", flush=True)

    params = dict(RESEARCH_DEFAULTS)
    profile = SessionProfile(lookback_sessions=params["lookback_sessions"])
    python_zones_off_price: list[dict[str, Any]] = []
    n_sesiones_warmup = 0
    n_sesiones_comparadas = 0

    for d in all_dates:
        mask = session_labels == d
        sess_ticks = slice_session(ticks, mask)
        # Antigravity (2026-08-26): NT8 ancla el bucket horario a
        # sessionIterator.ActualSessionBegin (17:00 CT oficial de plantilla),
        # NO al primer trade real -- verificado en nt8/aVolClusterPOI.cs:295.
        # session_begin_ns() de edgelab.bridge.sessions replica esa semantica
        # (ya validada 7/7 contra el oraculo real, ver su docstring).
        session_begin = nominal_session_begin_ns(int(sess_ticks.ts_ns[0]))
        bars = build_tick_bars(sess_ticks, ticks_per_bar=TICKS_PER_BAR)
        cells_by_block, close_by_block, end_ns_by_block = block_cells_and_meta(
            sess_ticks, bars, window_bars=WINDOW_BARS)
        en_ventana = VENTANA_COMPARADA[0] <= d <= VENTANA_COMPARADA[1]
        if en_ventana:
            n_sesiones_comparadas += 1
        else:
            n_sesiones_warmup += 1
        for blk in sorted(cells_by_block):
            cells = cells_by_block[blk]
            close_tick = int(close_by_block[blk])
            bucket = session_relative_bucket(int(end_ns_by_block[blk]), session_begin,
                                              params["time_bucket_minutes"])
            hist = profile.history_scores(bucket)
            out = detect_block(cells, hist, params=params, close_tick=close_tick)
            profile.add_block(bucket, out["best_score"])
            if en_ventana:
                for z in out["zones"]:
                    if z["kind"] == "OFF_PRICE":
                        python_zones_off_price.append({
                            "trade_date": d,
                            "ts_epoch": int(end_ns_by_block[blk]) / 1e9,
                            "lower_tick": z["lower_tick"], "upper_tick": z["upper_tick"],
                            "score": z["score"],
                        })
        profile.commit()

    print(f"[*] warmup: {n_sesiones_warmup} sesiones antes de la ventana, "
          f"{n_sesiones_comparadas} sesiones comparadas, "
          f"{len(python_zones_off_price)} zonas OFF_PRICE de Python en la ventana", flush=True)

    resultado = match_zones(python_zones_off_price, oracle_raw)
    resultado["n_sesiones_warmup"] = n_sesiones_warmup
    resultado["n_sesiones_comparadas"] = n_sesiones_comparadas
    resultado["ventana"] = list(VENTANA_COMPARADA)
    resultado["tolerancia_segundos"] = TOLERANCIA_SEGUNDOS
    resultado["hipotesis"] = ("con warmup real desde el inicio de la cinta (2025-10-10), "
                               "el match rate deberia acercarse al 100% si la causa del 70% "
                               "reportado sin warmup era el arranque en frio del SessionProfile")
    resultado["target_free"] = True
    resultado["outcomes_opened"] = False

    out_path = REPO_ROOT / "docs" / "research" / "avolcluster_60t_paridad_warmup_gc0426.json"
    out_path.write_text(json.dumps(resultado, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
                         encoding="utf-8")
    printable = {k: v for k, v in resultado.items()
                 if k not in ("unmatched_oracle_full", "unmatched_python_full")}
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    print(f"escrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
