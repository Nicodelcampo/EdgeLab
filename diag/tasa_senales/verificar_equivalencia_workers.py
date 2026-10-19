# -*- coding: utf-8 -*-
"""Verifica, campo por campo, la equivalencia entre 1 y N workers.

## Por qué existe este archivo

`curva_excursion_ticks.json` **publica** esta afirmación adentro del artefacto:

    "equivalencia_workers": "1 vs 2 EXACTA sobre 2 contratos con trabajo real
     en ambos, subset {BigTrap2, VolTicksPOC2, aVolCellPOI2}: por_umbral,
     por_kind, descartes y clases identicos. RSS pico 1.925 vs 2.734 MB."

La comparación se hizo, y dio EXACTA. Pero **la evidencia quedó en un
directorio temporal** —dos JSON de 687 KB— que se borra solo. O sea: una
afirmación publicada dentro de un artefacto versionado, sostenida por archivos
que dentro de un tiempo no van a existir.

Es exactamente el modo de falla que este expediente persigue en todos lados: un
número publicado cuya derivación nadie puede reconstruir. La corrida de 201
sesiones se hizo con `workers=4` **confiando en esa equivalencia**, así que no
es un detalle de trazabilidad — es el permiso de la corrida entera.

Este script rehace la comparación sobre los artefactos, emite un **acta chica y
versionable** con el `sha256` de cada entrada, y **falla si no son idénticos**.

## Qué compara, y por qué NO compara el archivo entero

Un `diff` de bytes daría FAIL siempre y no diría nada: los artefactos difieren
por construcción en `workers`, en `clave_de_corrida` (que incluye el plan) y en
`segundos` (el tiempo de pared no es determinista). Comparar eso sería fabricar
un fallo.

Lo que **tiene** que ser idéntico es todo lo que es un RESULTADO:

  - `por_umbral`  — los conteos por sesión y umbral, que son la curva
  - `por_kind`    — el desglose por tipo de zona
  - los cuatro descartes y la clase de kernel de cada indicador
  - `alejamiento_en_primera_reentrada` — los cuantiles

Y se declara explícitamente qué campos se **excluyen** y por qué. Una
comparación que no dice qué ignoró no es una comparación.

Uso:
    python diag/tasa_senales/verificar_equivalencia_workers.py A.json B.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SALIDA = Path(__file__).resolve().parent / "equivalencia_workers.json"

#: Campos que DEBEN coincidir. Son resultados: si alguno difiere, paralelizar
#: cambió el número y la corrida de 201 sesiones no era legítima.
CAMPOS_RESULTADO = ("por_umbral", "por_kind", "alejamiento_en_primera_reentrada",
                    "zonas", "kinds", "clase_kernel",
                    "zonas_sin_tramo_de_ticks", "zonas_sin_campos",
                    "zonas_sin_created_bar", "zonas_sin_clase_declarada",
                    "zonas_abstenidas_por_ambiguedad_intrabar", "estado")

#: Campos que se EXCLUYEN, con el motivo. Una comparación que no declara qué
#: ignoró no es una comparación: es un pase.
EXCLUIDOS = {
    "segundos": "tiempo de pared -- no determinista por definicion",
    "workers": "es justamente lo que varia entre las dos corridas",
    "clave_de_corrida": "incluye el plan y el numero de workers",
    "code_commit": "puede diferir si las corridas no fueron del mismo HEAD",
    "output_sha256": "hash del payload entero, que incluye los excluidos",
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def comparar(a, b):
    """Diferencias en los campos de resultado. Lista vacía = idénticos."""
    difs = []
    ca, cb = a.get("por_contrato") or {}, b.get("por_contrato") or {}
    if set(ca) != set(cb):
        difs.append(("por_contrato", "conjunto de contratos distinto: %s vs %s"
                     % (sorted(ca), sorted(cb))))
        return difs
    for arch in sorted(ca):
        ia, ib = ca[arch], cb[arch]
        if set(ia) != set(ib):
            difs.append((arch, "conjunto de indicadores distinto"))
            continue
        for ind in sorted(ia):
            ra, rb = ia[ind], ib[ind]
            for campo in CAMPOS_RESULTADO:
                va, vb = ra.get(campo), rb.get(campo)
                if va != vb:
                    difs.append(("%s/%s/%s" % (arch, ind, campo),
                                 "%.200s  !=  %.200s" % (va, vb)))
    if (a.get("curvas") or {}) != (b.get("curvas") or {}):
        difs.append(("curvas", "el agregado publicado difiere"))
    return difs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("a", help="artefacto de la corrida secuencial")
    ap.add_argument("b", help="artefacto de la corrida paralela")
    ap.add_argument("--rss", nargs=2, type=float, metavar=("MB_A", "MB_B"),
                    help="RSS pico medido de cada corrida, si se midio")
    x = ap.parse_args(argv)

    A = json.loads(Path(x.a).read_text(encoding="utf-8"))
    B = json.loads(Path(x.b).read_text(encoding="utf-8"))
    difs = comparar(A, B)

    print("A  %s  workers=%s  sesiones=%s  sha %s"
          % (Path(x.a).name, A.get("workers"), A.get("session_count"), sha(x.a)[:16]))
    print("B  %s  workers=%s  sesiones=%s  sha %s"
          % (Path(x.b).name, B.get("workers"), B.get("session_count"), sha(x.b)[:16]))
    print("\nexcluidos de la comparacion, a proposito:")
    for k, v in sorted(EXCLUIDOS.items()):
        print("  %-18s %s" % (k, v))

    n_ind = sum(len(v) for v in (A.get("por_contrato") or {}).values())
    print("\ncomparados: %d campos de resultado x %d (contrato,indicador)"
          % (len(CAMPOS_RESULTADO), n_ind))
    if difs:
        print("\nDIFIEREN  (%d)" % len(difs))
        for k, v in difs[:20]:
            print("  %s\n    %s" % (k, v))
    else:
        print("\nEXACTA: los %d campos coinciden en las %d unidades."
              % (len(CAMPOS_RESULTADO), n_ind))

    acta = dict(
        que="equivalencia entre corrida secuencial y paralela de la curva",
        por_que="la corrida de 201 sesiones uso workers=4 confiando en esto",
        veredicto="EXACTA" if not difs else "DIFIERE",
        a=dict(archivo=Path(x.a).name, sha256=sha(x.a), workers=A.get("workers"),
               sesiones=A.get("session_count")),
        b=dict(archivo=Path(x.b).name, sha256=sha(x.b), workers=B.get("workers"),
               sesiones=B.get("session_count")),
        campos_comparados=list(CAMPOS_RESULTADO),
        campos_excluidos=EXCLUIDOS,
        unidades_comparadas=n_ind,
        diferencias=[dict(donde=k, detalle=v) for k, v in difs],
        outcomes_accessed=False)
    if x.rss:
        acta["rss_pico_mb"] = dict(a=x.rss[0], b=x.rss[1])
    SALIDA.write_text(json.dumps(acta, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print("\n-> %s" % SALIDA)
    return 0 if not difs else 1


if __name__ == "__main__":
    sys.exit(main())
