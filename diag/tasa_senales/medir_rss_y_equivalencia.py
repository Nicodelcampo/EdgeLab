# -*- coding: utf-8 -*-
"""Mide RSS pico y equivalencia entre 1 y N workers, corriendo la curva de verdad.

## Por qué está versionado

`curva_excursion_ticks.json` **publica** el RSS pico y el veredicto de
equivalencia adentro del artefacto. Este script es el que los produjo, y hasta
la auditoría de procedencia del 2026-08-07 **vivía en un directorio temporal**.

La corrida de 201 sesiones usó `workers=4` confiando en esa equivalencia. Un
instrumento que sostiene el permiso de una corrida de 84.000 s de CPU no puede
estar en un directorio que se borra solo.

## Dos cosas que este instrumento hace bien y conviene no perder

**1. Mide el proceso Y sus hijos.** Con `ProcessPoolExecutor` el pico real es la
suma: medir sólo el padre daría un número tranquilizador y falso. Se resta el
RSS que ya había antes de arrancar, así que el número es el costo *marginal*.

**2. Usa 70 sesiones = DOS contratos, a propósito.** La primera medición usó
`--limite-sesiones 12`, que cae entero dentro de `6E_03-26`: **un solo
contrato**. La paralelización es POR CONTRATO, así que el segundo worker no
tenía trabajo — y el «speedup» de esa corrida no medía paralelismo. Esa primera
corrida está declarada inválida y **no** es la que sostiene la afirmación.

## Unidades — el defecto que encontró la auditoría

`rss_pico_gb` divide por `2**30`: son **GIGABYTES**. El artefacto publica «RSS
pico 1.925 vs 2.734 **MB**», que además de estar en la unidad equivocada **no
coincide** con la única medición preservada (1,88 vs 2,67 GB). Ver
`docs/SCRATCHPAD_PROVENANCE_AUDIT_2026-08-07.md` §3.

Uso:
    python diag/tasa_senales/medir_rss_y_equivalencia.py --sesiones 70
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = REPO / ".venv" / "Scripts" / "python.exe"

#: SUBSET FIJO, declarado. `Gaps2` y `HFTZones2` tardan >300 s cada uno sobre 60
#: sesiones y NO aportan a una prueba de equivalencia: lo que hay que demostrar
#: es que dos workers producen el mismo payload que uno, y para eso alcanza con
#: que ambos tengan trabajo real.
INDICADORES = ["BigTrap2", "VolTicksPOC2", "aVolCellPOI2"]

PS = ("Get-Process python -ErrorAction SilentlyContinue | "
      "Measure-Object -Property WorkingSet64 -Sum | "
      "Select-Object -ExpandProperty Sum")

#: Campos que NO pueden entrar en la comparación: difieren por construcción.
NEUTRALIZAR = ("workers", "output_sha256", "clave_de_corrida", "code_commit")


def rss_total_python():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", PS],
                           capture_output=True, text=True, timeout=10)
        v = (r.stdout or "").strip()
        return int(v) if v.isdigit() else 0
    except Exception:
        return 0


def correr(workers, sesiones, out, tmp):
    base = rss_total_python()          # lo que ya había corriendo, se resta
    cmd = [str(PY), "-u", r"diag\tasa_senales\curva_excursion_ticks.py",
           "--limite-sesiones", str(sesiones), "--workers", str(workers),
           "--fresh", "--checkpoint", os.path.join(tmp, "ck_%d.json" % workers),
           "--indicadores"] + INDICADORES + ["--out", out]
    t0 = time.time()
    p = subprocess.Popen(cmd, cwd=str(REPO), stdout=subprocess.DEVNULL,
                         stderr=subprocess.STDOUT)
    pico = 0
    while p.poll() is None:
        pico = max(pico, rss_total_python() - base)
        time.sleep(1.0)
    p.wait()
    return dict(workers=workers, segundos=round(time.time() - t0, 1),
                rss_pico_GB=round(max(0, pico) / 2 ** 30, 2), exit=p.returncode)


def limpiar(d):
    d = dict(d)
    for k in NEUTRALIZAR:
        d.pop(k, None)
    for _arch, r in (d.get("por_contrato") or {}).items():
        for _n, x in r.items():
            x.pop("segundos", None)
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sesiones", type=int, default=70,
                    help="70 = dos contratos. Menos de ~13 cae en uno solo y "
                         "el segundo worker no tiene trabajo.")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--tmp", default=None, help="dónde dejar los intermedios")
    a = ap.parse_args(argv)

    tmp = a.tmp or tempfile.mkdtemp(prefix="rss_equiv_")
    print("universo: %d sesiones | indicadores: %s | intermedios en %s"
          % (a.sesiones, INDICADORES, tmp), flush=True)

    o1 = os.path.join(tmp, "w1.json")
    oN = os.path.join(tmp, "w%d.json" % a.workers)
    r1 = correr(1, a.sesiones, o1, tmp)
    print("workers=1: %s" % r1, flush=True)
    rN = correr(a.workers, a.sesiones, oN, tmp)
    print("workers=%d: %s" % (a.workers, rN), flush=True)

    A = limpiar(json.loads(Path(o1).read_text(encoding="utf-8")))
    B = limpiar(json.loads(Path(oN).read_text(encoding="utf-8")))
    igual = json.dumps(A, sort_keys=True) == json.dumps(B, sort_keys=True)

    print("\n%-10s %10s %14s" % ("workers", "segundos", "RSS pico GB"))
    for r in (r1, rN):
        print("%-10d %10.1f %14.2f" % (r["workers"], r["segundos"], r["rss_pico_GB"]))
    if r1["segundos"] and rN["segundos"]:
        print("speedup: %.2fx" % (r1["segundos"] / rN["segundos"]))
    print("EQUIVALENCIA:", "EXACTA" if igual else "*** DIFIEREN ***")
    if not igual:
        for k in sorted(set(A) | set(B)):
            if json.dumps(A.get(k), sort_keys=True) != json.dumps(B.get(k), sort_keys=True):
                print("  difiere:", k)
    print("\nlos dos artefactos quedaron en %s -- si esta corrida sostiene una "
          "afirmacion publicada, VERSIONARLOS." % tmp)
    return 0 if igual else 1


if __name__ == "__main__":
    sys.exit(main())
