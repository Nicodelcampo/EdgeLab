# EMA 200/500/2000 de MGC reproducida en oro spot — prueba T2 (2022-07-01 a 2025-10-07)

Reglas: enmienda P1 §4.2 de `docs/research/REVISION_EMBUDO_DISCOVERY_Y_PLAN_ORO_20261004.md` (escrita antes de cargar estos datos). Herramienta: `tools/ema_spot_t2.py`; salida cruda `ema_spot_T2.json`. Una sola corrida: nulo de dirección por sesión, 200.000 sorteos, semilla 20261012, máximo de z sobre cinco horizontes, umbral 0,05. Muestra anterior al primer día de MGC usado (2025-10-08); no se leyó nada desde 2026-10-01.

## Límite declarado (leer primero)
La equivalencia con MGC resultó **SOLO_PRECIO** (`RESULTADO_EQUIVALENCIA.md`): las barras de ticks del spot no reproducen la formación de barras de MGC. Acá se usaron barras de **13 eventos de spot** (el N elegido en el solape), que disparan ≈ 1,7 veces más señales que la regla en MGC y en momentos distintos. Por lo tanto esta prueba **no es una réplica de la EMA de MGC**: es la misma regla aplicada a otra serie de barras sobre el mismo activo económico. Sirve para preguntar si esa familia de señales sobre el oro tuvo información direccional antes de octubre de 2025; no confirma ni refuta la estrategia de MGC.

## Datos
166.987.741 cotizaciones spot (bid/ask), 12.845.210 barras de 13 eventos, **9.812 señales** en 844 sesiones. Retorno por señal y horizonte: dirección × (mid(t + h) − mid(entrada)) en ticks de 0,1 USD, entrada en la cotización siguiente al cierre de barra, bruto de costos, truncado al fin de la sesión (16:00 CT).

## Resultado: **sin información direccional distinguible del azar** (p_max = 0,19)
| Horizonte | Media (ticks) | z | p (unilateral) | Media de largos | Media de cortos |
|---|---:|---:|---:|---:|---:|
| 15 min | +0,16 | 0,48 | 0,314 | +0,49 | −0,32 |
| 30 min | +0,36 | 0,68 | 0,249 | +1,11 | −0,47 |
| 1 h | +0,38 | 0,47 | 0,321 | +2,23 | −1,67 |
| 2 h | +0,90 | 0,78 | 0,218 | +3,84 | −2,36 |
| 4 h | +2,43 | **1,42** | 0,078 | +6,81 | −2,42 |

Máximo z = 1,42; **p_max = 0,19 > 0,05**. Con la regla de decisión del pre-registro de MGC: el análogo en spot queda **descartado como evidencia** con estos datos (no equivale a probar que no exista).

## Lectura
1. **Dirección.** En 2022-2025 los largos ganan y los cortos pierden a todos los horizontes (en 4 h, +6,8 y −2,4 ticks): es el patrón inverso al de MGC (octubre de 2025 a marzo de 2026: los largos perdían y los cortos ganaban). Es coherente con la **deriva del oro**, que subió durante la muestra; la prueba por sesión no la elimina del todo porque la deriva favorece más a un lado.
2. **Año por año (descriptivo)**, media a 4 h: 2022 +1,6; 2023 +1,2; 2024 +2,4; 2025 +3,8 ticks. Todo positivo y chico frente al spread del spot.
3. **Qué no dice.** No dice nada sobre la EMA de MGC en datos de futuros con barras de operaciones: con el límite de arriba, un resultado nulo aquí no la descarta ni uno positivo la habría confirmado.
4. **T1 (media neta de las 21 celdas con costos de spot)** quedó descriptiva en el plan y no se corrió: requiere el reproceso con stop y objetivo y, con el spread del spot, no tiene potencia.

## Pruebas y custodia
Contador global de pruebas: +5 (campaña `ETAPA-P1-EMA-T2-spot-2022-2025`). El holdout formal sigue sin abrirse.
