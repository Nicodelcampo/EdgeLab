"""Store v2 del bridge (F6.2): inmutable, content-addressed, tres niveles.

No guarda solo zonas finales. Por partición (una configuración corrida sobre un
dataset) escribe TRES tablas + manifest:

  observations.parquet — observaciones continuas (auditoría / refiltrado offline)
  events.parquet        — la timeline inmutable completa (fuente de verdad)
  zones.parquet         — proyección materializada para consulta rápida

Regla: zones DEBE poder reconstruirse desde events y dar el mismo digest de
núcleo — si difiere, se localiza el evento donde nació la discrepancia.

Layout (content-addressed; una carpeta por run):

  <root>/
    catalog.duckdb
    runs/instrument=<I>/contract=<C>/indicator=<K>/kernel_id=<KID>/
         bar_key=<BK>/config_id=<CID>/run_id=<RID>/
             manifest.json  observations.parquet  events.parquet  zones.parquet

Reglas duras:
- escribir a temp -> validar (P3.1) -> round-trip (P3.2) -> publicar por rename
  atómico. Partición publicada = INMUTABLE.
- reejecución idéntica: digests iguales -> idempotencia (no duplica); distintos
  -> ERROR DE DETERMINISMO (no sobrescribe, frena y reporta).
- cero zonas es un resultado VÁLIDO (zone_count=0, partición y manifest igual).

Estados en DOS ejes ortogonales (reemplazan el booleano `trusted`):
  integridad: computed -> persisted -> roundtrip_verified -> recomputed_exact
              -> api_verified | stale | failed
  paridad:    parity_pending | parity_exact | parity_covered | parity_failed
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys

from . import oracle
from .identity import ID_LEN, canonical_json, zone_key as _zone_key

SCHEMA_VERSION = 2
OBS_EVENT_TYPES = ("OBS", "TRAP")     # observaciones continuas por indicador

INTEGRITY_STATES = ("computed", "persisted", "roundtrip_verified",
                    "recomputed_exact", "api_verified", "stale", "failed")
PARITY_STATES = ("parity_pending", "parity_exact", "parity_covered", "parity_failed")


class DeterminismError(RuntimeError):
    """Reejecución con mismos inputs produjo digests distintos (no determinismo
    o corrupción). Nunca se sobrescribe: se frena y se reporta."""


class ImmutabilityError(RuntimeError):
    """Intento de reescribir una partición publicada con contenido distinto."""


# --------------------------------------------------------------------------- #
# Rutas / digests
# --------------------------------------------------------------------------- #
def _san(s):
    import re
    return re.sub(r"[^A-Za-z0-9._=-]+", "_", str(s)).strip("_") or "_"


def partition_dir(root, *, instrument, contract, indicator, kernel_id, bar_key,
                  config_id, run_id):
    return os.path.join(
        str(root), "runs",
        "instrument=" + _san(instrument), "contract=" + _san(contract),
        "indicator=" + _san(indicator), "kernel_id=" + _san(kernel_id),
        "bar_key=" + _san(bar_key), "config_id=" + _san(config_id),
        "run_id=" + _san(run_id))


def _digest(rows, sort_key):
    """sha256 sobre filas ordenadas canónicamente (JSON con claves ordenadas)."""
    h = hashlib.sha256()
    for row in sorted(rows, key=sort_key):
        h.update(canonical_json(row).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:ID_LEN]


# --------------------------------------------------------------------------- #
# Construcción de tablas desde la salida del kernel
# --------------------------------------------------------------------------- #
def _parse_payload_comma(header, line):
    parts = line.split(",")
    d = dict(zip(header, parts))
    seq = int(d.get("event_seq") or d.get("seq") or 0)
    etype = d.get("event_type", "")
    unix_ms = d.get("unix_ms")
    unix_ms = int(unix_ms) if unix_ms not in (None, "") else None
    zid = d.get("gap_id") or d.get("zone_id") or None
    if zid == "":
        zid = None
    payload = {k: v for k, v in d.items()
               if k not in ("event_seq", "seq", "event_type", "unix_ms")}
    return dict(seq=seq, event_type=etype, unix_ms=unix_ms, zone_id=zid,
                payload=json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _parse_payload_pipe(line):
    parts = line.split("|", 3)
    if len(parts) < 4:
        return None
    seq, iso, etype, payload = parts
    kv = {}
    for p in payload.split(";"):
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k.strip()] = v.strip()
    zid = kv.get("zone_id") or None
    kv["ts"] = iso
    return dict(seq=int(seq), event_type=etype, unix_ms=None, zone_id=zid,
                payload=json.dumps(kv, ensure_ascii=False, sort_keys=True))


def build_event_rows(csv_lines, header):
    """Esquema uniforme para todos los indicadores: seq, event_type, unix_ms,
    zone_id, payload(JSON con el resto de los campos del EventLog)."""
    rows = []
    is_pipe = header is None
    for ln in csv_lines:
        if not ln.strip():
            continue
        row = _parse_payload_pipe(ln) if is_pipe else _parse_payload_comma(
            header.split(","), ln)
        if row is not None:
            rows.append(row)
    return rows


def _side_of(z):
    if "dir" in z and z["dir"] in (1, -1):
        return "up" if z["dir"] == 1 else "down"
    k = (z.get("kind") or "").lower()
    if "bull" in k or "buyers" in k or "support" in k:
        return "bull"
    if "bear" in k or "sellers" in k or "resist" in k:
        return "bear"
    return "none"


_ZONE_PROMOTED = {"id", "indicator", "top", "bottom", "created_ms", "ended_ms",
                  "state", "kind", "touches", "end_reason", "timeline"}


def build_zone_rows(kernel_zones, *, run_id, indicator, config_id, bar_key,
                    contract, instrument, tick_size):
    rows = []
    for z in kernel_zones:
        if z.get("created_ms") is None or z.get("top") is None:
            continue
        lo_t = int(round(z["bottom"] / tick_size))
        hi_t = int(round(z["top"] / tick_size))
        side = _side_of(z)
        zk = _zone_key(run_id, z["id"], 0, int(z["created_ms"]), lo_t, hi_t, side)
        feats = {k: v for k, v in z.items() if k not in _ZONE_PROMOTED}
        rows.append(dict(
            zone_key=zk, run_id=run_id, indicator=indicator, config_id=config_id,
            bar_key=bar_key, contract=contract, instrument=instrument,
            zone_id=str(z["id"]), kind=z.get("kind"), side=side,
            final_state=z.get("state"), top=float(z["top"]), bottom=float(z["bottom"]),
            lower_tick=lo_t, upper_tick=hi_t, created_ms=int(z["created_ms"]),
            ended_ms=None if z.get("ended_ms") is None else int(z["ended_ms"]),
            touches=int(z.get("touches") or 0), end_reason=z.get("end_reason"),
            features=json.dumps(feats, ensure_ascii=False, sort_keys=True, default=str)))
    return rows


def _core(z_price_dict, tick_size):
    """Núcleo comparable de una zona (reconstruible desde events). Estado
    normalizado a terminal|activo para robustez de reconstrucción.

    La geometría se mide en MEDIO-tick (`tick_size/2`): los bordes de zona caen
    en la grilla de tick entero o medio-tick (p.ej. POC ± 0.5 tick), así que en
    medio-ticks son SIEMPRE enteros -> el redondeo nunca cae en un límite .5
    (evita el banker's rounding + error de float que hace divergir dos caminos
    que computan el mismo precio con operaciones distintas)."""
    ended = z_price_dict.get("ended_ms")
    st = (z_price_dict.get("state") or "").upper()
    norm = st if st in ("INVALIDATED", "EXPIRED") else ("CLOSED" if ended else "ACTIVE")
    ht = tick_size * 0.5
    return dict(zone_id=str(z_price_dict["id"]),
                created_ms=int(z_price_dict["created_ms"]),
                ended_ms=None if ended is None else int(ended),
                lower_ht=int(round(z_price_dict["bottom"] / ht)),
                upper_ht=int(round(z_price_dict["top"] / ht)),
                state=norm, touches=int(z_price_dict.get("touches") or 0))


def zones_core_digest_from_kernel(kernel_zones, tick_size):
    core = [_core(z, tick_size) for z in kernel_zones
            if z.get("created_ms") is not None and z.get("top") is not None]
    return _digest(core, lambda r: (r["created_ms"], r["lower_ht"], r["upper_ht"], r["zone_id"]))


def zones_core_digest_from_events(csv_lines, header, params_line, indicator,
                                  chart_tz, tick_size):
    """Reconstruye zonas desde el EventLog (mismo parser que el oráculo NT8) y
    devuelve el digest de núcleo. Debe coincidir con el del kernel."""
    lines = []
    if params_line:
        lines.append(params_line)
    if header:
        lines.append(header)
    lines.extend(csv_lines)
    rec = oracle.parse_records(lines, chart_tz=chart_tz, tick_size=tick_size)
    core = [_core(z, tick_size) for z in rec["zones"]
            if z.get("created_ms") is not None and z.get("top") is not None]
    return _digest(core, lambda r: (r["created_ms"], r["lower_ht"], r["upper_ht"], r["zone_id"]))


# --------------------------------------------------------------------------- #
# Entorno (para el eje de determinismo)
# --------------------------------------------------------------------------- #
def _env_fingerprint():
    lock = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "requirements", "core-bridge-dev.lock")
    lock_sha = None
    if os.path.exists(lock):
        h = hashlib.sha256()
        with open(lock, "rb") as fh:
            h.update(fh.read())
        lock_sha = h.hexdigest()[:ID_LEN]
    return dict(python="%d.%d.%d" % sys.version_info[:3], lockfile_sha256=lock_sha)


# --------------------------------------------------------------------------- #
# Escritura de parquet
# --------------------------------------------------------------------------- #
def _write_parquet(rows, path, columns):
    import pyarrow as pa
    import pyarrow.parquet as pq
    data = {c: [r.get(c) for r in rows] for c in columns}
    pq.write_table(pa.table(data), path, compression="zstd")


def _read_parquet_rows(path):
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    cols = t.column_names
    out = []
    pydata = {c: t.column(c).to_pylist() for c in cols}
    for i in range(t.num_rows):
        out.append({c: pydata[c][i] for c in cols})
    return out


_EVENT_COLS = ("seq", "event_type", "unix_ms", "zone_id", "payload")
_ZONE_COLS = ("zone_key", "run_id", "indicator", "config_id", "bar_key",
              "contract", "instrument", "zone_id", "kind", "side", "final_state",
              "top", "bottom", "lower_tick", "upper_tick", "created_ms",
              "ended_ms", "touches", "end_reason", "features")


# --------------------------------------------------------------------------- #
# Publicación de un run (P3.1 in-memory + P3.2 round-trip inline)
# --------------------------------------------------------------------------- #
def _parity_state(parity):
    if not parity:
        return "parity_pending"
    gate = parity.get("gate")
    if gate == "FAIL":
        return "parity_failed"
    if gate in ("PASS", "WARN"):
        return "parity_exact"
    return "parity_pending"


def _validate_in_memory(event_rows, zone_rows, kernel_zones, csv_lines, header,
                        params_line, indicator, chart_tz, tick_size):
    """P3.1: validaciones pre-escritura. Devuelve (errores, zone_core_digest)."""
    errs = []
    seqs = [r["seq"] for r in event_rows]
    if seqs != sorted(seqs):
        errs.append("event seq no monotono")
    zks = [r["zone_key"] for r in zone_rows]
    if len(zks) != len(set(zks)):
        errs.append("zone_key duplicado")
    for z in zone_rows:
        if z["lower_tick"] > z["upper_tick"]:
            errs.append("geometria invalida en %s: lower>upper" % z["zone_id"])
        if z["ended_ms"] is not None and z["created_ms"] > z["ended_ms"]:
            errs.append("created_ms>ended_ms en %s" % z["zone_id"])
    # reconstruccion: zones (kernel) == zones reconstruidas desde events
    dk = zones_core_digest_from_kernel(kernel_zones, tick_size)
    de = zones_core_digest_from_events(csv_lines, header, params_line, indicator,
                                       chart_tz, tick_size)
    if dk != de:
        errs.append("zones no reconstruibles desde events (kernel=%s events=%s)" % (dk, de))
    return errs, dk


def publish_run(root, *, kernel_result, indicator, tick_size, instrument, contract,
                bar_key, dataset_id, kernel_id, config_id, run_id, params, source,
                chart_tz="UTC", parity=None, generated_utc=None, param_set_id=None):
    """Publica un run al store (inmutable, content-addressed). Idempotente si los
    digests coinciden; DeterminismError si difieren. Devuelve el manifest."""
    csv_lines = kernel_result["csv_lines"]
    header = kernel_result.get("header")
    params_line = kernel_result.get("params_line")
    kernel_zones = kernel_result["zones"]

    event_rows = build_event_rows(csv_lines, header)
    obs_rows = [r for r in event_rows if r["event_type"] in OBS_EVENT_TYPES]
    zone_rows = build_zone_rows(
        kernel_zones, run_id=run_id, indicator=indicator, config_id=config_id,
        bar_key=bar_key, contract=contract, instrument=instrument, tick_size=tick_size)

    errs, core_digest = _validate_in_memory(
        event_rows, zone_rows, kernel_zones, csv_lines, header, params_line,
        indicator, chart_tz, tick_size)
    if errs:
        raise ValueError("%s: validacion P3.1 fallo: %s" % (run_id, "; ".join(errs)))

    ev_digest = _digest(event_rows, lambda r: r["seq"])
    ob_digest = _digest(obs_rows, lambda r: r["seq"])
    zn_rows_stored = [{k: z[k] for k in _ZONE_COLS} for z in zone_rows]
    zn_digest = _digest(zn_rows_stored,
                        lambda r: (r["created_ms"], r["lower_tick"], r["upper_tick"], r["zone_key"]))
    digests = dict(event=ev_digest, observation=ob_digest, zone=zn_digest,
                   zone_core=core_digest)

    ev_counts = {}
    for r in event_rows:
        ev_counts[r["event_type"]] = ev_counts.get(r["event_type"], 0) + 1
    zst_counts = {}
    for z in zone_rows:
        st = z["final_state"] or "None"
        zst_counts[st] = zst_counts.get(st, 0) + 1

    manifest = dict(
        schema_version=SCHEMA_VERSION, run_id=run_id, dataset_id=dataset_id,
        kernel_id=kernel_id, config_id=config_id, param_set_id=param_set_id,
        indicator=indicator, instrument=instrument, contract=contract,
        bar_key=bar_key, params=params, source=source, chart_tz=chart_tz,
        counts=dict(events=ev_counts, zone_states=zst_counts,
                    n_events=len(event_rows), n_observations=len(obs_rows),
                    n_zones=len(zone_rows)),
        digests=digests, env=_env_fingerprint(),
        integrity_state="roundtrip_verified", parity_state=_parity_state(parity),
        parity=parity, generated_utc=generated_utc)

    pdir = partition_dir(root, instrument=instrument, contract=contract,
                         indicator=indicator, kernel_id=kernel_id, bar_key=bar_key,
                         config_id=config_id, run_id=run_id)

    if os.path.isdir(pdir) and os.path.exists(os.path.join(pdir, "manifest.json")):
        with open(os.path.join(pdir, "manifest.json"), encoding="utf-8") as fh:
            prev = json.load(fh)
        if prev.get("digests") == digests:
            _catalog_upsert(root, manifest, pdir)
            return prev                      # idempotente: no reescribe
        raise DeterminismError(
            "%s: digests distintos a la particion publicada (prev=%s nuevo=%s). "
            "No se sobrescribe." % (run_id, prev.get("digests"), digests))

    tmp = pdir + ".tmp"
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp, exist_ok=True)
    _write_parquet(event_rows, os.path.join(tmp, "events.parquet"), _EVENT_COLS)
    _write_parquet(obs_rows, os.path.join(tmp, "observations.parquet"), _EVENT_COLS)
    _write_parquet(zn_rows_stored, os.path.join(tmp, "zones.parquet"), _ZONE_COLS)

    rt = _roundtrip_digests(tmp)
    if rt != dict(event=ev_digest, observation=ob_digest, zone=zn_digest):
        shutil.rmtree(tmp)
        raise ValueError("%s: round-trip P3.2 fallo (memoria != disco): %s" % (run_id, rt))

    with open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False, default=str)
    with open(os.path.join(tmp, "validation.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(p31_errors=[], digests=digests, roundtrip=rt,
                       integrity_state="roundtrip_verified"), fh, indent=2)
    with open(os.path.join(tmp, "parity.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(parity_state=manifest["parity_state"], parity=parity),
                  fh, indent=2, default=str)

    os.makedirs(os.path.dirname(pdir), exist_ok=True)
    os.replace(tmp, pdir)                    # publicacion atomica
    _catalog_upsert(root, manifest, pdir)
    return manifest


def _roundtrip_digests(pdir):
    ev = _read_parquet_rows(os.path.join(pdir, "events.parquet"))
    ob = _read_parquet_rows(os.path.join(pdir, "observations.parquet"))
    zn = _read_parquet_rows(os.path.join(pdir, "zones.parquet"))
    return dict(
        event=_digest(ev, lambda r: r["seq"]),
        observation=_digest(ob, lambda r: r["seq"]),
        zone=_digest(zn, lambda r: (r["created_ms"], r["lower_tick"],
                                    r["upper_tick"], r["zone_key"])))


# --------------------------------------------------------------------------- #
# Catalogo DuckDB (una fila por particion)
# --------------------------------------------------------------------------- #
def catalog_path(root):
    return os.path.join(str(root), "catalog.duckdb")


_CATALOG_DDL = (
    "CREATE TABLE IF NOT EXISTS partitions ("
    "run_id VARCHAR PRIMARY KEY, dataset_id VARCHAR, kernel_id VARCHAR,"
    "config_id VARCHAR, param_set_id VARCHAR, indicator VARCHAR, instrument VARCHAR,"
    "contract VARCHAR, bar_key VARCHAR, n_events BIGINT, n_observations BIGINT,"
    "n_zones BIGINT, event_digest VARCHAR, observation_digest VARCHAR,"
    "zone_digest VARCHAR, zone_core_digest VARCHAR, integrity_state VARCHAR,"
    "parity_state VARCHAR, generated_utc VARCHAR, dir VARCHAR, manifest_json VARCHAR)")


def _catalog_upsert(root, manifest, pdir):
    import duckdb
    con = duckdb.connect(catalog_path(root))
    try:
        con.execute(_CATALOG_DDL)
        con.execute("DELETE FROM partitions WHERE run_id = ?", [manifest["run_id"]])
        d = manifest["digests"]
        c = manifest["counts"]
        con.execute(
            "INSERT INTO partitions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [manifest["run_id"], manifest["dataset_id"], manifest["kernel_id"],
             manifest["config_id"], manifest.get("param_set_id"), manifest["indicator"],
             manifest["instrument"], manifest["contract"], manifest["bar_key"],
             c["n_events"], c["n_observations"], c["n_zones"], d["event"],
             d["observation"], d["zone"], d["zone_core"], manifest["integrity_state"],
             manifest["parity_state"], manifest.get("generated_utc"), pdir,
             json.dumps(manifest, ensure_ascii=False, default=str)])
    finally:
        con.close()


def catalog_df(root):
    """Catalogo como lista de dicts (una fila por particion)."""
    import duckdb
    p = catalog_path(root)
    if not os.path.exists(p):
        return []
    con = duckdb.connect(p, read_only=True)
    try:
        cur = con.execute("SELECT * FROM partitions ORDER BY indicator, config_id")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        con.close()


def zone_rows_digest(rows):
    """Digest de zonas sobre las columnas del store (mismo orden canónico que
    usa el manifest). Base de P3.4 (API) y P3.6 (auditor)."""
    return _digest([{k: r[k] for k in _ZONE_COLS} for r in rows],
                   lambda r: (r["created_ms"], r["lower_tick"], r["upper_tick"], r["zone_key"]))


def read_zone_rows(pdir):
    return _read_parquet_rows(os.path.join(pdir, "zones.parquet"))


def read_event_rows(pdir):
    return _read_parquet_rows(os.path.join(pdir, "events.parquet"))


_PART_FILTER_KEYS = ("indicator", "config_id", "contract", "instrument",
                     "bar_key", "integrity_state", "parity_state", "run_id",
                     "kernel_id", "dataset_id")


def get_partitions(root, **filters):
    """Filas del catálogo filtradas por identidad/estado (API pública)."""
    unknown = set(filters) - set(_PART_FILTER_KEYS)
    if unknown:
        raise KeyError("filtros desconocidos: %s" % sorted(unknown))
    out = []
    for r in catalog_df(root):
        if all(filters.get(k) in (None, r.get(k)) for k in _PART_FILTER_KEYS):
            out.append(r)
    return out


def get_zones(root, *, state=None, created_after_ms=None, created_before_ms=None,
              **pfilters):
    """Zonas (filas del store) de las particiones que matchean, vía la API
    pública (lee del catálogo + zones.parquet, nunca asume rutas). La fuerza
    bruta consume esto. `pfilters` = filtros de partición (indicator, config_id,
    contract, instrument, bar_key, integrity_state, parity_state, ...)."""
    rows = []
    for p in get_partitions(root, **pfilters):
        for z in read_zone_rows(p["dir"]):
            if state is not None and z["final_state"] != state:
                continue
            if created_after_ms is not None and z["created_ms"] < created_after_ms:
                continue
            if created_before_ms is not None and z["created_ms"] >= created_before_ms:
                continue
            rows.append(z)
    return rows


def set_state(root, run_id, *, integrity_state=None, parity_state=None):
    """Actualiza los ejes de estado de una particion (manifest + catalogo).
    NO toca los parquets publicados (inmutables)."""
    import duckdb
    for m in catalog_df(root):
        if m["run_id"] != run_id:
            continue
        man_path = os.path.join(m["dir"], "manifest.json")
        with open(man_path, encoding="utf-8") as fh:
            man = json.load(fh)
        if integrity_state is not None:
            if integrity_state not in INTEGRITY_STATES:
                raise ValueError("integrity_state invalido: %s" % integrity_state)
            man["integrity_state"] = integrity_state
        if parity_state is not None:
            if parity_state not in PARITY_STATES:
                raise ValueError("parity_state invalido: %s" % parity_state)
            man["parity_state"] = parity_state
        with open(man_path, "w", encoding="utf-8") as fh:
            json.dump(man, fh, indent=2, ensure_ascii=False, default=str)
        con = duckdb.connect(catalog_path(root))
        try:
            con.execute(_CATALOG_DDL)
            con.execute("UPDATE partitions SET integrity_state=?, parity_state=? WHERE run_id=?",
                        [man["integrity_state"], man["parity_state"], run_id])
        finally:
            con.close()
        return man
    raise KeyError("run_id no esta en el catalogo: %s" % run_id)
