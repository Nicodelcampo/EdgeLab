# OU-1 — Diagnóstico de reversión (Ornstein-Uhlenbeck): pre-registro

Escrito el 2026-10-12 **antes de correr nada sobre datos reales**. Script: `tools/ou1_study.py` (probado solo con series sintéticas). Es un estudio de **información**: no genera ni valida estrategias, no toca el holdout (fechas de sesión ≥ 2026-10-01).

## 1. Qué es y qué problema evita
Proceso OU: `dX = θ(μ − X)dt + σ dW`; vida media = ln2/θ. En discreto, `ΔX_t = a + b·X_{t-1} + ε` con `b = −θ·dt` (b < 0 ⇒ reversión).

**Defecto del método del reel (ADF/Hurst sobre X = ln P − SMA_N(ln P)):** esa X es estacionaria *por construcción*, aunque el precio sea una caminata aleatoria. En la prueba sintética (caminata aleatoria pura) el `b` crudo da −0,03 a −0,42, así que ADF rechazaría siempre. Por eso aquí **no se usa ADF ni Hurst como prueba**; se compara `b` contra un nulo procesado igual.

## 2. Qué análisis previos puede complementar (pregunta de Nico)
| Análisis previo | Relevancia | Qué aportaría OU | ¿Está en este estudio? |
|---|---|---|---|
| Barrido horario de oro: celdas de 15 min tras caída/alza (GC 04:30, 19:30, 04:15 CT) y réplicas H1/H2 | **Alta** | Esas celdas son apuestas de reversión a 15 min; mide si existe esa reversión en esas franjas, antes y después de 2025-07 | **Sí, Parte B** |
| Familias f1 momentum / f5 medias / f4 régimen (GC, ZB, FX, IDX; nada pasó Holm) | **Alta** | Dice a qué escalas hay momentum o reversión por activo; ayuda a interpretar por qué fallaron y a acotar las grillas futuras | **Sí, Parte A** |
| EMA (MGC, EMA T2, estrategias JForex HD_ES) | Media | Una EMA sigue tendencia; la vida media/escala indica si ese horizonte tiene momentum o reversión. Solo barras de tiempo (las barras de ticks no son equivalentes entre spot y futuro) | Parte A como contexto |
| GEX-1/1b (amplitud y autocorrelación según gamma) | Media-baja | `ac1` ya es casi el mismo objeto que `b` a 1 barra; las ac1 no salieron significativas | No; extensión posible barata reutilizando las métricas de sesión |
| AVCL-VOL-1 (clusters de volumen → RV futura, no direccional) | Baja hoy | Sirve en la etapa 2 direccional: ¿el movimiento posterior a un cluster revierte o continúa a 50-1.000 ticks? | No |
| Equivalencia spot/futuro, catálogo, resolver | Ninguna | — | — |

## 3. Datos
- Futuros (M1 de `edgelab_data.load_m1`, sesiones aprobadas 2025-07-01 → 2026-09-30): ES, NQ, YM, GC, ZB, 6E, 6J. Sesiones sin fuente se omiten y se declaran.
- Spot (Dukascopy, solo información, precio medio bid/ask): oro 2022-07-01 → 2025-06-30; USA500 2018-01-01 → 2025-06-30.
- Fecha de sesión CME (17:00–16:00 CT, +7 h). Precio = cierre del último minuto de cada barra.

## 4. Parte A — reversión por activo × escala (36 pruebas, Holm 36)
- 9 series × 4 celdas (barra, ventana SMA): (5 min, 1 h), (5, 4 h), (15, 4 h), (60, 4 h).
- `X_t = ln P_t − media de las últimas N barras (incluida la actual)`, N = ventana/barra; solo con ventana completa dentro de la misma sesión. `b` = pendiente agrupada de `X_{t+1} − X_t` sobre `X_t`.
- **Nulo:** signo aleatorio independiente por retorno de barra (misma magnitud, sin dependencia serial), 5.000 sorteos, semilla 20261012, **bilateral**. Estadístico `z = (b − media_nulo)/sd_nulo`; z < 0 reversión, z > 0 momentum.
- Descriptivo (no es prueba): vida media implícita en minutos = ln2/(−ln(1+b))·barra cuando −1 < b < 0.
- **Verificación previa (sintética, 300 sesiones):** caminata aleatoria ⇒ z entre 0,5 y 1,6 (p 0,12–0,60); OU con θ=0,01 por barra ⇒ z entre −19 y −39.

## 5. Parte B — mecanismo en GC (6 pruebas, Holm 6, familia aparte)
- Franjas CT 04:30, 19:30 y 04:15; fuentes: oro spot 2022-07→2025-06 y GC 2025-07→2026-09.
- `corr( r15 previo, r15 siguiente )` entre sesiones, con r15 previo = ln(P_t / P_{t−15 min}), siguiente = ln(P_{t+15 min} / P_t), P = apertura del minuto indicado. **Hipótesis unilateral: correlación negativa** (reversión; es el supuesto de las celdas largo-tras-caída y corto-tras-alza). Nulo: signo aleatorio sobre r siguiente, 20.000 sorteos.
- Franjas con menos de 100 sesiones válidas: no evaluable.

## 6. Reglas de decisión
1. **Parte A:** hay estructura a esa escala si Holm 36 ≤ 0,05. Se informa el signo (reversión o momentum).
2. **OU «sirve para EdgeLab»** solo si ≥ 1 celda de Parte A de un futuro pasa Holm 36 **y** su hermano spot (GC↔oro, ES↔USA500, cuando existe) tiene el mismo signo con p nominal < 0,05. Si no, **no hay apoyo para usar OU como filtro o régimen** y se archiva.
3. **Parte B:** una franja «tiene reversión a 15 min» si Holm 6 ≤ 0,05 en esa fuente. Resultado esperado y a informar: si el spot 2022-2025 no la muestra, es coherente con que H1/H2 no replicaron.
4. Ningún resultado de este estudio habilita por sí solo una estrategia; cualquier regla derivada requiere su propio pre-registro y embudo.

## 7. Registro
42 pruebas (36 + 6). Se registran en el contador global antes de correr (`tools/registro_global.py`). Resultado completo y negativos se publican tal cual.
