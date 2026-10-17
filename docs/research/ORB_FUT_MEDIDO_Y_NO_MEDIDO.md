# Familia ORB-FUT — registro MEDIDO / NO MEDIDO (2026-10-17)

Manifiesto: `ORB_FASE0_MANIFIESTO_20261017.md` (enmienda A1: RTH por reloj). Referente rector: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

## Antecedente (ya medido antes de esta fase)
ORB 5-min en ES y NQ, config unica, fills reales: **NQ -17/-19 ticks por trade (183 operaciones), ES -13**; muerto (EXP-043, `corpus/ssrn/cerebro/LEDGER_EXPERIMENTOS.md`). El "sobreviviente" inicial era un bug de signo.

## Fase 0A (sin retornos) — MEDIDO
Kernel `edgelab-orb-f0a-v1` v2, resultados `orb_f0_results_20261017/EXP_ORB_F0A_RESULTS.json`. ES y NQ por separado, tick, RTH 09:30-16:00 ET (por reloj; `outside_regular` no es RTH en este release).
- **Muestra:** descubrimiento (2025-07-18..2026-03-31): ES 178 sesiones validas, NQ 166, 0 descartes. Ventana limpia (2026-07-16..09-30): ES 42, NQ 50 (**insuficiente para confirmar**). Segundo camino independiente (barras de 1 min por `groupby`): 0 discrepancias en ancho y minuto del primer cruce.
- **Rango de 15 min (primaria):** ancho mediano ES 68.5 ticks (0.25 ATR14), NQ 401.5 ticks (0.30 ATR14). Costo 2.5t RT / ancho: mediana 3.6 % (ES) y 0.6 % (NQ): **el costo no es el problema** (bandera <= 10 % cumplida).
- **Rupturas:** casi todos los dias rompen algun lado (P(ninguna) ~ 0 para 5/15/30 min). Con 15 min: P(romper arriba/abajo/ambos) hasta 15:45 = ES 0.79/0.76/0.55, NQ 0.73/0.73/0.46. **Latigazo** (se rompe un lado y luego el otro antes de las 11:30) en 41 % (ES) y 34 % (NQ) de los dias con ruptura (62 % y 54 % con 5 min): coherente con la tasa de acierto de 26-33 % de EXP-043. Primer lado: ~50/50. Tiempo a la primera ruptura: mediana 1.7 min (ES), 2.4 min (NQ) tras cerrar el rango.
- **Terciles de filtros (N por estrato, 15 min):** volumen relativo, rango/ATR y |gap|/ATR: ~53 / 52 / 53 dias por tercil en ES y ~49 / 48 / 49 en NQ. En la ventana limpia: 14 y 17 por tercil: **no hay potencia para condicionar en ella**.
- **Potencia:** MDE (80 %, 2.5 % unilateral) de la media por dia = 2.8 x SD / sqrt(N): con N = 178 y SD = 1 R, **0.21 R** (ES); con SD = 2 R, 0.42 R. En la ventana limpia, con SD = 1 R, 0.43 R. La SD real la mide 0B.
- Banderas preliminares (manifiesto secc. 5): N >= 150, costo/ancho <= 10 %, integridad: **cumplidas en descubrimiento**; **GO/NO_GO final: ver 0B (ABSTENCION).**

## Fase 0B (extension firmada tras la ruptura, sin stop ni objetivo) — MEDIDO
Kernel `edgelab-orb-f0b-v1` v2 (spec `EXP-ORB-F0B-V2-A2`), resultados `orb_f0_results_20261017/EXP_ORB_F0B_RESULTS.json`. La corrida v1 queda **nula** (enmienda A2 del manifiesto, secc. 12: nulo mal construido y reloj ambiguo). Verificado: las 17 y 25 discrepancias entre caminos eran exactamente los dias cuyo precio cambia entre `<= t` y `< t` (prints con sello igual a `t`); con `< t` en ambos caminos hay **0 discrepancias** en las cuatro celdas.
Celda primaria (15 min, ruptura por toque, `E` al cierre 15:45), ventana de descubrimiento, ES / NQ:
- N = 173 / 161. **Media de `E` = -0.18 R / -0.14 R**, IC95 [-0.55, +0.20] / [-0.45, +0.18]; SD = 2.53 / 2.05 R. Nulo de permutacion de signos: p unilateral 0.80 / 0.79 (bilateral 0.39 / 0.43). A 11:30: +0.10 R / -0.01 R (p 0.19 / 0.55). **No hay continuacion bruta detectable en descubrimiento**, ya antes de stop y costos.
- **MDE de la media al cierre = 0.54 R (ES) y 0.45 R (NQ)**: por encima del umbral de 0.30 R. La SD (2.0-2.5 R, con colas de dias de rango angosto) es la limitante; no el costo (3.6 % y 0.6 % del ancho).
- Ventana limpia (2026-07-16..09-30), **solo descriptiva**: ES N = 41, `E` al cierre = +0.80 R, IC [+0.09, +1.50], p unilateral 0.018 (11:30: +0.66 R); NQ N = 49, +0.07 R, p 0.36. **Contradice a descubrimiento en ES** (-0.18 R), con N = 41 y SD 2.3 R: ocho celdas inspeccionadas (2 activos x 2 horizontes x 2 ventanas), una sola significativa y en la ventana mas corta. **No se promueve.** No es una replicacion independiente de nada: es una ventana mas, y consume la unica mirada descriptiva que el manifiesto le asignaba.
**Veredicto combinado (secc. 5, criterios escritos antes de mirar): ABSTENCION en ES y NQ.** No es `GO_FASE1` (MDE 0.54 / 0.45 R > 0.30 R). No es `NO_GO` (N > 100, costo/ancho << 25 %, y el IC95 de la media, +-0.37 R, **no** esta contenido en [-0.10, +0.10]). Traduccion honesta: con ~170 dias y esta dispersion, **este dato no puede distinguir un ORB de 15 min con edge de +0.3 R de uno sin edge**; lo que si descarta es un edge grande (>~0.5 R bruto) en descubrimiento.
**Consecuencia para "mejorar el ORB con herramientas de EdgeLab"** (`PENDIENTE_ORB_HERRAMIENTAS_EDGELAB_20261017.md`): el piso a mejorar no es un ORB "ya probado": su extension bruta es ~0 o negativa en nuestros datos. Y condicionar en terciles deja ~55 dias por celda: con SD 2 R el MDE por tercil es ~0.75 R. **Filtros, 3 franjas, grillas o ML no tienen potencia en este N**; agregarlos amplia la busqueda sin poder para verla (misma conclusion que P-53 en la familia HFTZones).

## NO MEDIDO / limites de 0A
- **Costo real de un stop de ruptura:** el dataset trae bid/ask en la fila del propio trade, asi que el "deslizamiento" da 0 por construccion y **no mide nada**; el spread en NQ (mediana 2-3 ticks en 09:45-10:30) es poco creible (las cotizaciones de este export son ruidosas, como ya documento `orb_tickfill.py`). Spread ES mediano 1 tick. Falta cotizacion continua (L1 de NT8: ES jul-sep via `edgelab-l2-es`; NQ no disponible).
- Cualquier retorno, extension post-ruptura, stop, objetivo o filtro como hipotesis: **0B y Fase 1**.
- Dias de calendario macro, otras aperturas (Globex/Londres), otros activos, el holdout (>= 2026-10-01, intacto).
