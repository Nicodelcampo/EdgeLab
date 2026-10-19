"""Exporta sesiones canónicas de descubrimiento (≤ 2026-03-31) para los notebooks de Kaggle. Correr localmente.
Minis (ES, NQ, YM): Lucid (research-v2, contrato canónico por sesión). Micros (MES, MNQ, MYM): NT8 canónico
(catálogos *_nt8_2025_2026q3_sessions_catalog.json, dataset edgelab-ticks-nt8-canonical)."""
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402

OUT = Path(__file__).with_name("sesiones")
OUT.mkdir(exist_ok=True)
END = "20260331"
for inst in ("ES", "NQ", "YM"):
    ss = [s for s in T2.canonical_sessions(inst) if s["trade_date"] <= END]
    out = [dict(trade_date=s["trade_date"], contract=s["contract"], start=int(s["start"]), end=int(s["end"]), file=Path(s["path"]).name) for s in ss]
    (OUT / f"sesiones_{inst}.json").write_text(json.dumps(dict(inst=inst, fuente="lucid", sessions=out)), encoding="utf-8")
    print(inst, "lucid", len(out), collections.Counter(s["contract"] for s in out), {s["file"] for s in out})
for inst in ("MES", "MNQ", "MYM"):
    cat = json.loads((REPO / "docs/research/contract_regimes" / f"{inst}_nt8_2025_2026q3_sessions_catalog.json").read_text(encoding="utf-8"))
    ss = [s for s in cat["sessions"] if s["trade_date"] <= END]
    out = [dict(trade_date=s["trade_date"], contract=s["contract"], start=int(s["start"]), end=int(s["end"]), file=Path(s["path"]).name) for s in ss]
    (OUT / f"sesiones_{inst}.json").write_text(json.dumps(dict(inst=inst, fuente="nt8", sessions=out)), encoding="utf-8")
    print(inst, "nt8", len(out), collections.Counter(s["contract"] for s in out))
