---
name: edgelab-barridos-creativos
description: Diseñar y lanzar en EdgeLab una familia nueva de estrategias como barrido masivo (gramática de hipótesis, régimen declarado ex ante, grilla genérica, embudo). Usar al proponer, diseñar o acelerar campañas en el Debian.
---

# Barridos creativos con rigor (EdgeLab)

Guía completa: `docs/research/agente/PLAYBOOK_CREATIVIDAD_Y_ESCALA_20261024.md`. Reglas: `CLAUDE.md`,
`docs/research/GUIA_GRILLA_MASIVA.md`, `docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md`. Si algo de acá
contradice esas reglas, mandan ellas. Nunca cambiar gates, FDR, mandato, archivos protegidos ni el protocolo del holdout.

## 1. Arranque
1. `python tools/estado.py`; árbol limpio; rama al día con `foundation/f0b-compatibility-probe`.
2. Leer `autopilot_runs/embudo/*/MEDIDO.md` (qué está vivo) y `docs/research/LINAJES.jsonl`.

## 2. Elegir la familia (sin mirar P&L)
1. `python -m edgelab.research.agente.gramatica 8 <AAAAMMDD>` → 8 cartas lejos de lo medido y distintas entre sí.
2. Quedarse con 1–2 cartas que tengan un **mecanismo económico** escribible (quién pierde plata del otro lado). Decir por qué se
   descartan las otras.
3. Si la idea comparte mecanismo y población con una familia medida, es su descendiente: declarar el padre en `LINAJES.jsonl`
   (hereda sus pruebas en bruto). Nunca disfrazar una variante de familia nueva.

## 3. Diseñar
1. Spec en `docs/research/agente/` con `Estado:` y hash de North Star: justificación económica, cómo podría refutarse, las 8
   familias de evento enumeradas (cuál se mide y por qué; evento vs estado), régimen y perillas con `n_celdas`.
2. Régimen: como **perilla** (`from edgelab.research.agente.regimen import VARIABLES_REGIMEN, agregar`; en `disparos` hacer
   `D = agregar(D, ctx)` y sumar `VARIABLES_REGIMEN["vol_diaria"]` a `VARIABLES`) y/o por **calendario**
   (`regimen.definicion` + `regimen.actual_desde` en la campaña, antes del PREFLIGHT). Nunca elegir la ventana después de verla.
3. Perillas: las que filtran son baratas, las ejecuciones multiplican la simulación. Valores geométricos; cortes por cuantiles
   del E0 de la misma fuente; ninguna perilla muerta.
4. Objetivo mediano ≥ 3 × fricción canónica (`edgelab/costos.py`; NQ 4,6 pts, ES 2,7 pts por viaje).

## 4. Implementar (perímetro del agente)
0. **Antes de escribir nada:** `python tools/existente.py buscar "<qué hace cada pieza>"` (lectores, disparos, simulador,
   nulos, resumen por sesión ya existen: `fuentes_ticks`, `grilla_generica`, `areas_expansion.simular`, `funnel/escalera`).
   Se reutiliza lo que sirva; una función copiada hace fallar `tests/test_existente.py`.
1. Módulo `edgelab/research/agente/<x>.py` con la interfaz de la guía §6 (`NOMBRE`, `INDICADORES`, `VARIABLES`, `EJECUCIONES`,
   `EJES_ORDINALES`, `BASE`, `disparos`, `niveles`). Bucles por evento en numba en lote.
2. Opcional y recomendado con muchos disparos: `niveles_lote(D, ej, ctx)` → arreglo `(len(D), 7)` con NaN en la columna 0 donde
   `niveles` daría None. El preflight exige que sea idéntico a `niveles`.
3. Tests `tests/agente/test_<x>.py`: `test_control_ruido`, `test_control_plantado`, `test_causal` (+ `test_oraculo` si numba).
4. `python -m edgelab.research.preflight edgelab.research.agente.<x>` en verde.

## 5. Lanzar
1. Linaje en `docs/research/LINAJES.jsonl`; conteo `grilla_generica.n_celdas(exp)` por fuente y canal en el contador global
   (`TrialRegistry.ensure`) **antes** de correr.
2. Campaña `config/autopilot/grillas/campanas/<cid>.json` con `"embudo": true`, `sensor`, `ejecucion`, `desc`, `oos`, `holdout`,
   `regimen`, justificación y refutación. Va como PR (es zona `PROPUESTA`).
3. El embudo la lleva solo. No mirar resultados de una corrida lanzada con código que después se corrigió en la medición.

## 6. Cerrar
- Agregar la familia a `MEDIDO` en `edgelab/research/agente/gramatica.py` (una línea, con `ref` al acta) para que no se repropongan.
- MEDIDO/NO MEDIDO en el mismo commit que el resultado. Todo nulo publica su MDE. Terminar con «Aporte al referente: …».

## Rendimiento (si un kernel tarda)
- `python tools/bench_grilla.py` mide el núcleo. Romano-Wolf ya no recorre el tensor denso por réplica (B = 1000 es barato).
- Memoria del bootstrap: `EDGELAB_RW_MEMORIA_GB` (2) y `EDGELAB_RW_BLOQUE_MB` (1024); mismo resultado con menos memoria.
- Todas las variantes de una familia van en el mismo kernel como perillas: separar kernels cuesta cómputo y no baja la multiplicidad.
