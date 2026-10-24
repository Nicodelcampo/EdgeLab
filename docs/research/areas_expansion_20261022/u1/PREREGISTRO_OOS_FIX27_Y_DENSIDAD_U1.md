# Pre-registro — OOS de U1-CRUZADO con el fix 27 y densidad del feed completa (2026-10-24)

Estado: VIGENTE — registrado antes de lanzar la corrida y antes de agregar los datos por día.
Pedido: Nico, hilo «Correr el OOS de U1» (2026-10-24), pendiente §4 de `docs/research/revision_20261024/REVISION_20261024.md`.

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
**Etapa del embudo:** A = `EF4` (verificación fuera de muestra de una regla ya congelada; no es `EF5`, no toca el holdout).
B = `EF0-A` (factibilidad del dato, target-free).
Regla: `MANIFIESTO_U1_CRUZADO.md`, sin cambios. Kernel `tools/kaggle_grilla/kernel_u1_cruzado.py` (código `4e23f908…`, ya
incluye el fix 27 de `edgelab/research/areas_expansion.py::simular`; reconstruido el 2026-10-24 y byte a byte igual al commiteado).

## A. OOS USATECH 2023-01-01 → 2025-07-31 con el fix 27
- **Por qué se relanza:** la corrida del 2026-10-23 (`integridad_oos/U1_OOS_US_*`) se hizo con el simulador anterior al
  error 27 (stop cruzado dentro de la vela llenado en el stop exacto). Por `GUIA_GRILLA_MASIVA.md` (tabla de errores) una
  corrida con código que después se corrigió **queda descartada** y se relanza. Sus archivos se conservan como histórico.
- **Qué se corre:** exactamente lo pre-registrado en `PREREGISTRO_INTEGRIDAD_Y_OOS_U1_CRUZADO.md`, paso 2: modo `OOS_US`,
  T1 y T3 (`E1A/T1/S3`, `E1A/T3/S3`), sin tope, en el propio CFD con la fricción canónica de NQ (`fuentes_ticks.FUENTES`,
  1,5455 pts, igual a `edgelab/costos.py` por `tests/research/test_fuentes_ticks.py`). Dos tramos por memoria, analizados juntos:
  - `edgelab-u1x-oos-fix27-a`: `DESDE=20230101`, `HASTA=20240331`
  - `edgelab-u1x-oos-fix27-b`: `DESDE=20240401`, `HASTA=20250731`
  - Datos: `nicolasbuttaro/edgelab-dukascopy-nq-usatech` v1 + `edgelab-data-catalog` (los mismos de la corrida descartada).
- **Decisión (sin cambios):** el lote de 2 ocupa el **paso 3 de LORD++ de la familia**, el mismo de la corrida descartada
  (α₃ ≈ 0,00189). No se abre un paso nuevo: el p de la corrida descartada se reemplaza, no se suma. Simes del lote y BH adentro
  (`escalera.probar_lote`), p unilateral por sesiones (`escalera.resumen_sesiones`, 4000 remuestreos, semilla por defecto).
- **Guarda contra el camino que se bifurca:** si la corrida nueva rechazara y la descartada no, no se declara confirmación:
  se informa la discrepancia y la lectura queda NO_CONCLUYENTE hasta el forward desde el 2026-10-23.
- **Lectura por el principio de edges actuales (igual que antes):** confirma → evidencia fuerte antes del holdout;
  media > 0 sin rechazo → consistente sin potencia; media ≤ 0 → no funcionaba en 2023–2025, baja prioridad, no mata.
- **Se publica además:** MDE (`escalera.mde`) con el SE observado, riesgo (drawdown, peor día, peor racha, p01), por año,
  y la diferencia operación por operación contra la corrida descartada (para cuantificar el efecto del fix 27 en este tramo).
- **Pruebas:** 2, registradas en el contador global como `u1_cruzado/oos_us_fix27` (se cuentan aparte por conservadurismo
  aunque reemplazan a `u1_cruzado/oos_us`).
- **Cómo podría refutarse lo que se afirme:** si la media de T1 o T3 es ≤ 0 o el IC90 cruza cero, el OOS no apoya a U1 en
  2023–2025; si la diferencia contra la corrida descartada es grande, el fix 27 sí importaba en este tramo y hay que re-medir
  todo lo que dependía de él.
- **Justificación económica:** U1 pierde poco seguido y mucho de a poco; el fix 27 corrige justamente el llenado del stop,
  que es donde vive la cola. Sin esta re-medición el OOS documentado no corresponde al simulador vigente.

## B. Densidad del feed: análisis de los datos por día (target-free)
- **Datos:** `U1_DENSIDAD_20230101_20260930_dias.csv`, salida de la corrida `edgelab-u1x-densidad` del 2026-10-23 (ya
  existía en Kaggle; la revisión del 24 sólo había bajado el JSON por trimestre). sha256
  `00410710d86bf6d1564956817d07c8522ae0966e5eae5afa95fcd5546b56e472`, 967 días, columnas `ses, ticks, minutos, zonas, rango`.
  El cálculo de densidad no pasa por `simular`, así que el fix 27 no lo afecta. Hasta acá sólo se miró el encabezado (4 filas).
- **Por trimestre (15, 2023-T1 → 2026-T3):** mediana por día de ticks, minutos, zonas (velas M1 con hueco) y rango;
  señales por sesión = señales del trimestre (`U1_DENSIDAD_*.json`) / sesiones.
- **Estadísticos fijados ahora:**
  - Spearman de señales/sesión contra rango (ρ_R), ticks (ρ_T), minutos (ρ_M) y zonas (ρ_Z), y ρ entre rango y ticks.
  - Spearman **parcial** de señales/sesión con rango controlando ticks (ρ_R|T) y con ticks controlando rango (ρ_T|R)
    (correlación de los residuos de rangos).
  - Cociente de ticks por día y de minutos por día de cada trimestre contra 2023-T1 (salto de feed = cambio ≥ 25 % sostenido).
- **Lectura fijada (operacionaliza la del pre-registro de topes):**
  - **Mercado:** ρ_R|T ≥ 0,5 y ρ_T|R < 0,5.
  - **Feed:** ρ_T|R ≥ 0,5 y ρ_R|T < 0,5. La paridad con el feed en vivo pasa a **bloqueante** para U1.
  - **Indeterminado:** cualquier otro caso. Por la revisión del 24, la paridad de feed sigue tratándose como bloqueante.
  - Con 15 puntos el análisis es descriptivo; no se reporta p como evidencia.
- **Integridad:** se listan los días con minutos < 1.000 o ticks < 25 % de la mediana de su trimestre (huecos del feed),
  con atención a 2025-T3 (4 señales en 66 sesiones en el JSON).
- **Pruebas:** 0 (target-free, sin desenlace).

## Lo que no se hace
- No se cambia la regla, los tramos, la fricción ni la ejecución al ver resultados.
- No se usa nada desde el 2026-10-01 (frontera `edgelab/holdout.py`; los tramos terminan el 2025-07-31 y el 2026-09-30).
- El resultado no elige topes ni variantes: es una verificación.
