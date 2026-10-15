# R3 — Dirección a 15–60 min en índices y metales (manifiesto PROPUESTO)

Estado: VIGENTE — APROBADO por Nico en chat el 2026-10-14 ("R3: Apruebo"); congelado antes de medir
Fecha: 2026-10-14
Familia / módulo: research · roadmap R3
North Star: `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`
Procedencia: release `liquid_tick_v1` v4 (manifiesto `db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5`, aprobada: `docs/infra/RELEASE_APPROVAL_20261014.md`); R2: `docs/research/R2_RECORRIDO_VS_FRICCION_RESULTADOS_20261014.md`.

> Aprobado por Nico ("R3: Apruebo", 2026-10-14) con las 2 celdas primarias, una sola apertura de la replicación y el rango de comisión (0,28–1,15 ticks) como cuenta de referencia (aún sin elegir broker). Este commit lo congela **antes** de medir.

## 0. Definiciones fijadas al congelar (no se cambian después de ver resultados)
- **Decisión:** para cada (L, H) los puntos de decisión son los minutos `m = L + j·H` (j ≥ 0) con `m + H ≤ 390` de la sesión regular 08:30–15:00 CT. Señal con los minutos `[m−L, m)`; **entrada = primer precio de trade del minuto `m`** (tick siguiente a la señal), **salida = último precio de trade del minuto `m+H−1`**. Retorno firmado `r = signo·(salida − entrada)` en ticks. Sin signo (empate) la ventana se descarta.
- **A:** `signo = sign(último precio del minuto m−1 − primer precio del minuto m−L)`. **B:** `signo = sign(Σ volumen·agresor en los minutos [m−L, m))`, agresor ∈ {−1, 0, +1} del release.
- **Neto:** `r − F`, con `F` = spread medio RTH + comisión + 2 ticks (R2). **La supervivencia se decide con `F` alta** (conservadora); `F` baja se informa.
- **Inferencia:** media neta por celda con bootstrap estacionario de sesiones (2.000 remuestreos, bloque medio de 5 sesiones, semilla 20261014). **Primarias** (NQ, L=15, H=15; familias A y B): sobreviven si el límite inferior del IC 95 % de la media neta es > 0. **Secundarias** (las 90 celdas): sobreviven si el p unilateral ajustado por Holm sobre las 90 es < 0,05. Se publican las 90 celdas completas, sobrevivan o no.
- **Replicación:** `2026-04-01 → 2026-09-30`, **una sola ejecución** (el script crea `REPLICATION_OPENED.json` y se niega a repetir), sólo sobre las celdas sobrevivientes del descubrimiento, con el mismo `F` alto; una celda se confirma si el límite inferior del IC 95 % de la media neta en replicación es > 0 y el signo coincide.
- Sin selección por valor, sin ajuste de umbrales ni de ventanas tras ver resultados; holdout `trade_date ≥ 20261001` no se lee.

## 1. Pregunta y justificación económica
R2 mostró que a 15–60 min el movimiento neto en índices y metales es 5–15 veces la fricción: el obstáculo no es el tamaño sino predecir la dirección. ¿Existe una señal causal, simple y pre-registrada que acierte la dirección del siguiente tramo de 15–60 min con una tasa neta de fricción positiva, en una partición de replicación que no se usó para elegirla?
Mecanismo candidato (por familia):
- **A. Persistencia/reversión del retorno intradía** (momentum de serie temporal): el flujo institucional que ejecuta en bloques deja autocorrelación a escala de minutos-horas; o el exceso se revierte por proveer liquidez.
- **B. Presión de flujo agresor**: el volumen neto agresor (compra − venta, regla de quotes) de los últimos L minutos anticipa el desplazamiento del siguiente tramo.

## 2. Espacio de eventos y estados (se enumera antes de congelar)
| Alternativa | Se mide | Por qué no / sí |
|---|---|---|
| **Estado continuo cada 15 min** (decisión en cada inicio de ventana no solapada de H min dentro de 08:30–15:00 CT) | **SÍ** (primaria) | usa todas las ventanas, N en sesiones, no depende de eventos raros |
| Evento: ruptura del rango inicial (IB) | no | población pequeña (1 por sesión); queda para una familia aparte registrada después |
| Evento: toque de zona (BigTrap2, AVZP2…) | no | ya medido y cerrado en sus familias |
| Estado por régimen de subasta (`session_auction`) | no | se registra como condicionante en una campaña posterior, no aquí |
| Apertura/cierre, noticias | no | fuera de la ventana 08:30–15:00 sin evento calendario |
Condición de refutación de la **elección de población**: si la familia no supera el nulo con ventanas no solapadas, no se reabre cambiando la ventana sin evidencia nueva.

## 3. Hipótesis y número efectivo
- Señales: A (signo del retorno de las últimas L min, L ∈ {15, 30, 60}) y B (signo del volumen agresor neto de las últimas L min, mismos L). Horizonte de predicción H ∈ {15, 30, 60}. Activos: NQ, ES, YM, RTY, GC.
- Celdas brutas = 2 familias × 3 L × 3 H × 5 activos = **90**.
- **N efectivo (declarado)**: los índices (NQ, ES, YM, RTY) se mueven juntos (correlación supuesta ≈ 0,8–0,9, por medir), así que cuentan como ≈ 2 apuestas independientes + GC = 3; L y H solapados cuentan ≈ 4; 2 familias ⇒ **N_ef ≈ 24**. La corrección se hace con Holm sobre las **90 celdas brutas** (conservador).
- **Celdas primarias pre-registradas (2):** NQ, L = 15, H = 15, familias A y B. Todo lo demás es secundario/exploratorio y se informa completo (todas las celdas, semillas y nulos), sin seleccionar por P&L máximo.

## 4. Partición y holdout
- **Descubrimiento:** 2025-07-18 → 2026-03-31. **Replicación:** 2026-04-01 → 2026-09-30, **una sola apertura**, sólo sobre celdas que sobrevivan en descubrimiento, sin elegir nada en ella. **Holdout:** `trade_date ≥ 2026-10-01`, sin tocar (enmiendas HOLDOUT-A1/A2/A3).
- Sesiones por partición (release v4): NQ 167 / 124; ES 179 / 121; YM 150 / 117; RTY 123 / 126; GC 150 / 123.

## 5. Estimandos (dos canales)
- **Direccional:** tasa de acierto del signo y retorno firmado medio (ticks) menos la fricción de viaje redondo `F` del activo, en sus dos extremos (comisión mínima y máxima; `REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md`).
- **No direccional:** distribución completa de retornos firmados por celda y por hora de inicio; magnitud |retorno| condicionada a la señal.
- Inferencia primaria (G2-A1): IC por bootstrap estacionario agrupado por sesión, límite inferior > 0 del retorno neto medio; DSR/MCPT/PBO sólo para el candidato que sobreviva. Sin P&L de estrategia (stops, tamaños) en esta etapa: es **información**, la ejecución viene después (cadena `geometría → información → P&L bruto → edge neto`).

## 6. Potencia (MDE) — la parte incómoda
Acierto mínimo para cubrir la fricción (R2): NQ 15 min ≈ 54 %; 30 min ≈ 53 %; 60 min ≈ 52 %. Efecto mínimo detectable (80 % de potencia, ventanas no solapadas, correlación intra-sesión ρ = 0,05 supuesta, α corregido):
| Activo, H | n_ef descubrimiento | MDE descubrimiento (α=0,05/90) | n_ef replicación | MDE replicación (α=0,05/8) |
|---|---:|---:|---:|---:|
| NQ 15 min | 1.930 | 4,7 pp | 1.433 | 4,4 pp |
| NQ 30 min | 1.357 | 5,6 pp | 1.008 | 5,3 pp |
| NQ 60 min | 802 | 7,2 pp | 595 | 6,8 pp |
| ES 15 min | 2.068 | 4,5 pp | 1.398 | 4,5 pp |
| GC 15 min | 1.733 | 4,9 pp | 1.421 | 4,4 pp |
**Lectura honesta:** el diseño sólo alcanza a detectar un efecto del tamaño del acierto de equilibrio (≈ 4 pp) en NQ/ES a 15 min; a 30–60 min el MDE (5–7 pp) supera lo que haría falta (2–3 pp). Para detectar 2 pp a 60 min hacen falta ≈ 4.900 ventanas efectivas, unas **6 veces** las actuales. **El límite es N (P-53), no el análisis**: un nulo a 30–60 min no distinguirá "no hay efecto" de "no hay potencia".

## 7. Cómo podría refutarse
- Celdas primarias sin límite inferior > 0 en descubrimiento ⇒ la familia queda `SIN EFECTO DETECTADO` a 15 min en NQ, con su MDE publicado; no se reabre ampliando horizontes sin evidencia nueva.
- Supervivencia en descubrimiento pero no en replicación ⇒ refutada para ese activo/horizonte.
- Efecto presente sólo en pocas sesiones (cola) ⇒ se informa la fracción de sesiones con retorno neto positivo; sin esa dispersión no se promueve.
- Un efecto de signo opuesto (reversión) se informa igual: el canal direccional se mide con signo.

## 8. Riesgos y datos faltantes
- **Potencia insuficiente** (§6) y un solo régimen de volatilidad (2025-08 → 2026-09).
- **Aggressor (familia B):** los prints interiores al spread son `UNKNOWN` y `sequence` no es secuencia de exchange (P-28): B se limita a la regla de quotes y no soporta microestructura de cola.
- **Costos:** slippage real sin medir (2 ticks RT declarados), comisión de la cuenta real sin definir, sin evidencia de fills pasivos.
- **Datos faltantes:** 309 sesiones P0 (`docs/infra/MISSING_EXPORTS_20261014.md`) y conflictos de fuente en 701 sesiones-contrato; mientras no se exporten, `N` queda fijo. Más sesiones llegan sólo con captura diaria continua.
- **Multiplicidad entre familias futuras:** esta campaña consume su propio presupuesto; no se transporta a otras familias.

## 9. Qué se pide a Nico (STOP)
1. OK al manifiesto y a las **2 celdas primarias**, con las 88 restantes como exploratorias.
2. OK a la lectura del holdout de replicación **una sola vez** (2026-04-01 → 2026-09-30) sobre las celdas sobrevivientes.
3. Confirmar la cuenta/broker de referencia para fricción (o aceptar el rango de 0,28–1,15 ticks de comisión).
Sin ese OK no se ejecuta nada.
