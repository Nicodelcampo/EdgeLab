#!/usr/bin/env python3
"""Barrido ESTÁTICO de la regla de diseño: ningún umbral de precio en `double`.

Regla (contrato de paridad §5, promovida a regla de diseño el 2026-07-26 por
decisión de Nico):

    Todo umbral de precio se compara en ÍNDICES ENTEROS DE TICK.
    Los `double` sólo para I/O: leer del feed, escribir al CSV, dibujar.

Por qué existe: la familia lleva **cuatro** apariciones, cada una en una
expresión distinta, y las cuatro se descubrieron gastando un oráculo. Buscarlas
leyendo código ya falló una vez (AUDIT-001 marcó como NULO la que resultó ser la
causa raíz de HFTZones2). Esto no reemplaza a `ulp_exposure.py` —que MIDE— sino
que lo precede: encuentra los candidatos para medir.

Heurística: una comparación es sospechosa si enfrenta dos expresiones que
involucran precios (`Close[0]`, `price`, `z.Upper`, `_swH`, …) o aritmética con
`TickSize`, **sin** pasar por `PriceToTick`/índices enteros.

Uso:  python tools/ulp_sweep.py [ruta_o_directorio ...]
Salida: una fila por candidato. 0 si no hay ninguno.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# Identificadores que representan un PRECIO (double) en los .cs del proyecto.
# Se agregan `top`/`bot`/`hi`/`lo` tras el barrido del 2026-07-26: sin ellos el
# detector se perdía `if (top - bot < ExpansionMinTicks * TickSize)`, que es
# exactamente la forma que se está buscando. Un detector que no se audita a sí
# mismo hereda el modo de falla de AUDIT-001.
PRECIO = r"(?:Close|Open|High|Low)\s*\[\s*\d+\s*\]|price|Price|_sw[HL]|" \
         r"z\.(?:Upper|Lower)|upper|lower|rowPrice|closePrev|openCurr|" \
         r"poc[A-Za-z]*Price|wick(?:Hi|Lo)[A-Za-z]*|gapPts|centroid|" \
         r"\btop\b|\bbot\b|\bhi\b|\blo\b|\bpiv[A-Za-z]*\b|" \
         r"\bz(?:Lo|Hi)\b|\bclose\b|\bopen\b|askQ|bidQ"
# Marcas de que YA está en dominio entero: si aparecen, no es candidato.
# OJO: ni `TickSize` ni `MinDiffTicks` deben contar como "ya es entero" — al
# contrario, `N * TickSize` es la forma CANÓNICA del bug. `Tick\b` no matchea
# dentro de `TickSize` ni de `MinDiffTicks` (no hay borde de palabra), que es
# justo lo que se quiere: esas líneas siguen siendo candidatas.
ENTERO = r"PriceToTick|Tick\b|tick\b|HalfTick|\blong\b|\(long\)|Math\.Round"

CMP = re.compile(r"[^<>=!]([<>]=?|==|!=)[^=]")
TIENE_PRECIO = re.compile(PRECIO)
TIENE_ENTERO = re.compile(ENTERO)
TICKSIZE = re.compile(r"TickSize|tick_size")


def _sin_comentario(linea: str) -> str:
    i = linea.find("//")
    return linea[:i] if i >= 0 else linea


def barrer(path: str):
    """Devuelve [(linea_nro, texto, motivo)] de candidatos."""
    out = []
    try:
        txt = open(path, encoding="utf-8-sig").read()
    except (OSError, UnicodeDecodeError) as e:
        return [(0, str(e), "no legible")]
    # no auditar la region generada por NT8: es codigo de NT8, no nuestro
    corte = txt.find("#region NinjaScript generated code")
    if corte > 0:
        txt = txt[:corte]
    for n, raw in enumerate(txt.splitlines(), 1):
        linea = _sin_comentario(raw)
        if not CMP.search(linea) or not TIENE_PRECIO.search(linea):
            continue
        if TIENE_ENTERO.search(linea):
            continue          # ya está en enteros (o redondea antes de comparar)
        motivo = ("umbral construido con TickSize" if TICKSIZE.search(linea)
                  else "comparacion directa entre precios")
        out.append((n, raw.strip(), motivo))
    return out


# ---------------------------------------------------------------------------
# Triaje sellado. Un detector que sólo lista 47 candidatos no es un gate: nadie
# lo va a leer dos veces. Lo útil es el DELTA — que falle cuando aparece una
# expresión que nunca se clasificó. Cada candidato se sella una vez, con
# veredicto y evidencia, y desde ahí el barrido es un detector de regresión.
#
# Veredictos admitidos (no se inventan nuevos sin pasar por el contrato):
#   INMUNE_MONOTONO  ambos operandos son precios de grilla llevados SIN
#                    aritmética. feed() y ticks*ts son ambas estrictamente
#                    monótonas en el índice de tick ⇒ el orden y los empates se
#                    preservan. Es el único caso donde "los dos son precios"
#                    alcanza como argumento.
#   INMUNE_MEDIOTICK el umbral vive a medio tick de la grilla ⇒ ningún precio
#                    negociable cae exactamente encima ⇒ empate imposible.
#   CORREGIDO        estuvo expuesto y ya se pasó a enteros. Se deja sellado
#                    para que un revert quede visible.
#   EXPUESTO_PENDIENTE  exposición MEDIDA > 0 y la corrección exige una decisión
#                    de diseño que Nico todavía no tomó.
#   FUERA_DE_ALCANCE la expresión vive en una capa que NO se porta a Python
#                    (visual/offline) ⇒ no puede romper paridad hoy.
#   NO_ES_PRECIO     falso positivo: son índices de array o pesos acumulados
#                    dentro de un helper. El detector matchea `lo`/`hi`/`mid`
#                    por nombre. Se sella igual: si mañana un helper empieza a
#                    comparar precios, la expresión cambia y vuelve a saltar.
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "ulp_sweep_baseline.json")
VEREDICTOS = {"INMUNE_MONOTONO", "INMUNE_MEDIOTICK", "CORREGIDO",
              "EXPUESTO_PENDIENTE", "FUERA_DE_ALCANCE", "NO_ES_PRECIO"}


def clave(archivo, texto):
    """Identidad estable de un candidato: archivo + expresión normalizada.

    Deliberadamente NO incluye el número de línea: agregar un comentario arriba
    no debe reabrir un triaje ya sellado.
    """
    return "%s :: %s" % (os.path.basename(archivo), re.sub(r"\s+", " ", texto).strip())


def main(argv=None):
    import json
    ap = argparse.ArgumentParser(description="Barrido estatico de la regla de enteros")
    ap.add_argument("paths", nargs="*", default=[], help=".cs o directorios")
    ap.add_argument("--baseline", action="store_true",
                    help="fallar solo ante candidatos NO triajeados (modo gate)")
    ap.add_argument("--emit-skeleton", action="store_true",
                    help="imprime el JSON de los candidatos sin veredicto")
    a = ap.parse_args(argv)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = a.paths or [os.path.join(repo, "nt8")]

    archivos = []
    for p in paths:
        if os.path.isdir(p):
            archivos += [os.path.join(p, f) for f in sorted(os.listdir(p))
                         if f.endswith(".cs")]
        else:
            archivos.append(p)

    sellado = {}
    if os.path.exists(BASELINE):
        sellado = json.load(open(BASELINE, encoding="utf-8"))["triaje"]

    print("=" * 88)
    print("BARRIDO ULP — regla: ningun umbral de precio se compara en double")
    print("=" * 88)
    total = 0
    nuevos, vistos = [], set()
    for f in archivos:
        hits = barrer(f)
        if not a.baseline:
            print("\n%s  ->  %d candidato(s)" % (os.path.basename(f), len(hits)))
        for n, txt, motivo in hits:
            total += 1
            k = clave(f, txt)
            vistos.add(k)
            v = sellado.get(k, {}).get("veredicto")
            if v is None:
                nuevos.append((k, n, txt, motivo))
            if not a.baseline:
                print("   L%-5d %-52s  [%s]" % (n, txt[:52], v or "SIN TRIAJE"))

    if a.emit_skeleton:
        print(json.dumps({k: dict(veredicto="", evidencia="")
                          for k, _, _, _ in nuevos}, indent=2, ensure_ascii=False))
        return 0

    print("\n" + "-" * 88)
    print("candidatos: %d   triajeados: %d   SIN TRIAJE: %d"
          % (total, total - len(nuevos), len(nuevos)))

    malos = [k for k, d in sellado.items()
             if d.get("veredicto") not in VEREDICTOS]
    if malos:
        print("\nveredicto invalido en el baseline:")
        for k in malos:
            print("   %s" % k)

    # Un sellado que ya no matchea ninguna línea = la expresión cambió. Eso NO
    # es un fallo (puede ser justamente la corrección), pero tiene que verse.
    huerfanos = [k for k in sellado if k not in vistos]
    if huerfanos:
        print("\nsellados que ya no aparecen en el codigo (expresion modificada):")
        for k in huerfanos:
            print("   %s" % k)

    if nuevos:
        print("\nFAIL — expresiones nuevas sin clasificar:")
        for k, n, txt, motivo in nuevos:
            print("   L%-5d %s" % (n, txt[:70]))
            print("          clave: %s" % k)
        print("\nCada una hay que MEDIRLA (tools/ulp_exposure.py) y sellarla en")
        print("%s. Un candidato NO es un bug: los bordes a" % BASELINE)
        print("medio tick son inmunes por construccion. Pero el que no se mide, no se sabe.")
        return 1
    if malos:
        return 1
    print("\nOK — ninguna expresion nueva sin clasificar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
