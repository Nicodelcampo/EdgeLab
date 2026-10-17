# Fase 0 — Ejecucion pasiva en ES: fill, seleccion adversa y valor por intento (manifiesto PRE-REGISTRADO, BORRADOR)

Estado: **PROPUESTA PARA NICO. No se ejecuta nada hasta su OK explicito.** Fecha: 2026-10-17.
Familia nueva: `EXEC-PASIVA-ES` (independiente de corredor x HFT; no hereda resultados, poblaciones ni presupuesto de multiplicidad).
Rama: `research/k37-prereg-corredor-hft-20261017` (archivo propio). Referente rector: `docs/NORTH_STAR.md`, cuerpo sha256
`05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

## 0. Por que esta fase (justificacion economica)
En k36/K37 el costo (1.546 ticks ida y vuelta) fue mayor que cualquier bruto observado (descubrimiento +0.68, replicacion -0.11). Ese costo se **supuso** igual
para limite inmediato y pasivo; nunca se descompuso. Hipotesis de lectura **no verificada**: 1.546 ~ 1 tick de spread cruzado + ~0.55 tick de comisiones/deslizamiento
(a confirmar contra el modelo de costos de k35 antes de usarla). Si una entrada pasiva en el touch ahorra el spread pero paga seleccion adversa y perdidas por no-fill,
**el neto depende de tres numeros que hoy no estan medidos**: probabilidad de fill, seleccion adversa tras el fill, y valor de lo que se pierde al no llenarse.
Esta fase los mide, sin estrategia ni direccion apostada, para que cualquier manifiesto posterior parta de un modelo de costos con evidencia.

- **Como podria refutarse:** si la seleccion adversa tras el fill (medida a 60 s) es >= al spread ganado, el pasivo en el touch no mejora a cruzar el spread y se descarta como via
  de reduccion de costo; si el fill pasivo conservador es tan raro que `F < 10 %`, tampoco sirve como mecanismo de entrada.

## 1. Poblacion y espacio de eventos (regla de poblacion)
Espacio considerado de "momentos de decision": (a) cierre de cada barra 100T estricta por sesion (T1); (b) cierres de impulso del corredor (preset 1, T2: 5.311 eventos);
(c) momentos aleatorios en tiempo reloj; (d) solo aperturas/cierres de sesion; (e) toques de zonas HFT o de otro nivel.
**Elegida: T1 como primaria** (cobertura uniforme, sin hipotesis de direccion, ya definida y auditada en k34-k37), **T2 como secundaria** (para ver si el momento tras un impulso difiere).
(c), (d) y (e) **no se miden aqui** y no se transportan resultados a ellos.
- Instrumento: **ES** unicamente (sin NQ/YM/6E/GC). Datos L1 de ticks: `edgelab-liquid-ticks-20261014` (estado del dataset: CANDIDATE_NOT_RESEARCH_APPROVED; usarlo exige el OK de Nico).
- Ventana primaria: descubrimiento 2025-07-18 a 2026-03-31 (178 sesiones). Ventana de **confirmacion de estabilidad**: 2026-04-01 a 2026-09-30 (se abre **una vez** para esta familia nueva). Holdout >= 2026-10-01 intacto.
- Sin parametros que ajustar: es una medicion descriptiva; el descubrimiento fija las estimaciones y la confirmacion exige estabilidad de signo y magnitud dentro del IC.

## 2. Definiciones congeladas
- Momento de decision `t0`: cierre de barra. Lado `s in {compra, venta}`, **siempre ambos** (promedio de lados por defecto; cada lado se reporta).
- Orden pasiva hipotetica: limite fijo al touch (compra al bid de `t0`, venta al ask de `t0`), **sin recotizar**, vive `tau` y se cancela si no se lleno.
- Entrada agresiva de referencia: cruza el spread (compra al ask, venta al bid de `t0`).
- **Reglas de fill (cota inferior/superior; la cola de ordenes no es observable en L1, por eso se acotan):**
  - `R_TT` (conservadora, la de k36): llena si algun trade opera al menos 1 tick **mas alla** del precio limite (compra: precio <= limite - 1 tick). **Primaria.**
  - `R_TOUCH` (optimista): llena si algun trade opera a precio <= limite (compra) / >= limite (venta). Cota superior de F; no se usa para decidir.
- `mid(t)`: (bid+ask)/2 de la ultima cotizacion <= t. Cotizaciones solo aparecen en filas de trades: cotizacion vieja es un sesgo declarado.
- `tau in {10 s, 60 s, 300 s}`; horizonte de markout `h in {10 s, 60 s, 300 s}` desde el instante del fill (o desde `t0` para la agresiva).
- **Markout** (en ticks, signo favorable al que compra/vende): `M = s * (mid(t_ref + h) - precio_de_entrada)`.

## 3. Estimandos
- **E1 Probabilidad de fill** `F(tau, regla)`: fraccion de ordenes pasivas que se llenan antes de `tau`; tambien mediana de tiempo a fill.
- **E2 Markout de la agresiva** `M_a(h)`: entrada cruzando el spread; contiene el costo del spread cruzado.
- **E3 Markout de la pasiva llenada** `M_p(h)`: entrada al touch, **condicional al fill**; contiene el spread capturado y la seleccion adversa.
- **E4 Ventaja por fill** `A(h) = M_p(h) - M_a(h)` = spread - seleccion adversa (aprox.). **Primario:** `A(60 s)` con `tau = 60 s`, `R_TT`, T1, promedio de lados.
- **E5 Valor por intento / edge de equilibrio:** con `F` y `A` medidos, el edge direccional por trade que haria indiferente pasar de agresiva a pasiva es `g* = F*A / (1-F)` ticks (si el
  predictor pierde `g` al no llenarse). Se publica como funcion de `F` y `A`; no se asume ningun `g`.
- **E6 Canal no direccional / distribucion completa:** cuantiles (5/25/50/75/95) de `M_p` y `M_a`, ademas de las medias; fraccion de fills seguidos de movimiento adverso >= 2 ticks en `h`.

## 4. Heterogeneidad (3 contrastes pre-especificados, Holm sobre 3)
S1 la orden va **a favor vs en contra** de la direccion de la barra 100T previa (el caso de una reversion es "en contra"); S2 spread de 1 tick vs >= 2 ticks en `t0`;
S3 primera media hora de la sesion regular vs resto. Todo lo demas (terciles de volumen, hora fina, estratos nuevos) es exploratorio y se marca como tal, sin inferencia.

## 5. Inferencia y multiplicidad
- Unidad: la **sesion**. SE clusterizado por sesion (varianza de totales por sesion). IC al 95 % bilateral para estimandos; para el criterio, limite unilateral 97.5 %.
- Decisoras: **m = 1** (E4 primario). S1-S3: Holm sobre 3. La grilla `tau x h x regla` se publica completa (landscape), sin seleccionar la mejor celda.
- Sin nulo de estrategia (no hay estrategia). Control de coherencia: **permutacion de lado** (comprar vs vender al azar a la misma hora): `A` debe ser simetrica salvo por la microestructura; una asimetria grande senala un defecto de datos.

## 6. Criterios (definidos antes de mirar)
- **PASIVO_RECUPERA** (E4): `F(60s, R_TT) >= 0.30` **y** limite inferior 97.5 % de `A(60 s)` > **+0.25 tick** **y** el signo se mantiene en la ventana de confirmacion.
- **PASIVO_NO_CONVIENE:** limite superior 97.5 % de `A(60 s)` < +0.25 tick **o** `F(60s, R_TT) < 0.10`.
- **ABSTENCION:** cualquier otro caso. No se reintenta sobre la misma ventana.
- Un resultado `PASIVO_RECUPERA` **no es un edge**: solo habilita un modelo de costos con evidencia para un manifiesto posterior.

## 7. Guardas fail-closed (el kernel aborta sin reportar)
- Cotizaciones validas (`ask >= bid > 0`) en >= 99 % de las filas usadas; si no, abstencion por calidad de datos.
- Prueba de causalidad del fill: el fill/no-fill en `tau` no cambia al alterar ticks posteriores a `t0 + tau` (perturbacion de futuro, diferencia 0.0).
- Prueba de prefijo del cierre de barra (mismo criterio que k37, v2): >= 200 casos verificados.
- >= 170 sesiones en descubrimiento y >= 80 en confirmacion; cualquier timestamp >= 2026-10-01 aborta.

## 8. Fuera de alcance y fases siguientes (no se ejecutan)
- **0C (opcional, requiere OK aparte):** cola real con L2 si el dataset `edgelab-l2-es-20261015` (CANDIDATE, ~29 sesiones de GC en otra familia; cobertura de ES a verificar) lo permite.
- **Fase 1** (otro manifiesto): una estrategia candidata evaluada con el modelo de costos que salga de esta fase.
- No se evalua ninguna estrategia, ningun umbral de entrada, ni se optimiza `tau`/`h`.

## 9. Ejecucion propuesta
Un kernel Kaggle (CPU) de una sola pasada, salida `EXP_F0_EXEC_PASIVA_ES_RESULTS.json` con la grilla completa y el veredicto automatico. Codigo, hash del kernel y manifiesto
congelados por commit **antes** de abrir la ventana de confirmacion. Registro MEDIDO/NO MEDIDO actualizado en el mismo commit que el resultado.

## 10. Decision que se le pide a Nico
1. **(A) Aprobar** este manifiesto (incluye usar `edgelab-liquid-ticks-20261014` pese a su estado CANDIDATE y abrir la ventana de confirmacion una vez), o
2. **(B) Aprobar solo el tramo de fill** (E1) y dejar el markout para despues, o
3. **(C) Pedir cambios** (poblacion, reglas de fill, criterios).
Mi recomendacion: **(A)**: el markout es lo que decide si el pasivo sirve, y la medicion es de una sola celda primaria, sin busqueda.

## 11. Autorizacion y hallazgo L2 (registro, 2026-10-17)
- Nico aprueba la **opcion A** en chat ("opcion A"), incluida la apertura unica de la ventana de confirmacion 2026-04-01..09-30 y el uso del dataset L1 CANDIDATE.
- **L2 de ES en Kaggle (verificado en `L2_RELEASE_MANIFEST.json`):** dataset privado `nicolasbuttaro/edgelab-l2-es-20261015`, 177 archivos-sesion (ES_09-26 y ES_12-26, **solapados en fechas**),
  2026-06-28 a 2026-10-14; por sesion: `l2_depth` (MBP-10), `l1_quotes` (cotizaciones con tamanos) y agregados `.npz`. QA: 174 PASS y 3 marcadas (2026-08-11 cruzado en ambos contratos; ES_12-26 2026-07-17).
  **`research_allowed = false`** ("L2 sin auditoria de payload ni aprobacion externa; solo preparacion tecnica"). Ventana de desarrollo L2 firmada: 2026-07-01..2026-10-31; holdout L2 2026-11-01..12-31 sin datos.
  Limitaciones declaradas: agresor L2 heuristico sin validar (no se usa), 5 archivos con reloj corrido (P-84), hay que elegir un contrato principal por sesion.
  **Consecuencias para F0:** (1) el L2 **no cubre** la ventana de descubrimiento de ticks (empieza 2026-06-28), solo el tramo jul-sep de la confirmacion; (2) las sesiones de octubre caen en el holdout de ticks (>= 2026-10-01): **no se usan**;
  (3) como la bandera `research_allowed` es falsa, **la Fase 0C (cola real con L2) queda fuera hasta que Nico levante esa bandera o apruebe el uso**. Cuando se habilite, usaria `l1_quotes` (resuelve la cotizacion vieja de L1) y `l2_depth` (posicion en cola) sobre ~jul-sep 2026 sin tocar octubre.
- Ejecucion F0 (T1/T2, ticks L1) autorizada: kernel `edgelab-f0-exec-pasiva-es-v1`.
