# ORB USATECH CFD — tres cajas y filtros

Estado: PRE-REGISTRO EXPLORATORIO — fijado antes de medir CFD
Fecha: 2026-11-08
Familia / módulo: ORB-NQ-FILTROS / USATECH

Nico pidió correr las tres variantes en CFD y señaló que hay varios años de datos. La evaluación se realiza separada del futuro: el CFD no es NQ, no se apilan ni se presentan como muestra homogénea y los resultados no son una réplica independiente ni habilitan una promoción.

## Universo y protección

- Fuente privada `nicolasbuttaro/edgelab-dukascopy-nq-usatech` v2, `USATECHIDXUSD_ticks.parquet`, SHA-256 `7037b34d431d1fe61d2a866a8305688d21c646bbb017b38559aef8d0dd332011`. Cotizaciones Dukascopy bid/ask; no hay last de mercado ni volumen negociado. Uso privado, sin redistribución. El recorte y SHA figuran en `docs/research/auditoria_kaggle_20261024/recorte_spot/recorte_edgelab-dukascopy-nq-usatech.json`.
- Ventana de trabajo 2023-01-03–2026-03-31, inclusiva: comienza donde existe el calendario de noticias usado y mantiene el extremo final de la medición NQ. La familia y otros estudios ya examinaron datos CFD de varios tramos: no llamarlos OOS independiente. El holdout desde la apertura CME de la sesión 2026-10-01 (2026-09-30 22:00 UTC) sigue sellado. El lector aborta antes de deserializar un row group solapado con el holdout y verifica el orden temporal.
- Sesión de referencia: días normales de NYSE 09:30–16:00 ET; feriados y cierres tempranos excluidos a priori. Archivo congelado `patches_for_review/orb_cfd_20261108/sesiones_xnys.json`, SHA-256 `95b27e2c8b63da4d6053496bc99e322302e01ba8ca188d7c4ff8c27565808f22`, generado por `exchange_calendars 4.13.2` XNYS, con control de fechas conocidas incluido. Referencias de NYSE: https://www.nyse.com/publicdocs/ICE_NYSE_2023_Yearly_Trading_Calendar.pdf y https://www.nyse.com/markets/hours-calendars ; cierre extraordinario de 2025-01-09: https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx. El calendario es referencia del mercado accionario, no evidencia certificada del horario ni de la ejecución de Dukascopy.
- Calidad retrospectiva: requiere todas las 385 barras M1 desde las 09:30 hasta las 15:55 ET y al menos una cotización entre 15:55 y 16:00; no prueba captura íntegra de ticks y no es filtro operable al inicio de sesión. Se incluyen 30 minutos antes de apertura para ATR; falta de barras o gaps excluye ATR cuando corresponda.

## Reglas y costos

Se conserva `senales_orb.py` de la corrida NQ: cajas de 5, 15 y 30 minutos, primera ruptura por cierre M1 posterior, una señal por duración y día, ambos lados, stop al extremo contrario, sin TP y salida al primer tick desde 15:55 ET antes de 16:00. OHLC y disparo de stop usan el mid bid/ask de CFD redondeado a 0,01 puntos, como `edgelab/research/fuentes_ticks.py`; en ausencia de last no se afirma reproducción exacta de un stop real. Entrada al primer tick estrictamente posterior a señal; largo compra ask y vende bid, corto compra ask al salir y vende bid al entrar. Sin doble cobro de spread.

Para una referencia de sensibilidad se suma 0,25 puntos de slippage por pata en escenario base y 0,50 adverso, más 0,288 puntos por viaje (5,76 USD / 20 USD por punto NQ). **Son supuestos inspirados en NQ, no tarifas ni slippage verificados de una cuenta CFD**, y no son el costo canónico de USATECH. R neto es P&L modelado / distancia de fill inicial al stop; señales que dejan el stop al lado inválido no se operan. Esta es una prueba del CFD con supuestos hipotéticos, no evidencia de fills operables ni sustituto de fricción CFD medida.

Noticias USD tier1 y tier2 del CSV existente, ventanas cerradas ±1 minuto: veto preventivo desde señal hasta 15:55 si hay intersección, y abortar si una salida retrasada cruza una ventana listada. CSV `8a152d092314c42498638cbee2144cef0851b013a8536ed0b661c3fdb8381234` es parcial y retrospectivo; no demuestra ausencia de todos los anuncios de alto impacto o cumplimiento total de la regla de noticias. La autorización previa de Nico es para medición exploratoria con esa limitación declarada.

## Filtros y estadística

Los mismos 360 cruces nominales de 3 duraciones × 6 días (incluye cualquiera) × 5 ventanas horarias (incluye cualquiera) × 4 ATR (incluye cualquiera). Día y hora son los de la señal ET; ATR14 simple M1 y terciles combinados sobre las señales elegibles de este universo, congelados antes de ejecutar fills. Estos cortes son retrospectivos y específicos de CFD, no trasplantados del futuro.

Un único canal conjunto total: mínimo 30 operaciones, maxT una etapa con signos compartidos por sesión, 10.000 réplicas, semilla 20261108 y alfa 0,05; no se afirma control sobre búsquedas históricas ni se ha probado la simetría. Años por separado sólo descriptivos, sin escoger ex post un subperíodo; 2026 es parcial. El conteo de celdas y múltiples búsquedas se informa y no habilita promoción sin evaluación y controles humanos.

## Implementación y controles antes de ejecutar

- Runner `patches_for_review/orb_cfd_20261108/medir_cfd.py` SHA-256 `8f36eb653db3852c02b866bb299a05ba8bf7efe99135031943ff0ca3a6de4b83`.
- Señales `patches_for_review/orb_nq_20261108/senales_orb.py` SHA-256 `d491b46ace2067e13399b443d5093cb072992b2579f3c9f9637e58dd212b56e6`; función maxT y veto `medir_exploratorio.py` SHA-256 `a43eb943fdd8ad3f05e12ac1a272206909d32b6b4b31202a0e59474e2fe88b7c`.
- 28 tests sintéticos aprobados para señales y conductor: partición de grupos, calendario, ATR, barra ausente, bid/ask, riesgo desde el fill, timestamps repetidos, stop de ambos lados y veto de noticia. Incluye pipeline sintético integral y guarda de holdout. No es auditoría independiente del motor integrado ni prueba de calidad del proveedor. Runtime falla cerrado ante discrepancia de hash, grupo solapado con holdout, cotización inválida o ausencia de salida.
- Guardar en Kaggle privado únicamente resúmenes agregados y cortes E0. No exportar ticks ni operaciones individuales. El código es exploratorio; cualquier resultado debe acompañarse de las limitaciones anteriores y no reemplaza la validación sobre el futuro.
