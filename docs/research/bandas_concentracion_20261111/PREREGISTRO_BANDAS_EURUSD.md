# BANDAS-EURUSD — ¿desde qué distancia ir hacia una banda de concentración OG+VI paga con 1:1 o 1:1,5?

Estado: PRE-REGISTRO (2026-11-11, pedido de Nico). Escrito antes de generar ninguna tabla. Etapa **EF2 exploratoria** sobre EXPLORA y
confirmación UNA vez sobre CONFIRMA con lo que se congele. Familia `LUXIMB_CONCENTRACION` (nueva: no hereda resultados ni multiplicidad).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Módulo `edgelab/research/bandas_eurusd.py` (cadena estándar, preflight en verde); detector = `bandas_concentracion.detectar` del PR
Nicodelcampo/EdgeLab#198 portado a numba con paridad exacta (`tests/research/test_bandas_eurusd.py`). Spec del detector:
`SPEC_BANDAS_CONCENTRACION_OG_VI_20261111.md` (alto 8 pips, umbral 22, vida 500 min).

## Pregunta (de Nico)
¿Hay alguna distancia entre el precio y una banda viva desde la cual ir HACIA la banda, con objetivo en su inicio (borde cercano) o en su
final (borde lejano) y riesgo 1:1 o 1:1,5, que sea rentable neta de costos? ¿Con qué criterio de muerte de la banda?

## Población (espacio de eventos: spec §5) y por qué
Se mide la **aproximación** (§5.2): primera vez en las 72 h posteriores al nacimiento que el cierre M1 pasa de > x a ≤ x pips del
borde cercano, con el precio fuera de la banda. Es la entrada que pide Nico. No se miden acá el primer toque como entrada, la ruptura
ni el estado continuo (alternativas escritas en la spec, para otra campaña).
**Control:** la misma operación hacia una franja ESPEJO a la misma distancia del otro lado del precio (sin concentración): real −
espejo separa «ir hacia la banda» de «la volatilidad lleva al precio a x pips de cualquier cosa».

## Perillas (fijadas acá)
- Distancia x: 5, 10, 15, 20, 30, 50 pips. Objetivo: borde cercano («ini») o lejano («fin»). Riesgo: 1:1 o 1:1,5.
- Muerte de la banda (evaluada en la vela del evento): DET (viva según el detector: ≤ 500 min desde la última vela que cumplió la
  concentración), V2 / V8 / V24 / V72 (horas desde el nacimiento), TOQUE (≤ 72 h y todavía no tocada), CRUCE (≤ 72 h y todavía no
  cruzada por un cierre).
- Ejecución: a mercado en el primer tick de la vela siguiente; stop a mercado al tick que lo cruza; objetivo límite; tope 240 velas,
  fin de sesión o hueco (motor único `edgelab/research/ejecucion.py`).
- Celdas: 7 × 6 × 2 × (real + espejo) × 2 riesgos = 336, registradas como `luximb_concentracion/eurusd_explora`.

## Costos y guarda
EURUSD con la fricción de 6E (`edgelab/costos.py`, ≈ 2,1 pips por viaje). La guarda de fricción ≤ 0,08 R exige riesgo ≥ ≈ 26 pips:
**sólo x = 30–50 pips puede ser elegible** (x chicas se informan pero su R neto lo come el costo). Spot de Dukascopy: el neto
definitivo se confirma en 6E (futuro) en forward.

## Datos y uso
EURUSD de Dukascopy (`edgelab-dukascopy-6e-eurusd`, ≈ 4,5 años hasta 2026-09-30; el holdout se rechaza en el lector).
- **EXPLORA:** desde el inicio de los datos hasta 2024-12-31 → búsqueda libre (`tools/tablas.py explorar`), nulo de la búsqueda.
- **CONFIRMA:** 2025-01-01 → 2026-09-30, UNA vez, ≤ 10 hipótesis congeladas con hash (`tools/tablas.py congelar|confirmar`).
  Declarado: el umbral 22 del detector se calibró (target-free, sin desenlaces) en mar–jun 2026, dentro de CONFIRMA.
- Paridad LUX-IMB en FX: ABSTENCIÓN (spec §4): las zonas de Python no se compararon con las de TradingView en EURUSD.

## Justificación económica y cómo podría refutarse
- **Justificación:** muchas zonas de desequilibrio apiladas en pocos pips marcan precios con órdenes sin completar; el precio que se
  acerca tendería a ir a buscarlas (imán) y a recorrerlas.
- **Refutación:** real − espejo ≤ 0 (ir hacia la banda no paga más que ir hacia una franja cualquiera a la misma distancia), o
  ninguna celda elegible queda sobre el nulo de la búsqueda en EXPLORA, o lo congelado da R neto ≤ 0 en CONFIRMA.

## Adenda (2026-11-11, antes de ver ninguna tabla): filtros de VWAP
Pedido de Nico: «probá filtrar con VWAP diario, VWAP de NY y ambos; no hay una manera definida, usá todas las mejores». La cadena
agrega a toda tabla `edgelab/research/rasgos_comunes.py`: VWAP anclado a la sesión y a las 09:30 de Nueva York, con su desvío
ponderado por volumen, y 10 filtros (hacia / contra cada VWAP, los dos hacia / los dos contra, lejos ≥ 1 desvío, lejos y hacia).
Las celdas suben en consecuencia (`tablas.conteo`) y la diferencia se registra aparte (`.../vwap`). Las tablas lanzadas antes de esta
adenda se relanzan con el código nuevo y no se miran.
