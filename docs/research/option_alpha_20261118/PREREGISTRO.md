# OPTION-ALPHA: ocho reglas extraídas del Top 20 Live de Option Alpha en M1 de ES, NQ y YM 2006–2025 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «extrae los 20 mejores ... encargate de dejar todo listo para correrlos en edgelab».
- **Catálogo y Diseño:** `CATALOGO_TOP20.md` y `DISENO.md`, misma carpeta.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP y EF5 en HOLDOUT (partición `HOLDOUT-A5`). **Familia:** `OPTION_ALPHA_A5` (nueva).
- **Módulo y campaña:** `edgelab/research/option_alpha_a5.py` (contrato `tablas.py`, motor único `ejecucion.py`) + `CAMPANA.json` + `tools/a5_campana.py`.

Antecedentes: «option alpha orb taco sandwich 1:45pm vix fomc heikin ashi» — familias parecidas: ORB_RR_MENOR, ORB_VARIANTES, CANASTA_ORB; NO_REPETIR: F-REELS-20261108, F-ORB-EMA20-NQ-STOP-OPUESTO, F-ORB5-BRUTO-ESTABLE; código: edgelab/stats/fixed_b.py:145, edgelab/discovery/features.py:20, tools/sandbox/l3_power.py:36

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (incluidas K40–K49: stop M1 en su nivel, columnas de identidad, variables conocidas antes de entrar, potencia en días).
- §1: cadena estándar (`tablas.py` + `a5_campana.py`), población declarada y causalidad verificada en `preflight`.
- §2: datos locales `M1NT8` verificados con `PROCEDENCIA.json` (`ES`, `NQ`, `YM`, `cboe_volatility_daily.parquet`, `us_market_events_calendar_2006_2026.parquet`), partición A5 y calibración obligatoria M1↔ticks (K30/K40) antes de correr DESC.
- §3: R neto con costos canónicos de `edgelab/costos.py` (mini y micro reportados; umbral de fricción operable ≤ 0,08 R) y unidades normalizadas por `ATR20` / `R15` / `R60` (K36).
- §4: confirmación jerárquica (REP con LORD++ → Holdout A5 con potencia ≥ 0,80 → instrumentos sin usar `RTY` y `EMD`).

Potencia previa: estimación conservadora previa a mirar desenlaces (efecto supuesto `0,10 R`, `sd_op ≈ 1,30 R`, α LORD++ `0,0125`):
- Frecuencia esperada en ventana A5 (`2006–2025`, 3 índices × ~250 sesiones/año): ~`15–21 ops/mes` por índice (~`45–60 ops/mes` en la canasta `ES+NQ+YM`) para `OA1/OA3/OA6/OA7/OA8` y ~`6–12 ops/mes` por índice para `OA2/OA4/OA5`.
- En DESC (7/12 meses ≈ 137 meses × 3 índices): `N ≈ 1.800–6.000` operaciones por regla; en REP (2/12 meses ≈ 39 meses): `N ≈ 500–1.700` operaciones por regla. Para detectar `0,10 R` con `sd = 1,30` al 80% de potencia con α `0,0125` hacen falta ~`1.580` operaciones → si DESC nomina con efecto ≥ `0,12 R` o se agrupan índices en REP/HOLDOUT, hay potencia suficiente; lo por debajo queda `SIN_POTENCIA` para evaluar con `RTY` y `EMD` o forward.
- **Enmienda K49 (2026-11-18, antes de calibrar y de correr):** la estimación de arriba cuenta operaciones; con tres índices el mismo día las operaciones no son independientes. La lectura de REP se decide con `a5.plan_lectura` (sumas por sesión de DESC, efecto supuesto = la mitad del de DESC, nivel LORD++ de la familia) y `tools/a5_campana.py rep` sólo prueba las nominadas con potencia ≥ 0,80 en días; las demás quedan `SIN_POTENCIA_PREVIA` sin leer su réplica.

## 1. Justificación económica
- **`OA1` (`1:45pm Taco`) & `OA2` (`1:45pm Sandwich`) & `OA8` (`Theta Fly EM%`):** en renta variable de EE. UU., los flujos direccionales matutinos suelen agotar su desequilibrio antes de las `13:30–13:45 ET`, generando compresión de gamma/reversión parcial hacia el rango de apertura (`15m ORB mid`) o ancla de media tarde (`13:45`) en días sin choque macro/volatilidad extrema.
- **`OA3` / `OA4` / `OA5` (`ORB 60m` + días Wed/Fri + Daily Bias):** a diferencia del ORB de 5m (`F-ORB5-BRUTO-ESTABLE`, stops chicos) o el retroceso a EMA20 (`F-ORB-EMA20-NQ-STOP-OPUESTO`), el Initial Balance de `60m` concentra el volumen de subasta institucional con stops amplios (`mid60` u opuesto, manteniendo fricción ≤ 0,08 R) y suma filtros estructurales provenientes de bots Live rentables (miércoles/viernes de `60Min ORB 10 Wide`, Daily Bias de `ORB Intelligence` y exclusión de FOMC).
- **`OA6` (`10m HA BB-MACD`) & `OA7` (`Trendy Put Dip SMA200`):** capturan aceleración de flujo intradía con filtro tendencial/volatilidad en 10m (`OA6`) y compra de retrocesos leves matutinos a favor de la tendencia primaria de `200` días (`OA7`).

## 2. Espacio de eventos y población
- **Espacio:** reglas intradía y swing-intradía derivadas del Top 20 Live de Option Alpha (`OA1`–`OA8`) más sus 5 controles directos (`OA1N`, `OA2N`, `OA4N`, `OA5N`, `OA8N`).
- **Fuera de esta corrida:** `xDTE $140-$350` y `Tasty Condor` (puro VRP lejano sin señal en futuro lineal), `Martingale TQQQ` y `DCA Multiple` (sin stop loss, incompatible con control de riesgo), e instrumentos `RTY` y `EMD` (reservados como confirmación fuera de muestra en §4.3; además `EMD` tiene spread estimado en `costos_canonicos.json`).
- **Población:** sesiones RTH (`09:30–16:00 ET`) sobre M1 real de NT8 (`ES`, `NQ`, `YM`), `2006-01-06 → 2025-07-31` (calibración en ticks reales `2025-08-05 → 2026-03-31`).

## 3. Cómo podría refutarse
- Cualquier regla queda refutada si su `R` bruto es `<= 0` con potencia suficiente en DESC/REP/HOLDOUT, si no supera la fricción canónica (R neto `<= 0` o fricción mediana `> 0,08 R`), o si su contraste frente al control (`OA1 - OA1N`, `OA2 - OA2N`, `OA4 - OA4N`, `OA5 - OA5N`, `OA8 - OA8N`) es `<= 0` mostrando que el filtro de Option Alpha (volatilidad, miércoles/viernes, Daily Bias o contención) no aporta valor respecto a operar sin filtro.
- Si ninguna regla sobrevive `BH q = 0,10` en futuros lineales, se concluye que el edge observado en Option Alpha proviene del cobro de prima implícita (VRP) y no de ventaja direccional trasladable al futuro.

## 4. Contador y linaje
- **Pruebas en exploración DESC (`a5_campana.py`):** `8` reglas absolutas + `5` contrastes contra control = **`13` hipótesis** en la familia BH (`q = 0,10`), **Los filtros macro (`vix_bajo`, `vix_40`, `ivr_20`, `no_fomc`, `sin_early_close`) NO se evalúan en esta corrida** (enmienda 2026-11-18, antes de correr): mirarlos serían 5 × 8 pruebas más fuera de la familia. Las columnas quedan en la tabla (causales: `vix_open` se conoce a las 09:30 y todas las entradas son ≥ 10:00; IVR y calendario son del cierre previo o fijos); si una regla sobrevive REP, los filtros se pre-registran como familia hija.
- **Linaje:** familia nueva `OPTION_ALPHA_A5`, hija de `ORB_A5` (OA3–OA5 son ORB de 60 m; hereda su multiplicidad en `LINAJES.jsonl`), referenciada contra `ORB_A5` y `M1_INTRADIA` para evitar repetir `F-ORB5-BRUTO-ESTABLE` y `F-ORB-EMA20-NQ-STOP-OPUESTO`). Sensibilidad reportada en años limpios `2006–2011`.
