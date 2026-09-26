# Registro de familia ESPEJO-IND: indicador de impulsos espejados (2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** REGISTRO + PROPUESTA DE DEFINICIÓN. **No hay código.** Se implementa sólo después del OK de Nico a §3.
**Contexto:** `IDEA_INDICADOR_ESPEJO_NICO_20260926.md`, `HANDOFF_2026-09-26_HFT_REV_Y_ESPEJO.md`,
`MANIFIESTO_ESPEJO_SEMEJANZA_MNQ_20260926.md`, `MANIFIESTO_ESPEJO_MACRO_ES_20260926.md`.

## 1. Excepción a F9 (firmada por Nico)
F9 (nuevos indicadores) está pausada por decisión sellada de Nico. **Nico la levanta para este indicador y sólo para
él** (pedido del 26/09: «Registrá la excepción a F9. F9 está pausada, y la autorizo para este indicador»).
La pausa sigue vigente para cualquier otro indicador.

## 2. Registro
- **Indicador:** `EspejoImpulsos`, un kernel target-free y causal en `edgelab/bridge/indicators/espejo_impulsos.py`
  (contrato `docs/kernel_contract.md`). Es `BAR_DRIVEN` sobre OHLCV; no necesita footprint.
- **Subfamilias** (se enumeran todas; ninguna se descarta al construir):
  - impulso eficiente / ineficiente;
  - agotamiento confirmado por retroceso / por caída de velocidad;
  - vuelta parecida / no parecida;
  - desenlace completado / fracasado / vencido.
- **Parámetros:** se congelan en el documento de implementación con los valores de §3.4, antes de mirar censos.
- **Ledger propio:** `artifacts/hippocampus/espejo_ind_20260926.jsonl`.
- **No transporta** resultados, poblaciones, terciles, costos ni presupuesto de multiplicidad de TBZX, ESPEJO-SIM
  ni ESPEJO-MACRO. Sólo reusa **código** (`detect`, `detect_var`, `eventos`) y **definiciones geométricas**.
- **Qué no es:** una campaña. No mide P&L, no ajusta nada mirando si hubo espejo. Medir su valor es una campaña
  aparte, con pre-registro y OK de Nico.
- **Justificación económica:**
  - un impulso empujado por pocos participantes explora precio sin aceptación;
  - cuando el empuje afloja, el precio no tiene razón para quedarse y deshace el recorrido;
  - si eso existe, la vuelta debería parecerse al impulso y terminar en A más seguido que el azar al cierre (p = f);
  - a escala suficiente, eso puede pagar la fricción, porque el exceso necesario es costo / W.
- **Cómo podría refutarse (la familia):**
  - en una campaña futura, los candidatos parecidos no completan el espejo más que el nulo al cierre;
  - o lo hacen igual que los no parecidos;
  - o sólo por la velocidad (sería momentum, no espejo).

## 3. Propuesta de definición operativa (para el OK de Nico)

### 3.1 «Impulso ineficiente»
| Alternativa | Definición | A favor | En contra |
|---|---|---|---|
| **I1 camino** | eficiencia e = \|neto\| / camino recorrido por cierres, en [e_min, e_max) | geometría pura, igual en 25t y en tiempo | un impulso de pocos saltos grandes sale «eficiente» aunque sea forzado |
| **I2 participación** | volumen por tick recorrido (V / W) por debajo del percentil 33 de los impulsos **anteriores** (sesiones previas, sin incluir el actual) | es lo más cercano a «forzado, sin participación» | en velas de 25t el volumen por vela es casi constante, así que mide duración y no participación |
| **I3 las dos** | I1 e I2 a la vez | lo más fiel a la tesis | menos eventos, dos parámetros |

**Recomendación:** **detectar todos los impulsos** con `detect_var` y eficiencia mínima baja (e_min = 0,3, en vez del
0,6 de TBZX). A cada impulso se le calculan los dos atributos y la etiqueta `ineficiente = I1 ∨ I2` se guarda, sin
filtrar. Así el censo contiene la población completa y la comparación eficiente / ineficiente queda para la campaña.
Filtrar al construir sería elegir la población sin alternativas escritas, que es justo lo que prohíbe la regla de
población.

**Cómo podría refutarse:** Nico juzga ✓/✗ una muestra de impulsos marcados «ineficientes» en el visor (el mismo
método de los picos); si la precisión es < 70 %, la definición no captura lo que él ve.

### 3.2 «Afloja» (agotamiento, punto B)
| Alternativa | Definición | Estado |
|---|---|---|
| **A1 retroceso** | B = extremo del impulso; se confirma cuando el retroceso desde B alcanza r·W (r = 0,3, igual que `detect`). Causal: se conoce al cierre de esa vela | **recomendada, primaria** |
| **A2 velocidad** | la velocidad de las últimas n velas cae por debajo de una fracción de la velocidad media del impulso | se guarda como atributo (vela y valor), no dispara el estado |
| **A3 agresión** | cae el volumen agresivo a favor del impulso | **no disponible en ES**: el agresor es válido sólo en NQ (en ES, ~80 %). Queda anotada, no se implementa |

**Cómo podría refutarse:** si las B de A1 caen sistemáticamente antes del extremo que Nico marcaría (juicio ✓/✗), el
retroceso r·W confirma demasiado temprano.

### 3.3 «Espejo parecido»
Se reusa `tools/espejo_semejanza.py::eventos`, que da cuatro componentes contra el tramo espejo (el impulso recorrido
al revés): `vel` (velocidad), `efi` (eficiencia), `forma` (camino normalizado) y `ondas` (cantidad de giros).
Se evalúa en x ∈ {0,25; 0,50; 0,75} de la vuelta. El rango percentil de cada componente se calcula contra una
**referencia causal**: eventos de sesiones anteriores, nunca de la misma sesión ni posteriores.

| Alternativa | Candidato si… | A favor | En contra |
|---|---|---|---|
| **S1 compuesto** | S = promedio de los 4 percentiles ≥ 0,66 (tercil alto, como ESPEJO-SIM) | un solo número, comparable con lo ya medido | el tercil viene de otro estudio |
| **S2 por componente** | `vel` y `forma` ≥ mediana (lo que Nico dijo: «velocidad y forma de las ondas») | fiel a las palabras de Nico | dos umbrales |
| **S3 sin umbral** | toda vuelta que llega a x = 0,25 es candidata y se colorea por S (continuo) | nada arbitrario, el visor muestra el gradiente | el estado «candidato» deja de significar «parecido» |

**Recomendación:** **S3 en el censo** (todas las vueltas, con S y sus 4 componentes), y **S2 como la marca de
«parecido»** en el visor (borde más grueso). El umbral queda como parámetro congelado, no como filtro del censo.

**Cómo podría refutarse:** Nico juzga ✓/✗ una muestra de vueltas marcadas «parecidas» y otra de «no parecidas»; si su
juicio no distingue entre los dos grupos, la semejanza calculada no es la que él ve.

### 3.4 Estados (sin repintado; todos quedan en el censo)
1. **IMPULSO:** A→B detectado; B se confirma por A1. Evento `IMP_CONFIRMED` al cierre de la vela que confirma.
2. **CANDIDATO:** la vuelta llega a x = 0,25 sin extremo nuevo más allá de B. Evento `MIRROR_CANDIDATE` con S y los
   componentes. Se actualiza en x = 0,50 y 0,75 con eventos **nuevos** (`MIRROR_PROGRESS`); nada anterior se reescribe.
3. **COMPLETADO:** la vuelta toca A antes de un extremo nuevo más allá de B. Evento `MIRROR_COMPLETED` con sobrepaso
   (fracción de W) y duración.
4. **FRACASADO:** un extremo nuevo más allá de B (`MIRROR_FAILED`, reason = `new_extreme`) o vencimiento
   (`MIRROR_EXPIRED`, reason = `horizon` / `session_end`). El horizonte es H = 3 × la duración del impulso en velas,
   con el fin de sesión como tope.
5. Los impulsos cuya vuelta nunca llega a x = 0,25 quedan como `IMP_NO_MIRROR` al vencer.

**Parámetros por defecto (se congelan con el OK):**
- **25t:** maxBars 20 y minW 17 t, de la configuración de Nico en TBZX; e_min 0,3; r 0,3.
- **Velas de tiempo (5 y 15 min):** `detect_var` con minW = 3·ATR(14) cerrado en la vela anterior, maxBars 24,
  e_min 0,3 y r 0,3.

### 3.5 Visor
- Colores:
  - impulso: gris;
  - candidato: ámbar (borde grueso si S2);
  - completado: verde;
  - fracasado: rojo;
  - sin espejo: gris claro.
- El impulso A→B y su vuelta B→(x o A) se dibujan como un par de segmentos unidos en B. Los niveles A y B se dibujan
  como líneas horizontales hasta el desenlace.
- Se dibuja **sólo con información disponible a la hora de cada vela**: el estado que se ve en la vela j es el que
  existía al cierre de j. Así el visor no muestra supervivientes.
- Funciona sobre `tick_25`, `time_5m` y `time_15m`: el kernel corre sobre la serie activa.

### 3.6 Tests (fixtures chicos y deterministas)
- Determinismo bit a bit.
- Anti-lookahead: truncar la serie en j no cambia ningún evento anterior a j.
- Los cuatro estados en caminos sintéticos armados a mano: espejo completo, extremo nuevo, vencimiento y vuelta que
  no llega a x = 0,25.
- Censo cerrado: cada impulso termina en exactamente un estado final.

## 4. Qué necesito de Nico
1. **Ineficiente:** ¿recomendación (censo completo + etiqueta I1 ∨ I2), o filtrar por I1, I2 o I3?
2. **Afloja:** ¿A1 retroceso r·W como primaria?
3. **Parecido:** ¿S3 en el censo + S2 (vel y forma ≥ mediana) como marca?
4. **Horizonte:** ¿3 × duración del impulso, con tope en fin de sesión?

## 5. OK de Nico (26/09) y estado
Nico: «estoy de acuerdo con todo eso, armalo» → se congelan las recomendaciones de §3 (censo completo con etiqueta I1 ∨ I2, A1 como agotamiento, S3 + S2, horizonte 3 × duración con tope de sesión).
**Estado al cortar la sesión:** código **no empezado**. Plan de implementación:
1. Núcleo causal en `edgelab/bridge/indicators/espejo_impulsos.py`: impulso con `tools/espejo_macro.py::detect_var` (umbral constante 17 t en 25t; 3·ATR previo en tiempo), e_min 0,3, r 0,3; sólo `why == 1` confirma B (los `why == 2` quedan en el censo como impulso sin confirmar).
2. Semejanza con `tools/espejo_semejanza.py::eventos` (sólo los componentes, que usan datos ≤ vela k; el desenlace se calcula aparte y de forma causal); percentiles contra la referencia de sesiones anteriores.
3. Estados y eventos de §3.4, por sesión; tests sintéticos de §3.6.
4. Capa del visor `bundles/espejo/<asset>.json` + dibujo con primitiva en `index.html` (tick_25, time_5m, time_15m).
