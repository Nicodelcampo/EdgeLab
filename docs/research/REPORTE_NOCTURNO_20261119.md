# Informe de la noche del 18 al 19-nov: auditoría de las estrategias, mejoras probadas y qué queda vivo

Estado: VIGENTE — informe de trabajo autónomo (pedido de Nico: «audita las estrategias que ya tenemos, las "mejores" y también el resto …
corregir errores, indagar, probar variantes, buscar mejoras, validarlas, y reportar todo el trabajo … sé cuidadoso al dar por muertas»).
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. **0 edges promovidos.** Todo lo de abajo pasó por la
cadena (pre-registro → conteo → corrida → DESC → REP con potencia K49); el holdout A5 y el terminal siguen sellados.
Tablero de frentes: `FRENTES_ABIERTOS_20261119.md`. Lo más valioso y qué indagar primero: `FACTORES_CON_VENTAJA.md`.

## 1. Resumen en cinco líneas
1. **La mejor candidata sigue siendo la canasta T + R en NQ** (T: ruptura de apertura de FundedSync; R: AtrPhase con stop 0,25 × ATR20).
   Las dos son régimen robusto (81/81 variantes de su grilla positivas, PBO 0,17 / 0,23, sin look-ahead). Queda pre-registrada su vigilancia
   forward (`regimen_forward_20261119/`), y es lo único que puede decidir: el vendedor armó su versión el 29-oct, así que no queda historia limpia.
2. **SOM y Franklin son señales reales, no regímenes netos.** Franklin rinde en días volátiles (+0,12/+0,15 R en DESC), pero ni REP ni otros
   índices tienen potencia para confirmarlo: queda para el forward.
3. **El resto del catálogo nuevo no pasa:** 0/8 y 0/12 en los dos lotes de Carril 2, 0/13 Option Alpha, Carril 1 (FLUJOS-MACRO) y RoboQuant con
   bruto real y neto negativo, ESTRUCTURALES (Gemini) refutadas, EXTERNAS-28 con 4/114 que pasan la fricción (Dual Thrust: neto ≈ 0).
4. **Carril 2 no es operable en LucidFlex:** Lucid obliga a estar plano a las 16:45 ET y no permite posiciones de un día al otro. Sí permite
   operar con noticias, así que T, R, SOM y Franklin no tienen restricción.
5. **Errores encontrados y corregidos con guardas en código:** K53 (FM6 no disparaba: la sesión cruza medianoche) y K54 (el kernel de ticks no
   tenía el VIX y FM7 se calibró contra otra regla). Ninguno cambió un veredicto, pero los dos habrían podido producir uno falso.

## 2. Estrategias «mejores» — auditoría y estado
| Estrategia | Qué se auditó | Veredicto | Número clave | Qué falta |
|---|---|---|---|---|
| **T** (FundedSync, NQ) | grilla de 81, PBO, quiebre sup-F, prefijo, corrección de Antigravity (ventana 2012+) | REGIMEN_ROBUSTO desde 2021 | +0,15 R/op neto (mediana de grilla) | forward (REGIMEN-FORWARD) |
| **R** AtrPhase en R | stop 0,25 × ATR20, grilla de 81, prefijo, ES | REGIMEN_ROBUSTO | +0,27 R/op, 16/19 años, ES +0,15 | forward en canasta con T |
| Canasta T + R | correlación, Lucid | candidata | Sharpe 2,43 desde 2020; Lucid +$440/cuenta y +$143/mes con la media contraída a la mitad (T sola +$425 / +$113) | forward |
| Z | grilla | INTERMEDIO (la fábrica es un pico) | — | sale de la canasta |
| A20 | ventana completa y desde 2017 | SOBREAJUSTE completa; INTERMEDIO desde 2017 (sólo 2022+, ES negativo) | — | sólo forward |
| SOM | régimen, mejoras, tamaño, stop | señal robusta, sin régimen neto; filtro de fricción pasa DESC | +0,013 R filtrado | forward |
| Franklin | régimen, mejoras, tamaño, stop | señal robusta; días volátiles pasan DESC; sin potencia en REP ni en YM/EMD/RTY | +0,12/+0,15 R en días volátiles | forward |

**Palancas probadas que NO son palanca** (para no repetirlas): el stop (el bruto es fijo en puntos), el tamaño sin sesgo de nivel de precio
(K52: las ganancias del contrato fijo eran sesgo), la hora del día para el spread (el costo canónico es correcto) y la fricción de RQ5/RQ6.

## 3. El resto del catálogo — lo nuevo de esta noche
| Campaña | Pruebas | Resultado | Cuidado al darlas por muertas |
|---|---|---|---|
| CARRIL2-LOTE1 (IBS+VIX, Double Seven, Turnaround Tuesday, cambio de mes) | 8 | 0/8 en BH | SIN_EVIDENCIA, no refutación: MDE 0,14–0,21 R; Double Seven +0,079 (p 0,047) repite F-CONNORS |
| CARRIL2-LOTE2 (pico de VIX, P80, eVRP, z-score de compresión, Dynamic Breakout II, rotación ES/GC) | 12 | 0/12 en BH | pico de VIX +0,136 R (p 0,018) y compresión +0,089 R (p 0,016; contra control p 0,029) son pistas: misma dirección mecánica. P80 y DBO negativos |
| FLUJOS-MACRO (Carril 1, FM1–FM8) | 16 | FM1/FM2 bruto real, neto negativo; REP sin potencia | grupo «bruto real sin neto intradía» (como RQ5) |
| EXTERNAS-28 | 114 | 4/114 pasan la fricción (todas Dual Thrust); Gemini ya las midió en DESC: bruto +0,03–0,05 (p < 0,005), neto ≈ 0 | REP sin potencia con un neto ≈ 0 |
| TAMANO-K52 | 4 | sin mejora | — |

## 4. Errores encontrados y guardas nuevas
- **K53 (FM6 no disparaba):** la sesión CME empieza 18:00 del día anterior y un filtro de minuto sin tope tomaba esa vela. Corregido, test con M1
  real, la calibración v1 archivada como descartada; `a5_campana.calibracion` frena si una definición no dispara.
- **K54 (FM7 con 42/209 sesiones comunes entre ticks y M1):** el kernel de ticks de Kaggle no tenía el parquet de CBOE y el módulo cayó en
  silencio a un respaldo (RV5 o ATR). Le pasaba también a OPTION-ALPHA. Guardas: `a5_campana.insumos_distintos` (frena la calibración si el M1
  trae una columna de contexto que los ticks no) y `tablas.insumos_externos` (adjunta el dataset M1NT8 a los módulos que leen CBOE o el
  calendario). Ningún veredicto cambia.
- **K50/K51** (de antes de la noche): JSONL roto por pegado de líneas y una corrida ad hoc lanzada antes de contarse; los dos con test en CI.
- **Ejecutabilidad (nueva lección):** verificar horario, tenencia y noticias de la cuenta objetivo antes de abrir una familia. Carril 2 se midió
  entero antes de ver que Lucid no admite overnight.

## 5. Qué queda vivo y qué haría después
1. **Forward de la canasta T + R** (y SOM/Franklin como regímenes) con `tools/seguimiento_forward.py <HASTA>` cuando haya datos sellados nuevos
   (el dataset sellado se actualizó por última vez el 16-nov; no había sesiones forward para leer). El vigilante decide solo: EDGE con e ≥ 20,
   suspender por futilidad o drawdown. **Corrección:** tarda ≈ 15 meses con la media de desarrollo y ≈ 33 con la mitad, no 4–8
   (`regimen_forward_20261119/ADENDA_POTENCIA.md`).
2. **Reversión de volatilidad implícita** (pico + compresión) como una sola hipótesis en datos no mirados: sólo sirve para una cuenta de broker
   (es de varios días). Con RTY/EMD la potencia histórica no llega a 0,8 (≈ 0,3): forward o nada.
3. **Franklin en días volátiles**: forward con vigilancia; ATR y VIX cuentan como una sola mejora.
4. **Decisiones tuyas:** si se quiere una cuenta de broker (sin la regla de las 16:45) para las estrategias de varios días; y operar T+R en
   micro cuando el vigilante dé EDGE (dinero real es sólo tuyo).

## 6. Auditoría de la canasta T + R (segunda parte de la noche)
- **Fechas fijas del vendedor (AUDITORIA-EXCLUSIONES, 1 prueba contada):** T excluía 24 días (20 «datos degradados», 8 vencimientos) que en
  nuestros datos rinden −0,22 R por día (percentil 4,7 % contra días al azar): sesgo del vendedor, pero chico. **T operable 2021–2026 =
  +0,181 R/op** (antes +0,186). R: inocua (los 3 días normales bloqueados eran ganadores).
- **R no se puede operar tal cual con el DLL:** el DLL no tiene stop para R; la R validada usa un stop de catástrofe 0,25 × ATR20. Sin stop
  la media es parecida pero la peor operación pierde ≈ 1,6 ATR20, del orden del límite diario de Lucid con 1 MNQ. Hace falta un stop externo
  o una estrategia NT8 propia; mientras tanto, en Lucid sólo T.
- **El forward tarda más de lo que escribí:** ≈ 15 meses hasta EDGE con la media de desarrollo y ≈ 33 con la mitad (no 4–8). Las reglas no
  cambian (`regimen_forward_20261119/ADENDA_POTENCIA.md`).
- **Archivos viejos del CFD con riesgo de T roto** (anteriores a la corrección del 16-nov): no usar su R; el forward vigente sale corregido.
- **Re-indagación por época** (`RE_INDAGACION_PISTAS_20261119.md`): la reversión corta clásica se apagó desde 2018; la compresión de
  volatilidad crece pero necesita días (no Lucid) y décadas de forward para confirmarse; Z es un pico de fábrica sin datos limpios con potencia.

- **Transferencia a datos nunca medidos (TRANSFER-RTY-EMD, 2 pruebas):** Z en Russell da +0,146 R desde 2018 (p 0,085; negativa antes,
  como en NQ) y la compresión de VIX +0,035 R (p 0,21): mismo signo, sin significancia. REP de RTY sigue sellado para confirmarlas.

Aporte al referente: se cerraron con evidencia y potencia publicada los frentes del catálogo nuevo, se descartó para Lucid todo lo que no es
operable allí, se corrigieron dos errores que podían dar falsos positivos, y la canasta T + R quedó como la única candidata con vigilancia
forward pre-registrada.
