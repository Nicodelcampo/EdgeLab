#!/usr/bin/env python3
"""Verificador fail-closed de los indices sellados del bundle Kaggle.

Verifica, sin leer un solo parquet y sin pyarrow:

  1. SELLOS: recomputa index_sha256 y recut_index_sha256 con la misma
     canonicalizacion de edgelab.kaggle.identity.sha256_json. Un manifiesto
     editado a mano no cierra.
  2. CADENA: recut_index.source_index apunta al bundle_index exacto (sello,
     tool, veredicto) y cada archivo objetivo coincide en source_sha256 y en
     rows_total con el registro sellado del bundle. Esto ata la medicion al
     indice, no a la palabra del operador.
  3. ARITMETICA: rows_keep + rows_drop == rows_total por archivo, sumas contra
     totals, fuga <= descarte, y particion del censo (limpios + objetivo).
  4. FRONTERA: el corte NO se le cree al manifiesto; se re-deriva de
     sessions_cme.session_bounds_utc_ns con la tzdata del sistema. Se exige
     ts_max_keep < corte y trade_date_max_keep <= 20260630.
  5. IDENTIDAD DE CODIGO: compara code_identity contra los blobs del repo
     tolerando checkout Windows (CRLF) sin tapar deriva semantica real.
  6. PRESUPUESTO HONESTO: proyecta el bundle DESPUES del re-corte (los 11
     archivos re-cortados vuelven a entrar). El campo projected_bundle de una
     corrida --precheck solo cuenta los limpios y subestima el problema.

Veredictos FAIL_* -> exit 1 (fail-closed). WARN_* y PASS -> exit 0.

Uso:
    python tools/verify_indices.py --bundle docs/research/bundle_index.json \
                                   --recut  docs/research/recut_index.json
    python tools/verify_indices.py --selftest

Solo stdlib + numpy.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

TOOL_ID = "tools/verify_indices.py@v1"
SCHEMA_VERSION = 1
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

EXPECTED_BUNDLE_TOOL = "tools/build_kaggle_bundle.py@v2"
EXPECTED_RECUT_TOOL = "tools/recut_holdout.py@v1"
HOLDOUT_FIRST_TRADE_DATE = 20260701
RESEARCH_MAX_TRADE_DATE = 20260630
EXPECTED_COLUMNS = 13
METADATA_FILES = 4

# Oraculo independiente de la frontera. Si sessions_cme y este numero no
# coinciden, algo cambio en la regla congelada o en la tzdata: es un FAIL.
EXPECTED_SESSION_OPEN_NS = 1782856800000000000
EXPECTED_NAIVE_CUT_NS = 1782864000000000000

VERDICT_PRECEDENCE = (
    "FAIL_SEAL",
    "FAIL_CHAIN",
    "FAIL_ARITH",
    "FAIL_CUT",
    "FAIL_STATUS",
    "FAIL_CODE",
    "WARN_MAINTENANCE",
    "WARN_BUDGET",
    "PASS",
)


# --------------------------------------------------------------------------- #
# utilidades
# --------------------------------------------------------------------------- #
def git_blob_sha1_bytes(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256_json(obj) -> str:
    """Igual a edgelab.kaggle.identity.sha256_json (claves ordenadas, compacto)."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(payload)


def load_module_by_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"no se pudo cargar {name} desde {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_repo_modules(repo_root: pathlib.Path) -> SimpleNamespace:
    kag = repo_root / "edgelab" / "kaggle"
    return SimpleNamespace(
        identity=load_module_by_path("_vi_identity", kag / "identity.py"),
        inventory=load_module_by_path("_vi_inventory", kag / "inventory.py"),
        sessions=load_module_by_path("_vi_sessions", kag / "sessions_cme.py"),
    )


class Report:
    """Acumulador de chequeos. level: FAIL | WARN | INFO."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, cid: str, ok: bool, detail: str, level: str = "FAIL") -> bool:
        self.rows.append(
            {"id": cid, "ok": bool(ok), "level": level, "detail": detail}
        )
        return bool(ok)

    def failed(self, level: str) -> list[dict]:
        return [r for r in self.rows if not r["ok"] and r["level"] == level]

    @property
    def n_ok(self) -> int:
        return sum(1 for r in self.rows if r["ok"])

    def render(self) -> str:
        out = []
        for r in self.rows:
            mark = "ok  " if r["ok"] else ("FALLA" if r["level"] == "FAIL" else "AVISO")
            out.append(f"  [{mark:5s}] {r['id']:34s} {r['detail']}")
        return "\n".join(out)


def _num(d: dict, key: str):
    v = d.get(key)
    return v if isinstance(v, (int, float)) else None


# --------------------------------------------------------------------------- #
# 1. sellos
# --------------------------------------------------------------------------- #
def check_seal(rep: Report, obj: dict, seal_key: str, label: str) -> None:
    declared = obj.get(seal_key)
    if not isinstance(declared, str) or len(declared) != 64:
        rep.add(f"seal.{label}.presente", False, f"{seal_key} ausente o no es sha256")
        return
    body = {k: v for k, v in obj.items() if k != seal_key}
    recomputed = canonical_sha256_json(body)
    rep.add(
        f"seal.{label}",
        recomputed == declared,
        f"declarado {declared[:16]}... recomputado {recomputed[:16]}...",
    )


# --------------------------------------------------------------------------- #
# 2. cadena bundle -> recut
# --------------------------------------------------------------------------- #
def check_chain(rep: Report, bundle: dict | None, recut: dict) -> None:
    src = recut.get("source_index") or {}
    rep.add(
        "chain.recut.tool",
        recut.get("tool") == EXPECTED_RECUT_TOOL,
        f"tool={recut.get('tool')!r}",
    )
    rep.add(
        "chain.source.tool",
        src.get("tool") == EXPECTED_BUNDLE_TOOL,
        f"source_index.tool={src.get('tool')!r}",
    )
    if bundle is None:
        rep.add(
            "chain.bundle.presente",
            False,
            "sin bundle_index.json no se puede atar la cadena",
            level="WARN",
        )
        return

    rep.add(
        "chain.bundle.tool",
        bundle.get("tool") == EXPECTED_BUNDLE_TOOL,
        f"bundle.tool={bundle.get('tool')!r}",
    )
    rep.add(
        "chain.sello_cruzado",
        src.get("index_sha256") == bundle.get("index_sha256"),
        f"recut->{str(src.get('index_sha256'))[:16]}... bundle->{str(bundle.get('index_sha256'))[:16]}...",
    )
    rep.add(
        "chain.veredicto_fuente",
        src.get("verdict") == bundle.get("verdict"),
        f"recut->{src.get('verdict')!r} bundle->{bundle.get('verdict')!r}",
    )

    by_name = {r.get("file"): r for r in bundle.get("files", []) if isinstance(r, dict)}

    # el conjunto objetivo debe ser exactamente el puesto en cuarentena
    quarantined = {
        r.get("file")
        for r in bundle.get("files", [])
        if isinstance(r, dict) and r.get("holdout_overlap")
    }
    targets = {r.get("file") for r in recut.get("files", [])}
    rep.add(
        "chain.conjunto_objetivo",
        targets == quarantined,
        f"objetivo={len(targets)} cuarentena_bundle={len(quarantined)}"
        + ("" if targets == quarantined else f" dif={sorted(targets ^ quarantined)}"),
    )

    sha_bad, rows_bad, missing = [], [], []
    for r in recut.get("files", []):
        name = r.get("file")
        b = by_name.get(name)
        if b is None:
            missing.append(name)
            continue
        if r.get("source_sha256") != b.get("sha256"):
            sha_bad.append(name)
        if _num(r, "rows_total") != _num(b, "rows"):
            rows_bad.append(name)
    rep.add("chain.archivos_en_indice", not missing, f"faltantes={missing or 'ninguno'}")
    rep.add(
        "chain.sha256_por_archivo",
        not sha_bad,
        f"sha256 medido == sellado en {len(recut.get('files', [])) - len(sha_bad)}/{len(recut.get('files', []))}"
        + (f" | discrepan={sha_bad}" if sha_bad else ""),
    )
    rep.add(
        "chain.rows_total_por_archivo",
        not rows_bad,
        "rows_total medido == rows sellado"
        + (f" | discrepan={rows_bad}" if rows_bad else ""),
    )


# --------------------------------------------------------------------------- #
# 3. aritmetica
# --------------------------------------------------------------------------- #
def check_arithmetic(rep: Report, recut: dict, bundle: dict | None) -> None:
    files = [r for r in recut.get("files", []) if isinstance(r, dict)]
    bad_sum, bad_leak = [], []
    s_total = s_keep = s_drop = s_leak = 0
    for r in files:
        t, k, d = _num(r, "rows_total"), _num(r, "rows_keep"), _num(r, "rows_drop")
        lk = _num(r, "rows_leaked_by_naive_utc_cut")
        if None in (t, k, d):
            bad_sum.append(r.get("file"))
            continue
        if k + d != t:
            bad_sum.append(r.get("file"))
        if lk is not None and lk > d:
            bad_leak.append(r.get("file"))
        s_total += t
        s_keep += k
        s_drop += d
        s_leak += lk or 0

    rep.add(
        "arit.keep_mas_drop",
        not bad_sum,
        f"cierra en {len(files) - len(bad_sum)}/{len(files)} archivos"
        + (f" | rotos={bad_sum}" if bad_sum else ""),
    )
    rep.add(
        "arit.fuga_subconjunto_descarte",
        not bad_leak,
        "fuga_naive <= rows_drop" + (f" | rotos={bad_leak}" if bad_leak else ""),
    )

    tot = recut.get("totals") or {}
    for key, got in (
        ("rows_total_source", s_total),
        ("rows_keep", s_keep),
        ("rows_drop", s_drop),
        ("rows_leaked_by_naive_utc_cut", s_leak),
    ):
        rep.add(
            f"arit.totals.{key}",
            _num(tot, key) == got,
            f"declarado {tot.get(key)!r} vs suma {got}",
        )
    rep.add(
        "arit.totals.targets",
        _num(tot, "targets") == len(files),
        f"declarado {tot.get('targets')!r} vs {len(files)} registros",
    )

    if bundle is not None:
        all_rows = sum(
            _num(r, "rows") or 0
            for r in bundle.get("files", [])
            if isinstance(r, dict)
        )
        clean_rows = _num(bundle.get("summary") or {}, "total_rows") or 0
        rep.add(
            "arit.particion_censo",
            clean_rows + s_total == all_rows,
            f"limpios {clean_rows} + objetivo {s_total} = {clean_rows + s_total} vs censo {all_rows}",
        )


# --------------------------------------------------------------------------- #
# 4. frontera re-derivada
# --------------------------------------------------------------------------- #
def check_cut(rep: Report, recut: dict, mods: SimpleNamespace) -> None:
    cut = recut.get("cut") or {}
    open_ns, _close = mods.sessions.session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)
    rep.add(
        "cut.rederivado_tzdata",
        int(open_ns) == EXPECTED_SESSION_OPEN_NS,
        f"sessions_cme dice {open_ns} y el oraculo {EXPECTED_SESSION_OPEN_NS}",
    )
    rep.add(
        "cut.manifiesto_vs_rederivado",
        _num(cut, "session_open_utc_ns") == int(open_ns),
        f"manifiesto {cut.get('session_open_utc_ns')!r} vs re-derivado {open_ns}",
    )
    rep.add(
        "cut.naive_utc",
        _num(cut, "naive_utc_cut_ns") == EXPECTED_NAIVE_CUT_NS,
        f"manifiesto {cut.get('naive_utc_cut_ns')!r}",
    )
    rep.add(
        "cut.gap_2h",
        _num(cut, "naive_utc_cut_gap_seconds") == 7200,
        f"gap={cut.get('naive_utc_cut_gap_seconds')!r} s",
    )
    rep.add(
        "cut.trade_dates",
        _num(cut, "holdout_first_trade_date") == HOLDOUT_FIRST_TRADE_DATE
        and _num(cut, "research_max_trade_date") == RESEARCH_MAX_TRADE_DATE,
        f"{cut.get('holdout_first_trade_date')!r}/{cut.get('research_max_trade_date')!r}",
    )

    boundary = int(open_ns)
    late, bad_td = [], []
    for r in recut.get("files", []):
        tmk = _num(r, "ts_max_keep_ns")
        if tmk is not None and tmk >= boundary:
            late.append(r.get("file"))
        td = _num(r, "trade_date_max_keep")
        if td is not None and td > RESEARCH_MAX_TRADE_DATE:
            bad_td.append(r.get("file"))
    rep.add(
        "cut.ts_max_keep_bajo_frontera",
        not late,
        "todo ts_max_keep < apertura de sesion" + (f" | violan={late}" if late else ""),
    )
    rep.add(
        "cut.trade_date_max_keep",
        not bad_td,
        f"todos <= {RESEARCH_MAX_TRADE_DATE}" + (f" | violan={bad_td}" if bad_td else ""),
    )


def check_maintenance(rep: Report, recut: dict, mods: SimpleNamespace) -> list[str]:
    """Ticks conservados dentro de la pausa 16:00-17:00 CT: no es leak, es calidad."""
    import numpy as np

    flagged = []
    for r in recut.get("files", []):
        tmk = _num(r, "ts_max_keep_ns")
        if tmk is None:
            continue
        if bool(mods.sessions.is_maintenance_break(np.asarray([int(tmk)], dtype=np.int64))[0]):
            flagged.append(r.get("file"))
    rep.add(
        "calidad.pausa_mantenimiento",
        not flagged,
        "ningun ts_max_keep cae en la pausa 16:00-17:00 CT"
        if not flagged
        else f"ultimo tick conservado dentro de la pausa en {flagged} (mercado halted; revisar integridad)",
        level="WARN",
    )
    return flagged


# --------------------------------------------------------------------------- #
# 5. identidad de codigo (tolerante a CRLF, no a deriva)
# --------------------------------------------------------------------------- #
MODULE_PATHS = {
    "identity": pathlib.Path("edgelab") / "kaggle" / "identity.py",
    "inventory": pathlib.Path("edgelab") / "kaggle" / "inventory.py",
    "sessions_cme": pathlib.Path("edgelab") / "kaggle" / "sessions_cme.py",
    "instruments": pathlib.Path("edgelab") / "instruments.py",
}


def classify_code_identity(declared: dict, repo_bytes: bytes) -> tuple[str, str]:
    """-> (estado, detalle). LF_EXACTO / CRLF_NORMALIZADO / DERIVA."""
    lf = repo_bytes.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    got = declared.get("git_blob_sha1")
    variants = (
        ("LF_EXACTO", lf),
        ("CRLF_NORMALIZADO", crlf),
    )
    for estado, data in variants:
        if got == git_blob_sha1_bytes(data):
            det = f"blob {str(got)[:12]}... bytes={declared.get('bytes')} == {len(data)}"
            if declared.get("bytes") not in (None, len(data)):
                return "DERIVA", det + " (bytes no coinciden con la variante)"
            if declared.get("sha256") not in (None, sha256_bytes(data)):
                return "DERIVA", det + " (sha256 no coincide con la variante)"
            return estado, det
    return "DERIVA", (
        f"blob declarado {str(got)[:12]}... no es el del repo "
        f"({git_blob_sha1_bytes(lf)[:12]}... LF / {git_blob_sha1_bytes(crlf)[:12]}... CRLF)"
    )


def check_code_identity(
    rep: Report, recut: dict, repo_root: pathlib.Path
) -> dict[str, str]:
    ci = recut.get("code_identity") or {}
    estados: dict[str, str] = {}
    for name, rel in MODULE_PATHS.items():
        declared = ci.get(name)
        path = repo_root / rel
        if not isinstance(declared, dict):
            rep.add(f"codigo.{name}", False, "ausente en code_identity")
            continue
        if not path.exists():
            rep.add(f"codigo.{name}", False, f"no existe en el repo: {rel}", level="WARN")
            continue
        estado, detalle = classify_code_identity(declared, path.read_bytes())
        estados[name] = estado
        rep.add(f"codigo.{name}", estado != "DERIVA", f"{estado}: {detalle}")
    crlf = sorted(k for k, v in estados.items() if v == "CRLF_NORMALIZADO")
    if crlf:
        rep.add(
            "codigo.checkout_crlf",
            False,
            f"checkout Windows con CRLF en {crlf}: git_blob_sha1 del working tree "
            "nunca va a igualar el blob commiteado (falso positivo de deriva)",
            level="WARN",
        )
    return estados


# --------------------------------------------------------------------------- #
# 6. consistencia de estados y presupuesto honesto
# --------------------------------------------------------------------------- #
def check_status_consistency(rep: Report, recut: dict) -> None:
    precheck = bool(recut.get("precheck"))
    files = [r for r in recut.get("files", []) if isinstance(r, dict)]
    if precheck:
        bad = [
            r.get("file")
            for r in files
            if r.get("status") != "PRECHECK_ONLY" or r.get("output") is not None
        ]
        rep.add(
            "estado.precheck_sin_salidas",
            not bad,
            "todos PRECHECK_ONLY y output=null" + (f" | rotos={bad}" if bad else ""),
        )
        rep.add(
            "estado.precheck_no_escribio",
            _num(recut.get("totals") or {}, "recut") == 0
            and not recut.get("linked_clean"),
            "recut=0 y linked_clean vacio (precheck no escribe nada)",
        )
    else:
        bad = [
            r.get("file")
            for r in files
            if r.get("status") == "RECUT" and not r.get("output")
        ]
        rep.add(
            "estado.recut_con_salida",
            not bad,
            "todo RECUT declara output" + (f" | rotos={bad}" if bad else ""),
        )
    rep.add(
        "estado.sin_problemas",
        not recut.get("problems"),
        f"problems={recut.get('problems') or 'vacio'}",
    )
    rep.add(
        "estado.veredicto",
        recut.get("verdict") == "PASS",
        f"verdict={recut.get('verdict')!r}",
        level="WARN" if recut.get("verdict", "").startswith("ABSTAIN") else "FAIL",
    )


def project_after_recut(
    rep: Report, bundle: dict | None, recut: dict, mods: SimpleNamespace
) -> dict:
    """Presupuesto del arbol research-v2 REAL: limpios + re-cortados + metadata."""
    if bundle is None:
        return {}
    summary = bundle.get("summary") or {}
    clean_bytes = _num(summary, "total_bytes") or 0
    clean_files = len(
        [r for r in bundle.get("files", []) if isinstance(r, dict) and r.get("eligible")]
    )
    by_name = {r.get("file"): r for r in bundle.get("files", []) if isinstance(r, dict)}

    recut_bytes = 0
    recut_rows = 0
    for r in recut.get("files", []):
        b = by_name.get(r.get("file")) or {}
        src_bytes = _num(b, "bytes") or 0
        t, k = _num(r, "rows_total") or 0, _num(r, "rows_keep") or 0
        recut_rows += k
        if t:
            recut_bytes += int(round(src_bytes * (k / t)))

    total_bytes = clean_bytes + recut_bytes
    top_level = clean_files + len(recut.get("files", [])) + METADATA_FILES
    proj_summary = {
        "total_gib": round(total_bytes / (1024**3), 3),
        "total_rows": (_num(summary, "total_rows") or 0) + recut_rows,
        "total_bytes": total_bytes,
    }
    gates = mods.inventory.budget_gates(proj_summary, top_level_files=top_level)
    verdict = gates.get("verdict")
    rep.add(
        "presupuesto.research_v2",
        verdict == "PASS",
        f"{top_level} archivos top-level y {proj_summary['total_gib']} GiB "
        f"({proj_summary['total_rows']} ticks) -> {verdict}",
        level="WARN",
    )
    declared = ((recut.get("projected_bundle") or {}).get("budget") or {}).get("gates", {})
    declared_files = ((declared.get("top_level_files_contract") or {}).get("value"))
    if declared_files is not None and declared_files != top_level:
        rep.add(
            "presupuesto.proyeccion_del_manifiesto",
            False,
            f"el manifiesto proyecta {declared_files} archivos top-level pero el arbol "
            f"post-re-corte tiene {top_level}: la proyeccion de --precheck subestima",
            level="WARN",
        )
    return {
        "top_level_files": top_level,
        "summary": proj_summary,
        "budget": gates,
    }


# --------------------------------------------------------------------------- #
# orquestacion
# --------------------------------------------------------------------------- #
def verdict_from(rep: Report) -> str:
    fails = {r["id"].split(".")[0] for r in rep.failed("FAIL")}
    mapping = [
        ("seal", "FAIL_SEAL"),
        ("chain", "FAIL_CHAIN"),
        ("arit", "FAIL_ARITH"),
        ("cut", "FAIL_CUT"),
        ("estado", "FAIL_STATUS"),
        ("codigo", "FAIL_CODE"),
    ]
    for prefix, verdict in mapping:
        if prefix in fails:
            return verdict
    warns = {r["id"].split(".")[0] for r in rep.failed("WARN")}
    if "calidad" in warns:
        return "WARN_MAINTENANCE"
    if "presupuesto" in warns:
        return "WARN_BUDGET"
    return "PASS"


def run(
    bundle_path: pathlib.Path | None,
    recut_path: pathlib.Path,
    repo_root: pathlib.Path,
) -> tuple[str, Report, dict]:
    mods = load_repo_modules(repo_root)
    recut = json.loads(recut_path.read_text(encoding="utf-8"))
    bundle = (
        json.loads(bundle_path.read_text(encoding="utf-8"))
        if bundle_path is not None and bundle_path.exists()
        else None
    )

    rep = Report()
    if bundle is not None:
        check_seal(rep, bundle, "index_sha256", "bundle")
    check_seal(rep, recut, "recut_index_sha256", "recut")
    check_chain(rep, bundle, recut)
    check_arithmetic(rep, recut, bundle)
    check_cut(rep, recut, mods)
    check_status_consistency(rep, recut)
    check_code_identity(rep, recut, repo_root)
    check_maintenance(rep, recut, mods)
    projection = project_after_recut(rep, bundle, recut, mods)
    return verdict_from(rep), rep, projection


# --------------------------------------------------------------------------- #
# selftest
# --------------------------------------------------------------------------- #
MOD_LF = b'"""modulo de prueba."""\n\nX = 1\nY = 2\n'


def _seal(obj: dict, key: str) -> dict:
    obj = dict(obj)
    obj.pop(key, None)
    obj[key] = canonical_sha256_json(obj)
    return obj


def _fake_bundle() -> dict:
    files = [
        {
            "file": "AA_06-26_ticks.parquet",
            "asset": "AA",
            "rows": 100,
            "bytes": 1000,
            "sha256": "a" * 64,
            "eligible": True,
            "holdout_overlap": False,
        },
        {
            "file": "AA_09-26_ticks.parquet",
            "asset": "AA",
            "rows": 28,
            "bytes": 280,
            "sha256": "b" * 64,
            "eligible": False,
            "holdout_overlap": True,
        },
    ]
    return _seal(
        {
            "tool": EXPECTED_BUNDLE_TOOL,
            "schema_version": 2,
            "files": files,
            "summary": {"total_rows": 100, "total_bytes": 1000, "total_gib": 0.001},
            "verdict": "ABSTAIN_LICENSE",
        },
        "index_sha256",
    )


def _code_identity_fixture(root: pathlib.Path, variant: str) -> dict:
    """code_identity sintetico para los cuatro modulos, en la variante pedida."""
    out = {}
    for name, rel in MODULE_PATHS.items():
        data = (root / rel).read_bytes()
        lf = data.replace(b"\r\n", b"\n")
        if variant == "crlf":
            payload = lf.replace(b"\n", b"\r\n")
        elif variant == "alien":
            payload = MOD_LF
        else:
            payload = lf
        entry = {
            "path": f"D:/EdgeLab/{rel.as_posix()}",
            "bytes": len(payload),
            "git_blob_sha1": git_blob_sha1_bytes(payload),
            "sha256": sha256_bytes(payload),
        }
        if variant == "bytes_off":
            entry["bytes"] = len(payload) + 7
        out[name] = entry
    return out


def _fake_recut(bundle: dict, *, root: pathlib.Path, variant: str = "lf") -> dict:
    return _seal(
        {
            "tool": EXPECTED_RECUT_TOOL,
            "schema_version": 1,
            "backend": "pyarrow",
            "precheck": True,
            "source_index": {
                "tool": EXPECTED_BUNDLE_TOOL,
                "index_sha256": bundle["index_sha256"],
                "verdict": "ABSTAIN_LICENSE",
            },
            "code_identity": _code_identity_fixture(root, variant),
            "cut": {
                "holdout_first_trade_date": HOLDOUT_FIRST_TRADE_DATE,
                "research_max_trade_date": RESEARCH_MAX_TRADE_DATE,
                "session_open_utc_ns": EXPECTED_SESSION_OPEN_NS,
                "naive_utc_cut_ns": EXPECTED_NAIVE_CUT_NS,
                "naive_utc_cut_gap_seconds": 7200,
            },
            "files": [
                {
                    "file": "AA_09-26_ticks.parquet",
                    "output": None,
                    "status": "PRECHECK_ONLY",
                    "source_sha256": "b" * 64,
                    "rows_total": 28,
                    "rows_keep": 25,
                    "rows_drop": 3,
                    "rows_leaked_by_naive_utc_cut": 2,
                    # 20:59:59Z = 15:59:59 CT, justo antes de la pausa 16:00-17:00
                    "ts_max_keep_ns": EXPECTED_SESSION_OPEN_NS - 3601 * 10**9,
                    "trade_date_max_keep": RESEARCH_MAX_TRADE_DATE,
                }
            ],
            "linked_clean": [],
            "problems": [],
            "totals": {
                "targets": 1,
                "recut": 0,
                "rows_total_source": 28,
                "rows_keep": 25,
                "rows_drop": 3,
                "rows_leaked_by_naive_utc_cut": 2,
            },
            "projected_bundle": {
                "budget": {
                    "gates": {"top_level_files_contract": {"value": 5}},
                    "verdict": "ABSTAIN_CAPACITY",
                }
            },
            "verdict": "PASS",
        },
        "recut_index_sha256",
    )


def selftest() -> int:
    fallas: list[str] = []
    checks = 0

    def chk(nombre: str, cond: bool) -> None:
        nonlocal checks
        checks += 1
        if not cond:
            fallas.append(nombre)
            print(f"  FALLA {nombre}")

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        # repo minimo: modulos reales + un modulo de prueba
        (root / "edgelab" / "kaggle").mkdir(parents=True)
        for name, rel in MODULE_PATHS.items():
            src = REPO_ROOT / rel
            if src.exists():
                (root / rel).write_bytes(src.read_bytes())
        sess = root / MODULE_PATHS["sessions_cme"]
        real_sessions = sess.read_bytes()
        blob_lf = git_blob_sha1_bytes(real_sessions.replace(b"\r\n", b"\n"))
        crlf = real_sessions.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        blob_crlf = git_blob_sha1_bytes(crlf)

        bundle = _fake_bundle()
        recut = _fake_recut(bundle, root=root, variant="lf")
        bp, rp = root / "bundle.json", root / "recut.json"

        def escribir(b, r):
            bp.write_text(json.dumps(b, indent=2), encoding="utf-8")
            rp.write_text(json.dumps(r, indent=2), encoding="utf-8")

        # --- S1: caso sano
        escribir(bundle, recut)
        v, rep, proj = run(bp, rp, root)
        chk("S1 caso sano -> PASS o WARN_BUDGET", v in ("PASS", "WARN_BUDGET"))
        chk("S1 sin FALLAS", not rep.failed("FAIL"))
        chk("S1 frontera re-derivada de tzdata", any(r["id"] == "cut.rederivado_tzdata" and r["ok"] for r in rep.rows))
        chk("S1 proyeccion cuenta 1+1+4=6", proj.get("top_level_files") == 6)

        # --- S2: sello del recut roto
        malo = dict(recut)
        malo["totals"] = dict(malo["totals"])
        escribir(bundle, malo | {"recut_index_sha256": "0" * 64})
        v, rep, _ = run(bp, rp, root)
        chk("S2 sello recut adulterado -> FAIL_SEAL", v == "FAIL_SEAL")

        # --- S3: sello del bundle roto
        escribir(bundle | {"index_sha256": "1" * 64}, recut)
        v, rep, _ = run(bp, rp, root)
        chk("S3 sello bundle adulterado -> FAIL_SEAL", v == "FAIL_SEAL")

        # --- S4: cadena rota (el recut apunta a otro indice)
        otro = _seal(
            {k: v2 for k, v2 in bundle.items() if k != "index_sha256"}
            | {"verdict": "PASS"},
            "index_sha256",
        )
        escribir(otro, recut)
        v, rep, _ = run(bp, rp, root)
        chk("S4 sello cruzado no coincide -> FAIL_CHAIN", v == "FAIL_CHAIN")

        # --- S5: sha256 de origen distinto al sellado
        r5 = json.loads(json.dumps(recut))
        r5["files"][0]["source_sha256"] = "c" * 64
        escribir(bundle, _seal(r5, "recut_index_sha256"))
        v, rep, _ = run(bp, rp, root)
        chk("S5 source_sha256 != sellado -> FAIL_CHAIN", v == "FAIL_CHAIN")

        # --- S6: aritmetica adulterada
        r6 = json.loads(json.dumps(recut))
        r6["files"][0]["rows_keep"] = 26
        escribir(bundle, _seal(r6, "recut_index_sha256"))
        v, rep, _ = run(bp, rp, root)
        chk("S6 keep+drop != total -> FAIL_ARITH", v == "FAIL_ARITH")

        # --- S7: particion del censo rota
        r7 = json.loads(json.dumps(recut))
        r7["files"][0]["rows_total"] = 30
        r7["files"][0]["rows_drop"] = 5
        r7["totals"]["rows_total_source"] = 30
        r7["totals"]["rows_drop"] = 5
        escribir(bundle, _seal(r7, "recut_index_sha256"))
        v, rep, _ = run(bp, rp, root)
        chk("S7 censo no particiona -> FAIL_CHAIN o FAIL_ARITH", v in ("FAIL_CHAIN", "FAIL_ARITH"))

        # --- S8: ts_max_keep por encima de la frontera
        r8 = json.loads(json.dumps(recut))
        r8["files"][0]["ts_max_keep_ns"] = EXPECTED_SESSION_OPEN_NS
        escribir(bundle, _seal(r8, "recut_index_sha256"))
        v, rep, _ = run(bp, rp, root)
        chk("S8 ts_max_keep >= frontera -> FAIL_CUT", v == "FAIL_CUT")

        # --- S9: trade_date de holdout conservado
        r9 = json.loads(json.dumps(recut))
        r9["files"][0]["trade_date_max_keep"] = HOLDOUT_FIRST_TRADE_DATE
        escribir(bundle, _seal(r9, "recut_index_sha256"))
        v, rep, _ = run(bp, rp, root)
        chk("S9 trade_date_max_keep en holdout -> FAIL_CUT", v == "FAIL_CUT")

        # --- S10: precheck que declara salidas
        r10 = json.loads(json.dumps(recut))
        r10["files"][0]["output"] = "E:/x.parquet"
        escribir(bundle, _seal(r10, "recut_index_sha256"))
        v, rep, _ = run(bp, rp, root)
        chk("S10 precheck con output -> FAIL_STATUS", v == "FAIL_STATUS")

        # --- S11: CRLF no es deriva
        r11 = _fake_recut(bundle, root=root, variant="crlf")
        escribir(bundle, r11)
        v, rep, _ = run(bp, rp, root)
        chk("S11 CRLF no dispara FAIL_CODE", v != "FAIL_CODE")
        chk(
            "S11 CRLF queda etiquetado como aviso",
            any(r["id"] == "codigo.checkout_crlf" and not r["ok"] for r in rep.rows),
        )
        chk(
            "S11 modulo clasificado CRLF_NORMALIZADO",
            any(
                r["id"] == "codigo.sessions_cme" and r["ok"] and "CRLF_NORMALIZADO" in r["detail"]
                for r in rep.rows
            ),
        )

        # --- S12: deriva real si dispara
        r12 = _fake_recut(bundle, root=root, variant="alien")
        escribir(bundle, r12)
        v, rep, _ = run(bp, rp, root)
        chk("S12 blob ajeno -> FAIL_CODE", v == "FAIL_CODE")

        # --- S13: bytes que no cuadran con la variante
        r13 = _fake_recut(bundle, root=root, variant="bytes_off")
        escribir(bundle, r13)
        v, rep, _ = run(bp, rp, root)
        chk("S13 bytes inconsistentes -> FAIL_CODE", v == "FAIL_CODE")

        # --- S14: pausa de mantenimiento marcada como aviso
        r14 = json.loads(json.dumps(recut))
        r14["files"][0]["ts_max_keep_ns"] = EXPECTED_SESSION_OPEN_NS - 1 * 10**9
        escribir(bundle, _seal(r14, "recut_index_sha256"))
        v, rep, _ = run(bp, rp, root)
        chk(
            "S14 ultimo tick en la pausa -> aviso, no falla",
            any(r["id"] == "calidad.pausa_mantenimiento" and not r["ok"] for r in rep.rows)
            and not rep.failed("FAIL"),
        )

        # --- S15: sin bundle, el recut igual se verifica pero avisa
        v, rep, _ = run(None, rp, root)
        chk(
            "S15 sin bundle -> aviso de cadena incompleta",
            any(r["id"] == "chain.bundle.presente" and not r["ok"] for r in rep.rows),
        )

    print(f"\nself-test: {len(fallas)} fallas, {checks} checks ok")
    return 1 if fallas else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verifica los indices sellados del bundle.")
    ap.add_argument("--bundle", default=None, help="ruta a bundle_index.json")
    ap.add_argument("--recut", default=None, help="ruta a recut_index.json")
    ap.add_argument("--repo-root", default=str(REPO_ROOT))
    ap.add_argument("--json-out", default=None, help="escribe el reporte en JSON")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.recut:
        ap.error("se requiere --recut (o --selftest)")

    repo_root = pathlib.Path(args.repo_root).resolve()
    recut_path = pathlib.Path(args.recut).resolve()
    bundle_path = pathlib.Path(args.bundle).resolve() if args.bundle else None

    verdict, rep, projection = run(bundle_path, recut_path, repo_root)
    print(f"{TOOL_ID}  repo={repo_root}")
    print(f"recut={recut_path}")
    print(f"bundle={bundle_path}\n")
    print(rep.render())
    print(
        f"\n{rep.n_ok}/{len(rep.rows)} chequeos ok  |  "
        f"{len(rep.failed('FAIL'))} fallas  |  {len(rep.failed('WARN'))} avisos"
    )
    print(f"VEREDICTO: {verdict}")
    if projection:
        b = projection["budget"]
        print(
            f"research-v2 proyectado: {projection['top_level_files']} archivos top-level, "
            f"{projection['summary']['total_gib']} GiB, "
            f"{projection['summary']['total_rows']} ticks -> {b.get('verdict')}"
        )
    if args.json_out:
        payload = {
            "tool": TOOL_ID,
            "schema_version": SCHEMA_VERSION,
            "verdict": verdict,
            "checks": rep.rows,
            "projection": projection,
        }
        pathlib.Path(args.json_out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return 0 if verdict.startswith(("PASS", "WARN")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
