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

## 5b. OK de Nico (26/09) y plan de la sesión local
Nico: «estoy de acuerdo con todo eso, armalo» → se congelan las recomendaciones de §3 (censo completo con etiqueta I1 ∨ I2, A1 como agotamiento, S3 + S2, horizonte 3 × duración con tope de sesión).
**Nota (27/09, merge):** este plan quedó **superado** por la implementación de §6 (sesión en la nube); se conserva como registro.
Plan que se había escrito:
1. Núcleo causal en `edgelab/bridge/indicators/espejo_impulsos.py`: impulso con `tools/espejo_macro.py::detect_var` (umbral constante 17 t en 25t; 3·ATR previo en tiempo), e_min 0,3, r 0,3; sólo `why == 1` confirma B (los `why == 2` quedan en el censo como impulso sin confirmar).
2. Semejanza con `tools/espejo_semejanza.py::eventos` (sólo los componentes, que usan datos ≤ vela k; el desenlace se calcula aparte y de forma causal); percentiles contra la referencia de sesiones anteriores.
3. Estados y eventos de §3.4, por sesión; tests sintéticos de §3.6.
4. Capa del visor `bundles/espejo/<asset>.json` + dibujo con primitiva en `index.html` (tick_25, time_5m, time_15m).

## 6. Implementación (2026-09-27) y encuadre de Nico: «zonas que no estuvieron listas»

**Nico (27/09):** el indicador tiene que marcar las zonas que no estuvieron «listas» para ser comerciadas, apostando a
que el precio las atraviese una vez que haya resuelto cierto nivel de comercio en otra área.

**Cómo entra al kernel.** Entra como **atributos del censo, no como filtros**: la regla de población sigue vigente y el
censo sigue completo.
- **`no_lista_lo` / `no_lista_hi` / `no_lista_frac`: la zona no lista.**
  - Se arma el perfil de volumen del impulso: el volumen de cada vela se reparte parejo en su rango, recortado a
    [A, B].
  - La zona es el tramo contiguo más ancho con densidad menor que 0,25 × la mediana del perfil. Es el precio que el
    impulso cruzó casi sin negociar.
  - El visor lo dibuja como una franja propia.
- **`aceptacion_B` y `velas_en_B`: si ya resolvió comercio en otra área.**
  - Es el volumen negociado en la banda de 0,25·W junto a B, desde B hasta cada evento de la vuelta, dividido por el
    volumen del impulso.
  - Se calcula en cada evento de la vuelta. Mide cuánto comerció el precio en B antes de volver.
- Los dos parámetros (0,25 de densidad y 0,25·W de banda) se congelan ahora, antes de mirar censos.

**Cómo podría refutarse el encuadre:**
- Nico juzga ✓/✗ en el visor una muestra de franjas «no listas».
- Si la precisión es menor que 70 %, el perfil no captura lo que él ve.
- Medir si el precio atraviesa esas franjas más que el azar después de aceptar en B es **campaña**: pre-registro y OK
  de Nico.

**Estado del código:**
- **Kernel:** `edgelab/bridge/indicators/espejo_impulsos.py`.
  - El detector está portado de `detect_var`, con test de paridad exacta.
  - Tiene todos los estados de §3.4 y los atributos de §3.1, §3.3 y §6.
- **Port JS del visor:** `viewer/nt8_bridge/espejo_impulsos.js`, con paridad de eventos Python ↔ JS testeada.
- **Tests:** `tests/research/test_espejo_impulsos.py` y `test_espejo_impulsos_js.py`. Cubren determinismo,
  anti-lookahead, los cuatro estados, fin de sesión, censo cerrado, zona no lista y paridad.
- **Causalidad:** el fin de sesión sale del calendario (`last_of_session`), no del final del arreglo. Una serie cortada
  deja los estados abiertos, sin inventar vencimientos.

## 7. Semejanza v2 por nivel de precio (2026-09-27, pedido de Nico: «lo más parecido posible, pero en espejo»)

### Qué estaba mal en la v1
Los componentes `forma`, `ondas` y `efi` comparan **caminos de cierres** con el tiempo normalizado. Con pocas velas no
miden nada. Diagnóstico target-free en ES RTH a 5 min, jul-2025 a mar-2026 (`tools/espejo_semejanza_diag.py`):
630 impulsos y 809 eventos de vuelta.

| x | vueltas de ≤ 2 velas | `ondas` = 0 | `efi` = 0 |
|---|---|---|---|
| 0,25 | **91 %** | 69 % | 41 % |
| 0,5 | 48 % | 50 % | 17 % |
| 0,75 | 16 % | 38 % | 9 % |

Con una vuelta de 2 cierres, `forma` compara el tramo espejo contra una **recta**. Así mide la curvatura del impulso,
no la de la vuelta.

### Qué mide la v2 (`semejanza_niveles`)
El espejo recorre **los mismos niveles** que el impulso, en orden inverso. Por eso la v2 se alinea por **nivel de
precio** y no por tiempo. Se mide sobre el tramo ya retrocedido [B − f·W, B], y cada vela aporta su rango H–L, no sólo
su cierre.

- **`sim_t`:** solapamiento (1 − ½·L1) entre el **tiempo pasado en cada nivel** durante el tramo espejo del impulso y
  durante la vuelta. Si el impulso frenó en un nivel, el espejo también frena ahí.
- **`sim_v`:** lo mismo con el **volumen por nivel**. Es la contracara de la zona no lista: donde el impulso no negoció,
  el espejo tampoco.
- **`sim_vel`:** exp(−|log(duración de la vuelta / duración del tramo espejo)|). Es absoluta, en [0, 1].
- **`sim_abs`:** (`sim_vel` + `sim_t`) / 2. Es absoluta: 1 significa espejo idéntico.
  - `sim_v` queda fuera del promedio porque en ES correlaciona 0,87–0,95 (Spearman) con `sim_t`: son casi la misma
    información.
- **Marca «parecida» (`S2v2`):** `sim_vel` y `sim_t` quedan en o por encima de la mediana de las sesiones anteriores.
  Es la misma regla que S2 (§3.3), con la forma por nivel en vez de la forma por cierres.

### Por qué es mejor, verificado sin mirar desenlaces
- **Tiene sentido con 1–2 velas de vuelta**, que es el caso del 91 % de los candidatos al 25 %.
- **Aporta información nueva:** `sim_t` casi no correlaciona con la velocidad (ρ ≈ −0,1). Separa forma de velocidad,
  que era la intención de las dos palabras de Nico («velocidad y forma de las ondas»).
- **Coincide con la v1 donde la v1 sí funciona:** al 75 %, donde el 84 % de las vueltas tiene 3 o más velas, ρ(`sim_t`,
  `forma`) = 0,63. Al 25 %, donde la v1 degenera, baja a 0,17.
- **Tests sintéticos:**
  - espejo exacto: `sim_t` y `sim_v` > 0,85 y `sim_vel` > 0,8;
  - la misma vuelta con la pausa en otro nivel y la misma velocidad baja `sim_t` en más de 0,15;
  - con una vuelta de una vela, `forma_fiable` = False, pero `sim_t` sigue definida.

### Qué se conserva
- La v1 sigue en el censo, sin cambios: `vel`, `efi`, `forma`, `ondas`, `S` y `S2`. Así los resultados de ESPEJO-SIM y
  ESPEJO-MACRO siguen siendo comparables.
- Cada evento lleva además `velas_vuelta` y `forma_fiable` (3 o más velas).
- El visor usa `S2v2` para el borde grueso.

### Cómo podría refutarse
Nico juzga ✓/✗ una muestra de vueltas `S2v2` y otra de no-`S2v2`. Si su juicio no las separa, la semejanza por nivel
tampoco es la que él ve. Medir si `S2v2` completa el espejo más que el azar es **campaña**: pre-registro y OK.

## 8. Corrección de Nico (27/09): qué es la «zona no lista»
- **Nico:** la zona no lista es **el espejo completo** (el rango A–B recorrido de ida y vuelta), no el tramo que el impulso cruzó sin negociar. La interpretación de §6 (`no_lista_*`) **no se descarta**: queda como atributo complementario.
- **Dos análisis distintos** (ninguno medido todavía):
  1. **Completar el espejo:** la vuelta B→A llega a A (lo que midieron ESPEJO-SIM y ESPEJO-MACRO, con impulsos eficientes).
  2. **El rango del espejo como zona a atravesar en el futuro:** después de completarse, el precio vuelve a cruzar A–B con más facilidad que el azar.
- **Sobre la definición del análisis 2 (Nico):** una carrera «llega a B antes de alejarse otro W» es demasiado restrictiva: el precio puede alejarse otro W del lado contrario y **aun así** atravesar el espejo después más que el azar. La definición tiene que permitir eso (p. ej. probabilidad o tiempo hasta atravesar dentro de un horizonte, sin barrera de fracaso, contra rangos de igual ancho, edad y distancia que no fueron espejo).
- **Estado:** Nico pide **no medir nada** hasta entender los mecanismos, calibrar y confirmar cuestiones de definición.
