# IDEA (registrada, NO ejecutada): zonas escalonadas chicas en ES + entrada en el retroceso — 2026-09-29

## Definición (de 45 marcas de Nico, ES 03-26, sesión 1–2/02/2026, 17:57–23:59 CT)
3 picos (38) o 4 (7); escalón a favor mediana 1 tick (0–3); total 2 ticks; 11 velas (6–31); retroceso entre picos
mediana 6,5 ticks (3–13,5); vela típica 2,5 ticks. 29 techos / 16 pisos.

**Detector ajustado a esas marcas** (`peaks_rule.series`, negativos = sólo huecos entre marcas, por indicación de Nico):
w 2, max_gap 15, max_step 3 ticks, min_pull 6 ticks, nmin 3, extensión hacia atrás, ≤ 35 velas entre primer y último pico.
F1 0,49 (precisión 0,47, cobertura 0,51) sobre las marcas: **coincidencia moderada**; ≈ 74 zonas/día en feb-2026.
Capa del visor: `bundles/peaks_det/ES_03-26_202602_25T_HFT.json` (local). Siguiente: juicio ✓/✗ de Nico.

## Observación de Nico (look-ahead, reconocido)
Tras los picos el precio casi siempre se va sin volver a tomarlos. Descriptivo sobre sus marcas: MFE/MAE medianos
14/2 ticks a 30 velas; carrera +8 vs ruptura del último pico 39/45 a favor. **Sesgado por marcar con el gráfico completo.**

## Estrategia propuesta (hipótesis)
Detectar con **2 picos** y entrar **en el retroceso** apostando a que se forma el 3.º/4.º pico y luego la salida; stop
apenas detrás del último pico (pocos ticks) → R:R potencialmente alto.
**Justificación económica:** absorción pasiva escalonada que cede de un lado.
**Cómo podría refutarse:** con detección causal a 2 picos, la tasa de 3.º pico + salida no supera al control emparejado,
o el R neto (comisión, spread 1 tick, fills límite en cola, slippage del stop) es ≤ 0 en replay tick a tick.

## Riesgos escritos antes de medir
Selección con hindsight en las marcas; stops de 2–4 ticks en ES son del orden del spread + comisión (el costo pesa
mucho sobre R); fills de límite en el retroceso dependen de la cola (P2 de GC: −0,034 W por llenado); multiplicidad
(variantes de 2/3/4 picos, retroceso, stop). **Mira outcomes: manifiesto + OK de Nico. Febrero = descubrimiento.**

## Actualización 29/09 — dos familias, dos detectores (juicios de Nico)
- **PLANAS v2** (marcas iniciales + 27 ✓ / 56 ✗): w 2, max_gap 15, escalón ≤ 2 ticks, retroceso ≥ 5, ≥ 3 picos,
  ≤ 35 velas. F1 0,60 (precisión 0,63 sobre juicios). ≈ 101 zonas/día. Los ✗ eran casi todos escalón 3 / total 6.
- **EMPINADAS v2** (73 ✓ / 27 ✗, archivo de juicios propio `labels/…__empinadas.json`): escalón ≤ 3, al menos un escalón
  de 3, total ≥ 5 ticks, retroceso ≥ 6, ≥ 3 picos, ≤ 35 velas. Precisión 0,66 (cobertura 1,0 por construcción: se juzgó
  la salida de este mismo detector). ≈ 35 zonas/día. Los ✗ son más largos (mediana 25 velas vs 18) y de 4 picos.
Visor: `?solo=det` (planas) y `?solo=det&det=empinadas`. Parámetros NO congelados todavía para test de outcomes.

## Descriptivo 29/09 (formación, sin P&L) — entrada anticipada con 2 picos (opción 3)
Candidata = 2 picos propios confirmados; ENTRADA = primera vela que vuelve a 1 tick del nivel del 2.º pico (≤ max_gap).
Feb-2026: planas 16.591 candidatas (≈ 690/día), 83 % tocan; **sólo 15 % de las que tocan terminan formando la zona**
(empinadas: 12.341, 82 %, **5 %**). La entrada anticipada entra mayoritariamente en series que NO se convierten en zona:
el test de outcomes debe medirse sobre TODAS las entradas, no sobre las que luego se confirmaron. Visor: `&cand=1`.

## Confirmación por precio (opción 2, elegida por Nico 29/09) — sin anticipar: 3 picos y dispara
Un pico se confirma cuando el extremo opuesto se aleja **2 ticks** sin que se supere el pico (media de la distancia a la
detección por velas: 2,5 ticks). Planas 2.705 zonas, empinadas 927; detección 1 vela antes (mediana). En las zonas
comunes con la versión por velas: ahorro medio 0,65 ticks, ≥ 2 ticks en el 25 %, ≥ 3 en el 10 %; en ~30 % dispara más
lejos que la versión por velas (allí el cierre ya estaba a 0–1 tick del pico). El disparo es un nivel intravela (orden
stop): el llenado real exige replay con deslizamiento. Visor: `&det=precio` y `&det=empinadas__precio`.
