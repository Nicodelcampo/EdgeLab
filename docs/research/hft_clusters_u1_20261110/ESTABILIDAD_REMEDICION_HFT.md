# Re-medición con estabilidad (regla 08/11) de las tablas HFT ya corridas

Estado: RESULTADO (2026-11-10). Cambio de medición `CM-ESTABILIDAD-SUB-BLOQUES` (`docs/research/CAMBIOS_DE_MEDICION.jsonl`), lente
`remedir`. Sin datos nuevos: re-lectura de `HFTC_rebotes.csv` (7 definiciones de rebote, clusters grandes, NQ/ES, DESC) y
`HFTC_info.csv` (rebote e imán con clusters de 4 zonas, NQ/ES/GC/YM, DESC). Medida: real − control por sesión (+ = el objeto
REBOTA más que un nivel cualquiera), 5 sub-bloques cronológicos, p de inversión de signo por sesión. Cifras:
`ESTABILIDAD_REMEDICION_HFT.json`.

## Rebote en clusters grandes (HFT-REBOTES): la hipótesis va AL REVÉS, de forma estable
| Definición | Sesiones | Real − control | Bloques + | p (rebote > control) |
|---|---|---|---|---|
| D0 primer regreso | 199 | −0,107 | 1/5 | 0,97 |
| D1 fresco y lejano | 111 | −0,180 | 1/5 | 0,99 |
| D2 aceptado y abandonado | 110 | −0,076 | 2/5 | 0,79 |
| D6 penetración fallida | 139 | −0,084 | 0/5 | 0,90 |
| D5 deriva | 39 | −0,366 | 0/5 | 0,96 |
| D3 rechazado al nacer / D4 memoria | 22 / 43 | +0,19 / +0,01 | 2/5 / 3/5 | 0,16 / 0,48 |

## Clusters chicos (paso de información): el mismo signo en los cuatro activos
Rebote real − control: −0,057 (535 sesiones, 1/5 bloques +); NQ −0,063, GC −0,050, YM −0,161, ES −0,012. Imán: +0,016 (3/5,
p 0,21; YM +0,105, 4/5, p 0,13): nada.

## Lectura
Ninguna definición de rebote se rescata con la regla de estabilidad: lo estable es lo contrario. Donde hubo actividad HFT (clusters
grandes o chicos, en NQ, GC, YM y en menor medida ES) el nivel **rebota menos** que un nivel cualquiera de la sesión. Es la misma
cuerda que `ESTABILIDAD_CLUSTERS.md` (real − control en ruptura) y que pone a prueba la confirmación congelada
(`CONFIRMACION_NO_DEFIENDE.md`) y la familia `REBOTE_NIVEL_SESION` (distancia a zonas como parámetro). D3 (rechazado al nacer,
+0,19 con 22 sesiones) queda como observación sin muestra.
