# Manifiesto: absorción como amplificador de contexto (NQ L2), 2026-09-24

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PROPUESTO. Hace falta el OK de Nico (regla STOP: mira el precio después de los eventos).
**Pedido de Nico (24/09):** la absorción no como entrada pura, sino como **sinergia**. Si el evento solo da ≈ 0 y la absorción sola da ≈ 0, ¿el evento más la absorción da una ventaja asimétrica? No se sabe qué evento. Las mediciones tienen que **sugerir qué eventos vale la pena medir**.
**Ledger:** `artifacts/hippocampus/nq_l2_20260924.jsonl` (el de la exploración, donde las particiones ya estaban declaradas). Toma las particiones de `MANIFIESTO_NQ_L2_EXPLORACION_20260924.md`, sin tocar `P-NQL2-CONF`.

## Estimando

Para cada contexto C y cada horizonte h, con el resultado Y medido **en la dirección que implica la absorción** (bid absorbido → arriba):

    I = [Y(abs ∧ C) − Y(ctrl ∧ C)] − [Y(abs ∧ ¬C) − Y(ctrl ∧ ¬C)]

- **Controles:** los ya corregidos, a la misma distancia del nivel y en el mismo tercil de volumen de los 60 s previos. Deben cumplir C igual que el evento.
- **Efecto del contexto solo:** en instantes al azar emparejados (hora, volatilidad), para verificar que "C solo ≈ 0".
- Lo que busca Nico es una **sinergia pura**: los dos efectos sueltos ≈ 0 y I > 0.

## Resultados (se miden varios canales y la distribución, por regla del proyecto)

Horizontes: 30, 60, 300 y 900 s.

| Canal | Qué mide |
|---|---|
| Con signo | movimiento del medio en la dirección implícita (ticks) |
| **Asimetría** | excursión favorable máxima menos adversa máxima dentro de h (MFE − MAE, en ticks) |
| **Carrera** | P(tocar +X antes que −X), X ∈ {8, 16} ticks (≈ 2 y 4 spreads RTH) |
| Sin signo | \|movimiento\| |

Además, deciles de Y en cada una de las cuatro celdas.

## Contextos (espacio enumerado ahora; cada uno con dirección propia)

A cada contexto se le asigna una dirección. La absorción queda **alineada**, **opuesta** o **neutral** respecto de ella. Todos se calculan en forma causal, desde los trades L1 del mismo archivo, que traen el agresor.

| # | Contexto | Origen en el proyecto | Niveles |
|---|---|---|---|
| C1 | Dentro o a ≤ 4 ticks de una **zona HFT** activa (HFTZonesNQPureV4, paridad certificada en NQ); lado de la zona | HP-006/007 | dentro · borde · afuera |
| C2 | **Toques previos** de esa zona (desgaste) | HP-007 | 0 · 1–2 · ≥ 3 |
| C3 | Borde de una **franja TBZ-EXP** o hueco **DWELL** | familia TBZ | borde de la franja · afuera |
| C4 | **Vela extrema** reciente (el "sello barato" que sobrevivió a F2.9) | F2.9 | ≤ 5 velas · no |
| C5 | **Tendencia** 5 y 30 min (signo del retorno, sobre σ) | filtro de dirección | a favor · contra · lateral |
| C6 | Lado del **VWAP** de la sesión | filtro de dirección | arriba · abajo |
| C7 | **Extremo del día o del overnight** (máximo o mínimo previo a ≤ 8 ticks) | Osler | sí · no |
| C8 | **Número redondo** (múltiplo de 100 puntos) a ≤ 8 ticks | Osler | sí · no |
| C9 | **Régimen de liquidez** (spread y profundidad en terciles causales) | 6E-REGIMES, V1 | bajo · medio · alto |
| C10 | **Bloque horario** (Asia, Europa, apertura RTH, RTH, cierre) | Fase 0 | 5 bloques |
| C11 | **QI** en el instante: acompaña o contradice la absorción | exploración B | a favor · contra |
| C12 | **Ruptura previa**: el nivel ya se había roto en los 5 min anteriores | lifecycle | sí · no |

- Quedan **fuera** en esta etapa: aVolClusterPOI (sin nulo propio, y se estudia sola), LUX-IMB (bloqueada) y noticias macro (sin calendario confiable).
- **Población:** los eventos de absorción del detector causal. Ya se probaron otras poblaciones (toque, estado continuo) en la exploración. **Cómo podría refutarse:** si I ≈ 0 en todos los contextos y a todos los horizontes, con un MDE chico, la absorción no amplifica los contextos listados.

## Dos etapas

1. **Barrido pre-listado** (C1–C12): se publica la tabla completa de I, cada efecto por separado, n de eventos y de sesiones, y MDE por celda.
2. **Búsqueda de heterogeneidad no listada:** un árbol "honesto".
   - Las sesiones de exploración se parten al azar en dos mitades: una construye los cortes y la otra estima el efecto.
   - Las variables son las mismas de C1–C12, pero continuas, más distancias y edades.
   - Profundidad ≤ 3, hojas con ≥ 15 sesiones.
   - Sirve para sugerir combinaciones que la lista no anticipó. **No prueba nada.**

## Número de miradas y reglas de sugerencia (escritas en el código antes de correr)

- Unas 12 × 2–5 niveles × 3 alineaciones × 4 canales × 4 horizontes ≈ **1.000 celdas descriptivas**, más las hojas del árbol.
- Se corrige con **BH-FDR q = 0,10** sobre la familia completa, con IC por sesión (bootstrap por bloques de sesión).
- **Una celda es SUGERENCIA sólo si cumple todo esto:**
  - pasa el FDR;
  - I > 0;
  - el efecto **económico** (asimetría o señal) es ≥ al spread p50 del bloque horario;
  - hay ≥ 30 eventos y ≥ 15 sesiones en la celda;
  - la señal no la hace una sola sesión (efecto con una sesión fuera, *leave-one-out*).
- Como mucho **5 sugerencias** pasan a `P-NQL2-CONF` (24/08–31/10). Se eligen por el límite inferior del IC, no por el punto máximo. Se confirman con un protocolo que se firma antes de abrir esa partición.

## Riesgos

- **Jardín de senderos que se bifurcan:** es la familia más expuesta del proyecto. Por eso el FDR, el piso económico, el tope de 5 y la confirmación en una reserva intacta.
- **Potencia:** con 41 sesiones, las interacciones necesitan del orden de 4 veces más muestra que un efecto principal. Muchas celdas van a salir sin potencia y se publican como tales, con su MDE, sin interpretarlas.
- **Contextos no independientes** (C1 con C2, C5 con C6): en la etapa 1 no se combinan. Las combinaciones sólo aparecen por el árbol honesto.
- **C1 y C3** se calculan con velas de 25 ticks armadas desde los trades de L1 del archivo, no desde `research-v2`: julio y agosto siguen siendo holdout de ticks. Esto vale por la enmienda L2, y el resultado **no puede combinarse** con estudios de ticks sobre esos meses.

## Qué hace falta construir

- En `tools/nq_l2_explore.py`, un paso `synergy`: contextos causales, las cuatro celdas, canales de asimetría y carrera, y MDE.
- Velas de 25 ticks y zonas HFT desde L1: se reutiliza `hftzones_universal` con el perfil de NQ.
- Árbol honesto: implementación propia chica, sin dependencias nuevas.

## Resultados (2026-09-24, corrida B, OK de Nico)

Reporte `artifacts/nq_l2_synergy/report.json` (sha `79627b67399f…`). Hay 41 sesiones de `P-NQL2-EXP`, 3.132 absorciones con 5 controles cada una y 900 celdas en la etapa 1. La reserva no se tocó.

**Desvío de procedimiento, corregido antes de interpretar.**
- La corrida A del reporte armaba el árbol con hojas de ≥ 8 sesiones; el manifiesto pide ≥ 15.
- Se invalidó en el ledger (`EP-NQL2-SYN-INVALIDATE-A`: OBS-S2 y SUG-NQ-SYN-1…4) y se rehízo con 15. El cambio **endurece** el criterio.
- `tree_dirty=True` en el reporte: la herramienta todavía no estaba commiteada cuando corrió. El código que corrió es exactamente el de este commit.

**Etapa 1 (C1–C12 pre-listados): ninguna sugerencia.**
- Una sola celda pasa el FDR, y no tiene dirección:
  - **absorción dentro de una zona HFT con ≥ 3 toques → |movimiento| a 900 s menor que su control en la misma zona**;
  - I = −21 ticks, IC [−32; −11], n = 1.363, 40 sesiones;
  - la zona gastada sola se mueve más (+31), y la absorción adentro la "calma".
- **Lectura:** es información de **volatilidad**, no de dirección. Puede servir para el tamaño de la posición o para el stop, no para entrar. Los canales abs a 30, 60 y 300 s van en el mismo sentido, pero no pasan el FDR.
- **Potencia:** el MDE típico de la interacción es de 5 a 7 ticks a 30–60 s y de 15 a 25 ticks a 300–900 s. Con 41 sesiones sólo se ven sinergias grandes.

**Etapa 2 (árbol honesto, 21 sesiones de estimación):** 3 hojas pasan las reglas, y **las tres dependen de la tendencia de 30 min** (`C5_r30`, medida en la dirección que implica la absorción):

| Hoja | Canal | τ en la mitad de estimación (ticks) | IC | n / sesiones |
|---|---|---:|---|---|
| −374 < r30 ≤ 84 y r5 ≤ 63 (el precio **no** corrió todavía hacia donde apunta la absorción) | sig 300 s | **+13,7** | [5,6; 21,8] | 984 / 21 |
| la misma, con r30 ≤ 105 y r5 ≤ 56 | asym 300 s | +13,2 | [5,1; 21,7] | 1.015 / 21 |
| r30 ≤ −352 (el precio corrió **en contra**) y lejos de un hueco DWELL | sig 60 s | +12,1 | [3,7; 22,6] | 68 / 15 |

- **Lado espejo, a modo descriptivo:** si el precio ya corrió a favor (r30 > 84), la absorción da **en contra**: −24,5 ticks [−36,6; −13,5] cerca de un extremo.
- **Lectura:** la absorción parece aportar dirección **sólo cuando el precio todavía no se movió hacia donde ella apunta**. Si ya se movió, marca agotamiento.
- **Advertencia fuerte:** la etapa 1, con los terciles pre-listados de C5 (±0,5σ), **no** lo ve (todos los IC cruzan 0). Por eso es una sugerencia débil: sale de una sola mitad de sesiones y el corte no coincide con la discretización declarada.

**Sugerencias para `P-NQL2-CONF`** (PROPOSED/LOW): **SUG-NQ-SYN-B-1…3**. Antes de abrir la reserva hay que firmar un protocolo con los cortes congelados (los de la hoja) y un solo canal y horizonte primario.

**Qué sugieren medir (el objetivo del pedido):**
1. **Tendencia de 30 min × absorción**, como contexto de agotamiento o continuación. Candidata natural a filtro de dirección.
2. **Zona HFT gastada × absorción**, como predictor de **baja volatilidad** (tamaño o stop, no entrada).
3. **Nada** en los contextos C3, C4, C6, C7, C8, C9, C11 y C12 a esta potencia. No se descartan: no hubo potencia para verlos.
