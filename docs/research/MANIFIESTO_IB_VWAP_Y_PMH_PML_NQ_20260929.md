# Pre-registro: IB→VWAP y PMH/PML en NQ (2026-09-29)

**Estado inicial (histórico):** preregistro elaborado; no se habían inspeccionado resultados ni corrido estrategias. **Repositorio:** Nicodelcampo/EdgeLab, rama `foundation/f0b-compatibility-probe`. **Datos:** dataset privado Kaggle `nicolasbuttaro/edgelab-nq-nt8-2026q3-l2ctx`, versión 1; desarrollo Q3-2026 solamente. No es confirmación y no toca sesiones desde la apertura CME del 1-oct-2026.

## Research y selección de variantes

Las fuentes públicas describen reglas de práctica, no evidencia independiente de rentabilidad. El Initial Balance se presenta como la primera hora de RTH estadounidense (09:30–10:30 ET); la variante IB→VWAP espera una ruptura y retroceso al VWAP para ubicar la entrada, en vez de perseguir el quiebre.[^1] Para PMH/PML hay más de una ventana posible de premarket; se fija 04:00–09:30 ET para impedir redefinir niveles ex post. Se elige sweep-and-reclaim después de la apertura inicial de 15 minutos: ruptura del extremo, cierre de 5 min de vuelta al rango y sostenimiento antes de entrar.[^2] El breakout-retest no es primario; no se escogerá variante usando sus resultados.

## Estrategia A — IB→VWAP, continuación

- Sesión RTH NQ en America/New_York. IB = máximo/mínimo de 09:30–10:30 ET. VWAP = acumulado de precio negociado × volumen / volumen desde 09:30 ET, reiniciado cada sesión.
- Señal: después de 10:30, primer cierre de barra de 5 min fuera del IB; después, primera barra de 5 min que toca VWAP y cierra de nuevo del lado de la ruptura y fuera del IB.
- Entrada market al primer tick disponible después del cierre confirmatorio. Stop a 1 tick más allá del extremo adverso de esa barra; objetivo fijo 2R; salida temporal 15:55 ET.
- Máximo una entrada por estrategia/sesión. Si ambas direcciones califican en la misma barra, no operar.

## Estrategia B — PMH/PML, sweep-and-reclaim

- Premarket fijo 04:00–09:30 ET; ORB 09:30–09:45 ET. No hay señales antes de 09:45.
- Señal larga: después del ORB, cotiza ≥1 tick bajo PML, luego una barra de 5 min cierra sobre PML y la barra siguiente también cierra sobre PML. Corto simétrico tras cotizar ≥1 tick sobre PMH y dos cierres bajo PMH.
- Entrada market al primer tick tras la segunda confirmación. Stop 1 tick más allá del extremo post-sweep; objetivo punto medio del rango premarket; salida temporal 15:55 ET.
- Máximo una entrada por estrategia/sesión. Si PMH y PML califican en la misma barra, no operar.

## Universo, métricas y análisis

- NQ únicamente; incluir sesiones RTH completas disponibles en los catálogos de la versión 1. Registrar contratos, fechas, sesiones excluidas y motivo antes de calcular resultados. Las etiquetas L2 no son predictor ni filtro de estas estrategias.
- Primaria: esperanza media por operación en R después de 2 ticks de deslizamiento total (1 por lado). Comisión excluida hasta verificar tarifa aplicable: publicar esperanza bruta, distribución de R, n de operaciones/sesiones, drawdown por sesión y comisión de equilibrio; sin comisión no declarar rentabilidad neta.
- Resolver TP/SL con secuencia tick a tick; si el orden intrabar no puede determinarse, asumir stop primero. Sin optimización de parámetros, sizing o piramidación.
- Dos pruebas primarias; bootstrap conjunto por sesión con remuestras comunes y corrección máximo-T, IC bilateral 95 %. Menos de 30 trades o menos de 20 sesiones distintas: inconcluso. Sensibilidad descriptiva a 0/2/4 ticks de coste total, nunca sustituyendo la primaria.
- A3 exploratorio; no usar datos desde 1-oct-2026 para selección. Una confirmación futura requiere hipótesis congelada y autorización separada.

## Puertas de ejecución

1. Confirmar hashes de datos/manifiestos, sesiones y SHA del código antes de abrir outcomes.
2. Validar runner en fixtures sintéticos de zona horaria, fronteras de sesión, señal, secuencia de llenado, stops/targets y costes.
3. Kaggle informó dataset versión 1 `Ready` (638,328,048 bytes) y mostró archivos de ticks NQ 09-26/12-26, catálogos y etiquetas L2. Sin embargo, el conector actual negó `kernels.get` al consultar `nicolasbuttaro/edgelab-nq-cruce25-clima-20260929`; no puedo editar ni ejecutar el notebook con el permiso actual. Ninguna corrida se lanzó.
4. El análisis pendiente NQ-CRUCE25-CLIMA de `Entrada 066` tampoco se debe lanzar aún: `Entrada 067 — Auditor` marca como bloqueantes el control del mismo clima y el bootstrap max-T conjunto, exige versionar/probar ART→UTC y señala que deben contarse las 40 sesiones aunque no tengan etiquetas válidas. También pide revisar el tercil de volatilidad y fijar soporte/potencia. Reparar ese análisis en forma separada.
5. Tras habilitar acceso a kernels privados/ejecución o conectar el Worker autorizado, ejecutar sólo la versión congelada; guardar logs y artefactos. Resultados: todavía desconocidos.

## Fuentes públicas

[^1]: Kathy Lien, “How to Trade the Initial Balance Like a Pro”, https://www.investing.com/analysis/how-to-trade-the-initial-balance-like-a-pro-200678607 — regla de IB de 60 minutos, ruptura y retroceso a VWAP/FVG; no valida rentabilidad independiente.
[^2]: Kathy Lien, “Trading Nasdaq 100 Premarket Levels With Sweeps and Reclaim”, https://www.investing.com/analysis/trading-nasdaq-100-premarket-levels-with-sweeps-and-reclaim-200686034 — ejemplo de rango 04:00–09:30, ORB 15 min, cierre de 5 min de vuelta al rango y objetivo en punto medio; no valida rentabilidad independiente.


## Actualización de ejecución — 29/09/2026

Nico autorizó «Retoma y correas». Ambas corridas se completaron en sandbox, con el dataset privado Kaggle v1 descargado. Código/precisiones/fixtures/preflight registrados antes de outcomes en `01dd9a5c6a83157a667b74638dd303af0ffd4f49`. Acta: `RESULTADO_IB_VWAP_PMH_PML_NQ_20260929.md`. IB: 5 trades, inconclusa; PM: 36 trades, punto negativo. Sin inferencia conjunta por gate previo de muestra, sin comisión ni fills reales, holdout intacto. Las puertas de permisos/L2 anteriores se conservan como historia, no como estado actual. No se alteran las reglas originales por estos resultados.
