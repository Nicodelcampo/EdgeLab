"""HOLDOUT-A4 (Nico, 2026-10-22): una sola frontera del holdout para todo el repo — la sesión CME del 2026-10-01.

Fuente de verdad: `edgelab/holdout.py`. Los scripts que corren sueltos en kernels de Kaggle pueden llevar una copia literal
(no tienen el paquete); este test exige que toda copia valga lo mismo y que no reaparezca ninguna otra fecha de holdout.
El corte FÍSICO de research-v2 / release v1 (2026-06-30 22:00 UTC) no es un holdout: se nombra como corte y sólo se acepta
en los artefactos que lo describen.
"""
import re
import subprocess
from pathlib import Path

from edgelab import holdout as H
from edgelab.research import holdout_guard

ROOT = Path(__file__).resolve().parents[1]
VALIDOS = {H.HOLDOUT_PRIMERA_SESION, str(H.HOLDOUT_PRIMERA_SESION_INT), H.HOLDOUT_APERTURA_UTC_ISO, H.HOLDOUT_APERTURA_UTC_ISO + "Z",
           str(H.HOLDOUT_APERTURA_UTC_NS), "1_790_805_600_000_000_000", "1_790_805_600"}   # la última, como segundos `* 1_000_000_000`
ASIGNACION = re.compile(r"^\s*([A-Z_]*HOLD[A-Z_]*)\s*=\s*(?:pd\.Timestamp\()?([\"']?)([0-9_:\-T]{8,})\2", re.M)


def _py_vivos():
    out = subprocess.run(["git", "ls-files", "edgelab", "tools", "validation", "sidecar"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    return [ROOT / p for p in out if p.endswith(".py")]


def test_la_guarda_y_el_autopilot_usan_la_frontera_unica():
    import edgelab.autopilot as ap
    assert holdout_guard.HOLDOUT_START_ISO == H.HOLDOUT_APERTURA_UTC_ISO
    assert holdout_guard.L2_HOLDOUT_START_ISO == H.HOLDOUT_APERTURA_UTC_ISO          # L2 ya no tiene frontera propia
    assert ap.HOLDOUT_FIRST_TRADE_DATE == H.HOLDOUT_PRIMERA_SESION
    holdout_guard.verificar_sello()
    import datetime as dt
    assert dt.datetime.fromtimestamp(H.HOLDOUT_APERTURA_UTC_S, dt.timezone.utc).isoformat() == "2026-09-30T22:00:00+00:00"


def test_ninguna_constante_de_holdout_vale_otra_fecha():
    malas = []
    for p in _py_vivos():
        for m in ASIGNACION.finditer(p.read_text(encoding="utf-8", errors="replace")):
            if m.group(3) not in VALIDOS and "END" not in m.group(1):      # el FIN del holdout (2026-12-31) es otro concepto
                malas.append(f"{p.relative_to(ROOT)}: {m.group(1)} = {m.group(3)}")
    assert malas == [], "constantes de holdout con otra fecha (HOLDOUT-A4 exige 2026-10-01):\n" + "\n".join(malas)


def test_no_quedan_las_fronteras_viejas_como_holdout():
    """2026-11-01 (L2) y 2026-07-01 no pueden aparecer en una línea que hable del holdout como su frontera."""
    patron = re.compile(r"(?i)holdout[^\n]{0,60}(2026-07-01|20260701|2026-11-01|2026-06-30T22)")
    # `holdout_boundary_*` es nombre de campo de manifiestos YA PUBLICADOS (inmutables): su valor es el corte físico del dataset.
    permitido = re.compile(r"(?i)corte|fisic|físic|frontera vieja|antes de HOLDOUT-A4|HOLDOUT-A4|era el sello|holdout_boundary_(ns|utc)")
    malas = []
    for p in _py_vivos():
        for i, l in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if patron.search(l) and not permitido.search(l):
                malas.append(f"{p.relative_to(ROOT)}:{i}: {l.strip()[:120]}")
    assert malas == [], "\n".join(malas)


def test_trade_date_y_ns():
    assert H.es_holdout_trade_date("2026-10-01") and not H.es_holdout_trade_date(20260930)
    assert H.es_holdout_ns(H.HOLDOUT_APERTURA_UTC_NS) and not H.es_holdout_ns(H.HOLDOUT_APERTURA_UTC_NS - 1)
    assert H.CORTE_FISICO_RESEARCH_V2_UTC_NS < H.HOLDOUT_APERTURA_UTC_NS


def test_el_visor_js_usa_la_misma_frontera():
    """El visor no puede importar Python: sus copias (density_field.js y el HTML) deben valer lo mismo."""
    pat = re.compile(r"\b(?:const|var|let)\s+([A-Z_]*HOLD[A-Z_]*)\s*=\s*([0-9_]+)")
    malas = []
    for rel in ("viewer/nt8_bridge/density_field.js", "viewer/nt8_bridge/index.html"):
        for m in pat.finditer((ROOT / rel).read_text(encoding="utf-8")):
            if m.group(2).replace("_", "") not in {str(H.HOLDOUT_APERTURA_UTC_NS), str(H.HOLDOUT_APERTURA_UTC_S), str(H.HOLDOUT_APERTURA_UTC_S * 1000)}:
                malas.append(f"{rel}: {m.group(1)} = {m.group(2)}")
    assert malas == [], malas
