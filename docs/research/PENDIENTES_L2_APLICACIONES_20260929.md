# Investigación pendiente: usos adicionales de L2 — 2026-09-29

Estado: **PENDIENTE DE INVESTIGACIÓN**. Autorización de Nico en chat: registrar las opciones e iniciar pruebas en sandbox, pudiendo descargar datos públicos. No autoriza abrir reservas/holdout, modificar la corrida NQ-CRUCE25-CLIMA ni promover estrategias.

Rama: `foundation/f0b-compatibility-probe`. HEAD de consulta: `f02075acfc08251e7f127384e9a99f12a85761bf`.
Herramienta solicitada `research`: no expuesta en esta sesión; se usan búsquedas web, Kaggle MCP y GitHub MCP. No se simula su uso.

## Espacio de investigaciones

| ID | Pregunta y métrica | Estado y requisito |
|---|---|---|
| L2-R01 | Costo de ejecución: ¿spread, profundidad y retiros agregan información sobre shortfall y markout? | PENDIENTE. Extensión de EXEC-QI a instantes de señal; no repetir como nueva la grilla ya medida. Cotizaciones sincronizadas y latencia/cola explícitas. |
| L2-R02 | Absorción/reposición vs agotamiento cerca de A/B: flujo agresivo elevado con poco avance, reposición posterior o caída de presión. | PENDIENTE. Definición causal, precios absolutos y mensajes/trades sincronizados. La reposición visible no demuestra iceberg. |
| L2-R03 | Ruptura acompañada vs frágil: presión, retirada delante y apoyo detrás. | PENDIENTE. Comparar contra mismo precio/volumen, horario y volatilidad; una pared visible no implica soporte. |
| L2-R04 | Camino hacia B: ¿flujo/liquidez explica avance y frenado? | PENDIENTE. Descriptivo primero; una regla de salida sólo usa información anterior a la decisión. No mirar NQ actual como parte de este piloto. |
| L2-R05 | Política de entrada: inmediata vs límite con vencimiento vs esperar spread. | PENDIENTE. Extensión de EXEC-QI a señales. Medir todos los intentos, incluso no llenados; no afirmar cola real con MBP. MM-QI ya muerto en su alcance, no reabrir silenciosamente. |

## Fuentes candidatas

1. https://www.kaggle.com/datasets/martinsn/high-frequency-crypto-limit-order-book-data — BTC/ETH/ADA, 15 niveles, agregaciones 1 s/1 min/5 min, cantidades de límites, mercado y cancelaciones. Prioridad de laboratorio. Un minuto NO sirve para fills rápidos ni secuencia intrasegundo.
2. https://www.kaggle.com/competitions/optiver-realized-volatility-prediction/data — dos niveles y trades por segundo; variables de liquidez y predicción de riesgo. Ventanas anonimizadas, no cola exacta. Revisar licencia de competencia antes de reutilización.
3. https://www.kaggle.com/datasets/praanj/limit-orderbook-data — precios/volúmenes de diez niveles; estudio de forma del libro. Fotos no distinguen ejecución de cancelación.
4. Datos propios NQ/ES: no hay raw L2 en el sandbox inventariado; los JSON de trades previos no sustituyen mensajes del libro. Solicitar/exportar una muestra autorizada y sincronizada antes de pruebas de estrategia.

## Investigación de fuentes ya iniciada

- `MANIFIESTO_EJECUCION_QI_L2_20260924.md` §10: simulación de pasivo/agresivo ya medida sobre grilla uniforme; falta en señales, fills reales y confirmación. No transportar costos entre mercados.
- Cont, Kukanov y Stoikov: https://arxiv.org/abs/1011.6402. OFI y profundidad explican cambios contemporáneos; relación contemporánea NO es predicción operable.
- Gould y Bonart: https://arxiv.org/abs/1512.03492. QI para siguiente movimiento del midprice en acciones; no implica rentabilidad de futuros.

## Piloto P0 (diseño escrito antes de calcular outcomes)

Laboratorio público BTC, archivo `BTC_1min.csv`, dataset martinsn v1. Es una prueba de factibilidad exploratoria, NO confirmación ni réplica de los papers. Mantener raw local-only y SHA-256.

1. Perfil, cobertura temporal, gaps, duplicados, nulos, signos y esquema. Verificar semántica antes de llamar a una variable profundidad/QI/OFI.
2. Si hay flujos válidos, construir desequilibrio de mercado agregado y diferencia de flujo neto de límites (altas menos cancelaciones), normalizados por su actividad. Son proxies; no el OFI exacto de eventos de Cont.
3. Describir asociación con retorno de midprice contemporáneo y, separadamente, del minuto siguiente; horizonte único 1 min. Nada de optimización de horizontes.
4. Comparar baseline (retorno previo, magnitud de retorno previo, spread) con baseline + dos proxies L2. Entrenar en los primeros 2/3 de días completos observados; evaluar en el tercio final. Purga en frontera y gaps. Sin barajar filas.
5. OLS con normalización sólo de entrenamiento y ridge fijo 1e-6 por estabilidad numérica; publicar RMSE y R² fuera de muestra, coeficientes, recuentos y diagnóstico por día. No convertirlo a P&L.
6. Señal explícita de éxito del piloto: extracción reproducible y prueba temporal válida; una mejora predictiva es exploratoria y requiere réplica. Si no hay mejora, no buscar corte ganador.
7. Para absorción, ruptura o fills, un minuto es insuficiente: estados BLOQUEADO_DATOS hasta contar con mensajes y precios sincronizados. No imputar evidencia.

Presupuesto: dos proxies, un horizonte y una comparación de modelos; sin grilla. Publicar también resultado negativo. Los días del tercio final son evaluación de este piloto, no holdout confirmatorio: ya quedan expuestos.

## Aporte al referente

Se separan opciones de investigación, trabajo ya medido y datos realmente necesarios, antes de probar retornos; se preservan la corrida vigente y las reservas.

## Actualización tras P0

Primer piloto BTC a un minuto ejecutado y publicado en `RESULTADO_L2_PUBLICO_P0_20260929.md`: no mejora agregada frente al baseline. R01–R05 permanecen pendientes en su alcance de estrategia; fuentes Optiver/10 niveles todavía sin pruebas. Próximo requisito: temporización/semántica auditada y mensajes sincronizados. No promover ni cambiar parámetros a partir del tercio final ya expuesto.
