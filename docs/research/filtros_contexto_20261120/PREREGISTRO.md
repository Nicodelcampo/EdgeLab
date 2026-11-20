# FILTROS-CONTEXTO: ¿VIX, VVIX, GEX, DIX, SKEW, la estructura VIX9D/VIX o el COT separan días buenos de malos en A20, T, R, Z-banda y RQ5? (pre-registro, 2026-11-20)

Estado: PRE-REGISTRO — se commitea y se cuenta antes de leer cualquier desenlace condicionado a un indicador.
- **Pedido de Nico (2026-11-20):** «Revisa si algún filtro como gex vix o alguno de la captura serviría para este caso u otros incluyendo
  las estrategias que ya están validadas. Luego de eso abrí el último holdout en el caso de que no haya nada que cambiar o probar en cuanto
  a filtros». La captura lista VIX, VVIX, GEX, DIX, SKEW, COT y put/call.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (tamiz de filtros en DESC de A5; réplica en REP). **Familia:** `FILTROS_CONTEXTO`; linaje padres `FUNDEDSYNC`, `RQ5_REGIMEN`,
  `GEX`, `DIA_TENDENCIA_A5` (información).
- **Herramienta:** `tools/filtros_contexto.py` (`conteo` sin desenlaces; `correr` con `registro_global.exigir_contada`, K51). Reusa las
  operaciones ya medidas de cada estrategia; no hay simulador nuevo.

Antecedentes:
- **F-GEX-DIA-TENDENCIA** (NO_REPETIR como filtro de T+Franklin+SOM): un GEX bajo marca días de tendencia, pero con AUC ≈ 0,55 no se pudo
  confirmar. **T|GEX ya se miró**: se incluye por completitud y sólo cuenta si replica.
- **F-DIA-TENDENCIA-CLASES-NUEVAS-NULAS:** DIX y otras clases nuevas dieron nulo como predictores del día de tendencia. **T|DIX ya se miró**
  en esa forma.
- **F-CRASH-VIX-INVERTIDA-REFUTADO.** Además, el carril 2 con VIX > P80 dio negativo y el pico de VIX está apagado desde 2018.
- **A20-REGIMEN** y la curva de A20 NQ (`A20_CURVA_NQ.png` de esta carpeta): positiva desde 2022 y negativa en 2018–2021. La curva es
  descriptiva y no se usa para elegir el filtro.
- **RQ5-REGIMEN:** REGIMEN_ROBUSTO en DESC y holdout A5 NO_CONCLUYENTE (+0,027 R).
- **Put/call total de CBOE excluido:** la serie local termina el 2019-10-04, así que no cubre el régimen. Se declara y no se prueba.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27/K49 potencia y nulos sin potencia, K36 escalas, K48 causalidad por fecha de publicación, K51 conteo antes de correr, K55/K56 diagnóstico y episodios).

Potencia previa:
- **Operaciones por tercil en DESC 2018-01 → 2025-07** (`CONTEO.json`, contadas sin desenlaces):
  - A20 ≈ 260–490;
  - T ≈ 270–480;
  - R ≈ 40–80;
  - Z-banda ≈ 37–61 días;
  - RQ5 ≈ 410–1.370 (el COT sólo con NQ y ES).
- **sd de R incondicional:** A20 2,36; T 1,14; R 1,83; Z-banda 1,10; RQ5 1,03.
- **MDE80 del contraste alto − bajo:**
  - A20 ≈ 0,50 R;
  - T ≈ 0,25 R;
  - R ≈ 0,99 R;
  - Z-banda ≈ 0,67 R;
  - RQ5 ≈ 0,13 R.
- **Lectura:**
  - R y Z-banda no tienen potencia para ningún filtro realista. Entran (todos los terciles extremos tienen n ≥ 30), pero un nulo ahí no dice nada.
  - Con A20 y T sólo se detecta un efecto grande.
  - RQ5 es la única con potencia para un efecto moderado.
  - Ningún nulo cierra nada (K49); cada prueba publica su MDE.

Diagnóstico de mecanismo:
- **Perillas:** no hay grilla de perillas. Son 7 indicadores × 5 estrategias. Los indicadores están correlacionados (Spearman de los
  percentiles: VIX–GEX −0,66, VIX–TERM +0,62, GEX–TERM −0,62, VIX–VVIX +0,53). El número efectivo de indicadores es 4,1 (`CONTEO.json`).
  Por eso las nominaciones de VIX, GEX y TERM en una misma estrategia se leen como un solo hallazgo, no como tres.
- **Dosis-respuesta:** se publican los tres terciles y si son monótonos.
- **Episodios:** para lo nominado se publica el contraste por año.

## Justificación económica
- **Volatilidad implícita y su convexidad (VIX, VVIX, TERM) y la gamma de los dealers (GEX):** cambian quién provee liquidez intradía.
  Con gamma corta, la cobertura de los dealers persigue el precio y alarga las tendencias. Eso favorece a A20, T, Z y RQ5, que siguen el
  movimiento del día. Con gamma larga la cobertura lo frena.
- **Flujo de compra en dark pools (DIX):** puede anticipar presión compradora.
- **Prima de cola (SKEW):** mide la demanda de protección.
- **Posicionamiento especulativo (COT):** extremos de posición pueden preceder a reversiones.
- **Quién pierde:** si un filtro funciona, el día malo excluido es aquel en que el contexto absorbe el movimiento. El costo es menos
  operaciones, y por la regla de frecuencia (FRECUENCIA_PROP) sólo vale si el R por mes no baja.

## Pruebas y decisión (fijas)
**Datos.** Cada indicador se convierte en su percentil móvil causal: 252 observaciones diarias, y 52 semanas para el COT.
- **Asignación a cada operación:** el último valor publicado estrictamente antes de la fecha de su sesión.
- **COT:** el informe del martes se usa desde las sesiones posteriores al viernes de publicación. Para NQ se usa el COT de NQ; para ES,
  el de ES. YM y RTY de RQ5 no tienen COT local y quedan fuera de esa prueba.
- **Fuentes:**
  - VIX y VIX9D/VIX: `data/m1nt8/cboe_volatility_daily.parquet`;
  - VVIX y SKEW: CBOE (`data/cboe_extra/`);
  - DIX y GEX: SqueezeMetrics (`data/DIX_squeezemetrics_20261108.csv`);
  - COT: CFTC legacy (`data/cot/`).

**Estrategias.** Son las operaciones ya medidas, con la misma medida que sus actas:
- **A20 NQ:** fábrica `A20_7_2_2.5_1.5`, `neto_pistas_20261119/RZ_OPS`. R = (resultado − fricción) / riesgo.
- **T NQ:** `m1_largo_20261117/FS_OPS_T2008_NQ`. R = neto / riesgo.
- **R NQ:** `R_21_100_2.5_660`, con stop de catástrofe de 0,25 × ATR20 aplicado con el MAE.
- **Z-banda NQ:** promedio diario de las 9 configuraciones, con el mismo stop.
- **RQ5:** fábrica `L60_m1_c689`, tp 2, en NQ, ES, YM y RTY (`rq5_regimen_20261119/OPS_DESC_REP`). R = r − fricción / riesgo.

**Ventana:** meses DESC de A5 entre 2018-01-01 y 2025-07-31. REP, sólo para la réplica de lo nominado. HOLDOUT y EMBARGO se descartan sin
leerse. La REP de RQ5 ya se miró en su media incondicional (`rq5_regimen_20261119/PREREGISTRO.md`); contra un indicador nunca se miró.

**Prueba (35 = 5 estrategias × 7 indicadores):**
- **Terciles fijos del percentil:** < 1/3, 1/3–2/3 y ≥ 2/3.
- **Estadístico:** media de R neto del tercil alto menos la del bajo.
- **Inferencia:** bootstrap por sesión (B 4.000, semilla 20261120), dos colas.
- **Nominación:** BH q 0,10 sobre las 35.

**Filtro operable de una prueba nominada:** excluir el tercil extremo de menor R.

**Réplica (meses REP 2018-01 → 2025-07):** el contraste tiene el mismo signo con p de una cola < 0,05, **y** el R por mes con el filtro es
mayor o igual que sin él.

**Veredicto:**
- **FILTRO_REPLICADO:** alguna prueba replica.
- **NOMINADO_SIN_REPLICA:** hay nominadas pero ninguna replica.
- **SIN_FILTRO:** ninguna nominada.

**Qué sigue según el veredicto:**
- **SIN_FILTRO o NOMINADO_SIN_REPLICA:** no hay nada que cambiar. Sigue la apertura del holdout terminal de A20 NQ (pedido de Nico, abajo).
- **FILTRO_REPLICADO:** no se cambia ninguna regla todavía. Se informa a Nico y el filtro iría al forward como variante paralela. El
  holdout terminal no se abre hasta que Nico decida, porque hay algo que probar.

**Contador:** 35 pruebas, registradas antes de correr.

## Holdout terminal de A20 NQ (condicional, declarado ahora)
- **Ventana:** sesiones desde la del 2026-10-01 (HOLDOUT-A4) hasta la última completa del M1 de NT8 local. Se descartan las sesiones de
  `SESIONES_EXCLUIDAS_HOLDOUT`.
- **Regla congelada:** la fábrica `A20_7_2_2.5_1.5` sin filtro, con la misma medida.
- **Prueba:** media de R neto > 0.
- **Potencia:** se registra antes de abrir. Será muy baja (≈ 20 operaciones por mes, sd 2,36). Se abre por decisión explícita de Nico en
  este pedido, que levanta K27 para esta apertura, como hizo con RQ5. Su resultado es descriptivo y no mata (K49).
- La apertura se registra con `holdout_ventanas.registrar_apertura` antes de calcular, una sola vez, y nunca se usa para elegir ni ajustar.

## Cómo podría refutarse
- Ningún contraste nominado: los indicadores no separan días buenos de malos en estas estrategias, dentro del MDE publicado.
- Un nominado que no replica en REP o cuyo filtro baja el R por mes: era ruido de selección o no paga la frecuencia perdida.
- Un nominado sin dosis-respuesta o concentrado en un año.
