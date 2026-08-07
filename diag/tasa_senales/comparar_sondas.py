# -*- coding: utf-8 -*-
"""Compara dos artefactos de la sonda. **Falla si no son comparables.**

## Por qué existe

Los dos artefactos versionados de `sonda_alejamiento_cero.py` —8 sesiones de
`6E 09-26` y 40 de `6E 12-25`— se emitieron **con conjuntos de campos
distintos**: el de 40 salió antes de que se agregara la medición del reloj, así
que ese campo venía en `null`. Dos artefactos del mismo script, versionados
juntos, y **nada en ellos decía por qué diferían**.

Un lector razonable habría concluido que en `6E 12-25` el reloj no aplicaba. La
conclusión habría sido falsa y el artefacto no daba con qué desmentirla.

## La regla, y por qué es fail-closed

**`schema_version` distinto ⇒ NO se comparan.** No se alinean los campos
comunes, no se ignoran los faltantes: se falla. Alinear lo que coincide es
justamente cómo un cambio de semántica pasa desapercibido — dos campos con el
mismo nombre y distinto significado se comparan sin ruido.

Las diferencias que **sí** se esperan —y por eso no son error— son las de
**muestra y período**: contrato, número de sesiones, ventana. Todo lo demás
—grilla de umbrales, umbral material, firewall, clase de kernel, huella del
código— tiene que coincidir, porque si no, los números no miden lo mismo.

Uso:
    python diag/tasa_senales/comparar_sondas.py A.json B.json

Exit: 0 = comparables y consistentes · 1 = no comparables · 2 = no se evaluó
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

#: Tienen que coincidir: si difieren, los números no miden lo mismo.
DEBEN_COINCIDIR = ("schema_version", "umbrales", "umbral_material_ns",
                   "firewall_max_fecha", "firewall_corte_utc_ns",
                   "clase_kernel", "huella_del_codigo", "outcomes_accessed")

#: Se ESPERA que difieran: son la muestra. Que difieran es el objeto de la
#: comparación, no un defecto.
PUEDEN_DIFERIR = ("contrato", "sesiones", "max_fecha", "output_sha256",
                  "code_commit", "por_indicador", "pregunta", "definiciones")

#: Métricas que se ponen lado a lado.
METRICAS = ("frac_dentro", "frac_cualquier_adelanto", "frac_adelanto_mayor_1s")


def cargar(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("a")
    ap.add_argument("b")
    x = ap.parse_args(argv)

    try:
        A, B = cargar(x.a), cargar(x.b)
    except Exception as e:
        print("no se pudo leer: %s" % e)
        return 2

    sa, sb = A.get("schema_version"), B.get("schema_version")
    if sa != sb or sa is None:
        print("NO COMPARABLES: schema_version %r vs %r" % (sa, sb))
        print("\nNo se alinean los campos comunes a proposito. Alinear lo que")
        print("coincide es como un cambio de semantica pasa desapercibido: dos")
        print("campos con el mismo nombre y distinto significado se comparan")
        print("sin ruido. Regenerar el artefacto viejo con el script actual.")
        return 1

    difs = [(k, A.get(k), B.get(k)) for k in DEBEN_COINCIDIR if A.get(k) != B.get(k)]
    if difs:
        print("NO COMPARABLES: %d campo(s) que deben coincidir difieren\n" % len(difs))
        for k, va, vb in difs:
            print("  %-24s %.90s\n  %-24s %.90s\n" % (k, va, "", vb))
        return 1

    print("schema %s | umbrales %s | umbral material %d ns"
          % (sa, A.get("umbrales"), A.get("umbral_material_ns") or 0))
    print("huella del codigo %s  (identica en los dos)"
          % (A.get("huella_del_codigo") or "?")[:16])
    print("\nMUESTRA -- se espera que difiera; es el objeto de la comparacion")
    print("  A  %-26s %3d sesiones  hasta %s"
          % (A.get("contrato"), A.get("sesiones") or 0, A.get("max_fecha")))
    print("  B  %-26s %3d sesiones  hasta %s"
          % (B.get("contrato"), B.get("sesiones") or 0, B.get("max_fecha")))

    pa, pb = A.get("por_indicador") or {}, B.get("por_indicador") or {}
    falta = sorted(set(pa) ^ set(pb))
    if falta:
        print("\nNO COMPARABLES: distinto conjunto de indicadores: %s" % falta)
        return 1

    print("\n%-16s %-12s %s" % ("indicador", "clase",
                                "  ".join("%22s" % m for m in METRICAS)))
    print("%-16s %-12s %s" % ("", "", "  ".join("%10s %10s" % ("A", "B")
                                                for _ in METRICAS)))
    faltantes = []
    for n in sorted(pa, key=lambda k: (pa[k].get("clase_kernel") or "", k)):
        ra, rb = pa[n], pb[n]
        celdas = []
        for m in METRICAS:
            va = ra.get(m, ra.get("reloj_de_barra_abriria_antes", {}).get(m))
            vb = rb.get(m, rb.get("reloj_de_barra_abriria_antes", {}).get(m))
            if va is None or vb is None:
                faltantes.append((n, m))
            celdas.append("%10s %10s" % (va, vb))
        print("%-16s %-12s %s" % (n, ra.get("clase_kernel"), "  ".join(celdas)))

    if faltantes:
        print("\nNO COMPARABLES: hay metricas en `null` pese a compartir schema.")
        for n, m in faltantes:
            print("  %s / %s" % (n, m))
        return 1

    print("\nCOMPARABLES: mismo esquema, misma grilla, mismo firewall, misma")
    print("huella de codigo. Las diferencias que quedan son de MUESTRA y PERIODO.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
