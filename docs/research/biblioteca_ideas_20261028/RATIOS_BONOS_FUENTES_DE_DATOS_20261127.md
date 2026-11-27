# Ratios de bonos argentinos: de dónde sacar los datos y los costos (relevamiento web, 2026-11-27)

Estado: REFERENCIA — relevamiento de fuentes, sin descargar datos ni medir. Idea de origen: `RATIOS_BONOS_LUCIONI_20261126_RESUMEN.md`.

La única prueba de acceso que se intentó (instalar y correr PyOBD) no se hizo: el permiso fue denegado. Todo lo que sigue sale de la
documentación pública de cada fuente.

## 1. Precios (lo crítico es el intradía histórico)

| Fuente | Qué da | Historia intradía | Acceso | Uso propuesto |
|---|---|---|---|---|
| **Open BYMA Data** vía PyOBD (`pip install PyOBD`, GPLv3, github.com/franco-lamas/PyOBD) | Diario OHLCV; intradía de **1 minuto** (`get_intraday_history(symbol, from_date, to_date)`); paneles de títulos públicos | **Sin verificar**: la firma acepta fechas, pero no está documentado cuánto guarda | Gratis, sin cuenta (datos con demora) | Primera prueba: cuánto 1 min de GD30/AL30 devuelve hacia atrás |
| **API IOL** (developers.iolinversiones.com) | Series históricas por título (`seriehistorica`: diarias); tiempo real por WebSocket con libro de órdenes | Sólo grabando hacia adelante | Gratis con cuenta IOL | Grabar puntas y operaciones en vivo; diario histórico |
| **Primary / Matba Rofex API** (pyRofex; apihub.primary.com.ar) | Market data REST/WebSocket/FIX; `get_trade_history` (operaciones) | reMarkets (demo) gratis; LIVE por un broker o por mpi@primary.com.ar; cobertura de BYMA en LIVE sin verificar | Cuenta del broker | Grabar en vivo con el broker que opere |
| **pyhomebroker** (crapher; discontinuado) | Diario histórico; intradía **sólo del día en curso**; libro nivel 2 | No | Cuenta en un broker soportado (Veta Capital id 284, Cocos 265, etc.) | Grabador diario si no hay otra opción |
| **BYMA Market Data** (byma.com.ar, APIs Delay20 / End of Day / Snapshot, FIX, «Data histórica») | Oficial, con demora o en tiempo real | Producto pago de datos históricos: hay que consultar (marketdata@byma.com.ar) | Las APIs son sólo para agentes miembro; los datos históricos son un producto comercial | La única vía a intradía histórico profundo y fiel |
| Planillas de terceros (la de Gus Lucioni / «Juan», Abbaco–Mercap) | Ratios ya calculados, velas de 5 s y 30 min | Desconocida | Pago | Sólo para comparar; no como fuente auditable |

**Conclusión de datos:**
- Diario histórico hay gratis: PyOBD o IOL.
- Intradía histórico profundo, gratis, no se encontró. Las opciones son:
  1. verificar cuánto guarda el 1 min de Open BYMA Data;
  2. comprarlo a BYMA;
  3. grabarlo hacia adelante con IOL o con el broker (puntas incluidas), que además da el spread real.

## 2. Datos de los bonos (flujos y especificación)
- **Flujos de fondos:** el cronograma oficial (prospectos del Ministerio de Economía). Fuentes de consulta: acuantoesta.com.ar/simulador
  (ticker, ley, cupón, valor residual, TIR) y screenermatic.com, con TIR, duration y flujo.
  - Los pares del video comparten flujo: AL30/GD30 tienen 13 cuotas desde el 09/07/2024; AL35/GD35, AE38/GD38 y AL41/GD41 tienen la
    misma estructura step-up.
  - AE38 y GD38 son ley local y ley NY con indenture 2005.
- **Especies por moneda:** pesos (AL30), MEP (AL30D) y cable (AL30C). El video opera en pesos porque es lo más líquido.
- **Liquidez:** el monto operado está en los paneles de IOL o de PuenteNet. Al 2026-11, AL30 es la especie de mayor volumen.

## 3. Costos
| Componente | Valor | Fuente |
|---|---|---|
| Derecho de mercado BYMA, títulos públicos contado | **0,01 %** por operación | BYMA, «Derechos de Mercado sobre Operaciones», vigente desde el 2026-08-14 |
| Préstamo de valores para venta en corto | **0,02 %** sobre el monto futuro, a cargo del tomador | ídem |
| Caución | 0,045 % prorrata | ídem |
| Comisión del broker con abono fijo (VetaFLAT) | 0 % por operación; abono de $85.000 (PRO), $160.000 (ADVANCE) o $285.000 (ELITE) por mes + IVA | vetacap.com.ar/personas |
| Cupo de descubierto y bonos de aire (VetaFLAT) | 175 % / 250 % / 400 % de la tenencia valorizada (tope $100 M / $200 M / $1.000 M) | ídem |
| Spread entre compra y venta | **A medir** con las puntas; el video da 0,3 % en GD29 como ejemplo de lo inoperable | Grabación propia |

- El abono no bonifica los derechos de mercado ni los impuestos. Se amortiza con volumen.
- En EdgeLab entra como costo fijo por mes: se compara contra el resultado bruto mensual, no por operación.

## 4. Qué hace falta para la primera medición (sin P&L)
1. Diario 2024–2026 de AL30, GD30, AL35, GD35, AE38, GD38, AL41 y GD41 (PyOBD o IOL). Con eso se mide si el ratio diario vuelve a la
   media y en cuánto tiempo, por par y por régimen.
2. El 1 min de Open BYMA Data, si guarda historia. Si no, grabar hacia adelante.
3. Puntas reales para el spread: grabación con IOL o con el broker.

Decisiones de Nico:
- abrir el mercado y las fuentes;
- permitir instalar y correr PyOBD o la API de IOL en el entorno;
- usar o no una cuenta propia, que la API de IOL exige.

Aporte al referente: deja identificadas las fuentes y los costos medidos (0,01 % de derecho, 0,02 % de préstamo, abono fijo). Muestra que
el cuello de botella es el intradía histórico, no el análisis.

## 5. Datasets encontrados (segunda búsqueda, 2026-11-27, verificados desde el entorno)
| Fuente | Qué trae | Historia | Acceso | Verificado |
|---|---|---|---|---|
| **data912.com** `/historical/bonds/{ticker}` | Diario OHLCV con volumen nocional (`v`), retorno diario y sigma de AL30, GD30, AL35, GD35, AE38, GD38, AL41, GD41 y las especies D/C | **Desde 2021-09-16** (≈ 1.265 ruedas) hasta el día anterior | Gratis, sin cuenta, 120 pedidos/min | Sí: 8/8 tickers responden (último dato 2026-11-26) |
| **data912.com** `/live/arg_bonds` | Foto en vivo con **puntas**: cantidad y precio de compra y venta, volumen, último | Sólo el momento (no hay historia) | Gratis | Sí: AL30 compra 82.130 / venta 82.200 (spread ≈ 0,09 %); GD30 85.200 / 85.390 (≈ 0,22 %) |
| Kaggle `juanfe/bonos-dolar-mep` | Cierres diarios de AL29, AL30, AL35, GD29, GD30, GD35 y GD38 en $ y D | Discontinuado en 2022 | Gratis | Sí, por la API de Kaggle (0,2 MB) |
| Kaggle, GitHub, Hugging Face | **Intradía histórico de bonos argentinos: no se encontró ninguno** | — | — | Búsquedas «argentina bonds», «AL30», «GD30», «bonos argentinos», «merval intraday», «byma» |

**Qué cambia:**
1. **Se puede medir ya, sin cuenta ni broker, la primera etapa:** si el ratio diario de cada par vuelve a la media, en cuánto tiempo y por
   régimen, de 2021-09 a hoy, con los 8 bonos de data912. Es target-free y requiere pre-registro.
2. **Para el intradía y el spread real, la opción concreta es grabar hacia adelante** con `/live/arg_bonds` (puntas cada pocos
   segundos, dentro del límite de 120 pedidos/min) o con la API de IOL. Ninguna fuente gratuita tiene intradía histórico.
3. data912 es un servicio de terceros sin garantía. Antes de usarlo para algo más que exploración, conviene cruzar algunos cierres
   contra BYMA o IOL.

## 6. Intradía de AL29/AL30 para la versión pasiva (tercera búsqueda, 2026-11-27)
Motivo: `OPERACIONES_AMIGO_AL29_AL30_MATRIZ_20261127.md`. Para medir la regla hacen falta **operaciones con hora** (y, si se puede, puntas)
de AL29 y AL30, en 24hs y CI. Nico consigue y descarga los datos; esta lista es para elegir de dónde.

| Fuente | Qué trae | Historia | Acceso y costo | Estado |
|---|---|---|---|---|
| **API de Primary del broker** (`api.veta.xoms.com.ar`; pyRofex con entorno LIVE apuntado a ese host) | `getTrades` (operaciones con hora, precio y cantidad), market data con puntas, WebSocket | Con `dateFrom`/`dateTo`; **sin verificar si cubre BYMA** (`MERV - XMEV - AL29 - 24hs`, `external=true`) ni cuánto guarda | El usuario y la contraseña de Matriz suelen servir para la API (lo dice `chuchocoder/pyrofex-to-excel`); si no, se la pide al broker | **La primera prueba que conviene hacer**: un día viejo de AL30 |
| **Historial de órdenes del amigo** (Matriz: órdenes y operaciones) | Sus órdenes, ejecutadas y no, con hora | Lo que guarde su cuenta | Su consentimiento | La mejor evidencia de ejecución real |
| **PPI (Portfolio Personal) API** (`itatppi.github.io/ppi-official-api-docs`) | `MarketData/Intraday`: operaciones (fecha, precio, volumen); `MarketData/Book`: profundidad; `MarketData/Search`: diario con fechas | El intradía no tiene parámetro de fecha: **probablemente sólo el día** | Gratis con cuenta PPI (claves en Gestiones → Gestión de servicio API) | Sirve para grabar operaciones y libro cada día |
| **Grabación propia** (data912 `/live/arg_bonds`, IOL WebSocket, Primary WebSocket o PPI) | Puntas (y operaciones con Primary/PPI/IOL) | Desde que se empieza | Gratis | Siempre posible; tarda meses |
| **BYMA APIs** (`byma.com.ar/productos/productos-de-datos/market-data/apis`) | Snapshot (tiempo real) USD 120/mes retail, Delay 20 min USD 60, EOD USD 30 | **No listan un producto de intradía histórico**; hay que consultarlo | marketdata@byma.com.ar | Preguntar por operaciones históricas de títulos públicos |
| **Open BYMA Data** (PyOBD, openbymadata) | 1 minuto con `resolution=1` | `carvalab/openbymadata`: «el intradía gratis devuelve sólo datos con demora, unas pocas barras por día» | Gratis | **Descartado** para esto |
| **TradingView** (`BCBA:AL29`, `BCBA:AL30`, `.CI`) | Velas | Profundidad según plan; datos de BYMA con demora salvo suscripción | Pago | Sólo velas, sin puntas ni operaciones: no alcanza para fills pasivos |
| **LSEG Tick History / Bloomberg** | Ticks históricos de muchas bolsas | Años | Muy caro o institucional (a veces por universidad) | Cobertura de BYMA sin verificar |
| data912 `/historical` | Sólo diario | 2021-09 → | Gratis | Ya en uso |

**Formato que necesita la medición:**
- Bonos: AL29 y AL30 en pesos, 24hs y CI. Si se puede, también GD29/GD30 y AL30D para controles.
- Operaciones: hora con segundos (y huso), precio, cantidad y, si viene, lado.
- Puntas (si hay): hora, compra, venta y sus cantidades.
- Período: lo más largo posible. Con menos de ≈ 3 meses no hay potencia para decidir.
- Fechas de pago de amortización y cupón de AL29 y AL30, para ajustar el ratio.

Notas:
- Desde la liquidación T+1, 48hs no cotiza: los símbolos son 24HS o CI.
- Las credenciales de API nunca van al chat ni al repo. Si la descarga corre en este entorno, se cargan con el formulario seguro;
  si corre en la máquina de Nico, quedan ahí.

## 7. La planilla pública de Martín Masella («Arbitraje Ratios», enviada por Nico el 2026-11-27)
- **Qué es:** la planilla del taller de Masella y Lucioni. Los precios en vivo salen de la API de Primary vía Veta (las credenciales son
  de Masella); los diarios, de IOL.
- **Qué guarda:** **sólo la rueda en curso.** Al día siguiente la hoja se reescribe.
  - «Intraday»: GD30/AL30 en 24hs **cada 10 segundos** (10:30 → 17:00), con el último precio y los dos ratios operables con puntas:
    GD>AL = bid GD30 / ask AL30 − 1 (rotar de GD a AL) y AL>GD = ask GD30 / bid AL30 − 1 (volver).
  - «D-C»: lo mismo para AL30D/AL30C.
  - «MD»: foto de puntas con cantidades de AL29, AL30, GD29 y GD30 (pesos, MEP y cable; CI y 24hs). **AL29 no tiene serie intradía.**
  - Pestañas por par (GD30/AL30, GD35/AL35, GD38/AE38, GD41/AL41, AE38/GD41) con sus 100 cierres y bandas de Bollinger (21 ruedas,
    1,5 desvíos), y «DataIOL», con el diario de GD30 y AL30 desde 2024-08.
- **Cómo se usa:** `python tools/bonos_masella_grabar.py grabar` cada día hábil entre las 17:05 y las 10:30 del día siguiente (no pisa
  una rueda ya grabada); `resumen` lista lo grabado. Destino: `data/bonos_ar/intradia_masella/<fecha>/`, gitignorado, con sha256.
  Lee cada hoja como CSV público (`gviz/tq?tqx=out:csv`); no necesita cuenta ni API.
- **Primera rueda grabada: 2026-11-27** (2.339 fotos). Descriptivo de un solo día, no es una prueba:
  - el ratio se movió con un desvío de 0,18 pp (rango 2,56–4,80 %, con los extremos en la apertura);
  - ida y vuelta con puntas costó una mediana de 0,10 pp (p10 0,05; p90 0,19).
  - La foto de spreads de BONOS-ROTACION se tomó después del cierre y daba 0,31 pp para el mismo par: durante la rueda las puntas son
    más finas. Esto no cambia ese veredicto (en REP el bruto era ≈ 0), pero la versión intradía necesita el costo de la rueda.
- **Para que alcance:** hacen falta ≈ 3 meses de ruedas grabadas para medir la regla intradía de la charla en GD30/AL30. Para AL29/AL30
  (las operaciones del amigo) sigue faltando intradía.

## 8. Intradía histórico sin esperar a grabar (cuarta búsqueda, 2026-11-27)
| Fuente | Qué da | Cuánto hacia atrás | Costo | Limitación |
|---|---|---|---|---|
| **TradingView, plan pago, «Exportar datos del gráfico»** (`BCBA:GD30`, `BCBA:AL30`, `BCBA:AL29` y sus `.CI`) | Velas OHLCV de 1 a 30 minutos | Barras por plan: 10.000 (Essential/Plus), 20.000 (Premium), 40.000 (Ultimate). Con ≈ 390 velas de 1 minuto por rueda, 20.000 ≈ 2,5 meses de 1 minuto, ≈ 1 año de 5 minutos o varios años de 30 minutos. La página de precios dice además «datos históricos por minuto»: 180 días (Essential), 365 (Plus), todo (Premium) | Premium ≈ USD 60 por un mes alcanza para exportar | Sólo último precio, sin puntas: el costo se estima aparte (abajo). Hay que confirmar en el gráfico que BYMA tenga velas intradía en el plan |
| **Pedírselo a Martín Masella** | Su planilla graba GD30/AL30 cada 10 s con puntas, por la API de Primary vía Veta, desde 2021 (la planilla se creó el 2021-04-02); puede tener historia guardada | Desconocido | Contacto directo (pide un «cafecito») | Depende de que lo haya guardado |
| **BYMA, Market Data** (marketdata@byma.com.ar) | Oficial | Producto histórico no publicado: preguntar por operaciones o velas intradía de títulos públicos | Desconocido | — |
| **La planilla «Juan» / Abbaco–Mercap** que muestra la charla | Ratios en velas de 5 s a 30 min | Desconocida | Pago | Sólo para comparar |
| `tvDatafeed` (no oficial, hasta 5.000 velas sin cuenta) | Igual que TradingView | 5.000 velas | Gratis | Contra los términos de TradingView: no se usa |

**Plan propuesto:**
- Señal con las velas exportadas de TradingView. Es la técnica de la charla: ratio contra su media, en velas de 5 a 30 minutos.
- Costo de cada rotación con las puntas grabadas de la planilla de Masella (§7). Es un costo estimado y declarado (K34), por franja horaria;
  una regla que sólo gane con ese costo en su p10 no pasa.
- Es la única combinación que mide hacia atrás sin esperar meses. La grabación sigue, para calibrar el costo y para el forward.
