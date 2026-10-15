# Manifiesto propuesto — Pasada 3 confirmatoria de `EmaCorridorTrend` (familia `EXP-CORRIDOR-CONF`)

Estado: **BORRADOR PARA AUDITORÍA Y OK DE NICO. NO EJECUTAR.** Ninguna medición sobre retornos corre sin aprobación (STOP de `CLAUDE.md`).
Fecha: 2026-10-15 · Referente rector: `docs/NORTH_STAR.md`, sha256 del cuerpo (valor declarado en `CLAUDE.md`) `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`; el auditor de gobernanza debe recomputarlo con `tests/test_north_star_hash.py`.
Antecedentes: `AUDITORIA_CORRIDA_KAGGLE_ES_MULTIRES_CORRIDOR_V4_20261015.md`, `AUDITORIA_PASADA2_CORRIDOR_ES_V4_20261015.md`.
Familia nueva registrada: `EXP-CORRIDOR-CONF`. No hereda resultados ni presupuesto de multiplicidad de otras familias; **hereda como hipótesis** (no como evidencia) los candidatos de Pasadas 1–2.

## 0. Resumen
1. Las 299 sesiones de ES están **quemadas** para confirmar F1/F2 (se eligieron mirándolas). Esta pasada confirma sobre datos **no usados para seleccionar**.
2. Una sola hipótesis primaria (`HA`, F1) y una secundaria exploratoria (`HB`, F2). F3 queda **fuera como trade** (bruto < fricción) y sólo se mantiene como nivel descriptivo.
3. Confirmación en **instrumentos independientes** (NQ y YM), cada uno con su fricción medida, y en ES futuro (holdout) cuando exista N; ES histórico sólo sirve de prueba de regresión del código (no de evidencia).
4. Criterio doble y preregistrado: **información** (¿gana más que el nulo?) y **economía** (¿el neto de fricción es positivo con IC clusterizado?). Se declara de antemano que la segunda **probablemente no tendrá potencia** (§7).
5. Parámetros, estratos, régimen y código **congelados**; nada se ajusta tras mirar.

## 1. Justificación económica (obligatoria)
Tras una tendencia estable (corredor EMA) que termina, el precio que regresa al borde exterior deja atrás una zona recorrida sin consolidación: poco volumen pasivo "adentro". Si el flujo que empujó la tendencia ya se agotó, el regreso puede continuar contra la tendencia hasta el origen del corredor (`orig_px`), donde sí hubo aceptación. Quien paga sería el flujo de tendencia tardío atrapado en el borde; quien cobra, la liquidez que entra en el retroceso. Mecanismo plausible, no demostrado: en ES la Pasada 2 no supera el nulo emparejado.

## 2. Cómo podría refutarse (obligatoria)
Refutada (alcance: este detector, estas definiciones, estos instrumentos y horizonte) si ocurre cualquiera:
- R1. El IC clusterizado por sesión del exceso de `HA` sobre el nulo emparejado incluye 0 o es negativo en la muestra confirmatoria agrupada.
- R2. El signo del efecto es inconsistente entre NQ y YM (uno ≤ 0).
- R3. El efecto desaparece en espejo (LONG vs SHORT) o sólo existe fuera de RTH.
- R4. El neto de fricción medido por instrumento es ≤ 0 (en ese caso el estado es "información sin economía", no "refutada").
- R5. La regresión sobre ES histórico no reproduce las cifras de la Pasada 2 (integridad: se invalida la corrida hasta explicar).
"Sin potencia" es un estado distinto de refutada y se declara con el MDE.

## 3. Datos y aislamiento
- Fuente: release `liquid_tick_v1` v4. Reconciliar antes el hash de manifiesto (`db9c42cd…` aprobado vs `06d7fb2a…` citado en las corridas de Gemini).
- **Holdout `trade_date ≥ 2026-10-01`: sellado.** Sólo se abre **una vez** por instrumento y por candidato, cuando se cumpla el N requerido de §7. El corte por sesión CME (no por UTC).
- Conjunto de confirmación: **NQ y YM**, sesiones `SELECTED` con `trade_date < 2026-10-01` (R2: NQ 289 y YM 263 sesiones). **Nunca se usaron para seleccionar nada.** Excluidos MES/MNQ/MYM: son copias casi perfectas del subyacente de ES/NQ/YM (no independientes; no suman evidencia).
- ES histórico (299 sesiones): **sólo prueba de regresión del código** (debe reproducir la Pasada 2). No cuenta como evidencia.
- Limitaciones de datos: `sequence` no es secuencia de exchange (P-28): ninguna lógica depende del orden de ticks con igual timestamp.
- No se transportan costos: fricción por instrumento (R2): ES 3,37–3,55; NQ 5,73–6,18; YM 4,60–5,05 ticks ida y vuelta.

## 4. Hipótesis congeladas
Definiciones exactas = las de la Pasada 2 (código `edgelab_es_corridor_pass2_falsification_v4_sym.py` sha256 `10e8fa9f22693b9269754e73b8fafe18b7694ccc70702f9a843ebea7b584c0ec` + `ema_corridor_trend.py` sha256 `3f4befdf8a6047b1259785c32f3046b456d11366654ed1d92ad36a2304336bc5`), sin modificar parámetros; sólo se parametriza tick size y calendario por instrumento (el cambio se verifica con la regresión de §8).

**HA (primaria) — F1A, regreso virgen al borde exterior confirmado al cierre.**
Resolución 100T; preset **1** (selectivo); estrato `STEEP_SLOPE`; sólo RTH (08:30–15:30 CT, **fijado desde ahora**); entrada al cierre de la barra de reingreso; dirección contraria a la tendencia; objetivo `1,0·ZoneHeight` (hacia el origen), parada simétrica; sin cruce de sesión; `no_overlap`.
*Nota de elección:* preset 1 y `STEEP_SLOPE` salieron de la Pasada 2 (selección sobre ES); su valor está en que ahora se prueba en datos nuevos. Que en ES el nulo emparejado no los respalde es **riesgo declarado**, no motivo para cambiarlos.

**HB (secundaria, exploratoria) — F2D, penetración 33,3% en zona virgen de pendiente empinada.**
500T; preset 2; `STEEP_SLOPE`; RTH; entrada límite con regla de trade-through (§6); objetivo `1,0·ZoneHeight`. Se reporta con su MDE; **no entra en la inferencia confirmatoria** porque se espera sin potencia.

**F3 (`orig_px`) — fuera del conjunto de trades.** Bruto 0,6–2,1 ticks vs fricción ≥ 3,4. Se conserva sólo como definición de nivel.

## 5. Estimando y criterios de éxito
Evento = una entrada que cumple HA. Resultado = gana si alcanza el objetivo antes que la parada, sin cruzar sesión (los no resueltos se reportan aparte y no se descartan en silencio).
- **Estimando de información (E1):** exceso de la tasa de acierto sobre el **nulo emparejado** (5 pseudo-eventos por evento real, contrato × media hora × `state==0`, mismas barreras). *Deficiencia conocida del nulo H-03 (iguala hora, no iguala el disparador); por eso se añade E1b.*
- **E1b:** exceso sobre 50 % **y** sobre un nulo de disparador comparable: eventos "regreso al borde exterior" sin la condición de pendiente empinada (misma geometría, misma hora). Reportar ambos.
- **Estimando de economía (E2):** expectativa neta por operación `E = (2w−1)·D̄ − F_instr` (ticks), con `D̄` la mediana de la barrera en ticks y `F_instr` el extremo alto de la fricción medida de R2 para ese instrumento; sensibilidad con la fricción baja.
- **Inferencia:** bootstrap/SE clusterizado por sesión, MCPT por inversión de signo de sesión (≥ 5.000), unilateral α = 0,05 sobre el **agrupado NQ+YM ponderado por varianza inversa**. Una sola prueba primaria ⇒ sin ajuste adicional; secundarias con Holm.
- **Éxito de información:** IC inferior (95 % unilateral) de E1 > 0 en el agrupado **y** signo positivo en NQ y YM por separado **y** espejo con ambos lados > 50 % **y** RTH ≥ ETH no requerido (el régimen ya está fijado).
- **Éxito económico:** además, IC inferior de E2 > 0 en el agrupado. De no cumplirse, el estado máximo es "información confirmada, economía no demostrada".
- Estados posibles: `CONFIRMADA_INFO`, `CONFIRMADA_INFO_Y_ECONOMIA`, `REFUTADA`, `SIN_POTENCIA`, `INCONSISTENTE`.

## 6. Ejecución y fills
- Entradas al cierre de barra: precio de cierre + spread medio medido + slippage declarado (R2).
- Entradas límite (HB): se considera llenada sólo si el precio **opera a través** del nivel al menos 1 tick (trade-through); sin ello, no hay fill. Sensibilidad con 2 ticks de trade-through.
- Empates a la parada. Sin fills imposibles. Barreras con tick size del instrumento.

## 7. Potencia y número efectivo de hipótesis
Número efectivo declarado: **1 primaria** (HA agrupada) + 1 secundaria (HB) + 2 desagregadas descriptivas (NQ, YM por separado). Cota superior: 4. No se prueban otros presets, estratos, barreras ni resoluciones.

Potencia (a recalcular por el auditor estadístico con los N reales de NQ/YM): en ES la HA tuvo ≈ 850 eventos / 299 sesiones (≈ 2,9 por sesión; SE clusterizado ≈ 1,7 pp, MDE80 ≈ 4,8 pp). Con NQ+YM se esperan del orden de 1.500 eventos agrupados (a verificar en la etapa de conteo, sin retornos): MDE80 ≈ 3,5–4 pp sobre 50 %. Por eso:
- Detectar información con efecto ≥ ~4 pp: **posible**.
- Detectar rentabilidad neta: el punto de equilibrio exige `w > 50 % + F/(2D)`; con D≈40 ticks y F≈3,5 en ES son ~54,4 %; en NQ/YM F es mayor pero D también. Un efecto neto de ~1 tick equivale a ~1,2 pp: **inalcanzable con este N**. El resultado económico más probable es `SIN_POTENCIA`. Se declara ahora para que no se lea como refutación ni como éxito.
- ES holdout (desde 2026-10-01): ~250 sesiones/año ⇒ ~700 eventos/año de HA. Se abre sólo si `N_acumulado ≥ 1.800` eventos de HA o a los 12 meses (lo que ocurra primero), una vez.

## 8. Plan de ejecución y controles de integridad
0. **Conteo target-free** (sin retornos): sesiones, zonas y eventos esperados de HA/HB por instrumento y por mitad; fija el N y el MDE definitivos. Publicarlos antes del paso 3.
1. Adaptar el script a NQ/YM sólo en tick size, calendario RTH y contratos; **regresión obligatoria** en ES: reproducir las cifras de la Pasada 2 (HA preset 1 STEEP 1,0H: N=852, 55,40 %; F3 25T 0,5H: N=28.338, 53,06 %). Si no coincide, parar.
2. Verificar simetría 1:1 (`mirror_check`) y que no se cruza `trade_date`.
3. Correr HA y HB en NQ y YM **una sola vez**; publicar el landscape completo (eventos, no resueltos, nulos, semillas).
4. Dossier con procedencia dirty-aware (`head_start/head_end`, limpio/sucio), versiones, semillas, hash del manifiesto de la release y del código.
5. Registro MEDIDO/NO MEDIDO actualizado **en el mismo commit** que el resultado.

## 9. Riesgos
| Riesgo | Mitigación |
|---|---|
| Poca potencia para la economía | Declarado (§7); el estado `SIN_POTENCIA` es válido |
| Nulo H-03 mal especificado (caso del 33,9 % en F2) | E1b con nulo de disparador; auditar tamaño de pseudo-muestra por estrato |
| Elección de preset/estrato por selección sobre ES (winner's curse) | Se prueba en datos nuevos; el sesgo reduce, no aumenta, la probabilidad de confirmar |
| El detector (parámetros en ATR) no se comporta igual en NQ/YM | Regresión + conteo previo; si los conteos difieren > 2×, informar, no ajustar |
| Resolución literal 100T ≠ misma escala de tiempo en NQ/YM | Se mantiene literal (preregistrado); sensibilidad temporal sólo descriptiva |
| Correlación entre NQ y YM con ES | Se reportan por separado; agrupado ponderado, correlación entre series estimada y declarada |
| Contaminación del holdout | Lectura única, sin diseño sobre él |

## 10. Plan de auditoría (reutiliza los roles A1–A7 de la propuesta de modelo)
A1 causalidad (entrada ≥ `cls_b+1`, características al instante de entrada, sin cajas finales); A2 estadística (potencia, clustering, nulo, MCPT); A3 economía (fricción por instrumento, trade-through); A4 datos (corte CME, contratos, hash de manifiesto, P-28); A5 código (regresión, simetría, versionado); A6 gobernanza (hash NORTH_STAR, STOP, independencia de familia, registro MEDIDO); A7 abogado del diablo (¿por qué HA está ya refutada por el nulo emparejado?). Plantilla de informe y criterio de aprobación: los de la propuesta de modelo §14.

## 11. Preguntas para Nico
1. ¿Aceptás que ES histórico quede sólo como regresión y que la confirmación sea en NQ y YM (+ holdout de ES a largo plazo)?
2. ¿HA con preset 1/STEEP/RTH/1,0H, o preferís otra configuración (decidir **ahora**)?
3. ¿HB queda como exploratoria sin potencia, o la sacamos?
4. Resolución literal 100T en NQ/YM, ¿o igualar la escala de tiempo?
5. ¿Tratamos `orig_px` (F3) sólo como nivel descriptivo y lo sacamos del presupuesto de trades?
6. Regla de apertura del holdout de ES (N ≥ 1.800 eventos o 12 meses).

*Aporte al referente:* convierte un barrido que seleccionó ganadores sobre sus propios datos en una confirmación sobre datos no usados, con la economía y la falta de potencia declaradas de antemano; así un resultado, positivo o no, es interpretable.

## 12. Respuestas de Nico (2026-10-15)
- P1 (ES histórico sólo como desarrollo/regresión; confirmación en NQ y YM + holdout de ES): **sí**.
- P2 (`HA` como primaria sin cambios): **sí**.
- P3 (`HB` exploratoria sin potencia): **sí**.
- P4–P6: pendientes (por defecto: 100T literal, `orig_px` sólo nivel descriptivo, holdout de ES a N ≥ 1.800 o 12 meses).
- Adicional: Nico pidió aplicar todas las herramientas posibles para filtrar y mejorar la precisión del efecto bruto. Se canaliza con `ADENDA_D_DESARROLLO_FILTROS_CORREDOR_20261015.md` (desarrollo sobre ES, NQ/YM sellados, nulo del pipeline). Esa adenda requiere su propio OK antes de correr.
