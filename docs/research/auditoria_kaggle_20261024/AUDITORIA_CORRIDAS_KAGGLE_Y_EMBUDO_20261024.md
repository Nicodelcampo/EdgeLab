# Auditoría de las corridas de Kaggle (22 al 24 de octubre) y del embudo para el Debian

Estado: VIGENTE para los hallazgos y los arreglos de código. Las propuestas P1–P8 están en estado PROPUESTA: deciden Nico.
Fecha: 2026-10-24
Familia / módulo: embudo de grilla (`edgelab/research/embudo.py`), AREAS-EXP-1, AREAS_EXP_1_CRUZADO (U1), EXPANSION_ZONAS
North Star: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Procedencia: base `foundation` en `baabe04c`. Kernels, logs, salidas y metadatos leídos por la API de Kaggle el 2026-10-24 entre
las 02:25 y las 03:10 UTC. Tabla por kernel: `CORRIDAS_KAGGLE_20261022_24.json` (este directorio).
Pedido de Nico: «auditá las corridas recientes y el funnel, para dejarlo listo y sin errores para el Debian, cosa de que pueda
lanzar corridas con millones de variantes correctamente analizadas, filtradas y promovidas».

## 1. Lo más importante
1. **Las 33 corridas terminaron bien.** Todas están en `complete` en Kaggle, son privadas, corren sin internet y usan código
   committeado: el SHA embebido coincide con un commit del repo en 30 de 33. Las 3 que no se pueden verificar son la v1.2
   descartada y los dos E0 target-free, armados antes de que el kernel guardara la cabecera. **Ninguna leyó el holdout:** todas
   las ventanas terminan el 2026-09-30 o antes, y los lectores cortan en el instante 2026-09-30 22:00 UTC.
2. **Faltaban 53 pruebas en el contador global, en 4 corridas con desenlaces.** Son el acuerdo de U1 en NQ, la Fase A de U1-B,
   la integridad de U1 y los topes fuera de muestra. Quedaron registradas de forma retroactiva y marcadas como tales.
3. **La réplica de NQ (abril a septiembre) se usó tres veces en el linaje AREAS-EXP-1.** Fueron la réplica v1.4, U1-B Fase A y
   U1-CRUZADO P2. HOLDOUT-A3 dice «una vez por familia». Es una cuestión de reglas, así que va como propuesta (**P2**).
4. **EXPANSION_ZONAS avanza con candidatas que no superan el azar.** En DESC no hubo ninguna nominación FDR ni rechazo de
   Romano-Wolf en los dos canales y en las dos fuentes, y aun así siguen 3 candidatas por campaña. Si nadie lo frena, gastan la
   réplica y la única apertura del holdout de la familia. Recomiendo pausarlas hasta que decidas **P1**.
5. **La densidad del feed de U1 sí estaba medida.** El kernel devolvió el CSV por día, pero nadie lo trajo al repo. Con la
   lectura fijada en el pre-registro, el resultado es **mercado y no feed**: las señales siguen al rango del día y no a los ticks.
   Esto corrige la revisión del 24-oct.
6. **El embudo tenía 9 defectos que podían romper o ensuciar una corrida desatendida en el Debian.** Quedan corregidos con tests,
   sin cambiar ninguna regla de validación (§4).
7. **Custodia:** el dataset privado `edgelab-dukascopy-nq-usatech` contiene 120 velas M1 (y sus ticks) del holdout, de 22:00 a
   23:59 UTC del 2026-09-30. Se subió antes de la frontera A4. El código no las lee, pero están físicamente en Kaggle (**P4**).

## 2. Las corridas, una por una (resumen; el detalle está en el JSON)
| grupo | kernels | ventana | pre-registro antes de lanzar | contador global | resultado en el repo | costo |
|---|---|---|---|---|---|---|
| AREAS-EXP-1 E0 | `areas-e0-{nq,usatech}` | 2025-08-05 → 2026-03-31 | target-free (no hace falta) | no corresponde | **no** (sin recibo) | 1,545 (literal) |
| AREAS-EXP-1 v1.2 | `areas-desc-usatech` | ídem | manifiesto `3e408cd9`, 1 min antes | sí | descartada sin mirar (correcto) | 1,545 |
| AREAS-EXP-1 v1.3 / v1.3b | `areas-v13-desc-*`, `areas-v13b-desc-*` | ídem | `fa5e3211`, mismo minuto | sí (v1.3b son las mismas celdas) | resumen en MEDIDO; JSON crudo no | 1,545 |
| AREAS-EXP-1 v1.4 DESC y REP | `areas-v14-{desc,rep}-*` | DESC dev; REP 2026-04 → 09 | `6128cb56` / `032e1878`, mismo minuto | sí | sí (`v14/`, idéntico byte a byte) | 1,545 |
| U1-INDAGA | `u1-indaga-{nq,usatech}` | NQ dev; USATECH hasta 2026-09-30 | `30ce30c2`, mismo minuto | sí | sí (idéntico) | 1,5455 |
| U1 acuerdo NQ | `u1-acuerdo-nq` | NQ dev | spec U1-INDAGA | **faltaba** (20) | sí (`U1-INDAGA_NQ_ACUERDO_REP.json`) | 1,5455 |
| U1-B Fase 0 y A | `u1b-fase0-nq`, `u1b-fasea-nq` | dev; NQ 2026-04 → 09 | acta `8b110e49` 1 min antes; adenda 1 min antes | Fase A **faltaba** (1) | Fase A sí (`faseA_resumen.json`) | 1,5455 |
| U1-CRUZADO P1 y P2 | `u1-cruzado-p{1,2}` | dev y 2026-04 → 09 | `96aa7f96`, mismo minuto | sí | sí (idéntico) | 1,5455 |
| U1 integridad / OOS | `u1x-integ-p*`, `u1x-oos-{a,b}` | dev; USATECH 2023-01 → 2025-07 | `814214f1`, mismo minuto | OOS sí; integridad **faltaba** (4) | sí (idéntico) | 1,5455 |
| U1 topes | `u1x-topes-p*`, `u1x-topes-oos-*` | dev; OOS | `531c9b5b`, 1 min antes | dev sí (14); OOS **faltaba** (28) | sí (idéntico) | 1,5455 |
| U1 topes fix 27 | `u1x-fix27-p*` | dev | fix `c8023869`, mismo minuto | re-medición (no son pruebas nuevas) | JSON sí; CSV de operaciones no | 1,5455 |
| U1 densidad | `u1x-densidad` | USATECH 2023-01 → 2026-09-30 | `531c9b5b` | target-free | JSON sí; **CSV por día no** (ahora sí) | — |
| EXPZ DESC | `embudo-expz-{nq,cfd}-desc-20250805` | dev | SPEC y campañas `cc2d2f28`, 7 min antes | sí, pero el commit `def71450` es **2 min posterior** al lanzamiento | **no** (sólo una línea en MEDIDO.md) | 1,5455 + 0,5 (de `costos.py`) |
| EXPZ INDAGA | `embudo-expz-{nq,cfd}-indaga-20250805` | dev | ídem | no se cuenta (P3) | **no**; el estado sigue en CORRIENDO | ídem |

Notas:
- **Pre-registro:** en todas las corridas con desenlaces el pre-registro está committeado antes del lanzamiento, o en el mismo
  minuto. Para el minuto exacto se tomó el `lastRunTime` de Kaggle y la hora del commit.
- **MEDIDO/NO MEDIDO:** se actualizó junto con cada resultado de AREAS y U1. EXPZ sólo escribe su `MEDIDO.md` de campaña, sin el
  nulo completo, porque el embudo no guardaba el RESULTADO (§4, arreglo 9).
- **Costos:** U1 y EXPZ usan la fricción canónica de NQ: 1,5455 pts más 0,5 de adverso, de `edgelab/costos.py`. Los kernels
  AREAS usan el literal `1.545` en `tools/kaggle_areas/areas_main.py`. Es 0,0005 pts menos, irrelevante en el número, pero viola
  la regla «costos sólo de `costos.py`» (**P8**).
- **Holdout:** `fuentes_ticks` y `areas_main` cortan en `HOLDOUT_APERTURA_UTC_NS`. La densidad llega hasta la sesión del
  2026-09-30, que cierra antes de la frontera.
- **Procedencia:** se recuperaron del kernel los 26 manifiestos de lanzamiento que no estaban committeados (versión de cada
  dataset). Quedan en `docs/data_catalog/launches/`.

## 3. Densidad del feed de U1: cerrada con la lectura del pre-registro
- **Qué había:** el kernel `edgelab-u1x-densidad` guardó `U1_DENSIDAD_20230101_20260930_dias.csv` (967 sesiones, con ticks,
  minutos, zonas y rango). Sólo se trajo el JSON con las señales por trimestre.
- **Resultado:** sobre 15 trimestres, las señales por sesión se correlacionan con el rango del día (Spearman 0,92, p de
  permutación 0,0001; parcial 0,90 dado ticks). No siguen a los ticks por día (parcial 0,22; elasticidad log-log 0,07, t 0,19).
  Los minutos con datos son constantes, unos 1.320 por día. **Lectura fijada: mercado.**
- **Alcance:** el rango está en puntos, sin normalizar por nivel de precio, que no estaba pre-registrado. Con n = 15 hay poca
  resolución. No reemplaza la paridad de zonas contra el feed en vivo, que sigue siendo condición para operar U1.
- **Archivos:** `areas_expansion_20261022/u1/topes/U1_DENSIDAD_LECTURA_20261024.json` y el CSV. Agregado en
  `AREAS_EXP_1_MEDIDO_Y_NO_MEDIDO.md`.

## 4. El embudo para el Debian: defectos encontrados y arreglos (sin cambiar reglas)
| # | defecto | qué pasaba | arreglo | test |
|---|---|---|---|---|
| 1 | Métricas por celda desalineadas | `groupby("celda")` omite las celdas sin operaciones. Las listas de latencia, topes y riesgo se acortaban, y la compuerta atribuía a la candidata *i* los números de la *i+1* o fallaba con IndexError. | `etapas._por_celda`: una fila por celda, en orden; si la celda no tiene operaciones, da n=0. | `test_por_celda_conserva_orden_y_celdas_sin_operaciones` |
| 2 | Kernel `complete` sin RESULTADO.json | `traer` lanzaba una excepción en cada ciclo, la campaña quedaba en CORRIENDO para siempre y la falla nunca se contaba. | Ahora cuenta como falla; a la tercera queda BLOQUEADA. | `test_resultado_ilegible_cuenta_como_falla_y_bloquea_a_la_tercera` |
| 3 | Registro de pruebas opcional | Si la configuración del Debian no traía `registry`, el embudo lanzaba DESC sin registrar nada. | Sin registro no se lanza ninguna etapa con desenlaces. | `test_sin_registro_no_se_lanza_una_etapa_con_desenlaces` |
| 4 | TOPES contaba 6 fijo | Con `topes.lista` propia, el contador no coincidía con lo que corría. | Cuenta los topes que corren de verdad. | `test_topes_registra_los_topes_que_corren` |
| 5 | Reglas «congeladas» que no lo estaban | El docstring dice que las reglas se escriben antes de usarse, pero las compuertas leían el JSON vivo: cambiar `seleccion`, `topes` o `n_fijo` después de DESC cambiaba la regla en silencio. | Las compuertas leen la copia del estado. Sólo `holdout.desde` puede moverse hacia adelante. Si cambia la identidad (familia, experimento, señal, ejecución o períodos), la campaña queda BLOQUEADA. | `test_reglas_congeladas_…`, `test_cambio_de_identidad_…` |
| 6 | Dos conductores sobre una campaña | Si se encendía el embudo del Debian, el Debian arrancaba EXPZ desde cero mientras la máquina de trabajo la conducía. Las dos empujaban **el mismo slug** de Kaggle, cada una con su estado, su libro de LORD++ y su libro de ventanas. | Campo `"conductor"` (`debian` o `local`). El Debian sólo conduce las suyas e informa el resto como omitidas; `embudo_correr.py` se niega a conducir una ajena. EXPZ-NQ y EXPZ-CFD quedan como `local`. | `test_un_solo_conductor`, `test_campanas_del_repo_…` |
| 7 | Libro de ventanas del holdout en el clon de código | En el Debian, el ACTA escribía la apertura en `docs/` del clon fijado. No se publicaba, y `update.sh` no podía cambiar de versión. | El libro vive en el estado (`autopilot_runs/HOLDOUT_VENTANAS.jsonl`). En cada ciclo se le agregan las filas nuevas del repo, y `sync_state.sh` lo sube. | `test_libro_de_ventanas_del_estado_se_une_al_del_repo` |
| 8 | Campañas que usan la réplica para descubrir | La plantilla de la guía (§8) traía `desc` hasta el 2026-09-30 con ejecución en NQ (viola A3) y `holdout.desde` 20261001. | El PREFLIGHT de la campaña rechaza `desc` u `oos` que toquen el holdout, `desc` posterior al 2026-03-31 con ES o NQ, y `holdout.desde` anterior a la frontera. Plantilla corregida. | `test_campana_a3_y_holdout` |
| 9 | Detalles del Debian | El slug de HOLDOUT_CONTEO llevaba «_», que Kaggle rechaza. El push tenía un timeout de 1.800 s y el servicio corta el ciclo a los 900. Los manifiestos de lanzamiento se escribían en archivos versionados del clon de código y bloqueaban `update.sh`. HOLDOUT podía decidir con menos de N operaciones. | Slug sin «_». Timeouts de 480, 120 y 300 s. `sync_state.sh` copia los manifiestos al estado y `update.sh` los guarda y restaura. HOLDOUT con menos de N queda BLOQUEADA. | `test_slug_sin_guion_bajo` |

No toqué gates, FDR, mandato ni archivos protegidos (`config/autopilot/protected.json`). Los arreglos 3, 5 y 8 hacen cumplir
reglas que ya están escritas (el contador antes de correr, las reglas escritas antes de usarse y la partición A3); no agregan
ninguna regla nueva.

**Escala (millones de variantes):** el cómputo pesado corre en Kaggle. EXPZ (233.280 celdas por canal) tardó unos 18 minutos y
U1-INDAGA (casi 3 M por canal), unos 19. El límite práctico es la memoria de Romano-Wolf: B × celdas evaluables × 4 bytes. Con
B = 200 son unos 0,8 GB por millón de celdas evaluables, así que un kernel de unos 30 GB aguanta alrededor de 25 M de evaluables.
Más que eso hay que partirlo por perilla de grupo.

## 5. Propuestas (las decide Nico; no apliqué ninguna)
- **P1. DESC sin señal no pasa.** Hoy una pista con IC90 inferior > 0 pasa aunque el tamiz FDR y Romano-Wolf den cero. Entre
  233.280 celdas, la mejor por IC90 es, por construcción, el máximo del azar. Propongo exigir al menos uno de los dos: nominación
  FDR o rechazo de Romano-Wolf en algún canal. Hasta que lo decidas, **recomiendo pausar EXPZ-NQ y EXPZ-CFD** (`activa: false`):
  la siguiente etapa que gasta algo es OOS en NQ de abril a septiembre, y después viene el ACTA con la única apertura de la
  familia.
- **P2. La réplica de A3 también se consume por linaje.** Propongo un libro de ventanas de réplica, como el del holdout, en el
  que la réplica de ES/NQ de abril a septiembre se consuma para la familia y para las que derivan de ella. Con eso, U1-B y
  U1-CRUZADO P2 serían una segunda y una tercera mirada, y EXPZ (diseñada después de U1) no tendría réplica limpia en NQ.
- **P3. Contar INDAGA e INTEGRIDAD en el registro.** Las dos usan desenlaces. INTEGRIDAD además decide (placebo y latencia).
  Contarlas sólo aumenta la multiplicidad declarada.
- **P4. Re-versionar `edgelab-dukascopy-nq-usatech`** cortado en 2026-09-30 22:00 UTC, y lo mismo con cualquier spot que se
  haya subido con corte en la fecha UTC. Hace falta tu OK, porque es una subida.
- **P5. Un solo libro de LORD++ por familia, versionado.** Hoy cada conductor tiene el suyo: la familia AREAS-EXP-1 lleva sus
  pasos a mano en las actas (α del paso 2 = 0,003608) y un libro nuevo en el Debian arrancaría otra vez en el paso 1. Propongo
  sembrarlo desde las actas y hacer que el embudo rechace un libro que no sea el canónico.
- **P6. MES y MNQ dentro de A3.** Son el mismo mercado que ES y NQ. Hoy la partición sólo nombra ES y NQ.
- **P7. Romano-Wolf:** sumar la corrección +1 a `p_rw_del_maximo` y usar B ≥ 500 cuando el umbral queda cerca del t máximo.
  Ya estaba anotado en la revisión del 24-oct.
- **P8. Costo de AREAS** desde `edgelab.costos`, en vez del literal 1,545. Además, el `CLAUDE.md` todavía dice que la release
  `liquid_tick_v1` v4 «no está aprobada», pero está aprobada desde el 2026-10-14 (`docs/infra/release_approval/release_approval_db9c42cd.json`).

## 6. Para arrancar en el Debian
1. `update.sh <sha de este PR una vez mergeado>`, con el timer parado.
2. En `/etc/edgelab/autopilot.json`: `"registry"` presente (si falta, el embudo ya no lanza), `"embudo": {"activo": true,
   "conductor": "debian", ...}` y `"decision": "escalera_v1"`.
3. Las campañas nuevas del agente llevan `"conductor": "debian"`; el programador ya lo pide en su instrucción. EXPZ queda en
   `local` hasta que decidas P1.
4. Doctor y un ciclo en `propose`. Revisar que `--status` muestre las campañas omitidas con su motivo.
5. Después de cada etapa con desenlaces, pasar al repo el `trial_registry.jsonl` y las aperturas de `HOLDOUT_VENTANAS.jsonl` del
   estado (`tools/registro_global.py`).

## 7. Qué no hice
- No avancé EXPZ (INDAGA terminó en Kaggle, pero la conduce otra máquina) ni la pausé: eso queda para P1.
- No toqué datasets de Kaggle (P4) ni las reglas de las propuestas.
- No volví a correr el OOS de U1 con el fix 27, que la revisión dejó pendiente.

Aporte al referente: el embudo ya puede correr solo en el Debian sin gastar la réplica ni el holdout por un error de código, de
conductor o de libro. El contador de pruebas recupera 53 pruebas que faltaban, y la densidad de U1 deja de ser una pregunta
abierta: el salto de señales es mercado. Lo que sigue bloqueando un edge operable (P1, P2 y la paridad de feed) queda escrito
como decisión, no como herencia.
