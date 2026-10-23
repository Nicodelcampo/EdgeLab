# EXPANSION-ZONAS — expansiones con zonas LUX-IMB en su extremo inicial: DENTRO y ANTES (2026-10-23)

Estado: VIGENTE — registrada antes de correr. Pedido de Nico (2026-10-23): barrer con la metodología del embudo (1) la estrategia de
expansiones con zonas en su 25 % inicial y (2) la variante con las OG/VI en el extremo inicial pero por fuera de la expansión,
antes de su inicio.

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Familia **EXPANSION_ZONAS**: independiente de AREAS-EXP-1 y de LUX-IMB-IMPULSOS (no se transportan resultados ni multiplicidad).
Código: `edgelab/research/expansion_zonas.py` (preflight ok; tests `tests/research/test_expansion_zonas.py`).

## Antecedente
La regla del visor de LUX-IMB-IMPULSOS (`luximb_parity_20261020/CANDIDATO_HOLDOUT_REGLA_VISOR_NQ_20261021.md`): +4,95 pts/op en
desarrollo, 0 de 14 en su mirada exploratoria del holdout. Es UNA celda propuesta a mano; acá se barre su vecindario completo y su
variante.

## Población (enumerada antes de congelar, regla de CLAUDE.md)
- **Familias de eventos posibles alrededor de una expansión:** creación de zonas durante el impulso, zonas preexistentes en el
  origen, primer toque de esas zonas al volver, toque n-ésimo, invalidación, vencimiento, confluencia con otras áreas, y el estado
  continuo (distancia a la zona más cercana en cada vela).
- **Se mide:** el EVENTO «expansión confirmada en tiempo real» con zonas en su extremo inicial, en dos versiones (DENTRO y ANTES).
- **Por qué:** es lo que pidió Nico y lo que tiene antecedente.
- **Refutación de la población:** si ninguna celda sobrevive y el MDE muestra potencia, se pasa al estado continuo y al primer toque.

## Variables (todas con velas ≤ k)
| perilla | niveles |
|---|---|
| variante | DENTRO (zonas creadas entre A y k, con punto medio en el 25 % inicial del rango) / ANTES (zonas vivas en A, creadas antes, por fuera de la expansión y a ≤ 25 % del rango de A) |
| R (amplitud) | ≥ 8 / 15 / 25 × ATR(14) de M1 |
| n_zonas | ≥ 1 / 2 / 3 / 5 |
| velocidad | terciles (rango / velas desde A), extremos |
| og_vi | sólo VI / mezcla / sólo OG / cualquiera |
| posición | posición media de las zonas dentro de su franja: terciles, extremos |
| tamaño | altura media de zona / rango: terciles, extremos |
| vol_rel | volumen por vela de la expansión / sesión anterior: terciles, extremos |

**Expansión:** el cierre se alejó ≥ R·ATR del extremo opuesto A de las últimas 30 velas. Se marca la primera vela que lo cumple; la
misma dirección no vuelve a marcar en 30 velas.

## Ejecuciones (30)
- **CONTRA**, es decir, vuelve hacia A, como la regla del visor: entrada al cierre (E1C) o en el tick siguiente (E1A); objetivo en A,
  en el 50 % del rango o en el punto medio de las zonas; stop a 0,2 / 0,5 / 1,0 × la distancia a A.
- **FAVOR**, es decir, continúa: E1C o E1A; stop a 0,2 o 0,5 × la distancia; objetivo a 1R, 2R o 3R.
- **Celdas:** 233.280 por canal y campaña.

## Campañas (embudo automático, `config/autopilot/grillas/campanas/`)
| cid | señal | ejecución | descubrimiento | OOS |
|---|---|---|---|---|
| EXPZ-NQ | NQ | NQ | 2025-08-05 → 2026-03-31 | 2026-04-01 → 2026-09-25 |
| EXPZ-CFD | DK:USATECHIDXUSD | NQ | 2025-08-05 → 2026-03-31 | 2026-04-01 → 2026-09-30 |

Pruebas: 2 × 233.280 por campaña (canales total y reciente) se registran al lanzar el descubrimiento. El resto de las etapas, con
sus reglas, son las del embudo (`docs/research/GUIA_GRILLA_MASIVA.md` §8).

## Justificación económica y refutación
- **Justificación:** una expansión que nace de (o atraviesa) una concentración de desequilibrios marca dónde hubo urgencia. El
  regreso hacia el origen (CONTRA) o la continuación (FAVOR) dependen de si esas órdenes quedaron llenas o pendientes.
- **Refutación:** ninguna celda pasa integridad y OOS, o el holdout a N fijo da media ≤ 0.
