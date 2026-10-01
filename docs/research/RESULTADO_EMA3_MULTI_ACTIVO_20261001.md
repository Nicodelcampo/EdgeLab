# Tres EMAs · MNQ / YM / RTY · pantalla exploratoria sin L2

Fecha: 2026-10-01. Estado: **0/24 SCREEN_PASS; 10 NO_SUPPORT, 14 INCONCLUSIVE_SAMPLE.** No despliegue, no confirmación, no validación automática.

## Pregunta y autorización

Nico pidió pruebas con tres EMAs, cruce, barrido, persistencia y varios activos, más research de filtros habituales. Esto autoriza esta pantalla explícita, no el holdout ni todas las campañas históricas. No es TEMA ni replica filtros de espejos; usa entradas propias de precio. No modifica IPC × L2 de Codex.

## Corrida real y procedencia

- Kaggle privado: https://www.kaggle.com/code/nicolasbuttaro/edgelab-ema3-multiasset-20261001, versión 1, kernel 136594888, COMPLETE. Log: unos 57 s hasta resultados y 65 s hasta exportación, una vez iniciado el kernel; no incluye cola externa.
- Código congelado antes de lanzamiento: `9bbafc0ee90db9950ceeaeeffd5bd531c931b35e19dc8db894990d0b84719922`.
- Manifest: `4ebd53667c9819157ea708bb63a6833513ba98806f3d38985837f5dccaf02b1d`.
- Fuente dev original: foundation/f0b-compatibility-probe@391314907dec889599493c4a38282171d94a2f25. Rama de entrega separada `research/ema3-multiasset-20261001`, hija de `research/rty-no-l2-six-tests-20260930@0b7c70da1dd1bc73932fc6a1d4594e7afb9ce21f` para conservar su acta/registro; sin merge ni tocar worktrees locales.
- Preflight ejecutado coincide con fuente congelada; API de notebook devuelve exactamente el wrapper privado enviado; wrapper verifica y ejecuta el archivo congelado. Manifest de salida idéntico byte a byte.
- Dataset privado `nicolasbuttaro/edgelab-ticks-nt8-canonical`, versión 1. Seis parquets utilizados con tamaño/filas/SHA reconciliados contra AUDIT_MANIFEST, tres catálogos verificados. El transporte descargó además RTY06-26 por su inventario común, pero el motor no lo abrió ni usó para features/outcomes de esta campaña.
- El transporte usa URLs firmadas privadas, no se publica. Las descripciones antiguas de manifests pre-recompresión no sustituyen hashes actuales del audit zstd:19. Sin Lucid.

## Contrato de medición

54 fechas CME comunes de 2025-10-07 a 2025-12-31, seleccionadas por catálogo previo; lista completa en manifest. Tres índices bursátiles correlacionados: no son tres clases de mercado independientes. Desarrollo ya expuesto en campañas anteriores, especialmente RTY; no llamarlo holdout.

- Barras 5 minutos, sólo prints reales; tres EMAs20/50/200, adjustFalse, Globex continuo por contrato, mínimo600 barras de calentamiento y hasta7 días anteriores de historia. Sin velas sintéticas ni paridad exacta con NT8 certificada.
- CROSS: EMA20 cruza EMA50 en cierre conocido, precio del lado direccional de EMA200.
- SWEEP: apilamiento previo20/50/200, penetración intrabar ≥1tick de la EMA50 congelada al cierre anterior y recuperación al cierre actual; simétrico corto. Es geometría OHLC, no identificación de barrido real de stops.
- BASE; DWELL30=6 cierres anteriores consecutivos al lado correcto de EMA50; SLOPE200=pendiente anterior en30min; ADX25=ADX14 Wilder anterior≥25. Cada filtro usa un subconjunto del mismo calendario BASE, sin reemplazar rechazos por otras señales.
- Decisiones entre10:05 y14:45ET; entrada en primera quote exportada válida después de cierre+250ms y dentro30s; salida primera quote a partir de entrada+1h hasta16ET. Separación BASE >1h+60s, no solapamiento por activo/familia. Las dos familias son experimentos distintos, no una cartera conjunta libre de solapamiento.
- Entrada/salida agresivas al bid/ask, 1tick de deslizamiento por lado. Comisión RT supuesta MNQUSD1.20 (2.4ticks); YM/RTYUSD4.50 (.9tick). No fills ejecutados, edad de quote no certificada. Sensibilidad extra1tick/lado descriptiva.
- U=ATR14 Wilder de barra5min estrictamente anterior. Neto/U es unidad de volatilidad, **no R de riesgo ni rentabilidad de cuenta**. Tabla conserva ticks por instrumento; no comparar ticks como magnitud económica entre activos.
- 24 celdas ×2 endpoints: neto/U y cambio direccional de mid/U contra dirección aleatoria a idénticos momentos. Bootstrap20k por54fechas con ceros de actividad, Bonferroni48, una cola; ≥30 trades con quote de salida y≥20 fechas activas. Dos límites inferiores>0 para SCREEN_PASS. MDE80 aproximado, no certificado de potencia.
- La diferencia filtro−BASE es descriptiva: no se probó formalmente valor incremental. Los48 endpoints se presupuestaron completos aunque algunas celdas no alcanzan muestra.

## Cobertura y QA

Se perfilaron113.601.621 filas de los recortes de precio/quotes, incluida historia anterior y filas intermedias para continuidad; no equivalen a prints exclusivamente dentro de las54sesiones objetivo. Sin precio/volumen nulo o no positivo;152 filas con quotes inválidas no elegibles para ejecución. Conteos por sesión reconciliados.

231 eventos BASE únicos; **231 posiciones simuladas por quotes con entrada y salida observadas, 0 sin entrada y 0 salida desconocida**. Los filtros reutilizan estos eventos y no pueden sumarse como operaciones independientes. Máximo lag de entrada14.252s; máximo lag de salida13.624s. Se incluyeron las salidas retrasadas, no se censuraron por superar1s como en la pantalla RTY previa.

Selftests PASS: EMA por recurrencia independiente, Wilder plano/tendencia, invariancia de prefijos, salida retrasada incluida, salida desconocida bloquea inferencia, aritmética de costos. QA real RTY target-free de prefijos PASS. Auditoría posterior reproduce identities/subsets/timing/costos/mid-alpha y24estadísticas, incluidos bounds y gates. La repetición de bootstrap reutiliza el método congelado, no valida independientemente sus supuestos.

## Resultados completos

| Celda | Entradas con salida | Fechas activas | Neto / ATR | Neto ticks | Estado |
|---|---:|---:|---:|---:|---|
| MNQ_CROSS_BASE | 30 | 23 | +0.608 | +111.97 | NO_SUPPORT |
| MNQ_CROSS_DWELL30 | 10 | 9 | +0.238 | -5.40 | INCONCLUSIVE_SAMPLE |
| MNQ_CROSS_SLOPE200 | 12 | 10 | +0.214 | +16.10 | INCONCLUSIVE_SAMPLE |
| MNQ_CROSS_ADX25 | 4 | 4 | +1.503 | +139.60 | INCONCLUSIVE_SAMPLE |
| MNQ_SWEEP_BASE | 54 | 39 | -0.273 | -8.97 | NO_SUPPORT |
| MNQ_SWEEP_DWELL30 | 35 | 31 | -0.544 | -34.49 | NO_SUPPORT |
| MNQ_SWEEP_SLOPE200 | 54 | 39 | -0.273 | -8.97 | NO_SUPPORT |
| MNQ_SWEEP_ADX25 | 22 | 21 | -0.736 | -63.99 | INCONCLUSIVE_SAMPLE |
| YM_CROSS_BASE | 29 | 24 | -0.026 | +3.13 | INCONCLUSIVE_SAMPLE |
| YM_CROSS_DWELL30 | 8 | 7 | -0.278 | -2.52 | INCONCLUSIVE_SAMPLE |
| YM_CROSS_SLOPE200 | 16 | 14 | +0.152 | +14.98 | INCONCLUSIVE_SAMPLE |
| YM_CROSS_ADX25 | 6 | 6 | +0.562 | +74.27 | INCONCLUSIVE_SAMPLE |
| YM_SWEEP_BASE | 44 | 35 | -0.842 | -37.95 | NO_SUPPORT |
| YM_SWEEP_DWELL30 | 32 | 27 | -0.934 | -46.52 | NO_SUPPORT |
| YM_SWEEP_SLOPE200 | 44 | 35 | -0.842 | -37.95 | NO_SUPPORT |
| YM_SWEEP_ADX25 | 12 | 12 | -1.114 | -63.15 | INCONCLUSIVE_SAMPLE |
| RTY_CROSS_BASE | 30 | 24 | +0.614 | +21.23 | NO_SUPPORT |
| RTY_CROSS_DWELL30 | 10 | 9 | +0.479 | +22.30 | INCONCLUSIVE_SAMPLE |
| RTY_CROSS_SLOPE200 | 18 | 16 | +0.050 | -2.12 | INCONCLUSIVE_SAMPLE |
| RTY_CROSS_ADX25 | 10 | 10 | +1.007 | +46.30 | INCONCLUSIVE_SAMPLE |
| RTY_SWEEP_BASE | 44 | 31 | +0.094 | +4.90 | NO_SUPPORT |
| RTY_SWEEP_DWELL30 | 27 | 21 | +0.410 | +16.25 | INCONCLUSIVE_SAMPLE |
| RTY_SWEEP_SLOPE200 | 43 | 30 | +0.467 | +18.80 | NO_SUPPORT |
| RTY_SWEEP_ADX25 | 15 | 11 | +0.411 | +17.50 | INCONCLUSIVE_SAMPLE |

## Lectura y prioridades

1. Ninguna variante demuestra ventaja neta y direccional bajo este contrato. Diez alcanzan el mínimo de muestra y no pasan; catorce quedan inconclusas por muestra. **No equivale a probar que todas las EMAs sean inútiles.**
2. CROSS BASE MNQ y RTY tienen medias positivas (~+0.608 y+0.614ATR), pero sus límites inferiores netos corregidos son−0.859 y−0.878ATR. Son candidatos observados, no ganadores ni autorización para confirmación. YM CROSS tiene29trades: queda inconcluso incluso antes de inferencia.
3. SWEEP BASE es negativo en MNQ/YM (−0.273/−0.842ATR); RTY+0.094ATR con incertidumbre amplia. La excepción RTY SLOPE200 llega+0.467ATR con43trades/30fechas, pero límite inferior neto−0.522ATR: tampoco pasa.
4. La potencia no se resuelve sólo pidiendo muchos días: los eventos y reservas temporales dejan30/29/30cruces BASE en54fechas. DWELL30 reduce a10/8/10; ADX25 a4/6/10. Medias altas con4–10casos no son evidencia confiable. No aumentar ventanas ni bajar filtros después para rescatar estas celdas.
5. SLOPE200 no cambia ningún SWEEP en MNQ/YM y quita sólo1de44 enRTY. No aporta discriminación aquí; coincide con la geometría previa ya exigida. La relación se midió por identidades, no sólo conteos.
6. Antes de otra tanda: diseñar un evento más frecuente y un horizonte acorde, verificar frecuencia **sin desenlaces**, y congelar una pregunta nueva. Ejemplo candidato: toque/recuperación en1min con confirmación5min completada, pocas versiones y bandas ATR; no ejecutado ni elegido por rentabilidad en esta entrega. La banda puede distinguir mero contacto de penetración y controlar extensión sin sumar filtros redundantes.
7. No desplegar estas reglas ni abrir validación deEne–Mar automáticamente. No elegir el máximo de24medias para luego llamarlo confirmatorio.

## Research: filtros comunes y qué no demuestra la bibliografía

- **Pendiente/apilamiento y dirección:** Fidelity explica EMA, mayor peso reciente, reacción/whipsaws y pendiente/soporte. IG describe stack20/50/200 y varias temporalidades, habitualmente en escala diaria. Trasladar esos periodos a5min es una decisión de investigación, no una configuración óptima demostrada.
- **Fuerza ADX:** Fidelity usa>25 como referencia de tendencia fuerte. ADX no da dirección. Probado aquí de forma separada y anterior; redujo mucho la muestra de cruces, sin validar ventaja.
- **Permanencia:** seis cierres anteriores/30min es la hipótesis de Nico, no un estándar universal. Puede reducir ruido, pero también tardanza y potencia; aquí no mejoró consistentemente las medias entre activos/eventos.
- **Separación y extensión normalizadas por ATR:** ATR mide volatilidad, no dirección. Bandas normalizadas permiten comparar penetración/distancia, pero no hay umbral rentable universal en las fuentes consultadas. Pendiente de manifiesto propio.
- **Volumen relativo:** Schwab lo presenta como confirmación; volumen alto también aparece en agotamiento. Para intradía comparar contra la misma hora de otras sesiones; no usar volumen absoluto como filtro universal.
- **Marco temporal superior:** sólo vela superior terminada. Nunca incluir la vela superior todavía parcial o su cierre futuro al etiquetar la señal inferior.
- **Estructura/ruptura:** confirmación contra niveles de soporte/resistencia que ya existían antes del evento, no pivotes reconstruidos con futuro.
- **Horario/noticias:** calendario fechado disponible antes; no eliminar a posteriori días con pérdidas. No medido aquí.

Fuentes leídas (educación sobre uso, no ensayos de rentabilidad de estos futuros):

1. https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/ema
2. https://www.fidelity.com/viewpoints/active-investor/average-directional-index-ADX
3. https://www.schwab.com/learn/story/understanding-simple-moving-average-crossovers
4. https://www.schwab.com/learn/story/average-true-range-indicator-and-volatility
5. https://www.schwab.com/learn/story/ways-volume-can-help-confirm-price-trends
6. https://www.ig.com/en/trading-strategies/moving-averages--a-guide-to-trend-trading-241031

## Límites conservados

Bounds extremos de bootstrap20k usan aproximadamente21draws en cola: precisión aproximada. Calendarios correlacionados y exposición de desarrollo limitan inferencia. El baseline aleatorio de dirección sólo prueba orientación media, no superioridad frente a buy-and-hold ni a estrategia EMA rival. Resultado condicionado a catálogo, horarios, horizonte1h y costos supuestos; no barridos de liquidez certificados, stops, fills o P&L real.

No se accedió a outcomes fuera deOct–Dic2025. Los hashes de contenedores completos no significan evaluación de otras ventanas. Holdouts cerrados. No códigos de transporte ni raw, precios individuales, ledgers privados o URLs firmadas en Git.

**Aporte al referente:** la pantalla real multi-activo permite descartar la promoción de estas24celdas bajo su contrato; delimita pérdida de potencia y redundancia de filtros sin confundir medias positivas con ventaja validada.
