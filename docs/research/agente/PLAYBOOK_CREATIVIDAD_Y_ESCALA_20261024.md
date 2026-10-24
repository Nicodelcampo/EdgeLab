# Playbook del agente del Debian: más ideas distintas, más variantes por hora, mismo rigor

Estado: PROPUESTA (2026-10-24; pasa a VIGENTE cuando Nico mergea el PR)
Fecha: 2026-10-24
Familia / módulo: research (grilla genérica, embudo, perímetro del agente)
North Star: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Procedencia: rama `claude/project-thread-dzozxn`, montada sobre las decisiones de validación del 2026-10-24 (PR #133 sobre #130)

Pedido de Nico (2026-10-24): «enfocate en maximizar la creatividad del agente del debian, derivado del abanico de posibilidades
a mano que permiten justamente este proceso creativo (con rigurosidad) …, maximizar las variantes probadas, maximizar la
eficiencia». Y sobre el OOS: «algunas estrategias funcionan por régimen, y eso no significa que no ganen plata ahora».

Este documento no cambia ninguna regla de validación. Las reglas están en `CLAUDE.md`, `docs/research/GUIA_GRILLA_MASIVA.md`
y `docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md`. Acá se explica cómo moverse rápido dentro de ellas.

**Justificación económica** (de este playbook): el cuello de botella del proyecto no es el filtro (tamiz, réplica y holdout ya
matan lo falso), sino la cantidad de ideas *distintas* que llegan al filtro con potencia. Con 0 edges promovidos, cada familia
nueva y bien diseñada vale más que mil variantes de la misma idea, porque las variantes de un mismo linaje heredan su
multiplicidad y las ideas nuevas no.
**Cómo podría refutarse:** si en las próximas 4 semanas las campañas que salen de cartas de la gramática no llegan a réplica con
más frecuencia que las que salen de variar la idea viva (con la misma cantidad de pruebas), la gramática no aporta y se retira.

---

## 1. El abanico a mano (inventario verificado el 2026-10-24)

| recurso | qué hay | dónde |
|---|---|---|
| **Ticks de futuros** | release `liquid_tick_v1`: 14 activos (ES, NQ, YM, RTY, MES, MNQ, MYM, GC, MGC, 6E, 6B, 6J, MBT, ZB), jul/ago-2025 → sep-2026, 1.395 M de filas | Kaggle privado `nicolasbuttaro/edgelab-liquid-ticks-20261014`; lector `edgelab/research/fuentes_ticks.py` |
| **Spot / CFD** | Dukascopy: USATECH, USA500, USA30, XAUUSD, EURUSD, GBPUSD, USDJPY, **desde 2023** (sirve de OOS largo) | `fuentes_ticks.bloques_dukascopy`, descargador `tools/dukascopy_descarga.py` |
| **Holdout** | sellado desde la sesión del 2026-10-01 (ventanas consumidas en `docs/research/HOLDOUT_VENTANAS.jsonl`) | sólo por acta (`edgelab/autopilot/holdout_apertura.py`) |
| **Indicadores con paridad** | LUX-IMB, aVolClusterPOI, aVolZonePOI2, VolTicksDef, HFTZonesNQ, HFTZones2, VolTicksPOC2 (PASS); BigTrap2 (con caveat) | `config/autopilot/indicadores.json` (vale en el instrumento y la resolución de su evidencia) |
| **Indicadores propios** | cualquiera causal, como `NATIVO_AGENTE` | `config/autopilot/grillas/indicadores_agente.json` + `indicadores.causal` |
| **Primitivas de precio** | expansión ≥ R·ATR, zonas y áreas, perfil de volumen por minuto y precio, VWAP | `areas_expansion.py`, `expansion_zonas.py`, `u1_indaga.py` (copiar el patrón) |
| **Régimen (nuevo)** | 7 variables causales listas como perillas | `edgelab/research/agente/regimen.py` |
| **Gramática (nueva)** | 8 ejes, 3,2 M de combinaciones, cobertura de lo ya medido | `edgelab/research/agente/gramatica.py` |
| **Simulador** | llenado declarado por operación (cierre, límite, tick siguiente), ambigüedad M1 resuelta con ticks, stop con hueco, tope de pérdida estructural, señal en un activo y ejecución en otro, retraso | `grilla_generica.simular_ops` |
| **Embudo** | PREFLIGHT → DESC → INDAGA → INTEGRIDAD → OOS → TOPES → ACTA → CONTEO → HOLDOUT | `edgelab/research/embudo.py`, campaña JSON con `"embudo": true` |
| **Costos** | fricción canónica por viaje (tabla abajo); 6B, 6J y ZB sin costo medido: no se lanzan | `edgelab/costos.py` |
| **Cómputo** | kernels de Kaggle autocontenidos (CPU, ~30 GB de RAM); el Debian orquesta | `embudo_runners.KaggleRunner` |

**Movimiento mínimo útil** (regla de relevancia: objetivo mediano ≥ 3 × fricción canónica, escenario base, `edgelab/costos.py`):

| instrumento | fricción por viaje | objetivo mediano mínimo |
|---|---:|---:|
| ES | 0,89 pts (3,55 ticks) | 2,7 pts |
| NQ | 1,55 pts (6,18 ticks) | 4,6 pts |
| YM | 5,05 pts | 15 pts |
| RTY | 0,44 pts | 1,3 pts |
| GC | 0,61 USD | 1,8 USD |
| 6E | 0,00021 | 0,00063 |
| MBT | 58,5 USD | 175 USD |

Las micros (MES, MNQ, MYM, MGC) tienen más fricción relativa que sus grandes: sirven para tamaño, no para descubrir.

---

## 2. Creatividad sistemática: de la gramática a una familia

### 2.1 La gramática
`edgelab/research/agente/gramatica.py` define el espacio de estrategias que se pueden construir con lo de arriba, en 8 ejes:

| eje | valores |
|---|---|
| objeto | 7 indicadores con paridad + 7 primitivas (expansión, rango de apertura, extremos previos, VWAP, perfil de volumen, franja horaria, divergencia entre activos) |
| evento | creación, aproximación, primer toque, toque n, invalidación, expiración, confluencia, **estado continuo** |
| lectura | continuación, reversión, ruptura, trampa, imán |
| régimen | ninguno + 7 variables de `regimen.py` |
| entrada | E1C, E1A, límite en retroceso, espera de volumen, confirmación |
| salida | estructural, múltiplo de R, tiempo, trailing |
| horizonte | minutos, intradía, sesión, multisesión |
| instrumento | 7 futuros con costo + 2 cruces (CFD → NQ, oro spot → GC) |

`MEDIDO` (en el mismo archivo) ubica en esas coordenadas lo que ya se midió: BigTrap2 imán y soporte (muertas), HFTZones en ES
(sin potencia), U1 y AREAS-EXP-1, EXPANSION_ZONAS, LUXIMB, AVZP2, barridos horarios, ORB, aVolClusterPOI EF0.

```
python -m edgelab.research.agente.gramatica 8 20261024        # 8 cartas, semilla del día
```

Cada **carta** es una familia candidata: lejos de lo medido (`novedad`), distinta de las otras cartas (≥ 3 ejes), con peso por
horizonte (macro antes que micro) y por paridad (un indicador fuera del instrumento de su evidencia pide su oráculo). Sale con los
campos que las reglas piden antes de correr: justificación económica y cómo podría refutarse (`COMPLETAR`), el espacio de eventos
enumerado (regla de población), el régimen declarado ex ante, la regla de fricción y los controles.

**Lo que hace riguroso este paso:** la elección entre cartas no mira ningún P&L, sólo coordenadas. Una carta no es una prueba:
no consume multiplicidad hasta que su campaña se registra en el contador global. El proponente del autopilot recibe 6 cartas por
ciclo (`cartas_gramatica` en el paquete) y tiene dos lentes nuevas: `hueco_gramatica` y `regimen_declarado`.

### 2.2 De carta a familia (orden)
1. **Mecanismo antes que patrón.** Si no se puede escribir quién pierde plata del otro lado, la carta se descarta (y se dice).
2. **Enumerar la población:** las 8 familias de evento, cuál se mide y por qué; separar evento de estado (el estado tiene más
   potencia: una observación por vela, no por toque).
3. **Perillas = las variantes.** Una carta define la familia; dentro, las perillas dan los millones de variantes: cortes desde
   cuantiles del E0, valores geométricos (1, 2, 4, 8), ejecuciones (entrada × objetivo × stop). Todas se cuentan en `n_celdas`.
4. **Módulo** en `edgelab/research/agente/<x>.py` con la interfaz de la guía §6, tests en `tests/agente/test_<x>.py`
   (`test_control_ruido`, `test_control_plantado`, `test_causal`; `test_oraculo` si usa numba).
5. **Preflight** (`python -m edgelab.research.preflight edgelab.research.agente.<x>`), **linaje** declarado en
   `docs/research/LINAJES.jsonl`, **campaña** en `config/autopilot/grillas/campanas/` con `"embudo": true` (la aplica una persona:
   es `PROPUESTA`).

### 2.3 Diversidad que conviene (por qué las ideas nuevas son más baratas)
Desde el 2026-10-24 una familia hereda en bruto las pruebas de sus padres (`q_linaje = q · (m + N_heredado) / m`). Una variante
de U1 paga los 19,4 M de pruebas de su linaje; una familia de una carta nueva arranca de cero. **A igual cómputo, una familia
genuinamente distinta tiene mucha más chance de pasar el tamiz que la variante número mil de la idea viva.** Esto no es un
truco: es exactamente lo que la herencia quiere medir. Declarar «nueva» una variante disfrazada para no heredar es fraude de
multiplicidad; la regla es que si comparte mecanismo y población con una familia medida, la declara como padre.

Fuentes de diversidad que siguen sin explorar casi nada (según `MEDIDO`):
- **estado continuo** en vez de evento (distancia a zonas activas, cantidad activa, posición en el perfil);
- **objetos de precio sin indicador**: extremos de la sesión anterior, POC/nodos del perfil previo, VWAP y sus bandas;
- **otros instrumentos**: GC, 6E, RTY, YM tienen costo medido y casi ninguna familia propia;
- **cruces**: señal en el spot largo (desde 2023), ejecución en el futuro (oro spot → GC es el par natural de U1-CRUZADO);
- **salidas por tiempo y trailing** frente a objetivos fijos;
- **horizonte de sesión y multisesión** (la fricción pesa menos).

---

## 3. Régimen: las dos formas válidas

Matiz de Nico: una estrategia que funciona ahora y no en 2023 puede ser buena. La condición es que el régimen se declare
**antes** de mirar el período que lo juzga. Hay dos formas y se pueden combinar:

| | régimen como **estado** (perilla) | régimen por **calendario** (campaña) |
|---|---|---|
| qué es | una variable causal en la vela de decisión: volatilidad relativa, eficiencia, tendencia del día, actividad, hora, día | «el régimen vigente empieza el AAAAMMDD», con su definición escrita |
| dónde | `regimen.VARIABLES_REGIMEN[...]` agregada a `VARIABLES` del experimento | `regimen.definicion` y `regimen.actual_desde` en el JSON de la campaña, antes del PREFLIGHT |
| multiplicidad | entra sola en `n_celdas` (cada nivel multiplica las celdas) | no agrega celdas |
| OOS | la celda congelada incluye el nivel: el OOS evalúa la señal **sólo con el régimen presente**; si en 2023 casi no aparece, da pocas operaciones (sin potencia, no refuta) | un OOS en contra que cae entero antes de `actual_desde` queda `EN_CONTRA_OTRO_REGIMEN` (sigue viva); dentro del régimen actual, con potencia, mata |
| operable en vivo | sí: se detecta en tiempo real | sólo si además hay una regla de detección (si no, es una apuesta a que el régimen sigue) |

Preferir el **estado**: es detectable en vivo, se valida solo en cada período y no depende de que el régimen siga. El calendario
sirve cuando el cambio es estructural y fechable (un cambio de contrato, de horario, de participantes).

Qué no vale: mirar el P&L por año y declarar después «el régimen empezó en 2025». Elegir la ventana después de verla es data
snooping, y la decisión D2 lo bloquea (la campaña no se puede editar después del PREFLIGHT).

`regimen.py` usa sólo velas ≤ k y sesiones cerradas (`tests/agente/test_regimen.py::test_causal`). Los bloques horarios son UTC
fijos (no ajustan horario de verano): si la hipótesis depende de la apertura de NY exacta, declararlo y usar una variable propia.

---

## 4. Escala: más variantes por hora

### 4.1 Qué cuesta qué (después de las mejoras de este PR)
| paso | costo | cómo abaratarlo |
|---|---|---|
| leer ticks y armar M1 (`contexto_m1`) | proporcional a ticks; minutos por activo-año | un kernel por fuente y período; todas las variantes de la familia en el mismo kernel (perillas, no kernels) |
| `disparos` | lo escribe el experimento | numba en lote por evento (nunca por operación en Python); la compilación de numba (~5–20 s) se paga una vez por kernel |
| `niveles` | antes: una llamada Python por disparo × ejecución | **`niveles_lote`** (nuevo, opcional): todos los disparos de una ejecución a la vez. ×6 medido; el preflight exige que sea idéntico a `niveles` |
| simulación | una vez por (disparo, ejecución), numba | las perillas que FILTRAN no se simulan: sólo las ejecuciones multiplican la simulación |
| tensor + estadísticas | O(operaciones + celdas) | p del tamiz con erf vectorizado (antes `np.vectorize`) |
| **Romano-Wolf** (B = 1000 desde hoy) | antes: B tensores densos completos, O(B × celdas × perillas) | **nuevo:** pares (sesión, celda) expandidos una vez a las celdas evaluables + producto matricial por réplica, por bloques, paralelo por sesión. Mismo sorteo y mismo resultado (oráculo) |

### 4.2 Benchmarks (este contenedor, 4 núcleos, Python 3.13; `tools/bench_grilla.py`, datos sintéticos)
| caso | antes | ahora | aceleración |
|---|---:|---:|---:|
| U1-INDAGA sintético (3 M de celdas, 384 evaluables, 25.744 operaciones), Romano-Wolf B = 200 | 32,7 s | 0,07 s | ×500 |
| Forma AREAS-EXP-1 (746 mil celdas, 376 mil evaluables, 2 M de operaciones uniformes), B = 200 | ~89 s | 13,5 s | ×7 |
| ídem, B = 1000 (el nuevo valor por defecto) | ~443 s | 26,1 s | ×17 |
| `niveles` 100 mil disparos × 8 ejecuciones (700 mil operaciones) | 1,0 s | 0,16 s | ×6 |

«Antes» con B grande es extrapolación lineal de 3 réplicas medidas (la implementación anterior es lineal en B; se informa así).
Romano-Wolf corre dos veces por DESC (canal total y reciente). En el caso disperso típico de un experimento del agente (muchas
celdas vacías) la ganancia es de dos órdenes de magnitud; en el denso, un orden. Memoria: la matriz bootstrap se guarda una sola
vez (B × evaluables, float32) si entra en `EDGELAB_RW_MEMORIA_GB` (2 por defecto); si no, se recalcula por bloques en cada paso
del step-down, con el mismo resultado. `EDGELAB_RW_BLOQUE_MB` (1024) acota cada bloque. Esto también resuelve el pico de 3 × M
que señaló la auditoría del embudo.

Las corridas ya lanzadas con el código anterior siguen siendo válidas: el cambio es de rendimiento, con oráculo que da el mismo
resultado (`tests/research/test_grilla_eficiencia.py`). `preflight.codigo_vigente` las marcará como «código cambió»; la
revisión es esta: no cambió la medición.

### 4.3 Diseño de perillas que rinde
- **Las que filtran son casi gratis**; las de ejecución multiplican la simulación. Más filtros, pocas ejecuciones bien distintas.
- **Valores geométricos y rangos amplios** (1, 2, 4, 8): variantes distintas de verdad, no ruido alrededor de un punto.
- **Ninguna perilla muerta**: `ejecuciones_equivalentes` y el preflight las cazan; una perilla muerta se rediseña.
- **Poda temprana sin mirar desenlaces**: el E0 da conteos por nivel. Si una celda no puede llegar a 30 operaciones y 20 sesiones
  en el período, no aporta potencia: se ensanchan los cortes antes del DESC (el E0 es target-free; los cortes salen de ahí).
- **Una sola corrida por fuente y período**: todas las variantes van como perillas del mismo kernel; separar en kernels sólo
  cambia el costo, no la multiplicidad.
- **El canal `reciente`** (3 meses declarados) ya existe: no hace falta una campaña aparte para «lo de ahora».

---

## 5. Lo que no se negocia (lista corta para el agente)
1. Pre-registro committeado y prueba registrada en el contador global **antes** de correr; si la grilla cambia, se registra de nuevo.
2. Linaje declarado antes del DESC; la herencia es en bruto.
3. FDR q 0,10 del canal como compuerta dura de DESC; Romano-Wolf es diagnóstico.
4. Costos sólo de `edgelab/costos.py`; objetivo mediano ≥ 3 × fricción.
5. Holdout: una apertura por familia, por acta, con la regla congelada; nunca para elegir.
6. Una corrida lanzada con código que después se corrigió (en la medición) no se mira: se descarta y se relanza.
7. Un nulo sin potencia no mata; toda muerte tiene alcance preciso.
8. Las reglas del embudo, los gates y el dinero real son de Nico.

---

## 6. Ciclo sugerido para el agente (Opus 5.5, en el Debian)
1. `tools/estado.py`, árbol limpio, `git pull` de la rama viva.
2. Leer el estado de las campañas (`autopilot_runs/embudo/*/MEDIDO.md`) y el tablero.
3. `python -m edgelab.research.agente.gramatica 8 <AAAAMMDD>`: elegir 1 o 2 cartas con mecanismo plausible (decir por qué las
   otras no).
4. Spec corta (justificación, refutación, población, régimen, perillas con conteo) → módulo → tests → preflight.
5. Linaje, registro, campaña JSON (PR para la persona). Mientras espera, la siguiente carta.
6. Al cerrar cada campaña: actualizar `MEDIDO` de la gramática (una línea) para que no se reproponga.

Meta de throughput razonable con la cuota de Kaggle: 2 familias nuevas por semana, cada una con 10⁵–10⁶ celdas, más las
etapas del embudo de las vivas. Lo que limita es la cantidad de familias con mecanismo, no el cómputo.

---

Aporte al referente: más familias distintas y con potencia llegan al filtro por la misma cuota (y Romano-Wolf con B = 1000 deja de
ser el paso caro), sin aflojar ninguna regla; el régimen entra como perilla declarada, que es la forma de buscar edges actuales sin
data snooping.
