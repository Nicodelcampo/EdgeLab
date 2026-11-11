# LUXIMB-AMARILLA — acta de apertura del holdout (2026-11-11)

Estado: VIGENTE — escrita y commiteada ANTES de lanzar el holdout. Autorizó Nico (2026-11-11): «abrí el holdout»; «si lo que se miró
desde el 1 de octubre no es tan parecido, medilo desde el 1 de octubre igualmente».

## Hipótesis congeladas (una sola vez, sin ajuste)

`docs/research/luximb_amarilla_20261111/r2/CONGELADAS_20261111_845c37fc.json` (módulo `edgelab.research.luximb_amarilla_r2`):

| # | definición | ejecución | filtro | desarrollo (NQ+USATECH, DESC+REP) |
|---|---|---|---|---|
| H1 | ctrl\|W2\|amarilla\|e2\|DESPUES | P_obj_75_stop_ext | vwapD_lejos_hacia | n 89, +0,144 R neto, t 4,89 |
| H2 | ctrl\|W2\|amarilla\|e2\|DESPUES | P_obj_50_stop_ext | vwapD_lejos_hacia | n 76, +0,066 R neto, t 4,68 |
| H3 | ctrl\|W2\|sin_filtro\|e2\|DESPUES | P_obj_75_stop_ext | vwapD_lejos_hacia | n 112, +0,126 R neto, t 4,28 |

p de desarrollo declarada: **0,05 para las tres** (sólo se sabe que superan el p95 del máximo del nulo de la búsqueda, t_max p95 = 4,02
sobre 14.064 celdas; la p por celda 0,0005 no corrige la búsqueda y no se usa). Combinación: Fisher (desarrollo, holdout) por hipótesis.

## Ventana: desde la sesión CME del 2026-10-01, NQ y DK:USATECHIDXUSD, sólo datos sellados

Qué del holdout ya se miró desde el 1-oct en este linaje (`docs/research/HOLDOUT_VENTANAS.jsonl`) y por qué no impide medir desde ahí:
- **LUXIMB_FADE_VISOR** (NQ, 1–21 oct, n 14, 14 stops): fade a mercado al marcar el impulso, stop 0,2·D. Regla distinta: AMARILLA
  entra mucho después (caja, ruptura a favor, excursión ≥ 2·H_am, cierre más allá del borde interno), con filtro VWAP. Poco parecida.
- **CORREDOR_VOL_GAPS_NQ / CFD_NQ** (desde 1-oct, n 20 y 16, media −34,9 y −22,9 pts, «alerta»): la secuencia de la caja amarilla es
  la misma idea, sobre otro impulso (corredor) y sin filtro VWAP. Es el pariente más cercano. Su resultado era **adverso** y se
  conocía antes de diseñar AMARILLA, así que el solapamiento sólo puede sesgar en contra de las hipótesis, no a favor.
- Se reporta además el resultado sólo desde 2026-10-23 (sesiones no miradas por ningún pariente) como sensibilidad.

## Potencia (declarada antes)

Desarrollo: ≈ 0,15 operaciones por sesión por hipótesis. Sellado disponible ≈ 21–23 sesiones por activo → se esperan ≈ 5–8
operaciones por hipótesis. Con ese n el holdout **no tiene potencia** para confirmar ni refutar (MDE ≫ 0,14 R): el resultado se
registra como dato, y la familia queda **sin más aperturas**. Las tres siguen en forward (e-proceso) desde la congelación.

## Cómo podría refutarse / justificación económica

Justificación: tras un impulso con absorción en la caja y una extensión que fracasa (cierre del otro lado de la caja), con el precio
lejos de su VWAP diario, el retroceso hacia el valor es más probable que la continuación. Refutación: media neta ≤ 0 en el holdout
con potencia suficiente (no la hay ahora) o en forward cuando el e-proceso tenga n ≥ 30.
