# BigTrap2 — adjudicación con nulo exactamente igualado por geometría

**Estado:** `PREREGISTERED_NOT_RUN`  
**Fecha:** 2026-08-11  
**Rama:** `research/bigtrap2-distance-matched-null`  
**Base fijada:** `audit/p0-bigtrap2-drift@ef83794d9b6c074cbeeee6ce8f4715c9f907f060`  
**NORTH_STAR:** el ejecutor debe calcular y publicar el SHA-256 completo de `docs/NORTH_STAR.md`; prefijo esperado `21bb3b01a33e2b37`  
**Outcomes/P&L/holdout:** prohibidos; `outcomes_accessed=false`

## 1. Decisión que motiva esta campaña

F1.1 publicó una brecha pareada de toque de aproximadamente 47 puntos porcentuales: BigTrap2 real 97,9 % frente a nulo-B 50,6 %, en 201/201 sesiones. La auditoría posterior encontró que esa comparación no adjudica distancia:

- el nulo-B histórico elige `close_t[j]` con `j = created_bar ± 180`, pero conserva como origen temporal el `created_bar` real;
- su distancia realizada al precio de creación tuvo mediana 13 ticks y p90 46 ticks;
- para las zonas reales, el seguimiento publicado informó 86,6 % a 0–2 ticks;
- estratificar la tasa del nulo por **su propia** distancia no crea pares real↔nulo con la misma geometría.

Por lo tanto, “la brecha de 47 pp es atracción” y “la brecha es sólo distancia” permanecen ambas como hipótesis. Esta campaña decide únicamente cuál de esas dos lecturas resiste un control geométrico exacto.

## 2. Auditoría del código histórico que no debe corregirse retroactivamente

Los artefactos F1.1 anteriores se conservan inmutables. La nueva implementación no debe reutilizar ciegamente estas funciones:

1. `F1_nulo_zonas_aleatorias.py::vida_de_zona` corta el slice en `created_bar + max_age_bars`, pero busca expiración con `edad > max_age_bars`; por eso el nulo histórico nunca clasifica `max_age` y lo deja censurado.
2. `F1.1_seguimiento.py::tocada_en_horizonte` busca intersecciones hasta K aunque la zona nula se hubiera eliminado antes por `close_through_gap`; no replica el lifecycle para horizontes cortos.
3. Nulo-B y nulo-C cambian la distancia al reanclar en otro `close`, y no igualan hora, volatilidad ni horizonte disponible zona por zona.

Estos puntos son predicciones verificables para tests truth-known. No autorizan reescribir resultados históricos; el nuevo artefacto debe explicar por qué no es comparable por identidad de implementación.

## 3. Pregunta y condición de refutación

> Manteniendo exactamente la geometría relativa de cada zona BigTrap2 y comparándola con tiempos de control de la misma hora y régimen causal, ¿la probabilidad de primer toque antes de la eliminación sigue siendo mayor en el timestamp donde ocurrió el evento BigTrap2?

- **Refuta la lectura fuerte de atracción:** el IC 95 % del residual pareado por sesión contiene 0.
- **Evidencia residual positiva:** el límite inferior del IC 95 % es mayor que 0.
- **Evidencia residual negativa:** el límite superior es menor que 0.

Ninguna etiqueta implica edge, dirección, retorno ni rentabilidad.

## 4. Event-space congelado

Se enumeran antes de construir la población:

- creación de zona;
- aproximación sin toque;
- primer toque;
- toque n-ésimo;
- invalidación `close_through` y `close_through_gap`;
- expiración por edad;
- censura administrativa por fin de datos;
- estado activo por barra.

**Población elegida:** todas las zonas creadas por BigTrap2, sin `sep_min`, sin condicionar por toque ni desenlace. Los demás estados se conservan como denominadores/diagnósticos, no como poblaciones alternativas ocultas.

## 5. Universo congelado

- Instrumento: 6E.
- Bar spec: `time:1` solamente.
- Indicador: kernel Python BigTrap2 declarado v2.2, defaults exactos.
- Universo: las mismas 201 sesiones de research usadas por F1.1, máximo 2026-06-30.
- Holdout 2026-07-01→2026-12-31: no se abre.
- `tick:25`: excluido; no tiene PASS P1/P2 documentado.
- Paridad v2.5.1: `PENDING`; todo artefacto debe citar el WARN de PR #10.
- Sin grilla de parámetros y sin selección posterior a resultados.

## 6. Geometría exacta y disponibilidad

Para la zona fuente i creada al cierre de la barra B:

```text
close_i = close_t[B]
rel_lo_i = lo_tick_i - close_i
rel_hi_i = hi_tick_i - close_i
height_i = rel_hi_i - rel_lo_i + 1
```

La zona sólo está disponible desde B+1. Para un control en barra J:

```text
null_lo_ij = close_t[J] + rel_lo_i
null_hi_ij = close_t[J] + rel_hi_i
```

Así se preservan **exactamente**, por construcción:

- altura;
- distancia firmada al precio;
- lado geométrico;
- posición relativa cuando la zona contiene el close;
- resolución en ticks enteros.

No se permite `round()` independiente de top/bottom: se revierte el padding de medio tick con la misma convención verificada por los tests existentes.

## 7. Selección de barras de control

### 7.1 Pool admisible

Para cada zona fuente:

- misma 6E y mismo contrato;
- otra sesión distinta de la sesión fuente;
- mismo índice de minuto dentro de la sesión;
- barra sin creación BigTrap2;
- suficientes barras futuras para evaluar exactamente el horizonte de la fuente;
- covariables calculadas únicamente con información disponible al cierre de J.

### 7.2 Covariables causales

- `sigma60_ticks = sqrt(mean(diff(close)^2))` usando las 60 diferencias que terminan en la barra B/J;
- `log1p(bar_volume)` de la barra B/J, disponible al cierre;
- minuto de sesión y contrato son exact-match, no entran al score.

### 7.3 Matching determinista

- Tomar `K=8` controles más cercanos por distancia euclídea robustamente estandarizada en `log1p(sigma60_ticks)` y `log1p(bar_volume)`.
- Escala: MAD del pool candidato; si MAD=0, esa covariable aporta 0 al score.
- Desempate estable por `(score, session_date, bar_index)`.
- Mínimo `MIN_CONTROLS=5`; con menos, la zona se abstiene y se reporta.
- Un control puede servir a varias zonas; la inferencia nunca trata las zonas como independientes.

### 7.4 Gates de balance

La campaña completa queda `ABSTAIN_MATCHING` si cualquiera ocurre:

- cobertura de zonas con ≥5 controles <95 %;
- `|SMD| > 0,10` para `log1p(sigma60_ticks)`;
- `|SMD| > 0,10` para `log1p(bar_volume)`;
- no hay 201 sesiones fuente con al menos una zona evaluable;
- la igualdad exacta de minuto o geometría falla una sola vez.

Los umbrales no pueden relajarse después de ver resultados.

## 8. Lifecycle truth-known

Una función nueva y pura debe devolver, desde B/J+1 y hasta el horizonte común:

- `first_touch_age`;
- `removed_age`;
- `removed_reason`;
- `touched_before_removal`;
- `censored`.

Precedencia por barra idéntica al kernel:

1. expiración si `age > max_age_bars`;
2. registrar toque si hay intersección;
3. invalidar por `FirstTouch`, `CloseThrough` o `max_touches` según parámetros;
4. un `close_through_gap` previo al primer toque impide contar intersecciones posteriores.

Con defaults `CloseThrough`, un toque y una invalidación pueden ocurrir en la misma barra; el toque cuenta porque el kernel lo registra primero. El horizonte primario de cada zona es:

```text
H_i = min(2000, barras futuras disponibles para la zona real)
```

Cada control debe disponer de al menos `H_i` y se evalúa con el mismo `H_i`.

## 9. Estimand e inferencia pre-registrados

### 9.1 Primario — adjudica exactamente F1.1

Para cada zona i:

```text
y_i = 1 si la zona real toca antes de remoción/censura dentro de H_i
p0_i = media de los K controles equivalentes
r_i = y_i - p0_i
```

Para cada sesión s se calcula `R_s = mean(r_i)` sobre sus zonas. El estimand es:

```text
Delta_matched = mean_s(R_s)
```

Las sesiones tienen igual peso. Una sesión con más zonas no gana más peso.

### 9.2 Inferencia primaria

- n esperado: 201 sesiones;
- HAC Bartlett sobre `R_s`, ordenadas cronológicamente;
- lag fijado: `ceil(sqrt(n_sessions))`;
- IC 95 % bilateral;
- MDE para α=0,05 y potencia=0,80: `(1,96 + 0,8416) * SE_HAC`;
- una sola hipótesis primaria; sin corrección adicional.

### 9.3 Secundarios — descriptivos, no promocionan

- primer toque dentro de 1, 2, 5, 10, 20, 60 y 120 barras, respetando lifecycle;
- curva de incidencia acumulada de primer toque;
- `close_through_gap`, expiración y censura;
- tiempo restringido al primer toque hasta 120 barras;
- PIT empírico/randomizado contra controles, únicamente para calibración del nulo;
- fracción de la brecha F1.1 explicada: `1 - Delta_matched / 0,470721`.

No se elige horizonte ni subconjunto después de mirar resultados.

## 10. Tests obligatorios antes de datos reales

1. Reanclaje conserva `rel_lo`, `rel_hi`, altura, distancia y lado tick por tick.
2. Zona disponible desde B+1; la barra creadora no toca.
3. Toque seguido de invalidación en la misma barra cuenta como toque.
4. `close_through_gap` antes del cruce censura toques posteriores.
5. Expiración ocurre exactamente cuando `age > max_age_bars`.
6. Control pertenece a otra sesión, mismo contrato y mismo minuto.
7. Barra control con creación BigTrap2 queda excluida.
8. Covariables nunca leen barras posteriores a B/J.
9. Horizonte control = horizonte fuente.
10. Selección de vecinos es determinista ante empates.
11. Dataset sintético sin efecto produce residual compatible con 0.
12. Dataset sintético con toque acelerado conocido produce residual positivo.
13. Ningún gate puede pasar con cero zonas/controles/sesiones.

## 11. Artefactos requeridos

- `diag/tasa_senales/F1.1_nulo_condicional_distancia.py`;
- `tests/research/test_bigtrap2_distance_matched_null.py`;
- `diag/tasa_senales/F1.1_nulo_condicional_distancia__<payload12>.json`;
- `docs/research/BIGTRAP2_DISTANCE_MATCHED_NULL_RESULT_2026-08-11.md`;
- actualización de `docs/REGISTRO_NO_MEDIDO_2026-08-10.md` en el mismo commit del resultado.

El JSON publica como mínimo:

- spec y NORTH_STAR SHA-256 completos;
- `head_start`, `head_end`, `dirty_start`, `dirty_end`;
- hashes de kernel, script, universo y datos/particiones;
- P0.1 WARN y estado de paridad;
- denominadores por filtro y abstención;
- balance del matching;
- resultado por sesión y agregado;
- SE HAC, IC y MDE;
- todos los secundarios enumerados;
- `outcomes_accessed=false`.

## 12. Orden de ejecución

1. Crear worktree exclusiva desde esta rama y verificar árbol limpio.
2. Implementar función pura + truth-known tests.
3. Ejecutar tests dirigidos y suite diferencial pertinente.
4. Ejecutar smoke sobre un contrato, sólo para validar estructura; no interpretar.
5. Si los gates del smoke pasan, ejecutar las 201 sesiones una sola vez.
6. Escribir artefacto + resultado + registro en el mismo commit.
7. Auditoría independiente del artefacto antes de cualquier interpretación.

## 13. Prohibiciones

- no tocar `bigtrap2.py`, sus defaults ni pins;
- no usar `tick:25`;
- no abrir holdout;
- no medir retornos, P&L, dirección, targets, stops o `QualityScore`;
- no barrer parámetros, K, covariables, calipers, horizontes ni gates;
- no reescribir artefactos F1.1 históricos;
- no presentar un resultado target-free como edge;
- no mergear PR #6/#7/#8/#9/#10 ni esta rama.

## Aporte al referente

Esta campaña reduce la principal incertidumbre del mayor efecto target-free observado en EdgeLab: separa “nivel informativo” de “zona casi encima del precio”. Un resultado positivo o negativo es útil porque decide si la familia BigTrap2 merece más investigación antes de ampliar el espacio de hipótesis.
