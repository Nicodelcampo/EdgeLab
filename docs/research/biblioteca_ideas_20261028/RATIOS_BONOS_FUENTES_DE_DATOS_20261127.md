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
