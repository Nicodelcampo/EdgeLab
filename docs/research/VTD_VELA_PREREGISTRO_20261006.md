# VTD-VELA — pre-registro: ¿la vela de la marca VolTicksDef anticipa el lado del tramo largo? — 2026-10-06

**Escrito ANTES de calcular nada con estos datos.** Decisión de Nico: opción (b), "probar la vela en datos limpios".
Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Información direccional, **no P&L**.

## Origen
VTD-DIR etapa 1 (`VTD_DIR_E1_RESULTADOS_20261006.md`): la vela de la marca no pasó el descubrimiento en MNQ (+0,027,
p = 0,11). Mirando después los 6 contratos MNQ, dio +0,044 contra +0,003 en barras al azar. Por haberse mirado después
del fallo, **MNQ queda excluido**: esta prueba usa sólo datos que no se tocaron para VTD-DIR.

## Datos (nunca usados para VTD-DIR)
- **ES, YM, RTY, MGC**, todos los contratos líderes con sesiones aprobadas por el RESOLVER, 2025-07-01 → 2026-09-30.
- Holdout (≥ 2026-10-01) no leído.
- Se excluyen NQ (mismo índice que MNQ, no es dato nuevo) y MES/MYM (duplican ES/YM).
- MGC ya fue visto en una exploración descriptiva de asimetría de excursiones
  (`EXPLO_ASIMETRIA_EXCURSION_20261006.md`), pero **no** con la vela como predictor. Se declara.

## Definición congelada
- VolTicksDef con parámetros por defecto (200 / 99,75 / reset por sesión / 30), barras de **150 ticks**, en todos los
  instrumentos. La paridad NT8 se validó en MNQ; aquí se usa el mismo código, que es determinista.
- Predictor: `s = signo(close − open)` de la barra marcada. Velas doji (s = 0) se excluyen.
- Resultado: `asim_10 = (U − D)/(U + D)`, excursiones desde el close de la marca en las 10 barras siguientes, en la
  misma sesión.
- **Control de deriva:** `asim_adj = asim_10 − media de asim_10 en barras al azar de la misma sesión` (1 de cada 7
  barras, excluyendo ±100 barras alrededor de marcas).
- Sólo RTH.

## Prueba única (formal)
- Estadístico: media de `s × asim_adj` sobre todas las marcas de los 4 instrumentos, pooled.
- Nulo: signo sorteado por sesión (todas las marcas de una sesión × ±1), 20.000 sorteos, semilla 20261007.
- **Unilateral**, H1: media > 0.
- **Decisión:** CONFIRMA si p ≤ 0,05 y la media > 0. Si no, la vela queda **descartada** como predictor del lado (para
  esta definición, estos datos y H10).
- MDE: se publica (≈ 2,5 × el SE por sesión).

## Descriptivos (no cambian la decisión)
- Por instrumento.
- H50.
- Sin control de deriva.
- Por régimen de amplitud.
- Tasa de acierto del lado (P(signo(U − D) = s)).

## Justificación económica
Los lotes grandes que generan la marca dejan su huella en el cuerpo de la vela. Si el lado de esos lotes anticipa el
tramo largo, se puede entrar en la dirección de la vela con el stop del lado corto.

## Cómo podría refutarse
Media ≈ 0 o negativa, o p > 0,05, con el MDE publicado.

## Registro
1 prueba, familia `VTD_VELA`. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
