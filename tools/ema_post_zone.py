#!/usr/bin/env python3
r"""EMAZ-D3 — volumen tras el fin de la zona CON la corrección del sesgo: referencia en la barra de ruptura (conocida en tiempo real) y control emparejado por el contramovimiento previo.
Reutiliza las zonas ya calculadas (zones_table_PRIVADA.csv de EMAZ-D2, dataset privado) en vez de volver a simularlas, y procesa los contratos en paralelo.
Config en env EMAZ_CFG: {"inst","desde","hasta","bar_ticks","zones_dir","workers"}."""
from __future__ import annotations
import dataclasses, gc, json, os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

KAGGLE = Path("/kaggle/input").exists()
if KAGGLE:
    _roots = [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")]
    os.environ["EDGELAB_DATA_ROOTS"] = os.pathsep.join(str(r) for r in _roots)
    sys.path.insert(0, str(next(p.parent for r in _roots for p in r.glob("edgelab-data-catalog/**/edgelab_data.py"))))
    sys.path.insert(0, str(next(p.parent.parent for r in _roots for p in r.glob("edgelab-code-zones/**/edgelab/__init__.py"))))
    OUT = Path("/kaggle/working")
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs/data_catalog")); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    OUT = Path(os.environ.get("EMAZ_OUT", "/tmp/emaz_out"))
OUT.mkdir(parents=True, exist_ok=True); os.environ.setdefault("EDGELAB_ALLOW_MISSING", "1")
from edgelab.bridge import bars as B, ticks as T      # noqa: E402
from edgelab.research import ema_zones as Z            # noqa: E402
from edgelab.research import ema_zone_desc as ZD       # noqa: E402

CFG = json.loads(os.environ.get("EMAZ_CFG", "{}")); INST = CFG.get("inst", "NQ"); DESDE, HASTA = CFG.get("desde", "2025-07-01"), CFG.get("hasta", "2026-09-30"); SPEC = int(CFG.get("bar_ticks", 25)); CT = "America/Chicago"
END_NS = pd.Timestamp("2026-09-30 22:00", tz="UTC").value


def session_date_of(end_ns):
    um, inv = np.unique(np.asarray(end_ns) // 60_000_000_000, return_inverse=True)
    c = pd.to_datetime(um * 60_000_000_000, utc=True).tz_convert(CT) + pd.Timedelta(hours=7)
    return np.asarray(c.strftime("%Y-%m-%d"))[inv]


def ct_minute_of_day(ts):
    c = pd.to_datetime(np.asarray(ts), utc=True).tz_convert(CT); return (c.hour * 60 + c.minute).to_numpy()


def contract_rows(c, sess):
    rows = sess[sess.contract == c]; ds, fl = rows.groupby(["dataset", "file"]).size().idxmax()
    first = pd.Timestamp(rows.date.min()).tz_localize(CT) - pd.Timedelta(days=3); last = pd.Timestamp(rows.date.max()).tz_localize(CT) + pd.Timedelta(hours=16)
    return ds, fl, int(first.value), int(min(last.value, END_NS))


def load_min(path, a, b):
    """Carga solo ts, precio y volumen (el resto del esquema no se usa aquí): ~3× menos memoria que load_canonical_parquet."""
    import pyarrow.parquet as pq
    t = pq.read_table(path, columns=["ts_utc_ns", "price_ticks", "volume"], filters=[("ts_utc_ns", ">=", int(a)), ("ts_utc_ns", "<", int(b))])
    ts = t.column("ts_utc_ns").to_numpy().astype(np.int64); px = t.column("price_ticks").to_numpy().astype(np.int64); vol = t.column("volume").to_numpy().astype(np.float64); del t
    return T.TickSeries(ts_ns=ts, price_ticks=px, volume=vol, bid_ticks=None, ask_ticks=None, sequence=np.arange(len(ts), dtype=np.int64), tick_size=0.25, instrument=INST, contract="?", source=str(path))


def process_contract(args):
    c, path, a, b, zones = args
    try:
        tk = load_min(path, a, b); mod = ct_minute_of_day(tk.ts_ns); keep = np.asarray(~((mod >= 960) & (mod < 1020)))
        tk = dataclasses.replace(tk, **{f: (getattr(tk, f)[keep] if getattr(tk, f) is not None else None) for f in ("ts_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")})
        bars = B.build_tick_bars(tk, SPEC); cc, hh, ll = (np.asarray(x, float) for x in (bars.close_t, bars.high_t, bars.low_t)); n = len(cc); sd = session_date_of(bars.end_ns)
        atr = Z.precompute(cc, hh, ll, ema_n=200, atr_n=100)["atr"]; bar_start = np.searchsorted(np.asarray(bars.tick_bar_idx), np.arange(n + 1))
        rows = ZD.post_break_rows(zones, cc, hh, ll, atr, sd, bar_start, np.asarray(tk.price_ticks, np.int64), np.asarray(tk.volume, float), seed=20261021 + len(c))
        for r in rows: r["contract"] = c
        return c, rows, None
    except Exception:
        import traceback; return c, [], traceback.format_exc()[-2000:]


def main():
    import edgelab_data as ed, concurrent.futures as cf, multiprocessing as mp
    t0 = time.time(); ed.check_inputs((INST, DESDE, HASTA)); sess = ed.sessions(INST, DESDE, HASTA)
    csv = next(p for r in ([Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")] if KAGGLE else [Path(CFG.get("zones_dir", "."))]) for p in r.rglob("zones_table*.csv")); Zdf = pd.read_csv(csv); print("zonas en la tabla", len(Zdf), flush=True)
    jobs = []
    for c in sorted(sess.contract.unique(), key=lambda x: (x[-2:], x[-5:-3])):
        ds, fl, a, b = contract_rows(c, sess); zs = Zdf[Zdf.contract == c].to_dict("records")
        if zs: jobs.append((c, str(ed._path(ds, fl)), a, b, zs))
    rows, errors = [], []; W = int(CFG.get("workers", 2))
    with cf.ProcessPoolExecutor(max_workers=W, mp_context=mp.get_context("fork")) as ex:
        for c, rr, err in ex.map(process_contract, jobs):
            print(c, "zonas", len(rr), "error" if err else "ok", flush=True); rows += rr
            if err: errors.append(dict(contract=c, tb=err))
    if not rows: (OUT / "ERROR.json").write_text(json.dumps(dict(errors=errors), indent=1)); return
    sub = lambda rs: ZD.summarize_post(rs) if len(rs) >= 30 else None
    res = dict(campaign="EMAZ-D3", note="descriptivo; referencia en la barra de ruptura; control emparejado por contramovimiento previo", n_zonas=len(rows), n_con_control=int(sum(1 for r in rows if r["match_dist_atr"] is not None)),
               todas=sub(rows), solo_ruptura=sub([r for r in rows if r["end_reason"] == "ruptura"]), solo_alejamiento=sub([r for r in rows if r["end_reason"] == "alejamiento"]), errors=errors, seconds=round(time.time() - t0))
    (OUT / "STUDY_RESULTS.json").write_text(json.dumps(res, indent=1, default=float)); print("listo", res["seconds"], "s")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback; (OUT / "ERROR.json").write_text(json.dumps(dict(traceback=traceback.format_exc()[-3000:]), indent=1)); print("ERROR", flush=True); raise
