# AUDITORIA-EXCLUSIONES: ¿las fechas que FundedSync excluye a mano inflan T y R? (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Origen:** auditoría nocturna de las mejores estrategias (pedido de Nico: «audita … corregir errores … sé cuidadoso»). El binario de
  FundedSync trae listas fijas de fechas: T (`FtmEngine`) excluye 8 fechas de vencimiento y **20 días de «datos degradados»** (2020–2026); R
  (`AtrPhase`) bloquea 8 sesiones, **3 de ellas días normales** (2022-08-03, 2022-08-30, 2023-04-05; las otras 5 son feriados o medias
  jornadas). Nuestra traducción las respeta, así que nuestras métricas de T y R heredan esas exclusiones. Si el vendedor sacó días perdedores
  mirando, el R medido está inflado (sesgo de selección del vendedor, no de EdgeLab).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (integridad sobre desarrollo ya mirado; no abre REP, holdout ni forward). **Familia:** `FUNDEDSYNC`.
- **Herramienta:** `tools/auditoria_exclusiones_fs.py` (motor de la traducción `edgelab.research.fundedsyncstack`, mismas fechas de arranque
  de `m1_largo.T_FECHAS`, `neto_pistas._ms/_ops` para R, fricción canónica). `registro_global.exigir_contada` al inicio (K51).

Antecedentes: T-REGIMEN, NETO-PISTAS (R con stop 0,25 × ATR20), INGENIERIA_INVERSA_FUNDEDSYNCSTACK §4.12 y §6.2 (listas fijas).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36 R con el stop, K40, K48, K51, K52).

Potencia previa: no es una prueba de efecto sino de integridad: ≈ 28 sesiones de T y ≈ 8 de R; se reporta el R de esos días contra la
distribución de días al azar del mismo tramo (percentil por permutación) y el impacto en el R medio del régimen 2021–2026.

## Justificación económica
- Un día excluido con un criterio que no se puede aplicar en vivo (no se sabe de antemano que un día tendrá «datos degradados») no es
  operable: en vivo esa operación se toma. El R operable es el que incluye esos días.

## Qué se mide y cómo se decide
- T (NQ, fábrica, `use_exclusion_calendars=False`) y R (NQ, fábrica, `blocked_sessions=()`, stop 0,25 × ATR20): operaciones de los días
  excluidos. **Exclusión inocua** si el R total de esos días no está en el 10 % inferior de la distribución de sumas de igual número de días
  al azar del tramo 2020–2026 (10.000 permutaciones) **y** el R medio 2021–2026 con esos días cae menos de 0,02 R. Si no, **SESGO_VENDEDOR**:
  las métricas de T/R se corrigen con los días incluidos (versión operable) y se documenta.
- Feriados y medias jornadas se reportan aparte (excluirlos es una regla que sí se puede aplicar en vivo con el calendario).
- **Cómo podría refutarse:** que los días excluidos sean sistemáticamente perdedores (percentil bajo) y cambien el veredicto de régimen.
- **Contador:** 1 prueba en `FUNDEDSYNC`.
