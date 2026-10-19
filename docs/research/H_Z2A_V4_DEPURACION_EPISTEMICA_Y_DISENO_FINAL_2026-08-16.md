# H-Z2A v4 — depuración epistémica, subhipótesis y diseño final

- **Fecha:** 2026-08-16
- **Estado:** `HYPOTHESIS_REFINED_NOT_RUN`
- **Decisión de Nico:** hacer v4 antes del manifiesto; `BigTrap2` se usa **sólo como fixture**; Nico ya dispone de L2 y GEX.
- **Firewall:** `outcomes_accessed=false`, `pnl_accessed=false`, `holdout_included=false`, `multiplicity_spent=0`.
- **No autoriza:** F4, lectura de outcomes, optimización, P&L, join L2/GEX↔zonas ni acceso al holdout.
- **Referente:** `docs/NORTH_STAR.md`, sha256 vigente `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.
- **Historia preservada:** v1 narra; v2 operacionaliza; v3 amplía la literatura; **v4 corrige y sustituye las afirmaciones señaladas aquí sin reescribir el pasado**.

---

## 0. Dictamen ejecutivo

La dinámica propuesta por Nico sigue siendo **plausible y testeable**, pero la búsqueda focalizada no encontró una fuente primaria que pruebe como una sola ley la secuencia completa:

> aproximación desde lejos → giro antes de la zona → separación/reset → segunda aproximación con fuerza → acceso y posible travesía.

La literatura sí respalda **componentes adyacentes**: interrupción de tendencias en niveles técnicos; clustering de órdenes; aceleración después de cruzar niveles; resiliencia/reposición del libro; revelación de liquidez latente; y pinning/repulsión en vencimientos de opciones. Por lo tanto, H-Z2A no es “un fenómeno ya demostrado” que EdgeLab sólo deba replicar. Es una **hipótesis compuesta original** cuya cadena debe desarmarse en estimands falsables.

Decisión de portadores, ya sin trasladarle a Nico una elección técnicamente prematura:

1. **`BigTrap2`: fixture de ingeniería únicamente.** Su altura mediana de 1 tick vuelve degenerada la medición de penetración y sus resultados anteriores cerraron la narrativa de “imán”.
2. **`aVolClusterPOI` v0.5: portador semántico principal**, usando una configuración fija ya existente, sujeto a ceguera de outcomes y a publicar los componentes de `QualityScore` sin filtrar por el score compuesto.
3. **`Gaps2` v2.0: control mecánico**, no sustituto semántico.
4. **`HFTZones2`: no es portador inicial**: hay evidencia de paridad fuerte, pero su estado canónico/formal y la limitación de resolución temporal deben reconciliarse antes de uso científico.

L2 y GEX **no se deben adquirir**: ya existen. El próximo trabajo es un inventario sellado y gates de validez. Se pueden auditar en paralelo, pero no condicionan la instrumentación outcome-free ni se cruzan con H-Z2A hasta pasar sus gates.

---

## 1. Correcciones explícitas a v3

| Afirmación de v3 | Corrección v4 | Consecuencia |
|---|---|---|
| “El fenómeno está estudiado” | Sus piezas están estudiadas; no se halló una prueba directa de la cadena completa ni del efecto condicional “near-miss → segunda aproximación”. | H-Z2A queda como hipótesis compuesta, no como replicación. |
| *Poor high / poor low* “es el near-miss con nombre propio” | Es una analogía de Auction Market Theory, no identidad de constructo. Normalmente describe falta de excess en un extremo ya subastado; H-Z2A exige **no acceso** a una zona ex ante. | Puede nombrar patrones visuales, no definir eventos ni aportar prior. |
| “Regla 80 %” como rival cuantitativo | No se verificó una fuente académica primaria ni una definición estable que justifique usar 80 % como tasa base para este setup. | Se elimina del fundamento y del manifiesto; sólo puede quedar como lore de práctica. |
| Densidad de indicadores = pico de profundidad | Kavajecz–Odders-White no autoriza esa igualdad. Confluencia de detectores y profundidad L2 son variables distintas. | La relación se vuelve una prueba de validez empírica, no una premisa. |
| Osler prueba el mecanismo de H-Z2A | Osler observa órdenes de un banco FX y explica reversión/cascada alrededor de niveles; no prueba near-miss→reset→A2 en futuros CME. | Evidencia mecanística transferida; exige replicación por activo. |
| Un efecto en un solo reloj es artefacto | Los relojes definen estimands distintos. Una divergencia puede ser real o un problema de medición. | Resultado “clock-sensitive”: diagnóstico obligatorio, no descarte automático. |
| Cinco relojes independientes | Tiempo, eventos, volumen e intrinsic/directional-change son relojes. Imbalance/run bars son esquemas de muestreo derivados de eventos. | Taxonomía corregida y un reloj primario por estimand. |
| “El motivo ya no existe” observado | Es una causa latente. Separación temporal, volumen transcurrido o una reversa no demuestran recarga de inventarios. | “Reset” pasa a ser etiqueta descriptiva; el mecanismo se adjudica con L2/MBO/GEX auditados. |
| `aVol` sin kernel ni paridad | HP-003 se refería a v0.4. v0.5 tiene kernel Python y evidencia de creación 72/72 en 6E, 119/119 antes del defecto ES y 307/311 después; D-6 le asigna `paridad exacta` para el store. | La frase de v3 queda obsoleta; persisten límites de alcance, datos y outcomes en el EventLog. |

---

## 2. Escalera de evidencia

### Nivel A — fuente primaria y evidencia directa para una pieza

1. **Osler (2000/2003)**: niveles publicados interrumpen tendencias; órdenes take-profit y stop-loss se agrupan de manera distinta cerca de números redondos; después del cruce puede intensificarse la tendencia. Datos FX de un gran banco. No identifica la secuencia H-Z2A completa.
   - https://www.newyorkfed.org/research/staff_reports/sr125.html
2. **Chung & Bellotti (2021, preprint)**: un algoritmo heurístico de soporte/resistencia encuentra probabilidades de rebote mayores tras rebotes previos y decaimiento temporal. Sus zonas se descubren desde extremos móviles y el análisis entra a la zona: no estudia el giro **antes** de acceder ni la segunda aproximación condicional.
   - https://arxiv.org/abs/2101.07410
3. **Xu et al. (2016)**: spread, profundidad e intensidad del LOB muestran resiliencia después de órdenes efectivas; en sus datos vuelven cerca del promedio en ~20 actualizaciones del best limit. Mercado y época diferentes; aporta variables y escalas, no transferibilidad automática.
   - https://arxiv.org/abs/1602.00731
4. **Golez & Jackwerth (2012)**: futuros S&P 500 pueden ser atraídos o repelidos por strikes en días de vencimiento según el mercado de opciones y el tipo de expiración. Es evidencia directa para un caso acotado, no para un régimen GEX diario universal.
   - https://doi.org/10.1016/j.jfineco.2012.06.010
5. **Ni, Pearson & Poteshman (2005)** y literatura posterior: clustering cerca de strikes en expiración y papel de rebalanceos de cobertura. La dirección depende de posiciones compradas/escritas; el OI agregado solo no identifica el signo del dealer.
   - https://doi.org/10.1016/j.jfineco.2004.08.005

### Nivel B — mecanismo o teoría adyacente

- **Kavajecz & Odders-White (2004):** vincula señales técnicas y provisión de liquidez; no equipara confluencia de indicadores con profundidad.
- **Lo & Hall (2015), Large (2007):** resiliencia como recuperación/reposición después de shocks; la reposición puede ser rápida cuando ocurre, pero no es garantizada.
- **Dall’Amico et al. (2018):** la liquidez visible es una fracción de la intención latente; su revelación depende de la distancia y puede retrasarse. Ausencia de profundidad visible no implica ausencia de liquidez.
  - https://arxiv.org/abs/1808.09677
- **Avellaneda & Lipkin (2003):** el pinning requiere, entre otras condiciones, market makers largos de opciones en agregado y OI grande; aun entonces la probabilidad no es uno.
  - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=458020

### Nivel C — ontologías de práctica

Auction Market Theory, *poor highs/lows*, Wyckoff, “liquidity sweeps” y Market Profile sirven para **generar vocabulario o variantes**, no para fijar tasas, mecanismos o decisiones. Cualquier número procedente de práctica debe reconstruirse sobre EdgeLab o retirarse.

### Resultado de la búsqueda exacta

No apareció un paper primario que estime:

`P(acceso/travesía en A2 | near-miss sin acceso en A1, reset, estado actual, zona ex ante)`.

Ésa es precisamente la contribución potencial de H-Z2A. La literatura informa el diseño y las explicaciones rivales; no sustituye el experimento.

---

## 3. Definición del evento sin narración causal

Para una zona `Z=[L,U]` fijada en `available_at_z`, una dirección de aproximación y precios enteros en ticks:

- `d(t) > 0`: precio fuera de la zona, del lado de aproximación.
- `d(t) = 0`: borde cercano.
- `d(t) < 0`: precio dentro o más allá, con otra variable para distinguir interior y borde lejano.
- La distancia se calcula por `zone_id`; nunca por “zona más cercana”.

### A1 — primera aproximación elegible

Comienza al entrar desde `d >= D_far` en el corredor de aproximación. Se conserva la trayectoria completa, no sólo una vela agregada.

### Near-miss

Ocurre sólo si:

1. `1 <= d_min <= δ_nm` ticks;
2. no hubo trade dentro de `[L,U]` antes del giro;
3. después de `d_min`, la distancia aumenta al menos `R_min` ticks antes de cualquier acceso;
4. la zona seguía disponible y no fue invalidada;
5. no hay gap de datos que impida demostrar el orden.

Se publican tres semánticas separadas:

- `trade_near_miss`: ningún trade dentro;
- `quote_near_miss`: ni bid ni ask alcanzan el borde;
- `book_near_miss`: la profundidad elegible no alcanza el borde.

No se mezclan. El estimand primario debe elegir una antes de correr.

### Intervalo post-rechazo

“Reset” se renombra internamente `post_rejection_interval`. Se mide en:

- milisegundos;
- número de trades/eventos;
- volumen transado;
- amplitud máxima de separación;
- cambios de estado observables.

Sólo L2/MBO puede apoyar términos como reposición o agotamiento. Sin esa evidencia, el intervalo no demuestra que “la causa dejó de existir”.

### A2 — segunda aproximación

Es el primer retorno elegible al corredor después del rechazo, con la zona aún activa. El landmark `t2` se fija **antes** de cualquier outcome. Fuerza, spread, volatilidad, flujo y profundidad se calculan sólo con información disponible en `t2`.

### Eventos posteriores, bajo riesgos competitivos

- `ACCESS`: primer trade dentro de la zona;
- `PENETRATION_k`: alcanza `k` ticks desde el borde relevante;
- `REJECT_AGAIN`: nueva separación `R_min` sin acceso;
- `ZONE_INVALIDATED` / `EXPIRED`;
- `OTHER_ZONE_INTERFERENCE`;
- `SESSION_END` / `DATA_GAP`.

No convertir censuras ni riesgos competitivos en “falló” de forma silenciosa.

---

## 4. Árbol de subhipótesis falsables

| ID | Pregunta | Estimand primario | Control decisivo | Qué mata |
|---|---|---|---|---|
| **H-ZVALID** | ¿La zona ex ante altera el path? | diferencia de hazard de acceso vs pseudozona apareada | nulo F1.1 por distancia, ancho, sesión, volatilidad y lado | una familia/config, no todo el core |
| **H-NM** | ¿Hay giros anticipatorios específicamente delante de zonas? | exceso de near-miss por oportunidad elegible | mismos paths alrededor de pseudozonas y niveles desplazados | la variante de zona/δ |
| **H-REVISIT** | ¿Después del near-miss hay revisita elegible? | CIF de A2 antes de expiración/invalidez | rechazos ordinarios apareados sin zona | la etapa “vuelve” |
| **H-A2ACCESS** | Dado que volvió, ¿la historia A1 aporta información sobre acceso? | hazard cause-specific de `ACCESS` desde `t2` | aproximaciones apareadas por **estado actual** sin historia near-miss | el incremento histórico; no H-ZVALID |
| **H-PEN** | Condicional al acceso, ¿hay penetración/aceleración adicional? | CIF `PENETRATION_k`; velocidad/impacto post-acceso | primeros accesos y pseudozonas, mismo estado | la etapa “atraviesa” |
| **H-MECH-L2** | ¿Cambió la oferta de liquidez entre A1 y A2? | diferencias preregistradas de profundidad/OFI/resiliencia | mismo nivel/hora en días apareados | el mecanismo de agotamiento/reposición |
| **H-GEX** | ¿Strikes/opciones modifican la dinámica? | interacción preregistrada con proxy GEX auditado | no expiración, strikes placebo, sign-sensitivity | el modificador GEX, no H-Z2A |
| **H-ECON** | ¿Una regla ejecutable paga costos? | expectativa neta y distribución de drawdowns | fills conservadores + W7 | la variante operable |

### Respuesta a la objeción “no se puede matar rápido”

Correcto: el **core** no se mata con una sola celda de bajo N. Sí se matan rápido variantes concretas por:

- falta de población;
- equivalencia con pseudozonas;
- inestabilidad de definición;
- ausencia de incremento histórico en H-A2ACCESS;
- imposibilidad de ejecución neta.

Cada eje tiene presupuesto de multiplicidad. El censo outcome-free decide qué celdas son testeables; no selecciona ganadores por outcome.

---

## 5. Contrafactuales y sesgos que el diseño debe bloquear

1. **Anticipación/front-running:** el giro antes del borde puede ser reacción a un nivel conocido, no consumo de inventario.
2. **Error de localización:** el “near-miss” puede ser toque real de bid/ask u otra representación de precio.
3. **Ancho elegido después:** mover el borde para acomodar el giro fabrica el fenómeno.
4. **Interferencia de otra zona:** con cobertura 99,31 %, atribuir el path a “la más cercana” es inválido.
5. **Regresión a la media / directional change mecánico:** toda reversa de tamaño `R_min` genera estructuras de retorno aun en nulos.
6. **Selección por supervivencia:** sólo las zonas que sobreviven hasta A2 entran; usar landmarking y riesgos competitivos.
7. **Actividad intradiaria:** velocidad, volumen y profundidad cambian por hora; aparear/normalizar por sesión.
8. **Warmup/roll:** una zona dependiente de perfil histórico cambia con el estado inicial; identidad de warmup en `config_id`.
9. **Liquidez latente:** el L2 visible no agota la oferta total; ausencia visible no prueba “motivo inexistente”.
10. **Noticias y shocks comunes:** registrar calendario o excluir ventanas preregistradas; nunca decidir ex post.

---

## 6. Relojes: estimands distintos, no concurso de confirmación

| Reloj/representación | Rol primario | Interpretación |
|---|---|---|
| **Directional-change** | delimitar aproximación, `d_min` y rechazo `R_min` | reloj nativo de la geometría del evento |
| **Eventos/trades** | hazard desde `t2`, intensidad y OFI | exposición por oportunidad de mercado |
| **Volumen** | cuánto flujo transcurrió entre A1 y A2 | proxy de actividad absorbida, no de causalidad |
| **Calendario** | latencia, riesgo económico y sesión | tiempo que una orden/cuenta permanece expuesta |
| Imbalance/run bars | representación secundaria de fuerza | muestreo adaptativo; no reloj independiente |

Reglas:

- El manifiesto nombra un reloj primario por estimand.
- Los otros son sensibilidad preregistrada.
- Igual signo en varios relojes fortalece transportabilidad, pero no se exige igual magnitud.
- Un resultado sólo presente en uno se etiqueta `CLOCK_SENSITIVE`; se investiga la razón antes de promover o descartar.
- Elegir después el reloj “que dio” queda prohibido.

---

## 7. Reconciliación de paridad: cinco autorizados y un sexto provisional

La aparente contradicción se resuelve separando **versión**, **alcance de evidencia** y **estado de gobernanza**.

### `aVolClusterPOI`

- HP-003 describe **v0.4** como prototipo sin kernel/paridad.
- v0.5 sí tiene `edgelab.bridge`/kernel y evidencia posterior:
  - 6E: 72/72 creaciones del oráculo, `max |Δscore|=0`, con cuatro extras marginales ligados a divergencias de barras;
  - ES: 119/119 exactas antes del defecto del 11-jun y 307/311 después;
  - D-6 decide su entrada al store como `paridad exacta`.
- Por lo tanto, v2/v3 usaron una ficha histórica como si fuera el estado actual. Corrección: **v0.5 no está bloqueada por ausencia de kernel**.
- Límites vigentes: EventLog contiene outcomes; `QualityScore` arbitrario; warmup de primer orden; el uso formal debe ser ciego a outcomes y conservar configuración fija.

### “Cinco” vs “seis”

**D-6 autoriza cinco entradas al store:**

1. BigTrap2 — exacta;
2. aVolClusterPOI v0.5 — exacta por decisión D-6;
3. Gaps2 — representativa;
4. AACloseOpenDiffs — representativa;
5. VolTicksPOC2 — representativa y con limitación de secuenciador.

**HFTZones2 es el sexto que explica el recuerdo:** existen reportes 1.599/1.599 y un artefacto posterior 4.821/4.821 `PASS`. Sin embargo, este último declara árbol sucio y D-6 todavía lo deja “pendiente de paridad NT8 formal”. Así que hoy debe nombrarse:

> **cinco autorizados para store + HFTZones2 con fuerte evidencia de paridad, pendiente de canonización formal**.

No existe un bloque homogéneo de “seis exactos”. `aVolCellPOI2` sigue pendiente.

### Decisión para H-Z2A

- Instrumentación: BigTrap2 fixture.
- Ciencia: aVolClusterPOI v0.5, configuración fija, export target-free.
- Control: Gaps2.
- No barrer resoluciones/params de aVol en esta campaña: eso sí reabriría F9 y otro presupuesto.

---

## 8. Auditoría estática del L2 que Nico ya tiene

Código inspeccionado:

- `tools/convert_l2_to_parquet.py`
- `edgelab/data/l2.py`

El parser actual convierte filas L2/L1 a Parquet, pero **no demuestra paridad del libro**. Hoy:

- parsea timestamps sin zona horaria explícita;
- separa L1 y L2 y no conserva un `source_row/event_seq` común para desempatar igualdad temporal;
- convierte precio `float → round(price/tick_size)` sin gate de residuo;
- no valida enums de `side`, `operation`, base de `level` ni semántica add/update/delete;
- no reconstruye snapshots;
- no verifica orden del libro, `best_bid < best_ask`, niveles únicos ni igualdad L2-top↔L1;
- no registra reset, gap, packet loss, cobertura o checksum por sesión;
- el formato descrito es **Market-by-Price de 10 niveles**, no MBO. No permite inferir posición de cola, identidad de órdenes ni icebergs de forma directa.

### Gates L2 antes del join

1. **L2-M0 · inventario/procedencia:** proveedor, licencia, instrumentos, contratos, sesiones, timezone, hashes raw, tamaños, esquema y rango temporal; detectar holdout y recortar físicamente.
2. **L2-M1 · parser:** `source_row` estable, ticks enteros con residuo cero, enums cerrados, timestamps UTC/CT con DST y monotonicidad por stream.
3. **L2-M2 · replay de libro:** semántica de operaciones, snapshots/reset, niveles ordenados y únicos, no-crossed book salvo estados documentados.
4. **L2-M3 · paridad L1:** top-of-book reconstruido desde L2 coincide con L1; reportar gaps y duración, no sólo porcentaje global.
5. **L2-M4 · alineación con trades:** probar reloj, latencia y orden para distinguir consumo, cancelación y reposición. Si falta trade tape compatible, abstener de atribuir consumo.
6. **L2-M5 · features selladas:** recién aquí profundidad 1/3/5/10, slope, microprice, OFI multinivel, add/cancel imbalance y resiliencia.

### Prueba mecanística H-MECH-L2

Comparar A1 y A2, siempre con controles por hora/volatilidad:

- profundidad del lado opuesto en el corredor;
- porcentaje de profundidad consumida/cancelada;
- tasa de reposición y half-life después del shock;
- intensidad de inserts/cancels;
- OFI y microprice antes de `t2`;
- recuperación del spread;
- estabilidad a 1/3/5/10 niveles.

“Menor profundidad visible en A2” es evidencia compatible con agotamiento, no prueba causal; la liquidez latente sigue siendo explicación rival.

---

## 9. Auditoría estática del GEX existente

Código inspeccionado: `edgelab/gex/reconstruct_daily_gex.py` y documentos GEX.

### Hallazgos bloqueantes

1. **Unidad incorrecta:** el comentario anuncia `OI × gamma × S² × 0,01 × multiplicador`, pero el código calcula sólo `OI × gamma × 100`. `total_net_gex` no está en dólares.
2. **Spot no calculado:** se crea `mid`, pero no se deriva ni usa `S`; el texto “estimate spot” no coincide con la implementación.
3. **Signo de dealer no observado:** call positiva/put negativa es una convención heurística. Open interest no dice qué lado tiene el dealer. Además, “vender una call deja al dealer largo gamma” es matemáticamente falso: una opción vendida es gamma negativa, call o put.
4. **`gamma_flip` no es un zero-gamma dinámico:** suma contribuciones actuales por strike y busca un cruce acumulado; no recalcula gamma/delta para precios spot hipotéticos. Si no hay cruce, sustituye `abs_wall`, mezclando constructos.
5. **Walls por OI:** `call_wall`/`put_wall` son máximos de OI, no de exposición gamma ni flujo dealer.
6. **Vencimientos y 0DTE:** el cálculo no carga columna de expiración ni deja auditar qué expiries integran el agregado.
7. **Mapeo SPY→ES y QQQ→NQ:** falta basis/cost-of-carry, horario, settlement y regla de traducción de strikes a futuros.
8. **Gate M0 insuficiente:** reproducir volumen/OI agregado del boletín CME no valida el historial strike×expiry ni la posición dealer de los parquets SPY/QQQ.
9. **Afirmación temporal excesiva:** la evidencia académica de pinning más directa está concentrada en expiraciones y puede incluir atracción o repulsión; no autoriza un filtro diario universal “+GEX=reversión, −GEX=momentum”.

### Estado corregido

Los parquets actuales deben conservarse, pero renombrarse conceptualmente como:

`CALL_PUT_OI_GAMMA_PROXY_UNVALIDATED`

No “dealer GEX”. No usarlos para elegir variantes ni como zona hasta pasar:

1. **GEX-M0:** procedencia/licencia/schema/hashes; chain strike×expiry; fecha de OI y disponibilidad real ex ante.
2. **GEX-M1:** fórmula y unidades con tests analíticos; multiplicador por producto; spot/future basis.
3. **GEX-M2:** escenarios de signo: dealer long/short por calls/puts, neutral y proxies de participant-side si existen. Reportar sensibilidad, no ocultarla.
4. **GEX-M3:** zero-gamma verdadero recalculando Greeks sobre una grilla de spot, con IV, tasa, dividendos/carry y tiempo a expiry congelados.
5. **GEX-M4:** traducción independiente SPY/SPX/options-on-futures ↔ ES, y QQQ/NDX ↔ NQ.
6. **GEX-M5:** prueba placebo por no-expiración, strikes desplazados y OI bajo; sólo después interacción con H-Z2A.

Para un primer experimento conservador, usar **strikes y OI como generador exógeno** y tratar el signo como desconocido. El efecto GEX se estima por interacción; no se presupone.

---

## 10. Arquitectura y manifiesto que seguirá a v4

```text
edgelab/research/z2a/
  zone_panel.py      distancia por zone_id; trade/quote semantics
  states.py          A1, near_miss, post_rejection_interval, A2
  clocks.py          directional-change, event, volume, calendar
  validity.py        constructo→observable→test
  census.py          población outcome-free por celda
  landmark.py        dataset en t2 + riesgos competitivos
  nulls.py           pseudozonas y paths apareados
  l2_features.py     sólo después de L2-M0…M5
  gex_proxy.py       sólo después de GEX-M0…M5
```

### Orden

1. **Inventario L2/GEX target-free**, sin join y con recorte físico de holdout si corresponde.
2. **Manifiesto H-Z2A numérico**: semántica de precio, `D_far`, `δ_nm`, `R_min`, clocks, matching, risks, tamaños y multiplicidad.
3. **STOP para aprobación de Nico.**
4. Instrumentación sobre BigTrap2 fixture.
5. Censo outcome-free en aVol v0.5 fijo + Gaps2 control.
6. Sólo las celdas con población suficiente pasan a Q-DINÁMICA.
7. L2/GEX entran después de sus gates como mecanismo/modificador, nunca para rescatar ex post un resultado.
8. Economía sólo con W7 completo.

---

## 11. Reparto de trabajo

### Auditor / Notion AI

- Mantener el contrato conceptual, evidencia y matriz de subhipótesis.
- Revisar artefactos producidos localmente y evitar que evidencia se convierta en orden.
- Redactar el manifiesto numérico y reducir la decisión de Nico a aprobar/rechazar.
- Registrar repo + Notion y conservar historial.

### Claude Code en la PC — primera orden, sin outcomes

1. Generar `l2_inventory.json` y `gex_inventory.json` con rutas relativas, hashes, proveedor, schema, instrumentos, contratos/underlyings, fechas, filas, bytes y posible overlap de holdout.
2. Para L2: adjuntar 100 filas raw representativas por tipo de operación, sin datos sensibles innecesarios, y documentar timezone/side/op/level desde la fuente.
3. Para GEX: identificar archivos raw que originaron SPY/QQQ, columnas disponibles (`expiry`, `iv`, `delta`, `gamma`, OI, bid/ask, underlying spot), proveedor y licencia.
4. Ejecutar sólo tests de inventario/estructura. **No correr H-Z2A, GEX stress test, P&L ni cruces.**
5. Commitear artefactos target-free con hashes completos y publicar una entrada de canal; Nico aprueba acciones, no inferencias.

---

## 12. Pendientes mínimos de Nico

1. **W7:** indicar broker/plan o entregar captura/statement. El proyecto calcula el round-turn; Nico no debe reconstruirlo a mano.
2. **L2/GEX:** no hace falta subirlos a Notion. Basta confirmar a Claude las carpetas y la procedencia/proveedor para producir los inventarios locales.
3. **Manifiesto:** no aprobar todavía. La próxima decisión será sobre un artefacto numérico congelado.

---

## 13. Criterio de salida de v4

V4 queda cerrada cuando existen:

- esta enmienda en repo y Notion;
- reconciliación explícita 5+1 de paridad;
- portador definido: BigTrap fixture / aVol ciencia / Gaps2 control;
- afirmaciones de Market Profile y GEX corregidas;
- contratos L2/GEX previos al join;
- árbol de subhipótesis y riesgos competitivos;
- orden local outcome-free y lista mínima de insumos de Nico.

**Resultado:** H-Z2A sigue siendo una buena familia para buscar edges, pero no porque la literatura ya garantice la secuencia. Lo es porque permite separar valor de zona, near-miss, revisita, incremento histórico, penetración, mecanismo y economía; cada pieza tiene un contrafactual y una forma honesta de fallar sin confundir una variante con el core.
