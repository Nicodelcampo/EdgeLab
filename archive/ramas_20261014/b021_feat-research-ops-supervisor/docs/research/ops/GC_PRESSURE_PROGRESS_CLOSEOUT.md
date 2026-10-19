# GC: presión y avance continuos — resultado descriptivo terminado

## Decisión
Hay población observable suficiente para diseñar una evaluación nueva: **44.374 anclas elegibles y 6.581 pares de ventanas sin solapamiento**, en las seis fechas originales de training. Esto **no** es edge, predicción, potencia ni episodios independientes. El censo prelabel coincide exactamente con el anterior: 76.284 observadas, 31.910 UNKNOWN, A_ONLY=2 y BOTH=0. No se cambió la definición A, la calibración ni la fuente.

Con avance dirigido previo ≥4 ticks, se observaron **3.180 pares sin solapamiento**: **1.292** con avance actual <−2; **637** con neto actual [−2,2); **1.251** con avance actual ≥2. Son tres categorías disjuntas del mismo subconjunto, no secuencia de éxito ni resultados futuros. Los 637 no son “absorciones nuevas”: no exigen presión alta ni confinamiento de rango/recorrido.

El descriptor presión actual ≥q80 y neto pequeño tiene **1.324 anclas /166 pares sin solapamiento**. Sigue siendo mucho más escaso que la población continua general; no asumir que cada hipótesis tiene el soporte general ni quitar requisitos para rescatar A.

| Fecha | Anclas elegibles | Pares sin solapamiento | Previo ≥4 → actual <−2 | Previo ≥4 → actual [−2,2) | Previo ≥4 → actual ≥2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2026-08-03 | 5,077 | 845 | 153 | 73 | 166 |
| 2026-08-04 | 5,428 | 861 | 131 | 106 | 135 |
| 2026-08-05 | 9,519 | 1,324 | 258 | 132 | 253 |
| 2026-08-06 | 8,376 | 1,225 | 262 | 110 | 258 |
| 2026-08-07 | 8,757 | 1,233 | 257 | 115 | 242 |
| 2026-08-10 | 7,217 | 1,093 | 231 | 101 | 197 |

Cada par describe 20 s previos +20 s actuales, terminados en la ancla, elegidos primero por fecha con separación ≥40 s. No está garantizada independencia temporal ni entre fechas. OTHER/RTH conserva la clasificación horaria previa, no certifica calendario particular de GC.

## Presión no equivale siempre a avance en su dirección
La correlación descriptiva presión/avance absoluto fue positiva en las **24 celdas fecha×fase×dirección**, rango **0,2543–0,6662**. Pero presión/avance dirigido fue negativa en **3/24** y positiva en 21/24, rango **−0,2625–0,5325**. Mayor presión se asocia con magnitud de movimiento, no uniformemente con avanzar en la dirección del flujo. No es causalidad o resultado futuro; las ventanas del censo completo se solapan.

Excepciones de signo para presión/avance dirigido:

| Fecha | Celda | Pearson descriptivo |
| --- | --- | ---: |
| 2026-08-03 | RTH:1 | -0.0027 |
| 2026-08-04 | OTHER:-1 | -0.1192 |
| 2026-08-07 | OTHER:-1 | -0.2625 |

La razón de presión/avance dirigido también tiene **2/24 celdas negativas**, rango −0,1653–0,4007. Todas las matrices 20/25, ceros, cuantiles y desgloses quedan en el recibo/CSV; no se promedian cuantiles ni correlaciones de sesiones para fabricar un pooled.

## Ejecución y pruebas
- Kaggle privado CPU **138608300/v1**, `edgelab-gc-pressure-progress-atlas-v1`: COMPLETE, una intención /un job /un poll. Fuente `5877f6587c0e374f404813323051bc1799538b52`, bundle `d641f6aa0ee462a9b806205bb99a8253aae903d0f8a5aae592e2643b3e9de902`, plan `95a9012db0b498cb783600b7aed0dd956b6669fe5dece304ba4a9c98ad771d37`.
- Recibo **160.283 bytes**, SHA `3886162c19d2a03d535c0cee53d7dda84ad4e186c48f61bcaf3e903936646f84`. Revisor: PASS_TARGET_FREE_CONTINUOUS_SUPPORT_AGGREGATE_RECONCILIATION_NOT_EDGE. Verifica hashes, alcance, censos, matrices/márgenes por fecha/celda y paridad anterior; **no reconstruye tape en host ni audita independientemente todos los momentos/cuántiles**.
- **707.465 ticks**, seis training. Runner **24.258 s**; boot con transporte **28.086 s**. RSS muestreado 189.833.216 bytes, no certificado del pico real. La carga anterior era distinta: **no se reclama speedup**.
- Prelaunch: **15 focales /969 ResearchOps /18 navegación PASS**; catálogo PASS_NAVIGATION_ONLY. Tests negativos de outcomes, holdout/plan/calibración, orden/UNKNOWN, rejillas, no solapamiento y startup aislado. La regresión corresponde al código fuente prelaunch, no a documentos añadidos en cierre. Después: **15 focales PASS**, con rechazo adicional del recibo parseado que no coincide con sus bytes sellados; runner/recibo originales intactos. Reproducción portable exacta de datos/CSV/spec; el orden de claves JSON no cambia el resultado.
- Código, protocolo, agregados, revisor, script portable, propuesta de conocimiento y journals/snapshot registrados. Journals originales `/data/operational-state/gc-pressure-progress-95a9012db0b4-{dispatch,watch}.sqlite`; **no reconstruirlos desde JSON ni resetear/reenviar**.

## Próximo hito y aporte al referente
1. Pasar de un proxy casi vacío a una representación medible, preservando sus negativos. El soporte de trayectorias da una pregunta investigable, no la respuesta económica.
2. Usar el revisor target-free como un paso verificable del ciclo pregunta→evidencia→memoria propuesta→nueva decisión. Readiness conserva `evaluation_authorized=False`; no autoaprobar Brain/edge.
3. Antes de nuevos outcomes: inspeccionar linaje de splits, fuente elegible y diseñar evaluación disjunta con baseline de componentes brutos y control de igual capacidad. Ventanas de agosto y septiembre ya declaradas/inspeccionadas no se venden como vírgenes; `GC_PRESSURE_PROGRESS_NEXT_DECISION.json` es diseño no enviado, no un plan aprobado.
4. No multiplicar configuraciones o combinar zonas todavía. Medir información incremental sobre baseline antes de mezclar AVZPOI2/BigTrap. En paralelo, el agente local resuelve la release líquida y sus problemas de procedencia/calendario según el reporte de reparación.

EdgeBrain: `GC_PRESSURE_PROGRESS_KNOWLEDGE_PROPOSAL.json` sigue PROPOSED_NOT_CANONICAL. Sin outcomes/P&L, holdout desde octubre, nuevos umbrales, modelos, QA general, merge, daemon Debian/24×7 o escritura canónica. COMPLETE es de esta campaña, no declaración de estado global de Kaggle.

## Reproducción de agregados
Desde raíz (no requiere ticks):

```bash
python tools/research_ops/audits/summarize_gc_pressure_progress.py prepare --raw docs/research/evidence/gc-pressure-progress/raw --out /tmp/gc-pressure-progress --ops /tmp/gc-pressure-progress-ops
python tools/research_ops/audits/summarize_gc_pressure_progress.py analyze --raw docs/research/evidence/gc-pressure-progress/raw --out /tmp/gc-pressure-progress --ops /tmp/gc-pressure-progress-ops
```

El profiler no admite directamente el JSON anidado: se normalizó a cuatro CSV con claves compuestas y cero duplicados. POOLED_TRAINING no se suma a las fechas. BOTH=0 y undefined_if_constant=False son constantes legítimas de este recibo, no imputaciones. El primer build del gráfico rechazó `version` ausente; se agregó versión1, sin cambiar datos, y el preflight canónico pasó.
