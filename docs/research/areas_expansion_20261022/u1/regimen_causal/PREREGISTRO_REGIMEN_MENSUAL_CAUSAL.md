# Pre-registro: U1-CRUZADO causal mes a mes contra medidas de régimen (2023-01 → 2026-09), experimento 1 de 4

Estado: VIGENTE, registrado antes de correr. Aprobado por Nico el 2026-11-02 («dale»; «seguí con los 4 experimentos»). Referente:
`docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF3: exploratorio, sobre
datos de desarrollo ya vistos y sin holdout.

## Pregunta
¿En qué régimen gana U1-CRUZADO con el código causal? ¿Hay alguna medida de régimen, conocida antes de operar, que separe los meses
buenos de los malos?

## Datos (corridas, todas con el código causal)
Kernel `tools/kaggle_grilla/kernel_u1_cruzado.py`, modo `TOPES`. Celda congelada: E1A/T3/S3 con tope `mult:3`.
| Período | Ejecución | Por qué |
|---|---|---|
| 2023-01 → 2024-03 | USATECH (propio) | no hay NQ en Kaggle antes de 2025-08 |
| 2024-04 → 2025-07 | USATECH (propio) | ídem |
| 2025-08-05 → 2026-03-31 | NQ | DESC |
| 2026-04-01 → 2026-09-30 | NQ | réplica |

## Medidas de régimen (causales: sólo sesiones anteriores a cada mes)
Sobre las sesiones de los 20 días anteriores al primer día del mes, con `topes/U1_DENSIDAD_20230101_20260930_dias.csv`:
1. rango diario medio de USATECH (`rango`);
2. tendencia: |cierre − cierre de 20 sesiones antes| / suma de rangos;
3. volatilidad de cierres: desvío de los retornos diarios.

## Análisis
- **Primario:** correlación de Spearman entre la media neta mensual y cada medida (3 pruebas), con IC por bootstrap de meses.
  Corrección de Holm sobre las 3.
- **Descriptivo:** media por año y por tercil de cada medida; cuántos meses positivos hay.

## Lectura fijada
- **Ninguna medida con Holm p < 0,10:** no hay una variable simple de régimen para elegir cuándo operar. Se informa con su MDE.
- **Una medida que pasa:** hipótesis NUEVA, «operar sólo en ese régimen». Se confirma sólo en el forward en papel, con el corte
  fijado acá (tercil superior o inferior según el signo), nunca con estos datos.

## Cómo podría refutarse
Que las correlaciones sean ≈ 0, o que cambien de signo entre 2023–2025 (USATECH) y 2025–2026 (NQ).

## Riesgos
- Mezcla dos ejecuciones: USATECH propio y NQ. Se reporta además cada tramo por separado.
- Son datos ya vistos: es exploración, no confirmación.

## Registro
3 pruebas en `TRIAL_REGISTRY_GLOBAL.jsonl` (`exp1/U1-REGIMEN-MENSUAL-CAUSAL`).

## Resultado (2026-11-02), en `RESULTADO.json` y `MENSUAL.csv`
`tools/u1/u1_regimen_mensual_causal.py`, con 39 meses (2023-02 → 2026-09).

| Medida | rho | IC90 | p Holm | rho US / NQ |
|---|---|---|---|---|
| rango | +0,21 | [−0,08; +0,48] | 0,44 | +0,04 / +0,60 |
| tendencia | −0,13 | [−0,39; +0,16] | 0,44 | −0,18 / −0,02 |
| volatilidad | +0,24 | [−0,06; +0,52] | 0,44 | +0,05 / +0,46 |

**Lectura (fijada antes): ninguna medida pasa Holm.** No hay una variable simple de régimen para elegir cuándo operar U1-CRUZADO.
- **MDE.** Con 39 meses el error estándar de rho es ≈ 0,16, así que sólo se detectaría |rho| ≳ 0,4. Una relación moderada no se
  descarta.
- **Rango y volatilidad tienen el mismo signo** en los dos tramos, pero sólo en NQ son fuertes (+0,60 y +0,46, con 13 meses).
  El rango está en puntos y el nivel del índice se duplicó entre 2023 y 2026: en parte mide nivel, no régimen.
- No se busca otra variable sobre estos mismos datos.
