"""Gate P3 — auditor de materialización del store (F6.3).

Siete subgates. P3.1 (validación in-memory) y P3.2 (round-trip) se ejecutan
inline al publicar (`store.publish_run`); acá viven los verificadores que se
corren sobre el store YA publicado, más el auditor adversarial:

  P3.0 completitud de campaña   (check_campaign)
  P3.2 round-trip               (verify_roundtrip)      — re-lee parquet vs manifest
  P3.3 determinismo/recompute   (verify_recompute)      — reejecuta desde el manifest
  P3.4 accesibilidad por API    (verify_api)            — consulta pública vs digest
  P3.5 integridad entre configs (verify_cross_config)   — nada se mezcla
  P3.6 auditor adversarial      (audit_partition detecta las 9 corrupciones)
  P3.7 recorrido total          (audit_all)             — el gate previo a la campaña

Un auditor que solo vio datos sanos no es evidencia: los tests corrompen copias
sintéticas a propósito y exigen que audit_partition las detecte (exit != 0).
"""
from __future__ import annotations

import hashlib
import json
import os

from . import identity, store


def _manifest_of(part_row):
    # el auditor mira el ARTEFACTO en disco (manifest.json), no el índice del
    # catálogo: un manifest alterado en disco debe detectarse.
    with open(os.path.join(part_row["dir"], "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# P3.2 — round-trip (re-lee los parquet, recalcula digests vs manifest)
# --------------------------------------------------------------------------- #
def verify_roundtrip(pdir, manifest):
    try:
        rt = store._roundtrip_digests(pdir)
    except Exception as e:                       # parquet truncado/ilegible
        return dict(ok=False, code="PARQUET_UNREADABLE", detail=str(e))
    man = manifest["digests"]
    for k in ("event", "observation", "zone"):
        if rt[k] != man[k]:
            return dict(ok=False, code="DIGEST_MISMATCH",
                        detail="%s: disco=%s manifest=%s" % (k, rt[k], man[k]))
    return dict(ok=True, code="OK")


# --------------------------------------------------------------------------- #
# P3.4 — accesibilidad por API (consulta pública, no lee archivos a mano)
# --------------------------------------------------------------------------- #
def verify_api(root, manifest):
    rows = store.get_zones(root, run_id=manifest["run_id"])
    d = store.zone_rows_digest(rows)
    if d != manifest["digests"]["zone"]:
        return dict(ok=False, code="API_DIGEST_MISMATCH",
                    detail="api=%s manifest=%s" % (d, manifest["digests"]["zone"]))
    return dict(ok=True, code="OK")


# --------------------------------------------------------------------------- #
# Identidad de partición: el manifest y las filas deben ser autoconsistentes
# (detecta parámetro alterado y filas de otro contrato/config mezcladas)
# --------------------------------------------------------------------------- #
def verify_identity(pdir, manifest):
    # config_id debe derivarse de los params del manifest (params alterado -> cambia)
    try:
        cid = identity.config_id(manifest["indicator"], manifest["params"],
                                 manifest["bar_key"], manifest["chart_tz"],
                                 manifest["kernel_id"])
    except Exception as e:
        return dict(ok=False, code="CONFIG_ID_UNCOMPUTABLE", detail=str(e))
    if cid != manifest["config_id"]:
        return dict(ok=False, code="MANIFEST_TAMPERED",
                    detail="config_id recomputado=%s manifest=%s (params alterados?)"
                    % (cid, manifest["config_id"]))
    # cada fila de zona pertenece a esta partición
    ident = dict(config_id=manifest["config_id"], contract=manifest["contract"],
                 instrument=manifest["instrument"], bar_key=manifest["bar_key"],
                 run_id=manifest["run_id"], indicator=manifest["indicator"])
    for z in store.read_zone_rows(pdir):
        for k, v in ident.items():
            if z.get(k) != v:
                return dict(ok=False, code="FOREIGN_ROW",
                            detail="zona %s con %s=%s (esperado %s)"
                            % (z.get("zone_id"), k, z.get(k), v))
    return dict(ok=True, code="OK")


# --------------------------------------------------------------------------- #
# P3.3 — determinismo por recomputación (reejecuta desde el manifest)
# --------------------------------------------------------------------------- #
def verify_recompute(root, manifest, chart_tz=None):
    from . import bars as bars_mod
    from . import ticks as ticks_mod
    from .indicators import BAR_DRIVEN, REGISTRY

    ind = manifest["indicator"]
    if identity.kernel_id(ind) != manifest["kernel_id"]:
        return dict(ok=False, code="STALE",
                    detail="kernel_id cambió (código distinto en el árbol; no se mezcla)")
    src = manifest.get("source") or {}
    path = src.get("path")
    if src.get("kind") == "synthetic" or not path or not os.path.exists(path):
        return dict(ok=None, code="UNAVAILABLE", detail="fuente no disponible para recomputar")
    if src.get("sha256") and _sha256_file(path) != src["sha256"]:
        return dict(ok=False, code="SOURCE_CHANGED", detail="sha256 de la fuente cambió")

    def iso_ns(s):
        if not s:
            return None
        from datetime import datetime, timezone
        return int(datetime.fromisoformat(s.replace("Z", "")).replace(
            tzinfo=timezone.utc).timestamp() * 1e9)

    tk = ticks_mod.load_canonical_parquet(
        path, contract=manifest["contract"],
        start_utc_ns=iso_ns(src.get("range_start_utc")),
        end_utc_ns=iso_ns(src.get("range_end_utc")))
    kind, _, val = manifest["bar_key"].partition("_")
    bars = (bars_mod.build_time_bars(tk, int(val)) if kind == "time"
            else bars_mod.build_tick_bars(tk, int(val)))
    tz = chart_tz or manifest.get("chart_tz", "UTC")
    mod = REGISTRY[ind]
    if ind in BAR_DRIVEN:
        res = mod.run(tk, bars, bars_mod.build_footprints(tk, bars),
                      params=manifest["params"], chart_tz=tz)
    else:
        res = mod.run(tk, bars, params=manifest["params"], chart_tz=tz)

    ev = store.build_event_rows(res["csv_lines"], res.get("header"))
    ob = [r for r in ev if r["event_type"] in store.OBS_EVENT_TYPES]
    zr = store.build_zone_rows(res["zones"], run_id=manifest["run_id"], indicator=ind,
                               config_id=manifest["config_id"], bar_key=manifest["bar_key"],
                               contract=manifest["contract"], instrument=manifest["instrument"],
                               tick_size=tk.tick_size)
    new = dict(event=store._digest(ev, lambda r: r["seq"]),
               observation=store._digest(ob, lambda r: r["seq"]),
               zone=store.zone_rows_digest(zr))
    man = manifest["digests"]
    if all(new[k] == man[k] for k in ("event", "observation", "zone")):
        return dict(ok=True, code="RECOMPUTED_EXACT")
    cur_env = store._env_fingerprint()
    if cur_env != manifest.get("env"):
        return dict(ok=False, code="ENV_DIFF",
                    detail="digests distintos con entorno distinto: %s vs %s"
                    % (cur_env, manifest.get("env")))
    return dict(ok=False, code="DETERMINISM_FAIL",
                detail="digests distintos con mismo entorno: nuevo=%s manifest=%s" % (new, man))


# --------------------------------------------------------------------------- #
# P3.5 — integridad entre configuraciones (nada se mezcla)
# --------------------------------------------------------------------------- #
def verify_cross_config(root):
    diags = []
    parts = store.catalog_df(root)
    # una consulta por config_id jamás devuelve zonas de otra
    for p in parts:
        rows = store.get_zones(root, config_id=p["config_id"])
        foreign = {z["config_id"] for z in rows if z["config_id"] != p["config_id"]}
        if foreign:
            diags.append(dict(code="CONFIG_LEAK", config_id=p["config_id"],
                              detail="aparecen configs %s" % sorted(foreign)))
    # (dataset_id, config_id) duplicado en runs distintos = config duplicada
    seen = {}
    for p in parts:
        key = (p["dataset_id"], p["config_id"])
        seen.setdefault(key, set()).add(p["run_id"])
    for key, rids in seen.items():
        if len(rids) > 1:
            diags.append(dict(code="DUPLICATE_CONFIG", detail="%s -> runs %s"
                              % (key, sorted(rids))))
    return dict(ok=not diags, diagnostics=diags)


# --------------------------------------------------------------------------- #
# P3.0 — completitud de campaña
# --------------------------------------------------------------------------- #
def check_campaign(root, campaign):
    """campaign = dict(campaign_id, dataset_id, expected_config_ids=[...])."""
    present = {p["config_id"] for p in store.get_partitions(
        root, dataset_id=campaign["dataset_id"])}
    expected = set(campaign["expected_config_ids"])
    failed = set(campaign.get("failed_config_ids", []))
    missing = expected - present - failed
    # duplicados: (dataset, config) en >1 run
    dup = [d for d in verify_cross_config(root)["diagnostics"]
           if d["code"] == "DUPLICATE_CONFIG"]
    ok = not missing and not dup and (expected == (present | failed) - (present - expected))
    return dict(ok=bool(not missing and not dup),
                expected=len(expected), present=len(present & expected),
                failed=len(failed), missing=sorted(missing), duplicated=dup)


# --------------------------------------------------------------------------- #
# P3.6/P3.7 — auditor de partición + recorrido total
# --------------------------------------------------------------------------- #
def _safe(fn, *a, **k):
    """Un check que lanza excepción ES una detección (auditor defensivo)."""
    try:
        return fn(*a, **k)
    except Exception as e:
        return dict(ok=False, code="EXCEPTION", detail="%s: %s" % (type(e).__name__, e))


def audit_partition(root, part_row, recompute=False):
    pdir = part_row["dir"]
    manifest = _manifest_of(part_row)
    checks = {}
    checks["roundtrip"] = _safe(verify_roundtrip, pdir, manifest)     # P3.2
    checks["identity"] = _safe(verify_identity, pdir, manifest)       # tamper/foreign
    checks["api"] = _safe(verify_api, root, manifest)                 # P3.4
    if recompute:
        checks["recompute"] = _safe(verify_recompute, root, manifest)  # P3.3
    ok = all(c.get("ok") is not False for c in checks.values())
    return dict(run_id=manifest["run_id"], indicator=manifest["indicator"],
                config_id=manifest["config_id"], ok=ok, checks=checks)


def audit_all(root, *, recompute_sample=0.0, campaign=None):
    parts = store.catalog_df(root)
    reports = []
    # muestreo determinista para P3.3 (sin random): 1 de cada N por posición
    step = 0 if recompute_sample <= 0 else max(1, int(round(1.0 / recompute_sample)))
    for i, p in enumerate(parts):
        rc = step and (i % step == 0)
        reports.append(audit_partition(root, p, recompute=bool(rc)))
    cross = verify_cross_config(root)                          # P3.5
    camp = check_campaign(root, campaign) if campaign else None
    ok = all(r["ok"] for r in reports) and cross["ok"] and (camp is None or camp["ok"])
    return dict(ok=ok, n_partitions=len(parts), partitions=reports,
                cross_config=cross, campaign=camp)
