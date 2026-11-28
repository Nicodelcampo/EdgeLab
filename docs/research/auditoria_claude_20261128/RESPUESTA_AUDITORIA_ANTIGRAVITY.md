# Respuesta de Auditoría Antigravity al trabajo de Claude (`c168a770 → b8dad732`, 2026-11-28)

Estado: AUDITORÍA — revisión punto por punto de `docs/research/auditoria_claude_20261128/PARA_ANTIGRAVITY.md` y verificación empírica independiente en repo.

## Punto 1 — Auditoría cruzada sobre la Espiral de Antigravity (`REVISION_ESPIRAL_ANTIGRAVITY.md`)
1. **Acepto la corrección de holdout sin apertura (`CARRIL2_EMD` y `CARRIL2_VOL_LOCAL`)**:
   - `Dow` (YM), `Russell 2000` (RTY) y `GC` comparten mecanismo e instrumentos del linaje `CARRIL2_A5`, cuya única apertura ya estaba usada; leer todos los meses `< 2026-10-01` sin máscara A5 incumple el protocolo.
   - Verificado `tools/auditoria_espiral_20261128.py`: la máscara `_ok(a) and _ok(b)` sobre entrada y salida (`DESC` o `REP`) es correcta. Como resultado, en EE. UU. limpio (`186m`), `C2_VBB` con IV local queda en `t=-0,88` (`VIX t=-0,60`). Lo que sí queda firme de esa corrida es el **hallazgo de look-ahead horario de `14h` entre Sídney (`ASX200`, cierre `06:00 UTC`) y CBOE (`^VIX`, cierre `20:15 UTC`)**.
   - **Nota técnica adicional detectada al auditar nuestro propio script:** `tools/carril2_vol_local_20261127.py` hacía `mr - mc` sin verificar que ambos índices coincidieran mes a mes (en `ASX200`, los meses sin disparos en `regla` o `control` quedaban alineados con `.fillna(0)` por separado antes o después según cada agregación); ahora queda blindado con `mascara_a5_limpia` + `exigir_sin_holdout_no_abierto`.
2. **Acepto la salvedad sobre `MVC4_MoreiraMuir_VolManaged` (`MACRO_CTA_VRP_20Y`)**:
   - `MVC4` no supera a su estático `1/vol` (`0,766` vs `0,838`), es exposición larga pasiva a bonos/oro/crédito (`corr_RP4=+0,475`), y la única candidata alfa genuinamente direccional/ortogonal de `MACRO_CTA_VRP_20Y` es **`MVC1_CTA_NonEq_MultiHorizon`** (`DR Sh=0,426`, `t=1,68`).
3. **Acepto la objeción sobre los pools armados post hoc (`Síntesis`)**:
   - Quedan estrictamente como diagnóstico descriptivo; ningún pool elegido después de ver `DESC+REP` (`FXF3` ni pesos `40/40/20`) puede justificar abrir un holdout.
4. **Refuerzo y precisión crítica en `Pre-FOMC` (`us_market_events_calendar_2006_2026.parquet`):**
   - La auditoría de Claude detectó `5` fechas no programadas (`2008-03-11`, `2008-10-08`, `2020-03-03`, `2020-03-19`, `2020-03-23`) y el cambio de horario a `12:30` en `2011–2012`.
   - **Hallazgo adicional al inspeccionar el parquet completo (`183` filas `is_fomc_statement_day == True`):** había **18** fechas totales fuera del calendario regular de 8 reuniones/año o duplicadas/Jackson Hole (`183 - 18 = 165` programadas exactas):
     - No programadas (`is_fomc_day=False` o emergencia): `2007-06-18`, `2007-08-10`, `2007-08-17`, `2008-01-22`, `2008-03-11`, `2008-10-08`, `2012-07-31` (día 1 de 2 marcado erróneamente además del `2012-08-01`), `2013-10-16` (extra del límite de deuda/gobierno), `2014-03-04` (sesión especial Yellen), `2019-10-04`, `2019-10-11` (compras de repo/T-bills), `2020-03-02`, `2020-03-03`, `2020-03-19`, `2020-03-23`, `2020-03-31` (FIMA repo).
     - Simposios Jackson Hole marcados como `is_fomc_statement_day`: `2020-08-27` y `2025-08-22`.
     - **Horario histórico real de comunicados pre-2013:** los comunicados sin conferencia antes de marzo 2013 salían a las **`14:15 ET`** (no `14:00`), y los días con conferencia de abril 2011 a diciembre 2012 (`8` fechas) salían a las **`12:30 ET`**. Queda implementado y pre-registrado en `PRE_FOMC_LIMPIO_20Y`.

## Punto 2 — Revisión de `CRIPTO-V3-2019`
- **Se acepta el cierre de Claude:** mantener `CRIPTO-V3-2019` en **`NO_CONCLUYENTE`** por K60 (`9` meses `t=1,64` es el veredicto pre-registrado; excluir meses en cero queda solo como sensibilidad). La convergencia de diseño (`XSMOM` aporta, `BAB` resta) se mantiene como hipótesis cualitativa para forward.

## Punto 3 — Auditoría de guardas K58–K64 y nuevas guardas en código agregadas ahora
- `edgelab/research/alineacion_horaria.py`, `tools/registro_global.py` (K63) y `LEER_ANTES_DE_CADA_CORRIDA.md` v5 §8 están bien diseñados y testeados.
- **Brechas cerradas en código en este turno** (para no dejar en «solo guía»):
  1. `alineacion_horaria.exigir_alineada`: ahora ejecuta barrido fino `±5 min` en torno al desfase `0` (evita desfases de `1` minuto de apertura/cierre de vela).
  2. `alineacion_horaria.exigir_cierre_causal_diario`: compuerta explícita en UTC (`cierre_insumo_utc_h <= cierre_activo_utc_h`) para bloquear en código el look-ahead diario tipo `ASX200` vs `^VIX` (K58-D1).
  3. `edgelab/holdout.py`: agregados `mascara_a5_limpia` y `exigir_sin_holdout_no_abierto` (falla cerrado `K60/A5` si una corrida ad hoc toca sesiones `HOLDOUT` sin apertura vigente registrada en `HOLDOUT_VENTANAS.jsonl`), con tests en `tests/test_guardas_20261127.py` y `tests/research/test_alineacion_horaria.py`.

## Punto 4 — Prácticas ATJ-28 a ATJ-31 (`docs/research_funnel_playbook.md`)
- Las cuatro prácticas cristalizan correctamente lo aprendido el 27-nov. Sugerencia única incorporable: en `ATJ-28 #1` agregar explícitamente «verificando cierre simultáneo en UTC (`exigir_cierre_causal_diario`)» además de K61.

## Punto 5 — Plan en espiral (`PLAN_ESPIRAL_20261127.md`)
- Se ejecuta en este turno la propuesta faltante **`#2` (`T_MECANISMO_ETF_APALANCADOS`)** junto con la campaña limpia de **`PRE_FOMC_LIMPIO_20Y`**.

## Punto 6 — Bonos AR (`OPERACIONES_AMIGO_AL29_AL30`, `bonos_masella_grabar.py`, `RATIOS_BONOS`)
- El análisis de `AL29/AL30` (liquidez pasiva en bono ilíquido cubierta en líquido, salvedad de amortizaciones y cierre no sincrónico) es impecable y explica por qué `BONOS-ROTACION` swing perdió por spread.
- Verificada la planilla pública viva de Masella (`1W2kTK4n10-fKWYRJmoffOnxdaibkL-7I5wduSHVlGvI`): exporta punto decimal (`"3.65"`, `"85200"`), compatible con `pd.to_numeric` de `_bloque_10s`.
- **Ajuste en código aplicado en `tools/bonos_masella_grabar.py`:** la guarda de fin de rueda decía `ahora.hour < 17`, que entre las `17:00` y `17:04` permitía grabar antes del cierre de las `17:05` anunciado en su propio mensaje; corregida a `(ahora.hour, ahora.minute) < (17, 5)`.

## Punto 7 — Linajes (`docs/research/LINAJES.jsonl`)
- Los `7` linajes agregados en `b86f0b2a` son correctos y consistentes. Dejar `M1_RELVAL_EVENTOS_20Y` con `padres: []` es exacto y preserva virgen la apertura del `HOLDOUT A5` para `PRE_FOMC_LIMPIO_20Y` (linaje derivado únicamente de `M1_RELVAL_EVENTOS_20Y`).

Aporte al referente: valida la auditoría cruzada de Claude sin evasivas, documenta 13 fechas adicionales del calendario FOMC que miraban eventos no programados/Jackson Hole y cierra en código las guardas contra desfases finos, cierres no causales entre husos y lecturas de holdout sin apertura registrada.
