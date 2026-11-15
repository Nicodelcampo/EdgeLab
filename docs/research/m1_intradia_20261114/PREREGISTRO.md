# ORB y pre-rango 08:12 sobre M1 de 12 años (pre-registro, 2026-11-15)

Estado: VIGENTE. Etapa EF3 (réplica con potencia de pistas vivas). North Star sha256 16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345.
Código: `edgelab/research/m1_intradia.py`; kernel `tools/kaggle_grilla/m1_intradia_main.py` (`tools/m1_intradia.py`). Datos: M1 de
Dukascopy (CFD) exportadas de SQX hasta 2026-09-29 16:14 NY (dataset privado `nicolasbuttaro/edgelab-sqx-m1`); 8 índices (S&P, Nasdaq,
Dow, Russell desde 2019, DAX, Nikkei, FTSE, Euro Stoxx). Linaje: F-ORB-EMA20-NQ-STOP-OPUESTO (pista viva) y H-SWEEP-1 (YM pre-rango).

## Reglas (fijas)
- **ORB**: rango 09:30 → 09:30+N (N 15/30/60 min, hora NY); el primer CIERRE fuera del rango fija el lado; entrada BRK (mercado, barra
  siguiente) o EMA20 (límite en la EMA20 de 2 min del momento de la ruptura); stop en el extremo OPUESTO del rango o en la MITAD;
  objetivo 1 R, 2 R o al cierre; salida 15:55 NY; piso de riesgo 0,2 × rango. 36 variantes por índice.
- **PRERANGO**: rango 08:12–09:12 NY; desde 09:30, primer extremo tocado y vuelta adentro (cierre) → entrada hacia el extremo opuesto;
  stop 0,25 × rango detrás del extremo tocado; objetivo el extremo opuesto. Además, la información: frecuencia de doble toque.
- Motor M1 conservador: stop atravesado por gap sale a la apertura; en la barra de un llenado por stop/límite sólo puede saltar el
  stop; objetivo sólo si lo atraviesa; stop y objetivo en la misma barra → stop. R **bruto** y **neto** (spread de Dukascopy por ida
  y vuelta). Validado sobre caminatas aleatorias (|t| < 3 en todas las celdas).
- Total: 37 variantes × 8 índices + 37 canastas = **333** (registradas en el contador).

## Inferencia (fijada antes)
- Nulo intradía: cada minuto toma la barra relativa del MISMO minuto del día de otro día al azar (conserva la volatilidad por hora,
  destruye la dependencia dentro del día); 30 réplicas de la familia entera; umbral = p95 del máximo t NETO en DESC (hasta 2019).
- Pista: t neto DESC > umbral **y** R neto > 0 en OOS 2020–2023 **y** en RECIENTE 2024-01 → 2025-07; PSEUDO (2025-08 → 2026-09) como
  réplica ex ante. Para NQ/ES/YM esa ventana se re-mide además sobre futuros reales en EdgeLab.
- La pregunta abierta de la pista ORB (¿es señal o fricción?): diferencia OPUESTO − MITAD en BRUTO. Si sólo existe en neto, es la
  palanca «stop grande frente a la fricción», no una señal.
- Canastas primero; los índices sueltos son el detalle.

## Justificación económica y cómo podría refutarse
ORB: la primera media hora concentra la información de la noche y del flujo institucional de apertura; la ruptura con stop en el extremo
opuesto deja correr el desequilibrio. Pre-rango: el rango previo a la apertura acumula órdenes en sus extremos; el barrido y regreso
señala absorción. Refutación: nada supera el nulo, o lo que lo supera es negativo en OOS o en RECIENTE, o la ventaja de ORB es sólo neta.

## Enmienda 1 (2026-11-15, antes de lanzar; pedido de Nico): tercera banda del VWAP
Se suma `VWAPB` (ficha EL-VWAP-BANDA3) al mismo kernel: VWAP anclado a las 09:30 NY con volumen de ticks de Dukascopy y su desvío
ponderado; desde las 10:00, el primer cierre del día fuera de ±K desvíos (K = 3, y K = 2 como control de dosis-respuesta) dispara
REV (hacia el VWAP: objetivo VWAP o banda 1; stop banda K+1 o extremo del día + 0,5 desvío) o CONT (a favor: objetivo 1 R o 2 R; stop
banda K−1). Bandas congeladas al disparo; cierre 15:55; piso de riesgo 0,5 desvío. 12 variantes por índice × 8 + 12 canastas = **108**
más en el contador. Lectura fijada: la banda 3 vale si supera al nulo, le gana a la banda 2 en la misma regla (dosis) y la ventaja existe
en bruto. Validado en caminatas aleatorias (|t| < 3). Limitación: volumen de ticks (proxy); la pseudo-réplica se re-mide en futuros con
volumen real.
