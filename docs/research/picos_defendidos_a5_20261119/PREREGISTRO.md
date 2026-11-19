# PICOS-DEFENDIDOS A5: un nivel de picos que se defendió y se vuelve a dejar termina tomándose (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr. Reemplaza, para lanzar, a `docs/research/agente/PICOS_DEFENDIDOS_20261119.md`
(PR Nicodelcampo/EdgeLab#200): misma idea y misma detección, otra partición y otra familia de pruebas. Auditoría:
`docs/research/agente/AUDITORIA_PICOS_DEFENDIDOS_20261119.md`.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (DESC de A5 sobre M1 largo; REP con un paso de LORD++). **Familia:** `PICOS_DEFENDIDOS_A5`.
- **Linaje:** padre `ESCALONADAS_M1_A5`, misma población de picos en M1 operada hacia la ruptura, como información.
- **Herramienta:** `tools/a5_campana.py` con `edgelab/research/picos_defendidos_a5.py`. El módulo usa la detección causal del PR
  (`edgelab/research/agente/picos_defendidos.py`) sin cambios. `registro_global.exigir_contada` al inicio (K51).

Antecedentes:
- **En contra:**
  - F-ESCALONADAS-M1-SIN-SENAL: escalera plana de picos en M1 operada a favor de la ruptura en NQ/ES/YM, 18/18 celdas ≈ 0 en bruto
    (A5 2006–2025);
  - F-FILTRO-PICOS-NO-AGREGA;
  - IPC-NIVEL-MES: un nivel con visitas se barre 6,2 pp menos;
  - DOBLE-RETROCESO: la lectura opuesta, sin señal.
- **A favor:** F-HFT-ZONAS-NO-SON-SOPORTE: donde hubo actividad el nivel rebota menos que un nivel cualquiera.
- **Lo nuevo frente a ESCALONADAS:** la secuencia completa (alejamiento, acercamiento sin tomar, nuevo alejamiento) y el disparador; se mide
  si eso agrega algo.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K33 costos, K36 escalas, K40 motor calibrado, K48 causalidad, K49 potencia, K51
conteo antes de correr, K53/K54 insumos, K55/K56 diagnóstico).

Potencia previa: la frecuencia por definición sale de la calibración M1 (eventos sin desenlaces) antes de correr. Las definiciones con
n < 30 en DESC no entran a la familia de BH (`potencia_previa.py --conteo`). Referencia: ESCALONADAS-M1 tuvo 38.011 series en DESC con MDE80
de 0,02–0,03 R. Una definición de este tamaño en 10 min tiene del orden de miles de eventos en 18 años y tres índices, con MDE80 ≈ 0,05 R
o menor. Si una definición queda con MDE80 > 0,15 R, su nulo se publica como SIN_POTENCIA.

Diagnóstico de mecanismo:
- **Perillas:** cada definición cambia una sola cosa respecto de la regla de la captura (PD0): el disparador (PD1–PD8), la temporalidad
  (PD9, PD10) o el filtro de tendencia (PD11 sin filtro; PD0C en contra, como control).
- **Lectura:** antes de leer la R de cada una se publican, con `edgelab.research.diagnostico_grilla`:
  - las operaciones por definición;
  - el número efectivo de variantes, porque las definiciones comparten eventos: una misma secuencia puede disparar varios disparadores;
  - la descomposición por meses (episodios).
- **Prueba de fondo:** que la tendencia a favor supere a la tendencia en contra (PD0 contra PD0C).

## Justificación económica
- **Mecanismo:** un nivel que se defendió acumula stops de quienes operan el rebote y órdenes de ruptura en reposo detrás. Si la tendencia
  empuja hacia el nivel, la próxima llegada ejecuta esa liquidez y el precio sigue más allá.
- **Quién pierde:** quien opera el rebote del nivel con el stop pegado.

## Reglas (fijas)
- **Regla de la captura de Nico (PD0):**
  - velas de 10 min armadas desde M1;
  - nivel PAR (dos picos del zigzag de 1,5 ATR con diferencia ≤ 0,25 de la excursión central);
  - alejamiento 1 ≥ 2 ATR, acercamiento a ≤ 1 ATR sin tomar el nivel, armado con un cierre ≥ 1 ATR del acercamiento;
  - tendencia E20 a favor;
  - entrada al disparo «ALEJA», hacia el nivel;
  - stop 1 tick detrás del extremo del alejamiento 2, con riesgo mínimo de 0,5 ATR;
  - objetivo P + 0,5 ATR o P + 1 ATR;
  - entrada a mercado en el primer tick tras la vela de decisión (motor único, calibrado); nada cruza la sesión.
- **Definiciones:**
  - PD0 = la regla de la captura;
  - PD1–PD8 = PD0 con cada otro disparador (REACERCA_33, REACERCA_50, EMA_TOQUE, EMA_DOBLE_CRUCE, CRUCE_EMAS, ESPEJO_75, ESPEJO_100, POC);
  - PD9 / PD10 = PD0 en 5 y 15 min;
  - PD11 = PD0 sin filtro de tendencia;
  - control de PD0: PD0C (tendencia en contra).
- **Datos:** M1 real de futuros de NT8 (`M1NT8:`), NQ, ES e YM, ventana 2006-01-06 → 2025-07-31.
  - Desenlaces sólo en meses DESC (exploración) y REP (confirmación) de A5.
  - HOLDOUT y EMBARGO no se calculan.
  - Calibración M1 contra ticks reales en 2025-08 → 2026-03 (ya mirado).
- **Costos:** fricción canónica de `edgelab/costos.py`:
  - NQ: 1,55 pts (adverso 2,05);
  - ES: 0,89 (1,39);
  - YM: la suya.
  - R neto = (resultado − fricción) / riesgo inicial.
- **Exploración (DESC):** 12 definiciones × 2 ejecuciones × (1 + filtros comunes) = 264 pruebas (`tablas.conteo`), BH q 0,10 sobre el R
  neto, bootstrap por sesión.
- **Confirmación (REP):** las nominadas, con un paso de LORD++ y plan de potencia (K49). Sin potencia = NO_CONCLUYENTE (no mata).
- **Contraste de la mitad tendencial:** PD0 − PD0C en DESC, reportado aparte (no entra a BH).
- **Contador:** 264 pruebas en `PICOS_DEFENDIDOS_A5`, registradas con `tools/registro_global.py preregistrado` antes de correr.

## Cómo podría refutarse
- 0 nominadas en DESC con MDE80 publicado ≤ 0,05 R.
- PD0 ≤ PD0C: la mitad tendencial de la idea no aporta.
- Las nominadas pierden en REP con potencia.
- El bruto de PD0 ≈ ESCALONADAS-M1: la secuencia «defendida» no agrega nada a la escalera de picos.
- Calibración M1 contra ticks fallida (K40) o un insumo que el M1 no tiene (K54: el POC se arma del perfil de volumen de M1).

## No medido
- La grilla del PR (velas de 1 y 3 min, picos Z15 y Z3, tres definiciones de tendencia más, cortes de alejamiento): no se corre.
- Stop de 1 y 2 ATR.
- Paridad con NT8.
- Versión de estado continuo.
- Otros activos.
