# Plan — más potencia con historia de NT8 (sin traducir estrategias)

Estado: PROPUESTA (2026-10-26). Pedido de Nico: «agregarle un módulo que traduzca los hallazgos a estrategias de NT8 para correrlas en
el Strategy Analyzer y tener más datos; para los CFD, JForex».

## Decisión de diseño: usar NT8 como FUENTE de datos, no como motor
Traducir cada regla a NinjaScript obliga a probar paridad estrategia por estrategia (fills límite, tope, costos) y cada diferencia
puede ser del traductor y no del mercado. Lo que da potencia son los **datos** viejos, no el motor de NT8. El repo ya tiene el camino:
- `nt8_tools/EdgeLabTickHistory.cs` (AddOn): baja ticks históricos (trade + bid/ask vigente) del servidor de la conexión de NT8, un archivo
  por día en UTC declarada, con manifiesto y sha256; modo **Probar** (un día por semana, sin escribir) para ver hasta dónde llega.
- El constructor de la release (`liquid_tick_v1`) ya lee ese formato; `fuentes_ticks.bloques_futuro` lee el resultado.
Con eso, las MISMAS celdas corren con el MISMO motor sobre historia nueva: paridad por construcción.
La traducción a NinjaScript queda para cuando haya algo confirmado y haga falta operarlo en vivo.

## Pasos
1. **Nico, en NT8**: AddOn EdgeLabTickHistory → Probar para NQ, ES y YM (y MNQ/MES/MYM si hace falta) desde 2018. Dice hasta dónde hay ticks.
2. **Nico**: exportar el tramo que haya entre esa fecha y 2025-07 (antes del release actual).
3. **Agente**: construir la extensión de la release con esos días, verificar (`tools/verify_release.py`), subir como dataset nuevo.
4. **Agente**: ATRAS (`tools/atras_celdas.py`, agregando las campañas a `CAMPANAS`) para EXPZ-NQ, ZGAP-NQ, U1-ZONAS-ES/NQ y AVCL-ES/NQ,
   con pre-registro propio como el de `PREREGISTRO_ATRAS.md`.
5. **CFD**: Dukascopy ya está en Kaggle desde 2023-01; para antes de 2023, `tools/dukascopy_descarga.py` (o JForex) cuando se pueda
   descargar. ATRAS de EXPZ-CFD y ZGAP-CFD sobre 2023-01 → 2025-08 ya está corriendo.

## Límite que no cambia
Historia vieja responde «¿funcionó antes?» (estabilidad), no «¿funciona ahora?». Por la regla de régimen (ATJ-24), el pasado no mata;
la confirmación sigue siendo el holdout a N fijo y después el paper.
