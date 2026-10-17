# ORB-CFD — Manifiesto Fase 0B (extensión firmada con potencia de Dukascopy)
Fecha: 2026-10-17. Estado: **BORRADOR — requiere STOP/OK de Nico antes de correr** (toca precios posteriores a la ruptura).
`docs/NORTH_STAR.md` sha256 (cuerpo): `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Hereda definiciones de `ORB_FASE0_MANIFIESTO_20261017.md` (secc. 4, 11, 12 / enmiendas A1, A2): extensión firmada, nulo de permutación de signos, reloj estricto `< t`.

## 0. Por qué existe
`ORB_FUT` (ES/NQ futuros) terminó en **ABSTENCIÓN**: ~170 días, SD de la extensión 2.0-2.5 R, MDE 0.45-0.54 R > 0.30 R. El límite es N, no el análisis (P-53). Hay en Kaggle 8.7 años de cotizaciones CFD de Dukascopy (USA500 2018-2026, USATECH y USA30 2023-2026) diseñados para esto: *"complemento de POTENCIA … el neto se confirma en futuros"* (README del dataset). El censo target-free (`orb_cfd_results_20261017/EXP_ORB_CFD_0A_CENSUS.json`, kernel `edgelab-orb-cfd-census-v1`) muestra datos limpios: >99 % de los días con primera cotización <= 300 s, huecos > 120 s en <= 8 días/año, 2.257 días RTH en USA500 y 966 en USATECH.

## 1. Familia y alcance (registrada antes de estudiarse)
Familia **ORB-CFD**, ledger propio. **No transporta** resultados, costos ni presupuesto de ORB_FUT. Conocimiento previo declarado (se vio antes de escribir esto): ORB_FUT ES/NQ, extensión al cierre en descubrimiento −0.18 / −0.14 R; ventana limpia ES +0.80 R (N = 41), NQ +0.07 R. Sólo **USA500 (análogo de ES)** y **USATECH (análogo de NQ)**. USA30 se deja fuera (YM no es el objetivo y suma una prueba). Nada ≥ 2026-10-01 existe en los datasets.

## 2. Espacio de eventos y estados (enumerado; se elige uno y se justifica)
Creación del rango · cierre del rango · **primer toque (ruptura) por precio fuera del rango** · ruptura por cierre de barra · toque n-ésimo · re-ingreso (latigazo) · confluencia con ATR/volumen/gap · estado continuo (posición relativa dentro del rango). **Se mide el primer toque de un rango de 15 min** porque es la misma celda de ORB_FUT (comparabilidad) y la única que el manifiesto original declaró primaria. El resto queda NO MEDIDO. Refutación de esta elección: si la extensión fuese distinta con ruptura por cierre de barra, esta celda no la vería (límite declarado).

## 3. Justificación económica y cómo podría refutarse
- **Justificación:** la apertura concentra información nueva y demanda de liquidez; la literatura (Crabel; Zarattini-Aziz 2023, acciones "in play"; Holmberg et al. 2013) reporta continuación tras la ruptura del rango inicial. Pero en nuestros datos de futuros el ORB 5-min está muerto (EXP-043) y la 0B es ≈ 0.
- **Se refuta si:** el IC 95 % de la media de `E` cabe en [−0.10, +0.10] R con p del nulo > 0.10 (NO_GO), o si `E` en el conjunto de replicación no confirma el signo.

## 4. Diseño
Precio = **mid** `(bid+ask)/2` (no hay trades; sin volumen ni agresor). RTH por reloj 09:30-16:00 ET con DST. Una celda primaria por instrumento: rango 15 min, ruptura por toque del mid, `E = signo × (P_t − nivel_roto)/ancho`, `P_t` = último mid estrictamente anterior a 15:45 ET. Segundo camino independiente (último mid por minuto, `groupby`): se exigen **0 discrepancias**.
**Guardas (fijadas con el censo, target-free, antes de ver ningún retorno):** primera cotización <= 300 s tras 09:30; hueco máximo 09:30-10:30 <= **120 s** (el CFD es menos denso que el futuro: 60 s descartaría 17-29 días/año en 2018-19); >= 20 cotizaciones en el rango; >= 100 cotizaciones en 15:00-15:45 (excluye cierres tempranos); ancho > 0. Días válidos: USA500 1.865 (M) y 300 (R); USATECH 628 (M) y 296 (R).
**Conjuntos:** **M (medición)** = hasta 2025-07-17 (USA500 desde 2018-01-02, USATECH desde 2023-01-03): **jamás visto para ORB**. **R (replicación)** = 2025-07-18..2026-09-30: **una sola mirada**, abierta después de fijar el veredicto de M y sólo si M da señal. Declarado: R coincide en fechas con la ventana de ORB_FUT ya vista, pero es otro instrumento y otro objeto.
**Equivalencia con el futuro (en R):** por día, `E_cfd` vs `E_fut` (mismo kernel 0B sobre ES/NQ): se publica correlación de Spearman y concordancia del lado de la ruptura. **Criterio de transporte:** Spearman >= 0.80 y concordancia >= 85 %. Si no se cumple, el resultado habla del CFD y **no se transporta a futuros**.

## 5. Criterios (definidos antes de mirar), por instrumento sobre M
- **Medible:** MDE (80 %, 2.5 % unilateral) <= **0.25 R**. (Esperado: ~0.15 R USA500, ~0.22 R USATECH con SD 2-2.5 R.)
- **SEÑAL_EN_M** (sólo ella abre R): límite inferior del IC 95 % de la media de `E` al cierre > 0 **y** p unilateral del nulo de permutación de signos < **0.025** (Bonferroni, 2 instrumentos) **y** mismo signo en la primera y la segunda mitad cronológica de M.
- **NO_GO:** IC 95 % dentro de [−0.10, +0.10] R **y** p > 0.10.
- **ABSTENCIÓN:** resto. Un `SEÑAL_EN_M` **no es un edge**: abre R (una mirada) y, si confirma, un manifiesto de estrategia (stop/salida causales, **costos de futuros** —el spread del CFD, 0.5 pts en USA500, no es el de ES—, y su propio STOP).
- **Número efectivo de hipótesis:** 2 celdas primarias (USA500, USATECH) × 1 horizonte. Descriptivo sin inferencia: horizonte 11:30, ventanas 5/30/60 min, media por año, canal no direccional, cuantiles 5/25/50/75/95, media recortada (1 %).

## 6. Riesgos y límites
CFD ≠ futuro (horario de cotización, formación del precio previa a la apertura, spread 2× el de ES): por eso la equivalencia es criterio explícito. Régimen: 2020 y 2022 de alta volatilidad y 2018-19 con cotizaciones ralas (mediana ~1.000 cotizaciones en 15 min). Colas: días de rango angosto inflan `E` en R (SD 2.5); se publica la media recortada como robustez, no como sustituto del estimand. Dependencia serial entre días: se publica además un IC de bootstrap por bloques mensuales como sensibilidad. Sin costos: bruto.

## 7. Ejecución
Un kernel Kaggle (CPU, datasets `edgelab-dukascopy-es-usa500` y `-nq-usatech`), congelado por commit antes de correr; resultados y registro `ORB_CFD_MEDIDO_Y_NO_MEDIDO.md` en el mismo commit. R se corre en un kernel aparte, sólo si M da `SEÑAL_EN_M`.

## 8. Decisión que se le pide a Nico
1. **(A)** Aprobar 0B-CFD sobre M para USA500 y USATECH tal como está escrito. 2. **(B)** Aprobar sólo USA500. 3. **(C)** Cambios (guardas, criterios, conjuntos).
**Recomendación: (A).** Cuesta una corrida de Kaggle; el resultado más probable es NO_GO o ABSTENCIÓN, y ambos son información útil antes de gastar presupuesto en filtros.
