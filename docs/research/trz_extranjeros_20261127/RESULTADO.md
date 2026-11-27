# TRZ-EXTRANJEROS: T y R de la cartera no se transfieren a Europa (resultado, 2026-11-27)

Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md), con adenda previa a la lectura (3 pruebas,
`FUNDEDSYNC_TRANSFER`). Motor: el arnés C# de la cartera NT8 con las configuraciones de producción. Herramienta:
`python tools/trz_extranjeros.py bajar|preparar|calibrar|correr` (`CALIBRACION.json`, `CALIBRACION_DIAGNOSTICO.json`, `RESULTADO.json`,
`OPS.csv.gz`).

## 1. Compuerta de calibración: lo que se pudo medir y lo que no
| Paso | Resultado |
|---|---|
| Nasdaq CFD de HistData contra NQ futuros, con la hora «EST fijo» de la documentación | **Falla** en T, R y Z |
| Diagnóstico: NQ futuros por el mismo circuito (volumen 1, sin noticias) | Calibran los tres (correlación 0,89–0,99): el problema no son las transformaciones |
| Correlación minuto a minuto CFD contra futuros | La hora de HistData es **Nueva York con horario de verano** y sello = apertura (0,97 en invierno; 0,91–0,95 en verano corrido 1 h) |
| Con la hora corregida | **T calibra** (0,122 contra 0,133; correlación 0,75). **R calibra** (0,176 contra 0,162; 0,95). **Z no calibra** (0,016 contra 0,102): no se lee |
| Verificación de apertura por índice (sin retornos) | DAX, FTSE, CAC y EuroStoxx coherentes. **Nikkei y ASX no:** quedan excluidos |

## 2. Resultado (DAX, FTSE, CAC y EuroStoxx; 2010/11 → 2026-09; costos de NQ en escala NQ)
| Serie | Meses | Sharpe anual | t | Meses + | Veredicto |
|---|---|---|---|---|---|
| **Canasta T+R (primaria)** | 190 | −1,15 | **−4,57** | 39 % | **EN_CONTRA** |
| T (3 índices; EuroStoxx sin operaciones de T) | 177 | −1,13 | −4,33 | 35 % | EN_CONTRA |
| R (4 índices) | 190 | −0,48 | −1,92 | 43 % | EN_CONTRA |
| Canasta con costos ×2 | 190 | −2,30 | −9,13 | — | — |
| Antes de 2020 | 109 | −1,69 | −5,09 | — | — |
| Desde 2020 | 81 | −0,50 | −1,31 | — | — |

Por índice:
- T: DAX t −2,67, FTSE −4,64, CAC −2,18.
- R: DAX −1,79, FTSE −1,53, CAC −0,12, EuroStoxx −1,10.

**Auditoría de integridad:**
- **No es el costo.**
  - R bruto por operación de T: CAC +0,03, DAX +0,03, FTSE −0,01, contra una fricción de 0,08–0,09 R.
  - En las operaciones sin corte de datos, el bruto de T es −0,05, −0,01 y −0,06.
  - En NQ, T gana +0,13 R neto por operación.
- **No son los datos.** Los CFD extranjeros cortan el 12–16 % de las operaciones de T por huecos en el contado (NQ futuros: 0,4 %;
  Nasdaq CFD: 3,8 %). Esas operaciones salen positivas: sacarlas empeora el resultado.
- R da bruto ≈ 0 en los cuatro índices.

## 3. Lectura
- **T y R no son mecanismos generales de apertura:** en Europa, con las reglas congeladas, no tienen ventaja ni bruta. Coincide con
  `VEREDICTO_M1_20261117.md`, que ya encontró R AtrPhase sólo en NQ y el «salto desde 2020» sólo en NQ, ES y YM.
- **Baja la confianza en la intradía de la cartera como ventaja estructural.** Sigue en pie que en NQ funciona en 2020–2026, pero esa es la
  muestra del vendedor. Este resultado vuelve más plausible que sea un ajuste a NQ en ese período que un mecanismo.
- **La confirmación sigue siendo el forward de T+R (desde 2026-11-14),** ahora con una expectativa previa más baja.
- **Z quedó sin medir:** no calibra con datos de CFD. Necesita M1 de futuros reales de esos índices (FDAX, FESX), una fuente que hoy
  no está.
- **Salvedades:** son CFD, no futuros; el costo es el de NQ (estimado, K34); la escala y la hora son transformaciones declaradas y
  calibradas contra el Nasdaq.

Diagnóstico de grilla: sin grilla. Configuraciones de producción del arnés (`T_stop100_BE15R_calFalse`, `R_osc30_end660_ATR50`); las
únicas decisiones son las transformaciones de datos, declaradas y calibradas antes de leer.
Episodios: T pierde en los tres índices en las dos épocas (antes de 2020, t −5,09; desde 2020, t −1,31); R ≈ 0 bruto en los cuatro.

Aporte al referente: con mercados que ni el vendedor ni EdgeLab habían mirado, la intradía T+R no se transfiere. Baja la confianza previa
de la canasta en forward y separa lo que es propio de NQ de lo que sería un mecanismo general.
