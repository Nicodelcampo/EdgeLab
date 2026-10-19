# AVZVOL: diagnósticos descriptivos del diseño de controles

Estado: **DESCRIPTIVE_COVARIATE_DESIGN_ONLY_UNADJUDICATED**. Implementación técnica
probada con fixtures sintéticos; no ejecución de mercado, aprobación de balance,
certificación de fuentes ni benchmark de outcomes. P2 sigue abierta y P4 prohibida.

## Entrada y uso

API puro: `edgelab.kaggle.avzvol_diagnostics.describe_control_census(real_rows,
candidate_rows, policy=..., holdout_start=...)`. Recalcula el matching mediante
`plan_covariate_matches`; no admite pares o pesos editables como evidencia.
Hereda el schema exacto de ocho covariables, cinco estratos, fechas pre-anchor,
prewindow completo y política externa explícita. Rechaza outcomes, duplicados,
valores no finitos y declaraciones posteriores al ancla o dentro del holdout.
Esto comprueba declaraciones, no autenticidad, disponibilidad causal ni calendario CME.
El llamador necesita autorización independiente ANTES de construir/enviar covariables
reales. No hay loader, acceso a archivos/red ni modificación de entradas.

Con el wheel instalado según [ENVIRONMENT](../ENVIRONMENT.md):

```bash
python tools/avzvol_design_smoke.py --report control-census
python tools/avzvol_design_smoke.py --report control-census --purpose research
python -m pytest -q tests/test_avzvol_diagnostics.py tests/test_avzvol_design.py
```

El primer comando usa exclusivamente valores inventados y política de fixture.
El segundo devuelve STOP/exit 2 antes de crear el fixture. El reporte por defecto
`--report match` conserva su comportamiento anterior. Ningún comando acepta datos externos.

## Poblaciones y pesos

Dentro de CADA estrato exacto `(contract, session, cell, clock_bucket, trend_sign)`:

1. Reales soportados contra todos los reales: muestra selección por soporte.
2. Reales soportados contra controles ponderados para el análisis: muestra diferencias de diseño.
3. Controles únicos seleccionados contra su censo candidato completo declarado.
4. Controles ponderados para el análisis contra ese mismo censo.

El censo de referencia conserva candidatos no elegidos e inelegibles por caliper.
No se sustituye por el subconjunto elegible, no se mezclan estratos, no se relajan
calipers ni se borran estratos sin soporte. Una población vacía devuelve
`NOT_COMPUTABLE_EMPTY_POPULATION` y métricas `null`, no ceros imputados.
Un candidato en el mismo contrato/sesión/ancla UTC que un real causa STOP en este
reporte, no exclusión silenciosa de la referencia. Esto NO prueba ausencia de racimo
para los demás candidatos ni completitud del censo.

Cada real soportado tiene masa `1 / N_reales_soportados`; sus controles comparten
esa masa por igual. La reutilización acumula peso en el control. Se calculan pesos
con fracciones exactas y se normalizan dentro del estrato para cada comparación.
El reporte conserva la masa global de cada estrato. El contraste identifica la
población de **reales soportados**, no un estimando de todos los reales.

## Métricas y límites

Para cada covariable y comparación: medias ponderadas, diferencia en unidades de
la escala EXTERNA congelada y máxima distancia entre ECDF ponderadas. Los empates
avanzan juntos con pesos exactos. La distancia ECDF es descriptiva: **no es test KS,
p-value ni inferencia**. La diferencia por escala externa **no es SMD**.

Los pares incluyen media firmada, media absoluta y máximo absoluto de diferencias
por escala: pares opuestos no ocultan discrepancias detrás de una media cero.
Se enumeran reutilización, peso por control, máximo peso y suma de pesos al cuadrado.
Esta última es concentración, **no tamaño muestral independiente ni ESS**.
Overflow es STOP: no clipping, corrección, winsorización ni imputación automática.

Siempre falsos: `balance_accepted`, `support_accepted`, `zone_absence_verified`,
`census_completeness_verified`, `source_quality_certified`, `research_authorized`,
`own_census_outcome_benchmark_implemented`, `inference_implemented`, `outcomes_read`,
`pnl_computed`, `economic_outcomes_computed` y `bias_adjudicated`.
Una distancia pequeña, empate o soporte completo NO modifica esos estados.

## Qué falta para P2

Censo real revisado y clasificación causal sin racimo; pins y calidad independientes;
política de calipers/escalas, aceptación de soporte/balance y estimando aprobados;
endpoints no económicos, dependencia/reutilización, familia y presupuesto congelados.
El **benchmark de outcomes de controles contra su propio censo NO está implementado**.
No elegir umbrales después de mirar datos. Los campos científicos del
[spec](../../specs/research/avzvol_incremental_design_v1.json) permanecen `null`.
El [tracker](../../config/research/avzvol_followup_proposals_v1.json) conserva P1–P4,
cero nuevos trials, evidencia histórica intacta y prohibición económica explícita.

## Validación técnica de este lote

Base: `6ead4815aec2a1e6791355257970a931588dc69b`. Suite CPU local:
573 tests + 25 subtests; navegación: 18 tests. Wheel construido e instalado
fuera del checkout en entornos CPU y core sin dependencias opcionales: reporte
sintético correcto en ambos, 21 imports core y STOP research/exit 2 sin entradas.
Estos PASS son de software/fixtures; no resultados científicos ni certificación.
