# Canal 030 — auditoría de `58f57b9`: blockCells NT8 reales

**Fecha:** 2026-09-01

## Identidad y alcance

El commit remoto `58f57b9b177167c1cfca46b809d29e9d4254c4ce` existe en
`research/avolcluster-nq-parity-oracle-20260901` y agrega:

- CSV diagnóstico NT8 `avolcluster_v05_NQ0626_120t_DIAG_20260901.csv`;
- 22.509 líneas de diff (meta/header + 22.508 bloques reportados);
- tamaño 22.998.868 B;
- blob git `276acc7e0fd7d0dc5ae8ea1fba0254457de8770c`;
- sha256 declarado `f42e416b4ab15717a6870d1ad01d686a1e8df5c2228139727d3b288fc286289d`;
- documento de diagnóstico y corrección del informe previo.

El parche que produjo el export está versionado en `78b5c94`: agrega un writer
opcional, apagado por defecto, después de la detección. No cambia `blockCells`, mediana,
clustering ni `CreateZone`; por eso no corresponde reejecutar el gate todavía.

## Qué queda confirmado

Para `py_id=372 / nt8_id=413`, el mecanismo de la divergencia **sí pasa de inferencia a
dato observado a nivel de bloque**:

- Python: 66 celdas, mediana 6, hot-threshold 12;
- NT8: 53 celdas, mediana 10, hot-threshold 20;
- NT8 carece de 13 niveles del extremo inferior presentes en Python;
- el volumen total de esos niveles es 31;
- `selected_count=17`, ancho 18 y densidad `17/18=0,944444…` cierran con el oráculo;
- el incremento de threshold explica el corte del cluster y el outlier geométrico de 8
  ticks.

Por lo tanto, para **este caso**, no hay bug de traducción del clustering: la entrada a
ese algoritmo ya es distinta.

Los casos `nt8_id=9` y `nt8_id=27` muestran además que diferencias pequeñas de volumen
en celdas compartidas pueden mover mediana y geometría. El caso 9 agrega un nivel
faltante; el 27 no presenta niveles faltantes.

## Dos límites que deben conservarse

### 1. Tres casos no prueban los 19 “en general”

La muestra es deliberada: el outlier máximo y dos casos típicos. Confirma que el
mecanismo existe y explica esos tres, pero no estima su frecuencia ni demuestra que sea
la causa de los 19 `GEOMETRY_DIFF`. El propio caso 27 no tiene pérdida de borde: sólo
ruido de valores. La formulación válida es **“mecanismo confirmado en tres casos con dos
subtipos”**, no “causa general confirmada”.

### 2. El punto exacto `Low[0]/High[0]` todavía es atribución causal plausible

Que NT8 pierda niveles de borde es consistente con el filtro leído en el `.cs`, pero el
CSV observa el estado final de `blockCells`; no registra cada tick rechazado por esa
línea. Para atribuir la pérdida específicamente a ese filtro —y no a otra diferencia
aguas arriba— hace falta una de estas dos pruebas:

1. contador/traza de ticks descartados por `kv.Key < lowTick || kv.Key > highTick`, con
   timestamp, precio, volumen y barra; o
2. corrida A/B target-free con el filtro sólo instrumentado/desactivado, verificando que
   reaparecen exactamente los niveles faltantes.

No hace falta tocar outcomes ni holdout para esa prueba.

## Siguiente orden de trabajo

Con el CSV ya producido, extender **sin nueva corrida pesada** el cruce a:

1. los 19 `GEOMETRY_DIFF` completos;
2. los cuatro `MISSING_IN_NT8` con ratio >1,30;
3. los 53 `MISSING_IN_NT8` restantes, clasificando al menos por decisión NT8,
   score/threshold y diferencia temporal;
4. si el matching temporal de un bloque es ambiguo, marcarlo `UNRESOLVED`, no elegir el
   vecino conveniente.

Salida machine-readable, una fila por caso:

`class, py_id, nt8_id, timestamp_delta_ms, n_cells_py, n_cells_nt8,
only_py_count, only_nt8_count, median_py, median_nt8, hot_threshold_py,
hot_threshold_nt8, selected_geometry_py, selected_geometry_nt8,
nt8_decision, mechanism_class, evidence_level`.

Clases mínimas: `EDGE_LEVELS_MISSING`, `SHARED_CELL_VALUE_NOISE`, `BOTH`,
`THRESHOLD_HISTORY_DIFF`, `TIME_MATCH_AMBIGUOUS`, `UNRESOLVED`.

## Estado de paridad

- Gate formal: **FAIL**.
- Outlier 372/413: causa de bloque confirmada.
- Generalización a los 19/57: pendiente de censo completo.
- Atribución a la línea exacta del filtro: pendiente de traza causal o A/B.
- Tolerancia representativa: todavía no se decide; primero se necesita la distribución
  completa del residual, no tres ejemplos.

**Aporte al referente:** convierte el mayor outlier en una causa observada sin inflar
n=3 a una ley general, separa “la entrada al clustering difiere” de “esta línea exacta
la descartó”, y reduce el próximo paso a un cruce target-free sobre un CSV ya generado,
sin rerun del gate ni apertura de outcomes.
