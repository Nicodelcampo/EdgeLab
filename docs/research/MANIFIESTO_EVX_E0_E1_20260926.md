# Manifiesto EVX (cruces EMA × VWAP) — registro de familia y etapas E0–E1, 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Aprobación:** Nico en chat, 26/09: «OK al embudo, SL/TP en ATR, registrá EVX y lanzalo». Cubre la regla STOP para mirar retornos **dentro de este embudo**.
**Diseño completo:** `docs/research/DISENO_EMA_VWAP_CRUCES_20260926.md`. Herramienta: `tools/evx.py`. Ledger: `artifacts/hippocampus/evx_20260926.jsonl`.

## 1. Registro de la familia EVX
- **Indicadores:** EMA(p) de cierres de velas de 25 ticks; VWAP de sesión con precio típico (H+L+C)/3, que se reinicia en la pausa diaria (hueco > 30 min).
- **Evento:** la EMA cambia de lado respecto del VWAP, fuera de las primeras 50 velas de cada sesión. Dirección: la del nuevo lado.
- **Subfamilias habilitadas:** p ∈ {21, 55, 144, 377}.
- **Ledger propio. No hereda nada** de TBZ, TBZX, TREND-MICRO ni de otras familias: ni poblaciones, ni costos, ni presupuesto de multiplicidad.
- **Event-space considerado** (regla de población): cruce (**elegido para E1**); estado «EMA del lado X» en cada vela (descartado para E1: el estado es otra pregunta, que queda para después); alejamiento máximo; regreso a la EMA o al VWAP (son modos de entrada de E2); cruce opuesto (es una salida). Se congela el **cruce como evento** porque es la regla que Nico quiere operar.
- **Justificación económica:** el VWAP de sesión es la referencia de precio institucional; que la EMA lo cruce después de un tramo largo o alejado indicaría un cambio de control del flujo.
- **Cómo podría refutarse:** el retorno direccional después del cruce no supera al de barras del mismo estado (misma pendiente de la EMA, misma distancia del precio a la EMA y al VWAP, misma actividad previa) en otras sesiones a la misma hora.

## 2. Datos y particiones
MYM (Lucid, canonizado, oct-2025 a mar-2026), YM, ES y NQ (research-v2 con contrato canónico, jul-2025 a mar-2026). Particiones `P-EVX-<ACTIVO>-EXP` (rol EXPLORATION), declaradas en el ledger antes de medir. Abr–jun y el holdout quedan cerrados.

## 3. E0 — censo (target-free)
Por activo y período: cruces por día, eventos totales y terciles de los filtros. **Descarta** la combinación si hay < 1 cruce por día o < 300 eventos.

## 4. E1 — información (sin P&L)
- **Retorno:** dir · (cierre[i+h] − apertura[i+1]) / ATR, con h ∈ {5, 20, 60, 200} velas. ATR = media exponencial (100 velas) del rango verdadero de las velas de 25 ticks, causal en i. Si el horizonte cruza el final de la sesión, el evento sale de esa celda (se cuenta cuántos).
- **Filtros (7, de a uno):** ninguno; tiempo del otro lado ≥ T1 / ≥ T2; alejamiento máximo |EMA − VWAP| / ATR ≥ T1 / ≥ T2; volumen desde el cruce anterior ≥ T1 / ≥ T2. Terciles del propio activo y período, calculados sobre la distribución de eventos (target-free).
- **Control:** 3 barras de otras sesiones, a la misma hora (± 1 h), con el **mismo estado** (a ± 25 % o ± 0,1 ATR): pendiente de 5 velas de la EMA, (precio − EMA)/ATR, (EMA − VWAP)/ATR y actividad previa (rango y duración de las últimas 20 velas). Mismo cálculo de retorno con la dirección del evento. Control de otra sesión: exento de CTRL_TIMING_V1, auditado igual.
- **Dos canales:** direccional (media del retorno) y no direccional (media de |retorno|), más la distribución completa.
- **Prueba:** diferencia pareada real − control, bootstrap por sesión (2.000 réplicas), IC 95 % y MDE. Familia E1: 4 períodos × 7 filtros × 4 horizontes × 4 activos = **448**, BH q = 0,10 sobre el canal direccional.
- **Pasa a E2** la celda (activo, período, filtro) con al menos un horizonte que pase FDR con signo positivo, y con el mismo signo en las dos mitades del período.

## 5. Lo que sigue (ya pre-registrado en el diseño)
E2 (P&L bruto de entradas × salidas, con control de entrada al azar con las mismas salidas), E3 (neto con costos propios), E4 (PBO, DSR, mesetas) y E5 (abr–jun, ≤ 3 configuraciones), sólo sobre los sobrevivientes de E1.

### Nota de implementación (26/09, antes de medir)
La caché de velas no guarda la apertura. En velas de tick contiguas, la apertura de i+1 es el trade siguiente al cierre de i (a ±1 tick). E1 usa el **cierre de i** como referencia, y la diferencia se absorbe igual en el evento y en el control. El ATR de 25 ticks tiene un piso de 1 tick.
