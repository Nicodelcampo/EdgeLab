# AVCL-PRE — expansión con la ventana previa FUERA del bloque creador — manifiesto — 2026-10-06

Aprobado por Nico en el chat ("Si correla"). Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.

## Por qué
En todas las mediciones previas, `y_rg` = log(rango de las H barras siguientes / rango de las H barras previas), y la
ventana previa **termina en la barra de creación**. En AVCL, con W = H = 10, esa ventana es exactamente el bloque
creador; con W = 20 queda dentro del bloque. La anomalía de W20 en AVCL-CIERRE (AT +0,25, OFF negativo) sugiere un
artefacto de geometría: la condición de creación (dónde cierra el precio respecto del cluster) puede seleccionar bloques
con un final comprimido o expandido y mover el cociente **sin que cambie el futuro**. En VTD, la barra marcada está
dentro de la ventana previa.

## Métrica corregida (target-free respecto del P&L)
`y_rg_pre_H = log((rango de [b+1, b+H] + 1) / (rango de [bs−H, bs−1] + 1))`, donde bs es el **inicio del bloque
creador** (AVCL: la barra siguiente al bloque anterior o el inicio de sesión; VTD: la barra marcada). Ventanas en la
misma sesión. Cola sin signo con R = rango de la ventana previa corregida. En la misma muestra se reporta también la
métrica vieja, para ver cuánto cambia.

## Datos
Caches ya calculados (`edgelab-avcl-grid-mnq-k1..k4`: 13 celdas AVCL; `edgelab-vtd-mnq-k1..k4`: VTD 50t/150t). MNQ,
RTH formal, mismo estimador (FE S0 + int10 + int50 + vol20 + vpk, SE por sesión).

## Pruebas formales (8, Holm, bilaterales)
- AVCL base: AT A1, AT A2, OFF A1, OFF A2 (`y_rg_pre` H10).
- AVCL W20: AT A1, OFF A1. Si el artefacto es real, la anomalía desaparece.
- VTD 150t A1 y VTD 50t A1.

Descriptivo: las 13 celdas + VTD, colas, H50, ETH.

## Lectura pre-registrada
- Si la base mantiene un β > 0 significativo con `y_rg_pre` → la expansión **no** era un artefacto de la ventana.
- Si cae a ≈ 0 → los resultados de expansión de AVCL-VOL-1/2/3, DIST y CIERRE quedan **invalidados en su magnitud** y
  hay que releerlos.
- W20: si se normaliza (AT y OFF del mismo signo y orden que la base), la anomalía era artefacto.

## Cómo podría refutarse
Lo de arriba es la refutación: la medición fue diseñada para poder matar el hallazgo principal.

## Registro
8 pruebas, familia `AVCL_PRE`. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
