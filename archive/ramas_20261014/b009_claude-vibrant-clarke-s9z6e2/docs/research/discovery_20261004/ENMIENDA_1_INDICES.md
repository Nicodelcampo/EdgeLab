# Enmienda 1 al pre-registro de familias: grupo de índices (IDX)

Estado: escrita **antes** de barrer IDX. Se agrega a `PREREGISTRO_FAMILIAS.md` (commit `39d0b78b`); no cambia ninguna especificación ni hash de las cinco familias.

## Por qué existe
El primer barrido (15 combinaciones: GC, ZB, FX) no incluyó futuros de índices sin que el pre-registro diera una razón. Fue una omisión de alcance, no una decisión técnica. El usuario pidió incluirlos.

## Qué se agrega
- **Grupo `IDX` = ES + NQ + YM**, fijado ahora y sumado por sesión en ticks de cada activo, igual que FX (`pool_cells`). Configuración en `config/discovery/assets/{ES,NQ,YM}.json` y `config/discovery/groups.json`.
- **MNQ queda afuera de este barrido, y es una desviación respecto de lo que se propuso en la conversación (ES, NQ, MNQ, YM).** Motivo: MNQ es el mismo índice que NQ a un décimo del tamaño; sumarlo no aporta evidencia independiente y duplicaría el peso de NQ. Además, su comisión de USD 4,50 por contrato completo no tiene sentido sobre un contrato de USD 0,50 por tick. Si se quiere MNQ, va como enmienda propia, con comisión de micro.
- Cinco combinaciones nuevas (5 familias × IDX): **69.888 celdas** (una rejilla por familia, el pool la cuenta una vez) en el contador de pruebas.
- Mismas semillas, hashes, partición D0/D1/D2 (D2 sellado), costos (USD 4,50 por contrato completo: ES 0,36 ticks, NQ 0,90, YM 0,90), guarda de retraso y elegibilidad por volumen.
- Datos: `edgelab-ticks-{es,nq,ym}-preholdout`, corte estricto `< 2026-06-30T22:00Z`. No se lee nada desde julio ni el holdout formal.

## Qué cambia en la regla de decisión
Holm del punto (i) pasa de **15 a 20** `p_max` (5 familias × 4 grupos). Consecuencias, dichas de antemano:
1. Los 15 resultados ya obtenidos se conocían cuando se escribe esto; la enmienda **solo endurece** el umbral para ellos (15 → 20), así que ninguno puede pasar de «no pasa» a «pasa». El menor Holm ajustado de GC sube de 0,112 a ≈ 0,15.
2. Los puntos (ii), (iii) y (iv) no cambian.
3. Los resultados de IDX no se conocen al escribir esto. Hay una expectativa débil: la estrategia del proveedor, aplicada a estos activos, no funcionó, y las aperturas del holdout de ES/NQ/MNQ ya se consumieron. Eso no usa nada de lo que este barrido calcula.

## Calibración sobre IDX (antes de barrer; base neutralizada, 40 repeticiones, 235 sesiones)
| Familia | Celdas | Falsos positivos (de 40) | Detección a 0,1 / 0,2 / 0,3 / 0,5 desvíos por operación |
|---|---:|---:|---|
| f1_momentum | 4.992 | 2 | 0,05 / 0,40 / 0,60 / 0,60 |
| f2_vwap | 4.992 | 2 | 0,00 / 0,45 / 0,45 / 0,70 |
| f3_flujo_absorcion | 23.424 | 2 | 0,00 / 0,25 / 0,40 / 0,75 |
| f4_regimen | 19.968 | 3 | 0,05 / 0,20 / 0,50 / 0,65 |
| f5_medias | 16.512 | 4 | 0,00 / 0,25 / 0,65 / 0,75 |

Lectura: los falsos positivos son compatibles con el 5 % nominal (4 de 40 tiene una probabilidad ≈ 13 % bajo el 5 %). La detección con 20 repeticiones por punto es ruidosa (por ejemplo 0,60 a 0,3 y a 0,5 en f1): no se ordenan los efectos con ese ruido. Es algo mejor que en GC en 0,2 a 0,3 desvíos, probablemente por las 235 sesiones y la suma de tres activos, pero sigue siendo baja por debajo de ≈ 0,3.

## Costo de cómputo
El armado de tensores de IDX tarda ≈ 190 s por barrido y llega a ≈ 13 GB de memoria (límite de 15 GB): los barridos se corren en serie. El nulo en sí tarda segundos; la GPU no aporta nada a esta escala (≈ 70.000 celdas por activo): el tiempo está en leer ticks, no en el nulo.
