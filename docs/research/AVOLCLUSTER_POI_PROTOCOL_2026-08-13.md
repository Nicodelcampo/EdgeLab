# aVolClusterPOI — masa de cluster, no celda ni trade (2026-08-13)

Estado: `PREREGISTERED_KERNEL_ONLY`
Spec: `specs/avolcluster_poi_v0.json`
NT8: `aVolClusterPOI.cs` v0.4 (prototipo visual)
Kernel: `edgelab/bridge/indicators/avolclusterpoi.py`

Complementa `aVolCellPOI2`. No cruza con BigTrap2.

## 1. Objeto

Niveles “hot” (volumen ≥ mediana del bloque × 2) contiguos se agrupan.
La **suma** del cluster se compara con el historial del mismo bucket horario
de sesiones **completas anteriores**. Sin historia del bucket: no detecta.

Eso no es un tick caliente (celda). Tampoco es un imán de BigTrap2.

## 2. Qué se mejoró respecto del .cs v0.4

El .cs es útil para ver. No es el kernel de investigación.

| En el .cs v0.4 | En research |
|---|---|
| percentil 95, min 5 muestras | percentil 98, min 20 muestras |
| QualityScore / LONG-SHORT / target-stop | fuera del detector |
| filtro predictivo opcional | prohibido en el kernel |
| dashboard de “aciertos” | no existe |

Min 5 muestras deja que un puñado de bloques fije el umbral. Misma lección
que aVolCellPOI2 v2.0: el gate tiene que pedir historia, no “que dibuje”.

## 3. Contrato que sí se conserva del .cs

- `OnBarClose`. La creadora no toca su zona.
- Ticks enteros. Sin claves double.
- Footprint = subserie 1-tick recortada al [low, high] de la barra.
- Bloques de `WindowBars`, anclados al inicio de sesión. El bloque parcial
  del final de sesión se descarta.
- Bucket: ancla en cierre − 1 s. SessionRelative default.
- Cuantil empírico sin interpolar.
- Sesión actual pending; se commitea en el roll. Primer roll descarta pending.
- Sin fallback a cola global entre horas.

## 4. Primer éxito

Los tests de cluster / warmup / no look-ahead. No un chart más poblado.
Formal sobre 6E: después, target-free, mismas reglas de ceros y placebo que
F2.7–F2.10. Sin P&L. Sin cruce.

## 5. El .cs en NT8

Se puede seguir usando para ver clusters. Dejar `EnablePredictiveFilter=false`.
No leer el % target/stop del dashboard como evidencia.
