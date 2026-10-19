#!/usr/bin/env python3
r"""Regenera los bundles 25t + HFT de los activos no-NQ con el perfil escalado (SCALED_FUNNEL_V1).

Reemplaza a los generados con `NQ_LITERAL_TRANSFER`. Reconstruye el plan desde los manifiestos existentes (mismas
ventanas de sesion, mismo parquet, mismo sha256) y usa el cierre de la sesion anterior como contexto del primer tick
(`CARRY`). Target-free; el holdout se verifica en el propio constructor.

    .venv\Scripts\python tools\rebuild_hft_bundles_scaled.py --workers 3
"""
from __future__ import annotations
import argparse, json, re, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
import build_multiasset_25t_hft_bundles as B  # noqa: E402
from edgelab.bridge.indicators import hftzones_universal as hu  # noqa: E402

PROFILE = hu.SCALED


def plan_from_manifests(bundles: Path, skip):
    out = []
    for f in sorted(bundles.glob("*.manifest.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        if "sessions" not in m or m["instrument"] in skip or m.get("profile") not in (B.hft.LITERAL, PROFILE):
            continue
        sess = [dict(trade_date=s["trade_date"], start_utc_ns=s["start_utc_ns"], end_utc_ns=s["end_utc_ns"],
                     prev_session_close_ticks=("CARRY" if s.get("first_tick_context") == "EXPLICIT" else None))
                for s in m["sessions"]]
        out.append(dict(asset_id=m["asset_id"], instrument=m["instrument"], contract=m["contract"], parquet=m["source_path"],
                        expected_sha256=m["source_sha256"], sessions=sess, profile=PROFILE, parity_status="PARITY_ABSTAIN",
                        _ticks=sum(s.get("ticks", 0) for s in m["sessions"])))
    return sorted(out, key=lambda e: -e["_ticks"])


def _sha(path):
    return path, B.sha256_file(Path(path))


def _build(args):
    entry, out = args
    entry = {k: v for k, v in entry.items() if k != "_ticks"}
    bundle, manifest = B.build_entry(entry, holdout_ns=B.DEFAULT_HOLDOUT_NS, source_sha256=entry["expected_sha256"])
    aid = manifest["asset_id"]
    B.write_json_atomic(out / f"{aid}.json", bundle)
    B.write_json_atomic(out / f"{aid}.manifest.json", manifest)
    twin = out / f"{aid}.js"
    if twin.exists():
        twin.unlink()                       # el gemelo .js quedaria con zonas del perfil viejo
    return aid, manifest["zones"], manifest["tick25_bars"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundles", type=Path, default=REPO / "viewer/nt8_bridge/bundles")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--skip", action="append", default=["NQ"], help="NQ ya usa su perfil literal (= escalado)")
    ap.add_argument("--only", help="regex sobre asset_id (prueba)")
    a = ap.parse_args()
    entries = plan_from_manifests(a.bundles, set(a.skip))
    if a.only:
        entries = [e for e in entries if re.search(a.only, e["asset_id"])]
    for e in entries:
        B.validate_entry(e, B.DEFAULT_HOLDOUT_NS)
        hu.profile(PROFILE, e["instrument"])            # falla si falta el perfil de ese activo
    paths = sorted({e["parquet"] for e in entries})
    with ProcessPoolExecutor(a.workers) as ex:
        shas = dict(ex.map(_sha, paths))
        for e in entries:
            if shas[e["parquet"]].lower() != e["expected_sha256"].lower():
                raise SystemExit(f"source hash mismatch: {e['parquet']}")
        print(f"hashes OK ({len(paths)} parquets); reconstruyendo {len(entries)} bundles", flush=True)
        done = {}
        for aid, z, n in ex.map(_build, [(e, a.bundles) for e in entries]):
            done[aid] = (z, n)
            print(f"{aid:34s} zonas={z:7d} barras={n:8d}", flush=True)
    # catalogo del visor: cuentas de zonas y perfil
    mf = a.bundles / "manifest.js"
    txt = mf.read_text(encoding="utf-8")
    cat = json.loads(txt[txt.index("["):txt.rindex("]") + 1])
    for it in cat:
        if it["id"] in done:
            it["zones"], it["candles"], it["profile"] = done[it["id"]][0], done[it["id"]][1], PROFILE
    mf.write_text("window.ASSET_CATALOG = " + json.dumps(cat, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(json.dumps({"rebuilt": len(done)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
