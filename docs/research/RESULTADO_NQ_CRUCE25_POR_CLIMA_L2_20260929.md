# Resultado NQ-CRUCE25-CLIMA (desarrollo A3, jul–sep 2026, NT8) — 2026-09-29

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8` · Manifiesto v4 (§6–§8) · Kernel Kaggle
`edgelab-nq-cruce25-clima-20260929` v2 (OK de Nico «subilo»). **Estudio de barreras desde el cierre de señal; no es
ejecución ni rentabilidad.** Salida: `artifacts/nq_cruce25_clima/nq_cruce25_clima.json` (local, sha256 `4eff9c959e4a0d1046f72537e6dee51e83875b1f883f200389d07ed3ef000d5e`).

## Procedencia (leída ANTES del resultado, §7.1)
entry.py ejecutado = descargado = blob de `adbfcdb` = `6c4dfe9c…`; código `2a3e5086`; 10 hashes de dataset OK. v1 falló
antes de producir outcomes (ruta Windows en el catálogo; Entrada 073). El hash difiere del de la 072 sólo por ese arreglo.

## Cobertura
- Velas: 56/56 sesiones del catálogo NT8. **5 de las 40 sesiones de evaluación sin velas** (10/09 y 15–18/09): causa raíz =
  el catálogo de ticks NT8 las excluye (10/09 hueco de 4 h; 15–18/09 el archivo 09-26 casi vacío tras el roll y el 12-26
  canónico arranca el 21/09). Es cobertura del dato, no del código. Quedan 35 sesiones; post-roll sólo 21–23/09.
- Por nivel: ~10.080 señales; sin clima 144–153; sin control del mismo clima 76–90 (casi todas en *toxic*); ~40 % de las
  señales con clima tenían el objetivo del 25 % ya alcanzado al cierre (sin operación, excluidas y contadas). Todas las
  celdas reconcilian (`cierra = True`).
- Terciles de volatilidad v1 vs v2: acuerdo 0,856.

## Primarias (x = 25 %, control del mismo clima, max-T conjunto sobre 12 celdas; t crítico 3,17)
| Nivel | Clima | Evaluables | Evento | Control | Dif | IC 90 % | t | MDE80 |
|---|---|---|---|---|---|---|---|---|
| N3 | calm | 4.046 | 0,632 | 0,651 | −0,018 | [−0,033; −0,002] | −1,89 | 0,027 |
| N3 | normal | 1.156 | 0,636 | 0,653 | −0,018 | [−0,047; +0,011] | −1,02 | 0,048 |
| N3 | volatile | 536 | 0,608 | 0,625 | −0,017 | [−0,057; +0,028] | −0,65 | 0,073 |
| N3 | toxic | 213 | 0,634 | 0,621 | +0,013 | [−0,061; +0,074] | 0,30 | 0,115 |
| N4 | calm | 3.940 | 0,635 | 0,652 | −0,017 | [−0,032; −0,002] | −1,94 | 0,025 |
| N4 | normal | 1.134 | 0,629 | 0,644 | −0,016 | [−0,046; +0,016] | −0,82 | 0,053 |
| N4 | volatile | 536 | 0,647 | 0,640 | +0,007 | [−0,038; +0,047] | 0,28 | 0,074 |
| N4 | toxic | 197 | 0,680 | 0,591 | +0,090 | [+0,026; +0,168] | 2,02 | 0,125 |
| N5 | calm | 3.881 | 0,621 | 0,637 | −0,016 | [−0,031; −0,001] | −1,81 | 0,025 |
| N5 | normal | 1.117 | 0,616 | 0,636 | −0,020 | [−0,052; +0,011] | −1,03 | 0,054 |
| N5 | volatile | 477 | 0,654 | 0,640 | +0,014 | [−0,038; +0,064] | 0,44 | 0,089 |
| N5 | toxic | 186 | 0,688 | 0,615 | +0,073 | [−0,006; +0,135] | 1,64 | 0,125 |

**0/12 sobreviven max-T.** Ninguna celda inconclusa por potencia (todas ≥ 30 eventos y ≥ 8 sesiones).

## Secundarias (descriptivas, IC marginales)
Global con control del mismo clima: −0,011 a −0,017 (N3 IC [−0,029; −0,005]); sin condición de clima: −0,008 a −0,013,
IC que tocan 0; sin post-roll: −0,013 a −0,020.

## Lectura
1. **El exceso del cruce al 25 % visto en Lucid (+2,2 a +4,6 pp) no aparece en NT8 jul–sep** con la convención operable
   (entrada al cierre de la señal): el global es ≈ −1 a −2 pp. Ojo: la convención difiere de la del estudio original (allí el
   objetivo podía estar ya alcanzado al cierre); el nulo es de **esta** pregunta, no refuta aquella medición.
2. Patrón por clima sin corrección: *calm* consistentemente negativo (~−1,7 pp, t ≈ −1,9 en los tres niveles) y *toxic*
   positivo (+7 a +9 pp) pero con MDE 0,125 y 29–32 sesiones: no distinguible de ruido tras max-T. Es exactamente la
   heterogeneidad que se preguntaba y **no sobrevive**; queda como observación, no como hipótesis promovida.
3. Estado: **SIN EFECTO DETECTADO por clima** (desarrollo). No habilita confirmación forward. Si se quisiera seguir *toxic*,
   haría falta un pre-registro nuevo con esa sola celda y más sesiones (oct+).
