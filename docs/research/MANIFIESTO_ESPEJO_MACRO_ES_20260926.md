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
