#!/usr/bin/env python3
"""Materializa una vez cada configuración autorizada y publica coordenadas PIT.

El trabajo pesado se ejecuta localmente. Este runner no lee outcomes ni P&L y
rechaza cualquier dato con timestamp >= 2026-07-01 UTC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from edgelab.bridge import bars as bars_mod  # noqa: E402
from edgelab.bridge import coordinate_store, identity, store  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402
from edgelab.bridge.indicators import BAR_DRIVEN, REGISTRY  # noqa: E402

HOLDOUT_START = "2026-07-01T00:00:00Z"
HOLDOUT_START_NS = coordinate_store.HOLDOUT_START_NS
AUTHORIZED_PARITY = {"parity_exact", "parity_covered"}


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _iso_ns(text: str) -> int:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1e9)


def _sha256_file(path: str, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _bar_series(ticks, spec: str):
    kind, sep, raw = spec.partition(":")
    if not sep or kind not in {"time", "tick"} or not raw.isdigit():
        raise ValueError(f"bar_spec inválido: {spec!r}")
    value = int(raw)
    if value < 1:
        raise ValueError("bar_spec debe ser >= 1")
    if kind == "time":
        return bars_mod.build_time_bars(ticks, minutes=value)
    return bars_mod.build_tick_bars(ticks, ticks_per_bar=value)


def _assert_clean_worktree() -> None:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=no"],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("no se pudo verificar git status") from exc
    if out:
        raise RuntimeError("worktree con cambios trackeados; campaña abortada")


def validate_inputs(campaign: dict, parity_catalog: dict,
                    config_catalog: dict) -> list[dict]:
    if campaign.get("target_free") is not True:
        raise ValueError("campaign.target_free debe ser true")
    if parity_catalog.get("target_free") is not True:
        raise ValueError("parity catalog no es target-free")
    if config_catalog.get("target_free") is not True:
        raise ValueError("config catalog no es target-free")
    if campaign.get("holdout_start") != "2026-07-01":
        raise ValueError("holdout_start debe ser 2026-07-01")

    parity_by_ref = {row["parity_ref"]: row for row in parity_catalog["entries"]}
    enabled = []
    labels = set()
    for cfg in config_catalog["entries"]:
        if not cfg.get("enabled", False):
            continue
        label = cfg["config_label"]
        if label in labels:
            raise ValueError(f"config_label duplicado: {label}")
        labels.add(label)
        indicator = cfg["indicator"]
        if indicator not in REGISTRY:
            raise ValueError(f"indicador no registrado: {indicator}")
        parity = parity_by_ref.get(cfg["parity_ref"])
        if parity is None:
            raise ValueError(f"parity_ref inexistente: {cfg['parity_ref']}")
        if parity["state"] not in AUTHORIZED_PARITY:
            raise ValueError(
                f"{label}: paridad no autorizada ({parity['state']})"
            )
        errors = identity.validate_params(indicator, cfg.get("params", {}))
        if errors:
            raise ValueError(f"{label}: parámetros inválidos: {'; '.join(errors)}")
        _bar_series(ticks_mod.make_synthetic(n_sessions=1, ticks_per_session=10),
                    cfg["bar_spec"])
        enabled.append({**cfg, "parity": parity})

    if not campaign.get("datasets"):
        raise ValueError("campaign sin datasets")
    for dataset in campaign["datasets"]:
        start_ns = _iso_ns(dataset["start_utc"])
        end_ns = _iso_ns(dataset["end_utc"])
        if start_ns >= end_ns:
            raise ValueError("ventana de dataset vacía o invertida")
        if end_ns > HOLDOUT_START_NS:
            raise ValueError("HOLDOUT_DATA_DETECTED en campaign")
        if not dataset.get("chart_tz"):
            raise ValueError("chart_tz obligatorio")
    return enabled


def _load_ticks(dataset: dict):
    if dataset.get("synthetic"):
        return ticks_mod.make_synthetic(
            start_utc=dataset["start_utc"].replace("Z", ""),
            n_sessions=int(dataset.get("n_sessions", 2)),
            ticks_per_session=int(dataset.get("ticks_per_session", 6000)),
            seed=int(dataset.get("seed", 7)),
        ), None
    path = dataset["path"]
    actual_sha = _sha256_file(path)
    expected_sha = dataset.get("source_sha256")
    if expected_sha and actual_sha != expected_sha:
        raise ValueError(f"source_sha256 no coincide: {path}")
    ticks = ticks_mod.load_canonical_parquet(
        path,
        contract=dataset.get("contract"),
        instrument=dataset.get("instrument"),
        start_utc_ns=_iso_ns(dataset["start_utc"]),
        end_utc_ns=_iso_ns(dataset["end_utc"]),
    )
    return ticks, actual_sha


def execute(campaign: dict, parity_catalog: dict, config_catalog: dict,
            output_root: str, *, validate_only: bool = False,
            require_clean: bool = True) -> dict:
    enabled = validate_inputs(campaign, parity_catalog, config_catalog)
    if validate_only:
        return {"status": "READY", "enabled_configs": len(enabled)}
    if require_clean:
        _assert_clean_worktree()

    generated = datetime.now(timezone.utc).isoformat()
    output = Path(output_root)
    store_root = output / "store"
    coordinates_root = output / "coordinate_store"
    completed = []

    for dataset in campaign["datasets"]:
        ticks, source_sha = _load_ticks(dataset)
        if len(ticks) and int(ticks.ts_ns[-1]) >= HOLDOUT_START_NS:
            raise ValueError("HOLDOUT_DATA_DETECTED en parquet")
        ds_id = identity.dataset_id(
            ticks, tz_interpretation="canonical_utc_verified",
            source_sha256=source_sha,
        )
        bars_cache = {}
        fps_cache = {}
        selected = set(dataset.get("config_labels", []))
        for cfg in enabled:
            if selected and cfg["config_label"] not in selected:
                continue
            instruments = set(cfg.get("instruments", []))
            if instruments and ticks.instrument not in instruments:
                continue
            indicator = cfg["indicator"]
            bar_spec = cfg["bar_spec"]
            if bar_spec not in bars_cache:
                bars_cache[bar_spec] = _bar_series(ticks, bar_spec)
            bars = bars_cache[bar_spec]
            footprints = None
            if indicator in BAR_DRIVEN:
                if bar_spec not in fps_cache:
                    fps_cache[bar_spec] = bars_mod.build_footprints(ticks, bars)
                    gate = bars_mod.p1a_gate(ticks, bars, fps_cache[bar_spec])
                    if gate["status"] != "PASS":
                        raise ValueError(
                            f"P1A FAIL {ticks.contract} {bar_spec}: {gate['diagnostics']}"
                        )
                footprints = fps_cache[bar_spec]
            module = REGISTRY[indicator]
            result = (
                module.run(
                    ticks, bars, footprints, params=cfg.get("params", {}),
                    chart_tz=dataset["chart_tz"],
                )
                if indicator in BAR_DRIVEN else
                module.run(
                    ticks, bars, params=cfg.get("params", {}),
                    chart_tz=dataset["chart_tz"],
                )
            )
            bar_key = f"{bars.kind}_{bars.param}"
            kernel_id = identity.kernel_id(indicator)
            config_id = identity.config_id(
                indicator, result["params"], bar_key, dataset["chart_tz"], kernel_id
            )
            run_id = identity.run_id(
                ds_id, config_id, dataset["start_utc"], dataset["end_utc"]
            )
            parity_state = cfg["parity"]["state"]
            parity_gate = "PASS" if parity_state == "parity_exact" else "WARN"
            run_manifest = store.publish_run(
                store_root,
                kernel_result=result,
                indicator=indicator,
                tick_size=ticks.tick_size,
                instrument=ticks.instrument,
                contract=ticks.contract,
                bar_key=bar_key,
                dataset_id=ds_id,
                kernel_id=kernel_id,
                config_id=config_id,
                run_id=run_id,
                params=result["params"],
                source={
                    "kind": "synthetic" if dataset.get("synthetic") else "parquet_f2",
                    "path": dataset.get("path"),
                    "sha256": source_sha,
                    "range_start_utc": dataset["start_utc"],
                    "range_end_utc": dataset["end_utc"],
                },
                chart_tz=dataset["chart_tz"],
                parity={
                    "gate": parity_gate,
                    "state": parity_state,
                    "parity_ref": cfg["parity_ref"],
                },
                generated_utc=generated,
                param_set_id=cfg["config_label"],
            )
            if parity_state == "parity_covered" and run_manifest["parity_state"] != parity_state:
                run_manifest = store.set_state(
                    store_root, run_id, parity_state="parity_covered"
                )
            rows = coordinate_store.build_coordinate_rows(
                kernel_result=result,
                run_id=run_id,
                dataset_id=ds_id,
                kernel_id=kernel_id,
                config_id=config_id,
                indicator=indicator,
                instrument=ticks.instrument,
                contract=ticks.contract,
                bar_key=bar_key,
                tick_size=ticks.tick_size,
            )
            coordinate_manifest = coordinate_store.publish_coordinates(
                coordinates_root,
                rows=rows,
                run_manifest=run_manifest,
                parity_state=parity_state,
            )
            completed.append({
                "config_label": cfg["config_label"],
                "run_id": run_id,
                "dataset_id": ds_id,
                "kernel_id": kernel_id,
                "config_id": config_id,
                "indicator": indicator,
                "instrument": ticks.instrument,
                "contract": ticks.contract,
                "n_zones": run_manifest["counts"]["n_zones"],
                "n_coordinates": coordinate_manifest["coordinate_count"],
                "coordinate_sha256": coordinate_manifest["coordinate_sha256"],
            })

    manifest = {
        "schema_version": "indicator_coordinate_campaign_v1",
        "status": "COMPLETE",
        "generated_utc": generated,
        "holdout_start": "2026-07-01",
        "runs": completed,
        "firewall": {
            "CAMPAIGN_OUTCOMES_OPENED": False,
            "PNL_ACCESSED": False,
            "HOLDOUT_TOUCHED": False,
            "WINNER_SELECTED": False,
            "EDGE_DECLARED": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    with open(output / "campaign_manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True)
    parser.add_argument(
        "--parity-catalog", default="specs/indicator_parity_catalog_v1.json"
    )
    parser.add_argument(
        "--config-catalog", default="specs/indicator_config_catalog_v1.json"
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)
    result = execute(
        _load_json(args.campaign),
        _load_json(args.parity_catalog),
        _load_json(args.config_catalog),
        args.out,
        validate_only=args.validate_only,
        require_clean=not args.allow_dirty,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
