"""Mide el tamaño del sesgo `isDown`-first: `HFTZonesESPureV2` contra `…V2Flat`.

QUÉ CONTESTA
============
Cuántas zonas desaparecen, cuántas aparecen, y si la geometría de las que sobreviven
cambia — al arreglar una sola cosa: que un tick **plano** ya no abra una racha bajista.

Es **target-free**: cuenta y compara geometría. No mira qué pasó después.

POR QUÉ ES UN RESULTADO Y NO UN CHEQUEO
=======================================
El censo descriptivo midió **92 % de zonas bajistas**, idéntico en tres buckets y tres
contratos, y el `.cs` explica por qué: con `cl == clP == op` las dos condiciones son
verdaderas y `isDown` se evalúa primero.

Pero *«el bug existe»* y *«el bug explica el 92 %»* son afirmaciones distintas. La
segunda sólo se prueba corriendo las dos versiones sobre la misma ventana. Si al
arreglarlo la asimetría no se mueve, la causa era otra y el diagnóstico estaba mal.

EMPAREJADO POR SESIÓN
=====================
Se comparan sólo los `(contrato, trade_date)` presentes en **las dos** bases. Comparar
totales de ventanas distintas mediría la ventana, no el fix.

Sin outcomes. Holdout excluido.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys
from collections import Counter

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.kaggle.sessions_cme import session_bounds_utc_ns, trade_date_ymd  # noqa: E402

SCHEMA_VERSION = "comparar_v2_vs_flat_v1"
CUTOFF_MS = session_bounds_utc_ns(20260701)[0] // 1_000_000
BASE_V2 = pathlib.Path(r"C:\LoggerHFT\data\oraculo_espurev2_ES.sqlite")
BASE_FLAT = pathlib.Path(r"C:\LoggerHFT\data\oraculo_espurev2flat_ES.sqlite")


def leer(p):
    con = sqlite3.connect("file:%s?mode=ro" % p.as_posix(), uri=True)
    filas = con.execute(
        "SELECT instrument, start_ts, end_ts, bucket, dir, price_upper, price_lower, "
        "height_ticks, pasos, total_vol FROM hft_zones WHERE start_ts < ?",
        (CUTOFF_MS,)).fetchall()
    con.close()
    if not filas:
        return {}
    st = np.array([f[1] for f in filas], dtype=np.int64)
    td = trade_date_ymd(st * 1_000_000)
    out = {}
    for f, d in zip(filas, td):
        out.setdefault((f[0], int(d)), []).append(f)
    return out


def resumen(zs):
    if not zs:
        return dict(n=0)
    dr = np.array([z[4] for z in zs], dtype=np.int64)
    alto = np.array([z[7] if z[7] is not None else np.nan for z in zs], dtype=np.float64)
    pasos = np.array([z[8] if z[8] is not None else np.nan for z in zs], dtype=np.float64)
    vol = np.array([z[9] if z[9] is not None else np.nan for z in zs], dtype=np.float64)
    return dict(n=len(zs), frac_alcista=round(float((dr > 0).mean()), 4),
                n_alcistas=int((dr > 0).sum()), n_bajistas=int((dr < 0).sum()),
                alto_mediana=round(float(np.nanmedian(alto)), 3),
                pasos_mediana=round(float(np.nanmedian(pasos)), 1),
                vol_mediana=round(float(np.nanmedian(vol)), 1),
                buckets=dict(Counter(str(z[3]) for z in zs)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", default=str(BASE_V2))
    ap.add_argument("--flat", default=str(BASE_FLAT))
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "comparacion_v2_vs_flat.json"))
    a = ap.parse_args()

    p_flat = pathlib.Path(a.flat)
    if not p_flat.exists():
        print("todavia no existe %s" % p_flat)
        print("compila HFTZonesESPureV2Flat en NT8 y corrélo con la misma configuracion.")
        return 2

    v2, fl = leer(pathlib.Path(a.v2)), leer(p_flat)
    comunes = sorted(set(v2) & set(fl))
    print("comparacion V2 vs V2Flat  ·  %s" % SCHEMA_VERSION)
    print("  sesiones: V2 %d  ·  Flat %d  ·  COMUNES %d" % (len(v2), len(fl), len(comunes)))
    if not comunes:
        print("  sin sesiones en comun: no se puede comparar sin medir la ventana")
        return 3

    za = [z for k in comunes for z in v2[k]]
    zb = [z for k in comunes for z in fl[k]]
    ra, rb = resumen(za), resumen(zb)

    # emparejado por sesion: la unidad es la sesion, no la zona
    dif_n, dif_alc = [], []
    for k in comunes:
        A, B = resumen(v2[k]), resumen(fl[k])
        dif_n.append(B["n"] - A["n"])
        if A["n"] and B["n"]:
            dif_alc.append(B["frac_alcista"] - A["frac_alcista"])
    dif_n = np.array(dif_n, dtype=np.float64)
    dif_alc = np.array(dif_alc, dtype=np.float64)

    # zonas identicas: misma sesion, mismo inicio, mismos bordes
    firma = lambda z: (z[1], z[5], z[6], z[4])                       # noqa: E731
    sa, sb = {firma(z) for z in za}, {firma(z) for z in zb}
    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]

    out = dict(
        schema_version=SCHEMA_VERSION,
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        emparejamiento="solo (contrato, trade_date) presentes en LAS DOS bases",
        n_sesiones_comunes=len(comunes),
        v2=ra, flat=rb,
        delta=dict(
            n_zonas=rb["n"] - ra["n"],
            frac_alcista=round(rb["frac_alcista"] - ra["frac_alcista"], 4),
            por_sesion_n=dict(mediana=float(np.median(dif_n)),
                              p25=float(np.percentile(dif_n, 25)),
                              p75=float(np.percentile(dif_n, 75))),
            por_sesion_frac_alcista=dict(
                mediana=round(float(np.median(dif_alc)), 4) if len(dif_alc) else None,
                p25=round(float(np.percentile(dif_alc, 25)), 4) if len(dif_alc) else None,
                p75=round(float(np.percentile(dif_alc, 75)), 4) if len(dif_alc) else None)),
        zonas=dict(solo_en_v2=len(sa - sb), solo_en_flat=len(sb - sa),
                   identicas=len(sa & sb),
                   firma="(start_ts, price_upper, price_lower, dir)"),
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios), alcance_comprometida=["edgelab/", "diag/"],
            medicion_comprometida=bool([f for f in sucios if f.startswith(("edgelab/", "diag/"))])))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("  zonas        V2 %6d   Flat %6d   delta %+d" % (ra["n"], rb["n"], rb["n"] - ra["n"]))
    print("  alcistas     V2 %5.1f%%  Flat %5.1f%%  delta %+.1f pp"
          % (ra["frac_alcista"] * 100, rb["frac_alcista"] * 100,
             (rb["frac_alcista"] - ra["frac_alcista"]) * 100))
    print("  identicas    %d   solo V2 %d   solo Flat %d"
          % (len(sa & sb), len(sa - sb), len(sb - sa)))
    print("  altura med   V2 %.2f  Flat %.2f" % (ra["alto_mediana"], rb["alto_mediana"]))
    print("  pasos med    V2 %.0f  Flat %.0f" % (ra["pasos_mediana"], rb["pasos_mediana"]))
    print("  escrito %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
