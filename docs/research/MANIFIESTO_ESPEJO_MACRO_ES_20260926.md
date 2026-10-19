# Manifiesto ESPEJO-MACRO: el espejo de impulsos grandes, a una escala que pueda pagar la fricción (ES, 2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Pedido de Nico (2026-09-26):** la misma lógica de ESPEJO-SIM, más macro, porque cuanto mayor es la distancia del
trade más se diluyen las fricciones.
**Estado:** PRE-REGISTRO. Escrito y commiteado antes de tocar datos. **No se ejecuta nada sin el OK explícito de
Nico** a este manifiesto (regla STOP: el estudio mide si el precio llega o no a un nivel, o sea retornos, y la
parte E2 es P&L).
**Familia:** ESPEJO-MACRO, registrada acá. Es independiente de ESPEJO-SIM (MNQ, 25 ticks) y de TBZX: no hereda
resultados, poblaciones, terciles, costos ni presupuesto de multiplicidad. Lo único que toma de ESPEJO-SIM es la
**definición** del evento, de la semejanza y del nulo al cierre, fijadas antes de ver estos datos.

## 1. Por qué macro: la cuenta que manda

Entrada en el evento (la vuelta recorrió la fracción f del impulso), objetivo en A (espejo completo), stop en B
(extremo nuevo). Con probabilidad p de llegar a A antes que a B:

  **EV por trade = W · (p − f) − costo**

Sin memoria, p = f. **El exceso mínimo que hace falta sobre el nulo es costo / W.** Con 2,4 t de ida y vuelta en ES
(costo agresivo medido en IVC):

| W | Exceso necesario |
|---|---|
| 17 t | 14 pp |
| 60 t | 4 pp |
| 120 t | 2 pp |
| 200 t | 1,2 pp |

ESPEJO-SIM encontró, sin replicar todavía, +1,5 a +5 pp en impulsos de 17 t. Sólo una escala mayor puede convertir un
exceso de ese tamaño en un edge neto.

## 2. Datos y particiones

| Rol | Fuente | Período | Qué se mide |
|---|---|---|---|
| **Descubrimiento** | SPY 1 min, Kaggle público `rockinbrock/spy-1-minute-data` (tercero, sin licencia declarada: sólo uso interno); sha256 `81d936c7…c49b`; se eliminan las 638.054 filas duplicadas idénticas como en `tools/ivc_largo.py`, y se aborta si hay minutos repetidos con valores distintos | 2008–2021, sólo RTH 9:30–16:00 ET | **información** (E1) |
| **Replicación** | ES, Kaggle `nicolasbuttaro/edgelab-ticks-es-preholdout`, ticks agregados a velas de tiempo | 2025-07-01 a 2026-03-31 | E1 y **E2** (económico) |
| **Confirmación** | ES abr–jun 2026 | una sola apertura | sólo si E2 replica, con campaña y OK de Nico |
| Holdout | desde 2026-07-01 | — | **no se toca** |

- **ES en dos variantes, declaradas ahora:**
  - **RTH 9:30–16:00 ET:** comparable con SPY. **Es la principal.**
  - **Sesión completa** (sin la pausa de 16:00–17:00 CT): secundaria, sólo descriptiva.
- **Sin cruce de sesiones:** cada día de SPY y cada trade date de ES es independiente. Todo evento se resuelve dentro
  de su sesión (en las cuentas de prop firms hay que cerrar antes del cierre).

## 3. Población

**Velas de tiempo:** 5 min (escala principal) y 15 min (escala secundaria), OHLC en precio.

**Detector:** la lógica TBZX de `tools/tbzx_espejo.py::detect`, sin cambios salvo el ancho mínimo, que pasa a ser
**relativo a la volatilidad**:
- `minW(j) = k · ATR14(j − 1)`: ATR de 14 velas cerrado en la vela anterior, causal;
- eficiencia ≥ 0,6 y fin del impulso con un retroceso ≥ max(2 ticks, 0,3·W), fijos como en TBZX;
- «tick» = 0,01 USD en SPY y 0,25 pts en ES.

**Grilla (fijada ahora, se publica entera):**

| Escala | `maxBars` | k |
|---|---|---|
| 5 min | {12, 24, 48} (1, 2 y 4 h) | {3, 4, 6} |
| 15 min | {4, 8, 16} (1, 2 y 4 h) | {3, 4, 6} |

18 configuraciones.

**Evento:** el primer cierre de vela en que la vuelta desde B alcanzó x ∈ {0,4; 0,5; 0,75} del impulso, sin extremo
nuevo antes. Uno por impulso y por x.

**Espacio de eventos considerado:**
- **Creación:** descartada, todavía no hay vuelta.
- **Estado continuo** (cada vela de la vuelta): sería el próximo paso si el evento no alcanza.
- **Segunda vuelta:** descartada.
- **Cómo podría refutarse la población:** si la semejanza sólo predice en el estado continuo.

## 4. Semejanza (idéntica a ESPEJO-SIM)

La vuelta, hasta el evento, se compara contra el tramo final del impulso invertido en el tiempo:

| Componente | Definición |
|---|---|
| `vel` | −\|log(velocidad de la vuelta / velocidad del tramo espejo)\| |
| `efi` | −\|eficiencia de la vuelta − eficiencia del tramo espejo\| |
| `forma` | −RMSE entre los caminos normalizados, con 20 puntos |
| `ondas` | −\|ondas por W de la vuelta − del tramo espejo\|, zigzag con umbral 0,1·W |
| **S** | promedio de los rangos percentiles (empates al medio) de los cuatro |

Las distribuciones de referencia y los terciles de S se fijan **en SPY** por configuración y se reusan sin cambios en
ES.

## 5. Resultado, nulo y estimands

**Espejo:** después del evento, llega a A antes de un extremo nuevo más allá de B, dentro de la sesión. Los
censurados (la sesión termina antes) se reportan y quedan fuera de la tasa.

**Nulo exacto, al cierre:** f = la fracción recorrida al **cierre** de la vela del evento. Es la lección de la
enmienda 1 de ESPEJO-SIM: el nulo al extremo de la vela está sesgado. El nulo al extremo se reporta sólo como
diagnóstico.

**E1 — información (SPY y ES):**
- exceso = P(espejo) − f;
- **prueba principal**: exceso(T3 de S) − exceso(T1 de S);
- secundarias: exceso(T3) contra 0 y las mismas pruebas por componente.

**E2 — económico (sólo ES, sólo configuraciones que sostienen E1):** por evento del T3, en ticks,

  `G = (espejo ? (1 − f)·W : −f·W) − costo − (espejo ? 0 : slip)`

- `costo` = 2,4 t de ida y vuelta (IVC agresivo), con escenario de 1,5 t;
- `slip` = 1 t extra en el stop;
- entrada al cierre de la vela del evento; ejecución a nivel de vela, sin reconstruir la cola.

**Candidato** sólo si el IC 95 % inferior de la media de G es > 0.

Sólo con velas no se puede auditar el fill del stop dentro de la vela. Antes de cualquier confirmación, E2 se recalcula
sobre los ticks de ES, con una salida realista.

## 6. Multiplicidad y reglas de decisión (fijadas ahora)

- **Descubrimiento (SPY):**
  - 18 configuraciones × 3 x × (principal + T3 contra 0 + 8 por componente) = **540 pruebas**, BH-FDR q = 0,10;
  - número efectivo de hipótesis primarias: **54** (la principal por configuración y x).
- **Replicación (ES RTH), E1 sostenido:**
  - la **misma** configuración, x y prueba pasan FDR en SPY;
  - en ES tienen el mismo signo con IC 95 % > 0;
  - son dos contratos o más de ES en la ventana: se exige que cada trimestre tenga el mismo signo, publicando el IC
    de cada uno.
- **E2** se calcula sólo para lo que sostiene E1. Lo demás se publica como descriptivo. **Nada se elige por mayor G.**
- **Confirmación abr–jun:** una apertura, con un solo candidato por configuración y x, congelado antes de abrir.
- **Todo nulo publica su MDE.** Si el MDE de ES supera costo/W, el resultado se declara «sin potencia», no «muerto».

## 7. Bootstrap y dependencia

- IC 95 % por bootstrap de **sesiones** (1.000 réplicas), porque los eventos de una sesión se superponen.
- Además, en ES, bootstrap por semana como chequeo de robustez.

## 8. Justificación económica y cómo podría refutarse

- **Mecanismo candidato:** una vuelta con la misma velocidad, eficiencia y estructura que el impulso indica un
  participante de tamaño comparable del otro lado. Los que entraron en el impulso quedan atrapados, y sus stops
  alimentan el recorrido completo. En escala de horas debería verse más limpio que en 25 ticks, donde domina el
  rebote de la vela.
- **Alternativas:**
  - el recorrido es el de un precio sin memoria (exceso ≈ 0);
  - la semejanza sólo refleja momentum de la vuelta: sostiene `vel` y no `forma`, `ondas` ni `efi`;
  - la semejanza sólo refleja volatilidad.
- **Se refuta** si:
  1. ninguna prueba principal pasa FDR en SPY;
  2. lo que pasa no replica en ES; o
  3. replica pero G tiene IC inferior ≤ 0 con costo de 2,4 t.

  En los casos 1 y 2 la familia se cierra con acta. En el 3 queda como información (filtro o timing de otra
  estrategia), no como sistema.

## 9. Riesgos y datos faltantes

- **SPY no es ES:** es un ETF, tiene sólo RTH, velas de 1 min armadas por un tercero y dividendos. Por eso en SPY
  sólo se mide información y ES es la replicación obligatoria.
- **SPY sin licencia declarada:** uso interno, no se publica.
- **Potencia en ES:** a 5 min y k = 3 se esperan del orden de 1 a 5 impulsos por sesión RTH, unos 150–900 eventos
  por x en 9 meses. Puede no alcanzar para 2 pp. El MDE se publica tal cual.
- **Superposición de impulsos y de eventos en distintos x del mismo impulso:** se reporta por x y no se suman.
- **Implementación:** `detect` hoy recibe `minW` fijo. La variante con umbral por vela se escribe con un test que
  reproduzca el detector original cuando el ATR es constante, antes de correr.
- **Faltan:**
  1. bajar SPY 1 min (Kaggle público) y ES pre-holdout (Kaggle privado, token nuevo);
  2. el script `tools/espejo_macro.py`, que reusa `eventos()` de `tools/espejo_semejanza.py` sobre velas de tiempo;
  3. el OK de Nico.

## 10. Artefactos previstos

- `artifacts/research/espejo_macro/SPY/`: descubrimiento, con el sha de la fuente y de la versión deduplicada.
- `artifacts/research/espejo_macro/ES_RTH/`: replicación.
- Ledger del cerebro: lecciones y evidencias con sha de cada reporte. Se actualiza el registro MEDIDO/NO MEDIDO en el
  mismo commit que cada resultado.

---
**Alcance (2026-09-26, pedido de Nico):** este estudio es un **tamiz** («¿seguir con la idea del espejo?»), no un
veredicto sobre el espejo. Qué midió exactamente, qué no y la regla para cerrar la familia:
`docs/research/ESPEJO_MEDIDO_Y_NO_MEDIDO.md`. Un NO de acá invalida sólo su población, su detector (impulsos
**eficientes**, eficiencia ≥ 0,6), su semejanza y su horizonte.

## Enmienda 1 — regla de lectura de muestra mínima (después de ver SPY, 2026-09-26)

- **Regla:** no se interpreta ninguna celda con n < 30 por tercil.
- **Por qué:** con 3 a 15 eventos, el bootstrap por sesión colapsa y el FDR marca diferencias de ±30–40 pp que son
  artefactos.
- **Alcance:** es una regla de lectura. No cambia ningún número, ninguna prueba ni el FDR publicado, y no rescata ni
  descarta nada que la regla de sostenido no decida.

## Resultado (2026-09-26): SPY descubre, ES **sin potencia**; el tamiz sigue en SÍ

**Procedencia:** código `tools/espejo_macro.py` en `8595910` (velas de ES por bloques, mismo resultado que `193eea3`).
- SPY: 3.347 días, `artifacts/research/espejo_macro/SPY/`.
- ES RTH: 198 días (18-jul-2025 a 31-mar-2026), `artifacts/research/espejo_macro/ES_RTH/` (sha `356142b2c42b`).
- E2: `artifacts/research/espejo_macro/E2/e2.json`.

**SPY (descubrimiento):**
- **Semejanza (prueba principal):** en 5 min, las vueltas parecidas completan el espejo +3 a +11 pp más que las poco
  parecidas.
- **Por fracción recorrida:**

| x | Exceso sobre f (al cierre) |
|---|---|
| 0,4 | −2 a −12 pp |
| 0,75 | +6 a +16 pp, en todas las configuraciones con muestra |

**ES (replicación):**
- Ninguna prueba cumple la regla de sostenido, así que **E2 no se calcula** (`sostenidos: []`).
- **La razón es potencia, no ausencia:** con 198 días, la media amplitud del IC es ~21 pp en la prueba principal
  (MDE ≈ 30 pp) y ~11 pp en el exceso general (MDE ≈ 15 pp). El efecto de SPY es de 4–11 pp: ES no podía detectarlo.

**Concordancia de signo** (descriptiva, celdas con n ≥ 20 en ES; no entra en la regla de sostenido):

| Prueba | Mismo signo que SPY |
|---|---|
| Parecidas − poco parecidas | **10 de 10** |
| Exceso general al cierre | 11 de 15 |

Si no hubiera relación, que las 10 coincidan tiene una probabilidad de ~0,1 %. Pero las celdas se solapan (mismos
días, configuraciones vecinas), así que es una señal para seguir, no una prueba.

**Estado:** `ESPEJO_MACRO_ES_SIN_POTENCIA`. **No es una muerte.**
- En los términos de `ESPEJO_MEDIDO_Y_NO_MEDIDO.md`, el tamiz sigue en **SÍ**.
- Hace falta más muestra de ES o un instrumento macro equivalente con más historia: NQ o YM macro, ES en sesión
  completa, ES anterior a jul-2025 si se consigue.
- La confirmación de abr–jun **no** se abre: no hay candidato.

## Enmienda 2 — potencia: NQ, YM y ES en sesión completa (pedido de Nico, 2026-09-26, antes de bajar esos datos)

**Motivo:** con 198 días de ES RTH el MDE (~30 pp) triplica el efecto de SPY. No cambia ninguna definición: evento,
semejanza, nulo al cierre, grilla, terciles y referencias de SPY quedan iguales.

- **Nuevas muestras de replicación,** mismas ventanas (inicio de datos a 2026-03-31) y mismo código:
  - NQ RTH;
  - YM RTH;
  - ES sesión completa (18:00–17:00 ET del trade date, sin la pausa, velas desde la apertura de la sesión).
  - NQ e YM también en sesión completa, descriptivos.
- **Prueba de replicación combinada (nueva, fijada ahora):** eventos de ES + NQ + YM en RTH juntos. El bootstrap es
  **por día calendario**, y un día con eventos en los tres instrumentos cuenta como **un** cluster. Así, la
  correlación entre índices no infla la muestra efectiva.
- **Sostenido (reemplaza al de §6 para la replicación):**
  1. la prueba pasa FDR en SPY;
  2. la muestra combinada tiene el mismo signo con IC 95 % > 0;
  3. cada instrumento por separado tiene el mismo signo, sin exigir IC.
- ES sesión completa se reporta aparte y no entra en la regla.
- **E2 sigue siendo sólo sobre ES,** porque sus costos son los medidos. Si la combinada sostiene, se calcula E2 en ES
  RTH y en ES sesión completa, y el IC de ES solo se reporta tal cual.
- **Regla de lectura:** n ≥ 30 por tercil, igual que la enmienda 1.
- **Riesgo declarado:** NQ, YM y ES están muy correlacionados. La combinada gana potencia por los días en que los
  instrumentos difieren, no por triplicar. El bootstrap por día lo refleja.

## Enmienda 3 — aclaración de E2 (después de ver la combinada, 2026-09-26)

- **Qué pasó:** la implementación de E2 (`sostenidos()`) sólo miraba la prueba principal (T3 − T1). El §6 define
  «sostenido» **por prueba**, y el exceso general al cierre es una de las pruebas publicadas. Una celda cumple la
  regla de la enmienda 2 en esa prueba: 5 min, `maxBars` = 12, k = 4, x = 0,75.

| Muestra | Resultado |
|---|---|
| SPY | +7,8 pp, pasa FDR |
| Combinada | +9,4 pp [+2,2, +16,1], n = 90 |
| Signo por instrumento | ES +, NQ +, YM + |

- **Corrección:** E2 se calcula para toda prueba sostenida, sobre **la población de esa prueba**: T3 para la principal,
  todos los eventos en x para el exceso general. No se agregan pruebas ni se cambia ningún umbral.
- **Alcance:** la corrección es posterior a ver datos, así que cualquier resultado de E2 queda como **candidato a
  confirmar**, nunca como edge. Además, hay que contar que la celda salió de 54 × 2 pruebas revisadas contra la regla.

## Resultado de la enmienda 2 (2026-09-26): la semejanza no replica en futuros; el exceso al 75 % sí, sin margen económico robusto

**Procedencia:** código en `5a92195` más la aclaración de E2 (enmienda 3). Artefactos en
`artifacts/research/espejo_macro/{NQ_RTH,YM_RTH,COMB_RTH,ES_FULL,NQ_FULL,YM_FULL,E2_ES_RTH,E2_ES_FULL}/`
(combinada sha `d57451f593fe`).
- Días RTH: ES 198, NQ 186, YM 169.
- ES sesión completa: 203 trade dates.

**E1 — semejanza (prueba principal, T3 − T1):**
- **No replica en la combinada RTH:** signos mezclados entre instrumentos e IC muy anchos.
- En ES sesión completa (descriptiva, fuera de la regla) es positiva en todas las celdas con n ≥ 30, de +3 a +14 pp,
  con dos IC > 0.
- **Estado: sin confirmar en futuros.**

**E1 — exceso general al cierre en x = 0,75 (el giro que ya recorrió tres cuartos):**

| Celda | SPY | Combinada | Signo ES / NQ / YM | ¿Cumple la regla? |
|---|---|---|---|---|
| 5 min, 12 velas, k = 4 | +7,8 pp, FDR | +9,4 pp [+2,2, +16,1] | + / + / + | **sí** |
| 5 min, 24 velas, k = 4 | +7,2 pp, FDR | +9,8 pp [+0,0, +18,0] | + / + / + | **en el límite** |
| 5 min, 12 velas, k = 3 | +6,3 pp, FDR | +4,9 pp [+0,6, +9,2] | + / + / **−** | **no**: falla el signo de YM |

`sostenidos()` no verifica el signo por instrumento: esa condición se chequeó a mano, y por eso se descarta 5m_12_3.

**E2 — económico en ES, entrada al cierre del evento, objetivo A, stop B:**

| Celda | Muestra | n | G con costo 2,4 t | G con costo 1,5 t |
|---|---|---|---|---|
| 5m_12_4 | ES RTH | 32 | +12,2 t [−0,5, +23,9] | +13,1 t [+0,5, +24,4] |
| 5m_12_4 | ES sesión completa | 311 | +1,5 t [−2,2, +5,4] | +2,4 t [−1,3, +6,2] |
| 5m_24_4 | ES RTH | 24 | +9,9 t [−9,8, +25,1] | — |
| 5m_24_4 | ES sesión completa | 279 | +1,7 t [−2,2, +5,4] | +2,6 t [−1,4, +6,6] |

**Lectura:**
- El único «candidato» formal (5m_12_4 RTH con costo 1,5 t) tiene n = 32 y sale de una enmienda posterior. **No se
  promueve.**
- Con la muestra más grande (sesión completa), el G medio es **positivo pero chico** (+1,5 a +2,6 t) y su IC cruza el
  cero.
- **No se abre la confirmación de abr–jun.**

**Estado:** `ESPEJO_MACRO_EXCESO_075_REPLICA_SIN_MARGEN_ROBUSTO`.
- La información existe: el giro que ya recorrió el 75 % completa el espejo más que el azar en SPY 2008–2021 y en
  ES, NQ e YM 2025–26.
- Hoy es chica frente al costo. El tamiz sigue en **SÍ**, y la dirección que señala es mejorar la entrada y el stop
  dentro de la ventaja macro (análisis «micro»), o sea el mapa de MAE/MFE, antes que buscar más semejanza.
