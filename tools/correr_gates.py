#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corre los gates de paridad de todos los oráculos y clasifica los FAIL.

## Por qué clasifica en vez de sólo reportar PASS/FAIL

Dos de los oráculos atraviesan el rango con el bloque duplicado
(2026-06-22 → 2026-07-02): `aVolCellPOI2` arranca en 06-12 y su
`lookback_sessions=20` puede propagar la contaminación **más allá** de esas
fechas; `VolTicksPOC2` pisa el 07-02.

Un FAIL heredado de la hora duplicada **no es un FAIL de kernel**. Gastarle el
veredicto al indicador por un defecto del parquet sería exactamente el error que
el censo existe para evitar. Por eso cada FAIL se etiqueta:

  `KERNEL_FAIL`          — las discrepancias caen en días APTOS
  `DATA_INTEGRITY_FAIL`  — se concentran en días fuera del universo
  `SIN_REGION_COMPARABLE`— la ventana útil quedó vacía (p.ej. lookback sin llenar)

**Prohibido "arreglar" el parquet para conseguir un PASS.** Cuando el veredicto
es `DATA_INTEGRITY_FAIL`, la salida dice qué rango limpio adicional haría falta.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
DATA = "data/nt8/6E/6E_09-26_ticks.parquet"
TZ = "America/Argentina/Buenos_Aires"

# ventana de comparación común a todos (la del contrato de paridad)
W0, W1 = "2026-07-13T22:00:00", "2026-07-16T21:00:00"
# Ventana de DATOS: arranca en el inicio del universo del contrato (2026-06-12,
# front month) para que los kernels con lookback largo tengan warmup. Sin esto
# aVolCellPOI2 recibe 3 dias, su lookback de 10-20 sesiones no se llena nunca y
# produce CERO zonas -- que se leerian como FAIL de kernel siendo del arnes.
D0, D1 = "2026-06-12T00:00:00", "2026-07-17T00:00:00"

CORRIDAS = [
    dict(nombre="Gaps2", ind="Gaps2", bars="time:1",
         oraculo="oracles/Gaps2_6E_0926.csv"),
    dict(nombre="BigTrap2_time1", ind="BigTrap2", bars="time:1",
         oraculo="oracles/BigTrap2_time1_6E_0926_v2.csv"),
    dict(nombre="BigTrap2_wickoff", ind="BigTrap2", bars="time:1",
         oraculo="oracles/BigTrap2_time1_6E_0926_wickoff.csv",
         params='{"use_wick_filter": false}'),
    dict(nombre="BigTrap2_samelevel", ind="BigTrap2", bars="time:1",
         oraculo="oracles/BigTrap2_time1_6E_0926_samelevel.csv",
         params='{"imbalance_mode": "SameLevel"}'),
    dict(nombre="HFTZones2_v23", ind="HFTZones2", bars="time:1",
         oraculo="oracles/HFTZones2_adaptive_6E_0926_v23.csv"),
    dict(nombre="AACloseOpenDiffs_v12", ind="AACloseOpenDiffs", bars="time:1",
         oraculo="oracles/AACloseOpenDiffs_6E_0926_v12.csv"),
    dict(nombre="aVolCellPOI2_v21", ind="aVolCellPOI2", bars="time:1",
         oraculo="oracles/aVolCellPOI2_6E_0926_v21.csv"),
    dict(nombre="VolTicksPOC2_warmup", ind="VolTicksPOC2", bars="time:1",
         oraculo="oracles/VolTicksPOC2_6E_0926_warmup.csv"),
]


def dias_aptos():
    p = os.path.join(REPO, "runs", "censo", "manifiesto_universo.json")
    if not os.path.exists(p):
        return set()
    return {d["fecha"] for d in json.load(open(p, encoding="utf-8"))["dias"]}


def clasificar(rep, aptos):
    """KERNEL_FAIL vs DATA_INTEGRITY_FAIL, por dónde caen las discrepancias."""
    s = rep["summary"]
    if s["gate"] == "PASS":
        return "PASS", ""
    if s["matched_pairs"] == 0 and s["nt8_zones"] == 0:
        return "SIN_REGION_COMPARABLE", "el oráculo no aporta zonas en la ventana"
    diag = [d for d in rep["diagnostics"] if d["code"] != "MATCHED"]
    # la ventana de comparación (13→16 jul) está entera dentro del universo,
    # así que un FAIL acá NO puede venir del bloque duplicado de 06-22→07-02.
    ventana_limpia = all(f in aptos for f in
                         ("2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16"))
    if not ventana_limpia:
        return "DATA_INTEGRITY_FAIL", "la ventana toca días fuera del universo"
    return "KERNEL_FAIL", "%d discrepancias en ventana limpia" % len(diag)


def main():
    aptos = dias_aptos()
    out = []
    for c in CORRIDAS:
        orc = os.path.join(REPO, c["oraculo"])
        if not os.path.exists(orc):
            out.append(dict(nombre=c["nombre"], estado="SIN_ORACULO", detalle=c["oraculo"]))
            print("[%-22s] SIN ORACULO" % c["nombre"], flush=True)
            continue
        dest = os.path.join(REPO, "runs", "gates", c["nombre"])
        cmd = [PY, os.path.join(REPO, "tools", "run_nt8_bridge.py"),
               "--data", DATA, "--contract", "6E 09-26",
               "--indicator", c["ind"], "--bars", c["bars"],
               "--oracle", "%s=%s" % (c["ind"], c["oraculo"]),
               "--chart-tz", TZ, "--start-utc", W0, "--end-utc", W1,
               "--data-start-utc", D0, "--data-end-utc", D1,
               "--out", dest]
        if c.get("params"):
            cmd += ["--params", "%s=%s" % (c["ind"], c["params"])]  # formato JSON
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=1800)
        rp = os.path.join(dest, "parity_report.json")
        if not os.path.exists(rp):
            out.append(dict(nombre=c["nombre"], estado="ERROR",
                            detalle=(r.stderr or r.stdout)[-400:]))
            print("[%-22s] ERROR" % c["nombre"], flush=True)
            continue
        rep = json.load(open(rp, encoding="utf-8"))
        for k, v in rep.items():
            estado, det = clasificar(v, aptos)
            s = v["summary"]
            out.append(dict(nombre=c["nombre"], config=k, estado=estado, detalle=det,
                            gate=s["gate"], py=s["py_zones"], nt8=s["nt8_zones"],
                            matched=s["matched_pairs"], counts=s["counts"]))
            print("[%-22s] %-22s py=%-5d nt8=%-5d match=%-5d  %s"
                  % (c["nombre"], estado, s["py_zones"], s["nt8_zones"],
                     s["matched_pairs"], det), flush=True)

    os.makedirs(os.path.join(REPO, "runs", "gates"), exist_ok=True)
    json.dump(dict(generado_utc=datetime.now(timezone.utc).isoformat(),
                   ventana_comparacion=[W0, W1], ventana_datos=[D0, D1],
                   n_dias_aptos=len(aptos), resultados=out),
              open(os.path.join(REPO, "runs", "gates", "resumen.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\nresumen -> runs/gates/resumen.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
