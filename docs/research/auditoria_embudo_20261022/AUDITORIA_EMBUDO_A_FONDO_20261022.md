# Auditoría a fondo del embudo y de la regla de decisión del autopilot (2026-10-22)

- **Pedido de Nico (2026-10-22):** auditar, arreglar y mejorar el embudo para que sea realista al promover o no un edge; permitir
  probar masivamente sin caer en sobreajuste, pero sin exigir tanto que se descarten propuestas que podrían funcionar; costos
  canónicos y unificados; que lo integre el sistema autónomo del Debian sin chocar con él.
- **Estado:** `IMPLEMENTADO_Y_PROBADO` (código + tests). La regla nueva del autopilot está **apagada por defecto**: se enciende con una
  línea de configuración en el Debian (§6). Nada de esto otorga estados G; el contrato G0–G5 no se tocó (la enmienda propuesta está en §7).
- **Archivos protegidos del autopilot:** ninguno modificado (`fdr.py`, `guard.py`, `spec.py`, `mandate.*`, `MANDATO.md` intactos; sus blobs
  coinciden con `config/autopilot/protected.json`).
- Continúa a `docs/research/AUDITORIA_EMBUDO_Y_SPRINT_20261020_22.md` (qué se probó en el sprint y por qué no pasó por el embudo).

## 1. Qué se auditó

| Pieza | Dónde | Rol |
|---|---|---|
| Playbook EF0–EF5 | `docs/research_funnel_playbook.md` | orden y prácticas (prosa) |
| Runner E1–E4 | `edgelab/funnel/` | matrices señal × (SL, TP) en D0/D1, nulo de máximo, meseta, contador |
| Contrato G0–G5 | `docs/edge_validation_contract.md`, `edgelab/research/g2*.py`, `promotion.py` | gates de promoción |
| Regla del ciclo autónomo | `edgelab/autopilot/` (`analyze`, `fdr`, `evidence`, `holdout_apertura`, `daemon`) | qué cuenta como acierto, alfa, apertura del holdout |
| Costos | ~20 tablas en `tools/`, `edgelab/autopilot/friccion.py`, `edgelab/research/costs.py` | fricción |

Además se leyeron los papers pertinentes del corpus propio (`corpus/ssrn`) y literatura externa (§9).

## 2. Hallazgos

| # | Gravedad | Hallazgo | Evidencia | Estado |
|---|---|---|---|---|
| H1 | **crítica** | **El autopilot quedó sin capacidad de descubrir.** Alpha-investing (w0 = payout = 0,05, f = 0,5): la riqueza bajó a **0,0025** tras 8 campañas. Cada campaña nueva se prueba con Holm a ~0,0013 repartido entre todas sus pruebas. | `docs/research/autopilot_runs/alpha.json` (copia del 15-oct) | resuelto con interruptor (§6) |
| H2 | **crítica** | **La regla de decisión exige demasiado en la etapa equivocada.** Holm (error familiar) se aplica a TODAS las pruebas planeadas, incluido el descubrimiento masivo. En la simulación con verdad conocida confirma el **2,4 %** de los edges reales moderados. Es el error de tipo II que describe Harris (2016): corregir de más sin potencia mata estrategias reales. | §5, `SIMULACION_POTENCIA.json` | resuelto (§4) |
| H3 | alta | **El runner cobraba 0,5 ticks a todo activo.** El kernel tiene `fees=.5` por defecto y el runner no lo pasaba. La fricción medida es 3,5–7,9 ticks. | `edgelab/funnel/screen.py`, `runner.py` | resuelto: costo obligatorio y registrado |
| H4 | alta | **El stop no modelaba el hueco** (contrato G0.4: «peor entre stop y open siguiente»). Un stop atravesado por un gap se anotaba a −SL exacto. | kernel CPU y GPU, oráculo | resuelto: kernel `v2_gap_stop_mtm_timeout` |
| H5 | alta | **La salida por tiempo valía 0** (−fees), sin importar dónde estuviera el precio. | ídem | resuelto: se valora al open siguiente al horizonte |
| H6 | alta | **~20 tablas de costos que no coinciden.** Para NQ van de 0,9 a 6,18 ticks por viaje. La campaña LUX-IMB usó 0,725 pts por viaje y la canónica es 1,545 pts. ORB0100 «NQ» usó la comisión de MNQ. `edgelab/research/costs.py` aplica a NQ/ES la comisión de 6E. | `grep COMM/COST tools/` | resuelto: fuente única `edgelab/costos.py` (§3) |
| H7 | alta | **El runner no cubre estudios de evento ni reglas con su propio simulador**, que es todo lo que se investigó en la práctica. | auditoría del 20-22/10 | resuelto: `edgelab/funnel/escalera.py` |
| H8 | alta | **Dos salidas, no tres.** Un nulo sin potencia se leía como muerte. No había un estado «viva, falta muestra» con el número de operaciones necesario. | M11, ATJ-18 | resuelto: `SIN_POTENCIA` con N necesario |
| H9 | media | **G4 asume una sola mirada**, pero los datos sellados llegan por semana y se miran cada vez (LUX-IMB, n = 14). Con p-valores clásicos, mirar repetido infla el error. | `CANDIDATO_HOLDOUT_REGLA_VISOR_NQ_20261021.md` | resuelto en código (e-procesos); enmienda propuesta §7 |
| H10 | media | **La apertura del holdout del autopilot sólo pide un hallazgo estadístico auditado.** El contrato pone G4 después de G3 (económico) y nadie verificaba potencia: se puede gastar la única apertura con un efecto que esa muestra no puede ver. | `holdout_apertura.py` | resuelto con interruptor (§6) |
| H11 | media | **Fechas de holdout distintas según el documento**: el contrato G4 dice 2026-07-01 → 2026-12-31; el autopilot y HOLDOUT-A3 (ES/NQ) dicen 2026-10-01. | `edge_validation_contract.md` §G4 vs `edgelab/autopilot/__init__.py` | pendiente: decisión de Nico, va al barrido de discrepancias |
| H12 | media | **El nulo de dirección aleatoria del runner le acredita la deriva** a señales con sesgo de dirección (largos en NQ alcista). El nulo que conserva la exposición (`schedule_nulls.exposure_preserving_direction_null`) existe pero el runner no lo usa. | `runner.run_e4` | pendiente (documentado) |
| H13 | baja | El DSR usa la varianza del estimador de un solo Sharpe como varianza entre pruebas; con pruebas muy correlacionadas exagera el recorte. | `g2.deflated_sharpe` | documentado; la escalera usa `n_efectivo` (Li-Ji) cuando hay matriz |
| H14 | baja | Tres tests del autopilot fallan en Windows también en el HEAD sin cambios (lock `fcntl`, git). No pasa en el Debian. | corrida comparada | va al barrido |
| H15 | baja | Los archivos protegidos tienen CRLF en la copia de trabajo de Windows: `check_protected` falla acá aunque los blobs estén bien. | §6 | va al barrido (`.gitattributes eol=lf` para protegidos) |

## 3. Costos canónicos (pedido de Nico)

- **Datos:** `config/costos/costos_canonicos.json`, citado a `REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md`. Tiene tick, valor del
  tick, comisión ida y vuelta por firma, spread medido (atlas v4) y escenarios de slippage del contrato G3.
- **Acceso:** `edgelab/costos.py`:
  - `friccion_rt_ticks(inst, escenario, incluye_spread, criterio)`;
  - `friccion_rt_puntos`, `friccion_rt_usd` y `desglose` (para citar el costo en un manifiesto).
- **Reglas:**
  - la comisión de decisión es la **máxima** entre las firmas que admiten algoritmos;
  - un instrumento sin un componente medido **falla cerrado** (`CostoNoMedido`). Pasa hoy con ZB, 6B y 6J (sin spread medido) y con EURUSD spot.
- **Compatibilidad:** `autopilot/friccion.py` ahora deriva de la fuente canónica con **los mismos valores** (ES 3,55 · MES 4,62 ·
  6E 4,16 · NQ 6,18 · GC 6,05 · MNQ 7,91; test `tests/test_costos_canonicos.py`). El ciclo no cambia de comportamiento.
- **Legado:** las tablas locales de `tools/` y `edgelab/research/costs.py` se dejan como están, porque reproducen campañas ya publicadas (CAMP-001 tiene golden
  tests). Toda campaña nueva cita `edgelab.costos`. Migrar o marcar las viejas va al barrido de discrepancias.

## 4. Diseño nuevo: probar mucho sin sobreajustar y sin matar lo que puede funcionar

La literatura y la simulación coinciden: **lo que protege del sobreajuste es la réplica en datos no mirados**, no exigir error familiar
sobre el descubrimiento. Exigirlo ahí sólo destruye potencia. Es el diseño descubrimiento → réplica de la genómica, que Harvey, Liu y Zhu
(2016) trasladan a finanzas. Tres niveles (`edgelab/funnel/escalera.py`, `secuencial.py`):

1. **Tamiz masivo, descubrimiento.**
   - Regla: FDR de Benjamini-Hochberg, o de Storey (adaptativo, más potente cuando hay muchos efectos reales), a q = 0,10 dentro de la campaña.
   - Lo que controla: la *fracción* de nominaciones falsas, no la chance de una sola. Por eso escala a miles de pruebas.
   - Nominar **no afirma nada**: da derecho a gastar una réplica.
   - Todo lo probado va al contador global, y el recorte por selección lo cobra después.
2. **Confirmación, réplica no mirada.**
   - Pocas pruebas: hasta 3 por campaña.
   - Cada una al nivel que le asigna **LORD++**: FDR en línea sobre toda la historia del proyecto (Javanmard y Montanari 2018; Ramdas et al. 2017).
   - A diferencia del alpha-investing, no se agota tras una racha sin hallazgos. La secuencia de niveles por defecto (`finita`, j^-1,6) está pensada para decenas o cientos de confirmaciones, no miles.
   - La réplica, el holdout y el paper se siguen con **e-procesos**, válidos aunque se mire cada semana: si bajo la hipótesis nula una cantidad tiene esperanza ≤ 1, la chance de que alguna vez llegue a 1/α es ≤ α (desigualdad de Ville).
3. **Tres salidas, no dos.**
   - `REFUTADA`: la cota *optimista* no llega al efecto útil.
   - `SIN_POTENCIA`: sigue viva, y el informe dice cuántas operaciones faltan.
   - Confirmada, que sube a `LISTA_PARA_HOLDOUT` sólo si además:
     - pasa lo económico con costos canónicos: neto base, sin las 5 mejores, ningún período > 80 %, sin colapso en escenario adverso;
     - **hay potencia** para ver el efecto *recortado* con las operaciones que dará el holdout.

     El recorte es el de Harvey-Liu sobre N_eff, en t agrupado por sesión.

El monitor secuencial también tiene **futilidad**: demuestra con evidencia que el efecto es menor que lo útil. Así una candidata muere por
un dato, no por cansancio.

## 5. Simulación con verdad conocida

`tools/embudo_simulacion_potencia.py`:
- 200 repeticiones de 60 campañas × 100 pruebas;
- el 3 % de las pruebas son edges reales;
- las 3 mejores de cada campaña van a réplica.

Resultado en `SIMULACION_POTENCIA.json`.

| Escenario | Diseño | Edges reales confirmados | Falsos por corrida | FDR |
|---|---|---|---|---|
| Sólo ruido | vigente | — | 0,005 | 0,5 % |
| Sólo ruido | **propuesto** | — | 0,025 | 2 % |
| Sólo ruido | sin corrección (script suelto) | — | **9,1** | **100 %** |
| Moderado (z 3,0 / 2,5) | vigente | **2,4 %** | 0,01 | 0,06 % |
| Moderado | vigente sin agotar el alfa | 10,3 % | 0,005 | 0,02 % |
| Moderado | **propuesto** | **35,6 %** | 0,37 | 0,55 % |
| Moderado | sin corrección | 52 % | 3,1 | 3,2 % |
| Fuerte (3,5 / 3,0) | vigente | 24,7 % | 0,035 | 0,06 % |
| Fuerte | **propuesto** | **56 %** | 0,39 | 0,38 % |
| Débil (2,5 / 2,0) | vigente | 0,3 % | 0 | 0 % |
| Débil | **propuesto** | **10 %** | 0,14 | 0,53 % |

Cómo leer la tabla:
- **El diseño propuesto confirma entre 2 y 37 veces más edges reales** que el vigente, con un FDR muy por debajo del 5 % que promete.
- El script suelto «encuentra» más, pero con ruido puro confirma 9 falsos por corrida. Es el modo de falla del sprint del 20-22/10.

## 6. Integración con el autopilot del Debian (sin chocar)

- **Interruptor:** `"decision": "escalera_v1"` en `/etc/edgelab/autopilot.json`. Opcional: `"escalera": {"alfa": 0.05, "q": 0.10}`. Sin la clave, el ciclo es idéntico al de hoy (tests de `tests/test_autopilot.py`).
- **Con el interruptor encendido** (`edgelab/autopilot/confirmacion.py`, `daemon.py`):
  - no se apuesta alfa ni se bloquea por riqueza agotada;
  - `fdr.py` y `alpha.json` quedan intactos: las corridas abiertas con alpha-investing se siguen liquidando con su regla;
  - el registro global de pruebas **antes de lanzar** no cambia;
  - al cerrar:
    - descubrimiento → tamiz FDR → **nominadas**, que abren pistas `WEAK_LEAD` en la evidencia viva;
    - réplica (`/rep/`) → LORD++ → **confirmadas**; acierto = al menos una réplica confirmada, como hoy;
  - la decisión es idempotente por `run_id` (`confirmaciones_lordpp.json` en el directorio de estado); reintentar no gasta otra posición de la secuencia;
  - la apertura del holdout exige además que el resultado del candidato traiga `escalera.estado == "LISTA_PARA_HOLDOUT"`. Es fail-closed: sin veredicto no se gasta la única apertura;
  - `status()` informa `decision` y `lord_nivel_siguiente`.
- **Los estudios lanzados por el autopilot emiten su resultado así:**
  - `escalera.para_autopilot(pruebas)`, el formato `results_flat` que `analyze.records` ya lee;
  - más `escalera.evaluar(...).to_dict()` bajo la clave `escalera` cuando el estudio tiene P&L por operación.
- **Tests:** `tests/test_autopilot_escalera.py` cubre:
  - un ciclo completo con el `alpha.json` real agotado, que igual confirma;
  - la idempotencia;
  - que sólo descubrimiento no es acierto;
  - que la apertura del holdout queda bloqueada sin veredicto.
- **Para encenderlo en el Debian:** actualizar el clon de código, agregar la clave y reiniciar el timer. No hay que refrescar el
  manifiesto de protegidos, porque ninguno cambió. Se recomienda pasar primero por `mode: propose` un ciclo, para ver `status()`.

## 7. Enmienda propuesta al contrato (NO aplicada; la firma es de Nico)

`G4-A1` (borrador): en el holdout, la regla PASS/FAIL de una sola mirada se reemplaza por el monitor secuencial con cotas declaradas
antes de abrir:
- **PASS:** e-valor de edge ≥ 20 (α = 0,05) **y** neto > 0 con n ≥ 30;
- **FAIL:** e-valor de futilidad ≥ 10 frente al 50 % de la expectativa de desarrollo, o neto ≤ 0 al llegar al n planeado;
- **mientras no cruce ninguno:** `SIN_DECIDIR`, y se siguen sumando datos sellados.

Mirar cada semana deja de ser una violación. Sigue prohibido reoptimizar.

## 8. Los dos candidatos reales con la escalera (`ESCALERA_CANDIDATOS_REALES.json`)

Primero se verificó que se reproducen exactamente los números publicados:
- LUX-IMB: 6 de 6 períodos, n y puntos;
- ORB: la réplica, n = 92 y +6,846 pts.

Después se cobró la fricción canónica de NQ (1,545 pts por viaje).

| Candidato | Neto canónico | Inferencia | Recorte por selección | Estado | Siguiente paso |
|---|---|---|---|---|---|
| LUX-IMB, regla del visor (NQ, 500 op., 212 sesiones) | **+4,05 pts/op (+0,20 R)**; la campaña había informado +4,92 con 0,725 pts de costo | IC 90 % [+0,01, +0,38] R; p = 0,036; t = 1,8 | 46 pruebas en su familia (98 en todo LUX-IMB): efecto esperado tras selección ≈ 0; DSR 0,33 | **SIN_POTENCIA** | sigue viva; ~950 operaciones para distinguirla del cero |
| Mirada al holdout (14 op., ya consumida) | −1,08 R/op | e-valor de edge 0,38; de futilidad 2,2 (umbral 10) | — | **SIN_DECIDIR** | ni confirma ni refuta; seguir con datos sellados semanales |
| ORB0100 1,5R/VWAP (NQ) | descubrimiento +8,6 pts/op; réplica **+6,3 pts/op** | réplica IC 90 % [−4,9, +17,3]; p = 0,17 frente al nivel LORD++ 0,011 | 782 pruebas en ORB0100 + ORB_HORARIOS: efecto esperado ≈ 0 | **SIN_POTENCIA** | ~1.050 operaciones; no abrir el holdout |

Económico con costos canónicos:
- **LUX-IMB pasa los cuatro duros:**
  - neto base > 0;
  - sigue positivo sin las 5 mejores;
  - ningún período pesa más del 80 %;
  - en escenario adverso queda en +0,17 R.

  4 de 6 períodos fueron positivos.
- **ORB0100 falla «sin las 5 mejores» en la réplica:** su resultado depende de cinco operaciones. Aunque tuviera potencia, hoy sería a lo sumo nivel B.

Lectura honesta:
- Ninguno de los dos está refutado y ninguno está cerca de confirmarse.
- La regla de LUX-IMB que se vio buena en el visor **es positiva neta con costos reales en el agregado**. Pero un t de 1,8 tras 46 variantes es lo que el azar produce seguido.
- Las 14 operaciones del holdout no alcanzan para matarla (la futilidad está en 2,2 de 10).
- La escalera la deja **en reserva con el número de operaciones que falta**: ni la descarta, como pasaba antes, ni la promueve, como sugería el visor.

## 9. Fuentes

Corpus propio (`corpus/ssrn/Normalizado/documentos`, `LITERATURE_CLAIM_UNVERIFIED`):
- `0210` Harris, *Limitations of Quantitative Claims About Trading Strategy Evaluation* (2016/2023): corregir sin potencia sube el error de tipo II, y descartar estrategias buenas es un costo de oportunidad.
- `0025` Viaggi, *A Standardized R-Multiple Framework for the Statistical Validation of Trading Edge*: largo mínimo del registro de operaciones en R, y umbral que sube cuando la regla sale de una búsqueda.
- `0006` *A Comprehensive Review of Statistical Methods in Quantitative Finance*, §10.3: Reality Check, SPA, BH/Storey, MCS; FDR frente a FWER cuando m es grande.

Externas:
- Arnott, Harvey y Markowitz (2019), [A Backtesting Protocol in the Era of Machine Learning](https://papers.ssrn.com/abstract=3275654).
- Bailey y López de Prado (2014), [The Deflated Sharpe Ratio](https://papers.ssrn.com/abstract=2460551); [MinTRL](https://www.risk.net/journal-risk/2223785/sharpe-ratio-efficient-frontier).
- Harvey y Liu (2015), [Backtesting](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF): recorte no lineal del Sharpe por pruebas múltiples.
- McLean y Pontiff (2016), [Does Academic Research Destroy Stock Return Predictability?](https://Www.Gwern.net/doc/economics/2016-mclean.pdf): −26 % fuera de muestra, −58 % tras publicar.
- Javanmard y Montanari, [On Online Control of False Discovery Rate](https://arxiv.org/abs/1502.06197); Fisher, [LORD/SAFFRON bajo dependencia positiva local](https://arxiv.org/pdf/2110.08161); [e-GAI (alpha-death)](https://arxiv.org/html/2506.01452v2).
- Fischer y Ramdas, [Sequential Monte-Carlo testing by betting](https://arxiv.org/html/2401.07365v4): e-procesos con validez en todo momento.
- López de Prado, [purged / combinatorial CV](https://en.wikipedia.org/wiki/Purged_cross-validation).
- Romano-Wolf y Hansen SPA en reglas técnicas ([Hsu, Hsu y Kuan 2010](https://ideas.repec.org/a/eee/empfin/v17y2010i3p471-484.html)).
- Modelo de fills y cola: [hftbacktest](https://www.mintlify.com/nkaz001/hftbacktest/concepts/queue-position).

**Aporte al referente:**
- El proyecto vuelve a poder confirmar edges reales: de 2 % a 36 % de potencia en el caso moderado, con FDR < 1 %.
- Los costos son uno solo y medidos.
- Los dos candidatos vivos tienen un veredicto realista con el número de operaciones que falta, en vez de un «muerto» o un «bueno en el visor».
