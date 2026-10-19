# R3 — Dirección a 15–60 min: resultados del descubrimiento (PROVISIONAL)

Estado: PROVISIONAL (partición de descubrimiento; la replicación **no se abrió**)
Fecha: 2026-10-14
Familia / módulo: research · R3
Manifiesto: `docs/research/R3_DIRECCION_15_60M_MANIFIESTO_PROPUESTO_20261014.md` (aprobado por Nico y congelado antes de medir, commit `b6ed1859`; implementación `4aef434e`)
Procedencia: `tools/r3_direccion.py`, release `liquid_tick_v1` v4 (`db9c42cd…14ce5`), descubrimiento 2025-07-18 → 2026-03-31 (NQ 166, ES 178, YM 150, RTY 123, GC 150 sesiones), `purpose=provisional_research`; el holdout (`trade_date ≥ 20261001`) y la partición de replicación no se leyeron. Resultados completos de las 90 celdas: `docs/research/r3_direccion_20261014/R3_discovery.json`.

## Resultado
**Ninguna celda sobrevive.** Las dos primarias (NQ, L=15, H=15) tienen retorno neto medio negativo y límite superior del IC cercano a 0; ninguna de las 90 celdas alcanza Holm < 0,05. Estado formal para NQ a 15 min en ambas familias: `SIN EFECTO DETECTADO` (con el MDE del manifiesto: ≈ 4,7 pp de acierto).

| Celda | Ventanas | Acierto | Bruta (ticks) | Neta F alta | IC 95 % neta | p Holm (90) |
|---|---:|---:|---:|---:|---|---:|
| NQ|A|15|15 (primaria) | 4078 | 50.0 % | -0.27 | -6.45 | [-11.81; -0.51] | 1.00 |
| NQ|B|15|15 (primaria) | 4089 | 49.4 % | 1.39 | -4.80 | [-9.43; 0.15] | 1.00 |
| NQ|A|15|60 | 974 | 51.6 % | 15.42 | 9.24 | [-10.88; 32.14] | 1.00 |
| GC|A|30|60 | 881 | 49.7 % | 11.32 | 5.27 | [-2.07; 13.18] | 1.00 |
| NQ|B|15|60 | 980 | 48.7 % | 8.95 | 2.77 | [-19.55; 26.12] | 1.00 |
| NQ|B|30|60 | 981 | 49.6 % | 7.28 | 1.10 | [-15.93; 17.29] | 1.00 |
| RTY|A|15|60 | 715 | 52.2 % | 5.49 | 1.05 | [-8.69; 11.52] | 1.00 |
| ES|B|15|60 | 1053 | 53.2 % | 4.33 | 0.78 | [-4.03; 5.58] | 1.00 |

- **Acierto medio:** familia A 49,6 %, familia B 49,3 %: indistinguible de una moneda. Retorno bruto medio por decisión: A +0,79 ticks, B +0,06 (la fricción de viaje es 3,3–7,9 ticks).
- 48 de 90 celdas tienen media bruta > 0 y sólo 6 una media **neta** > 0, todas a **H = 60 min** con ICs enormes (±20–30 ticks): es el rango de lo que produce el azar con ≈ 600–1.000 ventanas, no un hallazgo.
- Las seis mejores se muestran **a título informativo**: no se seleccionan ni se llevan a la replicación (el criterio de supervivencia está fijado en el manifiesto y ninguna lo cumple).

## Qué se cierra y con qué alcance
- **Cerrado:** señal de persistencia de retorno (A) y de presión de flujo agresor (B) con lookback 15/30/60 min y horizonte 15/30/60 min, decisión cada H minutos, entrada al primer trade del minuto siguiente, en NQ, ES, YM, RTY y GC, sobre 2025-07 → 2026-03. A 15 min en NQ/ES/GC el diseño tenía potencia para ≈ 4–5 pp: un acierto de equilibrio (≈ 54 %) habría aparecido y no apareció.
- **No cerrado:** H = 30–60 min (potencia insuficiente: MDE 5–8 pp contra 2–3 pp necesarios; un nulo ahí no distingue ausencia de efecto de falta de potencia), señales distintas de A y B, condicionamiento por régimen o por subasta, ejecución con stops, y cualquier otro estimando. No se transporta a otros activos ni familias.
- La replicación (2026-04 → 2026-09) **sigue sin abrirse**: con cero sobrevivientes no hay nada que replicar, y abrirla sin celdas sería gastar la única apertura.

## Qué sigue (propuestas, no ejecutadas)
1. Más N: la captura continua (`docs/PENDIENTES_DE_NICO_20261014.md`) es lo único que mueve el MDE a 30–60 min.
2. Familias distintas registradas por separado (p. ej. condicionamiento por régimen de subasta `session_auction` v3, ruptura del rango inicial) con su propio manifiesto y presupuesto.
3. No bajar umbrales ni cambiar ventanas sobre este mismo descubrimiento: sería otra prueba.
