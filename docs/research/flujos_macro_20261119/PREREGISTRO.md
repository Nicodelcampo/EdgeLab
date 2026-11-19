# FLUJOS-MACRO: ocho reglas de flujos institucionales, volatilidad implícita CBOE y sesgos de calendario/oro en M1 de ES, NQ, YM y GC 2006–2025 (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «lanzá una recopilacion mas ... de algoritmos que cumplan con los requisitos que vos definas como necesarios para que tengan altas probabilidades de tener edge luego de fricciones».
- **Catálogo y Diseño:** `CATALOGO_14_ESTRATEGIAS_POST_FRICCION.md` y `DISENO.md`, misma carpeta.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP y EF5 en HOLDOUT (partición `HOLDOUT-A5`). **Familia:** `FLUJOS_MACRO_A5` (nueva).
- **Módulo y campaña:** `edgelab/research/flujos_macro_a5.py` (contrato `tablas.py`, motor único `ejecucion.py`) + `CAMPANA.json` + `tools/a5_campana.py`.

Antecedentes: «concretum pagani zarattini vix9d channel trend ibs turnaround tuesday gold overnight gap london fix baltussen last 30m vol spike crush» — familias parecidas: BAJA_FRICCION_A5, ROBOQUANT_A5, FUNDEDSYNC, EL_DIA_TENDENCIA; NO_REPETIR: F-OPTION-ALPHA-FUTUROS, F-REELS-20261108, F-ORB-EMA20-NQ-STOP-OPUESTO, F-VENTAJA-EN-PUNTOS-NO-ESCALA; código: edgelab/research/baja_friccion_a5.py:1, edgelab/research/option_alpha_a5.py:46

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36 unidad normalizada, K38 ajuste del diseñador, K40 stop M1 en su nivel, K48 causalidad, K49 potencia en días, K50, K51).

Potencia previa: estimación conservadora previa a mirar desenlaces en **DÍAS** (`K49`, controlando correlación cross-index):
- Frecuencia esperada en ventana A5 (`2006–2025`, `4` instrumentos: `ES`, `NQ`, `YM`, `GC`):
  - Alta/media frecuencia (`FM1`, `FM2`, `FM3`, `FM6`, `FM8`): ~`8–21` sesiones activas/mes (`DESC ≈ 1.100–2.800` sesiones; `REP ≈ 310–800` sesiones). Con `sd_dia ≈ 1,10 R` y α LORD++ `0,0125`, tienen potencia `>= 0,80` en `REP` para efectos netos `>= 0,14–0,18 R`.
  - Frecuencia condicional/evento (`FM4` Martes débil, `FM5` Gap `5d` high, `FM7` Spike de VIX): ~`2–5` sesiones activas/mes (`REP ≈ 80–195` sesiones). Por `K49`, ninguna de estas tres podrá abrir `REP` sola salvo que su efecto esperado justifique potencia `>= 0,80` en `a5.plan_lectura`; de otro modo queda `SIN_POTENCIA_PREVIA` para evaluación en canasta o lectura conjunta con `RTY`/`EMD`.

## 1. Justificación económica
- **Sigma implícita diaria (`FM1`) & Bandas ATR + Asimetría Long (`FM2`):** en lugar de stops fijos o de micro-velas M1, `FM1` usa el precio de las opciones a 9/30 días (`VIX9D`/`VIX` de CBOE, causal `t-1`) como escala física de riesgo y objetivo (`0,50–1,0 × σ_impl`), mientras `FM2` mide por separado la continuación alcista vs bajista desde bandas `Open ± 0,50 · ATR14_D1` (Concretum Group, marzo 2026).
- **Reversión por liquidación al cierre y martes (`FM3` & `FM4`):** tras días que cierran en su cuartil inferior (`IBS < 0,25`), las coberturas forzadas de cierre suelen revertir parcialmente en la sesión siguiente; `FM4` aísla específicamente la sobre-reacción de los lunes (*Turnaround Tuesday*).
- **Flujos de Oro / Londres-COMEX (`FM5` & `FM6`):** los participantes norteamericanos persiguen gaps de ruptura sobre máximos de 5 días en `GC` (`FM5`) y rupturas tras cajas asiáticas/Londres comprimidas (`FM6`, cobertura LBMA AM Fix `05:30 ET`), manteniendo fricción baja (`<= 0,04 R`) con `SL >= 0,50–0,75 · ATR20_D1`.
- **Régimen de Volatilidad (`FM7`) & Estrés de Rebalanceo al Cierre (`FM8`):** `FM7` contrasta compras tras picos agudos de miedo implícito (`z20 >= 1,25`) frente a compresión de volatilidad (`z6 <= -0,90`); `FM8` restringe el momentum de última media hora (Baltussen et al. 2021) únicamente a sesiones de desplazamiento extremo (`>= 0,75 · ATR20`), donde los flujos forzados de cierre dominan la fricción (validado por el Sharpe `+1,452` en estrés vs `-0,628` incondicional en QC).

## 2. Espacio de eventos y población
- **Espacio:** 8 reglas intrasesión (`FM1`–`FM8`) más sus 8 controles directos (`FM1N`–`FM8N`) ejecutados al mercado con salida por objetivo/stop/fin, unidad `R` normalizada a `rg`.
- **Instrumentos:** `ES`, `NQ`, `YM` y `GC` (`M1NT8` real no ajustado). `RTY` y `EMD` quedan reservados para confirmación externa fuera de muestra (§4.3).
- **Fuera de esta corrida:** variantes estrictamente multi-día (`Daily IBS Multi-Día`, `Connors Double Seven`, `Turn-of-the-Month`, `Dual eVRP + Term Structure`, `Dynamic Breakout II`, `ES/GC Macro Rotation`) quedan documentadas en `CATALOGO_14_ESTRATEGIAS_POST_FRICCION.md` para un runner futuro de Carril 2 (sin el límite `GAP_S = 1800 s` de `ejecucion.py`).
- **Política de fricción histórica (`K52`):** las decisiones oficiales DESC/REP usan costos canónicos estrictos; de forma descriptiva (sin nominar) se reportará la partición `2006–2011` / `2012–2019` / `2020–2025` y sensibilidad a fricción constante en `bps` modernos.

## 3. Cómo podría refutarse
- Cada regla queda refutada si su `R` bruto en DESC no supera `BH q = 0,10`, si su fricción mediana excede `0,08 R`, si su `R` neto con costos canónicos es `<= 0` con potencia suficiente, o si su contraste contra control (`FMk - FMkN`) es `<= 0` (excepto en reglas asimétricas donde el control mide la dirección o régimen opuesto como diagnóstico de dirección, ej. `FM2` vs `FM2N` y `FM7` vs `FM7N`: en ambos casos cada brazo requiere además `R neto > 0` propio).

## 4. Contador y linaje
- **Pruebas en exploración DESC (`a5_campana.py`):** `8` reglas absolutas + `8` contrastes contra control = **`16` hipótesis** en `BH (q = 0,10)`. **Los filtros secundarios de tabla (`vix_contango`, `vix_alto`, `no_opex`, `no_fomc`, `sin_early_close`) NO se evalúan ni nominan en esta corrida.**
- **Linaje (enmienda de Claude, 2026-11-19, antes de calibrar y de correr):** `BAJA_FRICCION_A5` no existe en `LINAJES.jsonl` (no heredaría multiplicidad de nadie). Padres reales: `ORB_A5` y `ROBOQUANT_A5` (FM2 es la banda de ruido desde la apertura, ya medida como Noise Area y RQ5), `RANGO_ASIA0100_GC` y `EXTERNAS_A5` (FM6, caja Asia→Londres en oro), `DIA_TENDENCIA_A5` (FM8, días de desplazamiento fuerte). Sensibilidad obligatoria reportada en años limpios `2006–2011`.
