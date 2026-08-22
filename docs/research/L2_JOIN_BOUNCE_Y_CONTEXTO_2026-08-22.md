# L2 junio: semantica, falla de join con ticks, bounce y estructura para contexto

**Fecha**: 2026-08-22 · **Autor**: pasada GPT (chat Notion, sandbox) · **Rama**: `foundation/f0b-compatibility-probe`
**Clase de medicion**: estructura de datos. **No se midieron outcomes, MFE/MAE, P&L ni retornos.**
Los archivos de agosto (holdout gastado) no se subieron ni se tocaron. Datos usados:
`GC 08-26.Last.txt` + parquets L2 `20260621`–`20260626`.

---

## 0. Procedencia (M0)

- `GC 08-26.Last.txt`: sha256 `56f7d1c449ad7f823aea8a9b79a128d0efdfad759e697bf9c23566519c4ff014`,
  coincide con el handoff; **1.081.633** lineas exactas; serie monotona no-decreciente.
- Cubre 24-jun → 20-jul con huecos (27-28 jun; 3-6 jul parcial; 7-15 jul ausente).
  Ventana discovery 24–30 jun: **538.572 ticks** (24: 144.994 · 25: 115.133 · 26: 93.681 ·
  29: 85.396 · 30: 99.368).
- Formato: `yyyyMMdd HHmmss fffffff;last;bid;ask;volume`; subsegundo en unidades de 100 ns.
  **Trae bid/ask por print**: habilita midquote sin L2.
- Parquets leidos con decoder propio (el sandbox no tiene pyarrow ni red): Thrift compact +
  ZSTD via libzstd. Metadata escritor: parquet-cpp-arrow v22.

## 1. Semantica L2 medida

| columna | tipo fisico | contenido observado |
|---|---|---|
| `record_type` | string | `L1` / `L2` |
| `market_data_type` | int32 | 0..8 |
| `timestamp` | string | `yyyyMMddHHmmss` |
| `subsecond` | int64 | 0..9.956.928 → unidades de 100 ns (misma unidad que el tick file) |
| `operation` | int32 nullable | {0,1,2}; NULL solo en filas L1 |
| `position` | int32 nullable | 0..10; NULL solo en filas L1 |
| `market_maker` | string | siempre vacio |
| `price` | double | precio real; 0.0 en filas de stats |
| `volume` | int64 | ver lecturas |

Dominios medidos (250k filas del 21-jun + 3M del 24-jun). Se rotula lo inferido:

- **L2** (~75 % de las filas): mdt ∈ {0,1}, operation ∈ {0,1,2}, position 0..10 →
  actualizaciones de libro por nivel (alta/cambio/baja), MBP de 11 posiciones. *(inferido del
  dominio, no de documentacion del feed)*
- **L1**, mdt ∈ {0,1}: sin operation ni position; precio real; size p50 = 1 → top of book
  bid/ask. GC con 1–5 contratos en top es plausible. *(inferido)*
- **L1**, mdt = 2: precio + vol = 1. **310 filas en 3M del 24-jun (0,01 %)**. Si fuera la
  clase "trade", habria ~60k en esa ventana, no 310. *(la identificacion de clase es
  hipotesis; el conteo es medido)*
- **L1**, mdt 5: volumen monotono creciente dentro del mismo instante → volumen acumulado de
  sesion. mdt 8: ~43.314 → interes abierto. mdt 3/4/6/7: precios sueltos con vol 0 → stats de
  sesion. *(inferido)*

**Punto clave**: no hay evidencia de que este L2 traiga el stream de trades en volumen.

## 2. El join 3/20.486: reproducido y diagnosticado

24-jun. Ticks: 144.994 prints (03:00:00–23:59:59 UTC). L2: 12 row groups = 3.000.000 filas,
01:00:00–10:00:04 UTC. Ventana de solape: **26.701 prints** (03:00–10:00 UTC). Match por
(timestamp_100ns, precio) con barrido de offset ±8 h:

| criterio | mejor offset | hits | tasa sobre solape |
|---|---|---|---|
| exacto ts+precio, todo el L2 | +4 h | **10** | **0,04 %** |
| mismo segundo + precio (ignora subsec) | +4 h | **330** | **1,2 %** |
| solo filas L1 (quotes) | +4 h / −3 h | 3–7 | ~0 |

**Conclusion medida**: la falla no es de zona horaria ni de unidad de subsegundo (ambos feeds
usan 100 ns; el mejor offset apenas junta ruido). La causa estructural: **este L2 no contiene
el stream de trades que genero el tick file**, o lo contiene con semantica de timestamp
incompatible (event time vs receipt time). Con cualquiera de las dos, no hay emparejamiento
que cierre: no se puede pegar contexto L2 a los eventos del tick file con estos archivos.

Lo que SI habilita el L2 por si solo, sin join:

- **OFI (Cont–Kukanov–Stoikov)**: computable del libro: altas/bajas/cambios L2 mas depleciones
  de cola L1. No necesita el tick file.
- **Profundidad en top**: distribucion de sizes L1. Computable; **no medida hoy**.
- Lo que queda bloqueado: cruzar OFI/profundidad con las cubetas de 25 ticks del tick file.
  Caminos posibles: reconstruir trades desde depleciones de cola L1, o conseguir el feed L2
  con trades. **No medido.**

## 3. Bounce: dPx con last trade vs midquote (medido, discovery 24–30 jun)

21.542 cubetas autocortadas de 25 ticks, tick file solo (usa el bid/ask por print):

| metrica | last trade | midquote |
|---|---|---|
| \|dPx\| p50 | 7,0 | 6,5 |
| \|dPx\| media | 8,13 | 7,80 |
| dPx == 0 | 4,25 % | 2,24 % |

Diferencia por cubeta |dPx_last − dPx_mid|: **p50 = 2,5 · media = 2,62 · p90 = 5,5 · p99 = 9,0 ·
max = 67,5 ticks**. En **7,6 %** de las cubetas el signo de dPx cambia entre ambas mediciones.

Con denominador `1 + |dPx|` y escala mediana de 7 ticks, 2,5 ticks de ruido mediano es ~35 %
de la escala. **Medido: dPx debe ser midquote.** En NT8 es barato: la subserie de 1 tick ya
expone bid/ask (se usa para clasificar agresor); hay que registrar el mid al abrir y al cerrar
la cubeta.

## 4. Estructura para parametrizar por horario y contexto (pedido de Nico)

Pedido: que la estructura del indicador permita determinar **despues**, en EdgeLab, en que
horarios y contextos funciona mejor y con que parametros.

Diseno propuesto para v1.1 (**no implementado aca**: el acta multimodelo no cerro; falta la
pasada Kimi y la sintesis):

1. **El indicador exporta; EdgeLab decide.** v1.0 ya lo hace en lo central: `TRAP` se exporta
   siempre que hay geometria, con `a_score`, `a_thr`, `a_pass` y los `run_*`; `q`,
   `MinStackedRows`, `MinTrapFrac` y `RequireFlowSideMatch` se barren **offline por contexto**
   sin re-correr NT8. Mantener.
2. **Nada que defina el evento como constante.** Ya cumplido en v1.0 (todo lo que cambia el
   evento es NinjaScriptProperty). Queda como regla de contrato permanente.
3. **Claves de contexto que faltan en el export de v1.0** (cerrar en v1.1):
   - `t_start` de la cubeta: hoy solo se exporta el timestamp del ultimo tick. Sin el rango
     [t0, t1], la cubeta que cruza la apertura (08:30 ET) no se puede asignar a un regimen.
   - `n_ticks` y `duration_ms` por cubeta (contexto de actividad; hoy `n_ticks` solo esta en
     `BARRA_PROCESADA`, no en `TRAP`).
   - `bid_close`, `ask_close`, `spread_close`: contexto de liquidez y habilita §3.
   - `trade_date` CME explicito: la sesion no es el dia calendario; hoy habria que inferirlo.
   - Todo se computa dentro de la cubeta → causal por construccion.
4. **Lo que no es barrible offline** (declararlo para que EdgeLab no lo descubra tarde):
   `TapeWindowTicks` y `TicksPerRow` (cambian la particion), `ScoreMode` e `ImbalanceMode`
   (cambian el calculo). Cada valor exige su propia corrida. El barrido offline cubre solo la
   capa de seleccion.
5. **Nada de logica de contexto adentro del indicador** (no un parametro "SoloRTH"): cada
   hipotesis de horario exigiria recompilar y esconderia la seleccion en el codigo. El patron
   correcto: export rico → EdgeLab etiqueta contexto (hora del dia, dia de la semana, volumen
   relativo con baseline causal, spread, volatilidad rolling, calendario macro) → **cada celda
   contexto × parametros es un trial** del presupuesto de multiplicidad.
6. Gobernanza: que la estructura permita el barrido **no autoriza** el barrido libre.
   Contextos y grillas se pre-registran antes de mirar outcomes; lo demas se etiqueta
   exploratorio.

## 5. Artefactos del sandbox

- `pqmeta.py`, `pqread.py`: decoder Parquet minimo sin dependencias (Thrift compact +
  ZSTD/libzstd). Suficiente para estos archivos (dict-encoding + ZSTD).
- `out/l2_probe_20260621.json`, `out/join2_20260624.json`, `out/bounce_jun.json`,
  `out/ticks_gc0826.npz`.
- Pendiente y declarado **no medido**: distribucion de profundidad L1; TI vs OFI por cubeta
  (bloqueado por §2); confirmacion de la semantica de `market_data_type` contra documentacion
  del feed.
