#!/usr/bin/env python3
"""Materializa el piloto Binance USD-M de forma reproducible y sin outcomes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from edgelab.crypto.binance_usdm import (
    BinanceUsdmContract,
    load_binance_usdm_pair,
    sha256_file,
)
from edgelab.crypto.target_free import target_free_census

NORTH_STAR_SHA256 = "d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1"


def _git_snapshot() -> dict[str, object]:
    def run(*args: str) -> str:
        p = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
        if p.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} falló: {p.stderr.strip()}")
        return p.stdout.strip()

    return {
        "head": run("rev-parse", "HEAD"),
        "tree_dirty": bool(run("status", "--porcelain", "--untracked-files=all")),
    }


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(payload, tmp, indent=2, default=str)
        tmp.write("\n")
        temp_name = tmp.name
    os.replace(temp_name, path)


def main() -> int:
    p = argparse.ArgumentParser(description="Binance USD-M trades+bookTicker -> BigTrap2 TickSeries")
    p.add_argument("--trades", type=Path, required=True)
    p.add_argument("--book-ticker", type=Path, required=True)
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--tick-size", required=True, help="PRICE_FILTER.tickSize congelado")
    p.add_argument(
        "--quantity-unit-base",
        required=True,
        help="Unidad explícita de volumen base. No tiene default.",
    )
    p.add_argument("--trades-sha256")
    p.add_argument("--book-sha256")
    p.add_argument("--quantity-unit-status", default="PROVISIONAL_EXCHANGE_STEP_SIZE",
                   help="Estado de la unidad. Sin default economico: describe QUE es el valor.")
    p.add_argument("--quantity-unit-source", default="exchangeInfo.LOT_SIZE.stepSize",
                   help="Procedencia declarada del valor de unidad.")
    p.add_argument("--allow-partial-join", action="store_true")
    p.add_argument("--allow-offtick-prices", action="store_true",
                   help="DIAGNOSTICO: excluye y cuenta precios fuera de la grilla de tick. Marca la corrida como excluyente; no se promueve.")
    p.add_argument("--allow-dirty", action="store_true")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    git_start = _git_snapshot()
    if git_start["tree_dirty"] and not args.allow_dirty:
        raise RuntimeError("árbol git dirty al inicio; usar --allow-dirty sólo para diagnóstico")

    contract = BinanceUsdmContract(
        symbol=args.symbol,
        tick_size=args.tick_size,
        quantity_unit_base=args.quantity_unit_base,
        quantity_unit_status=args.quantity_unit_status,
        quantity_unit_source=args.quantity_unit_source,
    )
    result = load_binance_usdm_pair(
        args.trades,
        args.book_ticker,
        contract,
        expected_trades_sha256=args.trades_sha256,
        expected_book_sha256=args.book_sha256,
        require_full_coverage=not args.allow_partial_join,
        allow_offtick_prices=args.allow_offtick_prices,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ticks_path = args.out_dir / f"{contract.symbol}_bt2_ticks.parquet"
    sidecar_path = args.out_dir / f"{contract.symbol}_bt2_sidecar.parquet"
    manifest_path = args.out_dir / f"{contract.symbol}_bt2_manifest.json"
    result.tick_frame().to_parquet(ticks_path, index=False)
    result.sidecar.to_parquet(sidecar_path, index=False)

    git_end = _git_snapshot()
    provenance_ok = (
        git_start["head"] == git_end["head"]
        and (not git_start["tree_dirty"])
        and (not git_end["tree_dirty"])
    )
    manifest = {
        "schema": "edgelab.crypto.binance_usdm_pilot/1.1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "north_star_sha256": NORTH_STAR_SHA256,
        "outcomes_accessed": False,
        "join_contract": "bookTicker.transaction_time < trade.time",
        "event_identity": ["trade_time_ns", "trade_id"],
        "contract": result.contract.to_dict(),
        "inputs": {
            "trades": {
                "path": str(args.trades),
                "sha256": sha256_file(args.trades),
                "bytes": args.trades.stat().st_size,
            },
            "book_ticker": {
                "path": str(args.book_ticker),
                "sha256": sha256_file(args.book_ticker),
                "bytes": args.book_ticker.stat().st_size,
            },
        },
        "outputs": {
            "ticks": {
                "path": str(ticks_path),
                "sha256": sha256_file(ticks_path),
                "bytes": ticks_path.stat().st_size,
                "rows": len(result.ticks),
            },
            "sidecar": {
                "path": str(sidecar_path),
                "sha256": sha256_file(sidecar_path),
                "bytes": sidecar_path.stat().st_size,
                "rows": len(result.sidecar),
            },
        },
        "report": result.report.to_dict(),
        "target_free_census": target_free_census(result.ticks),
        "population": {
            "event_space": "todos los trades del archivo diario USD-M; sin selección por resultado",
            "included": "trade con bookTicker estrictamente anterior",
            "excluded": "sin book previo; sólo permitido con --allow-partial-join y cuantificado",
        },
        "provenance": {
            "head_start": git_start["head"],
            "head_end": git_end["head"],
            "tree_dirty_start": git_start["tree_dirty"],
            "tree_dirty_end": git_end["tree_dirty"],
            "valid": provenance_ok,
            "allow_dirty_requested": bool(args.allow_dirty),
        },
    }
    _atomic_json(manifest_path, manifest)
    print(json.dumps({"manifest": str(manifest_path), "report": manifest["report"]}, indent=2))
    if not provenance_ok:
        print("PROVENANCE_INVALID: HEAD cambió o el árbol no estuvo limpio", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
