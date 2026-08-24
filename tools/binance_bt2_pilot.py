#!/usr/bin/env python3
"""Materializa el piloto Binance USD-M de forma reproducible y sin outcomes."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from edgelab.crypto.binance_usdm import (
    BinanceUsdmContract,
    load_binance_usdm_pair,
    sha256_file,
)

NORTH_STAR_SHA256 = "d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1"


def _git_state() -> dict[str, object]:
    def run(*args: str) -> str:
        p = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
        return p.stdout.strip() if p.returncode == 0 else "UNKNOWN"

    head = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return {"head_start": head, "head_end": head, "tree_dirty": bool(status and status != "UNKNOWN")}


def main() -> int:
    p = argparse.ArgumentParser(description="Binance USD-M trades+bookTicker -> BigTrap2 TickSeries")
    p.add_argument("--trades", type=Path, required=True)
    p.add_argument("--book-ticker", type=Path, required=True)
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--tick-size", required=True, help="PRICE_FILTER.tickSize congelado")
    p.add_argument(
        "--quantity-unit-base",
        required=True,
        help="Unidad explícita de volumen base; p.ej. 0.001 BTC. No tiene default.",
    )
    p.add_argument("--trades-sha256")
    p.add_argument("--book-sha256")
    p.add_argument("--allow-partial-join", action="store_true")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    contract = BinanceUsdmContract(
        symbol=args.symbol,
        tick_size=args.tick_size,
        quantity_unit_base=args.quantity_unit_base,
    )
    result = load_binance_usdm_pair(
        args.trades,
        args.book_ticker,
        contract,
        expected_trades_sha256=args.trades_sha256,
        expected_book_sha256=args.book_sha256,
        require_full_coverage=not args.allow_partial_join,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ticks_path = args.out_dir / f"{contract.symbol}_bt2_ticks.parquet"
    sidecar_path = args.out_dir / f"{contract.symbol}_bt2_sidecar.parquet"
    manifest_path = args.out_dir / f"{contract.symbol}_bt2_manifest.json"
    result.tick_frame().to_parquet(ticks_path, index=False)
    result.sidecar.to_parquet(sidecar_path, index=False)

    manifest = {
        "schema": "edgelab.crypto.binance_usdm_pilot/1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "north_star_sha256": NORTH_STAR_SHA256,
        "outcomes_accessed": False,
        "join_contract": "bookTicker.transaction_time < trade.time",
        "contract": result.contract.to_dict(),
        "inputs": {
            "trades": {"path": str(args.trades), "sha256": sha256_file(args.trades)},
            "book_ticker": {"path": str(args.book_ticker), "sha256": sha256_file(args.book_ticker)},
        },
        "outputs": {
            "ticks": str(ticks_path),
            "sidecar": str(sidecar_path),
        },
        "report": result.report.to_dict(),
        "population": {
            "event_space": "todos los trades del archivo diario USD-M; sin selección por resultado",
            "included": "trade con bookTicker estrictamente anterior",
            "excluded": "sin book previo; sólo permitido con --allow-partial-join y cuantificado",
        },
        "justificacion_economica": (
            "Probar si microestructura 24/7 y mayor heterogeneidad de liquidez permite que "
            "BigTrap2Absorption aporte información transferible y finalmente expectativa neta."
        ),
        "como_podria_refutarse": (
            "Falla causal del join, sensibilidad no resuelta a la unidad de volumen, gaps no "
            "explicados, o ausencia de información estable en días/activos preregistrados."
        ),
        "provenance": _git_state(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "report": manifest["report"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
