#!/usr/bin/env python3
"""Genera docs/data_catalog/RESOLVER.json: UNA respuesta por (instrumento, sesión) — qué dataset/archivo/contrato leer y
si la sesión está aprobada para análisis (con el motivo si no). Sale de sessions.json + las mismas reglas de
tools/data_curate.py (no inventa reglas nuevas). Lo consume edgelab_data.py, que es lo único que un agente debe usar.
  python tools/data_resolver.py"""
import argparse
import datetime as dt
import glob
import json
import re
from datetime import datetime, timezone
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "docs/data_catalog"
HOLDOUT_FIRST = "2026-10-01"
SPOT_NOTE = ("Spot/CFD Dukascopy (dataset edgelab-dukascopy-*): complemento de POTENCIA para pruebas de información "
             "(dirección, forma) cuando los futuros no alcanzan. Limitaciones: bid/ask de spot/CFD, no libro CME; "
             "volumen = liquidez cotizada, no trades; spread y costos distintos (oro: ~5,8 ticks GC vs 3 en COMEX); "
             "horario distinto. NO sirve para costos ni ejecución del futuro: el neto se confirma siempre en futuros.")

DELETED_DATASETS = {"mnq-parquet", "mnq-tick-data"}     # borrados por el usuario (estaban públicos, 2026-10-05): sus sesiones quedan NO aprobadas con motivo explícito

SPOT_DATASETS = {  # spot/CFD hermano de cada futuro (no reemplaza al futuro)
    "GC": "edgelab-dukascopy-xauusd-ticks-m1", "MGC": "edgelab-dukascopy-xauusd-ticks-m1",
    "ES": "edgelab-dukascopy-es-usa500", "MES": "edgelab-dukascopy-es-usa500",
    "NQ": "edgelab-dukascopy-nq-usatech", "MNQ": "edgelab-dukascopy-nq-usatech",
    "YM": "edgelab-dukascopy-ym-usa30", "MYM": "edgelab-dukascopy-ym-usa30",
    "6E": "edgelab-dukascopy-6e-eurusd", "6B": "edgelab-dukascopy-6b-gbpusd", "6J": "edgelab-dukascopy-6j-usdjpy"}
# Intervalos con libro cruzado (bid > ask, volumen 0) en el feed de Dukascopy: falla del proveedor, no se corrige; excluir.
SPOT_EXCLUSIONS = [
    {"datasets": ["edgelab-dukascopy-6e-eurusd", "edgelab-dukascopy-6j-usdjpy"], "from_utc": "2024-10-09T23:00:00Z",
     "to_utc": "2024-10-10T01:00:00Z", "reason": "libro cruzado (bid>ask) EUR/USD 1.620 y USD/JPY 2.576 ticks, volumen 0"}]


ALT_PRIORITY = ("edgelab-ticks-nt8-reexport-20261005", "edgelab-ticks-nt8-canonical", "edgelab-nt8-historical-missing-20261001", "edgelab-ticks-es-nq-2026q3-ext",
                "edgelab-nq-nt8-2026q3-l2ctx", "edgelab-mgc-nt8-raw-parquet-20261002")      # lo que no está acá (los *-preholdout y mnq-parquet) va al final
_CT = re.compile(r"(?P<sym>[A-Z0-9]+)[ _-](?P<mm>\d{2})-(?P<yy>\d{2})")


def _alt_rank(ds):
    return ALT_PRIORITY.index(ds) if ds in ALT_PRIORITY else (len(ALT_PRIORITY) if ds.endswith("-preholdout") else len(ALT_PRIORITY) + 1)


def load_daymaps(scan_dirs):
    """(dataset, archivo) -> {fecha: (trades, volumen, minutos)} y contrato, desde los escaneos por archivo (scan__*.json o scan/<ds>/*.json)."""
    out = {}
    for d in scan_dirs:
        for f in glob.glob(str(Path(d) / "**" / "*.json"), recursive=True):
            if "scan" not in Path(f).name and "scan" not in Path(f).parent.name:
                continue
            try:
                x = json.loads(Path(f).read_text(encoding="utf-8"))
            except Exception:
                continue
            if not x.get("recognized") or not x.get("days") or x.get("trades", 0) < 1000:
                continue
            m = _CT.search(Path(x["file"]).name)
            if not m:
                continue
            out[(x["dataset"], x["file"])] = {"contract": f"{m['sym']}_{m['mm']}-{m['yy']}",
                                              "days": {dt.date.fromordinal(r["td"]).isoformat(): (r["trades"], r["volume"], r["minutes"]) for r in x["days"]}}
    return out


def add_alternatives(instruments, daymaps):
    """A cada sesión le agrega, si existen, fuentes alternativas del MISMO contrato y fecha, en orden de prioridad; `consistent` = trades dentro de 1 % y minutos dentro de 2 del primario."""
    by_contract = {}
    for (ds, fl), v in daymaps.items():
        by_contract.setdefault(v["contract"], []).append((ds, fl, v["days"]))
    n_alt = 0
    for sym, v in instruments.items():
        for r in v["sessions"]:
            alts = []
            for ds, fl, days in sorted(by_contract.get(r["contract"], []), key=lambda t: _alt_rank(t[0])):
                if (ds, fl) == (r["dataset"], r["file"]) or r["date"] not in days or ds in DELETED_DATASETS:
                    continue
                tr, vol, mi = days[r["date"]]
                ok = abs(tr - r["trades"]) <= 0.01 * max(tr, r["trades"], 1) and abs(mi - r["minutes"]) <= 2
                alts.append({"dataset": ds, "file": fl, "consistent": bool(ok)})
            if alts:
                r["alts"] = alts
                n_alt += 1
    return n_alt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alt-scans", action="append", default=[], help="carpetas con escaneos por archivo (puede repetirse)")
    ap.add_argument("--kaggle-files", default=None, help="JSON {dataset: [archivos]} con lo que HOY existe en Kaggle (para RESOLVER_STATUS.md)")
    a = ap.parse_args()
    sess = json.loads((D / "sessions.json").read_text(encoding="utf-8"))
    cur = json.loads((D / "curated.json").read_text(encoding="utf-8"))
    out = {"schema": "EDGELAB_RESOLVER_V1", "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "holdout_first_trade_date": HOLDOUT_FIRST, "rules": cur.get("rules"),
           "how_to_use": "import edgelab_data as ed; ed.load_ticks('MNQ','2026-01-01','2026-09-30')  # sólo sesiones aprobadas",
           "spot_complement": SPOT_NOTE, "spot_datasets": SPOT_DATASETS, "spot_exclusions": SPOT_EXCLUSIONS,
           "instruments": {}}
    for sym, rows in sess.items():
        conflict = set(cur["instruments"][sym]["caveat_sessions_source_conflict"]["contracts"])
        lst = []
        for r in rows:
            if r["post_holdout"] or r["date"] >= HOLDOUT_FIRST:
                continue                                   # el holdout ni siquiera se lista
            why = ("liquidez_baja" if r["below_25pct_instrument_median"] else
                   "sesion_truncada" if r["thin_minutes"] else None)
            if r["dataset"] in DELETED_DATASETS:
                why = "fuente_borrada(" + r["dataset"] + ")"
            lst.append({"date": r["date"], "contract": r["contract"], "dataset": r["dataset"], "file": r["file"],
                        "approved": why is None, "reason": why, "caveat": "fuente_en_conflicto" if r["contract"] in conflict else None,
                        "trades": r["trades"], "volume": r["volume"], "minutes": r["minutes"]})
        v = cur["instruments"][sym]
        out["instruments"][sym] = {"verdict": v["verdict"], "tick_size": v["tick_size"], "tick_value_usd": v["tick_value_usd"],
                                   "approved_sessions": sum(x["approved"] for x in lst), "sessions": lst}
    if a.alt_scans:
        print("sesiones con fuentes alternativas:", add_alternatives(out["instruments"], load_daymaps(a.alt_scans)))
    (D / "RESOLVER.json").write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding="utf-8")
    write_map(out)
    if a.kaggle_files:
        write_status(out, json.loads(Path(a.kaggle_files).read_text(encoding="utf-8")))
    print({k: (v["approved_sessions"], len(v["sessions"])) for k, v in out["instruments"].items()})


def write_map(out):
    """DATASETS_POR_INSTRUMENTO.md: qué datasets adjuntar a un kernel para cada instrumento (los que el resolver usa como primarios) y cuáles no hacen falta."""
    used, rows = {}, []
    for sym, v in sorted(out["instruments"].items()):
        c = {}
        for r in v["sessions"]:
            if r["approved"]:
                c[r["dataset"]] = c.get(r["dataset"], 0) + 1
                used[r["dataset"]] = used.get(r["dataset"], 0) + 1
        rows.append((sym, v["verdict"], v["approved_sessions"], sorted(c.items(), key=lambda t: -t[1]), out["spot_datasets"].get(sym)))
    L = ["# Qué datasets adjuntar, por instrumento (generado por `tools/data_resolver.py`)", "",
         "Solo el resolver decide la fuente de cada sesión (`edgelab_data.py`). Para un kernel, adjuntá los datasets de la fila del instrumento; `python docs/data_catalog/edgelab_data.py INST DESDE HASTA` da la lista exacta para un rango. Además siempre: `edgelab-data-catalog` (código y resolver).", "",
         "| Instrumento | Veredicto | Sesiones aprobadas | Datasets primarios (sesiones) | Spot/CFD hermano (solo potencia) |", "|---|---|---:|---|---|"]
    L += [f"| {s} | {vd} | {n} | " + "; ".join(f"`{d}` ({k})" for d, k in c) + f" | {sp or '-'} |" for s, vd, n, c, sp in rows]
    (D / "DATASETS_POR_INSTRUMENTO.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def write_status(out, kaggle):
    """RESOLVER_STATUS.md: qué sesiones aprobadas dependen de archivos que HOY no existen en Kaggle, y si hay alternativa consistente."""
    have = {ds: set(fs) for ds, fs in kaggle.items()}
    miss = {}            # dataset -> archivo -> [n_sesiones, n_con_alternativa_consistente_existente]
    for sym, v in out["instruments"].items():
        for r in v["sessions"]:
            if not r["approved"] or r["file"] in have.get(r["dataset"], set()):
                continue
            m = miss.setdefault(r["dataset"], {}).setdefault((sym, r["file"]), [0, 0])
            m[0] += 1
            if any(x["consistent"] and x["file"] in have.get(x["dataset"], set()) for x in r.get("alts", [])):
                m[1] += 1
    L = ["# Estado del resolver frente a Kaggle (generado por `tools/data_resolver.py`)", "",
         "Sesiones aprobadas cuyo archivo primario **no existe hoy en Kaggle**. «Con alternativa» = hay otra fuente del mismo contrato y fecha, consistente (trades a 1 %), que sí existe: `edgelab_data` la usa sola y avisa.", ""]
    if not miss:
        L.append("Todo lo que el resolver referencia existe en Kaggle.")
    for ds, d in sorted(miss.items()):
        tot = sum(x[0] for x in d.values()); alt = sum(x[1] for x in d.values())
        L += [f"## `{ds}`" + ("  — **dataset sin los archivos (re-subir)**" if not have.get(ds) or len(have[ds]) <= 1 else ""), "", f"{tot} sesiones aprobadas dependen de {len(d)} archivos que faltan; {alt} tienen alternativa existente y **{tot - alt} no tienen ninguna (esas fallan hasta que se suba el archivo)**.", "",
              "| Instrumento | Archivo que falta | Sesiones | Con alternativa | Sin alternativa |", "|---|---|---:|---:|---:|"]
        L += [f"| {s} | `{f}` | {x[0]} | {x[1]} | {x[0] - x[1]} |" for (s, f), x in sorted(d.items())]
        L.append("")
    (D / "RESOLVER_STATUS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("estado escrito:", {ds: sum(x[0] for x in d.values()) for ds, d in miss.items()})


if __name__ == "__main__":
    main()
