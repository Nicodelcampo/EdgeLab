# FS-NFCO-A5: N, F, C y O de FundedSync (traducción corregida) por DESC → REP de A5 (pre-registro, 2026-11-26)

Estado: PRE-REGISTRO — se commitea y se cuenta antes de leer.
- **Pedido de Nico (2026-11-26):** «adelante con cada paso» (paso 2 de `docs/DECISIONES_20261126.md`).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3.** **Familia:** `FUNDEDSYNC`. **Pruebas:** 8 (4 en DESC y 4 en REP).
- **Herramienta:** `tools/fs_nfco_a5.py` (llama a `exigir_contada`).

Cambio respecto a falla previa: no repite una regla NO_REPETIR. Es la primera lectura en R por bloque A5 de N, F, C y O con la traducción
corregida.

Antecedentes:
- `remedicion_fs_il_20261121/RESULTADO.md`: t mensual 2022–26 de N 1,95, F 1,62, C 1,49 y O 0,78.
- `estabilidad_cartera_20261126/RESULTADO.md` §C: N y F cumplen el criterio de estabilidad sobre la Interdía; N también sobre la Intradía.
- **Declarado:** el HOLDOUT A5 de FundedSync no está limpio. Las operaciones de los 15 módulos se calcularon en todos los meses desde el
  2026-11-17 (`m1_largo_20261117`) y la familia ya usó su apertura terminal. La confirmación limpia es el forward.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K49 potencia, K51, K56 episodios).

Potencia previa:
- Operaciones 2018–2026-09 en DESC por módulo, aprox.: N 500, F 600, C 300 y O 450; en REP, ≈ 30 % de eso.
- Con sd ≈ 1 R, el MDE80 en DESC es ≈ 0,11–0,16 R y en REP ≈ 0,2–0,3 R.
- Un nulo en REP no mata (K49).

Diagnóstico de mecanismo: no aplica (fábricas del vendedor, sin grilla). Se publican los episodios por año.

## Justificación económica
- **N:** ruptura alcista de N días con filtro de aceptación.
- **F:** orb de Fabio en 5 minutos con delta.
- **C:** continuación de gap contenido.
- **O:** tendencia diaria con tamaño inverso a la volatilidad nocturna.
- Son mecanismos distintos de T, R y Z; si tienen ventaja, suman diversificación.

## Lectura (fija)
- **Datos:** `remedicion_fs_il_20261121/FS_OPS_NQ_IL.csv.gz` (versión del vendedor, sin escala).
- **Medida:** R neto = neto / riesgo.
- **Régimen:** 2018-01-01 → 2026-09-30, misma convención que RQ5-REGIMEN.
- **DESC:** media de R > 0, bootstrap por sesión, BH q 0,10 sobre las 4.
- **REP:** sólo las nominadas, mismo signo con p de una cola < 0,05.
- **Desenlaces:** CONFIRMA_REP, NO_CONCLUYENTE o SIN_NOMINAR, con el MDE publicado.
- **O:** en 2025-10 → 2026-09 no opera por su techo de margen; se informa.

## Cómo podría refutarse
Ninguna nominada en DESC, o nominadas que no sostienen el signo en REP con potencia.

## Enmienda (2026-11-26, antes de leer N y O)
- **Qué pasó:** N y O no tienen stop (riesgo vacío) y la primera corrida los dejó sin operaciones. La herramienta trató el grupo vacío como
  nominado: era un error, y ese resultado se descarta.
- **Corrección de la unidad:** para los módulos sin stop, la unidad de R es el ATR20 de la sesión previa (`m1_largo.atr20`, la convención
  del repo para módulos sin stop). Sus salidas no se cambian: R = neto / ATR20.
- **Ya visto en la primera corrida:** F y C usan su riesgo propio y sus resultados quedan como salieron (SIN_NOMINAR).
- **Familia de BH:** sigue con las 4.
