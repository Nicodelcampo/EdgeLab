# HANDOFF 2026-08-21 noche — sandbox auditor → Claude local

> **Punto de entrada para continuar ESTA línea (GC / BigTrap2 / L2 / SL-TP-BE).**
> El handoff de la mañana (`HANDOFF_2026-08-21_ESTADO_COMPLETO.md`) sigue valiendo
> para HFTZones-ES. **Este lo complementa y lo corrige en un punto: el holdout
> de GC agosto YA se gastó** (H-GC-BT2-1, commit `5814f1f`).
>
> Rama: `foundation/f0b-compatibility-probe`.
> Autor de esta sesión: auditor en Notion sandbox (no la máquina local).
> Nada de lo afirmado abajo depende de recordar el chat.

---

## 0. Qué se estaba haciendo

Nico ve burbujas de BigTrap2 en **GC DEC26, 25 tick**, con `SizeScaling`, y quiere
un edge: al cierre de la vela, SL / TP / BE sobre **ticks crudos**, en **todos**
los tickframes, filtrando por contexto / L2 / otros indicadores.

Eso **no** es H-GC-BT2-1 (carrera ±B sin BE). Son objetos distintos.

---

## 1. Holdout — estado real (corregir el handoff de la mañana)

| ventana | estado |
|---|---|
| Holdout calendario `2026-07-01 → 2026-12-31` | **sigue existiendo** |
| **GC 12-26, 11–21 ago** | **GASTADO** por H-GC-BT2-1 (`5814f1f`), autorizado por Nico |
| **GC 12-26, 17–21 ago** (oráculo v2.5.1 de esta noche) | **también holdout**; se usó para Capa D y «vela siguiente», etiquetado OVERFIT / descriptivo |
| **GC 08-26, 24–30 jun** | **discovery** — único bloque pre-holdout con ticks en esta sesión |
| **GC 08-26, 1–20 jul** | holdout; **no usar para elegir config** |

**Prohibido** coronar SL/TP/BE/frame mirando agosto. Julio 08-26 tampoco.

---

## 2. Identidad de los archivos (no están en git; son locales)

| archivo | sha256 | qué es |
|---|---|---|
| `oracle_events__Tick25.csv` | `e89fed221a4ecaa984ee58494c960671d5a2858d4d8b1840064e91a3e3050a84` | BigTrap2 **v2.5.1** (no 2.5.2), GC DEC26, 17–21 ago, 11.964 TRAPs, 122 ZONE_CREATED, **0 FOOTPRINT_MISMATCH** |
| `GC 12-26.Last.txt` | `dd67cacbc877739f3643235ab89ed4fab358c02c799aa06c274a45f757d581aa` | 683.188 ticks, 17–21 ago |
| `GC 08-26.Last.txt` | `56f7d1c449ad7f823aea8a9b79a128d0efdfad759e697bf9c23566519c4ff014` | 1.081.633 ticks, 24-jun → 20-jul |

**Reloj:** oráculo en ART; ticks en epoch «como UTC». **+3 h = match 100 %** de
`BARRA_PROCESADA` (24.093/24.093). Medido, no inferido.

Params del oráculo v2.5.1: `ticks_per_row=1`, `imbalance_ratio=3`, Diagonal,
AggressiveSide, wick 30, CloseThrough, `tick_size=0.1`.

Las capturas de Nico tenían **`SizeScaling,30`**. El oráculo es la población **sin**
renderer. Son dos conjuntos. `SizeScaling` / `TopPercentFilter` son **forbidden**.

Parquets L2 GC (12 archivos, esquema NT8 crudo
`record_type, market_data_type, timestamp, subsecond, operation, position,
market_maker, price, volume`, ZSTD): junio 21–26 ~37,6 M filas (discovery) +
agosto 16–21 ~34,3 M (holdout). **No commiteados.** Semántica de columnas
**pendiente de intake** (distinto al L2 de ES).

---

## 3. Lo ya medido esta noche (artefactos en este commit)

### 3.1 CF-4 — L2 no filtró H-GC-BT2-1

`docs/research/atlas_bigtrap2_gc.json` (commit `5814f1f`):
`con_estado_de_libro=3`, `sin_l2=5370`, `frac_con_libro=0.0001`.
El commit habla de atlas con libro; el JSON lo desmiente.
`h_gc_bt2_barreras.py` **no lee L2**.

### 3.2 H-GC-BT2-1 (ya en el repo, `5814f1f`)

16/16 celdas primarias `supera_equilibrio=false`. B5 T25: TRAP 48,70 % vs p*=65 %
y control 50,96 %. Holdout gastado para **ese** estimando (carrera ±B, sin BE).

### 3.3 Capa D — overfitting declarado (holdout 17–21 ago)

Artefacto: `docs/research/h_gc_bt2x_path_overfit.json`.

Camino libre 15 min / 2000 ticks, 11.962 TRAPs:

| | MFE p50 | MAE p50 | MFE≥18 | MAE≥9 |
|---|---:|---:|---:|---:|
| todos | 38 | 36 | 74 % | 86 % |
| vol≥30 (n=122) | 40 | 39 | 80 % | 84 % |

**Simétrico.** RR libre p50 ≈ 0,96.

Features PRE (`vol`, `max_ratio`, `n_rows`, `bar_vol`, hora, lado) **idénticas**
entre TP / SL / BE-scratch (regla SL9 TP18 BE+2). No hay filtro causal en esas
columnas.

«Mejor» grilla bruta holdout: SL13 TP30 BE off, EV +0,72 t **sin fricción**.
Con 1,5 t queda negativo. **No elige config.**

### 3.4 Claim «la vela siguiente va contra la absorción»

Artefacto: `docs/research/h_gc_bt2x_next_bar.json`.

11.840 casos, close→close a favor **47,4 %** (50,3 % sin empate). vol≥30: **44,3 %**.
Mediana 0 t. No es continuación. La percepción es selección (`SizeScaling` +
ejemplos ganadores).

### 3.5 Barrido 8 frames × SL/TP/BE — discovery 24–30 jun

Artefacto: `docs/research/h_gc_bt2x_sweep_frames.json`.
Scripts: `diag/tasa_senales/h_gc_bt2x_sweep_frames.py`.

Población: TRAP `vol≥30` al close (no SizeScaling). Kernel sandbox = `process_bar`
de BigTrap2 (Diagonal, ratio=3, wick=30, `ticks_per_row=1`). 538.572 ticks.
960 celdas. **NO ES EDGE.**

| frame | burbujas | mejor celda | wr | EV bruto | EV−1,5 |
|---:|---:|---|---:|---:|---:|
| 5 | 25 | SL21 TP55 BE+1 | 4 % | −0,32 | −1,82 |
| 10 | 24 | SL8 TP34 off | 25 % | +2,50 | +1,00 |
| 15 | 55 | SL5 TP55 off | 20 % | +7,00 | +5,50 |
| **25** | 96 | SL3 TP21 BE+1 | 13 % | +1,59 | **+0,09** |
| 50 | 150 | SL13 TP21 off | 46 % | +2,64 | +1,14 |
| 100 | 331 | SL3 TP55 BE+5 | 7 % | +2,38 | +0,88 |
| 150 | 452 | SL13 TP55 off | 23 % | +2,33 | +0,83 |
| 500 | 691 | SL8 TP55 BE+8 | 10 % | +1,67 | +0,17 |

El top 15 **entero** es frame 15 / TP 55 / n=55 (11 wins). Lotería de 5 días.
`vol≥30` **no escala**: en 500-tick, 691/1081 barras son «burbuja».

Frame 25 (el del gráfico de Nico) ≈ **cero neto**.

---

## 4. Plan vivo (no ejecutar otra cosa)

Detalle: `docs/research/H-GC-BT2-X_PLAN_Y_MEDIDO.md`.

Capa 0 identidad — hecha para DEC26; L2 GC semántica pendiente.
Capa 1 plantilla SL9/TP18/BE+2 sobre **más discovery** — falta N.
Capa 2 familia gestión — no coronar el top del barrido.
Capa 3 params indicador — hace falta kernel del repo o más oráculos.
Capa 4 tickframes — el barrido 3.5 es un probe de 5 días, no la capa.
Capa 5 contextos — después, un filtro, no producto cartesiano.
Capa D overfitting — hecha, no alimenta elección.

**Siguiente movimiento que no es más overfitting:** más días pre-1-jul de GC
(ticks + oráculo o kernel del repo) y un piso `n_burbujas≥200` y `n_sesiones≥10`
antes de mirar EV. Confirmar una celda congelada **una sola vez** en holdout.

---

## 5. Qué NO hacer

- Reabrir H-GC-BT2-1 ni F2.7–F2.10.
- Elegir SL5/TP55/15t como «el edge».
- Filtrar por L2 hasta que el join pegue (CF-4 / P-59).
- Usar `SizeScaling` como población.
- Medir velas como horizonte del trade (el camino es tick).
- Transportar fricción de 6E/ES a GC.
- Asentar P-NN solo en Notion: el board manda (`PENDIENTE.md`).

---

## 6. Board a asentar (texto canónico)

Copiar a `PENDIENTE.md` en el **mismo** commit local si este dump no pudo
reescribir el board entero (archivo enorme). Texto en
`docs/research/BOARD_H-GC-BT2-X_2026-08-21.md`.

- **P-58** — H-GC-BT2-1 gastó holdout GC ago; no reusar para elegir gestión.
- **P-59** — join L2 del atlas GC falló (3/20.486); no filtrar por libro.
- **P-60** — `vol≥30` no escala con tickframe; definir burbuja por frame.

---

## 7. Cómo reproducir

Datos gitignorados (rutas de esta sesión):

```
oracle   oracle_events__Tick25.csv
ticks    GC 12-26.Last.txt
ticks    GC 08-26.Last.txt
```

```
python diag/tasa_senales/h_gc_bt2x_path_overfit.py
python diag/tasa_senales/h_gc_bt2x_next_bar.py
python diag/tasa_senales/h_gc_bt2x_sweep_frames.py
```

Ajustar las constantes `ORACULO` / `TICKS` / `TICKS_PATH` a las rutas locales.

---

**Aporte al referente:** deja medido que lo que se ve en el gráfico (vela siguiente,
excursiones, «mejor» SL/TP) no sobrevive a la población ni a 5 días de discovery
con 960 celdas; el holdout de agosto ya no es bala limpia para esta familia.
