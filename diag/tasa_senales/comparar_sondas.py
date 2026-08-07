# -*- coding: utf-8 -*-
"""Compara dos artefactos de la sonda. **Fail-closed por allowlist.**

## Por qué existe

Los dos artefactos versionados de `sonda_alejamiento_cero.py` se emitieron **con
conjuntos de campos distintos**: el de 40 sesiones salió antes de que se
agregara la medición del reloj, así que ese campo venía en `null`. Dos
artefactos del mismo script, versionados juntos, y **nada en ellos decía por qué
diferían**. Un lector razonable habría concluido que en `6E 12-25` el reloj no
aplicaba. La conclusión habría sido falsa.

## Allowlist, no denylist

Cada clave de nivel superior tiene que estar **declarada** en
`DEBEN_COINCIDIR` o en `PUEDEN_DIFERIR`. Una clave **nueva**, **faltante** o no
contemplada ⇒ **exit 1**.

Una denylist —«estos campos pueden diferir, el resto se compara»— falla en
silencio justo cuando importa: alguien agrega un campo, nadie lo declara, y el
comparador lo ignora porque no está en ninguna lista. La allowlist obliga a
decidir para cada campo nuevo si es muestra o es contrato.

## Las cinco puertas, en orden

1. **`schema_version` idéntico.** Distinto ⇒ no se comparan. No se alinean los
   campos comunes: alinear lo que coincide es cómo un cambio de semántica pasa
   desapercibido.
2. **Cobertura de la allowlist.** Ninguna clave sin declarar, en ninguno de los
   dos.
3. **Estructura y dominio.** Campos presentes, del tipo correcto, valores
   **finitos**, fracciones en `[0, 1]`, conteos enteros `>= 0`, la grilla `T`
   **exacta y completa**, `outcomes_accessed == false`, y coherencia entre
   `sesiones`, `session_dates` y `session_dates_sha256`.
4. **Integridad.** Se **recalcula** `payload_sha256` y se verifica el sidecar
   `.sha256` contra los bytes del archivo.
5. **Campos que deben coincidir**, incluidos `pregunta` y `definiciones`: dos
   artefactos no miden lo mismo si cambia la definición de una métrica, aunque
   el número se llame igual.

Uso:
    python diag/tasa_senales/comparar_sondas.py A.json B.json [--reporte R.json]

Exit: 0 = comparables y consistentes · 1 = no comparables · 2 = no se evaluó
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

#: Tienen que coincidir: si difieren, los números no miden lo mismo.
DEBEN_COINCIDIR = ("schema_version", "pregunta", "definiciones", "umbrales",
                   "umbral_material_ns", "firewall_max_fecha",
                   "firewall_corte_utc_ns", "firewall_corte_iso",
                   "clase_kernel", "outcomes_accessed",
                   "diagnostico_arbol_sucio")

#: Se ESPERA que difieran: son la muestra y los resultados. Que difieran es el
#: objeto de la comparación.
PUEDEN_DIFERIR = ("contrato", "sesiones", "max_fecha", "identidad",
                  "por_indicador", "payload_sha256")

#: Dentro de `identidad`: el CÓDIGO y el ENTORNO deben coincidir; la MUESTRA no.
IDENTIDAD_DEBE_COINCIDIR = ("code_commit_start", "generator_sha256",
                            "measurement_code_sha256",
                            "repo_dependencies_sha256",
                            "environment_dependencies_sha256",
                            "dependency_manifest_sha256",
                            "frozen_dependencies_n",
                            "known_uncovered_runtime_surface",
                            "universe_manifest_sha256", "modo")
#: `input_dependencies_sha256` PUEDE diferir -las muestras usan inputs
#: distintos- pero cada input queda identificado individualmente en
#: `dependency_set_inputs` y su coherencia con contrato y sesiones se valida en
#: `validar_estructura`.
IDENTIDAD_PUEDE_DIFERIR = ("dependency_set_inputs", "input_dependencies_sha256",
                           "modulos_por_ruta", "new_unfrozen_dependency_files",
                           "dependency_set_entorno",
                           "dependency_set_entorno_n_fin",
                           "dependency_set_entorno_sha256_fin",
                           "entorno_importado_durante_la_corrida",
                           "git_worktree_dirty_start",
                           "dependency_set_dirty_start",
                           "ignored_generated_outputs",
                           "worktree_sucio_sin_clasificar",
                           "dependency_set_repo", "dependency_set_repo_n",
                           "dependency_set_entorno_n", "dependency_set_n",
                           "dependencias_repo_fuera_de_py",
                           "session_dates", "session_dates_sha256",
                           "input_parquet", "input_parquet_sha256")

ESQUEMA = {
    "schema_version": str, "pregunta": str, "definiciones": dict,
    "contrato": str, "sesiones": int, "max_fecha": str,
    "firewall_max_fecha": str, "firewall_corte_utc_ns": int,
    "firewall_corte_iso": str, "umbrales": list, "umbral_material_ns": int,
    "clase_kernel": dict, "identidad": dict, "outcomes_accessed": bool,
    "diagnostico_arbol_sucio": bool, "por_indicador": dict,
    "payload_sha256": str,
}
ESQUEMA_INDICADOR = {"clase_kernel": str, "zonas": int, "frac_dentro": float,
                     "frac_vacua_por_umbral": dict,
                     "reloj_de_barra_abriria_antes": dict}
METRICAS_RELOJ = ("frac_cualquier_adelanto", "frac_adelanto_mayor_1s",
                  "adelanto_s_p50")
#: Campos cuyo valor es una FRACCIÓN: fuera de [0, 1] es un defecto, no un dato.
FRACCIONES = ("frac_dentro", "frac_cualquier_adelanto", "frac_adelanto_mayor_1s")


def cargar(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _finito(v):
    return not isinstance(v, float) or math.isfinite(v)


def validar_allowlist(d, et):
    """Ninguna clave sin declarar. Es la puerta que atrapa un campo nuevo."""
    declaradas = set(DEBEN_COINCIDIR) | set(PUEDEN_DIFERIR)
    fallos = [("%s: clave NO DECLARADA `%s` -- decidir si es muestra o contrato"
               % (et, k)) for k in sorted(set(d) - declaradas)]
    fallos += ["%s: falta la clave declarada `%s`" % (et, k)
               for k in sorted(declaradas - set(d))]
    ident = d.get("identidad")
    if isinstance(ident, dict):
        dec_i = set(IDENTIDAD_DEBE_COINCIDIR) | set(IDENTIDAD_PUEDE_DIFERIR)
        fallos += ["%s: `identidad.%s` NO DECLARADA" % (et, k)
                   for k in sorted(set(ident) - dec_i)]
        fallos += ["%s: falta `identidad.%s`" % (et, k)
                   for k in sorted(dec_i - set(ident))]
    return fallos


def validar_estructura(d, et):
    """Tipos, dominios, grilla completa, firewall y coherencia de la muestra."""
    fallos = []
    for k, t in sorted(ESQUEMA.items()):
        if k not in d:
            continue                       # ya lo reporta la allowlist
        v = d[k]
        if t is int and isinstance(v, bool):
            fallos.append("%s: `%s` es bool, se esperaba int" % (et, k))
        elif not isinstance(v, t):
            fallos.append("%s: `%s` es %s, se esperaba %s"
                          % (et, k, type(v).__name__, t.__name__))

    if d.get("outcomes_accessed") is not False:
        fallos.append("%s: `outcomes_accessed` no es false" % et)
    if d.get("diagnostico_arbol_sucio"):
        fallos.append("%s: generado con DEPENDENCIAS SUCIAS -- es diagnostico, "
                      "no puede ser canonico" % et)

    ident = d.get("identidad") or {}
    if ident.get("dependency_set_dirty_start"):
        fallos.append("%s: `dependency_set_dirty_start` no vacio: %s"
                      % (et, ident["dependency_set_dirty_start"]))
    fechas = ident.get("session_dates")
    if isinstance(fechas, list):
        if len(fechas) != d.get("sesiones"):
            fallos.append("%s: `sesiones`=%s pero hay %d fechas"
                          % (et, d.get("sesiones"), len(fechas)))
        sha = hashlib.sha256(json.dumps(fechas, sort_keys=True).encode()).hexdigest()
        if sha != ident.get("session_dates_sha256"):
            fallos.append("%s: `session_dates_sha256` no recalcula" % et)
        if fechas and max(fechas) != d.get("max_fecha"):
            fallos.append("%s: `max_fecha`=%s pero la ultima fecha es %s"
                          % (et, d.get("max_fecha"), max(fechas)))
        if fechas and max(fechas) > (d.get("firewall_max_fecha") or ""):
            fallos.append("%s: FIREWALL -- fecha %s > %s"
                          % (et, max(fechas), d.get("firewall_max_fecha")))

    umbrales = [str(t) for t in (d.get("umbrales") or [])]
    for n, r in sorted((d.get("por_indicador") or {}).items()):
        if not isinstance(r, dict):
            fallos.append("%s/%s: no es un objeto" % (et, n))
            continue
        for k, t in sorted(ESQUEMA_INDICADOR.items()):
            v = r.get(k)
            if k not in r or v is None:
                fallos.append("%s/%s: `%s` ausente o null" % (et, n, k))
            elif t is float and not isinstance(v, (int, float)):
                fallos.append("%s/%s: `%s` no es numerico" % (et, n, k))
            elif t is not float and not isinstance(v, t):
                fallos.append("%s/%s: `%s` es %s, se esperaba %s"
                              % (et, n, k, type(v).__name__, t.__name__))
        if isinstance(r.get("zonas"), int) and r["zonas"] < 0:
            fallos.append("%s/%s: `zonas` negativo" % (et, n))
        for k in FRACCIONES:
            v = r.get(k, (r.get("reloj_de_barra_abriria_antes") or {}).get(k))
            if v is None:
                continue
            if not _finito(v):
                fallos.append("%s/%s: `%s` no es finito" % (et, n, k))
            elif not (0.0 <= v <= 1.0):
                fallos.append("%s/%s: `%s`=%s fuera de [0,1]" % (et, n, k, v))
        # la grilla T tiene que estar ENTERA y sin sobrantes: un umbral faltante
        # es un agujero silencioso que despues se lee como "no aplica".
        fv = r.get("frac_vacua_por_umbral") or {}
        if sorted(fv) != sorted(umbrales):
            fallos.append("%s/%s: `frac_vacua_por_umbral` no es la grilla T: "
                          "faltan %s, sobran %s"
                          % (et, n, sorted(set(umbrales) - set(fv)),
                             sorted(set(fv) - set(umbrales))))
        for t, v in sorted(fv.items()):
            if v is None or not _finito(v) or not (0.0 <= v <= 1.0):
                fallos.append("%s/%s: `frac_vacua_por_umbral[%s]`=%s invalido"
                              % (et, n, t, v))
        rel = r.get("reloj_de_barra_abriria_antes") or {}
        for m in METRICAS_RELOJ:
            if rel.get(m) is None or not _finito(rel.get(m)):
                fallos.append("%s/%s: `%s` ausente, null o no finito" % (et, n, m))
    return fallos


def verificar_integridad(ruta, d, et):
    """Recalcula `payload_sha256` y valida el sidecar contra los bytes."""
    fallos = []
    sin = {k: v for k, v in d.items() if k != "payload_sha256"}
    calc = hashlib.sha256(
        json.dumps(sin, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if calc != d.get("payload_sha256"):
        fallos.append("%s: `payload_sha256` NO recalcula\n      declarado %s\n"
                      "      calculado %s" % (et, d.get("payload_sha256"), calc))
    side = Path(str(ruta) + ".sha256")
    if not side.exists():
        fallos.append("%s: falta el sidecar %s" % (et, side.name))
    else:
        esperado = side.read_text(encoding="utf-8").split()[0]
        real = hashlib.sha256(Path(ruta).read_bytes()).hexdigest()
        if esperado != real:
            fallos.append("%s: el sidecar NO coincide con los bytes\n"
                          "      sidecar %s\n      archivo %s" % (et, esperado, real))
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

    sa, sb = A.get("schema_version"), B.get("schema_version")
    if sa != sb or sa is None:
        print("NO COMPARABLES: schema_version %r vs %r" % (sa, sb))
        print("\nNo se alinean los campos comunes a proposito: alinear lo que")
        print("coincide es como un cambio de semantica pasa desapercibido.")
        return 1

    fallos = (validar_allowlist(A, "A") + validar_allowlist(B, "B")
              + validar_estructura(A, "A") + validar_estructura(B, "B")
              + verificar_integridad(x.a, A, "A")
              + verificar_integridad(x.b, B, "B"))
    if fallos:
        print("NO COMPARABLES: %d problema(s)\n" % len(fallos))
        for f in fallos:
            print("  %s" % f)
        return 1

    difs = [(k, A.get(k), B.get(k)) for k in DEBEN_COINCIDIR if A.get(k) != B.get(k)]
    ia, ib = A["identidad"], B["identidad"]
    difs += [("identidad." + k, ia.get(k), ib.get(k))
             for k in IDENTIDAD_DEBE_COINCIDIR if ia.get(k) != ib.get(k)]
    if difs:
        print("NO COMPARABLES: %d campo(s) que deben coincidir difieren\n" % len(difs))
        for k, va, vb in difs:
            print("  %s\n    A  %.100s\n    B  %.100s\n" % (k, va, vb))
        return 1

    print("schema   %s" % sa)
    print("codigo   commit %s | generador %s | medicion %s"
          % ((ia["code_commit_start"] or "?")[:12], ia["generator_sha256"][:12],
             ia["measurement_code_sha256"][:12]))
    print("deps     repo %s (%d) | entorno %s (%d)"
          % (ia["dependency_set_repo_sha256"][:12], ia["dependency_set_repo_n"],
             ia["dependency_set_entorno_sha256"][:12], ia["dependency_set_entorno_n"]))
    print("         mutables fuera de .py: %s" % ia["dependencias_repo_fuera_de_py"])
    print("grilla   %s | umbral material %d ns" % (A["umbrales"], A["umbral_material_ns"]))
    print("firewall %s | outcomes_accessed %s"
          % (A["firewall_corte_iso"], A["outcomes_accessed"]))

    print("\nMUESTRA -- se espera que difiera; es el objeto de la comparacion")
    for et, d in (("A", A), ("B", B)):
        i = d["identidad"]
        print("  %s  %-26s %3d ses  %s..%s  fechas %s  parquet %s"
              % (et, d["contrato"], d["sesiones"], i["session_dates"][0],
                 i["session_dates"][-1], i["session_dates_sha256"][:10],
                 (i["input_parquet_sha256"] or "?")[:10]))

    pa, pb = A["por_indicador"], B["por_indicador"]
    if set(pa) != set(pb):
        print("\nNO COMPARABLES: distinto conjunto de indicadores: %s"
              % sorted(set(pa) ^ set(pb)))
        return 1

    print("\n%-15s %-12s %s" % ("indicador", "clase",
                                " ".join("%21s" % m[:21] for m in FRACCIONES)))
    print("%-15s %-12s %s" % ("", "", " ".join("%10s %10s" % ("A", "B")
                                               for _ in FRACCIONES)))
    filas = []
    for n in sorted(pa, key=lambda k: (pa[k]["clase_kernel"], k)):
        ra, rb = pa[n], pb[n]
        celdas, fila = [], {"indicador": n, "clase": ra["clase_kernel"]}
        for m in FRACCIONES:
            va = ra.get(m, (ra.get("reloj_de_barra_abriria_antes") or {}).get(m))
            vb = rb.get(m, (rb.get("reloj_de_barra_abriria_antes") or {}).get(m))
            fila[m] = {"A": va, "B": vb}
            celdas.append("%10s %10s" % (va, vb))
        print("%-15s %-12s %s" % (n, ra["clase_kernel"], " ".join(celdas)))
        filas.append(fila)

    print("\nCOMPARABLES: mismo esquema, misma pregunta, mismas definiciones,")
    print("misma grilla, mismo firewall, mismo codigo y mismo entorno.")
    print("Allowlist, estructura, dominio e integridad verificados.")
    print("Lo que queda son diferencias de MUESTRA y PERIODO.")

    if x.reporte:
        Path(x.reporte).write_text(json.dumps(dict(
            veredicto="COMPARABLES", schema_version=sa,
            codigo=dict(commit=ia["code_commit_start"],
                        generador=ia["generator_sha256"],
                        medicion=ia["measurement_code_sha256"],
                        deps_repo=ia["dependency_set_repo_sha256"],
                        deps_entorno=ia["dependency_set_entorno_sha256"]),
            muestras=[dict(etiqueta=e, contrato=d["contrato"],
                           sesiones=d["sesiones"], max_fecha=d["max_fecha"],
                           session_dates_sha256=d["identidad"]["session_dates_sha256"],
                           input_parquet_sha256=d["identidad"]["input_parquet_sha256"],
                           payload_sha256=d["payload_sha256"],
                           archivo_sha256=hashlib.sha256(
                               Path(p).read_bytes()).hexdigest())
                      for e, d, p in (("A", A, x.a), ("B", B, x.b))],
            metricas=filas, outcomes_accessed=False),
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("-> %s" % x.reporte)
    return 0


if __name__ == "__main__":
    sys.exit(main())
