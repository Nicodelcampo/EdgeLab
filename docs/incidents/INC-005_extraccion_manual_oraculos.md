# INC-005: Extracción Manual de Oráculos en Holdout

## El Incidente
La población entera de oráculos pre-registrados en `oracles/` (cubriendo `Gaps2`, `BigTrap2`, `HFTZones2`, `AACloseOpenDiffs`, `aVolCellPOI2`, `VolTicksPOC2`) abarca días del mes de julio de 2026. Específicamente, la ventana de comparación extraída para paridad llega sistemáticamente hasta el **16 de julio de 2026**.
Toda esa porción de julio recae dentro de lo que era el holdout sellado original (`>= 2026-07-01`).

## La Brecha (Air Gap Breach)
El firewall del holdout (`edgelab/research/holdout_guard.py`) estaba diseñado para interceptar los accesos desde código Python. Sin embargo, los oráculos se generan mediante un acto humano manual interactuando con la interfaz de NinjaTrader 8.
Esa extracción es estructuralmente invisible para el firewall. El humano cruzó la barrera de julio cargando el chart, generó los CSV de los oráculos, y los depositó en el repositorio.
Posteriormente, cuando `correr_gates.py` ejecutó la validación consumiendo esos oráculos, el firewall de Python autorizó la lectura de los parquets etiquetándola como un uso permitido (`target_free_validation`). Esto blanqueó una filtración pre-existente, dejando asentado en el log un permiso válido para una acción ilícita de fondo.

## El Catalizador
El defecto se mantenía silenciado porque el gate de `aVolCellPOI2` fallaba precozmente (`DATA_INTEGRITY_FAIL`) al detectar sólo 8 días limpios en el parquet.
Con la llegada de `594f708`, la reparación del detector de duplicados (censo) purgó el bloque corrupto y expuso los 26 días limpios reales, permitiendo que el gate corriera la validación de ventana. Al fallar el kernel, obligó a auditar la ventana de comparación (`07-13` a `07-16`), desenterrando la existencia del oráculo ilícito.

## Resolución (Cuarentena Permanente)
Dado que los datos de julio fueron vistos manual y repetidamente (tanto en este incidente como en el incidente del Atlas Nulo INC-002), se dictamina que:
**El rango `2026-07-01` a `2026-07-16` queda declarado en CUARENTENA PERMANENTE.**
Estos días ya no pueden conformar el holdout (porque fueron espiados), ni pueden formar parte del conjunto de estudio de pre-holdout (porque introducen contaminación vista). El filtro estructural reside en `universo_estudio.py`.
