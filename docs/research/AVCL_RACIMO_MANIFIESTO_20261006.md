# AVCL-RACIMO — ¿las zonas agrupadas en tiempo y espacio tienen efecto propio? — manifiesto — 2026-10-06

Aprobado por Nico ("dale me sirve"). Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Información, **no P&L**. Origen: capturas de MNQ 25t con zonas apiladas (`[R x4]`, `[R x5]`) seguidas de movimientos fuertes.

## Población (enumeración previa)
Eventos AVCL: creación (aislada o en racimo), toque, salida, invalidación y estado. Se congela **la creación**, partida
en **en racimo** contra **aislada**. Unidad: cada zona creada.

## Criterios de racimo (fijados antes de medir, por conteo y sin mirar resultados)
- **Principal:** el del propio indicador, `burst_count ≥ 3`: al menos 3 zonas, incluida la actual, creadas en las
  últimas 200 barras con centros a ≤ 40 ticks. Es lo que el chart muestra como `[R xN]`.
- **Secundario (apilamiento denso):** al menos 3 zonas en las últimas 120 barras con bandas superpuestas o a ≤ 8 ticks.
- **Aislada:** `burst_count = 1` y ninguna otra zona en ±200 barras a ≤ 40 ticks.
- Conteos en MNQ 12-26 25t: principal 33 % de las zonas; secundario 8 %.

## Datos
- **Principal:** MNQ 50t (paridad validada), celda base (p95, W10, None, MaxAge 500), cache
  `edgelab-avcl-grid-mnq-k1..k4`, 6 contratos, RTH.
- **Réplica exploratoria:** MNQ 25t (el chart de Nico; paridad no validada a 25t).
- Holdout no leído.

## Resultados (todas sin el artefacto de AVCL-PRE)
- `y_pre_H` = log(rango [b+1, b+H] / rango [bs−H, bs−1]), con **bs = inicio del bloque de la PRIMERA zona del racimo**.
  Para las aisladas, el de su propio bloque.
- Excursiones U/D desde el close de creación en H barras.
  - OFF: `s_H = lado × (U − D)/(U + D)`, con s > 0 = se aleja (rechazo) y s < 0 = vuelve y atraviesa.
  - Cola sin signo: \|close[b+H] − close[b]\| ≥ rango previo (ventana fuera del racimo).
- H ∈ {10, 50}.

## Estimador
β de racimo contra aislada, con FE (contrato × franja de 30 min, tercil de amplitud relativa, decil de volumen del bloque).
SE por sesión. Bilateral.

## Pruebas formales (8, Holm) — criterio principal, 50t
- `y_pre` H10 y H50, AT y OFF (4).
- `s` H10 y H50, sólo OFF (2).
- Cola sin signo H10, AT y OFF (2).

## Descriptivos
- Criterio secundario.
- Dosis (burst 3 / 4 / ≥ 5).
- Racimo de lado homogéneo contra mixto.
- 25t completo.
- Comparación contra barras al azar.

## Justificación económica
La concentración repetida de volumen anómalo en el mismo nivel y en poco tiempo puede marcar un nivel de inventario
grande. Si se rompe, desencadena un movimiento más largo (stops/liquidación); si aguanta, el rechazo es más firme.

## Cómo podría refutarse
β ≈ 0 en todas, con el MDE publicado: el racimo no se distingue de una zona aislada en el mismo contexto.

## Registro
8 pruebas, familia `AVCL_RACIMO`. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
