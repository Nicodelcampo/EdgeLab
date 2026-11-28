# ADAPTAR-PRESENTE 1: parámetros en puntos fijos que el nivel de precio volvió activos — T y F de FundedSync con tope proporcional al precio (pre-registro, 2026-11-26)

Estado: PRE-REGISTRO — se commitea y se cuenta antes de correr.
- **Decisión de Nico** (`docs/DECISIONES_20261126.md`): adaptar al presente de forma estructural, llevando las unidades absolutas a unidades
  invariantes, sin reoptimizar. Una sola variante por estrategia.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3.** **Familia:** `FUNDEDSYNC`. **Pruebas:** 2 (T y F).
- **Herramienta:** `tools/adaptar_presente.py` (llama a `exigir_contada`).
- **Código:** opción `escala_precio_ref` en `FtmConfig` (T) y `FabioConfig` (F); 0 = el vendedor, sin cambios.

Cambio respecto a falla previa: no es una grilla ni una regla NO_REPETIR. Es un cambio de unidad de un parámetro, con un único valor
derivado de una ventana declarada, no del desempeño.

Antecedentes:
- **Auditoría** (`DECISIONES_20261126.md`, sobre `remedicion_fs_il_20261121/FS_OPS_NQ_IL.csv.gz`):
  - el stop de T está acotado a [2, 100] puntos y el tope ata el 0 % de las operaciones en 2017, el 72 % en 2022 y el 93 % en 2026;
  - F descarta entradas con riesgo > 125 puntos y pasó de ≈ 160 operaciones por año (2012–2019) a 76 en 2025 y 18 en 2026 (p90 del riesgo
    121 puntos).
- **Otros parámetros absolutos encontrados y no incluidos acá:**
  - O deja de operar con NQ > 25.000 por su techo de margen (`floor(25.000 / cierre)`, auditoría de Antigravity); es tamaño, no regla;
  - E tiene stop y objetivo fijos de 30 y 45 puntos;
  - W, N y Q tienen umbrales de pocos ticks.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 escalas, K40 motor, K51, K56 episodios).

Potencia previa:
- T tiene ≈ 225 operaciones por año y F ≈ 150 por año antes del cambio. En 2012 → 2026-09 son ≈ 3.300 y ≈ 1.900 operaciones.
- Se compara la misma regla con y sin escala, sobre las mismas sesiones, así que el contraste es pareado por mes.

Diagnóstico de mecanismo:
- **Una perilla y un valor.** El tope se multiplica por precio / P_ref, con P_ref = mediana del cierre diario de NQ entre 2022-01 y
  2025-08 = **15.758**: la ventana del backtest del vendedor hasta el lanzamiento del producto.
- **Qué hace:** fija lo apretado del tope relativo al precio en el nivel que tenía cuando el vendedor lo calibró. Antes de 2022 el tope
  queda más chico que el original (en 2017 ≈ 37 pts para T) y en 2026 más grande (≈ 182 pts).
- **Se publica:** por año, la fracción de operaciones en el tope y las operaciones por año.

## Justificación económica
- El stop por rango de T y el filtro de riesgo de F se pensaron relativos al movimiento del mercado.
- Un tope fijo en puntos se vuelve otra regla cuando NQ cuadruplica su precio. Llevarlo a proporción del precio conserva la regla que se
  diseñó y se midió.

## Qué se corre y cómo se decide (fijo)
- **Corrida:** T y F en NQ (M1 de NT8, 2010 → 2026-09-30, sin el terminal), con el mismo motor y la misma fricción de la re-medición. Línea
  base (escala 0) y variante (P_ref 15.758) en la misma corrida.
- **Medidas:** USD con 1 MNQ (bruto − fricción del micro) y R por operación.
- **Se adopta la variante** si, en 2012 → 2026-09:
  - su Sharpe mensual no es peor que el de la base en más de 0,1;
  - su % de años positivos es ≥ el de la base;
  - y la fracción de operaciones en el tope queda estable por año (no sube con el precio).
- Si no se cumple, se mantiene la del vendedor y se informa.
- Se reporta aparte 2022 → 2026-09.
- Nada de esto se mira en el holdout terminal.

## Cómo podría refutarse
- La variante empeora el Sharpe en > 0,1 o tiene menos años positivos: el tope fijo era parte de la ventaja, no un desajuste.
- La fracción en el tope sigue subiendo: la escala elegida no corrige el desajuste.
