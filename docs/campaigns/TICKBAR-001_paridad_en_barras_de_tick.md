# TICKBAR-001 — Paridad en barras de TICK (desbloqueo de BigTrap2)

> Este documento sirve al referente rector: ver [`../NORTH_STAR.md`](../NORTH_STAR.md)
> (sha256 `21bb3b01a33e2b373859a38ac4615de376a6262f0aa7ced0e8f5dec33b5256a8`).
> **Estado: ABIERTA (diagnóstico), 2026-07-25.**

## 1. Justificación económica (obligatoria)

BigTrap2 es el **segundo candidato a edge** del proyecto y su hipótesis es de
**microestructura**: detecta agresión atrapada leyendo el footprint por nivel de
precio. Esa señal vive en la resolución donde la microestructura es observable —
**velas de tick (10t / 25t)**, no de tiempo. `time:1` fue el laboratorio donde se
verificó la fidelidad del traductor, no el hábitat de la hipótesis.

Hoy `tick:25` da **FAIL con 89,12 % de `FOOTPRINT_MISMATCH`**. Mientras eso siga
así, el edge de BigTrap2 es **inmedible e inmonetizable**: no se puede correr una
campaña de descubrimiento sobre datos que no reproducen lo que el indicador ve en
el chart. TICKBAR-001 **no es deuda técnica: es el acceso al segundo edge.**

## 2. Cómo podría refutarse (obligatoria)

- Si tras clasificar la causa y aplicar el fix el mismatch **no** cae a ~0 %, la
  hipótesis "el desalineamiento es de construcción y no de datos" queda refutada
  y hay que sospechar del **feed** (ticks que NT8 recibe y el parquet F2 no, o
  viceversa) — otra investigación, no un parche.
- Si el fix funciona en `tick:25` pero **no** en `tick:10`, era un parche
  ajustado a `N=25` y se rechaza: la corrección debe ser general.

## 3. Estado de partida (medido)

| bar_spec | `FOOTPRINT_MISMATCH` | barras | tasa | gate |
|---|---:|---:|---:|---|
| `time:1` (O1) | 4 | 15.939 | **0,03 %** | FAIL sólo por el artefacto de 1 ULP (corregido en v2.1; pendiente oráculo v2 / `PRED-001`) |
| `tick:25` (O4) | 26.661 | 29.916 | **89,12 %** | FAIL |

Dato ya establecido que acota el espacio de hipótesis: el offset de numeración de
barras NT8→Python es **constante (7377)** en toda la ventana, con 762 barras
coincidentes ⇒ **las barras de 25 ticks están alineadas**. El problema es el
**contenido** del footprint, no el corte… *o eso parecía con el ruido del
footprint encima*. TICKBAR-001 lo verifica sin suponerlo.

Volumen total desviado sólo **0,94 %** ⇒ mala **asignación** entre barras, no
pérdida de datos.

## 4. Las cuatro hipótesis, con predicción falsable

Cada una predice una **firma distinta y excluyente** en los dos ledgers que
exporta el instrumental de §5.

### H1 — STREAM: NT8 y Python no ven la misma secuencia de trades

*Predicción falsable:* los **digests del stream difieren ANTES de armar barras**.
Concretamente: el digest acumulado sobre `(precio_tick, volumen)` de los primeros
`k` eventos diverge en algún `k`, y el primer índice de divergencia es
identificable. Además `n_eventos` totales difiere, o difiere algún
`(precio, volumen)` en la misma posición.

*Si H1 es cierta*, ninguna corrección de construcción de barras puede arreglar
nada: el problema es de datos (feed, filtros de NT8, o el export F2).

### H2 — BAR BUILDER: mismas secuencias, reglas de corte distintas

*Predicción falsable:* los digests de stream son **idénticos** (H1 descartada),
pero los `sequence_id` de cierre de barra **divergen**, y el **drift crece
monótonamente** a lo largo de la ventana (típico de un desfase de ±1 evento por
barra que se acumula).

Sospechosos concretos: dónde arranca la primera barra de la sesión, cómo se
tratan los timestamps empatados, y si el tick número `N` cierra la barra actual o
abre la siguiente.

### H3 — ATRIBUCIÓN: mismos cortes, tick fronterizo mal acumulado

*Predicción falsable:* los límites de barra son **idénticos** (mismos
`sequence_id` de primero y último evento por barra), y los footprints difieren
**exactamente en ±1 tick en los bordes** — es decir, la diferencia por barra es
un único evento, el primero o el último, y `Σ|Δ|` por barra ≈ el volumen de ese
evento.

Esta es la versión "take/reset en el orden equivocado" del caveat ya declarado en
la guía §11.

### H4 — MIXTA

Se declara **sólo si aparece más de una firma** de las anteriores en la misma
ventana. No es la opción por defecto: exige evidencia de cada firma por separado.

## 5. Instrumental (§B2) — construir ANTES de leer resultados de CAMP-001

- **Exporter NT8**: `nt8/TickBarDiag.cs`, indicador **nuevo**. No se toca
  `BigTrap2.cs`. Vuelca dos ledgers sobre una ventana corta (~100–200 barras de
  25t). Entregado en **CRLF y sin región generada** (lección de HFTZones2).
- **Comparador Python**: `tools/tickbar_diag.py`, clasifica automáticamente en
  `STREAM_MISMATCH` / `BAR_BUILDER_MISMATCH` / `ATTRIBUTION_MISMATCH` /
  `MIXED_MISMATCH`, con un solo comando y salida legible.

## 6. Prohibiciones (§B3)

**PROHIBIDO implementar un fix antes de tener la clasificación.** Arreglar a
ciegas la causa "probable" es exactamente el error que el ULP enseñó a no
repetir: ahí el diagnóstico preciso convirtió 101 diffs en una predicción bit a
bit. Mismo estándar acá.

**PROHIBIDO** normalizar los CR-CR-LF de `BigTrap2.cs` hasta después del oráculo
v2 que valida `PRED-001` (§B5). Después, commit aislado con prueba de contenido
lógico idéntico.

## 7. Cierre pre-registrado (§B4)

1. Causa **clasificada** y documentada con la firma que la identificó.
2. Fix con **predicción falsable estilo PRED-001** (magnitud esperada del
   mismatch tras el fix) **ANTES** de re-exportar.
3. **PASS en `tick:25`** y **después** repetir en **`tick:10`**: el arreglo debe
   ser general, no un parche que sólo funciona con `N=25`.
4. Oráculos nuevos en **archivos separados** (el `.cs` abre en modo append).
5. Sección nueva en el contrato de paridad: **"tick bars: condiciones de
   comparabilidad"**.
6. Recién entonces el `bar_spec` de tick pasa a `parity_covered` y BigTrap2 queda
   **elegible para su propia campaña** en su resolución natural.
