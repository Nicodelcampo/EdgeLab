# Banco de ideas (generado por `python tools/ideas.py --write`; no editar a mano)

Estado: VIGENTE. Fuente: `docs/research/ideas/BANCO_IDEAS.jsonl` (`edgelab/research/ideas.py`).

Balance: `{"fuente_tipo": {"literatura": 7, "edgelab": 9, "sqx": 2, "practicante": 9}, "clase": {"tendencia": 5, "carry_macro": 1, "estacionalidad": 3, "evento": 2, "reversion": 5, "ruptura": 3, "volatilidad": 3, "microestructura": 3, "cartera": 2}, "prior": {"alto": 4, "medio": 15, "bajo": 8}, "estado": {"EN_DISENO": 2, "PROPUESTA": 17, "REFUTADA": 4, "EN_PRUEBA": 1, "PISTA_VIVA": 3}, "horizonte": {"días-meses": 2, "semanas": 1, "días": 2, "horas": 1, "intradía": 16, "overnight": 1, "horas-días": 4}}`

## LIT-CARRY-FX — Carry de monedas
- Clase: carry_macro · fuente: literatura · prior: alto · estado: PROPUESTA · horizonte: semanas · activos: AUDUSD, NZDUSD, USDJPY, EURJPY, GBPJPY, USDCAD, USDCHF
- Mecanismo: Las monedas de tasa alta se aprecian frente a las de tasa baja más de lo que predice la paridad de tasas (el diferencial se cobra vía swap).
- Justificación económica: Prima por riesgo de crash: el carry pierde fuerte en crisis de liquidez; quien lo provee cobra por ese riesgo.
- Cómo podría refutarse: Con swaps reales de la cuenta objetivo, la canasta de carry 2013-2026 no tiene retorno neto > 0 o su cola izquierda rompe las reglas de drawdown de la prop.
- Traducción: SQX/MT5 D1: posición en pares según el signo del swap (dato del bróker); filtro de tendencia opcional; requiere tenencia de varios días (cuenta swing).
- Fuentes: Lustig, Roussanov, Verdelhan (2011), Common Risk Factors in Currency Markets, RFS; Koijen, Moskowitz, Pedersen, Vrugt (2018), Carry, JFE

## EL-KNN-SOMBRA — Capa KNN sobre las operaciones pasadas de una regla propia (como T de FundedSync)
- Clase: cartera · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: intradía · activos: NQ, ES, YM, RTY
- Mecanismo: Capa KNN sobre las operaciones pasadas de una regla propia (como T de FundedSync)
- Justificación económica: Ver RESULTADO_MECANISMOS.md §2
- Cómo podría refutarse: T: única que gana también fuera de días de tendencia
- Traducción: Probar sobre PREAPERTURA-NQ y CVGAP-ES-C (desarrollo → réplica no mirada)
- Fuentes: docs/research/fundedsyncstack_20261115/RESULTADO_MECANISMOS.md

## PRAC-VOL-TARGET — Cartera con volatilidad objetivo y tendencia simple (Carver)
- Clase: cartera · fuente: practicante · prior: medio · estado: PROPUESTA · horizonte: días-meses · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD, XAGUSD, WTI, BRENT, COBRE, GAS, EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD
- Mecanismo: Escalar cada posición por la inversa de su volatilidad reciente estabiliza el riesgo y mejora el Sharpe de reglas simples.
- Justificación económica: La volatilidad es persistente y no predice proporcionalmente el retorno; ajustar el tamaño reduce las colas.
- Cómo podría refutarse: La cartera con volatilidad objetivo no mejora la esperanza del desafío de la prop (drawdown y cobro) frente al tamaño fijo.
- Traducción: Money management de SQX por volatilidad/ATR; en EdgeLab, simulación de la prop con ambos tamaños.
- Fuentes: Carver (2015), Systematic Trading; Moreira, Muir (2017), Volatility-Managed Portfolios, JF

## LIT-FIN-DE-MES — Cambio de mes en índices
- Clase: estacionalidad · fuente: literatura · prior: alto · estado: REFUTADA · horizonte: días · activos: USA500, USATECH, USA30, DAX, Nikkei, FTSE, EuroStoxx, Russell
- Mecanismo: Los índices rinden más en los últimos días hábiles y primeros del mes que en el resto.
- Justificación económica: Flujos de caja institucionales periódicos (pagos y aportes de fin de mes) presionan precios de forma predecible.
- Cómo podría refutarse: 2013-2026 en los 8 índices: la ventana de cambio de mes no rinde más que ventanas del mismo largo elegidas al azar. | 2026-11-15: refutada en CFD (docs/research/macro_literatura_20261114/RESULTADO.md).
- Traducción: SQX D1: largo del día -N al +M del mes (N, M ≤ 4), salida por tiempo; sin indicadores.
- Fuentes: Ariel (1987), A Monthly Effect in Stock Returns, JFE; Etula, Rinne, Suominen, Vaittinen (2020), Dash for Cash: Monthly Market Impact of Institutional Liquidity Needs, RFS

## LIT-NOCHE — Retorno nocturno vs diurno en índices
- Clase: estacionalidad · fuente: literatura · prior: medio · estado: REFUTADA · horizonte: overnight · activos: USA500, USATECH, USA30, Russell
- Mecanismo: Casi todo el retorno de los índices de EE.UU. ocurre fuera del horario regular (cierre → apertura).
- Justificación económica: Prima por cargar riesgo durante el cierre (sin poder salir) y presión de venta intradía.
- Cómo podría refutarse: 2013-2026: largo del cierre a la apertura no rinde más que largo de la apertura al cierre, después de swap y spread. | 2026-11-15: refutada en CFD (docs/research/macro_literatura_20261114/RESULTADO.md).
- Traducción: SQX H1: largo al cierre RTH, salida a la apertura; requiere tenencia overnight.
- Fuentes: Cliff, Cooper, Gulen (2008), Return Differences between Trading and Non-trading Hours

## FS-O-OVERNIGHT — Tenencia overnight con filtro diario
- Clase: estacionalidad · fuente: practicante · prior: bajo · estado: PROPUESTA · horizonte: intradía · activos: NQ
- Mecanismo: Tenencia overnight con filtro diario
- Justificación económica: La del vendedor (docs/research/fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md)
- Cómo podría refutarse: Positivo débil en todos los tramos | medido 2026-11-16 (RESULTADO_CADENA.md)
- Traducción: Overnight en futuros con filtro; cruzar con LIT-NOCHE
- Fuentes: FUNDEDSYNCSTACK 1.0.0.5 (traducción en edgelab/research/fundedsyncstack)

## LIT-PRE-FOMC — Deriva antes del FOMC
- Clase: evento · fuente: literatura · prior: medio · estado: PROPUESTA · horizonte: horas · activos: USA500, USATECH, USA30
- Mecanismo: El S&P sube en las 24 horas previas a los anuncios del FOMC más que en cualquier otro día.
- Justificación económica: Resolución de incertidumbre y prima de riesgo concentrada antes del anuncio.
- Cómo podría refutarse: 2016-2026 (posterior a la publicación): la ventana previa al FOMC no rinde más que el resto de los días; el efecto publicado se reportó debilitado.
- Traducción: Calendario FOMC como indicador externo en SQX (o regla de fecha); largo H1 desde 24 h antes hasta el anuncio.
- Fuentes: Lucca, Moench (2015), The Pre-FOMC Announcement Drift, JF

## FS-C-GAP — Gap de apertura en 1 min
- Clase: evento · fuente: practicante · prior: bajo · estado: PROPUESTA · horizonte: intradía · activos: NQ
- Mecanismo: Gap de apertura en 1 min
- Justificación económica: La del vendedor (docs/research/fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md)
- Cómo podría refutarse: Régimen: OOS +10 pts, 2024–2025 −4 | medido 2026-11-16 (RESULTADO_CADENA.md)
- Traducción: Gap con confirmación intradía (nuestros gaps M1 ≈ 0)
- Fuentes: FUNDEDSYNCSTACK 1.0.0.5 (traducción en edgelab/research/fundedsyncstack)

## EL-DELTASWEEP-SEQ — Secuencias de disparos de barrido de delta (NQ)
- Clase: microestructura · fuente: edgelab · prior: bajo · estado: EN_PRUEBA · horizonte: intradía · activos: NQ
- Mecanismo: Dos o más barridos de delta con flip en el mismo sentido en poco tiempo marcan absorción insistente y resuelven a favor del que absorbe.
- Justificación económica: Agresores atrapados repetidamente en un nivel defendido.
- Cómo podría refutarse: Forward congelado en NQ con n ≥ 30 no da R > 0; DELTASWEEP-PAT sin celdas sobre el nulo. | 2026-11-14: patrones (DELTASWEEP-PAT, ≈79.000 celdas) refutados; queda sólo S2 V4W AM en forward.
- Traducción: No traducible a barras de SQX (necesita ticks con bid/ask): sigue en EdgeLab; en MT5 sólo si el bróker da ticks reales.
- Fuentes: docs/research/deltasweep_20261114/MEDIDO_Y_NO_MEDIDO.md (S2 V4W AM: +0,26/+0,28 R, bajo el nulo)

## FS-A-ABSORB — Absorción por delta en 1 y 20 min
- Clase: microestructura · fuente: practicante · prior: bajo · estado: PROPUESTA · horizonte: intradía · activos: NQ
- Mecanismo: Absorción por delta en 1 y 20 min
- Justificación económica: La del vendedor (docs/research/fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md)
- Cómo podría refutarse: A1 sin ventaja (fricción); A20 sólo reciente | medido 2026-11-16 (RESULTADO_CADENA.md)
- Traducción: Probar con delta real de ticks, no proxy
- Fuentes: FUNDEDSYNCSTACK 1.0.0.5 (traducción en edgelab/research/fundedsyncstack)

## FS-S-SWEEP — Barrido de liquidez en 3 min
- Clase: microestructura · fuente: practicante · prior: bajo · estado: PROPUESTA · horizonte: intradía · activos: NQ
- Mecanismo: Barrido de liquidez en 3 min
- Justificación económica: La del vendedor (docs/research/fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md)
- Cómo podría refutarse: Sólo 2024–2026 positivo | medido 2026-11-16 (RESULTADO_CADENA.md)
- Traducción: Buscar variable de régimen; relacionar con DeltaSweep
- Fuentes: FUNDEDSYNCSTACK 1.0.0.5 (traducción en edgelab/research/fundedsyncstack)

## EL-CAJA-AMARILLA-MACRO — Reversión tras extensión fallida (caja amarilla) en escala macro
- Clase: reversion · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: horas-días · activos: USA500, USATECH, USA30, DAX, XAUUSD, WTI, EURUSD
- Mecanismo: Tras un impulso, la extensión a favor que vuelve a cerrar dentro de la zona de alto volumen revierte hacia el 50 % del impulso.
- Justificación económica: Agresores atrapados en la extensión fallida cierran en contra; la zona de volumen es donde estaba la liquidez del movimiento.
- Cómo podría refutarse: En H1/H4 multi-activo 2013-2026 la regla no supera a su control (la misma expansión sin la extensión fallida) ni a su nulo de proyecto.
- Traducción: SQX H1/H4: rango de N barras > k·ATR; nueva extensión que cierra de vuelta; entrada en contra, objetivo 50 % del impulso, stop en el extremo.
- Fuentes: docs/research/FACTORES_CON_VENTAJA.md: F-AMARILLA-DESPUES-VWAP-LEJOS (holdout obj 50 % +0,086 R, n 11)

## EL-VWAP-BANDA3 — Tercera banda del VWAP (±3 desvíos): extensión extrema intradía
- Clase: reversion · fuente: edgelab · prior: medio · estado: REFUTADA · horizonte: intradía · activos: SP, NQ, DJ, Russell, DAX, Nikkei, FTSE, EuroStoxx
- Mecanismo: Un cierre más allá de ±3 desvíos del VWAP de la sesión marca una extensión extrema: o revierte hacia la banda 2/1/VWAP (agotamiento) o, en días de tendencia, continúa; la dosis (1→2→3 desvíos) debería ordenar el efecto.
- Justificación económica: El VWAP es el precio de referencia de ejecución institucional; a 3 desvíos los algoritmos de ejecución dejan de comprar caro/vender barato y aparecen los que revierten a la media; en tendencias fuertes, en cambio, el desvío lo mueve el flujo y la banda se vuelve soporte en movimiento.
- Cómo podría refutarse: En M1 de 12 años (8 índices) la reversión desde ±3σ no supera al nulo intradía ni a la misma regla desde ±2σ (sin dosis-respuesta), o sólo funciona en neto (fricción). | 2026-11-15: dosis en bruto en 2012–2019 y 2025-08→2026-09, negativa 2020–2023: candidata de régimen (RESULTADO.md). | régimen no detectable (RESULTADO_REGIMEN_VWAPB.md).
- Traducción: Generador en m1_intradia: primer cierre fuera de ±3σ del VWAP anclado a las 09:30 NY (después de 30 min); reversión a mercado con objetivo banda 2σ / 1σ / VWAP y stop 4σ o extremo + 0,5σ; continuación como variante opuesta; control ±2σ; cierre 15:55; nada al fin de semana.
- Fuentes: Pedido de Nico (2026-11-15); edgelab/research/rasgos_comunes.py (VWAP y desvíos ya calculados; sólo se usa ≥ 1 desvío); docs/research/luximb_amarilla_20261111/r2/EXPLORACION.md (todas las celdas sobre el nulo tenían VWAP lejos)

## EL-VWAP-LEJOS — Precio lejos del VWAP y yendo hacia él
- Clase: reversion · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: intradía · activos: USA500, USATECH, USA30, DAX
- Mecanismo: A ≥ 1 desvío del VWAP diario y moviéndose hacia él, el precio tiende a volver al VWAP.
- Justificación económica: El VWAP es el precio de referencia de ejecución institucional; los desvíos grandes atraen órdenes de ejecución.
- Cómo podría refutarse: En H1 multi-índice, entrar hacia el VWAP desde ≥ 1 desvío no supera a entradas al azar a la misma distancia.
- Traducción: SQX H1: VWAP y sus bandas (bloque nativo), entrada hacia el VWAP, objetivo el VWAP, stop ATR.
- Fuentes: docs/research/luximb_amarilla_20261111/r2/EXPLORACION.md (todas las celdas sobre el nulo tenían VWAP lejos)

## FS-N-NDAY — Varios días a la baja → largo
- Clase: reversion · fuente: practicante · prior: bajo · estado: PROPUESTA · horizonte: intradía · activos: NQ
- Mecanismo: Varios días a la baja → largo
- Justificación económica: La del vendedor (docs/research/fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md)
- Cómo podría refutarse: Sólo el último año | medido 2026-11-16 (RESULTADO_CADENA.md)
- Traducción: Reversión multi-día en índices
- Fuentes: FUNDEDSYNCSTACK 1.0.0.5 (traducción en edgelab/research/fundedsyncstack)

## SQX-PLANTILLA-REVERSION — Línea de base: plantilla de reversión de SQX
- Clase: reversion · fuente: sqx · prior: bajo · estado: EN_DISENO · horizonte: días · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD
- Mecanismo: Builder con la plantilla estándar de reversión (señales contrarias, órdenes límite) sobre la canasta.
- Justificación económica: Línea de base para las ideas de reversión (caja amarilla, VWAP lejos).
- Cómo podría refutarse: Si las ideas de reversión con mecanismo no le ganan, no agregan nada.
- Traducción: apply_build_template Mean-Reversal + Data con la canasta; proyecto nulo hermano.
- Fuentes: SQX internal/web/BUILDER/simpleTemplates: Mean-Reversal

## FS-T-KNN-ORB — ORB de 15 min filtrado por KNN de 14 rasgos entrenado con operaciones sombra
- Clase: ruptura · fuente: practicante · prior: alto · estado: PISTA_VIVA · horizonte: intradía · activos: NQ
- Mecanismo: ORB de 15 min filtrado por KNN de 14 rasgos entrenado con operaciones sombra
- Justificación económica: La del vendedor (docs/research/fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md)
- Cómo podría refutarse: OOS 2020–2023 +13,2 pts t 4,37 (> 1,92 nulo); positiva 2024–2026; 19 ops/mes con stop | medido 2026-11-16 (RESULTADO_CADENA.md)
- Traducción: Filtro KNN sobre operaciones sombra aplicable a ORB/VWAP/zonas de EdgeLab
- Fuentes: FUNDEDSYNCSTACK 1.0.0.5 (traducción en edgelab/research/fundedsyncstack)

## EL-NIVELES-NO-DEFIENDEN — Los niveles con actividad no defienden: continuación al romperlos
- Clase: ruptura · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: horas-días · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD
- Mecanismo: Donde hubo mucha actividad el precio atraviesa más que en un nivel cualquiera; en escala macro, la ruptura del máximo/mínimo del día o semana previa continúa.
- Justificación económica: Stops acumulados detrás de niveles visibles; al dispararse aceleran el movimiento.
- Cómo podría refutarse: Rupturas del máximo/mínimo previo en H1/H4 no continúan más que cruces de niveles al azar a igual distancia. | 2026-11-15: ruptura del día previo intradía en 4 índices M1 ≈ 0 en bruto (RESULTADO_LOTE2.md); la versión H1/H4 multi-día sigue sin medir.
- Traducción: SQX H1/H4: orden stop en el máximo/mínimo del día o semana previa; objetivo y stop en ATR.
- Fuentes: FACTORES: F-HFT-CLUSTER-GRANDE-NO-DEFIENDE (A-D), F-HFT-ZONAS-NO-SON-SOPORTE

## FS-SALIDA-AL-CIERRE — Mantener la ruptura hasta el cierre con stop duro, sin salidas técnicas
- Clase: ruptura · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: intradía · activos: NQ, ES, YM, RTY
- Mecanismo: Mantener la ruptura hasta el cierre con stop duro, sin salidas técnicas
- Justificación económica: Ver RESULTADO_MECANISMOS.md §2
- Cómo podría refutarse: Descriptivo FundedSync: salidas técnicas pierden, las que llegan al cierre ganan mucho
- Traducción: Variante en ORB/PREAPERTURA/CVGAP de EdgeLab y en S/W/N/A20 sobre otros índices
- Fuentes: docs/research/fundedsyncstack_20261115/RESULTADO_MECANISMOS.md

## LIT-TSMOM — Momentum de serie de tiempo multi-activo
- Clase: tendencia · fuente: literatura · prior: alto · estado: EN_DISENO · horizonte: días-meses · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD, XAGUSD, WTI, BRENT, COBRE, GAS, EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD
- Mecanismo: El retorno de los últimos 1-12 meses de un activo predice el signo del próximo mes en índices, bonos, monedas y materias primas.
- Justificación económica: Subreacción inicial a la información y sobrerreacción tardía (anclaje, flujos de cobertura y de inversores lentos); prima de riesgo por crisis.
- Cómo podría refutarse: La canasta 2013-2026 (posterior a la publicación) en CFD no supera a la misma canasta con señales de signo aleatorio, después de costos y swap. | 2026-11-15: forma semanal sin fin de semana ≈ 0 en bruto (RESULTADO.md); la forma mensual sigue sin medir. Sigue en SQX (lote 1).
- Traducción: SQX D1/H4: largo/corto según el retorno de N días (N 20-250) o cruce de medias lentas; stop ATR largo; tamaño por volatilidad; fitness sobre la canasta.
- Fuentes: Moskowitz, Ooi, Pedersen (2012), Time Series Momentum, JFE; Hurst, Ooi, Pedersen (2017), A Century of Evidence on Trend-Following Investing, JPM

## EL-PREDECIR-DIA-TENDENCIA — Predecir días de tendencia (rango temprano, volumen relativo de apertura, amplitud)
- Clase: tendencia · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: intradía · activos: NQ, ES, YM, RTY
- Mecanismo: Predecir días de tendencia (rango temprano, volumen relativo de apertura, amplitud)
- Justificación económica: Ver RESULTADO_MECANISMOS.md §2
- Cómo podría refutarse: Noche/gap/vol20/tend60 no los anticipan (13–19 % vs 15,6 %)
- Traducción: Filtro común para toda regla de ruptura; familia E0 sin retornos
- Fuentes: docs/research/fundedsyncstack_20261115/RESULTADO_MECANISMOS.md

## FS-Z-TRENDDAY — Día de tendencia por buckets de 15 min en RTH
- Clase: tendencia · fuente: practicante · prior: medio · estado: PISTA_VIVA · horizonte: intradía · activos: NQ
- Mecanismo: Día de tendencia por buckets de 15 min en RTH
- Justificación económica: La del vendedor (docs/research/fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md)
- Cómo podría refutarse: OOS +26,6 pts t 3,19, sin stop, 2 ops/mes | medido 2026-11-16 (RESULTADO_CADENA.md)
- Traducción: Detectar día de tendencia temprano; cruzar con noche movida (ASIA)
- Fuentes: FUNDEDSYNCSTACK 1.0.0.5 (traducción en edgelab/research/fundedsyncstack)

## LIT-INTRADAY-MOM — Momentum intradía de la primera media hora
- Clase: tendencia · fuente: literatura · prior: medio · estado: REFUTADA · horizonte: intradía · activos: USA500, USATECH, USA30, Russell
- Mecanismo: El retorno de la primera media hora (con el overnight) predice el de la última media hora del mismo día.
- Justificación económica: Rebalanceo tardío de inversores informados y cobertura de opciones/ETF apalancados al cierre.
- Cómo podría refutarse: En USA500/USATECH 2013-2026 la última media hora con el signo de la primera no supera al azar después de costos. | 2026-11-15: refutada en CFD (docs/research/macro_literatura_20261114/RESULTADO.md).
- Traducción: SQX M30/H1 con filtro horario: entrada 15:30 ET según el signo 16:00(t-1)→10:00, salida al cierre.
- Fuentes: Gao, Han, Li, Zhou (2018), Market Intraday Momentum, JFE

## SQX-PLANTILLA-TENDENCIA — Línea de base: plantilla de tendencia/ruptura de SQX
- Clase: tendencia · fuente: sqx · prior: bajo · estado: PROPUESTA · horizonte: horas-días · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD
- Mecanismo: Builder con la plantilla estándar de tendencia (órdenes stop, señales a favor) sobre la canasta.
- Justificación económica: Línea de base: toda idea de tendencia con mecanismo tiene que ganarle a la búsqueda genérica de su estilo.
- Cómo podría refutarse: Si las ideas con mecanismo no le ganan, el mecanismo no agrega nada sobre la búsqueda genérica.
- Traducción: apply_build_template TrendFollowing + Data con la canasta; proyecto nulo hermano.
- Fuentes: SQX internal/web/BUILDER/simpleTemplates: TrendFollowing

## EL-HUIDA-VETO — No entrar en continuación tras una huida en contra
- Clase: volatilidad · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: horas-días · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD
- Mecanismo: Después de un movimiento fuerte en contra, las entradas de continuación rinden peor; vetarlas mejora cualquier regla de tendencia.
- Justificación económica: La huida indica cambio de régimen o liquidación forzada; la continuación pierde su ventaja.
- Cómo podría refutarse: Aplicado como filtro a LIT-TSMOM, el veto no mejora el R neto ni en bruto (si sólo mejora en neto es fricción).
- Traducción: Filtro en SQX: rango de las últimas N barras en contra > k·ATR → no entrar.
- Fuentes: FACTORES: F-HUIDA-CONTINUACION (PISTA_VIVA)

## EL-STOP-POR-VOL-PRONOSTICADA — Stops y tamaño por la volatilidad pronosticada (rugoso/HAR) en vez del ATR de ayer
- Clase: volatilidad · fuente: literatura · prior: medio · estado: PROPUESTA · horizonte: intradía · activos: NQ, ES, YM, RTY
- Mecanismo: La volatilidad diaria es rugosa y pronosticable (−30 % de error vs caminata aleatoria); el stop/tamaño ajustado al rango esperado mantiene la fricción en R y el riesgo en USD estables
- Justificación económica: Fricción fija en puntos: un stop proporcional al rango esperado evita los stops cortos que sólo pagan fricción
- Cómo podría refutarse: La cartera v2 con stops/tamaño por vol pronosticada no mejora R ni drawdown frente a micros fijos en datos no usados
- Traducción: Capa de dimensionamiento sobre la cartera v2 y las reglas de ruptura
- Fuentes: Gatheral, Jaisson, Rosenbaum (2014) Volatility is Rough; Corsi (2009) HAR-RV; docs/research/fundedsyncstack_20261115/RESULTADO_TANDA2.md

## FS-R-ATRPHASE — Fase de ATR en 10 min (expansión tras compresión)
- Clase: volatilidad · fuente: practicante · prior: medio · estado: PISTA_VIVA · horizonte: intradía · activos: NQ
- Mecanismo: Fase de ATR en 10 min (expansión tras compresión)
- Justificación económica: La del vendedor (docs/research/fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md)
- Cómo podría refutarse: OOS +28,1 pts t 2,46, sin stop, 3 ops/mes | medido 2026-11-16 (RESULTADO_CADENA.md)
- Traducción: Gatillo por régimen de volatilidad; stop relativo al ATR
- Fuentes: FUNDEDSYNCSTACK 1.0.0.5 (traducción en edgelab/research/fundedsyncstack)
