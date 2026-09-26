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

### Enmienda de cobertura del control (26/09, ANTES de mirar retornos)
Con MYM, la tolerancia de estado ±25 % / ±0,1 ATR y la búsqueda en 40 sesiones al azar dejaban **sin control al 68 %** de los eventos. El resto habría sido un subconjunto sesgado. Mirando sólo la cobertura (target-free):
1. el control se busca en **todas** las otras sesiones, en orden aleatorio (cobertura 59 %);
2. la tolerancia pasa a **±50 % / ±0,15 ATR** (cobertura **94 %**, 81 % con 3 controles).

Los eventos sin control no difieren en los filtros (medianas: 94 contra 113 velas del otro lado, 2,48 contra 2,46 ATR de alejamiento). No se miró ningún retorno antes de este cambio.

## 6. Resultado E0–E1 (26/09; `artifacts/evx/report_e1.json`, sha `014c4ed67893`, auditoría de controles PASS)
- **E0:** todas las celdas pasan el censo. Cruces por día: MYM 3,7–14 · YM 3,2–12 · ES 11–43 · NQ 6,9–26, según el período de la EMA.
- **E1:** **0 de 448** celdas pasan BH-FDR. **Ninguna pasa a E2.** Media de las diferencias −0,014 ATR; 41 % positivas (lo esperable por azar, o algo peor). Las celdas más «significativas» sin corregir son **negativas**: ES EMA55, a 20–60 velas, el cruce rinde menos que el control (−0,1 a −0,27 ATR).
- **Potencia:** MDE mediano 0,49 ATR. Se descarta un efecto direccional del cruce **mayor que ~0,5 ATR** en estos horizontes; uno menor no se puede distinguir con 6–9 meses de datos (y sería muy chico frente al costo).
- **Canal no direccional:** el movimiento absoluto después del cruce no es mayor que el del control con el mismo estado.

**Conclusión (alcance preciso):** con la EMA en 21, 55, 144 o 377 velas de 25 ticks, en MYM, YM, ES y NQ, en exploración, **el cruce EMA × VWAP no aporta información direccional** frente a una barra con el mismo estado (pendiente, distancia a la EMA y al VWAP, actividad) a la misma hora de otra sesión. Tampoco con los filtros de tiempo, alejamiento o volumen. El embudo se detiene en E1, como estaba pre-registrado: E2–E5 no se corren. No se tocó abr–jun ni el holdout.
