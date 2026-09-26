# Manifiesto VREV-A (reversión al VWAP tras agotamiento) y VCONT (continuación tras el primer alejamiento) — E1, 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Aprobación:** Nico en chat, 26/09: «probá la reversión tras agotamiento y la continuación».
**Origen:** VREV E1 (§6 de `MANIFIESTO_VREV_E1_20260926.md`) dejó abiertas las dos hipótesis. **Son familias propias**: no reinterpretan el resultado de VREV.
**Herramienta:** `tools/vrev2.py`. Ledger propio: `artifacts/hippocampus/vrev2_20260926.jsonl`, con particiones `P-VREVA-*` y `P-VCONT-*`. Las particiones no pueden superponerse dentro de un mismo ledger: la corrida en el ledger de VREV falló por eso, antes de medir.
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
