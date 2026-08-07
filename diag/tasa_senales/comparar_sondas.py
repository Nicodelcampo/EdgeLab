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

## Las cuatro puertas, en orden

1. **`schema_version` idéntico.** Distinto ⇒ NO se comparan. No se alinean los
   campos comunes: alinear lo que coincide es justamente cómo un cambio de
   semántica pasa desapercibido.
2. **Estructura completa.** Compartir `schema_version` no garantiza que los
   campos estén ni que tengan el tipo correcto. Se valida el esquema entero,
   incluido `frac_vacua_por_umbral` y **que su grilla sea la declarada**.
3. **Campos que deben coincidir**, incluidos **`pregunta` y `definiciones`**.
   Estos dos estaban en la lista de «pueden diferir», lo cual contradecía el
   propósito: **dos artefactos no miden lo mismo si cambia la definición de una
   métrica**, aunque el número tenga el mismo nombre.
4. **Integridad.** Se **recalcula** `payload_sha256` —antes sólo se imprimía— y
   se verifica el sidecar `.sha256` contra los bytes del archivo.

Lo que **sí** se espera que difiera son la **muestra y el período**: contrato,
sesiones, fechas, ventana, parquet de entrada. Que difieran es el objeto de la
comparación.

Uso:
    python diag/tasa_senales/comparar_sondas.py A.json B.json [--reporte R.json]

Exit: 0 = comparables y consistentes · 1 = no comparables · 2 = no se evaluó
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

#: Tienen que coincidir: si difieren, los números no miden lo mismo.
DEBEN_COINCIDIR = ("schema_version", "pregunta", "definiciones", "umbrales",
                   "umbral_material_ns", "firewall_max_fecha",
                   "firewall_corte_utc_ns", "clase_kernel", "outcomes_accessed")

#: Dentro de `identidad`: el CÓDIGO tiene que ser el mismo; la MUESTRA no.
IDENTIDAD_DEBE_COINCIDIR = ("code_commit_start", "generator_sha256",
                            "measurement_code_sha256",
                            "universe_manifest_sha256")
IDENTIDAD_PUEDE_DIFERIR = ("session_dates", "session_dates_sha256",
                           "input_parquet", "input_parquet_sha256",
                           "working_tree_dirty_start")

#: Esquema mínimo obligatorio: campo -> tipo(s). Si falta o no tipa, se falla.
ESQUEMA = {
    "schema_version": str, "pregunta": str, "definiciones": dict,
    "contrato": str, "sesiones": int, "max_fecha": str,
    "firewall_max_fecha": str, "firewall_corte_utc_ns": int,
    "firewall_corte_iso": str, "umbrales": list, "umbral_material_ns": int,
    "clase_kernel": dict, "identidad": dict, "outcomes_accessed": bool,
    "por_indicador": dict, "payload_sha256": str,
}
ESQUEMA_INDICADOR = {
    "clase_kernel": str, "zonas": int, "frac_dentro": float,
    "frac_vacua_por_umbral": dict, "reloj_de_barra_abriria_antes": dict,
}
METRICAS_RELOJ = ("frac_cualquier_adelanto", "frac_adelanto_mayor_1s",
                  "adelanto_s_p50")


def cargar(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def validar_estructura(d, etiqueta):
    """Campos presentes, con el tipo correcto, y la grilla `T` completa."""
    fallos = []
    for k, t in sorted(ESQUEMA.items()):
        if k not in d:
            fallos.append("%s: falta `%s`" % (etiqueta, k))
        elif not isinstance(d[k], t) or (t is int and isinstance(d[k], bool)):
            fallos.append("%s: `%s` es %s, se esperaba %s"
                          % (etiqueta, k, type(d[k]).__name__, t.__name__))
    ident = d.get("identidad")
    if isinstance(ident, dict):
        for k in IDENTIDAD_DEBE_COINCIDIR + IDENTIDAD_PUEDE_DIFERIR:
            if k not in ident:
                fallos.append("%s: falta `identidad.%s`" % (etiqueta, k))
    if d.get("diagnostico_arbol_sucio"):
        fallos.append("%s: generado con ARBOL SUCIO -- es diagnostico, no "
                      "puede ser canonico" % etiqueta)

    umbrales = [str(t) for t in (d.get("umbrales") or [])]
    for n, r in sorted((d.get("por_indicador") or {}).items()):
        if not isinstance(r, dict):
            fallos.append("%s/%s: no es un objeto" % (etiqueta, n))
            continue
        for k, t in sorted(ESQUEMA_INDICADOR.items()):
            if k not in r:
                fallos.append("%s/%s: falta `%s`" % (etiqueta, n, k))
            elif r[k] is None:
                fallos.append("%s/%s: `%s` es null" % (etiqueta, n, k))
            elif t is float and not isinstance(r[k], (int, float)):
                fallos.append("%s/%s: `%s` no es numerico" % (etiqueta, n, k))
            elif t is not float and not isinstance(r[k], t):
                fallos.append("%s/%s: `%s` es %s, se esperaba %s"
                              % (etiqueta, n, k, type(r[k]).__name__, t.__name__))
        # la grilla T tiene que estar ENTERA: un umbral faltante es un agujero
        # silencioso en la tabla que despues se lee como "no aplica".
        fv = r.get("frac_vacua_por_umbral") or {}
        faltan = [t for t in umbrales if t not in fv]
        if faltan:
            fallos.append("%s/%s: `frac_vacua_por_umbral` no cubre la grilla: "
                          "faltan %s" % (etiqueta, n, faltan))
        nulos = [t for t in umbrales if fv.get(t) is None]
        if nulos:
            fallos.append("%s/%s: `frac_vacua_por_umbral` en null para %s"
                          % (etiqueta, n, nulos))
        rel = r.get("reloj_de_barra_abriria_antes") or {}
        for m in METRICAS_RELOJ:
            if rel.get(m) is None:
                fallos.append("%s/%s: `%s` ausente o null" % (etiqueta, n, m))
    return fallos


def verificar_integridad(ruta, d, etiqueta):
    """Recalcula `payload_sha256` y valida el sidecar de bytes."""
    fallos = []
    sin = {k: v for k, v in d.items() if k != "payload_sha256"}
    calc = hashlib.sha256(
        json.dumps(sin, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if calc != d.get("payload_sha256"):
        fallos.append("%s: `payload_sha256` NO recalcula\n    declarado %s\n"
                      "    calculado %s" % (etiqueta, d.get("payload_sha256"), calc))
    side = Path(str(ruta) + ".sha256")
    if not side.exists():
        fallos.append("%s: falta el sidecar %s" % (etiqueta, side.name))
    else:
        esperado = side.read_text(encoding="utf-8").split()[0]
        real = hashlib.sha256(Path(ruta).read_bytes()).hexdigest()
        if esperado != real:
            fallos.append("%s: el sidecar NO coincide con los bytes\n"
                          "    sidecar %s\n    archivo %s"
                          % (etiqueta, esperado, real))
    return fallos


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--reporte", help="escribe el resultado de la comparacion")
    x = ap.parse_args(argv)

    try:
        A, B = cargar(x.a), cargar(x.b)
    except Exception as e:
        print("no se pudo leer: %s" % e)
        return 2

    # (1) esquema
    sa, sb = A.get("schema_version"), B.get("schema_version")
    if sa != sb or sa is None:
        print("NO COMPARABLES: schema_version %r vs %r" % (sa, sb))
        print("\nNo se alinean los campos comunes a proposito. Alinear lo que")
        print("coincide es como un cambio de semantica pasa desapercibido.")
        print("Regenerar el artefacto viejo con el script actual.")
        return 1

    # (2) estructura y (4) integridad
    fallos = (validar_estructura(A, "A") + validar_estructura(B, "B")
              + verificar_integridad(x.a, A, "A") + verificar_integridad(x.b, B, "B"))
    if fallos:
        print("NO COMPARABLES: %d problema(s) de estructura o integridad\n" % len(fallos))
        for f in fallos:
            print("  %s" % f)
        return 1

    # (3) campos que deben coincidir
    difs = [(k, A.get(k), B.get(k)) for k in DEBEN_COINCIDIR if A.get(k) != B.get(k)]
    ia, ib = A["identidad"], B["identidad"]
    difs += [("identidad." + k, ia.get(k), ib.get(k))
             for k in IDENTIDAD_DEBE_COINCIDIR if ia.get(k) != ib.get(k)]
    if difs:
        print("NO COMPARABLES: %d campo(s) que deben coincidir difieren\n" % len(difs))
        for k, va, vb in difs:
            print("  %s\n    A  %.100s\n    B  %.100s\n" % (k, va, vb))
        return 1

    print("schema  %s" % sa)
    print("codigo  generador %s | medicion %s | commit %s"
          % (ia["generator_sha256"][:12], ia["measurement_code_sha256"][:12],
             (ia["code_commit_start"] or "?")[:12]))
    print("grilla  %s | umbral material %d ns"
          % (A["umbrales"], A["umbral_material_ns"]))
    print("firewall %s | outcomes_accessed %s"
          % (A["firewall_corte_iso"], A["outcomes_accessed"]))

    print("\nMUESTRA -- se espera que difiera; es el objeto de la comparacion")
    for et, d in (("A", A), ("B", B)):
        i = d["identidad"]
        print("  %s  %-26s %3d ses  hasta %s  fechas %s  parquet %s"
              % (et, d["contrato"], d["sesiones"], d["max_fecha"],
                 (i["session_dates_sha256"] or "?")[:10],
                 (i["input_parquet_sha256"] or "?")[:10]))

    pa, pb = A["por_indicador"], B["por_indicador"]
    if set(pa) != set(pb):
        print("\nNO COMPARABLES: distinto conjunto de indicadores: %s"
              % sorted(set(pa) ^ set(pb)))
        return 1

    METRICAS = ("frac_dentro", "frac_cualquier_adelanto", "frac_adelanto_mayor_1s")
    print("\n%-15s %-12s %s" % ("indicador", "clase",
                                " ".join("%21s" % m[:21] for m in METRICAS)))
    print("%-15s %-12s %s" % ("", "", " ".join("%10s %10s" % ("A", "B")
                                               for _ in METRICAS)))
    filas = []
    for n in sorted(pa, key=lambda k: (pa[k]["clase_kernel"], k)):
        ra, rb = pa[n], pb[n]
        celdas, fila = [], {"indicador": n, "clase": ra["clase_kernel"]}
        for m in METRICAS:
            va = ra.get(m, (ra.get("reloj_de_barra_abriria_antes") or {}).get(m))
            vb = rb.get(m, (rb.get("reloj_de_barra_abriria_antes") or {}).get(m))
            fila[m] = {"A": va, "B": vb}
            celdas.append("%10s %10s" % (va, vb))
        print("%-15s %-12s %s" % (n, ra["clase_kernel"], " ".join(celdas)))
        filas.append(fila)

    print("\nCOMPARABLES: mismo esquema, misma pregunta, mismas definiciones,")
    print("misma grilla, mismo firewall, mismo codigo. Estructura e integridad")
    print("verificadas. Lo que queda son diferencias de MUESTRA y PERIODO.")

    if x.reporte:
        Path(x.reporte).write_text(json.dumps(dict(
            veredicto="COMPARABLES",
            schema_version=sa,
            codigo=dict(generador=ia["generator_sha256"],
                        medicion=ia["measurement_code_sha256"],
                        commit=ia["code_commit_start"]),
            muestras=[dict(etiqueta=e, contrato=d["contrato"],
                           sesiones=d["sesiones"], max_fecha=d["max_fecha"],
                           session_dates_sha256=d["identidad"]["session_dates_sha256"],
                           input_parquet_sha256=d["identidad"]["input_parquet_sha256"],
                           payload_sha256=d["payload_sha256"])
                      for e, d in (("A", A), ("B", B))],
            metricas=filas, outcomes_accessed=False),
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("-> %s" % x.reporte)
    return 0


if __name__ == "__main__":
    sys.exit(main())
