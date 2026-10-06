"""edgelab_data — ÚNICA puerta de entrada a los datos de EdgeLab en Kaggle (o local).

Uso (notebook de Kaggle con el dataset `edgelab-data-catalog` y los datasets de ticks agregados como input):
    import sys; sys.path.insert(0, '/kaggle/input/edgelab-data-catalog')
    import edgelab_data as ed
    ed.sessions('MNQ')                                  # tabla de sesiones aprobadas (fecha, contrato, dataset, archivo)
    df = ed.load_ticks('MNQ', '2026-01-01', '2026-09-30')  # sólo sesiones aprobadas, serie líder, sin holdout
    m1 = ed.load_m1('MNQ', '2026-01-01', '2026-09-30')     # barras M1 construidas desde esos mismos ticks

Reglas que este módulo hace cumplir (no las saltees leyendo parquets a mano):
- Una respuesta por sesión: dataset/archivo/contrato salen de RESOLVER.json (serie líder, prioridad de fuente fija).
- Sesiones no aprobadas (liquidez baja, truncadas) se excluyen salvo include_rejected=True, y siempre se informan.
- Holdout: nada con fecha de sesión >= 2026-10-01; pedirlo es un error.
- Spot Dukascopy NO se mezcla con futuros: ver RESOLVER['spot_complement'].
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
RESOLVER = json.loads((HERE / "RESOLVER.json").read_text(encoding="utf-8"))
HOLDOUT = RESOLVER["holdout_first_trade_date"]
ROOTS = [Path(p) for p in os.environ.get("EDGELAB_DATA_ROOTS", "/kaggle/input").split(os.pathsep)]
CT = "America/Chicago"


def _check(start, end):
    if end >= HOLDOUT or start >= HOLDOUT:
        raise ValueError(f"holdout: no se leen sesiones desde {HOLDOUT}")


def sessions(inst: str, start: str = "1900-01-01", end: str = "2026-09-30", include_rejected: bool = False) -> pd.DataFrame:
    _check(start, end)
    s = pd.DataFrame(RESOLVER["instruments"][inst]["sessions"])
    s = s[(s.date >= start) & (s.date <= end)]
    return s if include_rejected else s[s.approved]


def _path(dataset: str, file: str) -> Path:
    for r in ROOTS:
        for cand in (r / dataset / file, *(r / dataset).glob(f"**/{Path(file).name}")):
            if cand.exists():
                return cand
    raise FileNotFoundError(f"agregá el dataset '{dataset}' como input (falta {file}); raíces: {ROOTS}")


def _alts(row) -> list:
    """Alternativas de una sesión (pandas pone NaN en las filas que no tienen)."""
    v = getattr(row, "alts", None)
    return v if isinstance(v, list) else []


def _exists(ds: str, fl: str) -> bool:
    try:
        _path(ds, fl)
        return True
    except FileNotFoundError:
        return False


def resolve_sources(inst: str, start: str, end: str, include_rejected: bool = False) -> pd.DataFrame:
    """Sesiones con el archivo que REALMENTE se va a leer: el primario del resolver si está montado; si no, la primera alternativa consistente
    (mismo contrato y fecha, trades a 1 %) que esté montada; si no hay ninguna, dataset/file quedan en None y `missing_primary` dice qué falta."""
    s = sessions(inst, start, end, include_rejected).copy()
    ds_out, fl_out, note = [], [], []
    for r in s.itertuples(index=False):
        if _exists(r.dataset, r.file):
            ds_out.append(r.dataset); fl_out.append(r.file); note.append("")
            continue
        alt = next((a for a in _alts(r) if a.get("consistent") and _exists(a["dataset"], a["file"])), None)
        if alt:
            ds_out.append(alt["dataset"]); fl_out.append(alt["file"]); note.append(f"alternativa de {r.dataset}")
        else:
            ds_out.append(None); fl_out.append(None); note.append("falta")
    s["primary_dataset"], s["primary_file"] = s["dataset"], s["file"]
    s["dataset"], s["file"], s["source_note"] = ds_out, fl_out, note
    return s


def required_files(inst: str, start: str, end: str, include_rejected: bool = False) -> list[tuple[str, str]]:
    """(dataset, archivo) PRIMARIOS que hacen falta para esas sesiones (lo ideal). Úsalo ANTES de lanzar un kernel para saber qué datasets adjuntar."""
    s = sessions(inst, start, end, include_rejected)
    return sorted({(d, f) for d, f in zip(s.dataset, s.file)})


DROPPED: list[dict] = []        # sesiones aprobadas que se OMITIERON por no tener ninguna fuente (solo con EDGELAB_ALLOW_MISSING=1); guardalas en tus resultados


def _allow_missing() -> bool:
    return os.environ.get("EDGELAB_ALLOW_MISSING", "") == "1"


def check_inputs(*requests) -> None:
    """Falla en segundos (no tras 25 minutos de proceso) si alguna sesión no tiene NINGUNA fuente montada. Avisa si se usan alternativas. requests: (inst, start, end).
    Con EDGELAB_ALLOW_MISSING=1 NO falla: omite esas sesiones, las lista en pantalla y las deja en `DROPPED` (decisión explícita del usuario, hay que declararla en el resultado)."""
    missing = {}; alt = {}
    for inst, a, b in requests:
        for r in resolve_sources(inst, a, b).itertuples(index=False):
            if r.source_note == "falta":
                missing.setdefault(r.primary_dataset, set()).add(r.primary_file)
            elif r.source_note:
                alt[r.source_note] = alt.get(r.source_note, 0) + 1
    for k, n in alt.items():
        print(f"[edgelab_data] AVISO: {n} sesiones leídas de una fuente alternativa consistente ({k}); adjuntá el primario para evitarlo", flush=True)
    if missing and _allow_missing():
        for inst, a, b in requests:
            for r in resolve_sources(inst, a, b).itertuples(index=False):
                if r.source_note == "falta" and not any(d["instrument"] == inst and d["date"] == r.date for d in DROPPED):
                    DROPPED.append({"instrument": inst, "date": r.date, "dataset": r.primary_dataset, "file": r.primary_file})
        print(f"[edgelab_data] ATENCIÓN: {len(DROPPED)} sesiones aprobadas OMITIDAS por no tener ninguna fuente (EDGELAB_ALLOW_MISSING=1): " + ", ".join(f"{d['instrument']} {d['date']}" for d in DROPPED), flush=True)
        return
    if missing:
        raise FileNotFoundError("faltan inputs (sin alternativa montada); agregá estos datasets al kernel antes de correr: " + "; ".join(f"{d} ({len(f)} archivos, p. ej. {sorted(f)[0]})" for d, f in missing.items()))


def _session_date(ts_ns: np.ndarray) -> np.ndarray:
    """Fecha de sesión CME (17:00-16:00 CT), idéntica a la del catálogo (edgelab.discovery.data.tdate_ordinal):
    se etiqueta por el fin del minuto, se corre 1 ns atrás y se suman 7 h en hora de Chicago."""
    lab = (np.asarray(ts_ns) // 60_000_000_000 + 1) * 60_000_000_000 - 1
    ix = pd.to_datetime(lab, unit="ns", utc=True).tz_convert(CT) + pd.Timedelta(hours=7)
    return ix.strftime("%Y-%m-%d").to_numpy()


def load_ticks(inst: str, start: str, end: str, columns=None, include_rejected: bool = False) -> pd.DataFrame:
    """Ticks de las sesiones aprobadas, leyendo de cada archivo SOLO las sesiones que el resolver le asigna."""
    s = sessions(inst, start, end, include_rejected)
    if columns is not None and "ts_utc_ns" not in columns:
        columns = ["ts_utc_ns", *columns]
    out = []
    for (ds, fl), g in s.groupby(["dataset", "file"]):
        want = set(g.date)
        pf = pq.ParquetFile(_path(ds, fl))
        # rango UTC que cubre las sesiones pedidas (sesión d = d-1 17:00 CT .. d 16:00 CT; margen de 1 día)
        lo = pd.Timestamp(min(want)).tz_localize("UTC").value - 2 * 86_400 * 10**9
        hi = pd.Timestamp(max(want)).tz_localize("UTC").value + 2 * 86_400 * 10**9
        icol = pf.schema_arrow.get_field_index("ts_utc_ns")
        for i in range(pf.num_row_groups):
            st = pf.metadata.row_group(i).column(icol).statistics
            if st is not None and st.has_min_max and (st.max < lo or st.min > hi):
                continue
            t = pf.read_row_group(i, columns=columns).to_pandas()
            if not len(t):
                continue
            sd = _session_date(t["ts_utc_ns"].to_numpy())
            m = np.isin(sd, list(want))
            if m.any():
                t = t[m].copy(); t["session_date"] = sd[m]; out.append(t)
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True).sort_values("ts_utc_ns", kind="stable").reset_index(drop=True)
    tick = RESOLVER["instruments"][inst]["tick_size"]
    df.attrs.update(instrument=inst, tick_size=tick, holdout=HOLDOUT)
    return df


def _load_m1_slow(inst: str, start: str, end: str, include_rejected: bool = False) -> pd.DataFrame:
    """Versión original (tick por tick en pandas). Se conserva SOLO para verificar que `load_m1` da lo mismo; es ~20-50 veces más lenta."""
    t = load_ticks(inst, start, end, ["ts_utc_ns", "price_ticks", "volume", "aggressor", "contract"], include_rejected)
    if t.empty:
        return t
    t["minute"] = (t.ts_utc_ns // 60_000_000_000) * 60_000_000_000
    g = t.groupby(["session_date", "minute"], sort=True)
    m1 = g.agg(open=("price_ticks", "first"), high=("price_ticks", "max"), low=("price_ticks", "min"),
               close=("price_ticks", "last"), volume=("volume", "sum"), trades=("price_ticks", "size"),
               contract=("contract", "first")).reset_index()
    buy = t[t.aggressor == "buy"].groupby(["session_date", "minute"]).volume.sum()
    m1["buy_volume"] = m1.set_index(["session_date", "minute"]).index.map(buy).fillna(0).to_numpy()
    m1.attrs.update(instrument=inst, tick_size=t.attrs["tick_size"], units="price_ticks")
    return m1


_MIN = 60_000_000_000


def _minute_session_date(minute_ns: np.ndarray) -> np.ndarray:
    """Fecha de sesión de cada MINUTO (igual que `_session_date` por tick: depende solo del minuto). Se calcula una vez por minuto, no por tick."""
    return _session_date(minute_ns)


def _file_m1(path: Path) -> pd.DataFrame:
    """M1 de TODAS las sesiones de un archivo de ticks, en una pasada por grupos de filas con numpy (sin cadenas por tick).
    Columnas: session_date, minute, open, high, low, close, volume, trades, contract, buy_volume."""
    pf = pq.ParquetFile(path, read_dictionary=[c for c in ("aggressor", "contract") if c in pq.ParquetFile(path).schema_arrow.names])
    rows = []; vdt = None
    for i in range(pf.num_row_groups):
        t = pf.read_row_group(i, columns=["ts_utc_ns", "price_ticks", "volume", "aggressor", "contract"])
        vdt = vdt or t.column("volume").type.to_pandas_dtype()
        ts = t.column("ts_utc_ns").to_numpy(); n = len(ts)
        if not n:
            continue
        px = t.column("price_ticks").to_numpy(); vol = t.column("volume").to_numpy().astype(np.int64)
        ag = t.column("aggressor").combine_chunks(); ct = t.column("contract").combine_chunks()
        buy_code = ag.dictionary.to_pylist().index("buy") if "buy" in ag.dictionary.to_pylist() else -1
        isbuy = (ag.indices.to_numpy(zero_copy_only=False) == buy_code) if buy_code >= 0 else np.zeros(n, bool)
        minute = (ts // _MIN) * _MIN
        st = np.r_[0, np.flatnonzero(minute[1:] != minute[:-1]) + 1]; en = np.r_[st[1:], n]
        cts = np.asarray(ct.dictionary.to_pylist(), dtype=object)[ct.indices.to_numpy(zero_copy_only=False)[st]]
        rows.append(pd.DataFrame(dict(minute=minute[st], open=px[st], high=np.maximum.reduceat(px, st), low=np.minimum.reduceat(px, st), close=px[en - 1],
                                      volume=np.add.reduceat(vol, st), trades=(en - st).astype(np.int64), contract=cts, buy_volume=np.add.reduceat(np.where(isbuy, vol, 0), st).astype(np.float64))))
    if not rows:
        return pd.DataFrame()
    m = pd.concat(rows, ignore_index=True)
    # un minuto puede quedar partido entre dos grupos de filas: se une (primero/último en orden de archivo)
    g = m.groupby("minute", sort=True)
    m = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), volume=("volume", "sum"),
              trades=("trades", "sum"), contract=("contract", "first"), buy_volume=("buy_volume", "sum")).reset_index()
    m["volume"] = m["volume"].astype(vdt)            # mismo tipo que la versión original (pandas conserva el entero de la columna)
    m.insert(0, "session_date", _minute_session_date(m["minute"].to_numpy()))
    return m


def _m1_cached(ds: str, fl: str) -> pd.DataFrame:
    """M1 por archivo con caché en disco (EDGELAB_M1_CACHE, por omisión ~/.cache/edgelab_m1): la primera vez se arma, después se lee en segundos.
    Si existe el dataset `edgelab-m1-bars` como input, se usa directamente (ver tools/m1_store_build.py)."""
    key = f"{ds}__{fl.replace('/', '__')}.m1.parquet"
    for r in ROOTS:
        for cand in (r / "edgelab-m1-bars" / key, *(r / "edgelab-m1-bars").glob(f"**/{key}")):
            if cand.exists():
                return pd.read_parquet(cand)
    src = _path(ds, fl)
    cdir = Path(os.environ.get("EDGELAB_M1_CACHE", Path.home() / ".cache" / "edgelab_m1")); cdir.mkdir(parents=True, exist_ok=True)
    c = cdir / f"{key[:-len('.m1.parquet')]}__{src.stat().st_size}.m1.parquet"
    if c.exists():
        return pd.read_parquet(c)
    m = _file_m1(src)
    m.to_parquet(c)
    return m


def load_m1(inst: str, start: str, end: str, include_rejected: bool = False) -> pd.DataFrame:
    """Barras M1 (inicio de minuto, UTC) de las sesiones aprobadas: OHLC en ticks de precio, volumen, trades, volumen comprador agresor.
    Mismo resultado que `_load_m1_slow` (verificado en tests/test_edgelab_data_m1.py y en tools/m1_speed_check.py), mucho más rápido: agrega por grupo de filas con
    numpy, calcula la fecha de sesión una vez por minuto y guarda el M1 de cada archivo en caché."""
    check_inputs((inst, start, end))
    s = resolve_sources(inst, start, end, include_rejected)
    s = s[s.source_note != "falta"]
    if s.empty:
        return pd.DataFrame()
    out = []
    for (ds, fl), g in s.groupby(["dataset", "file"]):
        m = _m1_cached(ds, fl)
        out.append(m[m.session_date.isin(set(g.date))])
    m1 = pd.concat(out, ignore_index=True).sort_values(["session_date", "minute"], kind="stable").reset_index(drop=True)
    m1.attrs.update(instrument=inst, tick_size=RESOLVER["instruments"][inst]["tick_size"], units="price_ticks")
    return m1


def load_spot(inst: str, start: str, end: str, kind: str = "m1") -> pd.DataFrame:
    """Spot/CFD Dukascopy hermano del futuro `inst` (kind='m1' o 'ticks'). SOLO para potencia en pruebas de información;
    ver RESOLVER['spot_complement']. Aplica las exclusiones del proveedor y bloquea el holdout. Fechas en UTC."""
    _check(start, end)
    ds = RESOLVER["spot_datasets"][inst]
    files = [p for p in (r / ds for r in ROOTS) if p.exists()]
    if not files:
        raise FileNotFoundError(f"agregá el dataset '{ds}' como input")
    f = next(files[0].glob(f"*_{'m1' if kind == 'm1' else 'ticks'}.parquet"))
    lo = pd.Timestamp(start, tz="UTC").value; hi = pd.Timestamp(end, tz="UTC").value + 86_400 * 10**9
    t = pq.read_table(f, filters=[("time_utc_ns", ">=", lo), ("time_utc_ns", "<", hi)]).to_pandas()
    for x in RESOLVER["spot_exclusions"]:
        if ds in x["datasets"]:
            a, b = pd.Timestamp(x["from_utc"]).value, pd.Timestamp(x["to_utc"]).value
            t = t[(t.time_utc_ns < a) | (t.time_utc_ns >= b)]
    t.attrs.update(instrument=inst, spot_dataset=ds, warning=RESOLVER["spot_complement"])
    return t.reset_index(drop=True)


if __name__ == "__main__":      # python edgelab_data.py MES 2025-07-01 2026-09-30  -> datasets que hay que adjuntar al kernel
    import sys
    inst, a, b = sys.argv[1:4]
    need = required_files(inst, a, b); sess = sessions(inst, a, b)
    alts = sorted({x["dataset"] for al in sess.get("alts", pd.Series(dtype=object)) if isinstance(al, list) for x in al if x.get("consistent")} - {d for d, _ in need})
    print(json.dumps({"adjuntar (primarios)": sorted({d for d, _ in need}), "alternativos consistentes (cubren parte de las sesiones si falta algún primario)": alts}, indent=1, ensure_ascii=False))
