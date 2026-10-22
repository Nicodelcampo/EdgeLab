"""Censo por (contrato, fecha de trading, grupo de fuente) a partir de la evidencia del escaneo por hora.

Qué hace, en orden:
  1. Carga los bins por hora de todas las fuentes (texto A/A2/B y parquets derivados P) y su inventario.
  2. Asigna a cada grupo su offset horario VERIFICADO (sólo si el veredicto lo permite) y calcula fecha de trading.
  3. Detecta bloques copiados con corrimiento horario dentro de cada grupo y los excluye de la medición (se conservan en
     la tabla de adjudicación; nada se borra de los originales).
  4. Agrega por sesión sólo horario regular: ticks, volumen, minutos activos, hueco máximo y spread p99.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.data.liquid_release.calendar_tz import in_break, raw_hour_index, trade_date
from edgelab.data.liquid_release.dedupe import adjudicate, find_shifted_duplicates, refine_ambiguous

HOLDOUT_FIRST_TRADE_DATE = 20261001
OK_VERDICTS = ("UTC_VERIFIED", "INSUFFICIENT_EVIDENCE", "UTC_WITH_ANOMALIES")
SUM_COLS = ["n", "vol", "n_vol_le0", "off_last", "off_bid", "off_ask", "noquote", "crossed", "locked", "last_gt_ask",
            "last_lt_bid", "n_min"]


def load_scan(*scan_dirs) -> tuple[pd.DataFrame, pd.DataFrame]:
    """-> (inventario de fuentes, bins por hora). Cada scan_dir tiene parts/*.json y parts/*.parquet."""
    inv, bins = [], []
    for d in scan_dirs:
        for f in glob.glob(str(Path(d) / "parts" / "*.json")):
            if f.endswith(".error.json"):
                continue
            inv.append(json.load(open(f, encoding="utf-8")))
        for f in glob.glob(str(Path(d) / "parts" / "*.parquet")):
            bins.append(pd.read_parquet(f))
    inv = pd.DataFrame(inv)
    inv["group"] = inv["kind"] + "|" + inv["root"].str.split("\\").str[-1] + "|" + inv["contract"]
    bins = pd.concat(bins, ignore_index=True)
    bins = bins[bins["n"] > 0].copy()
    bins["group"] = bins["source_id"].map(inv.set_index("id")["group"])
    bins["contract"] = bins["source_id"].map(inv.set_index("id")["contract"])
    bins["instrument"] = bins["source_id"].map(inv.set_index("id")["instrument"])
    bins["kind"] = bins["source_id"].map(inv.set_index("id")["kind"])
    return inv, bins


def merge_group_bins(bins: pd.DataFrame) -> pd.DataFrame:
    """Une los bins de un grupo (varios archivos por día pueden compartir una hora cruda en los bordes)."""
    sums = [c for c in SUM_COLS + ["fp_ts", "fp_px", "fp_bid", "fp_ask"] if c in bins.columns]
    agg = {c: "sum" for c in sums}
    agg.update(first_ts="min", last_ts="max", max_gap_ns="max")
    out = bins.groupby(["group", "contract", "instrument", "kind", "raw_date", "raw_hour"], as_index=False).agg(agg)
    hist = np.array(bins["spread_hist"].tolist(), dtype=np.int64)
    key = bins.groupby(["group", "raw_date", "raw_hour"], sort=True).ngroup().to_numpy()
    H = np.zeros((key.max() + 1, hist.shape[1]), dtype=np.int64)
    np.add.at(H, key, hist)
    order = bins.groupby(["group", "raw_date", "raw_hour"], sort=True).size().index.to_frame(index=False)
    hdf = order.assign(spread_hist=list(H))
    return out.merge(hdf, on=["group", "raw_date", "raw_hour"], how="left")


def annotate(bins: pd.DataFrame, tz: pd.DataFrame):
    """Agrega offset, fecha de trading, in_break y marca de duplicado. Una fila por (grupo, fecha cruda, hora cruda).
    Devuelve (bins anotados, tabla de duplicados adjudicados)."""
    verdict = tz.set_index("group")["verdict"].to_dict()
    offset = tz.set_index("group")["best_offset_h"].to_dict()
    pieces, dup_tables = [], []
    for grp, b in bins.groupby("group"):
        o = int(offset[grp]) if verdict.get(grp) in OK_VERDICTS else 0
        naive = raw_hour_index(b["raw_date"].to_numpy(), b["raw_hour"].to_numpy())
        b = b.assign(utc_offset_h=o, trade_date=trade_date(naive, o), in_break=in_break(naive, o),
                     tz_verdict=verdict.get(grp, "UNKNOWN"))
        d = find_shifted_duplicates(b) if "fp_ts" in b.columns else pd.DataFrame()
        drop = set()
        if len(d):
            adj = adjudicate(d, {(r.raw_date, r.raw_hour): bool(r.in_break) for r in b.itertuples()})
            inst = b["instrument"].iloc[0]
            peers = bins[(bins["instrument"] == inst) & (bins["group"] != grp)]
            peer_n = peers.groupby(["raw_date", "raw_hour"])["n"].sum().to_dict()
            adj = refine_ambiguous(adj, peer_n)
            adj.insert(0, "group", grp)
            dup_tables.append(adj)
            drop = {(r.drop_date, r.drop_hour) for r in adj.itertuples() if r.verdict != "AMBIGUOUS"}
        b = b.assign(dup_copy=[(r, h) in drop for r, h in zip(b["raw_date"], b["raw_hour"])])
        pieces.append(b)
    dups = pd.concat(dup_tables, ignore_index=True) if dup_tables else pd.DataFrame()
    return pd.concat(pieces, ignore_index=True), dups


def _p(hist_row: np.ndarray, q: float) -> float:
    tot = hist_row.sum()
    return float("nan") if tot == 0 else float(np.searchsorted(np.cumsum(hist_row), q * tot, side="left"))


def session_census(ann: pd.DataFrame) -> pd.DataFrame:
    """Una fila por (grupo, contrato, trade_date). Sólo horario regular y sin bloques copiados. Los ticks en pausa/fin de
    semana y los bloques copiados se cuentan aparte (n_break, n_dup_copy) para que sean visibles."""
    a = ann.copy()
    use = (~a["in_break"]) & (~a["dup_copy"])
    for c in SUM_COLS + [x for x in ("fp_ts", "fp_px", "fp_bid", "fp_ask") if x in a.columns]:
        a[c + "_reg"] = np.where(use, a[c], 0)
    FPS = [x for x in ("fp_ts", "fp_px", "fp_bid", "fp_ask") if x in a.columns]
    a["n_break"] = np.where(a["in_break"], a["n"], 0)
    a["n_dup_copy"] = np.where(a["dup_copy"] & ~a["in_break"], a["n"], 0)
    a["gap_reg"] = np.where(use, a["max_gap_ns"], 0)
    keys = ["group", "contract", "instrument", "kind", "trade_date", "utc_offset_h", "tz_verdict"]
    g = a.groupby(keys, as_index=False).agg(
        **{c + "_reg": (c + "_reg", "sum") for c in SUM_COLS + FPS}, n_break=("n_break", "sum"), n_dup_copy=("n_dup_copy", "sum"),
        n_all=("n", "sum"), max_gap_reg_ns=("gap_reg", "max"), first_ts=("first_ts", "min"), last_ts=("last_ts", "max"))
    H = np.array(a["spread_hist"].tolist(), dtype=np.int64)
    kid = a.groupby(keys, sort=True).ngroup().to_numpy()
    Hr = np.zeros((kid.max() + 1, H.shape[1]), dtype=np.int64)
    np.add.at(Hr, kid[use.to_numpy()], H[use.to_numpy()])
    order = a.groupby(keys, sort=True).size().index.to_frame(index=False)
    sp = order.assign(spread_p50=[_p(h, 0.5) for h in Hr], spread_p99=[_p(h, 0.99) for h in Hr], spread_n=Hr.sum(1))
    return g.merge(sp, on=keys, how="left")


KIND_PRIORITY = {"B": 3, "A2": 2, "A": 2, "P": 1}
BAD_TZ = ("NOT_VERIFIED",)


def adjudicate_sources(cen: pd.DataFrame):
    """Una fuente por (contrato, fecha de trading). Regla FIJA, sin mirar resultados:
       1) se descartan grupos con huso NOT_VERIFIED;
       2) gana el de más minutos activos en horario regular; 3) luego el de menor hueco máximo; 4) luego prioridad B > A2 = A > P.
    Devuelve (elegidos, conflictos). `identical` = todas las fuentes candidatas tienen huellas idénticas en la sesión."""
    c = cen[(cen["n_reg"] > 0) & (~cen["tz_verdict"].isin(BAD_TZ))].copy()
    c["prio"] = c["kind"].map(KIND_PRIORITY).fillna(0)
    c = c.sort_values(["contract", "trade_date", "n_min_reg", "max_gap_reg_ns", "prio"], ascending=[True, True, False, True, False])
    fpc = [x for x in ("n_reg", "vol_reg", "fp_ts_reg", "fp_px_reg", "fp_bid_reg", "fp_ask_reg") if x in c.columns]
    g = c.groupby(["contract", "trade_date"], sort=False)
    chosen = g.head(1).copy()
    cnt = g.size().rename("n_candidates").reset_index()
    ident = g[fpc].apply(lambda d: len(d.drop_duplicates()) == 1).rename("identical").reset_index()
    chosen = chosen.merge(cnt, on=["contract", "trade_date"]).merge(ident, on=["contract", "trade_date"])
    chosen["assurance"] = np.where(chosen["kind"] == "P", "PARQUET_DERIVED_ORIGINAL_NOT_AVAILABLE", "TEXT_ORIGINAL_SHA_VERIFIED")
    multi = c.merge(chosen[["contract", "trade_date", "group"]].rename(columns={"group": "chosen_group"}), on=["contract", "trade_date"])
    multi = multi[multi.groupby(["contract", "trade_date"])["group"].transform("nunique") > 1]
    conflicts = multi.merge(chosen[["contract", "trade_date", "identical"]], on=["contract", "trade_date"])
    return chosen, conflicts[~conflicts["identical"]]
