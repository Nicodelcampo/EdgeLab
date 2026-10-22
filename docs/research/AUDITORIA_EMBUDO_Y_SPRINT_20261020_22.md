# Auditoria del embudo y registro del sprint 2026-10-20 .. 2026-10-22 (LUX-IMB, ORB, EURUSD)

Estado: VIGENTE (auditoria + indice). Fecha: 2026-10-22. Pedido de Nico: "ordenar el repo; documentar todas las pruebas;
determinar si el embudo funciona, si lo uso como agente, y si que haya descartado las expansiones con OG/VI al inicio
sugiere que esta mal disenado, ya que visualmente arrojaba buenos resultados".
Referente sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

## 1. Indice de todo lo medido (20 campanias, 1.535 pruebas; registradas retroactivamente en el contador global)
`tools/registrar_campanias_20261020.py` -> `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl` (total del proyecto: 155.167 pruebas, incluidas las 450 del trabajo externo de GC, §1b).

| familia | campania | pruebas | veredicto | documento |
|---|---|---:|---|---|
| LUX-IMB | paridad NT8 -> Python (NQ DEC26) | — | 1507/1507 logica, 1373/1373 punta a punta | `luximb_parity_20261020/PARIDAD_LUXIMB_NQ1226_20261020.md` |
| LUX-IMB | M1-M3 rebalanceo / control / continuacion | 7 | sin efecto (MDE 8,4 pp) | `.../RESULTADOS_M1_M2_M3_LUXIMB_NQ_20261020.md` |
| LUX-IMB | M4 penetracion 25-75 % | 10 | sin efecto (signo opuesto) | `.../RESULTADOS_M4_PENETRACION_LUXIMB_NQ_20261020.md` |
| LUX-IMB | M5 vuelta al inicio cargado | 6 | sin efecto (+2,2 pp n.s.) | `.../RESULTADOS_M5_INICIO_CARGADO_LUXIMB_NQ_20261020.md` |
| LUX-IMB | M6 escalonadas 150t sobre area cargada (NQ) | 6 | sin efecto a favor; menos recorrido | `.../RESULTADOS_M6_ESCALONADAS_LUXIMB_NQ_20261020.md` |
| LUX-IMB | M7 / M7b ES (freno) + control volatilidad | 6 | era volatilidad de regimen | `.../RESULTADOS_M7_ES_AREA_CARGADA_20261020.md`, `..._M7B_...` |
| LUX-IMB | M8 franjas desbalance + GBM | 5 | sin efecto (MDE ~6 pp; ML no mejora) | `.../RESULTADOS_M8_FRANJAS_DESBALANCE_20261020.md` |
| LUX-IMB | M9 distancia/tiempo/zonas | 8 | NQ +6,6 pp no confirma en ES | `.../RESULTADOS_M9_DISTANCIA_TIEMPO_ZONAS_20261020.md` |
| LUX-IMB | M10 / M10b 6 activos | 4 | nada transporta; H3 era "precio ya visitado" | `.../RESULTADOS_M10_M10B_MULTIACTIVO_20261020.md` |
| LUX-IMB | M11 grilla SL/TP/BE del fade del visor | 40 | lectura CORREGIDA: entrada vale en NQ (+4,95 pts/op en 499) | `.../RESULTADOS_M11_GRILLA_SLTP_20261020.md`, `CORRECCION_LECTURA_M11_20261020.md`, `DASHBOARD_VISOR_POR_PERIODO_NQ_20261020.md` |
| LUX-IMB | variantes TP/SL/BE + auditoria look-ahead | 5 | BE no suma; sesgo de supervivencia corregido (0 marcas cambian) | `.../AUDITORIA_ENTRADA_LOOKAHEAD_Y_BE_20261021.md` |
| LUX-IMB | candidato congelado + holdout exploratorio (n=14) | 1 | 14 SL / 0 TP (-20,15 pts/op); apertura de esas sesiones consumida | `.../CANDIDATO_HOLDOUT_REGLA_VISOR_NQ_20261021.md`, `HOLDOUT_DATOS_INTEGRIDAD_NQ1226_20261021.md` |
| ORB0100 | grilla 48 (NQ IS/OOS + ES) | 48 | original sin edge; 1 variante al limite | `orb0100_20261021/RESULTADOS_ORB0100_20261021.md` |
| ORB0100 | V2 multiactivo (24 variantes x 8 activos) | 25 | nada transporta | `.../RESULTADOS_ORB0100_V2_MULTIACTIVO_20261021.md` |
| ORB0100 | replicacion NQ abr-sep | 1 | +6,85 pts/op, NO_CONCLUYENTE | `.../REPLICACION_NQ_ABR_SEP_PREREGISTRO_20261021.md` |
| ORB0100 | franjas OG/VI como filtro | 3 | no suman ni restan | `.../RESULTADOS_ORB_HORARIOS_Y_FRANJAS_20261021.md` |
| ORB-HORARIOS | 704 celdas (44 ventanas x 2 x 8) + GC nocturno abr-jun | 705 | 0 pasan BH; GC nocturno refutado | idem + `PREREGISTRO_GC_NOCTURNO_20261021.md` |
| EURUSD | grilla escalonadas (648, misma de MNQ) | 648 | 0/648 sobreviven max-T | `eurusd_escalonadas_20261021/RESULTADO_EURUSD_ESCALONADAS_ESCALAS_20261021.md` |
| EURUSD | simulaciones visuales (SL mitad / ult2 / pri2 x escalas) | 7 | exploracion; con costos solo 150t ~+0,09 R | `.../INDICADOR_ESCALONADAS_OGVI_EURUSD_20261021.md` |
Registros MEDIDO/NO MEDIDO por familia: `luximb_parity_20261020/LUXIMB_MEDIDO_Y_NO_MEDIDO.md`, `orb0100_20261021/ORB0100_MEDIDO_Y_NO_MEDIDO.md`.
Herramientas NT8: `nt8/user_indicators/ImbalanceDetectorLuxAlgoMTF.cs` (export), `ORB0100Filtros.cs`; addons
`nt8/addons/ReplayDownloaderEdgeLab.cs` y `EdgeLabTickHistory.cs` (8.1.8.4, modo HOLDOUT SELLADO).

## 1b. Incidente de procedencia: trabajo de otro proceso en este arbol
Al ordenar el repo aparecieron, sin commitear, `tools/luximb_parity/gc_150t_grid_visual.py`, `gc_150t_full_experiment.py`,
`docs/research/eurusd_escalonadas_20261021/gc_150t_grid_visual.json`, `gc_150t_experiment_full.json` e
`INFORME_GC_150T_GRILLA_COSTOS_OOS_20261021.md`, escritos el 2026-10-21 entre 13:52 y 14:01 por **otro proceso** (no por
esta sesion) en el mismo directorio de trabajo — viola "un solo escritor por directorio" (mismo tipo de falla que el
incidente del 2026-08-10). Contenido: barrido de 450 combinaciones de escalonadas 150t en GC (contratos 12-25 / 02-26 /
04-26, todo descubrimiento) que declara 6 configuraciones con R neto > 0 en los tres contratos. **Sin manifiesto previo, sin
registro, sin correccion por multiplicidad de familia y sin auditar por esta sesion**: se conserva como
`EXPLORATORIO_NO_AUDITADO` (procedencia externa) y se registran sus 450 pruebas en el contador global. No se promueve nada.

**Actualización 2026-10-22 (`USER_REPORTED`):** Nico aclara que son pruebas suyas hechas con Antigravity el 2026-10-21, «sin
mucha importancia». Procedencia resuelta; el estado `EXPLORATORIO_NO_AUDITADO` y las 450 pruebas en el contador se mantienen.
Sigue en pie la regla: un escritor por directorio (otra herramienta en el mismo árbol, otra worktree).

## 2. ¿El embudo funciona?
El embudo existe en tres piezas: el playbook EF0-EF5 (`docs/research_funnel_playbook.md`), el runner `edgelab/funnel/`
(+ `tools/discovery_scan.py` con nulo de maximo por sesion y D0/D1/D2) y el **contador global de pruebas**
(`TRIAL_REGISTRY_GLOBAL.jsonl`). Las piezas estadisticas son correctas (revision 2026-10-04). Pero:
- El runner esta pensado para **matrices de senales/configs** (screening de arrays), no para **estudios de eventos con
  simulacion de operaciones a medida** (impulsos, escalonadas, ORB), que es todo lo que se hizo en este sprint.
  `COMPONENT_FUNNEL.md` mismo dice que faltan "wiring upstream y criterios estadisticos especificos".
- Conclusion: **funciona como marco conceptual y contador, no como herramienta que cubra estas preguntas.**

## 3. ¿Lo use como agente?
**No.** Escribi scripts propios por hipotesis (`tools/luximb_parity/*`, `tools/orb0100/*`, `tools/eurusd_escalonadas_grid.py`).
Si aplique sus principios (manifiesto antes de mirar, holdout, Holm/BH/max-T, controles, MDE, nulos), pero:
1. **No registre ninguna campania en el contador global** (1.535 pruebas fuera de la cuenta hasta hoy).
2. No etiquete las etapas EF (que era EF2 exploratorio y que EF4/EF5).
3. No use `discovery_scan` ni el nulo de maximo por sesion del runner.
**Causa raiz (senalizacion):** `CLAUDE.md` nombra el playbook como "practicas transversales" pero sus rituales no dicen
"toda campania con desenlaces se registra en el contador global" ni "declara su etapa EF"; el runner no cubre estudios de
eventos, asi que el camino natural es escribir un script nuevo. Correccion aplicada: ritual nuevo en `CLAUDE.md` (registro
global + etapa EF + simulacion visual realista) y registro retroactivo.

## 4. ¿Descartar las expansiones con OG/VI al inicio sugiere que el embudo esta mal disenado?
Hechos (todos en los documentos de la tabla):
| fuente | numero |
|---|---|
| visor (entrada en X, sin costos, periodo de diseno NQ 09-26) | +0,8 R/op, 30 % acierto (+1.781 pts en 150 op) |
| misma regla, entrada realista + costos, NQ 09-26 | +5,6 pts/op |
| misma regla realista, todos los periodos NQ (499 op) | **+4,95 pts/op, IC 95 % [+0,55, +9,2]**, positiva 4/5 periodos |
| misma regla en ES | ~0 |
| holdout exploratorio NQ oct-2026 (n = 14) | 14 SL / 0 TP, -20,15 pts/op |
Diagnostico:
1. **La impresion visual estaba inflada** por tres razones medidas: entrada en el extremo X (relleno optimista: explica 2-3x
   del resultado), sin costos, y mirada sobre el mismo periodo con el que se diseno y ajusto la regla.
2. **Pero el sistema tambien fallo** en dos puntos que NO son estadisticos:
   a. **Validez de constructo (diseno de hipotesis, mio):** M1-M10 midieron mecanismos (rebalanceo, penetracion, desbalance,
      freno) en vez de la **regla operable que Nico estaba mirando**. Probaban "¿las zonas causan X?" y no "¿esta regla gana
      plata?". La regla exacta recien se midio en M11.
   b. **Lectura de M11 (mia):** se declaro muerta la regla porque el ranking de SL/TP era ruido y ningun tramo excluia 0;
      se confundio "parametros sin valor" con "entrada sin valor" y se afirmo "efecto del periodo" sin calculo
      (`CORRECCION_LECTURA_M11_20261020.md`). Con el agregado, la regla en NQ era un candidato real.
3. Lo que el embudo hizo bien: no la promovio sin prueba independiente, la llevo a holdout congelado, y la primera mirada
   fuera de muestra (n = 14) salio en contra. Con n = 14 no es veredicto, pero va en la direccion del filtro, no del visor.
**Respuesta:** no esta mal disenado en lo estadistico; estuvo **mal aplicado** en dos lugares (constructo y lectura) y
**mal senalizado** (no se usa solo). El "buen resultado visual" no era evidencia: la mitad era relleno optimista y periodo
de diseno.

## 5. Cambios que quedan como practica
1. Idea surgida en el visor -> **primero se mide la regla exacta** (entrada realista + costos, todos los periodos, agregado
   + consistencia) y recien despues los mecanismos.
2. Toda campania con desenlaces: **registro en el contador global** antes de correr y **etapa EF declarada** en el manifiesto.
3. Simulaciones del visor: mostrar **entrada al cierre de la confirmacion** y **costos** por defecto (pendiente de implementar
   en el tablero de picos; el de impulsos ya entra en la confirmacion).
4. Pendiente de diseno: un runner de **estudios de eventos** dentro de `edgelab/funnel/` (eventos -> simulacion -> nulo
   -> multiplicidad -> registro) para que el camino facil sea el correcto.

Aporte al referente: deja contado todo lo probado (1.535 pruebas), explica por que el visor y el embudo discreparon y
corrige la senalizacion para que el proximo analisis pase por el embudo sin depender de la memoria del agente.
