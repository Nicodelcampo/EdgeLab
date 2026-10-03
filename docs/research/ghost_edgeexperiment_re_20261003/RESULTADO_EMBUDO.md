# EdgeExperiment en el embudo de EdgeLab — resultado (2026-10-03)

Pre-registro: `PREREGISTRO_EMBUDO.md` (y su enmienda 1, escrita al ver los resultados 1–5 y antes de correr los controles de deriva). Números: `resultados_embudo.json`. Contador de pruebas: `trial_registry.jsonl` (63 pruebas, cadena válida). La lógica de la estrategia no está en este repositorio.

## Veredicto (regla pre-registrada)
**`CANDIDATO_REQUIERE_CONFIRMACION_FUTURA` — no es un edge validado.** Pasa todas las reglas de descarte en la muestra fuera de la ventana de ajuste del proveedor, pero la muestra es corta, no es virgen y la prueba del mejor de 60 reglas no rechaza el azar.

## Datos y réplica
- MNQ, ticks de Kaggle, 2025-08-01 a 2026-06-30 (holdout de EdgeLab `2026-06-30T22:00Z` sin tocar), 211 sesiones; huecos 03-20→04-06 y 06-10→06-25.
- Barras de 1 minuto desde ticks: 27/27 trades de la réplica coinciden exactamente con los generados sobre las barras de NinjaTrader (SEP26, hasta el holdout). Las tablas de oportunidades reproducen las 1.959 señales y los 1.929 trades no cerrados por netting, con 0 diferencias.
- Ejecución principal: mercado en el primer tick tras la orden, compra al ask / venta al bid; comisión de usuario USD 1,90 ida y vuelta = 3,8 ticks.

## Resultados MNQ (ticks netos por trade; 1 tick = USD 0,50)
| | IS (hasta 2026-05-27) | OOS (desde 2026-05-28) |
|---|---:|---:|
| Trades / sesiones | 1.837 / 198 | 122 / 13 |
| Media neta, fills de libro | **+23,9** (IC95 ≈ +14 a +34) | **+83,8** (IC95 +26,5 a +142,3) |
| Media neta, fills al open de barra (réplica del proveedor) | +25,8 | +86,0 |
| Nulo de dirección por sesión (5.000) | p = 0,0002 | p = 0,007 |
| Nulo de dirección que preserva la exposición (5.000) | p = 0,0002 | p = 0,001 |
| Calendarios placebo (2.000) | p = 0,0005 | p = 0,0015 |
| Línea base «siempre largo», mismas horas | +8,0 | −5,5 |
| Sin la mejor sesión / sin las 3 mejores (total, ticks) | 40.683 / 35.654 | 7.245 / 3.618 |
| Largos / cortos (total, ticks) | 33.124 / 10.787 | 5.048 / 5.170 |
| Con 1 tick de slippage por lado | +21,9 | +81,8 |

- **Mejor de 60 reglas** (nulo de máximo del embudo, IS partido en D0/D1, 24 reglas con ≥10 trades en ambos tramos): **p_max = 0,22**. Ninguna regla individual se distingue del azar una vez corregida la selección entre 60. La evidencia es del conjunto (patrón de calendario), no de reglas sueltas.
- Rentabilidad positiva en 10 de 11 meses; positiva en largos y en cortos; positiva por tenencia (15/30/60 min), por franja horaria (overnight, Londres/pre-apertura y sesión de EEUU) y por tipo de filtro (continuación, reversión y sin filtro).
- P&L descriptivo con netting entre reglas (1 contrato): IS +USD 21.885 y OOS +USD 5.098 con fills de libro.

## Qué no queda demostrado
1. **OOS corto y no virgen**: 13 sesiones, 122 trades. El usuario vio estadísticas agregadas del backtest del proveedor de jun–sep sobre contratos poco líquidos. El OOS (+83,8) es 3,5 veces el IS (+23,9): lo razonable es esperar algo más cercano al IS, o menos si el calendario se minó.
2. **Multiplicidad desconocida**: el proveedor eligió 60 reglas de un espacio que no conocemos. El IS está contaminado por esa búsqueda; sólo el OOS cuenta, y el mejor-de-60 no se rechaza.
3. **Supuestos**: calendario de sesión CME mínimo (la plantilla de NinjaTrader no estaba disponible); ejecución idealizada (sin latencia); la réplica reproduce lo observado en dos contratos pero hay parámetros no identificables (calentamiento, margen de sesión).
4. **Cobertura**: faltan 2 semanas de junio y el tramo marzo–abril.

## Transferencia: mismo calendario congelado, sin reoptimizar
| Activo | IS media neta (ticks) / trades | OOS media neta / trades | p dirección OOS | p calendario placebo OOS |
|---|---|---|---:|---:|
| YM (Dow) | +3,8 (IC +0,4 a +7,4) / 1.875 | +15,8 (IC +6,3 a +25,1) / 227 | 0,0003 | 0,0005 |
| GC (oro) | +5,8 (IC −2,3 a +14,7) / 1.963 | −5,5 (IC −20,7 a +11,8) / 226 | 0,58 | 0,40 |
| ZB (bono 30a) | −0,8 / 1.358 | −0,8 / 171 | 0,20 | 0,35 |
| 6J (yen) | −1,4 / 1.796 | −1,8 / 174 | 0,75 | 0,81 |

Comisión USD 1,90 convertida a ticks de cada activo (para YM y GC es menor que la real de un contrato completo). Lectura: **sólo se transfiere a otro índice bursátil**; no a oro, bonos ni yen. Un índice correlacionado no es una réplica independiente (YM y MNQ comparten el flujo intradía de EEUU).

## Siguiente paso para confirmar
Una **única** apertura del holdout de MNQ (desde 2026-07-01, ticks de `edgelab-ticks-nt8-canonical`) con la especificación congelada y estos umbrales: media neta > 0, IC95 excluye 0 y p de dirección y de calendario placebo ≤ 0,05. Requiere decisión explícita del usuario porque consume el holdout; no se hizo.
