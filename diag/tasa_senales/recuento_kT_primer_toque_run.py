# -*- coding: utf-8 -*-
"""Mide `f` de BigTrap2 con primer toque + excursión/retorno.

La salida contiene las dos composiciones outcome-free que pueden diferir:

* orden A: `sep_min` sobre todos los primeros toques, luego `k_T > 0` y retorno;
* orden B: `k_T > 0` y retorno, luego `sep_min` sobre entradas realizables.

No lee P&L, TP/SL, horizonte posterior al retorno ni outcomes. El firewall de
`dias_research()` y `corte_del_sello()` es obligatorio.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, CLASE_KERNEL, LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART,
    bars_mod, corte_del_sello, dias_research, git_head,
    pd, sesion_ct, ticks_mod,
)
from diag.tasa_senales.recuento_kT import eventos_kT  # noqa: E402
from diag.tasa_senales.recuento_kT_primer_toque import seleccionar_dos_ordenes  # noqa: E402
from edgelab.research.first_touch_decongestion import (  # noqa: E402
    FIRST_TOUCH_SEP_MINUTES, decongest_first_touch_events,
)
from edgelab.research.first_touch_population import extract_first_touch_events  # noqa: E402

INDICADOR = "BigTrap2"
T = 34
SALIDA = Path(__file__).resolve().parent / "recuento_kT_primer_toque.json"
SCHEMA_VERSION = "recuento_kT_primer_toque_v1"


def _cargar_y_candidatos(archivo, fechas):
    """Devuelve primeros toques enriquecidos con validez geométrica outcome-free."""
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                    + pd.Timedelta(days=1))
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())
    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / archivo),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value),
    )
    ts = np.asarray(tk.ts_ns)
    px = np.asarray(tk.price_ticks).astype(np.float64)
    sq = np.asarray(tk.sequence)
    if not bool((np.diff(sq) > 0).all()):
        return {"estado": "ABSTAIN", "motivo": "sequence no es orden total"}

    bars = bars_mod.build_time_bars(tk, 1)
    fp = bars_mod.build_footprints(tk, bars)
    resultado = REGISTRY[INDICADOR].run(tk, bars, fp, chart_tz=TZ_CHART)
    zones = {z["id"]: z for z in resultado.get("zones") or [] if z.get("id")}
    toques = extract_first_touch_events(resultado)
    elegibles = set(fechas)
    candidates, violations = [], []
    counters = Counter()

    for row in toques:
        zone_id = row["zone_id"]
        zone = zones.get(zone_id)
        if zone is None:
            raise RuntimeError("primer toque sin zona: %s" % zone_id)
        created_bar, touch_bar = row["created_bar"], row["first_touch_bar"]
        if not created_bar < touch_bar:
            violations.append({"zone_id": zone_id, "rule": "created_bar < touch_bar"})
            continue
        if created_bar < 0 or created_bar >= len(bars.end_ns):
            raise RuntimeError("created_bar invalida: %s" % zone_id)
        disp = int(bars.end_ns[created_bar])
        i0 = int(np.searchsorted(ts, disp, side="right"))
        ended_ms = zone.get("ended_ms")
        i1 = (int(np.searchsorted(ts, int(ended_ms) * 1_000_000, side="right"))
              if ended_ms is not None else len(ts))
        por_t, _dentro = eventos_kT(
            px, zone["bottom"] / tk.tick_size, zone["top"] / tk.tick_size,
            i0, min(i1, len(ts)), [T],
        )
        if por_t is None:
            counters["sin_tramo"] += 1
            valid, k, j = False, None, None
        else:
            k, j = por_t[T]
            valid = k is not None and k > 0 and j is not None and j > k
            if k is None:
                counters["nunca_se_aleja"] += 1
            elif k == 0:
                counters["k_cero"] += 1
            elif j is None:
                counters["sin_retorno"] += 1
            else:
                counters["retorno_valido"] += 1

        session = sesion_ct(row["first_touch_ms"] * 1_000_000)
        if session not in elegibles:
            counters["toque_fuera_universo"] += 1
            continue
        candidates.append({
            "zone_id": archivo + "::" + zone_id,
            "archive": archivo,
            "session_date": session,
            "created_ms": row["created_ms"],
            "first_touch_ms": row["first_touch_ms"],
            "created_bar": created_bar,
            "touch_bar": touch_bar,
            "k_T": k,
            "j_retorno": j,
            "valid": valid,
            "outcomes_accessed": False,
        })

    return {
        "estado": "OK", "candidates": candidates, "counters": dict(counters),
        "violations": violations, "zones": len(zones), "first_touches": len(toques),
    }


def _summary(selection, session_count):
    rows = selection["events"]
    per_session = Counter(row["session_date"] for row in rows)
    return {
        "events": len(rows),
        "events_per_session": round(len(rows) / session_count, 6),
        "sessions_with_event": len(per_session),
        "per_session": dict(sorted(per_session.items())),
    }


def hash_sources(paths):
    """Huella estable de todas las fuentes que pueden cambiar esta medición."""
    digest = hashlib.sha256()
    for source in sorted((Path(p).resolve() for p in paths), key=lambda p: str(p)):
        digest.update(str(source).encode("utf-8"))
        digest.update(source.read_bytes())
    return digest.hexdigest()


def sources_medicion():
    indicator_file = Path(REGISTRY[INDICADOR].__file__).resolve()
    return [
        Path(__file__).resolve(),
        Path(eventos_kT.__code__.co_filename).resolve(),
        Path(seleccionar_dos_ordenes.__code__.co_filename).resolve(),
        Path(extract_first_touch_events.__code__.co_filename).resolve(),
        Path(decongest_first_touch_events.__code__.co_filename).resolve(),
        Path(dias_research.__code__.co_filename).resolve(),
        indicator_file,
    ]


def resumen_archivo(measured, selection=None, *, session_count=None):
    """Conserva conteos auditables sin volcar cada zona al artefacto Git."""
    summary = {
        "estado": measured["estado"],
        "candidate_count": len(measured["candidates"]),
        "valid_before_sep_count": sum(row["valid"] for row in measured["candidates"]),
        "counters": measured["counters"],
        "violations": measured["violations"],
        "zones": measured["zones"],
        "first_touches": measured["first_touches"],
    }
    if selection is not None:
        if session_count is None:
            raise ValueError("session_count es obligatorio con selection")
        summary["orden_a"] = _summary(selection["orden_a"], session_count)
        summary["orden_b"] = _summary(selection["orden_b"], session_count)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(SALIDA))
    ap.add_argument("--limite-sesiones", type=int, default=None)
    args = ap.parse_args(argv)

    dias, universe_report = dias_research()
    if args.limite_sesiones is not None:
        dias = dias[:args.limite_sesiones]
    by_archive = {}
    for day in dias:
        by_archive.setdefault(day["archivo"], []).append(day["fecha"])
    plan = [(archive, sorted(fechas)) for archive, fechas in sorted(by_archive.items())]
    max_date = max(date for _archive, fechas in plan for date in fechas)
    assert max_date <= MAX_FECHA, "FIREWALL: %s > %s" % (max_date, MAX_FECHA)
    session_count = sum(len(fechas) for _archive, fechas in plan)
    print("universo: %d sesiones | max %s <= %s | %s T=%d"
          % (session_count, max_date, MAX_FECHA, INDICADOR, T), flush=True)

    all_candidates, per_archive, all_violations = [], {}, []
    for archive, fechas in plan:
        started = time.time()
        print("== %s : %d sesiones" % (archive, len(fechas)), flush=True)
        measured = _cargar_y_candidatos(archive, fechas)
        if measured["estado"] != "OK":
            raise RuntimeError("%s: %s" % (archive, measured["motivo"]))
        selection_archive = seleccionar_dos_ordenes(
            measured["candidates"],
            session_date_of_ms=lambda ms: sesion_ct(ms * 1_000_000),
            sep_minutes=FIRST_TOUCH_SEP_MINUTES,
        )
        per_archive[archive] = resumen_archivo(
            measured, selection_archive, session_count=len(fechas)
        )
        all_candidates.extend(measured["candidates"])
        all_violations.extend(measured["violations"])
        print("   primeros=%d validos=%d (%.1fs)" % (
            len(measured["candidates"]), sum(x["valid"] for x in measured["candidates"]),
            time.time() - started), flush=True)

    if all_violations:
        raise RuntimeError("FIREWALL: %d violaciones temporales" % len(all_violations))
    both = seleccionar_dos_ordenes(
        all_candidates, session_date_of_ms=lambda ms: sesion_ct(ms * 1_000_000),
        sep_minutes=FIRST_TOUCH_SEP_MINUTES,
    )
    for label, value in both.items():
        for row in value["events"]:
            if not (row["created_bar"] < row["touch_bar"] and row["k_T"] > 0
                    and row["j_retorno"] > row["k_T"]):
                raise RuntimeError("FIREWALL: invariante fallida %s" % label)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "purpose": "f con primeros toques y excursion+retorno, dos ordenes",
        "indicator": INDICADOR, "T": T,
        "sep_minutes": FIRST_TOUCH_SEP_MINUTES,
        "session_count": session_count, "max_fecha_universo": max_date,
        "firewall_max_fecha": MAX_FECHA, "firewall_corte_iso": str(corte_del_sello()),
        "universe_filter_report": universe_report, "outcomes_accessed": False,
        "code_commit": git_head(),
        "measurement_code_sha256": hash_sources(sources_medicion()),
        "measurement_sources": [str(p.relative_to(REPO_PATH)) for p in sources_medicion()],
        "candidate_count": len(all_candidates),
        "valid_before_sep_count": sum(x["valid"] for x in all_candidates),
        "orden_a": _summary(both["orden_a"], session_count),
        "orden_b": _summary(both["orden_b"], session_count),
        "violations": all_violations,
        "per_archive": per_archive,
    }
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    Path(args.out).write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print("orden A: %.3f/ses | orden B: %.3f/ses" % (
        payload["orden_a"]["events_per_session"], payload["orden_b"]["events_per_session"]
    ))
    print("-> %s\nEXIT=0" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
