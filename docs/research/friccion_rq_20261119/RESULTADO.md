# FRICCION-RQ: ensanchar el stop no baja la fricción de RQ5/RQ6 (su ventaja es un monto fijo en puntos); el tamaño de la posición sí puede (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (18 pruebas en `ROBOQUANT_A5`; registra un lanzamiento descartado antes del conteo).
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `RESULTADO.json`, `OPS.csv.gz` (sólo DESC,
ES + NQ + YM, 2006–2025). Etapa EF3; REP y holdout sin leer. Nota de procedencia: después de lanzar esta corrida se agregó a
`tools/friccion_rq.py` sólo la guarda `exigir_contada` al inicio (K51), que no cambia ningún cálculo.

## 1. Curva bruto–stop (decisión pre-registrada)
| Regla | m = 1 (bruto / fricción / neto) | m = 1,5 | m = 2 | m = 3 | cierre m=2 | Veredicto |
|---|---|---|---|---|---|---|
| RQ5 banda de ruido | +0,062 / 0,073 / −0,011 | +0,040 / −0,009 | +0,029 / −0,007 | +0,018 / −0,007 | −0,008 | **TIMING** |
| RQ6 retroceso al VWAP | +0,054 / 0,084 / −0,029 | +0,033 / −0,023 | +0,027 / −0,015 | +0,018 / −0,009 | −0,014 | MEJORA_SIN_NETO |
| RQ2 reversión al mínimo previo | +0,073 / 0,090 / −0,017 | +0,068 / +0,008 | +0,061 / **+0,016** (IC90 inf −0,016) | +0,042 / +0,012 | +0,005 | MEJORA_SIN_NETO |
- En RQ5 y RQ6 **el bruto cae a la par de la escala: el bruto en puntos no cambia** (RQ5 NQ: +5,1 · +5,5 · +6,9 · +6,1 pts con m = 1 → 3;
  ES ≈ +1,4–1,5). La ventaja es un monto fijo por operación, no una fracción del stop: agrandar el stop sólo cambia la unidad.
- RQ2 conserva más bruto al ensanchar y su neto llega a +0,016 R con m = 2, pero el IC90 inferior (−0,016) no pasa la regla.

## 2. Otras palancas (descriptivo, sin decisión)
- **Una operación por día:** las tres reglas ya operan una vez por día e instrumento; no hay nada que podar.
- **RQ5 + RQ6 en una sola posición cuando coinciden:** empeora (neto −0,071 contra −0,021 separadas). En los 4.943 días en que coinciden de
  lado el bruto medio es ≈ 0: la ventaja está en los días en que dispara una sola.
- **Salir en el objetivo con orden límite** (sin medio spread ni slippage de salida): +0,000 a +0,012 R. Casi nada, porque la mayoría
  sale por stop o al cierre. Cambiar el modelo canónico sería semántica de validación (Nico); queda sólo como sensibilidad.
- **Entrada con orden límite:** no se midió (F-SELECCION-ADVERSA-PASIVA: ≈ −0,07 R de selección adversa).

## 3. Hallazgo fuera de la decisión: el tamaño de la posición (exploratorio, cambio de estimando después de mirar)
El R medio por operación supone riesgo constante (tamaño ∝ 1/stop): las operaciones de stop chico pesan mucho y ahí la fricción se lo come
todo. Con **un contrato fijo** (P&L en puntos), m = 1:
| | ES neto pts/op (t) | NQ neto pts/op (t) | YM | R como cociente de sumas (ES / NQ) |
|---|---|---|---|---|
| RQ5 | +0,60 (1,4) | **+3,57 (2,0)** | −1,26 | +0,041 / +0,068 |
| RQ6 | +0,35 (1,0) | +2,35 (1,8) | +0,13 | +0,028 / +0,052 |
| RQ2 | −0,19 | −6,66 (−2,1) | −0,43 | negativo |
- RQ5 y RQ6 sí pagan la fricción en ES y NQ con tamaño fijo; RQ2 no (su R positivo venía de stops chicos). YM no paga en ninguna.
- Es exploratorio: el estimando se cambió después de ver la curva y los puntos de NQ pesan más los años recientes (precio más alto). Es
  coherente con la palanca ya confirmada F-STOP-CORTO-ES-FRICCION (contrato fijo sube el t medio). **Siguiente paso:** pre-registrar
  RQ5 + RQ6 en ES + NQ con tamaño fijo o ∝ 1/√riesgo, estimando = R como cociente de sumas, y planificar su lectura de REP + holdout con
  K49 (potencia en días) antes de abrir nada.
