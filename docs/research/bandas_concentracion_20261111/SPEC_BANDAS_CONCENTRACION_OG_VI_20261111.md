# Bandas de concentración OG+VI (LUX-IMB) — especificación del detector

Estado: VIGENTE (especificación target-free; **sin ninguna medición de desenlaces**)  
Fecha: 2026-11-11 · Origen: pedido de Nico a partir de su chart de TradingView (EURUSD M1, Imbalance Detector [LuxAlgo]).  
Referente: `docs/NORTH_STAR.md` · sha256 del cuerpo `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.  
Familia: **LUX-IMB-CONCENTRACION** (nueva; no hereda resultados, poblaciones, costos ni presupuesto de multiplicidad de
LUX-IMB-IMPULSOS ni de ninguna otra familia).

## 1. Qué es

Nico marca a mano, sobre el Imbalance Detector de LuxAlgo (OG + VI), franjas horizontales de unos 6–10 pips donde se
apilan muchas zonas. La idea: **un corte vertical en un momento dado atraviesa muchas zonas vivas dentro de un rango de
precio chico**. Esta especificación convierte esa marca visual en una regla causal y reproducible.

## 2. Regla (idéntica en los tres lugares)

| dónde | archivo |
|---|---|
| referencia Python | `edgelab/bridge/indicators/bandas_concentracion.py` (`detectar`) |
| visor (capa `&cz=1`) | `viewer/nt8_bridge/bandas_concentracion.js`, usado por `viewer/nt8_bridge/index.html` (EDGELAB_CONC_ZONAS_V1) |
| CLI (lista + calibración) | `tools/luximb_parity/bandas_concentracion.py` |
| tests y paridad Python↔JS | `tests/research/test_bandas_concentracion.py` |

1. **Zonas de entrada:** LUX-IMB OG y VI en M1 (las del bundle del visor, `runs[0].zones` con `source == "luxalgo"`),
   cada una con `t0` (nace al cierre de su vela), `t1 = t0 + 500 min`, `bottom`, `top`.
2. **Corte vertical:** en cada vela M1, por su hora de apertura `t`, se toman las zonas con `t0 <= t < t1`
   (ya nacidas y vivas).
3. **Banda candidata:** de alto `alto` (por defecto **8 pips**), empezando en el piso de cada zona viva; cuenta las zonas
   **completamente contenidas** (`top <= piso + alto`; `bottom >= piso` por construcción).
4. **Marca:** si la mejor banda contiene **>= `umbral` zonas** (por defecto **22**), se marca; se sacan esas zonas del
   corte y se repite, así un mismo corte puede dar varias bandas en precios distintos (sin compartir zonas).
   Desempate: el piso más bajo con el máximo conteo.
5. **Unión de encadenadas:** si la banda marcada pisa en precio una banda todavía viva (`t <= t1` de esa banda), no nace
   una nueva: la existente se alarga a `t1 = t + 500 min` y guarda `n = max(n, conteo)`. Si no, nace `[t, t + 500 min]`.

**Causalidad.** `t0`, `piso`, `techo` y `n0` se conocen en `t0` con información de `t0`. **`t1` y `n` dependen del
futuro** (la banda se alarga mientras la concentración sigue): ningún análisis puede usarlos como dato disponible en `t0`.
Una regla operable sobre la banda sólo puede usar lo que la banda "sabe" en cada vela: que nació, y si en esa vela
sigue cumpliendo la condición.

**Parámetros declarados:** `alto = 8 pips`, `umbral = 22`, `vida = 500 min`. En el visor: `&czh=<pips>`, `&czk=<zonas>`.
Para no-FX, `alto` se da en ticks del instrumento (el CLI y el visor usan pip = 10 ticks sólo cuando tick < 0,001).

## 3. Calibración (target-free; no mira precios futuros ni desenlaces)

Objetivo fijado por Nico **antes** de mirar: entre 1 y 3 bandas cada 2 días de mercado.
Datos: bundle `EURUSD_DUKAS_M1_LUXIMB` (Dukascopy mid, 2026-03-17 → 2026-06-17, 96.069 velas M1, 5.188 zonas;
sha256 del JSON `7a53f36f17e7ef0fba340597cb81d103954e4ea37c3e944b7b86c075532eaec6`), 66,4 días hábiles. `alto = 8 pips`.

| umbral | bandas | por 2 días | duración media (h) |
|---|---|---|---|
| 18 | 80 | 2,41 | 16,8 |
| 20 | 72 | 2,17 | 16,3 |
| **22** | **63** | **1,90** | 16,1 |
| 25 | 49 | 1,48 | 15,8 |
| 28 | 38 | 1,14 | 15,8 |

Se eligió 22 por quedar en el centro del rango pedido. La lista completa de las 63 bandas está en
`BANDAS_EURUSD_MAR_JUN_2026.json` (esta carpeta). Paridad: Python y JS dan las mismas 63 bandas (mismos `t0`, `t1`, `piso`, `n`).

Observado al calibrar (no es resultado, es descripción del detector): el reparto es desparejo — hay semanas sin bandas
(17→26-mar) y días con varias.

## 4. Datos y cómo reconstruirlos

- El bundle no está en git (`viewer/nt8_bridge/bundles/*.json` es dato local). Se construye con
  `python tools/luximb_parity/build_luximb_fx_bundle.py <ticks.parquet> EURUSD <desde> <hasta> viewer/nt8_bridge/bundles`
  desde ticks de Dukascopy (JForex: UTC, bid, ask, last = mid). El builder agrega la entrada al catálogo `manifest.js`.
- Para ver las bandas: `http://localhost:8089/?asset=EURUSD_DUKAS_M1_LUXIMB&corr=0&cz=1&tf=time_1m`.
- **Holdout (HOLDOUT-A4): sesiones >= 2026-10-01 para todo instrumento.** Mar–jun 2026 es desarrollo. No construir
  bandas sobre datos del holdout para elegir nada (sí está permitido para validaciones target-free: paridad, geometría).
- La paridad del detector LUX-IMB está medida en NQ (1507/1507), **no en FX** (`PARITY_ABSTAIN` en el bundle EURUSD).
  Cualquier análisis sobre EURUSD hereda esa abstención: primero conviene confirmar que las zonas de Python coinciden con
  las del indicador de TradingView/NT8 sobre el mismo par.

## 5. Espacio de eventos y estados (regla de población, obligatorio antes de congelar cualquier población)

Las familias que se pueden medir sobre una banda, todas distintas; ninguna está elegida todavía:

1. **Nacimiento** (`t0`): el momento en que el corte cruza el umbral. Evento, N ≈ 1 por día.
2. **Aproximación**: el precio se acerca a una banda viva desde afuera (a k pips).
3. **Primer toque** del precio a la banda viva (desde arriba / desde abajo, por separado).
4. **Toque n-ésimo.**
5. **Ruptura / aceptación**: cierre M1 del otro lado de la banda (y permanencia m velas).
6. **Expiración**: fin de la banda sin tocar (sólo observable a posteriori; ojo con `t1`).
7. **Precio dentro de la banda** (estado continuo, vale en cada vela) y **distancia a la banda viva más cercana**
   (estado continuo, mucha más potencia que los eventos).
8. **Confluencia**: varias bandas vivas cerca, o banda + otra estructura (sesión, nivel redondo).
9. **Intensidad**: el conteo en cada vela (no sólo el binario ≥ umbral), como variable continua.

**Separar evento de estado** (regla permanente): una campaña que mida sólo toques debe justificar por escrito por qué
no mide el estado (7) ni la intensidad (9).

## 6. Hipótesis candidatas (para que el agente de análisis elija y pre-registre; ninguna medida)

- **Justificación económica.** Muchas zonas de desequilibrio (OG/VI) superpuestas en pocos pips marcan precios donde
  el flujo fue unilateral varias veces en pocas horas: posible liquidez en reposo / órdenes dejadas sin llenar.
  Predicción a probar: el precio *reacciona* (rebota o se frena) en la banda más de lo que lo hace en una franja de igual
  alto sin concentración.
- **Cómo podría refutarse.** (a) Contra un control de franjas de 8 pips con el mismo historial de precio (misma distancia,
  misma volatilidad, misma hora) pero sin concentración, la tasa de rebote/frenado no difiere, con MDE publicado;
  (b) el efecto existe sólo porque las zonas se crean donde el precio ya estuvo lateral (la banda describe un rango, no
  lo predice) — el control debe igualar "tiempo que el precio pasó en esa franja" antes de `t0`;
  (c) el efecto no supera costos canónicos de EURUSD (`edgelab/costos.py`).
- Medir **los dos canales** (direccional y no direccional: |movimiento| o tasa de cruce) y la distribución completa.

## 7. Lo que falta antes de cualquier medición con desenlaces

- Manifiesto/pre-registro committeado con: etapa EF del embudo, población elegida de la lista §5 con alternativas
  escritas, control, estimand, número efectivo de hipótesis, MDE, costos canónicos.
- Registro en el contador global (`docs/research/TRIAL_REGISTRY_GLOBAL.jsonl` vía `TrialRegistry.ensure`) **antes** de correr.
- Preflight (`edgelab.research.preflight`) si es grilla; revisor + revisor2.
- Registro MEDIDO/NO MEDIDO propio de la familia (se crea con la primera medición, en el mismo commit).
- Confirmar paridad LUX-IMB en FX (o declarar la abstención como riesgo en el manifiesto).
