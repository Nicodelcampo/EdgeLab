# -*- coding: utf-8 -*-
"""Detector adversarial de look-ahead. **Target-free**: no mira P&L ni retornos.

## La prueba definitiva, y por qué es mejor que un AUC sospechoso

La forma habitual de detectar look-ahead es indirecta: entrenás, ves un AUC de
0,9997 y sospechás. Eso tiene dos defectos graves. Llega **tarde** —después de
haber corrido una búsqueda sobre retornos, que acá está bajo STOP— y **no
prueba nada**: un AUC alto puede ser leak o puede ser un edge real, y un AUC
bajo no descarta un leak chico que igual invalida el resultado.

La prueba directa no necesita ninguna etiqueta:

> **Invariancia por truncamiento.** Si `f` es causal, entonces para todo `t`
>
>     f(datos[:t+1])[t]  ==  f(datos_completos)[t]
>
> Una función que mira hacia adelante **no puede** cumplir esto: al truncar, lo
> que miraba deja de existir y el valor cambia.

Es una prueba **positiva** de causalidad, no una sospecha. Y corre sobre datos
sintéticos, así que no consume oráculo ni toca el holdout.

## Costo y muestreo

Verificar todos los `t` cuesta O(n²). Se muestrean `n_probes` posiciones. El
muestreo es **determinista** (LCG propio, misma familia que `research/g2.py`)
porque un test que falla sólo a veces se termina desactivando.

Un detalle que importa: hay que probar cerca del **final** de la serie. Un leak
de 1 barra es invisible en el medio si la ventana es larga, pero en las últimas
posiciones no tiene dónde esconderse. `probe_positions` sesga hacia el final a
propósito.
"""
from __future__ import annotations


class CausalityViolation(AssertionError):
    """Se probó que la función mira hacia adelante."""


def _lcg(seed):
    """Congruencial lineal — sin numpy.random, para no depender del estado global."""
    x = seed & 0xFFFFFFFF
    while True:
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        yield x


def probe_positions(n, n_probes=24, seed=20260726, tail_frac=0.4):
    """Posiciones a verificar, deterministas y sesgadas hacia el final.

    `tail_frac` de las sondas caen en el último 10 % de la serie: ahí es donde
    un look-ahead de pocas barras queda sin margen para esconderse.
    """
    if n <= 2:
        return list(range(n))
    n_probes = min(n_probes, n)
    n_tail = max(1, int(n_probes * tail_frac))
    tail0 = max(1, int(n * 0.9))
    g = _lcg(seed)
    pos = set()
    for _ in range(n_tail * 4):
        if len(pos) >= n_tail:
            break
        pos.add(tail0 + next(g) % max(1, n - tail0))
    for _ in range((n_probes - len(pos)) * 6):
        if len(pos) >= n_probes:
            break
        pos.add(1 + next(g) % (n - 1))
    return sorted(p for p in pos if 0 <= p < n)


def assert_causal(fn, data, *, n_probes=24, seed=20260726, eq=None,
                  nombre="feature"):
    """Verifica invariancia por truncamiento. Levanta `CausalityViolation`.

    `fn(subserie) -> lista alineada a la subserie`. Se compara el ÚLTIMO valor de
    `fn(data[:t+1])` contra el valor en `t` de `fn(data)`.

    `eq` permite comparar con tolerancia si el modelo es estocástico — pero ojo:
    un modelo con muestreo no-sembrado **falla este test por no ser
    reproducible**, y eso es un hallazgo, no un falso positivo. Sembrar y volver
    a correr.
    """
    if eq is None:
        def eq(a, b):
            if a is None or b is None:
                return a is b
            if isinstance(a, float) and isinstance(b, float):
                return (a != a and b != b) or a == b   # NaN == NaN cuenta igual
            return a == b

    completo = list(fn(data))
    if len(completo) != len(data):
        raise CausalityViolation(
            "%s: fn devolvió %d valores para %d filas — no está alineada."
            % (nombre, len(completo), len(data)))

    fallas = []
    for t in probe_positions(len(data), n_probes, seed):
        parcial = list(fn(data[:t + 1]))
        if not parcial:
            fallas.append((t, "vacío", completo[t]))
            continue
        if not eq(parcial[-1], completo[t]):
            fallas.append((t, parcial[-1], completo[t]))

    if fallas:
        det = "\n".join(
            "    t=%-6d truncado=%-20r completo=%-20r" % f for f in fallas[:8])
        raise CausalityViolation(
            "%s MIRA HACIA ADELANTE.\n"
            "Con la serie truncada en t el valor cambia, o sea que el valor "
            "'de t' usaba datos posteriores a t.\n"
            "%d de %d sondas fallaron:\n%s\n"
            "Causa habitual: unir la salida del modelo por `target_ts` en vez de "
            "por `available_at`, o un rolling/expanding centrado."
            % (nombre, len(fallas), min(n_probes, len(data)), det))
    return True


def assert_store_causal(store, index_ns, key, *, nombre="feature"):
    """Verifica que una serie servida por `PITFeatureStore` sea causal.

    Redundante con la invariante del store — a propósito. El store la garantiza
    *por construcción*, y este test la verifica *por comportamiento*. Si alguien
    optimiza `as_of` y rompe el `bisect`, la garantía estructural se evapora en
    silencio y sólo queda esto.
    """
    def fn(idx):
        return store.series(idx, key)
    return assert_causal(fn, list(index_ns), nombre=nombre)


def diagnose_join(pred_index_ns, generated_at_ns):
    """Diagnostica el error de `join` más común, antes de que llegue al store.

    Se le pasan el índice con que el modelo devolvió sus predicciones y los
    instantes de generación reales. Si coinciden, el índice **es** el instante de
    generación y unir por él está bien. Si el índice está corrido hacia adelante,
    es `target_ts` y unir por él mete look-ahead de `horizon` barras.
    """
    if len(pred_index_ns) != len(generated_at_ns):
        return dict(ok=False, code="LARGOS_DISTINTOS",
                    detalle="%d vs %d" % (len(pred_index_ns), len(generated_at_ns)))
    adelantos = [int(a) - int(b) for a, b in zip(pred_index_ns, generated_at_ns)]
    peor = max(adelantos) if adelantos else 0
    if peor <= 0:
        return dict(ok=True, code="INDICE_ES_GENERATED_AT", max_adelanto_ns=peor)
    return dict(
        ok=False, code="INDICE_ES_TARGET_TS", max_adelanto_ns=peor,
        n_adelantadas=sum(1 for a in adelantos if a > 0),
        detalle=("el índice de las predicciones está hasta %.1f s por delante del "
                 "instante en que se generaron. Unir por ese índice le da a cada "
                 "barra una predicción hecha con datos de esa misma barra o "
                 "posteriores." % (peor / 1e9)))
