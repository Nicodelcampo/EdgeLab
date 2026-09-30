# IDEA (registrada, en calibración a ciegas): espejo × picos acumulados antes de A — ES (2026-09-30)

**Nico:** entrar cuando se crea el espejo (o un poco antes) **sólo si justo antes de A** (inicio del primer impulso) hay
picos acumulados; sin picos el precio no tiene motivo para ir ahí y el trade falla. A priori: acumulación de picos
justifica entrar; imbalance justifica no entrar. **No se exige una zona IPC detectada**: se juzga si hay o no picos.
**Parámetros a explorar después:** configuración del espejo, punto de entrada (al crearse o antes), configuración de picos.

## Paso 1 — calibración a ciegas (target-free)
`tools/blind_espejo_eventos.py` → 80 espejos completados al azar (de 411) de ES 03-26 ene-2026, velas 100t, nivel N3
(min_w 17 ticks, 20 velas). Cada evento se exporta SÓLO hasta la vela en que el precio vuelve a A (momento de decidir):
el futuro no está en el archivo. Página `viewer/nt8_bridge/blind_espejo.html`: Nico marca picos (clic) y el veredicto
(picos / sin picos / dudoso). Juicios en `labels/blind_espejo_ES_03-26_202601_25T_HFT.json`.
Siguiente: con los juicios, un detector de «picos antes de A» y recién ahí un pre-registro con outcomes (manifiesto + OK).
**Cómo podría refutarse:** los espejos con picos no se separan de los sin picos (ni del control) en la continuación más allá de A.

## Exploración 30/09 (pedida por Nico antes de entrenar; NO pre-registrada, n chico)
`tools/blind_espejo_outcomes.py` → `es_escalonadas/blind_espejo_outcomes_*.json`. Mismos 80 espejos (verificado A/B).
Operación: a mercado al cierre de la vela en que el precio vuelve a A, en la dirección de la vuelta (más allá de A);
tick a tick con bid/ask y 0,40 ticks de comisión; SL 0,5 W / 1 W × TP 1R / 2R.
**Los juzgados «con picos» (25) rinden PEOR que los «sin picos» (55) en las 4 celdas** (dif. −0,20 a −0,83 R; la de
SL 0,5 W / TP 2R con IC 90 % [−1,27; −0,37]); tasa de objetivo 12–32 % vs 18–47 %. Con esta mecánica, la hipótesis
«picos antes de A → continuación» va al revés en la muestra. Exploratorio: no es un test; no se entrena el detector
para esta dirección sin revisar antes la mecánica (dirección, punto de entrada) con Nico.
