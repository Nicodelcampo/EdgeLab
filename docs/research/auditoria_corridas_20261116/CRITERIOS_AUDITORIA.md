# Auditoría de corridas: criterios, método y hallazgos (2026-11-16)

Estado: VIGENTE — registro vivo. Pedido de Nico: «definí criterios para buscar errores en las corridas anteriores y descartar sesgos o
resultados inválidos». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Complementa
`ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` (errores de diseño) con errores de **ejecución y datos** encontrados en resultados ya publicados.

## 1. Clases de error (qué se busca)
| # | Clase | Ejemplos reales | Cómo se detecta |
|---|---|---|---|
| A1 | **Reloj y zona horaria** | CSV en UTC leídos como hora del servidor (Russell, DAX…; 2026-11-16); índice en µs convertido como ns (fechas de 1970); día UTC como sesión | Perfil de rango/volumen por minuto contra la apertura conocida de cada mercado, invierno y verano; grep de `astype("int64") // 10**9`; test de sesión CME |
| A2 | **Fuga de holdout** | Corte en 2026-10-01 00:00 UTC (la sesión abre 22:00 UTC del 30-sep) en QuantLab y LuxImb | grep de literales de fecha; toda frontera desde `edgelab/holdout.py` (test) |
| A3 | **Campos con significado engañoso** | `stop_price` de FundedSync = stop ACTIVO al salir (no el inicial); `sequence` no es secuencia del exchange; `ts_local_ns` duplicado | Leer el motor donde se escribe el campo; correlación del campo con el resultado (un «riesgo» que achica a las ganadoras es futuro) |
| A4 | **Llenados optimistas** | Stop llenado a su precio con gap en contra; vela de entrada sin revisar el stop; objetivo antes que stop en la misma vela | Revisar el simulador: orden stop/objetivo, apertura con gap, vela de entrada |
| A5 | **Futuro en indicadores** | Vela de la señal incluida en su propio filtro; ATR o percentil con el día actual | Test de causalidad por prefijo para todo código nuevo |
| A6 | **Costos** | R ya neto dividido otra vez por el riesgo; fricción de otro instrumento; comisión mal elegida | Fricción en R por operación publicada; `costos.py` único |
| A7 | **Escalas y unidades** | Puntos vs R vs USD; USD por punto del micro; preset de otro instrumento | Revisar conversiones en el informe; unidades explícitas en cada tabla |
| A8 | **Cobertura de datos** | Salidas viejas de Kaggle por reutilizar el slug; días que faltan; archivo que termina antes | Contar velas/días; slug nuevo por corrida |
| A9 | **Estadística** | Bootstrap por operación en vez de por sesión; BH mal aplicado; signo del p | Revisar contra la implementación común |
| A10 | **Selección y multiplicidad** | Confirmar con datos ya vistos; pruebas fuera del contador | Contador global y actas; quién eligió qué y cuándo |

**Gravedad**: alta si el resultado sostiene una decisión vigente (cartera, forward, holdout, PALANCA); media si sostiene un NO_REPETIR
(puede estar escondiendo una pista); baja si es descriptivo o ya superado.

## 2. Método
1. Barrido automático de patrones en el código (A1, A2, A3, A7) y kernel de auditoría de datos (zona de cada archivo).
2. Inventario de resultados afectados, por gravedad.
3. Lo afectado **se re-mide** con el código corregido (slug nuevo; la corrida vieja queda como histórico). Si la conclusión cambia, se
   actualizan el factor y la decisión en el mismo commit.
4. Cada clase confirmada deja una **guarda automática** (test o chequeo en `tools/cierre.py`).

## 3. Hallazgos (2026-11-16)
| # | Clase | Hallazgo | Alcance | Estado |
|---|---|---|---|---|
| H1 | A1 | En `edgelab-sqx-m1` y `edgelab-sqx-barras` sólo los `*_M1_dukas` vienen en hora del servidor (NY + 7); **Russell, DAX, EuroStoxx, FTSE, Nikkei y petróleo vienen en UTC** (kernel `edgelab-auditoria-tz-m1`: picos a las 08:00/07:00 en el DAX = 09:00 Frankfurt, 00:00 en el Nikkei = 09:00 Tokio, etc.). Se leían con − 7 h: 2 h (invierno) / 3 h (verano) corridos. | M1 intradía lote 1 (5 de 8 índices), lote 2 (DAX), régimen VWAPB (DAX), literatura macro (NOCHE/IMOM en 6 activos H1; corte del día en D1), tanda 2 L1 (Russell, ya re-medida: sin cambio) | Lectores corregidos (`m1_intradia.zona_m1`, `fuentes_ticks.M1_EN_UTC`, `macro_literatura.leer`); un archivo sin zona declarada ya no se lee (test). **Re-corridas lanzadas** (`-tz`). |
| H2 | A3 | `stop_price` de FundedSync es el stop activo al salir (movido a la entrada al activarse el stop administrado). | «R» de la cadena (valores absurdos, nunca decidió nada); tamaño de T a 200 USD en la tanda 4 (superado por la Cartera B a 1 MNQ); ronda 2 de mejora (descartada y re-medida) | Kernel corregido: riesgo inicial de T = clip(rango 09:30–09:45 × 1,25, 2, 100); el resto de los módulos sigue con «stop al salir» (documentado) |
| H3 | A2 | Guardas de holdout en 2026-10-01 00:00 UTC (QuantLab, bundle de LuxImb). | QuantLab: corregido antes de medir SOM. LuxImb: **sin fuga real** (el bundle filtra por fecha de sesión CME; la del 1-oct queda fuera salvo pedido explícito, y entonces la guarda dispara) | Guardas desde `edgelab.holdout` |
| H4 | A1 | `t = tt.astype("int64") // 10**9` en el kernel de FundedSync: depende de la resolución de pandas. Hoy da segundos en Kaggle (verificado en las operaciones), pero es el mismo error de unidades que falló en local. | Ninguno medido | Corregido a conversión independiente de la resolución |
| H5 | A4 | Motor de SOM: stop llenado a su precio con gap en contra y vela de entrada sin stop. | Primera medición de SOM (descartada) | Corregido antes de la medición válida |
| H6 | A4 (al revés) | Motor del catálogo SQX: en órdenes stop, el extremo de la barra de entrada se tomaba como posterior al llenado (lo peor), aunque la barra abre del otro lado; 17–41 % de stops en la barra de entrada en M15/H4. Sesgo **pesimista**: mata candidatas. | Catálogo SQX v1 (descartada) | Orden por M1 dentro de la barra (`sqx_catalogo.simular(m1=…)`, test); v2 sin cambio de veredicto |

## 4. Re-mediciones (resultado)
| Estudio | Antes → después | ¿Cambia la conclusión? |
|---|---|---|
| Tanda 2 L1 (Russell, salida al cierre) | S y W 3/3 → 3/3 (W conjunto +0,121 → +0,107) | No |
| Tanda 2 L3/L4 (días de tendencia, vol rugosa; Russell) | anticipación 0 índices → 0; H ≈ 0,05 → ≈ 0,05 | No |
| Tanda 2 L3 mediodía | 0 índices → 0 | No |
| Literatura macro (6 activos en UTC) | mejor t 1,90 → 1,90 (umbral 4,02); NOCHE bruta DESC +0,032 → +0,024; 14 variantes cambian, todas peores | No |
| M1 intradía lote 2 (DAX) | el DAX tenía **18 gaps** en 14 años (ventana equivocada) → 253; ninguna variante pasa, bruto ≈ 0 | No (ahora bien medido) |
| Régimen VWAPB (DAX) | reciente bruto **+0,47 → −0,09**; 2020–23 +0,05 → +0,20 | **Sí, en lo descriptivo del DAX** (frase retirada); el holdout (NQ+YM) no lo usó |
| Franklin (gap en el stop) | 2020–26 NQ +0,100 → +0,097, ES +0,116 → +0,115; holdout +0,268 → +0,267 R, Fisher 0,104 → 0,105 | No |
| M1 intradía lote 1 (5 índices en UTC) | ninguna variante pasa (mejor t neto −2,4); bruto DESC por familia e índice: ORB −0,06…−0,01, pre-rango −0,06…+0,07, VWAPB +0,01…+0,05 (antes +0,04…+0,08) | No |

## 5. Guardas que quedan
- `tests/test_auditoria_patrones.py` (en `tools/cierre.py`): prohíbe convertir fechas dividiendo el int64 por 1e9 y la frontera del holdout a
  medianoche UTC.
- `m1_intradia.zona_m1` y `fuentes_ticks.M1_EN_UTC` (test): un CSV sin zona horaria declarada no se lee.
- Simuladores: `_sim_velas`, `franklin_variantes` y SOM llenan el stop a la apertura cuando hay gap.

## 6. Balance de esta vuelta
Cinco clases de error confirmadas y cerradas en código (H1–H5). De ocho re-mediciones, **ninguna cambia una decisión**: sólo se retira una
afirmación descriptiva (DAX reciente en VWAPB). Los NO_REPETIR afectados (pre-rango 08:12, ORB, gap/ruptura del día previo, banda 3 del VWAP,
literatura macro) quedan sostenidos con los datos bien leídos. Pendiente para la próxima vuelta: inventario de A8 (salidas viejas de Kaggle) y
A9/A10 sobre las campañas del embudo anteriores al 2026-11-14.
