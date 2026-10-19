# Manifiesto VREV-A (reversión al VWAP tras agotamiento) y VCONT (continuación tras el primer alejamiento) — E1, 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Aprobación:** Nico en chat, 26/09: «probá la reversión tras agotamiento y la continuación».
**Origen:** VREV E1 (§6 de `MANIFIESTO_VREV_E1_20260926.md`) dejó abiertas las dos hipótesis. **Son familias propias**: no reinterpretan el resultado de VREV.
**Herramienta:** `tools/vrev2.py`. Ledger propio: `artifacts/hippocampus/vreva_vcont_20260926.jsonl` (`vrev2_20260926.jsonl` quedó como historial de un intento que falló al declarar particiones, antes de medir), con una partición por activo, `P-VREV2-<ACTIVO>-EXP`, compartida por las dos familias porque se miden en la misma corrida y sobre las mismas sesiones (dentro de un ledger las particiones no pueden superponerse). Las particiones no pueden superponerse dentro de un mismo ledger: la corrida en el ledger de VREV falló por eso, antes de medir.
**Regla de alcance (§0 de VREV, vigente):** conclusiones sólo por celda; estados INFO+ / INFO− / SIN_INFO (MDE ≤ 0,1) / SIN_POTENCIA; lista explícita de lo no medido.

## 0. Corpus consultado antes (Cerebro SSRN, local `E:\$ACerebroSSRN`, 26/09)
Sobre VWAP, el corpus sólo tiene **ejecución** (#4 «A Closed-Form Execution Strategy to Target VWAP»; #84 y #290, VWAP execution con deep learning). No hay trabajos sobre VWAP como señal de reversión o continuación. Coincide con la búsqueda web del 26/09: los institucionales lo usan como benchmark, no como alpha. Esto no dice nada a favor ni en contra: la prueba es empírica.

## 1. Evento base (común a las dos familias)
Primer alejamiento |cierre − VWAP| ≥ X·ATR (ATR de velas de 25 ticks, como en VREV), X ∈ {3, 4, 6}; se rearma tras volver a menos de X/2; fuera de las primeras 50 velas de la sesión.

## 2. VREV-A: reversión tras agotamiento
**Disparo** (dentro de 60 velas desde el alejamiento; el precio tiene que seguir a ≥ X/2 ATR del VWAP, si no, no hay entrada):
- **A1-10 / A1-20:** 10 o 20 velas sin nuevo extremo de la excursión;
- **A2:** retroceso de 1 ATR desde el extremo de la excursión;
- **A3:** la pendiente de 5 velas de la EMA(21) cambia de signo hacia el VWAP.

**Operación:** hacia el VWAP. Objetivo = VWAP en la vela de entrada. Stop = extremo de la excursión + k·ATR, con k ∈ {0,5; 1}.
**Justificación económica:** el primer alejamiento lleva inercia (VREV); si la inercia se agota lejos del VWAP, la referencia institucional vuelve a atraer el precio.
**Cómo podría refutarse:** el acierto no supera al control de mismo estado con la misma geometría.

## 3. VCONT: continuación tras el primer alejamiento
**Entrada** (alejándose del VWAP):
- **K0:** al cierre de la vela del alejamiento;
- **K1:** primer cierre con nuevo extremo dentro de 30 velas (la continuación se confirma).

**Operación:** objetivo a m·ATR más allá (m ∈ {2, 4}); stop a k·ATR hacia el VWAP (k ∈ {1, 2}).
**Justificación económica:** el primer cruce de un umbral de alejamiento marca flujo direccional que todavía no terminó.
**Cómo podría refutarse:** el acierto no supera al control de mismo estado con la misma geometría.

## 4. Medida, control y prueba (E1, economía incluida)
- **Acierto:** objetivo antes que stop en 200 velas o hasta el fin de sesión; si caen en la misma vela, cuenta como stop.
- **Secundarias:** R bruto, recorrido en ticks menos costo provisional (ES 1,4 · NQ 2,0 · YM 2,0 · MYM 3,0 t) y retorno direccional a 20, 60 y 200 velas.
- **Control:** 3 barras de otras sesiones, a la misma hora (± 1 h), con el mismo estado (distancia firmada al VWAP, pendiente de la EMA(21) y actividad: ±50 % o ±0,15 ATR), en la misma dirección y con **la misma geometría transferida en ATR** (objetivo y stop a la misma distancia en ATR).
- **Familias BH q = 0,10:**
  - VREV-A: 3 X × 4 disparos × 2 k × 4 activos = **96**;
  - VCONT: 3 X × 2 entradas × 2 m × 2 k × 4 activos = **96**.
- **Pasa a E2:** INFO+, R bruto real > R bruto del control, recorrido neto de costo > 0 y el mismo signo en las dos mitades.

## 5. No medido (queda abierto)
X en escala diaria o en bandas σ del VWAP; VWAP anclado; disparos de flujo (delta, absorción, L2); salidas por tiempo o trailing; objetivos parciales; velas de tiempo; filtros de régimen (tipo de día, gap); otros activos.

## 6. Resultado E1 (26/09; `artifacts/vrev2/report_e1.json`, sha `4affcca82cd0`, cobertura de controles ≥ 99 %, auditoría PASS)

### VREV-A (reversión tras agotamiento): 0 INFO+ · 33 INFO− · 63 SIN_INFO
Con los cuatro disparos de agotamiento (10 o 20 velas sin nuevo extremo, retroceso de 1 ATR, giro de la pendiente de la EMA21), X de 3 a 6 y stop detrás del extremo, **ninguna celda llega al VWAP más que el control** del mismo estado. Las INFO− se concentran en ES (el agotamiento no borra la inercia) y en X = 6 de MYM y YM. El neto de costo es negativo en todas.
**Alcance:** sólo estos disparos y esta geometría. Sigue abierto: agotamiento por flujo (delta, absorción, L2), X en escala diaria o por bandas σ, VWAP anclado y objetivos parciales.

### VCONT (continuación tras el primer alejamiento): 8 INFO+ · 19 INFO− · 69 SIN_INFO
- **Las 8 INFO+ son todas del Dow (MYM e YM) con X = 6**, sin ninguna en ES ni NQ. Ejemplos: YM K1 m2 k2, 53,4 % contra 45,0 % (+8,4 pts); MYM K1 m2 k2, 53,2 % contra 46,6 %; YM K0 m2 k1, 36,5 % contra 32,8 %. Hay coherencia entre los dos contratos del mismo subyacente.
- **Ninguna pasa a E2:** el neto de costo es negativo en todas (la mejor, YM K1 X6 m4 k2, −0,2 t).
- En ES y NQ, las INFO− se concentran en objetivos lejanos con stop corto (m4 k1): la continuación hasta 4 ATR con 1 ATR de riesgo ocurre **menos** que en el control.

**Lectura por celda:** en el Dow, con alejamientos grandes (6 ATR de vela de 25 ticks), hay información de continuación medible pero chica, que con estas geometrías no paga el costo. No se generaliza a «la continuación funciona en el Dow» ni a «no funciona en ES».
**Queda abierto:** geometrías con más recorrido (trailing, objetivos por estructura), X > 6 y en escala diaria, filtros de régimen, y la réplica de la pista del Dow en abr–jun, que sólo tendría sentido con una geometría que pague el costo en exploración.
