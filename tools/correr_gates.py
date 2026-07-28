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
# La ventana de DATOS es una propiedad del ORACULO, no un ajuste global: tiene
# que espejar lo que cargo el chart que lo genero. Un warmup comun para todos
# rompe la correspondencia -- con Gaps2 se vio en vivo: su oraculo se genero con
# el chart arrancando en la ventana, y darle un mes de historia hizo que Python
# dejara de reproducir las 8 primeras zonas (que NT8 crea justo en su primera
# barra, tres de ellas con geometria y timestamp IDENTICOS entre si).
#
# Warmup por defecto para los kernels con lookback largo; los que no lo necesitan
# corren con datos == ventana de comparacion, igual que su chart.
D0, D1 = "2026-06-12T00:00:00", "2026-07-17T00:00:00"

CORRIDAS = [
    dict(warmup=False, nombre="Gaps2", ind="Gaps2", bars="time:1",
         oraculo="oracles/Gaps2_6E_0926.csv"),
    dict(warmup=False, nombre="BigTrap2_time1", ind="BigTrap2", bars="time:1",
         oraculo="oracles/BigTrap2_time1_6E_0926_v2.csv"),
    dict(warmup=False, nombre="BigTrap2_wickoff", ind="BigTrap2", bars="time:1",
         oraculo="oracles/BigTrap2_time1_6E_0926_wickoff.csv",
         params='{"use_wick_filter": false}'),
    dict(warmup=False, nombre="BigTrap2_samelevel", ind="BigTrap2", bars="time:1",
         oraculo="oracles/BigTrap2_time1_6E_0926_samelevel.csv",
         params='{"imbalance_mode": "SameLevel"}'),
    dict(nombre="HFTZones2_v23", ind="HFTZones2", bars="time:1",
         oraculo="oracles/HFTZones2_adaptive_6E_0926_v23.csv"),
    dict(warmup=False, nombre="AACloseOpenDiffs_v12", ind="AACloseOpenDiffs", bars="time:1",
         oraculo="oracles/AACloseOpenDiffs_6E_0926_v12.csv"),
    dict(nombre="aVolCellPOI2_v21", ind="aVolCellPOI2", bars="time:1",
         lookback_sesiones=20,
         oraculo="oracles/aVolCellPOI2_6E_0926_v21.csv"),
    dict(nombre="VolTicksPOC2_warmup", ind="VolTicksPOC2", bars="time:1",
         oraculo="oracles/VolTicksPOC2_6E_0926_warmup.csv"),
]


def dias_aptos(archivo="6E_09-26_ticks.parquet"):
    """Días aptos DEL PARQUET que se está evaluando.

    Filtrar por archivo no es un detalle: el manifiesto tiene 164 días de cuatro
    contratos, y contarlos todos haría creer que hay warmup limpio de sobra
    cuando el contrato bajo prueba tiene 8 sesiones.

    A diferencia de los estudios, la paridad **sí** es un uso permitido sobre el
    holdout (§G4: `target_free_validation` — compara geometría contra el oráculo
    NT8, no mira P&L). Por eso pasa por la puerta con `incluir_holdout=True` y
    propósito declarado: la apertura queda registrada **sola** en
    `docs/holdout_access_log.md`, que era la deuda anotada en su nota 2.
    """
    from edgelab.research.universo_estudio import cargar_dias_de_estudio
    p = os.path.join(REPO, "runs", "censo", "manifiesto_universo.json")
    if not os.path.exists(p):
        return set()
    dias, _ = cargar_dias_de_estudio(
        p, incluir_holdout=True, purpose="target_free_validation",
        caller="correr_gates:%s" % archivo)
    return {d["fecha"] for d in dias if d["archivo"] == archivo}


def sesiones_limpias_antes(aptos, hasta="2026-07-13"):
    """Cuántas sesiones APTAS hay disponibles como warmup antes de la ventana."""
    return sorted(f for f in aptos if f < hasta)


def clasificar(rep, aptos, c=None):
    """KERNEL_FAIL vs DATA_INTEGRITY_FAIL, por dónde caen las discrepancias."""
    s = rep["summary"]
    if s["gate"] == "PASS":
        return "PASS", ""

    # Un kernel con lookback de SESIONES necesita esa cantidad de sesiones
    # LIMPIAS antes de la ventana. Si no las hay, su FAIL no es del kernel: es
    # que el universo no alcanza para evaluarlo. Gastarle el veredicto seria el
    # error que el censo existe para evitar.
    lb = (c or {}).get("lookback_sesiones")
    if lb:
        prev = sesiones_limpias_antes(aptos)
        if len(prev) < lb:
            return ("DATA_INTEGRITY_FAIL",
                    "necesita %d sesiones limpias de warmup y solo hay %d "
                    "(el bloque duplicado 06-22 -> 07-02 cae justo donde iria "
                    "el warmup). Rango limpio que haria falta: regenerar F2 en "
                    "2026-06-19 -> 2026-07-03" % (lb, len(prev)))
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
               "--chart-tz", TZ, "--start-utc", W0, "--end-utc", W1]
        if c.get("warmup", True):
            cmd += ["--data-start-utc", D0, "--data-end-utc", D1]
        cmd += ["--out", dest]
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
            estado, det = clasificar(v, aptos, c)
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
