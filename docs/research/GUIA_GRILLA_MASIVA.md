# Guía para experimentos de grilla masiva (miles a millones de variantes)

Estado: VIGENTE (2026-10-22, nacida de AREAS-EXP-1; se actualiza con cada corrida)

Sirve para cualquier experimento con muchas perillas: zonas, indicadores o reglas de entrada y salida. Las herramientas son:
- `edgelab/research/grilla_masiva.py`: perillas, tensor, criba FDR, máscara y meseta;
- `edgelab/funnel/escalera.py`: inferencia, recorte, económico y potencia;
- `edgelab/funnel/secuencial.py`: holdout y paper;
- `tools/kaggle_grilla/construir_kernel.py`: kernel autocontenido con SHA;
- `edgelab/costos.py` y `edgelab/holdout.py`: costos y frontera del holdout.

El ejemplo completo es AREAS-EXP-1: `edgelab/research/areas_expansion*.py`, `tools/kaggle_areas/`, `docs/research/areas_expansion_20261022/`.

## 1. Orden obligatorio

1. **Spec escrita** con cada variable definida de forma exacta: qué se mide, cuándo y con qué datos (sólo el pasado del disparo). Se escriben también la justificación económica y cómo podría refutarse.
2. **Motor con tests de resultado conocido:** cada pieza (eventos, variables, simulador, tensor) contra casos armados a mano.
3. **Oráculo para todo código compilado** (numba): una versión Python simple de la misma regla y un test que las compare sobre datos aleatorios **con empates**.
4. **Controles de punta a punta sin mercado:**
   - ruido puro → 0 nominadas;
   - efecto plantado → el embudo lo encuentra y elige la dirección correcta.

   Si el control positivo da algo raro, la definición está mal, no el mercado.
5. **E0 target-free en los datos reales:** conteos por configuración y distribuciones de cada variable.
   - **Los cortes de las perillas salen de acá** (cuantiles de cada fuente), nunca de números elegidos a ojo.
   - Si una perilla deja casi todo en un nivel, no filtra nada y hay que recalibrarla.
6. **Registro en el contador global ANTES de correr con desenlaces.** Si la grilla cambia, se registra de nuevo; no se reutiliza la cuenta vieja.
7. **DESC (descubrimiento):** tensor, tamiz FDR y E2 sobre sobrevivientes. Se elige para réplica por la cota inferior del IC, nunca por P&L máximo.
8. **REP:** las celdas y los cortes se congelan desde el descubrimiento; el período nunca se miró y el nivel lo asigna LORD++.
9. **Holdout:** sólo con `LISTA_PARA_HOLDOUT`, con seguimiento secuencial.

## 2. Reglas que salen de errores reales (no repetirlos)

| Error (AREAS-EXP-1, 2026-10-22) | Regla |
|---|---|
| El «área» se definió como zonas pegadas; Nico pedía «X zonas en X área». Resultado: 0,35 áreas por día. | Releer el pedido variable por variable y confirmar con un E0 que el objeto existe en cantidad útil antes de congelar. |
| Cortes de comercio fijos (0, 1, 3) cuando la mediana real era 10 → la perilla no filtraba. | Cortes desde cuantiles del E0 de cada fuente, guardados en el resultado. |
| La búsqueda compilada ordenaba por una clave combinada `-cnt*1e12 + ancho` y perdía precisión. | Nunca combinar claves en un float: ordenamientos estables sucesivos (como `lexsort`). Oráculo con empates casi exactos. |
| Valores faltantes (v_rel de la primera sesión) se rellenaban con −1 y caían en el tercio «bajo». | Un dato faltante nunca cae en un nivel real: índice −1 (fuera de la celda). Test explícito. |
| Una vela M1 que toca SL y TP se resolvía siempre como SL. | Resolver con el orden real de los ticks de esa vela; un stop saltado se llena en el tick real. Informar cuántos casos se resolvieron así. |
| Se fijó la entrada a mercado «en la apertura siguiente» como si fuera la única correcta. | **El momento de llenado es una decisión de cada análisis, no una regla del motor.** Se declara por operación (`limite` 0 = cierre de la vela de decisión, 2 = primer tick siguiente) y, si hay duda, se prueban las dos como perilla. |
| El reporte E0 recorría 3 de 4 valores de W. | Recorrer siempre con `len(...)` de la tupla de valores, nunca con un número escrito a mano. |
| Minutos repetidos entre bloques se descartaban en silencio. | Fallar ruidosamente ante datos inconsistentes. |
| El manifiesto exigía ≥ 20 sesiones por celda y el código no lo aplicaba. | Cada condición del manifiesto tiene su línea de código y su test. |
| El manifiesto pedía «MDE por zona de la grilla si no pasa ninguna» y el kernel no lo calculaba; hubo que relanzar sólo para eso. | Toda grilla publica `grilla_masiva.resumen_nulo` (MDE del tamiz y de confirmación por nivel de perilla, colas de t) nomine o no. |
| El tamiz BH trataba como independientes celdas anidadas, contaba celdas no probables, usaba t por operación y un solo promedio del período: 0 de 1 millón y nadie sabía si era nulo o filtro. | Además del tamiz: `romano_wolf` (umbral medido con remuestreo por sesiones), canal `reciente` declarado y `pistas` distintas a réplica (ATJ-24, ATJ-25). |
| Se aplicó LORD++ de a una a 80 réplicas simultáneas: gastó el nivel en las primeras y las últimas (las mejores) quedaron con nivel ≈ 0. | Un lote de réplicas simultáneas usa un procedimiento por lote (BH dentro del lote con el nivel de un paso LORD++, o LORD por lotes), declarado en el manifiesto. |
| U1-INDAGA: el BE (mover el stop a la entrada al recorrer 1R) nunca se armaba porque el objetivo quedaba antes de 1R. 48 de 96 ejecuciones eran copias. | `grilla_generica.ejecuciones_equivalentes` publica los grupos idénticos en cada corrida. Una perilla muerta se rediseña, no se vuelve a correr igual. |
| La regla de selección de U1 pedía la media de cada candidata de USATECH en NQ, y el kernel de NQ sólo publicaba sus propias pistas. | Si la regla cruza fuentes, el manifiesto planea el paso: REP de las candidatas sobre la exploración de la otra fuente, con los cortes de esa fuente. |
| El ciclo autónomo pasaba cada `/rep/` de una corrida de a una por LORD++, en orden alfabético. | `escalera.probar_lote`: una corrida es un paso de LORD++ (Simes del lote; si rechaza, BH adentro). |
| Una familia nueva del agente no estaba en `result_files` del Debian: la corrida se lanzaba y nunca se cerraba. | Por defecto se lee `STUDY_RESULTS.json`, que es lo que escribe todo kernel genérico. |
| Un experimento aplicado por el programador no tenía cómo convertirse en corrida. | Campañas como datos en `config/autopilot/grillas/campanas/*.json` → `generate.campanas_grilla`. |
| Marginales con muestras chicas (U1 en NQ: n = 66 en la base) salían vacías. | Se informa desde 10 operaciones con la marca `chica`; `MARGINALES_POOL` agrega perillas para ganar potencia. |
| U1-B: las cotas del e-proceso salieron del peor caso de 69 operaciones (×1,5) de una regla con stop más allá del extremo; en datos nuevos una pérdida las superó y el seguimiento se detuvo (LIMITE_VIOLADO). | Seguimiento secuencial sólo con pérdida máxima por operación estructural: la regla tiene un tope de stop, o las cotas salen de la geometría de la regla, nunca del peor caso visto. |
| El generador sintético reiniciaba el precio a 20.000 cada día: el «ruido» tenía reversión plantada sin querer y los controles de ruido no eran de ruido (lo encontró el preflight). | `sintetico.bloques` continúa el precio entre días; `test_ruido_sintetico_es_martingala` lo verifica. |
| Resultados de una regla elegida entre miles de celdas leídos sin recorte (U1-B: +7,3 en la selección, −0,18 después). | Toda pista y réplica publica `media_esperada_fuera` (recorte de Harvey-Liu con el número de celdas miradas). |
| Se lanzó una corrida con código que después tuvo correcciones. | Esa corrida **no se mira**; se documenta como descartada y se relanza. Mirarla y después corregir sería ajustar con los datos. |
| El perfil de volumen por disparo en Python hacía lento el kernel con ticks reales. | Perfilar antes de lanzar; los bucles por evento, en numba y en lote; nada por operación en Python que pueda hacerse por evento. |
| `fcntl`, `/dev/null` y CRLF rompían herramientas en Windows. | Las herramientas compartidas con el Debian se prueban en las dos plataformas (la suite corre en Windows con `tests/conftest.py`). |
| Corte del holdout a las 00:00 UTC (deja pasar 2 h de la sesión). | La frontera sale sólo de `edgelab/holdout.py` (apertura de la sesión, 22:00 UTC del día anterior). |

## 3. Capacidad, cobertura y relevancia

- **Escala:** cada operación se simula una vez. Las perillas que filtran se discretizan y las celdas salen del tensor con sumas acumuladas: costo O(operaciones + celdas). En AREAS-EXP-1 son ~1 millón de celdas y ~8 millones de operaciones por fuente, en minutos.
- **Cobertura de escenarios:** valores con espaciado geométrico y rangos amplios (p. ej. A/H ≥ 1, 2, 4, 8; W = 5, 15, 40, 100), para que las variantes sean distintas de verdad.
- **Multiplicidad honesta:**
  - las celdas anidadas comparten operaciones: el tamiz es FDR (escala a millones) y la selección final usa meseta, N_eff y réplica;
  - la t por operación del tamiz es aproximada, porque no agrupa por sesión. Por eso E2 recalcula con bootstrap por sesiones antes de elegir.
- **Relevancia:** sólo pasa a réplica una celda cuyo objetivo mediano esté a ≥ 3× la fricción canónica (`friccion.RATIO_MIN`) y con ≥ 20 sesiones. Lo chico frente al costo no se promueve aunque sea significativo.
- **Realismo:**
  - costos de `edgelab/costos.py` (base y adverso);
  - las órdenes límite sólo se llenan si el precio atraviesa el nivel por 1 tick;
  - stops con hueco al precio real;
  - nada cruza la sesión;
  - un CFD o spot se informa como información, no como operable.
- **Potencia:** todo nulo publica su MDE. Una celda sin potencia no es una celda refutada.

## 4. Reutilizar para una corrida nueva

1. Escribir el módulo del experimento: eventos, variables, `niveles` y `perillas()`. El simulador y el núcleo se reutilizan.
2. Escribir el conductor con modos `E0`, `DESC` y `REP`. Copiar de `areas_expansion_run.py`.
3. Escribir el principal del kernel (lectura de datos) y empaquetarlo con `tools/kaggle_grilla/construir_kernel.py`.
4. Seguir el orden de §1.

## 5. Para el agente del Debian

| quiere | cómo | qué pasa |
|---|---|---|
| **usarla** | RunSpec de `config/autopilot/grillas/AREAS_EXP_1.json` (kernel committeado `tools/kaggle_areas/kernel_areas.py`) | pre-registro → revisores → guardas → Kaggle → `STUDY_RESULTS.json` → `escalera_v1` |
| **variantes de la misma idea** | env `GRILLA` = JSON con NS/WS/XS/A_CORTES; cortes desde un E0 propio | `n_trials` = `areas_expansion.n_celdas()`; el bloque JSON va idéntico en el pre-registro |
| **un experimento nuevo** (otro objeto, otras variables) | pedido al programador; el código va en `edgelab/research/agente/` y `tools/agente/` y reutiliza el núcleo | se aplica solo con la suite verde y `test_control_ruido`, `test_control_plantado` y, si usa numba, `test_oraculo` |
| **mejorar el núcleo** (`grilla_masiva`, simulador, escalera) | pedido al programador | queda como rama `autopilot/propuesta/<id>` para revisión humana: lo usan todas las corridas |

Lo que no cambia con el código nuevo: las corridas cuentan en el contador global, el holdout sólo se abre por protocolo, una corrida con código corregido después no se mira, y la réplica usa celdas y cortes congelados.

## 6. Escribir un experimento nuevo (el camino del agente)

El conductor es genérico (`edgelab/research/grilla_generica.py`). Un experimento es un módulo chico; el ejemplo completo es
`edgelab/research/u1_indaga.py` (con sus tests en `tests/research/test_u1_indaga.py`).

```python
NOMBRE = "MI-EXP"
INDICADORES = ["LUX-IMB"]                      # sólo PASS de config/autopilot/indicadores.json (o NATIVO_AGENTE con test_causal)
VARIABLES = [Variable("A/H", "A_H", "ge", cortes=(4, 8, 16), piso=True),        # cortes con significado
             Variable("vol_rel", "vol_rel", "extremos", cuantiles=3)]           # o por cuantiles del E0 de la misma fuente
EJECUCIONES = [(entrada, objetivo, stop, be) for ...]                            # lo que el experimento necesite
EJES_ORDINALES = (0,)                           # para la meseta
BASE = {"A/H": 1, "ejecución": 0}               # celda de referencia de las marginales (indagación)
def disparos(ctx): ...                          # DataFrame con k (vela de decisión) + variables con SÓLO el pasado de k
def niveles(fila, ej, ctx): ...                 # (start, limite 0/1/2, s, entrada, stop, objetivo, be) o None
```

1. Los tests van en `tests/agente/test_<módulo>.py`: `test_control_ruido`, `test_control_plantado` y `test_causal`
   (`edgelab/research/indicadores.causal`). Si el módulo usa numba, también `test_oraculo`.
2. El kernel se arma con `python tools/kaggle_grilla/construir_kernel_experimento.py <módulo> tools/agente/kernel_<x>.py`.
   El experimento se elige con `EXPERIMENTO=<ruta.del.módulo>`, y además `FUENTE`, `MODO`, `DESDE` y `HASTA`. La plantilla está en
   `config/autopilot/grillas/PLANTILLA_GENERICA.json`.
3. Registro: `grilla_generica.n_celdas(exp)` por fuente y canal, en el contador global, antes de correr.
4. El simulador y los lectores de datos (`fuentes_ticks.py`) no se copian. Una fuente nueva es una función más en `FUENTES`.
5. Un **indicador propio** entra como `NATIVO_AGENTE` en `config/autopilot/grillas/indicadores_agente.json`, que está en el perímetro del agente y sólo admite ese estado, con `modulo` y `test_causal`. Sirve para research si pasa `causal()`. No se opera en vivo
   hasta tener su versión NT8 con paridad.

## 6b. Preflight (antes de lanzar cualquier cosa)
`python -m edgelab.research.preflight <módulo>` y, para campañas, `preflight.verificar_campana`. Para resultados ya bajados,
`preflight.codigo_vigente(resultado)` dice si el código cambió desde la corrida.

## 7. Variante buena → indagar antes del P&L básico (ATJ-26)

Una celda que sobrevive (o una pista que replica) no pasa directo a un P&L de confirmación. Antes se indaga con un experimento
propio alrededor de ella, con la celda como `BASE` del módulo:
- **marginales:** se mueve una perilla por vez, para ver qué variable ordena el retorno y cuál filtra;
- **dónde está y cuánto vale lo que la explica:** volumen, velocidad, valor justo, régimen;
- **esperas antes de entrar:** retroceso, volver al volumen, esperar a que se haga volumen;
- **acuerdo entre fuentes.**

La regla de selección para la confirmación se escribe antes de mirar, y la confirmación usa datos que la indagación no tocó.

## 8. El embudo automático (2026-10-23): sólo se escribe la lógica y la campaña

Pedido de Nico: «que siga siempre un embudo, en cualquier activo y con cualquier lógica, sin errores, sin armarlo cada vez, y
autónomo en el Debian».

**Lo único que se escribe:**
1. **El módulo del experimento,** con la interfaz de §6.
2. **La campaña,** como JSON en `config/autopilot/grillas/campanas/` con `"embudo": true`. Ejemplo: `U1_CRUZADO.json`.

```json
{"cid": "...", "familia": "...", "experimento": "edgelab.research.agente.mi_exp", "sensor": "DK:USATECHIDXUSD", "ejecucion": "NQ",
 "desc": [20250805, 20260331], "oos": [20260401, 20260925], "embudo": true, "conductor": "debian",
 "justificacion_economica": "...", "como_podria_refutarse": "...",
 "seleccion": {"max_candidatas": 3}, "holdout": {"desde": 20261023, "n_fijo": 150}}
```

- **`conductor`** (obligatorio desde la auditoría del 2026-10-24): `"debian"` la conduce el ciclo del Debian; `"local"`, sólo
  `tools/embudo_correr.py --conductor local`. Sin conductor no la conduce nadie: dos conductores relanzan el mismo slug de Kaggle
  y llevan estados, libros de LORD++ y de ventanas distintos.
- **Períodos:** con ES o NQ como señal o ejecución, `desc` termina el 2026-03-31 y abr–sep es la réplica (HOLDOUT-A3/A4): el
  PREFLIGHT de la campaña lo rechaza si no. `holdout.desde` no puede reusar sesiones consumidas (`docs/research/HOLDOUT_VENTANAS.jsonl`).
- **Reglas congeladas:** desde PREFLIGHT las compuertas leen la copia de `seleccion`, `integridad`, `topes` y `holdout` guardada en
  el estado; cambiar el JSON después no cambia la regla (sólo `holdout.desde` puede moverse hacia adelante). Cambiar familia,
  experimento, señal, ejecución o períodos bloquea la campaña: se abre otra con otro `cid`.

- **`sensor`** es dónde se calcula la señal y **`ejecucion`** dónde se opera.
- **Valores posibles:** cualquier futuro del release (`NQ`, `ES`, `GC`, …) o spot de Dukascopy (`DK:<SÍMBOLO>`).
- **Activos sin costo medido:** si el instrumento de ejecución no tiene costo medido en `edgelab/costos.py` (hoy 6B, 6J y ZB), la
  campaña no se lanza.

**Todo lo demás lo hace `edgelab/research/embudo.py`, un paso por ciclo del agente:**
PREFLIGHT → DESC → INDAGA → INTEGRIDAD (alineación, placebo, latencia) → OOS (un paso del libro de LORD++ de la familia; no
mata) → TOPES (regla declarada) → ACTA (regla congelada antes de mirar) → CONTEO (cuenta operaciones del holdout sin ver P&L) →
HOLDOUT (primeras N, un paso de LORD++) → CONFIRMADA / REFUTADA / SIN_POTENCIA.

En cada etapa, el embudo también:
- registra las pruebas en el contador global antes de lanzar;
- escribe su línea en `MEDIDO.md` y su estado.

| pieza | dónde |
|---|---|
| Kaggle: arma el kernel con todas las dependencias, resuelve datasets y fricción del activo, lanza y trae | `edgelab/research/embudo_runners.KaggleRunner` + `tools/kaggle_grilla/embudo_main.py` |
| Holdout con datos sellados de la máquina | `embudo_runners.LocalRunner` + `fuentes_ticks.bloques_spot_sellado` / `bloques_nq_sellado` |
| Datos nuevos de Dukascopy, sin JForex | `tools/dukascopy_descarga.py`, timer `edgelab-datos-dukascopy` |
| Señal en un activo, ejecución en otro | `grilla_generica.simular_ops(cx_ej=...)` (oráculo: igual a U1-CRUZADO validado) |
| Controles estándar | `edgelab/research/controles.py` |
| Libro de LORD++ por familia | `edgelab/funnel/libro_lord.py` |
| Densidad del feed y régimen por mes | etapa E0 (`etapas.densidad`) |

**Qué queda humano a propósito:**
- **Cambiar las reglas del embudo:** un sistema que afloja sus propios filtros fabrica falsos positivos.
- **Habilitar dinero real:** el embudo termina en CONFIRMADA; operar con dinero real es un interruptor de Nico.
- **Datos de futuros forward en el Debian:** necesitan un feed (Rithmic o Databento). Mientras tanto, si el P&L en el futuro y en el
  spot se verificó equivalente (como en U1-CRUZADO), el forward se decide sobre Dukascopy.

## 9. Creatividad y escala (2026-10-24)
Cómo elegir familias nuevas y correr más variantes por hora sin aflojar nada: `docs/research/agente/PLAYBOOK_CREATIVIDAD_Y_ESCALA_20261024.md`
(skill `.claude/skills/edgelab-barridos-creativos/`).
- **Gramática de hipótesis** (`edgelab/research/agente/gramatica.py`): 8 ejes, cobertura de lo medido, cartas sin mirar P&L.
- **Régimen como perilla** (`edgelab/research/agente/regimen.py`): 7 variables causales; se cuentan solas en `n_celdas`.
- **`niveles_lote`** opcional en un experimento: el preflight exige que sea idéntico a `niveles`.
- **Romano-Wolf** sin tensor denso por réplica (pares sesión × celda + producto matricial; oráculo en
  `tests/research/test_grilla_eficiencia.py`); benchmark `tools/bench_grilla.py`.


## Diseño: celdas evaluables (2026-10-25)
Una celda con menos de `MIN_OPS` (30) operaciones no puede rechazar nunca: no es una prueba, es una perilla vacía. En EXPZ el 96 % de las
233.280 celdas no llegó a 30 (33.480 operaciones en total) y en U1-INDAGA el 98 %. Antes de lanzar una grilla, estimar con el E0
(target-free) cuántas operaciones tendrá cada celda y preferir menos perillas por evento a más celdas vacías. El linaje hereda sólo las
evaluables (`docs/research/EVALUABLES.jsonl`, D6), pero una grilla con la mayoría de las celdas vacías igual pierde potencia: la señal
real queda repartida en celdas chicas que no llegan al tamiz.
