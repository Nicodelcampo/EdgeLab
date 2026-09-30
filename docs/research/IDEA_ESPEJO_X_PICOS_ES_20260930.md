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
