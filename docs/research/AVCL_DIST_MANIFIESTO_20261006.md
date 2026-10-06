# AVCL-DIST — distribución completa del desplazamiento (colas de los dos lados) — manifiesto — 2026-10-06

Origen: Nico, 2026-10-06 ("es un dato importante, hay que hacerse cargo de eso"). SR-DIR midió sólo la **media** del
canal direccional, contra la regla permanente "todo efecto se mide en dos canales más la distribución completa". Una
media ≈ 0 puede esconder colas engordadas hacia los dos lados: zonas que salen disparadas alejándose (las capturas de
Nico) y otras que vuelven y atraviesan.
Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Información, **no P&L**. Soporte/resistencia no se evalúa: "alejarse/volver" se mide como desplazamiento, sin juzgar el
nivel.

## Datos y estimador
Cache de VOL-2 (MNQ 2025-07 → 2026-09, 50t, parámetros congelados), RTH formal. Estimador lineal de probabilidad con FE
(S0 + int10 + int50 + vol20 + vpk), SE por sesión, bilateral.

## Variables
- `R_H` = rango de las H barras previas, en ticks (escala local).
- OFF: `s_H = lado × (close[b+H] − close[b])`, donde lado = +1 soporte / −1 resistencia. Controles: pseudo-lado =
  signo del retorno de las 10 barras previas, como en SR-DIR, para no confundir con momentum.
- **Cola de alejamiento:** 1[s_H ≥ R_H]. **Cola de regreso:** 1[s_H ≤ −R_H].
- **Cola sin signo:** 1[|close[b+H] − close[b]| ≥ R_H] (AT y OFF).

## Pruebas formales (6, Holm)
- OFF × H ∈ {10, 50} × {alejamiento, regreso}: 4.
- {AT, OFF} × H10 × cola sin signo: 2.

Lectura pre-registrada:
- **Las dos colas suben** → expansión bidireccional: el sello sirve para estrategias de volatilidad, no para dirección.
- **Sólo sube alejamiento** → hay dirección en la cola aunque la media sea ≈ 0.
- **Sólo sube regreso** → atracción en la cola.

## Descriptivos
- Curva de cuantiles 1…99 de `s_H` (OFF) y de `|Δclose|/R` (AT, OFF), eventos contra controles del mismo estrato S0
  (diferencia de cuantiles, IC por bootstrap de sesiones).
- Las mismas colas con umbrales 0,5R y 2R.
- Por quintil de `anomaly_ratio` (Q1 contra Q5) y por ancho de zona (angosta contra ancha).
- H200.

## Justificación económica
Si las dos colas engordan, hay valor en estructuras de volatilidad (breakout bilateral / straddle intradía, ampliar el
stop en la ventana). Si engorda una sola, hay valor direccional en un subconjunto aunque la media lo esconda.

## Cómo podría refutarse
Que ninguna cola difiera de los controles más allá del MDE: la expansión sería un ensanchamiento suave del centro de la
distribución, sin eventos grandes.

## Registro
6 pruebas, familia `AVCL_DIST`. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
