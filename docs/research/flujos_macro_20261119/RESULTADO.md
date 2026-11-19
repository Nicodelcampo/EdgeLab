# FLUJOS-MACRO (Carril 1): FM1 y FM2 tienen bruto real pero neto negativo; REP sin potencia (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (16 pruebas en `FLUJOS_MACRO_A5`, linaje enmendado por Claude antes de correr). North Star
sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `CALIBRACION.json` (v2), `CORRIDA.json`, `DESC.json`,
`OPS_DESC_REP.csv.gz`. Módulo de Antigravity `edgelab/research/flujos_macro_a5.py`.

## 0. Integridad
- **Bug K53 encontrado y corregido antes de correr:** FM6/FM6N no disparaban nunca en datos reales (la sesión CME empieza 18:00 del día
  previo y `mo >= 495` tomaba esa vela; el test sintético no cruza medianoche). Corregido con un test con M1 real que falla con el código
  viejo; la calibración v1 quedó archivada como descartada (`descartada_calib_v1/`). Guarda nueva: `a5_campana.calibracion` frena si una
  definición no dispara en la calibración.
- Calibración v2: 12/16. No calibran FM5, FM7, FM6N y FM7N (no pueden nominarse). **Pendiente de revisar:** en FM7/FM7N sólo 42 de 209
  sesiones coinciden entre M1 y ticks, una discrepancia de generación de eventos (no sólo de desenlaces) que conviene investigar antes de
  cualquier uso de FM7. **Causa raíz (2026-11-19, K54):** el kernel de ticks no tenía el parquet de CBOE (vix_prev vacío en las 4 tablas
  de ticks) y el módulo cayó en silencio al respaldo RV5 (FM7) y ATR/cierre (stop de FM1). La calibración de las reglas que usan VIX
  (FM1, FM7) comparó reglas distintas y no vale; no cambia ningún veredicto (FM1/FM2 neto negativo, FM7 no nominable). Guardas en
  `a5_campana.insumos_distintos` y `tablas.insumos_externos`.

## 1. DESC (ES+NQ+YM+GC, meses DESC de A5)
| | R bruto | p | años + | R neto | fricción R | neto operable | Nominada |
|---|---|---|---|---|---|---|---|
| FM1 canal VIX9D/VIX (10:00) | +0,022 | 0,0008 | 70 % | −0,016 | 0,038 | −0,012 | sí |
| FM2 banda ATR desde la apertura | +0,057 | 0,003 | 80 % | −0,008 | 0,065 | +0,037 | sí |
| FM1 − FM1N (fade de los primeros 30 min) | +0,044 | 0,001 | | | | | sí |
| FM8 último tramo en días de desplazamiento | +0,034 | 0,026 | 65 % | −0,036 | 0,070 | | no (BH) |
| FM3, FM4, FM5, FM6, FM7 | −0,019 a +0,029 | ≥ 0,15 | | negativo | | | no |
- **REP no se leyó (K49):** potencia en días 0,06–0,07 para las tres nominadas.

## 2. Lectura
- FM1 y FM2 son momentum de apertura / sesgo del día: la misma familia que RQ5 (banda de ruido de Zarattini), T y R. Tienen bruto real y
  estable, pero con su ejecución intradía la fricción se come el neto; el stop y el tamaño ya se mostraron no-palancas para este tipo de
  ventaja (F-VENTAJA-EN-PUNTOS-NO-ESCALA, TAMANO-K52).
- FM6 (caja Asia→Londres en oro) ya corregido da bruto negativo (−0,019): no hay ventaja en esa ruptura.
- No hay candidata operable en el Carril 1 de este catálogo.
