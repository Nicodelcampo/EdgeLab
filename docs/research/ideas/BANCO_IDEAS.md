# Banco de ideas (generado por `python tools/ideas.py --write`; no editar a mano)

Estado: VIGENTE. Fuente: `docs/research/ideas/BANCO_IDEAS.jsonl` (`edgelab/research/ideas.py`).

Balance: `{"fuente_tipo": {"literatura": 6, "edgelab": 5, "sqx": 2, "practicante": 1}, "clase": {"tendencia": 3, "carry_macro": 1, "estacionalidad": 2, "evento": 1, "reversion": 3, "ruptura": 1, "volatilidad": 1, "microestructura": 1, "cartera": 1}, "prior": {"alto": 3, "medio": 8, "bajo": 3}, "estado": {"PROPUESTA": 13, "EN_PRUEBA": 1}, "horizonte": {"días-meses": 2, "semanas": 1, "días": 2, "horas": 1, "intradía": 3, "overnight": 1, "horas-días": 4}}`

## LIT-CARRY-FX — Carry de monedas
- Clase: carry_macro · fuente: literatura · prior: alto · estado: PROPUESTA · horizonte: semanas · activos: AUDUSD, NZDUSD, USDJPY, EURJPY, GBPJPY, USDCAD, USDCHF
- Mecanismo: Las monedas de tasa alta se aprecian frente a las de tasa baja más de lo que predice la paridad de tasas (el diferencial se cobra vía swap).
- Justificación económica: Prima por riesgo de crash: el carry pierde fuerte en crisis de liquidez; quien lo provee cobra por ese riesgo.
- Cómo podría refutarse: Con swaps reales de la cuenta objetivo, la canasta de carry 2013-2026 no tiene retorno neto > 0 o su cola izquierda rompe las reglas de drawdown de la prop.
- Traducción: SQX/MT5 D1: posición en pares según el signo del swap (dato del bróker); filtro de tendencia opcional; requiere tenencia de varios días (cuenta swing).
- Fuentes: Lustig, Roussanov, Verdelhan (2011), Common Risk Factors in Currency Markets, RFS; Koijen, Moskowitz, Pedersen, Vrugt (2018), Carry, JFE

## PRAC-VOL-TARGET — Cartera con volatilidad objetivo y tendencia simple (Carver)
- Clase: cartera · fuente: practicante · prior: medio · estado: PROPUESTA · horizonte: días-meses · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD, XAGUSD, WTI, BRENT, COBRE, GAS, EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD
- Mecanismo: Escalar cada posición por la inversa de su volatilidad reciente estabiliza el riesgo y mejora el Sharpe de reglas simples.
- Justificación económica: La volatilidad es persistente y no predice proporcionalmente el retorno; ajustar el tamaño reduce las colas.
- Cómo podría refutarse: La cartera con volatilidad objetivo no mejora la esperanza del desafío de la prop (drawdown y cobro) frente al tamaño fijo.
- Traducción: Money management de SQX por volatilidad/ATR; en EdgeLab, simulación de la prop con ambos tamaños.
- Fuentes: Carver (2015), Systematic Trading; Moreira, Muir (2017), Volatility-Managed Portfolios, JF

## LIT-FIN-DE-MES — Cambio de mes en índices
- Clase: estacionalidad · fuente: literatura · prior: alto · estado: PROPUESTA · horizonte: días · activos: USA500, USATECH, USA30, DAX, Nikkei, FTSE, EuroStoxx, Russell
- Mecanismo: Los índices rinden más en los últimos días hábiles y primeros del mes que en el resto.
- Justificación económica: Flujos de caja institucionales periódicos (pagos y aportes de fin de mes) presionan precios de forma predecible.
- Cómo podría refutarse: 2013-2026 en los 8 índices: la ventana de cambio de mes no rinde más que ventanas del mismo largo elegidas al azar.
- Traducción: SQX D1: largo del día -N al +M del mes (N, M ≤ 4), salida por tiempo; sin indicadores.
- Fuentes: Ariel (1987), A Monthly Effect in Stock Returns, JFE; Etula, Rinne, Suominen, Vaittinen (2020), Dash for Cash: Monthly Market Impact of Institutional Liquidity Needs, RFS

## LIT-NOCHE — Retorno nocturno vs diurno en índices
- Clase: estacionalidad · fuente: literatura · prior: medio · estado: PROPUESTA · horizonte: overnight · activos: USA500, USATECH, USA30, Russell
- Mecanismo: Casi todo el retorno de los índices de EE.UU. ocurre fuera del horario regular (cierre → apertura).
- Justificación económica: Prima por cargar riesgo durante el cierre (sin poder salir) y presión de venta intradía.
- Cómo podría refutarse: 2013-2026: largo del cierre a la apertura no rinde más que largo de la apertura al cierre, después de swap y spread.
- Traducción: SQX H1: largo al cierre RTH, salida a la apertura; requiere tenencia overnight.
- Fuentes: Cliff, Cooper, Gulen (2008), Return Differences between Trading and Non-trading Hours

## LIT-PRE-FOMC — Deriva antes del FOMC
- Clase: evento · fuente: literatura · prior: medio · estado: PROPUESTA · horizonte: horas · activos: USA500, USATECH, USA30
- Mecanismo: El S&P sube en las 24 horas previas a los anuncios del FOMC más que en cualquier otro día.
- Justificación económica: Resolución de incertidumbre y prima de riesgo concentrada antes del anuncio.
- Cómo podría refutarse: 2016-2026 (posterior a la publicación): la ventana previa al FOMC no rinde más que el resto de los días; el efecto publicado se reportó debilitado.
- Traducción: Calendario FOMC como indicador externo en SQX (o regla de fecha); largo H1 desde 24 h antes hasta el anuncio.
- Fuentes: Lucca, Moench (2015), The Pre-FOMC Announcement Drift, JF

## EL-DELTASWEEP-SEQ — Secuencias de disparos de barrido de delta (NQ)
- Clase: microestructura · fuente: edgelab · prior: bajo · estado: EN_PRUEBA · horizonte: intradía · activos: NQ
- Mecanismo: Dos o más barridos de delta con flip en el mismo sentido en poco tiempo marcan absorción insistente y resuelven a favor del que absorbe.
- Justificación económica: Agresores atrapados repetidamente en un nivel defendido.
- Cómo podría refutarse: Forward congelado en NQ con n ≥ 30 no da R > 0; DELTASWEEP-PAT sin celdas sobre el nulo.
- Traducción: No traducible a barras de SQX (necesita ticks con bid/ask): sigue en EdgeLab; en MT5 sólo si el bróker da ticks reales.
- Fuentes: docs/research/deltasweep_20261114/MEDIDO_Y_NO_MEDIDO.md (S2 V4W AM: +0,26/+0,28 R, bajo el nulo)

## EL-CAJA-AMARILLA-MACRO — Reversión tras extensión fallida (caja amarilla) en escala macro
- Clase: reversion · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: horas-días · activos: USA500, USATECH, USA30, DAX, XAUUSD, WTI, EURUSD
- Mecanismo: Tras un impulso, la extensión a favor que vuelve a cerrar dentro de la zona de alto volumen revierte hacia el 50 % del impulso.
- Justificación económica: Agresores atrapados en la extensión fallida cierran en contra; la zona de volumen es donde estaba la liquidez del movimiento.
- Cómo podría refutarse: En H1/H4 multi-activo 2013-2026 la regla no supera a su control (la misma expansión sin la extensión fallida) ni a su nulo de proyecto.
- Traducción: SQX H1/H4: rango de N barras > k·ATR; nueva extensión que cierra de vuelta; entrada en contra, objetivo 50 % del impulso, stop en el extremo.
- Fuentes: docs/research/FACTORES_CON_VENTAJA.md: F-AMARILLA-DESPUES-VWAP-LEJOS (holdout obj 50 % +0,086 R, n 11)

## EL-VWAP-LEJOS — Precio lejos del VWAP y yendo hacia él
- Clase: reversion · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: intradía · activos: USA500, USATECH, USA30, DAX
- Mecanismo: A ≥ 1 desvío del VWAP diario y moviéndose hacia él, el precio tiende a volver al VWAP.
- Justificación económica: El VWAP es el precio de referencia de ejecución institucional; los desvíos grandes atraen órdenes de ejecución.
- Cómo podría refutarse: En H1 multi-índice, entrar hacia el VWAP desde ≥ 1 desvío no supera a entradas al azar a la misma distancia.
- Traducción: SQX H1: VWAP y sus bandas (bloque nativo), entrada hacia el VWAP, objetivo el VWAP, stop ATR.
- Fuentes: docs/research/luximb_amarilla_20261111/r2/EXPLORACION.md (todas las celdas sobre el nulo tenían VWAP lejos)

## SQX-PLANTILLA-REVERSION — Línea de base: plantilla de reversión de SQX
- Clase: reversion · fuente: sqx · prior: bajo · estado: PROPUESTA · horizonte: días · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD
- Mecanismo: Builder con la plantilla estándar de reversión (señales contrarias, órdenes límite) sobre la canasta.
- Justificación económica: Línea de base para las ideas de reversión (caja amarilla, VWAP lejos).
- Cómo podría refutarse: Si las ideas de reversión con mecanismo no le ganan, no agregan nada.
- Traducción: apply_build_template Mean-Reversal + Data con la canasta; proyecto nulo hermano.
- Fuentes: SQX internal/web/BUILDER/simpleTemplates: Mean-Reversal

## EL-NIVELES-NO-DEFIENDEN — Los niveles con actividad no defienden: continuación al romperlos
- Clase: ruptura · fuente: edgelab · prior: medio · estado: PROPUESTA · horizonte: horas-días · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD
- Mecanismo: Donde hubo mucha actividad el precio atraviesa más que en un nivel cualquiera; en escala macro, la ruptura del máximo/mínimo del día o semana previa continúa.
- Justificación económica: Stops acumulados detrás de niveles visibles; al dispararse aceleran el movimiento.
- Cómo podría refutarse: Rupturas del máximo/mínimo previo en H1/H4 no continúan más que cruces de niveles al azar a igual distancia.
- Traducción: SQX H1/H4: orden stop en el máximo/mínimo del día o semana previa; objetivo y stop en ATR.
- Fuentes: FACTORES: F-HFT-CLUSTER-GRANDE-NO-DEFIENDE (A-D), F-HFT-ZONAS-NO-SON-SOPORTE

## LIT-TSMOM — Momentum de serie de tiempo multi-activo
- Clase: tendencia · fuente: literatura · prior: alto · estado: PROPUESTA · horizonte: días-meses · activos: USA500, USATECH, USA30, DAX, USTBOND, BUND, GILT, XAUUSD, XAGUSD, WTI, BRENT, COBRE, GAS, EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD
- Mecanismo: El retorno de los últimos 1-12 meses de un activo predice el signo del próximo mes en índices, bonos, monedas y materias primas.
- Justificación económica: Subreacción inicial a la información y sobrerreacción tardía (anclaje, flujos de cobertura y de inversores lentos); prima de riesgo por crisis.
- Cómo podría refutarse: La canasta 2013-2026 (posterior a la publicación) en CFD no supera a la misma canasta con señales de signo aleatorio, después de costos y swap.
- Traducción: SQX D1/H4: largo/corto según el retorno de N días (N 20-250) o cruce de medias lentas; stop ATR largo; tamaño por volatilidad; fitness sobre la canasta.
- Fuentes: Moskowitz, Ooi, Pedersen (2012), Time Series Momentum, JFE; Hurst, Ooi, Pedersen (2017), A Century of Evidence on Trend-Following Investing, JPM

## LIT-INTRADAY-MOM — Momentum intradía de la primera media hora
- Clase: tendencia · fuente: literatura · prior: medio · estado: PROPUESTA · horizonte: intradía · activos: USA500, USATECH, USA30, Russell
- Mecanismo: El retorno de la primera media hora (con el overnight) predice el de la última media hora del mismo día.
- Justificación económica: Rebalanceo tardío de inversores informados y cobertura de opciones/ETF apalancados al cierre.
- Cómo podría refutarse: En USA500/USATECH 2013-2026 la última media hora con el signo de la primera no supera al azar después de costos.
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
