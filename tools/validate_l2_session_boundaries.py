#!/usr/bin/env python3
r"""Valida la continuidad entre sesiones L2 consecutivas de un mismo instrumento+contrato.

Motivacion (conversacion con el auditor externo, 2026-09-22): un downloader puede confirmar
que el archivo `.nrd`/CSV de un dia llego, pero eso NO prueba que el libro se pueda
reconstruir sin discontinuidad real contra el dia anterior. Diez descargas de fechas
consecutivas no forman automaticamente diez sesiones continuas -- hay que medirlo.

Que valida, por cada PAR de sesiones consecutivas que aparecen en `--base/manifests/*.manifest.json`
(el orden lo da la fecha, no el calendario -- si falta un dia en disco, el par salta al
siguiente disponible y eso tambien queda registrado):

1. INVERSION DE RELOJ: `last_ts_us(D)` tiene que ser <= `first_ts_us(D+1)`, EXCEPTO un
   solapamiento negativo chico (>= -30s) en una frontera que de otro modo seria continua --
   eso es `EXPECTED_BOOTSTRAP_OVERLAP` (`continuity_status=REVIEW_MINOR_OVERLAP`), causa raiz
   medida fila a fila en docs/research/SOLAPAMIENTO_FRONTERA_SESIONES_L2_20260922.md: la
   rafaga de bootstrap del dia nuevo queda sellada con la hora nominal de arranque, no con
   hora de llegada real, y puede quedar "antes" de la cola genuina del dia anterior sin que
   ningun evento este duplicado. Cualquier otro gap negativo sigue siendo HARD FAIL
   (`FAIL_CLOCK_INVERSION`) -- esto no relaja el chequeo en general.
2. CLASIFICACION DEL GAP (HEURISTICA, no un calendario CME certificado -- para eso existe
   `edgelab/data/cme_equity_index_calendar.py`, que es de indices, no metales, y no modela
   el gap intradiario). Se mide contra el patron EMPIRICO observado en GC 08-26
   (docs/research/RESOLUCION_RELOJ_GC_L2_20260922.md): archivos lunes-jueves consecutivos
   empalman con gap < 60s; el cierre de semana (viernes -> proximo dia disponible) da un
   gap del orden de decenas de horas. Cualquier gap que no calce con ninguno de esos
   patrones queda `GAP_UNCLASSIFIED_REVIEW_NEEDED` -- NUNCA se acepta en silencio.
3. BOOTSTRAP DEL LIBRO DE D+1 (opcional, `--skip-book-check` para saltarlo): corre
   `build_l2_viewer_bundle.build()` fail-closed sobre D+1 y expone su `book_status`. Una
   frontera no puede declararse continua si el libro del lado derecho no reconstruye.

Salida: `<out>/boundaries/<D>__<D+1>.json`, un manifest por frontera con el esquema que
describio el auditor (left_session, right_session, gap_seconds, gap_classification,
right_book_bootstrap, continuity_status), mas un resumen agregado en stdout.

Target-free. No abre outcomes, P&L ni holdout -- esto es integridad estructural, no senal.

    .venv\\Scripts\\python tools\\validate_l2_session_boundaries.py --base E:\\DatosNT8\\gc_aug26_canonical_parquets ^
        --instrument GC --contract "GC 08-26" --out runs\\l2_continuity\\gc_08-26
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

FAIL_CLOCK_INVERSION = "FAIL_CLOCK_INVERSION"
EXPECTED_CONTINUOUS = "EXPECTED_CONTINUOUS"
EXPECTED_WEEKEND = "EXPECTED_WEEKEND"
EXPECTED_BOOTSTRAP_OVERLAP = "EXPECTED_BOOTSTRAP_OVERLAP"
GAP_UNCLASSIFIED = "GAP_UNCLASSIFIED_REVIEW_NEEDED"

# Umbrales HEURISTICOS calibrados contra el patron real medido en GC 08-26 (30 sesiones,
# ver RESOLUCION_RELOJ_GC_L2_20260922.md): lunes-jueves consecutivos empalman en 0.1-2.2s;
# el cierre de semana da un gap de decenas de horas. Margenes generosos a proposito -- lo
# que importa es distinguir "empalme normal" y "fin de semana" de "cualquier otra cosa".
CONTINUOUS_GAP_MAX_S = 300.0            # 5 min de margen sobre el 2.2s real observado
WEEKEND_GAP_MIN_S = 6 * 3600.0          # piso generoso: un fin de semana real nunca es < 6h
WEEKEND_GAP_MAX_S = 4 * 24 * 3600.0     # techo generoso: cubre un feriado largo pegado al finde

# Solapamiento NEGATIVO chico en fronteras lunes-jueves-domingo->siguiente: causa raiz medida
# y documentada en docs/research/SOLAPAMIENTO_FRONTERA_SESIONES_L2_20260922.md -- la rafaga de
# bootstrap (ADD) que reconstruye el libro al arrancar el archivo nuevo queda sellada con la
# hora NOMINAL de arranque de sesion, no con una hora de llegada real, y puede quedar "antes"
# de la cola genuina de actividad del dia anterior sin que ningun dato este mal (verificado
# fila a fila: los precios de la cola de D y la cabeza de D+1 NO coinciden -- no hay evento
# duplicado). Rango medido: -4.0s a -7.6s en GC 12-26 (5 fronteras) + -5.68s en GC 08-26.
# -30s es ~4-7x mas laxo que lo medido -- margen, no ajuste para que pasen los tests.
BOOTSTRAP_OVERLAP_MIN_S = -30.0


def _session_ts_bounds(base: Path, session: str) -> tuple[int, int]:
    """(first_ts_us, last_ts_us) combinando l1_quotes + l2_depth de una sesion."""
    parts = []
    for sub in ("l2_depth", "l1_quotes"):
        p = base / sub / f"{session}.parquet"
        if p.exists():
            parts.append(pq.read_table(p, columns=["ts_us"]).to_pandas()["ts_us"])
    if not parts:
        raise FileNotFoundError(f"no hay l1_quotes ni l2_depth para la sesion {session} en {base}")
    allts = pd.concat(parts)
    return int(allts.min()), int(allts.max())


def _session_date(session: str) -> date:
    return datetime.strptime(session, "%Y%m%d").date()


def classify_gap(day_before: date, day_after: date, gap_seconds: float) -> str:
    """Ver docstring del modulo: heuristica, no calendario CME certificado.

    `_CONTINUOUS_DOW` incluye domingo: medido contra los 30 dias reales de GC 08-26, un
    archivo de domingo tambien cubre el ciclo completo 01:00-00:59:59 ART y empalma con el
    lunes en 0-2s, igual que lunes-jueves entre si. La version anterior de esta regla solo
    contemplaba lunes-jueves y marcaba los 5 empalmes domingo->lunes reales como
    GAP_UNCLASSIFIED -- no estaba mal (nunca acepto algo en silencio), pero subcubria un
    caso legitimo que si se puede clasificar con evidencia.

    Un gap NEGATIVO chico (>= BOOTSTRAP_OVERLAP_MIN_S) en una frontera que de otro modo
    calificaria como EXPECTED_CONTINUOUS es EXPECTED_BOOTSTRAP_OVERLAP, no un fail duro --
    causa raiz medida en docs/research/SOLAPAMIENTO_FRONTERA_SESIONES_L2_20260922.md. Un
    gap negativo mas alla de ese margen, o en cualquier otra frontera, sigue siendo
    FAIL_CLOCK_INVERSION: esto NO relaja el chequeo en general, solo reconoce el patron
    especifico ya verificado fila a fila (no hay evento duplicado)."""
    dow_before = day_before.weekday()   # 0=lunes ... 6=domingo
    calendar_days = (day_after - day_before).days
    _CONTINUOUS_DOW = (0, 1, 2, 3, 6)   # lunes-jueves y domingo: el dia siguiente empalma liso
    would_be_continuous = calendar_days == 1 and dow_before in _CONTINUOUS_DOW
    if gap_seconds < 0:
        if would_be_continuous and gap_seconds >= BOOTSTRAP_OVERLAP_MIN_S:
            return EXPECTED_BOOTSTRAP_OVERLAP
        return FAIL_CLOCK_INVERSION
    if would_be_continuous and gap_seconds <= CONTINUOUS_GAP_MAX_S:
        return EXPECTED_CONTINUOUS
    if dow_before == 4 and WEEKEND_GAP_MIN_S <= gap_seconds <= WEEKEND_GAP_MAX_S:
        return EXPECTED_WEEKEND
    return GAP_UNCLASSIFIED


def _book_bootstrap_status(base: Path, session: str, tick_size: float) -> str:
    """`build()` fail-closed sobre la sesion D+1. Solo el book_status importa aca -- no se
    corren detectores/heatmap, es caro hacerlo si no hace falta (por eso --skip-book-check)."""
    from tools.build_l2_viewer_bundle import build, BookAbstain
    l1p, l2p = base / "l1_quotes" / f"{session}.parquet", base / "l2_depth" / f"{session}.parquet"
    try:
        _, _, _, val, _, _, _ = build(l1p, l2p, snap_seconds=5, tick_size=tick_size, exploratory=True)
        return val["book_status"]
    except BookAbstain as e:
        return e.status


def validate_boundaries(base: Path, out_dir: Path, tick_size: float, *, skip_book_check: bool = False) -> dict:
    man_dir = base / "manifests"
    sessions = sorted(p.stem.replace(".manifest", "") for p in man_dir.glob("*.manifest.json"))
    if len(sessions) < 2:
        raise SystemExit(f"se necesitan al menos 2 sesiones convertidas en {man_dir}, hay {len(sessions)}")

    out_dir.mkdir(parents=True, exist_ok=True)
    boundaries_dir = out_dir / "boundaries"
    boundaries_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for left, right in zip(sessions, sessions[1:]):
        _, left_last = _session_ts_bounds(base, left)
        right_first, _ = _session_ts_bounds(base, right)
        gap_s = (right_first - left_last) / 1_000_000.0
        d0, d1 = _session_date(left), _session_date(right)
        classification = classify_gap(d0, d1, gap_s)

        right_bootstrap = "SKIPPED" if skip_book_check else _book_bootstrap_status(base, right, tick_size)

        if classification == FAIL_CLOCK_INVERSION:
            status = "FAIL_CLOCK_INVERSION"
        elif classification == GAP_UNCLASSIFIED:
            status = "REVIEW_GAP_UNCLASSIFIED"
        elif classification == EXPECTED_BOOTSTRAP_OVERLAP:
            status = "REVIEW_MINOR_OVERLAP"
        elif not skip_book_check and right_bootstrap != "PASS":
            status = "REVIEW_BOOK_BOOTSTRAP"
        else:
            status = "PASS"

        record = dict(
            left_session=left, right_session=right,
            left_last_ts_us=left_last, right_first_ts_us=right_first,
            gap_seconds=gap_s, gap_classification=classification,
            same_contract=True,        # implicito: ambas viven bajo el mismo --base
            right_book_bootstrap=right_bootstrap,
            continuity_status=status,
        )
        results.append(record)
        (boundaries_dir / f"{left}__{right}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    summary = dict(
        schema="edgelab_l2_continuity_report_v1",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        base=str(base), sessions_found=len(sessions), boundaries_checked=len(results),
        pass_count=sum(1 for r in results if r["continuity_status"] == "PASS"),
        review_count=sum(1 for r in results if r["continuity_status"].startswith("REVIEW")),
        fail_count=sum(1 for r in results if r["continuity_status"].startswith("FAIL")),
        boundaries=results,
    )
    (out_dir / "continuity_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True, help="carpeta con l1_quotes/, l2_depth/ y manifests/")
    ap.add_argument("--instrument", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-book-check", action="store_true",
                    help="no correr build() fail-closed sobre cada sesion derecha (mas rapido, menos estricto)")
    a = ap.parse_args(argv)

    man_dir = a.base / "manifests"
    first_man = sorted(man_dir.glob("*.manifest.json"))[0]
    tick_size = float(json.loads(first_man.read_text(encoding="utf-8"))["conversion"]["tick_size"])

    summary = validate_boundaries(a.base, a.out, tick_size, skip_book_check=a.skip_book_check)
    print(json.dumps(dict(instrument=a.instrument, contract=a.contract,
                          sessions_found=summary["sessions_found"], boundaries_checked=summary["boundaries_checked"],
                          pass_count=summary["pass_count"], review_count=summary["review_count"],
                          fail_count=summary["fail_count"])))
    return 1 if summary["fail_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
