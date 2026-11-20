# ORB: variantes diseñadas con lo que EdgeLab ya midió y con la literatura (diseño, 2026-11-18)

Estado: DISEÑO — base del pre-registro (`PREREGISTRO.md`, misma carpeta). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Pedido de Nico:** «quiero que midas variantes de ORB. Diseñalas vos en base a los datos que ya hay en EdgeLab, y también con
  research en Internet».
- **Se mide con la misma maquinaria que ESCALONADAS-M1 e IB-MADONNA:** M1 de NT8, NQ/ES/YM 2006–2025, partición A5, motor único con K40,
  calibración contra ticks, R bruto y neto.

## 1. Lo que ya sabemos (EdgeLab)
- **F-ORB-EMA20-NQ-STOP-OPUESTO (NO_REPETIR).** ORB 9:30–10:00 con entrada en el retroceso a la EMA20: +0,01 a +0,07 R, sin IC90 que
  excluya el cero, sólo NQ y quizás sólo fricción (stop grande).
  - **Consecuencia:** ninguna variante elige el stop por P&L; el stop es estructural o del protocolo de la literatura, y siempre se mira
    el BRUTO.
- **OTR930 (EN_SEGUIMIENTO):** negativa en NQ M1 2012 → 2025-07 y en el Dow en los 4 tramos. La ruptura del rango de las 9:30 sin más no
  tiene ventaja en 13 años.
- **T, FtmOrb (FundedSync):** ORB de 15 min + clasificador KNN sobre operaciones sombra.
  - Es la pista fuerte en NQ, en R, desde 2012, y pasa ES/YM 2020+.
  - **Lo que la sostiene es el filtro, no el ORB:** las variantes de abajo prueban filtros con mecanismo explícito en lugar de un KNN.
- **ORB0100 (EN_CONTRA)** y **PREAPERTURA-NQ (refutada atrás):** rangos de otros horarios no transfieren.
- **Palancas:**
  - **F-STOP-GRANDE-FRENTE-A-FRICCION:** las salidas al cierre y los stops de rango completo dan fricción baja en R.
  - **F-SELECCION-ADVERSA-PASIVA:** sin entradas límite.
- **El régimen no explica casi nada; la fricción relativa sí** (VEREDICTO_M1). La lectura se hace en bruto en 20 años y en neto con la
  fricción de hoy.

## 2. Literatura (research en Internet, 2026-11-18)
- **Zarattini y Aziz (2023), «Can Day Trading Really Be Profitable?» (SSRN 4416622):** ORB de 5 min en QQQ.
  - Regla: dirección de la primera vela de 5 min, entrada a las 9:35, stop en el lado opuesto de esa vela, objetivo 10R o cierre.
  - Resultado: 33 % de CAGR 2016–2023, **sin spread ni slippage**.
- **Zarattini y Aziz (2024, SSRN 4729284):** ORB en «stocks in play». El volumen relativo es el filtro que más mejora.
- **Zarattini, Aziz y Barbon (2024), «Beat the Market» (SSRN 4824172):** ruptura del «Noise Area», una banda alrededor de la apertura
  con el movimiento medio de 14 días a esa hora, decisiones cada 30 min, VWAP como stop dinámico, salida al cierre.
  - Sharpe 1,33 en SPY 2007–2024.
  - Los parámetros se fijaron con los mismos datos: hay una réplica fuera de muestra en discusión (L. Swedroe, 2025).
- **Gao, Han, Li y Zhou (2018), «Market Intraday Momentum» (JFE):** el retorno de la primera media hora predice el de la última, en
  SPY 1993–2013.
- **Crabel (1990):** ORB con contracción previa (NR4/NR7). Los días de rango angosto anticipan expansión.
- **Holmberg, Lönnbark y Lundström (2013):** ORB en futuros de crudo con éxito mayor que el azar.

**Lo que se toma:**
- reglas cerradas de la literatura, con sus parámetros publicados (no se ajustan);
- y los filtros con mecanismo: volumen relativo, contracción, gap, momentum de la primera media hora, banda de ruido.

## 3. Variantes (cada una, una hipótesis; parámetros de la fuente o relativos, K36)
| # | Nombre | Regla | Fuente / mecanismo | Cómo podría refutarse |
|---|---|---|---|---|
| O1 | ORB 5 min (Zarattini-Aziz) | vela 9:30–9:35: compra si cierra arriba, venta si abajo (sin operación si \|C−O\| < 5 % de su rango); entrada a las 9:35; stop en el lado opuesto de la vela; objetivo 10R o cierre RTH | la regla publicada, en futuros y con costos | bruto ≤ 0 con potencia |
| O2 | ORB 15 min, ruptura por cierre | primer cierre M1 fuera del rango 9:30–9:45 entre 9:45 y 12:00 → a favor, en la vela siguiente; stop en el lado opuesto; salida al cierre RTH | la base de T sin el KNN | bruto ≤ 0 |
| O3 | ORB 30 min con contracción (Crabel) | O2 con el rango 9:30–10:00, sólo si rango/ATR20 diario ≤ su percentil 30 de las 120 sesiones previas; stop en la mitad del rango | contracción → expansión | O3 − (mismo ORB 30 sin contracción) ≤ 0 |
| O4 | ORB 15 a favor del gap | O2 sólo si la ruptura va en la dirección del gap (apertura contra cierre RTH previo) y el gap ≥ 0,1·ATR20 | gap and go: flujo de la noche que continúa | O4 − O2 en contra del gap ≤ 0 |
| O5 | ORB 15 con volumen relativo | O2 sólo si el volumen de 9:30–9:45 ≥ 1,5× su media de las 20 sesiones previas a la misma hora | el filtro clave de Zarattini-Aziz (2024): participación anormal | O5 − O2 sin volumen ≤ 0 |
| O6 | Momentum de la primera media hora (Gao et al.) | signo del retorno cierre previo → 10:00; entrada a las 15:30 en ese signo; salida al cierre RTH; stop 1× rango medio de 30 min (20 sesiones) | información lenta y rebalanceo al cierre | bruto ≤ 0 |
| O7 | Noise Area (Zarattini-Aziz-Barbon) | bandas = apertura ± media de 14 días de \|precio/apertura − 1\| a esa hora (ajustadas por el gap); en cada :00/:30 desde 10:00, compra si el cierre > banda superior y > VWAP RTH (venta al revés); stop = VWAP o la banda, la más cercana; salida al cierre RTH; una por día | la regla publicada (sin el stop dinámico: el motor usa stop fijo; se declara) | bruto ≤ 0 |
| O8 | ORB 15 fallido | primer cierre fuera del rango de 15 min y, en ≤ 15 min, cierre de vuelta adentro → fade al lado opuesto; stop extremo de afuera + 0,05·rango | la ruptura que no se sostiene atrapa a los que la compraron | bruto ≤ 0 |

## 4. Medición
**Motor y salidas:**
- La salida al cierre RTH (16:00) necesita una salida por hora por fila: la tenencia de hoy del motor es de 240 velas.
- Se agrega al motor único como columna opcional (vela de salida), con su calibración, **después** de que ESCALONADAS-M1 e IB-MADONNA
  terminen sus corridas, para no cambiar el motor bajo su calibración.

**Pruebas:** 8 absolutas + 3 contrastes (O3, O4, O5 contra su complemento) = 11. BH q 0,10 en DESC y LORD++ en REP.

**Apertura:** apertura A5 única con compuerta económica y potencia ≥ 0,8.

**Linaje:** familia nueva diseñada desde la literatura (no derivada de T, OTR930 ni ORB-EMA20).
- Esas familias miraron NQ 2012–2025 con otras reglas de apertura.
- Por eso se reporta aparte la sensibilidad en 2006–2011, años que ninguna regla de apertura de EdgeLab miró en NQ salvo el «atrás» de T
  (2008–2011, regla distinta).
