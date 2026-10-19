# AVCL-VOL-3 — dosis-respuesta, compresión, ETH, estabilidad, agrupamiento, AT/OFF, magnitud — manifiesto — 2026-10-06

Aprobado por Nico en el chat del 2026-10-06 ("Si", a lanzar el kernel barato del punto 2 de la iteración 2).
Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Información de volatilidad y rango; **no P&L** ni dirección. Soporte/resistencia fuera de alcance.

## Datos
Cache de VOL-2 (`edgelab-avcl-cache-mnq-k1..k4`): MNQ 2025-07 → 2026-09, sesiones aprobadas, parámetros del indicador
congelados. Holdout no leído. Estimador: el de VOL-2 A1 (FE S0 + int10 + int50 + vol20 + vpk, SE por sesión).

## Pruebas formales (8, Holm, bilaterales)
- **H-a, dosis-respuesta (2):** pendiente de la interacción evento × z(log `anomaly_ratio`) sobre `y_rg` H10 RTH, en
  AT y en OFF. `anomaly_ratio` = score / umbral del detector. Pendiente > 0: más anomalía, más expansión.
- **H-c, compresión (4):** β A1 de `y_rv` a H50 y H200, RTH, AT y OFF. Bilateral; el signo esperado es negativo.
- **H-d, ETH formal (2):** β A1 de `y_rg` H10 en ETH, AT y OFF.

## Descriptivos (sin regla de decisión, no suman pruebas)
- **H-a bis:** dosis con `cluster_share`, `density`, ancho de zona, `quality_score`, `burst_count`; β por quintil de
  `anomaly_ratio`.
- **H-b:** β AT·`y_rg` H10 por contrato y por franja RTH (08:30–10:00, 10:00–13:00, 13:00–15:00 CT).
- **H-e:** zonas en ráfaga (`burst_count` ≥ 2) contra aisladas, y SE clusterizado por sesión × hora contra sólo
  sesión, para ver la sensibilidad de la inferencia a la dependencia.
- **H-f:** AT contra OFF: diferencia de β, distancia y ancho.
- **H-l:** exceso de rango en ticks = (e^β − 1) × rango previo medio de los eventos, a H10/H50, comparado con el costo
  de ida y vuelta en MNQ (USD 1,90 + 1 tick por lado ≈ 5,8 ticks).

## Justificación económica
Si la expansión crece con la intensidad de la anomalía, se puede filtrar por intensidad hasta superar el costo. Si es
estable en el tiempo y en ETH, el sello es utilizable en toda la sesión.

## Cómo podría refutarse
- Dosis plana o negativa: el efecto no escala con la anomalía, y la zona es un indicador binario débil.
- Efecto concentrado en un contrato o una franja: inestable.

## Registro
8 pruebas en la familia `AVCL_VOL1_CREATION_VOL`. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
