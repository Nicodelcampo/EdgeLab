# RTY60 ampliado: la ventaja inicial no se mantiene

## Veredicto

**NO PASA el screen ampliado ni G1. No promover a confirmación ni uso operativo.** Es un resultado negativo de esta configuración fija en desarrollo ampliado, no una prueba de que todo momentum sea inútil. No se añadieron filtros, se invirtió dirección ni se retunearon parámetros después de abrir resultados.

| Población | Sesiones | Trades simulados | Media trades/sesión | Neto USD/trade |
| --- | ---: | ---: | ---: | ---: |
| Original | 54 | 243 | 4,50 | +69,20 |
| Adicional | 121 | 535 | 4,42 | −20,14 |
| Conjunto | 175 | 778 | 4,45 | +7,77 |

La mediana del conjunto es 4 trades/sesión. Son resultados de un contrato RTY (no M2K), tras spread observado, comisión SUPUESTA de USD 2,25 por lado y un tick de deslizamiento por lado. No son fills reales ni comisiones certificadas del usuario.

## Estabilidad temporal y por contrato

| Tramo | Sesiones | Trades | Neto USD/trade |
| --- | ---: | ---: | ---: |
| 2025 Q4 | 56 | 250 | +64,14 |
| 2026 Q1 | 60 | 266 | +0,76 |
| 2026 Q2 | 59 | 262 | −38,91 |

| Contrato natural | Sesiones activas | Trades | Neto USD/trade |
| --- | ---: | ---: | ---: |
| RTY 12-25 | 47 | 212 | +89,53 |
| RTY 03-26 | 58 | 258 | +5,13 |
| RTY 06-26 | 60 | 267 | −49,44 |
| RTY 09-26 | 10 | 41 | −25,84 |

09-26 incluye sólo diez fechas de junio: su nombre NO significa que se leyeran desenlaces de julio–septiembre. El antiguo subconjunto de 03-26 era negativo; su muestra ampliada es ligeramente positiva en USD y negativa en U (−0,0161/trade). No trasladar la conclusión del subconjunto a las 58 fechas.

## Robustez e inferencia

- Total neto base: USD 6.044; sin los cinco mejores TRADES: **−USD 4.023,50**.
- Dos ticks de deslizamiento por lado: **−USD 2,23/trade**; tres: **−USD 12,23/trade**.
- Drawdown máximo del saldo de trades CERRADOS: USD 21.671. No es mark-to-market ni riesgo intratrade.
- G1 falla por dependencia de los cinco mejores trades y concentración en RTY 12-25 (314% del total neto, mientras otros contratos restan).
- Media neta: +0,0373 U/trade. Bootstrap estacionario nativo, clusters cronológicos de sesión, ratio sumPnL/sumTrades: 50.000 réplicas. IC percentil 95% [−0,1284; +0,2080] U. Límite inferior Bonf12 −0,1806 U; alpha_U también falla (−0,0874 inferior).
- Componente nativo bootstrap-t, 175 sesiones/10.000 réplicas válidas, confianza 99,1667%: intervalo [−0,1941; +0,2852] U. Tampoco establece media positiva.
- En las 121 fechas adicionales, neto −0,0980 U/trade y alpha_U −0,0044/trade; ambos límites corregidos son negativos.
- Se conserva presupuesto Bonf12; sensibilidad Bonf122 es presupuesto histórico PARCIAL, no FWER histórico certificado. N_eff total desconocido.
- 175 sesiones superan la barrera de tamaño del componente nativo, **no aprueban G2 global**: PBO/DSR con historia completa, WF de selección, vecinos y paridad siguen incompletos. No fabricar PBO con una única configuración.

## Población y protocolo congelado

Fechas del catálogo 20251007–20260630; 175 sesiones elegibles/activas, sin exclusiones por resultado. Las 121 adicionales incluyen dos fechas Q4 ya expuestas y 119 de enero–junio cuya exposición global en EdgeLab no está certificada. Es DEVELOPMENT ampliado autorizado por Nico, NO holdout ni OOS ciego. No se reetiqueta como validación automática del protocolo anterior.

Barras 5 min; diferencia de precio frente a 60 min (NO ROC porcentual) ≥ 1×SMA TR20 estrictamente anterior; dirección del cambio. Warmup 600 barras con hasta siete días calendario anteriores, reset por contrato. Señales desde 10:00 ET hasta cierre 14:45 ET. Reserva 3660 s. Entrada primera quote bid/ask válida estrictamente posterior a señal+250 ms, dentro de 30 s. Salida primera quote válida desde entrada real+60 min hasta 16:00 ET. Desconocidas/solapamientos bloquean; no descartar salidas tardías selectivamente.

Holdout general desde 20260701 cerrado. El archivo físico 09-26 se descargó/hasheó entero por custodia, pero los predicados de lectura de precios y targets quedaron anteriores a julio. NORTH_STAR prevalece sobre índices desactualizados y las enmiendas ES/NQ/L2 no abren RTY.

## Procedencia, ejecución y auditoría

- Fuente de módulos nativos: foundation@391314907dec889599493c4a38282171d94a2f25. Padre de entrega: 06ffb156f02e3ca2b27916602e789112dbc42de5.
- Consultados NORTH_STAR, edge_validation_contract, Brain research_history_ledger, holdout_guard, universo_estudio, costs, cluster_estimand y g2_ratio. El Brain no certifica exposición exhaustiva.
- Kaggle privado nicolasbuttaro/edgelab-rty60-expanded-20261001, versión 1 COMPLETE; kernel 136605154; fuente exacta verificada, DONE a 102,62 s de cómputo.
- Manifiesto asentado en Notion antes de los nuevos outcomes: SHA-256 3a8ed3160dfc993745eb4e862924cee55fbb129dd6d672219589f11d2b07fd19. Runner 4236787c7688c33e088b9b3aa6b24e996fd0a1e5529ec17b5eb26bebeb852e31. Módulos exactos en manifest.json.
- Custodia y preflight leídos antes de resultados; manifests originales tienen hash pre-recompresión ZSTD, bytes actuales contra AUDIT_EXPECTED congelado. No confundirlos ni sustituirlos silenciosamente.
- 54 tests dirigidos PASS (48 previos + 6 nuevos), NO suite completa; 12 chequeos de prefijo PASS.
- 778/778 COMPLETE, cero solapamientos registrados. Auditoría independiente de aritmética, identidad y agregaciones de las 778 filas. Los 243 trades originales reproducen señal, quotes y PnL exactamente.
- Seis muestras raw independientes (inicio/medio/fin de 06-26 y 09-26) verifican barras/TR/ROC y primera quote válida. NO replay independiente exhaustivo de todas las filas.
- No certificación de reloj absoluto, edad de quote, fills en vivo, fees del usuario ni paridad NT8. Raw, ledgers de precio, productor privado y URLs firmadas no se publican.
- Gráfico canónico paired-panels con preflight estático aprobado. Revisión visual de navegador no ejecutada: el verificador disponible lanza Chromium separado, prohibido en este entorno. No afirmar QA visual.

## Decisión y entrega

Conservar esta configuración y su fracaso como referencia; no consumir holdout para rescatarla. Una hipótesis nueva necesitará su propio protocolo, presupuesto de búsqueda y separación de muestras.

Acta, manifiesto, resultados agregados, código exacto público y MEDIDO se entregan juntos en research/rty60-expanded-20261001. Rama aislada: sin merge ni cambios a allowlist, fuentes, campañas IPC/L2 o worktrees locales.

Aporte al referente: ampliar la historia evita confundir una media inicial favorable con una ventaja estable; la frecuencia se mantiene, pero el resultado posterior y la robustez no acompañan.
