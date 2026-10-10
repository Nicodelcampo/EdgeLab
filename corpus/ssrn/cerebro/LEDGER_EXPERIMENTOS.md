# Ledger de experimentos — CerebroSSRN

El órgano que convierte al cerebro de opinión en terceridad: cada fila es un
ciclo **propuesta (cerebro) → test (ecosistema) → resultado (segundidad) →
lo que el cerebro aprende**. El cerebro relee este archivo antes de proponer,
para no repetir lo ya refutado y para acumular hábito (ley) sobre evidencia.

Formato por entrada: fecha · uso · hipótesis · qué se corrió · resultado ·
veredicto · qué cambia.

---

## EXP-001 — 2026-07-13 · Uso 1 (auditor anti-overfitting)

**Hipótesis a auditar**: el "cluster robusto" del estudio de excursiones del
12-jul (`runs/excursion_study/20260712_201602`) — bucket Predator/any +
`vol_rate` en el decil superior + TP/SL grandes, que sobrevivía IS+OOS — es
edge real y no el más suertudo de una búsqueda masiva.

**Test corrido**: `scripts/deflated_audit.py` (VectorBT). Reusa los kernels de
`brute_excursions` y agrega Deflated Sharpe Ratio (Bailey & López de Prado) +
Benjamini-Hochberg FDR — ambas herramientas nombradas por el corpus (doc6, doc67).
Salida: `runs/deflated_audit/20260713_131702`.

**Resultado (segundidad — el dato empujó de vuelta)**:
- 35.280 combos con muestra suficiente = intentos efectivos.
- Haircut por multiplicidad **SR0 = 0.796** (Sharpe por-trade esperado del
  más suertudo de 35.280 bajo la nula).
- **Mejor Sharpe por-trade observado en TODO el estudio = 0.656 < 0.796.**
- **0 combos** superan Deflated Sharpe > 0.95. Ni uno.
- Cluster robusto (972 combos): 418 tenían OOS>0 (parecían robustos por el
  filtro naïve), pero **DSR máximo = 0.000**. Cero sobreviven DSR o BH-FDR.
- BH-FDR q=0.10: 963 "descubrimientos" IS → 55 con OOS>0 → 0 en el cluster.

**Veredicto**: el "cluster robusto" era **ruido** — supervivencia del más
suertudo de 35.280 pruebas. La coincidencia IS+OOS del reporte previo no
distingue edge de suerte a esa escala de búsqueda. El auditor (método traído
del corpus) contradijo la lectura de superficie del estudio propio. **Primer
acto de terceridad completado: el cerebro tocó la segundidad y ganó posición
de ley.**

**Caveats honestos**: (a) los 35.280 combos NO son independientes (comparten
eventos y filtros solapados), así que N efectivo es menor y SR0 algo alto/duro;
pero el mejor Sharpe (0.656) queda debajo incluso de un haircut más suave, y
los OOS de los tops son negativos — la conclusión aguanta. (b) El split IS/OOS
70/30 cae sobre el roll 06-26→09-26: la degradación mezcla overfit con cambio
de régimen; no se pueden separar con este dataset.

**Qué cambia**:
1. No construir sobre el cluster de zonas Absorb/Predator del rebote genérico.
   Está refutado. (Anotado también en PUENTE_ECOSISTEMA.md.)
2. `deflated_audit.py` pasa a ser paso obligatorio de cualquier corrida futura
   de grilla/Optuna antes de creerle a un combo.
3. La debilidad no prueba que las zonas no sirvan — prueba que ESTE diseño
   (familia rebote, esta grilla, este split) no muestra edge. Próximos usos
   (2 features de order flow, 3 meta-labeling, condicionamiento fuera del roll)
   siguen abiertos, ahora con el auditor de guardia.

---

## EXP-003 — 2026-07-13 · zona como imán (excursión → retorno)

**Pregunta**: ¿qué distancia de excursión E y qué retroceso X% maximizan
P(el precio vuelve a la zona)? Test: `scripts/excursion_return.py` sobre las
7.351 zonas HFT, ventana 8h. Salida: `runs/excursion_return/20260713_134201`.

**Resultado**: la respuesta literal es **degenerada** — para E < ~90 ticks el
precio vuelve a la zona con P≈0.97-1.00 sin importar X (el argmax es E=5-10,
X=80%, P=0.997, pero es casi certeza trivial). El condicionamiento en X aporta
**lift ≈ 0** porque la tasa base ya es ~1. El hallazgo REAL está en la tasa
base por distancia: P(retorno) se mantiene ~1 hasta ~90 ticks, 0.97 en 90-130,
y **cae a 0.475 por encima de 130 ticks (32.5 pts)**. Ahí se rompe el imán.
Señal secundaria: a X bajo (10%) con E moderado-alto (65-90) la P baja a 0.73
— retroceso chico tras excursión grande = mayor chance de runaway al tramo
sin-retorno.

**Veredicto / caveat de terceridad**: P(retorno)≈1 bajo 90 ticks es casi
**tautológico** en un nivel de 1 tick sobre 8h — el precio difundiendo revisita
cualquier nivel cercano casi seguro, sea zona o no. Para afirmar "imán real"
falta el NULL: comparar contra niveles aleatorios a la misma distancia. Si un
nivel random también vuelve ~100% bajo 90t, la zona no tiene edge de imán, es
difusión. **Próximo paso obligatorio antes de creer en el imán: correr ese
null.** Lo útil YA: el riesgo de fade no es "¿vuelve?" (bajo 90t casi siempre)
sino la cola >130t donde la mitad no vuelve — esas son las que funden una
estrategia de reversión ingenua.

---

## EXP-005 — 2026-07-14 · imán en HFT vs close-open (comparación simétrica)

`scripts/magnet_backtest_hft.py` corrió el mismo first-passage+null sobre las
zonas HFT y las comparó head-to-head con los gaps close-open. Salida:
`runs/magnet_backtest_hft/20260714_001344`. **Veredicto: el edge de fade es
ESPECÍFICO de los gaps close-open.** Las zonas HFT dan expectancy neta NEGATIVA
en toda la grilla E=10-80 y son PEORES que su propio null (fadear una zona HFT
es peor que fadear un nivel random). Ejemplo E50 δ32: HFT real −3.17 (null
−0.81, edge −2.35) vs CO real +4.96 (null −0.43, edge +5.39). Consistente con
EXP-001 (las HFT tampoco tenían edge de rebote). **Conclusión: concentrar el
trabajo de order flow / afinado en los gaps close-open; las zonas HFT no son
la fuente de edge para esta familia.** Cerebro reconstruido con 401 papers
(2488 nodos, 3476 aristas, 771 hallazgos) — base más completa para el afinado.

---

## EXP-004 — 2026-07-13 · imán close-open como ENTRADA REAL (first-passage + null + DSR)

**Diseño (informado por el cerebro)**: `scripts/magnet_backtest.py`. Trade =
first-passage (doc "Non-Stationary Model for Stat-Arb"): entrar al fade cuando
el precio llega a E ticks del gap, TP=gap (gana E), SL=E+δ (pierde δ), neto de
costos, peor caso intra-vela. Fuerza bruta E×δ×overlap×diff×dir. Auditado con
Deflated Sharpe + BH-FDR, split IS/OOS, y NULL (misma estrategia sobre niveles
random = close de barras M1 al azar). Salida: `runs/magnet_backtest/20260713_153802`.

**Resultado — tensión productiva**:
- **481/1071 combos con expectancy neta > 0**; los tops muy lindos: exp +23
  ticks, PF 2.7-3.0, win 73%, y **OOS positivo** (+29 a +42 ticks).
- **PERO 0 sobreviven Deflated Sharpe > 0.95** (mejor DSR 0.42; mejor
  Sharpe/trade 0.58 vs haircut SR0=0.591). Ningún combo puntual es "el edge"
  contra la multiplicidad de 1071 pruebas.
- **El NULL es la validación fuerte y PASA**: las zonas reales le ganan a los
  niveles random por **+3 a +5 ticks netos, consistente** en todo el espacio
  de parámetros (real +3/+5 vs null NEGATIVO -0.4/-2.4). El null pierde plata;
  el real la gana. **La ubicación del gap es real, no difusión.**

**Reconciliación**: hay un edge de UBICACIÓN real y modesto (~+5 ticks sobre
random, robusto y OOS-positivo), pero el Sharpe/trade es bajo (~0.5) así que
NINGÚN combo puntual es significativo contra la multiplicidad. El edge vive en
la ROBUSTEZ (many-combos-positivos + gana-al-null + OOS+), no en un combo. El
DSR con N=1071 es demasiado duro (combos dependientes → N efectivo menor), así
que probablemente subestima; el null es el juez más limpio acá y es favorable.

**Estructura predicha por el cerebro, CONFIRMADA**:
- Paradoja del stop (doc 77/103): los stops APRETADOS (δ=8-16) NO aparecen en
  los tops; los ganadores tienen δ=32-48 (moderado-ancho). Cortar la reversión
  con stop chico la mata; el runaway >65t obliga a un stop finito. Óptimo en el
  medio, como decía el corpus.
- Entrada en excursiones GRANDES (E=50-65), no chicas.
- **overlap≥6 (confluencia alta) aparece en TODOS los tops** — sugestivo de que
  el heatmap sí ayuda para el TRADE (distinto de EXP-002 donde no movía el
  P-retorno descriptivo). No establecido (DSR bajo), pero es la pista a seguir.
- Costos NO matan el edge (TP grande: +24 a cost 0, +22 a cost 2).

**Próximo paso**: el edge de ubicación existe pero es ruidoso por-trade. Para
subir el Sharpe/trade sobre el haircut: (1) MÁS DATOS (jun-jul es fino, ~1 mes);
(2) filtro de order flow (Uso 2: OFI/Kyle en el momento de la entrada) para
quedarse solo con los fades de mejor calidad; (3) walk-forward real fuera del
roll. La ubicación ya está validada; falta afilar la señal por-trade.

---

## EXP-002 — 2026-07-13 · segunda fuente de zonas (AACloseOpenDiffs) — CORRIDO

**Datos**: el logger generó `loggers/ES_close_open_zones.csv` (7.271 gaps
close-open, 14-jun→13-jul). Normalización verificada: +3h (el logger hace
ToUniversalTime pero la máquina está en UTC-3 → 93.3% de gaps matchean
open/close exacto de la vela con +3h; escala de precio ya coincide). Velas
hasta 6-jul → 5.614 zonas usadas. Test: `scripts/excursion_return_closeopen.py`
(excursión→retorno + fuerza bruta sobre overlap_at_birth/diff_ticks/direction).
Salida: `runs/excursion_return_closeopen/20260713_140939`.

**Resultado**:
1. **El imán close-open es mucho más TIGHT que el HFT.** Tasa base de retorno:
   ~1.00 hasta 65 ticks, y **cae por un acantilado a 0.165 (65-90), 0.033
   (90-130) y 0.002 (130+)**. Comparar con las zonas HFT (EXP-003): cliff a
   130t cayendo a 0.475. Los micro-gaps son imanes locales fuertes pero SIN
   pull de largo alcance: un gap del que el precio se aleja >65t esencialmente
   no se rellena en 8h (n=472 a 130+, P=0.2%).
2. **`overlap_at_birth` (la confluencia/heatmap — la señal estrella del
   indicador) NO predice el retorno.** A distancia de excursión fija: E=30-45,
   X=50% → ov≥0: 0.923 vs ov≥2: 0.913 (n143/n92). La fuerza bruta sobre los
   parámetros de la zona no encontró lift real: los "top por lift" son
   artefactos de seleccionar excursiones chicas (base más baja en la selección
   filtrada), no edge del overlap. **Hallazgo negativo importante: el rojo del
   heatmap se ve significativo pero no agrega información de gap-fill.**

**Veredicto / caveats**: mismo problema de tautología que EXP-003, agravado —
la banda es de 1 tick (diff mediano=1), así que "volver a tocar" bajo 65t es
casi trivial (difusión). Falta el NULL (niveles random). Además el cliff a 65t
tiene componente de tiempo (excursiones lejanas tardan y comen la ventana de
8h), pero la comparación con HFT es apples-to-apples (mismo MAX_HOLD) y la
diferencia 0.2% vs 47% a 130+ es real. **Lo robusto y accionable: el umbral de
~65 ticks** (estable IS/OOS) — un gap corrido >65t está prácticamente muerto
para fill; inversamente los gaps dentro de 65t son targets de fill confiables
(pendiente confirmar vs null que no sea pura difusión). El overlap se puede
BAJAR de prioridad como feature de fill.

---

## EXP-004b — 2026-07-14 · RE-TEST con 13× datos: el edge de ubicación queda REFUTADO

Se reconstruyeron los gaps desde las velas M1 directamente
(`scripts/build_closeopen_zones.py` → `ES_close_open_zones_M1.csv`, 73.579
gaps dic-31→jul-6, ~13× la muestra del indicador, independiente del chart).
Resultado: (1) en la muestra completa el edge-vs-null cae a ~0 (+0.1/+0.4) y
la expectancy real es negativa; (2) **el +5 de EXP-004 era un ARTEFACTO del
diseño del null**: el null muestreaba niveles de TODA la historia mientras los
gaps reales vivían solo en jun-jul; comparados dentro de la misma ventana,
el null también da +4 (edge real −0.07..−0.36). El gap NO aporta sobre un
nivel aleatorio del mismo período. **LECCIÓN DE MÉTODO (va a CEREBRO_SSRN.md):
el null debe replicar la distribución TEMPORAL de los eventos, no solo su
mecánica.** Lo que sí es real: el fade de extensiones es fuertemente
RÉGIMEN-dependiente (jun/jul muy +, ene/mar/abr −; mensual E50δ32: ene −2.9,
abr −5.1, jun +1.6, jul ++). El objeto de research pasa a ser el RÉGIMEN.

## EXP-009 — 2026-07-14 · hora de sesión — EJECUTADO
`runs/exp009_hour_cut/20260714_003406`. Positivos ruidosos e inconsistentes
IS/OOS salvo 04 ART (apertura europea, + en ambos combos y OOS fuerte, IS
débil). Lo robusto son los NEGATIVOS: 22-03 y 05 ART (Asia ilíquida) pierden
consistente en ambos combos y mitades. Accionable como EXCLUSIÓN horaria.

## EXP-007-lite — 2026-07-14 · gates de régimen simples — EJECUTADO
Gate A (trailing fade-friendliness 5d, embargo 1d) y Gate B (choppiness 5d >
mediana IS), point-in-time. ON>OFF en todas las celdas (dirección correcta,
A&B el mejor: +0.90 vs −1.24 en E50δ32), pero ON_IS negativo en todas: los
gates baratos NO detectan el régimen dentro de IS — la mejora la aporta el
período OOS que ya era favorable. El gate de régimen REAL (HMM sobre
OFI/vol, doc66; EXP-007 full) queda como única hipótesis fuerte abierta, con
expectativas moderadas. EXP-006 (anatomía del gap) queda PAUSADO: su premisa
(que el gap-nivel es especial) murió con el null corregido; sus features
(flujo firmado, burst) se reciclan como candidatos de detección de régimen.

## EXP-007 Fase 1 — 2026-07-14 · HMM diario walk-forward — EJECUTADO Y MATADO

`scripts/exp007_hmm_gate.py` → `runs/exp007_hmm_gate/20260714_004426`.
Pre-registro completo en el docstring (features rv/logchop/gap_rate; estado
bueno = mayor chop en train, elegido por TEORÍA no por PnL; decodificación
filtrada sin lookahead; refit mensual expansivo; combos sonda E50δ32/E65δ24;
3 criterios de éxito). **Fallan los TRES**: (1) abril (peor mes) tuvo gate 70%
ON — no lo apagó; (2) expectancy gateada NEGATIVA (−2.12/−4.06 vs OFF
+0.43/+0.31 — el gate es ANTI-predictivo); (3) t del spread diario con signo
invertido (−1.05/−1.93). Junio ganó en los días que el HMM llamó "malos".
**La hipótesis "régimen choppy diario → fade rentable" queda REFUTADA en
walk-forward.** Observación post-hoc (NO accionable, sería sign-flipping
minado de datos): el signo invertido sugiere que los días de BAJO chop fueron
mejores para el fade — se anota como curiosidad, no como estrategia. Fase 2
(HMM tick-level doc66) NO recibe luz verde. **LA LÍNEA COMPLETA DEL FADE DE
EXTENSIONES SOBRE GAPS QUEDA CERRADA**: sin edge de ubicación (004b), sin
gate barato (007-lite), sin gate HMM diario (007-F1). Activos que sobreviven:
la exclusión horaria 22-03/05 ART (robusta), la infraestructura (magnet_bt,
builder M1, auditor DSR, disciplina de null), y las lecciones de método.

---

## EXP-011 — 2026-07-15 · ZB (T-Bond 30y): reversión + HVN rebote/excursión

`scripts/zb_analysis.py`. Datos: velas M1 ZB (dic-jul) + HVN de
aVolCellPOITick.csv. **Gotcha resuelto**: HVN son SEP26, velas continuas con
roll ~fin-mayo → abr/may con offset −0.5; se restringió a jun-jul alineado
(dif~0, tz offset 0). Protocolo completo: first-passage + costo 1t + DSR +
NULL de calendario + corte mensual + IS/OOS. Salida:
`runs/zb_analysis/20260715_114021`.

Resultados:
- **A) Reversión z-score (estrategia del cerebro, doc 'mean reversion
  strategy')**: 0 combos sobreviven DSR>0.95 en NINGUNA config (lb×k). El mejor
  (lb=30, k=2.5, tp16/sl32) da mensual +0.58/+0.55t (ambos meses +) pero Sharpe
  ~0 y no significativo por multiplicidad. Positivo débil, NO confirmado.
- **B) Rebote en HVN — FALSO EDGE DESMENTIDO.** A primera vista rentable:
  exp +2.8t, PF 1.68, win 51%, 7 descubrimientos BH-FDR. PERO el NULL (mismos
  toques, niveles RANDOM) da IDÉNTICO: exp +2.77t, PF 1.69. **Edge vs null:
  mediana −0.15t, solo 14/36 combos le ganan al azar.** Y mensual +5.5 jun /
  −1.5 jul. Conclusión: rebotear en un nodo de alto volumen NO es mejor que
  rebotear en cualquier nivel — el "edge" es solo "en ZB el precio revierte en
  cualquier lado", no una propiedad del HVN. Caso de manual del null test.
- **C) Excursión→retorno HVN**: P(retorno)~1 bajo 8t, cae a 0.14 (32-48t) y
  **0.00 arriba de 48t** (n=157). Mismo patrón imán/difusión que el ES; cliff
  ~32t. Descriptivo, probablemente difusión (falta null).

Veredicto ZB: ningún edge confirmado. El HVN rebote es el ejemplo perfecto de
por qué el null es obligatorio — PF 1.68 que un backtest ingenuo habría creído.
La reversión z-score merece más datos pero no está probada. Instrumento y
scripts quedan listos (ZB en config, kernel `firstpass` genérico reutilizable).

## EXP-012 — 2026-07-15 · ZB reversión z-score GATEADA POR VOL — el mejor candidato

`scripts/zb_meanrev_volgate.py`. Testea la hipótesis del cerebro (reversión
rinde mejor en alta vol). Régimen point-in-time (rv 2h > mediana trailing 5d).
**La hipótesis se confirma direccional y REPLICA en las 2 configs**:
- lb=30 k=2.5 (tp16/sl24): HIGH-VOL +0.88t vs LOW-VOL −0.17t. Timing z-score
  vs null high-vol: **+1.31t**. Pero OOS −1.16 (falla el split 70/30).
- lb=60 k=2.0 (tp4/sl12): HIGH-VOL +0.46t vs LOW-VOL −0.43t. Timing vs null:
  **+1.28t**. Monthly jun +0.06 / jul +0.78 (ambos +). **IS +0.51 / OOS +0.39
  (AMBOS +).** Primer resultado de toda la saga positivo en null + ambos meses
  + IS/OOS simultáneamente.

**CORRECCIÓN 2026-07-15 (el usuario detectó la sobre-restricción)**: los
resultados de arriba eran de jun-jul SOLO — error mío: restringí a la ventana
de las zonas HVN, pero la reversión z-score SOLO usa velas (serie continua
ajustada por roll, verificada sin gap), así que corresponde la HISTORIA
COMPLETA (~6.5 meses, dic-jul, 148k velas). Re-corrido sobre todo:
- lb=30 k=2.5 (tp24/sl32): HIGH-VOL **+0.05t** vs LOW-VOL −0.30t (era +0.88).
  Mensual MIXTO: ene +0.50, feb −0.57, mar −1.23, abr +0.31, may +0.07, jun
  +1.34, jul +0.23 (3 meses negativos). IS −0.25 / OOS +0.65.
- lb=60 k=2.0 (tp4/sl12): HIGH-VOL **−0.16t** vs LOW-VOL −0.20t (ambos
  negativos ahora). Mensual mayormente negativo. IS −0.20 / OOS −0.08.

**VEREDICTO CORREGIDO: el "mejor candidato" era LUCK DE RÉGIMEN de un tramo
favorable de 6 semanas. Con el año completo la estrategia es break-even a
levemente negativa. Otra línea cerrada.** LO ÚNICO real que sobrevive el año
completo: **el timing del z-score bate a las entradas random en high-vol por
+0.93 a +1.13t, replicado y consistente** — una micro-señal genuina, pero más
chica que el costo + la no-rentabilidad general, así que NO es operable.
Lección de método (a CEREBRO_SSRN.md): **nunca restringir la ventana de una
estrategia a la de un dato accesorio que no usa; correr siempre sobre toda la
historia disponible.** El corte mensual sobre 6 semanas no basta — se necesitan
suficientes EPISODIOS de régimen (acá ~6-7 meses recién muestran el mix real).

## EXP-013 — 2026-07-15 · ZB gaps close-open: falso edge (3er desmentido de gaps)

`scripts/zb_gaps_bt.py`. El usuario logueó 23.578 gaps de AACloseOpenDiffs
(ZB SEP26). Dos hallazgos previos: (a) roll desalinea abr-may (SEP26 vs velas
continuas) → se RECONSTRUYEN desde velas (51.438 gaps, 6.5 meses, sin roll);
(b) **overlap_at_birth y diff_ticks son DEGENERADOS en ZB** (diff=1 tick en
99%, overlap no discrimina) — sin materia prima para "muchos parámetros" como
tenía value migration. Sweep: (overlap, dir) × E × SL, first-passage, costo 1t.
Salida: `runs/zb_gaps_bt/20260715_115619`.

Resultado: **0 combos sobreviven DSR en ningún corte.** El NULL de calendario
lo mata: gaps edge vs niveles random = mediana **−0.17t**, solo 5/36 le ganan
al azar. El "mejor" combo (E32/SL12, exp +2.42t) tiene DSR 0.90 y mensual
CAÓTICO (ene −4.2, feb +5.9, mar −4.3, may −2.9, jul +23.7) — el promedio lo
domina un outlier de julio (régimen favorable reciente, la misma trampa).
**Veredicto: los gaps close-open NO son fuente de edge en ZB tampoco** — igual
que el ES (EXP-004b). Un gap close-open es solo un nivel de precio; fadearlo =
fadear un nivel random. **Tercer desmentido consistente de la familia gaps.**

## EXP-014 / 014b — 2026-07-15 · VOID SWEEP → el PRIMER EDGE REAL (momentum-ruptura)

Concepto #2 del usuario (rechazo forzado en imbalance / void sweep). Void =
Fair Value Gap. Trade de MOMENTUM/RUPTURA (1er concepto no-fade). ES, 6.5 meses.
`scripts/exp014_void_sweep.py` + `exp014b_momentum_isolation.py`.

- EXP-014: el barrido con momentum da exp +1.4t, PF 1.41, **DSR=1.00**, IS+OOS+,
  7/8 meses +. PERO el NULL (voids random) da IDÉNTICO → **el void NO importa**
  (edge vs null ~0). El edge está en la estructura momentum+R:R, no en el void.
- EXP-014b (test decisivo, mismas entradas, distinta dirección): **MOMENTUM
  +1.76t (IS+1.70/OOS+1.87, dsr1.0) vs RANDOM +0.22t vs ANTI −1.59t.** Gradiente
  limpio y SIMÉTRICO → el momentum predice la dirección, confirmado. NO es el
  void, NO son las mecánicas TP/SL. Segundo control: momentum en barras
  PURAMENTE random = −1.09t → tampoco es momentum ambiente; es específicamente
  **momentum en el instante de CRUZAR un nivel (ruptura en curso)** con stop
  ajustado + target lejano (R:R asimétrico ~6:1, win ~28%).

**PRIMER EDGE que sobrevive TODA la batería** (DSR + IS/OOS + mensual + null de
dirección + aislamiento de momentum), tras 13 experimentos donde todos los
FADES murieron. Conclusión de estructura de mercado coherente: el ES intradía
es de CONTINUACIÓN, no de reversión — por eso los fades morían y el momentum
gana. Nota honesta: entrada de ruptura puede tener peor slippage que 1t; ES
~6 meses; validar en vivo/paper y en otros instrumentos. Pero es real, no un
espejismo de calendario ni de mecánicas. Irónicamente salió de un concepto
(void) que quedó DESMENTIDO — el proceso disciplinado encontró el mecanismo
verdadero debajo. Próximo: caracterizar mejor el setup de ruptura (qué define
un buen nivel a romper), probar el exit óptimo, y correr en ZB/otros.

## EXP-015 / 015b — 2026-07-15 · EXPRIMIR el edge: breakout de FUERZA (el squeeze)

Cerebro: time-series momentum (Moskowitz, doc 18) se concentra en MOVIMIENTOS
EXTREMOS; trailing stop por cierre de EMA (doc). Reformulé la entrada como
ruptura de canal DONCHIAN (corpus-backed, cruce de nivel por construcción).
`scripts/exp015_breakout.py` + `exp015b_strength_filter.py`. ES + ZB.

EXP-015 hallazgos:
- Breakout crudo ~0 (exp +0.05..+0.38t) pero **la expectancy crece MONÓTONA con
  la FUERZA de la ruptura** en TODOS los N (ej. N=20: Q1 −2.23 → Q4 +1.16).
  **Moskowitz confirmado: el edge está entero en las rupturas fuertes.**
- Dirección siempre importa: momentum + / anti −0.8..−1.0 (simétrico).
- Trailing EMA (idea del cerebro) NO transfiere a M1 intradía: peor que R:R fijo
  (todas negativas). El R:R asimétrico fijo gana.
- **ZB: todo negativo** (no tiene tendencia intradía suficiente) — es un edge
  del ES. Instrumento-específico.

EXP-015b — el SQUEEZE (filtro de fuerza point-in-time, umbral percentil
expanding, ES Donchian N=40):
- todas +0.23t → **fuerza>P90 +2.16t ($27), IS+1.46 / OOS+4.20, 6/7 meses +,
  anti-dirección −0.79t.** Monótono en el percentil. OOS > IS (NO overfit).

**EDGE CARACTERIZADO Y EXPRIMIDO**: rupturas de momentum FUERTES (decil
superior) en ES intradía, R:R asimétrico fijo (stop ajustado + target lejano),
dirección = la ruptura. Point-in-time, OOS-confirmado, mensual-estable,
dirección-confirmada. Único caveat: DSR 0.75 (no cruza 0.95 estricto por la
selección del combo tp/sl), pero todo lo demás es abrumador (16/20 combos +,
gradiente monótono, IS+OOS+, 6/7 meses, null de dirección −). Falta: slippage
real de ruptura (tp32/sl4 es 8:1, stop muy chico — sensible al fill), validar
en vivo/paper. Es lo más sólido de 15 experimentos. Contraste total: TODOS los
fades murieron, el momentum-FUERTE de continuación en ES es lo que sobrevive.

## EXP-016 — 2026-07-15 · Order flow: L2/volumétrico — qué agrega (y qué no)

El usuario consigue L2/OrderFlow+. Consulta al cerebro: OFI (14 docs) predice
corto plazo PERO necesita TAMAÑOS y su horizonte es segundos; queue/depth
predicen pero son L2 duro (modelar cola = trampa de fills optimistas); doc 265
(futuros de tasa, familia ZB): order book slope/imbalance NO significativos, el
n° de trades domina → L2 aporta poco a bonos. Horizonte L2 (segundos) ≠ nuestro
edge (minutos).

Logger construido: `OrderFlowTickLogger.cs` (OnMarketData, agresor + tamaños
bid/ask, no requiere OrderFlow+, realtime). Para los TAMAÑOS/OFI y (luego) L2.

**Pre-test con data existente**: el FOOTPRINT/DELTA (agresor-signed volume) se
reconstruye ya desde los ticks (last vs bid/ask) — `scripts/es_delta_breakout.py`,
`data/es_delta_m1.parquet`. Testeado sobre la ruptura fuerte del ES: **el delta
NO mejora el edge** (confirma +1.67 vs en-contra +1.78, sin separación). La
ruptura ya captura la presión direccional. **Conclusión: el valor del L2 NO está
en el footprint/delta (redundante), sino en (a) TAMAÑOS para realismo de fill/
slippage —ataca el caveat #1 del edge—, y (b) profundidad para el filtro
fino/grueso del libro.** Correr el logger por los tamaños; L2 para fills. No
sobre-invertir en footprint.

## EXP-017 — 2026-07-15 · Robustez + fuerza vol-normalizada (avance gratis)

`scripts/es_edge_robustness.py`. Dos tests sin L2:
- **Stress de slippage**: el edge decae ~1t por tick de fricción. tp32/sl4:
  +2.16(1t)/+1.16(2t)/+0.16(3t)/−0.84(4t). En ES realista (~1-2t) queda
  +1.16..+2.16. Sobrevive fricción realista pero a mitad de magnitud en el peor
  caso → JUSTIFICA L2 para modelar fills en ES (decide +2.16 vs +1.16), pero
  no es espejismo.
- **FUERZA VOL-NORMALIZADA (mom/ATR) — MEJORA REAL**: vol-norm >P90 = **+3.07t
  ($38), 20/20 combos +, DSR 0.99** (¡primera vez que CRUZA el 0.95 estricto!)
  vs cruda +2.16t, 16/20, DSR 0.75. Y el mejor combo pasa a tp32/sl16 (R:R 2:1,
  stop 16t = menos frágil al slippage). Un breakout X-ticks en régimen calmo es
  "más fuerte" que el mismo en régimen salvaje; la normalización por ATR lo
  captura. **Es el mejor estado del edge**: momentum-ruptura fuerte
  vol-normalizada en ES, R:R 2:1, DSR 0.99, 20/20 combos, OOS+. Falta: fills
  reales (L2 ES) + validación en vivo.

Decisión L2: conseguirlo del **ES no ZB** (edge está en ES; corpus doc 265 dice
que L2 no es significativo en futuros de tasa). L2 histórico en CSV, por los
TAMAÑOS (fill realism) + profundidad (fino/grueso). El footprint/delta ya se
descartó (EXP-016, no ayuda).

## EXP-018 — 2026-07-15 · Inducción Pre-Objetivo (concepto #3) — REFUTADO

`scripts/exp018_inducement.py`. Objetivo = HVN del ES construido desde el VAP
(top-20 del día previo, point-in-time). Setup: aproximación (D) + cercanía sin
tocar (C) + excursión contraria (E, la "inducción") → entrada apostando a que
el precio RETOMA hacia el HVN y lo barre. 5 params del usuario operacionalizados.

Resultado: **todas las celdas E×sl pierden (0% aciertos), IDÉNTICO al null**
(edge vs random = 0.00 en las 20 celdas). El contra-movimiento pre-objetivo NO
es una trampa que se revierte — es momentum que CONTINÚA; apostar a la
reanudación hacia el HVN pierde, y pierde igual en un nivel random (no es del
HVN). Caveat de operacionalización: la entrada cae en el extremo de la excursión
contraria (peor timing, "cuchillo que cae"), pero eso es fiel al concepto. **3er
concepto del usuario refutado por la misma razón estructural: reversión pierde,
momentum continúa.** El único edge sigue siendo el momentum-ruptura fuerte
vol-normalizado (EXP-017). Nota: setups escasos (~95-675 sobre 6.5m).

**EXP-018b (permisivo + bug arreglado)**: con params permisivos (D>=4, C<=20) y
entrada por CONFIRMACIÓN (no en el extremo) — el usuario pidió bien probar más
permisivo. Bug corregido: v1 excluía como setup a TODO nivel tocado en la ventana
(el 71%!) → P(barrido)=0 tautológico. Arreglado (fases: aproximar sin tocar →
contra-excursión → toque = barrido). Resultado: **P(barrido)=0.89 tras la
inducción** (¡parece validar el concepto!) y trade +7.33t DSR 1.00 16/16. PERO
el **NULL de niveles random barre MÁS (0.93)** y también gana (+5.13t DSR 1.00).
El barrido es DIFUSIÓN (tras un contra-movimiento chico el precio vuelve a
cualquier nivel cercano ~90%), no una propiedad del HVN ni de la inducción — el
mismo imán trivial de EXP-002/003. El trade "gana" explotando difusión con stops
chicos (no sobrevive slippage). Contraste clave con EXP-017: ahí el anti-momentum
era simétricamente NEGATIVO (dirección real); acá el null es POSITIVO (solo
mecánica). **Concepto #3 refutado — el null lo revela.** Lección: sin params
permisivos no se ve el 0.89 que parece validar; sin null uno se lo cree.

## PROPUESTAS (cruces estrella, 2026-07-14, cerebro v2 401 papers) — pendientes

**EXP-006 (LA ESTRELLA) — Anatomía del gap: clasificador temporal-vs-permanente.**
Cruce doc96[alta] (la ejecución algorítmica clusteriza al inicio de cada
segundo/minuto; los clusters los originan no-HFTs y los HFT PROVEEN liquidez
ahí) + doc118[alta] (impacto temporal vs permanente separable por OLS simple;
el temporal REVIERTE) + doc66 (OFI ajustado por spread, tick-level) + doc4
(impacto de MOs es temporal si el LOB repone rápido; el flujo persistente es
permanente). Mecanismo: nuestros gaps close-open SON objetos del boundary M1
— exactamente donde disparan las child orders TWAP/VWAP. Hipótesis: gap nacido
de ráfaga de ejecución (alta intensidad de trades vs baseline del reloj, OFI
firmado desalineado con continuación, volumen/tick colapsado) = impacto
TEMPORAL → fade con edge; gap con flujo firmado persistente = impacto
PERMANENTE → es el runaway >65t (el 0.2%-fill de EXP-002). Features al nacer
(computables HOY: es_full_ticks tiene bid/ask → quote rule): OFI ±30s,
trades/seg vs baseline por segundo-del-minuto, volumen por tick, spread medio.
Test: re-correr magnet_backtest condicionado por el clasificador; éxito = el
grupo "temporal" sube Sharpe/trade sobre el haircut DSR y el grupo
"permanente" concentra los runaways. Pliega adentro la P2 y P3 de Gemini
(periodicidad como clasificador, no como estrategia nueva; vacío de liquidez
proxy volumen-por-tick, sin L2).

**EXP-007 — Regime gate.** HMM (doc66; comunidad regime-switching, 8 docs)
para apagar el fade en régimen tendencial. Honesto: hallazgos doc66 robustez
baja (sin OOS/costos). Versión barata primero: vol realizada + |drift| M1
rodante como gate binario; HMM solo si el gate barato muestra señal.

**EXP-008 — Stop dinámico fat-tail.** doc103[alta] (residuos no-normales,
p<1e-16) + doc103[media] (saltos Poisson → stop finito óptimo) + paradoja
empírica EXP-004 (δ=32-48 ganó, δ=8-16 murió). δ escalado por intensidad de
ráfaga local + time-stop por half-life de primer pasaje (vs 8h fijo).

**EXP-009 — Corte por hora de sesión** (intraday seasonality, 8 docs;
time-of-day conditioning). El filtro más barato con soporte replicado.

---

**EXP-006 (LA ESTRELLA) — Anatomía del gap: clasificador temporal-vs-permanente.**
Cruce doc96[alta] (la ejecución algorítmica clusteriza al inicio de cada
segundo/minuto; los clusters los originan no-HFTs y los HFT PROVEEN liquidez
ahí) + doc118[alta] (impacto temporal vs permanente separable por OLS simple;
el temporal REVIERTE) + doc66 (OFI ajustado por spread, tick-level) + doc4
(impacto de MOs es temporal si el LOB repone rápido; el flujo persistente es
permanente). Mecanismo: nuestros gaps close-open SON objetos del boundary M1
— exactamente donde disparan las child orders TWAP/VWAP. Hipótesis: gap nacido
de ráfaga de ejecución (alta intensidad de trades vs baseline del reloj, OFI
firmado desalineado con continuación, volumen/tick colapsado) = impacto
TEMPORAL → fade con edge; gap con flujo firmado persistente = impacto
PERMANENTE → es el runaway >65t (el 0.2%-fill de EXP-002). Features al nacer
(computables HOY: es_full_ticks tiene bid/ask → quote rule): OFI ±30s,
trades/seg vs baseline por segundo-del-minuto, volumen por tick, spread medio.
Test: re-correr magnet_backtest condicionado por el clasificador; éxito = el
grupo "temporal" sube Sharpe/trade sobre el haircut DSR y el grupo
"permanente" concentra los runaways. Pliega adentro la P2 y P3 de Gemini
(periodicidad como clasificador, no como estrategia nueva; vacío de liquidez
proxy volumen-por-tick, sin L2).

**EXP-007 — Regime gate.** HMM (doc66; comunidad regime-switching, 8 docs)
para apagar el fade en régimen tendencial. Honesto: hallazgos doc66 robustez
baja (sin OOS/costos). Versión barata primero: vol realizada + |drift| M1
rodante como gate binario; HMM solo si el gate barato muestra señal.

**EXP-008 — Stop dinámico fat-tail.** doc103[alta] (residuos no-normales,
p<1e-16) + doc103[media] (saltos Poisson → stop finito óptimo) + paradoja
empírica EXP-004 (δ=32-48 ganó, δ=8-16 murió). δ escalado por intensidad de
ráfaga local + time-stop por half-life de primer pasaje (vs 8h fijo).

**EXP-009 — Corte por hora de sesión** (intraday seasonality, 8 docs;
time-of-day conditioning). El filtro más barato con soporte replicado.

**Auditoría de la charla Gemini**

---

## EXP-029 — 2026-07-16 · ES Tick Sweep Fade — SEGUNDO EDGE VALIDADO (TICK-LEVEL)

`scripts/exp029_es_tick_momentum.py` + `scripts/exp031_es_sweep_fade_rth.py`.
Datos: ES_ticks.parquet (148.8M ticks). Hipotesis: ticks consecutivos misma
direccion (sweep) en <=500ms indican agotamiento temporal -> fade.

**Resultados (RTH Sweep >10t/500ms, tp24/sl8):**
- **+3.75t ($47), win=43%, IS=+4.33, OOS=+3.00, DSR=1.00, 14/30 DSR>.95**
- **5/8 meses positivos (62%)**
- **TODAS las horas RTH positivas** (13h-20h UTC, +2.62 a +5.30t)
- ANTIdirection: **-2.15t ($-27), 0/30 combos positivos**
- RTH Sweep >12t/500ms: **+6.29t ($79), win=50%, 26/30 DSR>.95**

**Veredicto**: Edge real, consistente, direccional. Debilidad: concentracion en
marzo (+7.51t) y junio (+5.96t); meses negativos leves (-0.05 a -0.42t). El
Sweep es el edge "workhorse": mas trades, mas consistente mensualmente.

## EXP-030 — 2026-07-16 · ES Tick Impulse Fade — TERCER EDGE VALIDADO (TICK-LEVEL)

**Resultados (RTH Impulse >12t/2s, tp24/sl3):**
- **+10.29t ($129), win=53%, IS=+11.48, OOS=+8.52, DSR=1.00, 21/30 DSR>.95**
- ANTIdirection: **-2.19t ($-27), 0/30 combos positivos**
- RTH Impulse >14t/2s: **+13.30t ($166), win=68%, 24/30 DSR>.95**

**Veredicto**: Edge mas fuerte por trade pero MENOS consistente mensualmente
(2/8 meses, 25%). Solo marzo (+12.18t) y junio (+10.07t) positivos.
Altamente regimen-dependiente. El Impulse es el "sniper": mas edge por trade,
mas selectivo.

NOTA ESTRUCTURAL: Ambos edges son FADE en ES tick-level. Esto CONTRADICE la
tesis M1 previa ("ES es continuacion"). A nivel tick (<=500ms) la microestructura
REVIERTE; a nivel M1 (minutos) CONTINUA. Dos regimenes temporales distintos,
dos edges complementarios. Validado por anti-test en ambos casos.

## EXP-031 — 2026-07-16 · ES Sweep Fade + RTH filter + hourly breakdown

Agrega filtro RTH (13-21 UTC) y corte por hora. Confirma que TODAS las horas
RTH son positivas, el edge no depende de una hora especifica. El filtro RTH
reduce ruido overnight sin degradar el edge.

## EXP-032 — 2026-07-16 · Validacion fill-real (tick bid/ask) del edge M1 de EXP-017

Pregunta del usuario (via Gemini): ¿el edge de EXP-017 (Donchian N=40, fuerza
vol-normalizada >P90) es falso porque se backtestea en velas M1 y no es
replicable con ejecucion real tick-by-tick? `scripts/exp019_tick_fill_validation.py`.

**Diseño**: para las MISMAS señales M1 (mismo bar, direccion, nivel roto),
reconstruir (a) el FILL real = primer tick donde ask(long)/bid(short) cruza el
nivel (simula una stop order real, capta el slippage genuino), y (b) el
first-passage TP/SL tick-a-tick sobre `ES_ticks.parquet` (148.8M ticks,
bid/ask reales), sin la ambiguedad "quien llego primero dentro del minuto"
que tiene el first-passage sobre high/low de vela M1.

**Hallazgo lateral (antes del resultado principal)**: `es_m1_candles.parquet`
tiene DOS huecos de ~10-11 dias en abril 2026 (04-03→04-14, 04-17→04-28) no
documentados en HANDOFF_RESEARCH.md (que solo registraba el hueco de 4 dias
de jun por el roll). Un Donchian de N=40 barras cuyo lookback cruza uno de
estos huecos produce una señal FANTASMA (nivel de hace 10 dias tratado como
"hace 40 minutos"). Se filtraron 86/11857 señales con `lookback > 3*N min`
antes de correr el test limpio. Corregido y documentado en
HANDOFF_RESEARCH.md sec.3. **Todo experimento anterior con features de
ventana rodante en ES M1 cerca de esas fechas debe considerarse con esta
salvedad** (impacto probablemente chico — pocas señales por hueco — pero no
auditado retroactivamente).

**Resultado principal (vol-norm >P90, N=40, n=1038 señales limpias, fill
real logrado en 992/1038=95.6%)**:
- M1 idealizado @cost=0: mejor combo (tp32/sl16) exp=+3.90t, DSR=1.00, 20/20 DSR>.95.
- M1 idealizado @cost=3t: exp=+0.90t, DSR=0.00, 0/20 DSR>.95 (ya fragil, consistente con EXP-017).
- **TICK real (fill+exit reales) @cost=0**: exp=+2.79t, DSR=0.96, solo **5/20** combos DSR>.95 (vs 20/20 en M1).
- **TICK real @cost=0.5t (fee minimo, YA NO necesita costo de slippage — esta en el fill)**:
  exp=+2.29t, **DSR=0.52, 0/20 DSR>.95**.
- Comparacion combo-a-combo: el fill real quita **-0.5 a -2.6 ticks** de expectancy
  respecto al M1 idealizado en TODOS los 20 combos (peor en SL chicos: sl4 pierde
  ~2t, el nivel roto rara vez tiene liquidez exacta ahi).

**CORRECCION (mismo dia, tras regenerar las velas)**: a pedido del usuario,
`es_m1_candles.parquet` fue REGENERADO desde `ES_ticks.parquet` (fuente de
verdad; `scripts/build_es_m1_from_ticks.py`). El archivo viejo (export NT8,
en cuarentena en `data/_deprecated/`) tenia ~20 dias faltantes en abril que
los ticks SI tienen; la serie nueva: 183.218 velas (vs 156.718), dic-30 →
jul-10 (+4 dias), sin huecos falsos (queda un hueco REAL jul-02→jul-08 que
los ticks tampoco tienen, feriado 4-jul + fin de semana). Gotcha nuevo: el
indice debe ser datetime64[ns] (MarketData hace astype(int64)//1e6).

**Resultado FINAL con datos limpios (n=1210 señales, fill real 100%)**:
- El slippage real de la entrada stop es ~CERO: media +0.11t, p50 0, p99 1t.
  Los slippages de +200..+1250t de la primera corrida eran 100% artefactos de
  los huecos del archivo viejo (señales fantasma), NO comportamiento de mercado.
- M1 idealizado @cost=0: +3.77t, DSR=1.00, 20/20.
- **TICK real @cost=0: +2.89t, DSR=0.95, 10/20 combos DSR>.95.**
- **TICK real @cost=0.5t (fee): +2.39t ($30, tp32/sl16), DSR=0.66, 0/20,
  pero 19/20 combos con exp>0 y OOS=+1.11.**
- La degradacion M1→TICK restante (-0.2 a -2.4t) ya NO es slippage de fill:
  es la AMBIGUEDAD INTRABAR del first-passage M1 (con SL grande y TP chico el
  M1 hasta era pesimista: tp8/sl12-16 mejora en tick). Con stops chicos (sl4)
  el M1 regalaba ~2t resolviendo la ambiguedad a favor.

**Veredicto final**: la critica de Gemini era correcta en el mecanismo pero por
la razon equivocada: el fill de la stop order ES replicable (slippage real
~0.1t), lo que inflaba el M1 era (a) señales fantasma por huecos de DATOS
(bug nuestro, corregido) y (b) la ambiguedad intrabar del first-passage.
Estado del edge: **real pero mas chico de lo que decia EXP-017** — con
ejecucion tick-realista queda +2.4..+2.9t por trade (tp32/sl16), 19-20/20
combos positivos, OOS+, pero **DSR 0.66-0.95: NO cruza el liston estricto de
multiplicidad con fee incluido**. Queda como "edge candidato, no confirmado
al maximo rigor". Los edges tick-nativos (EXP-029/030) siguen siendo el
estado del arte. IMPORTANTE: todo experimento M1 previo a 2026-07-16 corrio
sobre la serie con huecos; los veredictos NEGATIVOS no cambian (mas datos no
resucita un null), pero cualquier resultado POSITIVO M1 futuro debe usar la
serie regenerada.

---

## EXP-005 — 2026-07-13 · magnet backtest ZONAS HFT (simetrico a EXP-004)

**Diseno**: identico a EXP-004 pero sobre 7.186 zonas HFT normalizadas
(indicador HFTZonesESPureV22). Features de filtrado: bucket (Absorb/Predator/
Ultra), vol_rate (percentiles 50/75/90), direction. Mismos grids ExD, mismo
null (close de barras M1 al azar), mismo Deflated Sharpe + BH-FDR, split
IS/OOS. Script: scripts/magnet_backtest_hft.py. Salida:
runs/magnet_backtest_hft/.

**Resultado**: NO hay edge de ubicacion en zonas HFT. Expectancy negativa en
42/49 combos sin filtros. Edge vs null mediano = -1.5 (NEGATIVO). CO gana
en 38/49 combos. Unico rescate: dir=1 + vr>=75 tiene senal positiva pero
DSR 0.05-0.11 (no significativo).

**Veredicto**: el edge de iman esta en los GAPS CLOSE-OPEN, no en las zonas
HFT. Las zonas HFT podrian servir como CONFIRMACION (feature secundario),
no como senal primaria de entrada. Proximo paso: OFI filter sobre gaps.

---

## EXP-041 — 2026-07-17 · AUDITORIA DE CAUSALIDAD INTRABAR del edge de momentum ES — **EL EDGE MUERE**

**Hipotesis/motivo**: auditando la sesion Gemini se detecto un bug estructural
que tambien es NUESTRO (EXP-015/017/032): el filtro de fuerza usa
close[i] y atr[i] de la barra de ruptura i, pero el fill de la stop ocurre
DENTRO de esa barra -> al momento del fill el filtro es incomputable
(lookahead intrabar de la DECISION, no del fill). Seleccionar por el cierre de
la barra de entrada = seleccionar trades donde la ruptura ya corrio a favor.

**Test** (scripts/exp041_causal_strength.py, exp041b_limit_retest.py; motor
tick bid/ask de EXP-032, mismas 20 celdas tp/sl, datos limpios):
- BASELINE lookahead (referencia EXP-032): +2.89t @cost0 / +2.39t @0.5t.
- A) CAUSAL stop: filtro (momentum40 y ATR60 hasta i-1, firmado en direccion
  de la ruptura, P90 expanding), stop en el nivel: **+0.82t @0 / +0.32t @0.5
  / -0.18t @1t; OOS NEGATIVO (-0.58 con fee); DSR 0.00-0.07.**
- B) CAUSAL confirmacion: filtro original al cierre de i, MARKET al open de
  i+1: paga +4.48t promedio vs el nivel -> **negativo en 20/20 combos**.
- B') CAUSAL limit-retest: confirma al cierre, LIMIT en el nivel roto (fill
  conservador solo si atraviesa): 96.8% retest pero **-0.69t @cost0, 0/20
  combos positivos** (adverse selection: el retest sobre-representa rupturas
  fallidas).

**Veredicto**: **REFUTADO. El edge de momentum-breakout M1 del ES
(EXP-014b/015/017/032) era en su gran mayoria un artefacto de lookahead
intrabar del filtro de fuerza.** En toda formulacion 100% causal la
expectancy neta con fee es <=+0.3t y OOS negativa. Se retracta el estado
"candidato" de EXP-032. La critica externa (Gemini) tenia razon en la
CONCLUSION aunque por la razon incompleta: el fill si era replicable
(EXP-032); lo irreplicable era la decision del filtro. La tanda de mejoras
de volumen diseñada (normalizacion/buckets horarios/RVOL/NAV/VWAP/volume
clock, ids provisorios EXP-033..038 del diseño) queda SUSPENDIDA por su
propio criterio pre-registrado (no se mejora un baseline muerto); los
diseños quedan archivados por si un edge causal resucita.

**Regla nueva (va a CEREBRO_SSRN.md)**: todo filtro de una entrada intrabar
(stop/limit dentro de la barra i) debe computarse SOLO con datos hasta i-1;
si la señal necesita el cierre de i, el backtest debe pagar el precio de
la confirmacion (market en i+1 o limit con fill conservador). Chequeo
obligatorio en todo experimento nuevo y en la revision de los viejos.

---

## EXP-042 — 2026-07-17 · Auditoria del pipeline NQ + "confluencia" ES×NQ (sesion Gemini) — **REFUTADO**

**Contexto**: la sesion Gemini reporto "+12.12t netos ($60), 455 trades de
elite, DSR 1.00, null +3.45/DSR 0.58, slippage 1.98t" para NQ Donchian40 +
rvol>1.5 & z60>1 + ES del lado del VWAP. Reproduccion exacta as-is:
confirmada (+12.12t, 455, DSR 1.00). Auditoria: scripts/exp042_nq_audit.py.

**Bugs encontrados por inspeccion y cuantificados**:
- B1 CINTA NQ ENVENENADA (merge_nq_ticks.py): 4 contratos trimestrales
  concatenados SIN ajuste de roll y re-ordenados por timestamp; en las
  semanas de roll los archivos se solapan y quedan DOS contratos
  entrelazados tick a tick (475.743 saltos >20pt; 459.952 en dic 11-19;
  ~15.000 en jun 14-18; 40% con ida-y-vuelta inmediata). Spread p50=3t
  (ES limpio: ~1t), slippage medio 2t (ES limpio: 0.11t). Los .txt fuente
  fueron BORRADOS tras el merge: la cinta no es reconstruible sin
  re-exportar de NT8.
- B2 lookahead de fuerza (identico a EXP-041).
- B3 lookahead del filtro de volumen: rvol/z60 del minuto i usan el volumen
  COMPLETO del minuto de entrada.
- B4 lookahead del filtro macro: dist_vwap del ES del MISMO minuto i.
- B5 null debil: permuta el offset del nivel pero conserva direccion del
  momentum y timing — no es "entradas aleatorias" (la direccion ES el
  edge, EXP-014b); por eso su null dio +3.45.

**Descomposicion (mismo motor tick, fee 0.5t)**:
- R0 as-is: +12.12t, n=455, DSR 1.00 (reproducido).
- R2 solo sacando ventanas envenenadas: +11.99t (el veneno directo en SU
  subset era chico: 10 trades; el daño real de B1 es la calidad global de
  spread/fills y los rolls sin ajustar).
- R3/R4 CAUSAL (fuerza i-1, rvol/z60 en i-1, vwap ES en i-1): n colapsa
  455 -> 107, **exp = -1.81t, DSR 0.02**. El +12.12 era LOOKAHEAD casi en
  su totalidad (el "volumen confirmando" era el volumen de la propia barra
  de ruptura, y el aval del ES era el VWAP del minuto aun no cerrado).

**Veredicto**: **REFUTADO integralmente.** Las afirmaciones "codigo blindado,
100% simetrico a NT8, matematicamente auditado y certificado" son falsas:
un bot NT8 no puede conocer close[i]/rvol[i]/vwap[i] al momento del fill
intrabar. La cinta NQ_ticks.parquet queda marcada INUTILIZABLE para
investigacion (usable solo con exclusion de ventanas + re-export limpio por
contrato con back-adjustment). La idea intermercado ES×NQ en si (lead-lag /
confluencia) NO queda refutada como concepto: queda sin evidencia, y solo
puede testearse con cinta NQ limpia y filtros causales.

---

## EXP-043 — 2026-07-17 · EdgeLab: gauntlet nuevo (MCPT/PBO/SPA) + primera tanda de estrategias del informe compass

**Contexto**: proyecto aislado `C:\$AEdgeLab` (plan en su PLAN.md) creado tras
EXP-041/042. Novedades de infraestructura: (a) cinta NQ LIMPIA reconstruida
desde exports por contrato (empalme por volumen, cero solapamiento, offset de
roll jun medido = +311.38 pts, gate: corr diaria NQ~ES 0.951, 348 saltos vs
475.743 de la envenenada; hueco de export mar-20→abr-19 documentado como
frontera; el 12-25 no se exporto: la serie arranca dic-11); (b) gauntlet con
MCPT de Masters (permutacion por-sesion que preserva el retorno open→close
del dia y re-corre el pipeline COMPLETO), PBO/CSCV y SPA (arch), smoke test
PASADO (estrategia random muere: MCPT p=0.37, PBO 0.44, OOS invertido).
Costo pre-registrado 2.5t RT. Config UNICA por estrategia, sin grillas.

**Resultados (gauntlet completo, umbrales pre-registrados)**:
1. **Noise Area ES (Zarattini SSRN 4824172): MUERTA por expectancy**
   (-2.90t/trade, n=146, win 34%). Dato clave: MCPT p=0.002 — la estructura
   de momentum intradia EXISTE (las permutaciones pierden -11.000t vs -424t
   real), pero no paga costos en esta ventana de 6.5 meses.
2. **Noise Area NQ: MUERTA** (-20.2t/trade, MCPT p=0.13).
3. **ORB 5-min ES: MUERTA por MCPT** (p=0.15) — el caso de libro: +36.96t,
   7/8 meses+, OOS +64.8... pero el null (que conserva la deriva diaria)
   gana +2979t: era la DERIVA del semestre. Ningun test previo del
   ecosistema hubiera detectado este falso positivo.
4. **Cruce ES→NQ causal (cierre de la pregunta intermercado)**: acuerdo
   -12.7t vs desacuerdo -45.9t sobre los trades NQ, pero p=0.75 (permutacion
   por mes, n_desacuerdo=25). **SIN informacion condicional.** La "2da
   dimension" queda sin evidencia (no refutada como concepto: sin evidencia
   con datos limpios y filtros causales).
5. **ORB 5-min NQ: SOBREVIVE la tanda** — +249.18t/trade neto (n=111, win
   69%), 8/8 meses positivos, IS +187 / OOS +390, **MCPT p=0.006** (le gana
   al null que ya conserva la deriva diaria). Robusto a costos (spread real
   NQ ~3t: incluso a 6t RT queda +245t).

**Caveats pre-registrados del sobreviviente (NO es edge confirmado)**:
(a) la permutacion intradia construye "opening ranges" artificialmente
angostos en el null (los primeros 5 min reales son las barras mas anchas del
dia) → el p=0.006 esta algo inflado a favor; falta el walk-forward MCPT de
Masters como confirmacion; (b) una sola config en UN regimen (semestre
alcista fuerte del NQ, +25%): sin episodio bajista/rango en muestra; (c)
fills M1 peor-caso pero sin bid/ask real: FALTA la validacion tick contra
nq_ticks_clean (siguiente paso obligatorio); (d) n=111 dias.

**Veredicto**: gauntlet operativo y calibrado (mata random, mata deriva
disfrazada). 4 lineas muertas con causa identificada. 1 candidato (ORB NQ)
pasa a la fase de validacion dura: tick-fills reales + walk-forward MCPT +
esperar regimen distinto o datos viejos para test multi-regimen.

**CORRECCION EXP-043 (mismo dia, 2026-07-17) — EL "SOBREVIVIENTE" ERA UN BUG
NUESTRO. RETRACTADO.** La validacion tick pre-registrada (F6.1) dio -17.12t
vs +235.84t del M1 para las MISMAS entradas/direcciones (183/183 identicas).
El diff trade-a-trade encontro la causa en `strategies/orb.py`: el stop-loss
del SHORT estaba booked con signo invertido — `res=(hi-entry)` en vez de
`(entry-hi)` — convirtiendo CADA perdida de short stopeado en ganancia del
mismo tamaño (ejemplo 2025-08-28: stop de -450t contabilizado +447.5t).
Con el signo corregido, los dos simuladores COINCIDEN:
- **ORB 5-min NQ (10.5 meses, 183 trades): -18.68t/trade M1 / -17.12t tick,
  win 33%, MCPT p=0.58 → MUERTA.**
- **ORB 5-min ES: -13.06t/trade, win 26% → MUERTA** (MCPT p=0.03: pierde
  MENOS que el null — misma historia que Noise Area ES: hay estructura,
  no paga costos).
Resultado neto de la tanda compass: **CERO sobrevivientes** (5 de 5 lineas
muertas, todas con causa identificada).

**Leccion metodologica (va a CEREBRO_SSRN.md como regla 8)**: el MCPT NO
detecta bugs de implementacion — el bug corre igual en la serie real y en
las permutadas (el p=0.002/0.006 del ORB bugueado era GIGO). Lo unico que lo
cazo fue la REPLICACION EN UN SEGUNDO SIMULADOR INDEPENDIENTE (tick vs M1).
Regla: ningun sobreviviente se asienta sin acuerdo entre dos simuladores
independientes (motor distinto, datos de resolucion distinta).

---

## EXP-044 — 2026-07-18 · Capa anti-bugs (motor compartido + harness) y auditoria de EXP-029/030 — **REFUTADOS; la cinta ES tambien esta envenenada en las semanas de roll**

**Infraestructura nueva (pedido del usuario: minimizar la responsabilidad del
LLM analista y los falsos positivos)**:
- `edgelab/engine.py`: motor de ejecucion tick COMPARTIDO — la estrategia
  entrega solo (indice_de_decision, direccion); el motor fuerza entrada al
  tick SIGUIENTE (causalidad por construccion), LONG paga ASK / SHORT vende
  BID, TP exige trade-through, SL dispara por last y llena al bid/ask
  (nunca mejor que el nivel), UNA sola formula de PnL. Las clases de bug de
  EXP-041/043/044 son imposibles de escribir en codigo de estrategia.
- `validation/harness.py` (`full_audit`): preflight mecanico (escenarios
  sinteticos con desenlace conocido, mirror test de precios espejados,
  prefix test anti-lookahead, verificador de ledger con re-derivacion
  independiente y tolerancia ~0) + gauntlet (grid DSR, PBO/CSCV, null
  ANTI-direccion automatico, IS/OOS, corte mensual). Veredictos PASS/FAIL
  con diagnostico exacto: cero interpretacion requerida.
- `CONTRATO_LLM.md`: contrato para cualquier LLM/humano — implementa SOLO la
  funcion de señal; prohibido reimplementar fills/PnL; el harness decide.

**Hallazgo de datos (grave): `ES_ticks.parquet` esta ENVENENADO en las
semanas de roll** — mismo mecanismo que el NQ viejo: dos contratos
entrelazados tick a tick (~55 pts aparte, mismo milisegundo; verificado
2026-03-20 07:00:05 last oscilando 6596↔6651). 1.16M saltos >5pt
concentrados en mar-15..20 (~680k) y jun-11..15 (~478k). Ventanas
declaradas en `edgelab/config.py::ES_POISON_WINDOWS` con filtro mecanico
`poison_mask()`. ERRATA de alcance: toda señal tick-level de esas semanas es
artefactual, y las velas M1 regeneradas heredan rangos inflados ahi (el
veredicto negativo de EXP-041 no cambia; los positivos tick SI).

**Auditoria EXP-029/030 (params y headline del ledger, sin re-tunear)**:
- Preflight: APROBADO 4/4 en ambas (espejo exacto, sin lookahead, ledger
  re-derivado OK) -> los numeros que siguen son creibles.
- Con motor real y dias limpios: **SWEEP -1.23t/trade (n=13.615, 0/30 combos
  positivos), IMPULSE -2.99t (n=3.224, win 6%, 0/30)**. El ANTI tambien
  pierde (-1.76/-1.42): a escala tick el spread se come TODA direccion.
- FORENSE (replica de la convencion vieja: fill al last del propio tick de
  señal, sin spread, stop teletransportado, cost 1t):
  * IMPULSE: total +6.07t, pero DENTRO de las ventanas envenenadas
    **+13.77t/trade × 2.967 trades = +40.863t** vs FUERA **-1.01t**
    (aporte -3.258t). El 48% de las señales y el 100%+ del PnL del "edge"
    era fadear oscilaciones fantasma entre dos contratos.
  * SWEEP: dentro +0.29t, fuera -1.46t. El +3.75t del ledger requeria ademas
    la entrada EN el mismo tick de la señal (capturar el print ya visto =
    lookahead de reaccion) — irrealizable.

**Veredicto**: **EXP-029/030/031 REFUTADOS integralmente.** Sus ganancias
eran (a) veneno de roll (impulse: totalidad), (b) entrada en el print ya
observado, (c) stop teletransportado, (d) fill sin spread. La familia "fade
tick-level en ES" queda CERRADA con datos actuales. Con esto, NINGUN edge
del ecosistema viejo sigue vivo. Accion pendiente de datos: re-exportar ES
por contrato (como se hizo con NQ) para tener cinta tick sana tambien en
las semanas de roll.

---

## EXP-045 — 2026-09-01 · Calibracion de HFTZonesNQImpulseV2_5 y NO-transferibilidad de umbrales entre instrumentos

**Problema**: el indicador saturaba el chart de NQ (pared de zonas). Diagnostico
visual: todas las zonas en azul acero = `ColorTimingUnresolved` -> en data
historica el timing no es confiable, con `TimingPolicy=CausalQualityAware` la
compuerta fisica se AUTO-DESACTIVA (`timingGateApplied=false` => `physicalGate=true`)
y quedan solo las compuertas estructurales, que estaban muy laxas.

**Medicion** (replica offline de StepEngine/FinalizeStreak en modo FailureCount,
`$AEdgeLab/tools/calibrar_hftzones.py`, 4 dias de cinta real por instrumento):
- NQ con defaults viejos: **380 zonas/h**. ES: 147 zonas/h.
- Causa: en NQ el |delta| mediano por print es 2 ticks -> `MinSweepTicks=4` se
  alcanza con 2 prints; `MinNetDisplacementTicks=2` = un solo cambio de precio;
  `MinDirectionalEfficiency=0.10` admite camino 10x el neto; `MinVolumeSurprise=0.50`
  deja pasar volumen POR DEBAJO del baseline. Ademas la familia AbsorbProxy
  (`DetectAbsorb=true`) SALTEA las compuertas de displacement y efficiency
  (~60 zonas/h de baja evidencia; el propio header la declara "descriptive
  proxy, not L2 truth").

**Defaults nuevos NQ (v2.5.1, aplicados)**: MinPasos 8->12, MinSweepTicks 4->8,
MinNetDisplacementTicks 2->4, MinDirectionalEfficiency 0.10->0.35,
MinVolumeSurprise 0.50->1.20, DetectAbsorb true->false, MaxAgeBars 50000->4000,
MaxZonesDrawn 5000->400. Medido: **20.0 zonas/h (19x menos)**. NO se tocaron
`FallosTolerados`/`RetroFloorTicks`/`RetroPctHeight`/`SegmentationMode`: definen
la SEGMENTACION y por lo tanto los `event_id` (romperia comparabilidad con
exports previos). El universo exportado sigue completo (`ResearchUniverse`);
lo que cambia es el flag `pass` y lo que se dibuja.

**Hallazgo transversal — los umbrales NO son portables entre instrumentos**
(medido, no supuesto):

| feature del segmento | NQ | ES |
|---|---|---|
| \|delta\| por print (mediana, cuando cambia) | 2 t | 1 t |
| prints sin cambio de precio | 61% | 88% |
| altura p50 / p90 | 5 / 13 t | 3 / 7 t |
| validSteps p50 / p90 | 3 / 13 | **77 / 371** |
| dirEfficiency p50 / p90 | -0.33 / 0.45 | **-0.11 / 0.11** |

`validSteps` difiere **25x** y `dirEfficiency` p90 **4x**. Mecanismo: `valid`
cuenta los prints PLANOS como validos; ES tiene 88% de prints planos (libro
profundo, muchos trades al mismo precio) y se mueve de a 1 tick, asi que
acumula rachas larguisimas sin desplazarse. Copiar los numeros de NQ a ES da
0.4 zonas/h; copiar los de ES a NQ da la pared. **Lo unico portable es el
OBJETIVO** (~20 zonas/h) con cada umbral en el percentil equivalente de la
distribucion PROPIA del instrumento — y el percentil comun tampoco coincide
(NQ P89 vs ES P49) porque las compuertas estan correlacionadas de forma
distinta en cada mercado.

**Config equivalente medida para ES** (~20.7 zonas/h): MinSweepTicks=3,
MinPasos=76, MinNetDisplacementTicks=2, MinDirectionalEfficiency=-0.11,
MinVolumeSurprise=1.15, DetectAbsorb=false, EnforceNQInstrument=false.
**GC: sin datos** — requiere export de ticks y correr la herramienta.

**Ampliacion EXP-045 (2026-09-01) — version ES separada + la compuerta que
faltaba**. Se creo `HFTZonesESImpulseV2_5.cs` (enums globales renombrados
HNQI25->HESI25, clase y guarda de instrumento ES/MES). Verificado con csc de
Roslyn contra las DLLs de NT8: compilando AMBOS archivos juntos solo aparecen
los 8 CS0103 de `indicator` de la region generada (4 por archivo, identicos al
original) y CERO CS0101 -> conviven sin colision.

**Hallazgo (feedback del usuario: "marca cualquier zona aunque no sea HFT")**:
con umbrales calibrados solo por ESTRUCTURA, los segmentos que pasaban en ES
duraban **mediana 17 s, p90 2 min, maximo 22 min** — no son eventos HFT. Causa
raiz: `TimingPolicy=CausalQualityAware` + timing no confiable => `physicalGate`
NO se aplica, y la velocidad (lo unico que define "HFT") nunca filtra.

**Por que el timing no es confiable en ES**: el **87% de los ticks consecutivos
comparten el mismo milisegundo**. Los cuantiles de intervalo colapsan al piso
(`effMaxAvgMs = 1.0 ms`), asi que la calibracion adaptativa de velocidad es
inservible sobre esta cinta. El intervalo MEDIO mide cuantizacion del
timestamp, no velocidad de mercado; la DURACION del segmento (inicio->fin) si
es robusta a esa cuantizacion.

**Config ES-HFT final (medida)**: `AdaptiveMode=false` +
`TimingPolicy=LegacyAlwaysFilter` (para que la compuerta fisica aplique
siempre) + `ManualMaxTotalMs=5000` como compuerta HFT real,
`ManualMaxAvgMs=200` laxo a proposito (no debe ser el que filtra),
`ManualMaxPausaMs=1500`, `ManualMinVolRate=50`, `ManualMinTotalVol=8`
(ademas fija `baselineMedianVol=ManualMinTotalVol/MinPasos=1.0`, el volumen
mediano REAL por tick del ES; con 1.5 el `volumeSurprise` era inalcanzable y
daban 0.3 zonas/h), `MinPasos=8`, `MinSweepTicks=4`,
`MinDirectionalEfficiency=0.0`, `MinVolumeSurprise=1.15`.
Resultado: **4.7 zonas/h, duracion p50 2.0 s, altura p50 7 t, 160 contratos/s**
(antes: 20.7 zonas/h con duracion p50 17 s).

**Techo estructural del ES**: aun relajando el cap a 20 s el maximo alcanzable
son ~13 zonas/h. Los bursts direccionales genuinamente rapidos son RAROS en ES
(libro profundo, movimientos de 1 tick, 88% de prints planos). No es un
defecto de calibracion: es la microestructura. En NQ el mismo indicador da
20 zonas/h sin necesidad de la compuerta de duracion.
