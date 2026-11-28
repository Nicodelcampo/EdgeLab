# ESTABILIDAD-CARTERA: la caída del final, mitigaciones declaradas, estrategias que podrían sumar estabilidad y corridas a lanzar (pre-registro, 2026-11-26)

Estado: PRE-REGISTRO — descriptivo y de selección declarada; se commitea y se cuenta antes de calcular.
- **Pedido de Nico (2026-11-26):** «hay muchas inestables, y de las estables muchas tienen una caída al final. ¿Esa caída es mitigable?
  Indagá. Quiero que las carteras tengan la mayor estabilidad posible y la mayor probabilidad de seguir comportándose como en el pasado.
  Fijate si hay otras estrategias descartadas o en revisión que podrían sumar estabilidad, y si hay corridas que valen la pena lanzar».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2.** **Familia:** `CANASTA_CORRELACION`.
- **Herramienta:** `tools/estabilidad_cartera.py` (llama a `registro_global.exigir_contada`).

Cambio respecto a falla previa: no repite ninguna regla NO_REPETIR. Usa series ya medidas y evalúa las mitigaciones walk-forward sobre toda la
historia, no sobre la caída que motivó la pregunta.

Antecedentes:
- `carteras_locales_correlacion_20261126/RESULTADO.md` (adendas 2 y 3).
- `cartera_nt8_20261125/RESULTADO.md` §2: escalar según colchón o volatilidad empeoró en Lucid, y 1/N es difícil de batir (DeMiguel et al.
  2009; Cederburg et al. 2020).
- FACTORES: F-REVERSION-CORTA-APAGADA-2018, F-COMPRESION-VOL-CRECE, F-FRANKLIN-OTROS-INDICES, F-Z-TRANSFER-RTY, F-FS-IL-REMEDICION-V-CANDIDATA.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 todo en USD con 1 micro, K49 un nulo sin potencia no mata, K56 episodios).

Potencia previa: no aplica a una prueba única. Las mitigaciones se juzgan por el cambio en Sharpe mensual y en caída máxima walk-forward;
con ≈ 75 meses, una diferencia de Sharpe anual < 0,4 no se distingue del ruido, y se publica así.

Diagnóstico de mecanismo: no aplica (sin grilla de perillas). Hay 3 mitigaciones fijas y un tamiz de candidatas con un criterio fijo.

## Justificación económica
- Una caída común a todas en el mismo tramo es un factor de mercado. Ni un filtro por estrategia ni el tamaño la evitan; la evita sumar algo
  que no dependa de ese factor.
- Una caída propia de una estrategia puede ser ruido, que se recupera, o una pérdida de ventaja, que no. Sólo el forward lo distingue.

## Qué se calcula (fijo)
Datos: USD por día con 1 micro, neto de la fricción canónica del micro, 2019-07 → 2026-09 (todas las particiones; el terminal no está
abierto). Fuentes ya medidas:
- la matriz de `cartera_nt8_20261125`;
- la re-medición de FundedSync con la traducción corregida;
- SOM y Franklin en otros índices (`m1_largo_20261117`);
- RQ5 en YM y RTY;
- Carril 2: corridas NT8 de C2_VZ/C2_EVRP hasta 2026-09; el resto de definiciones, sólo hasta 2025-07, marcadas.

**A. La caída del final (descriptivo).** Para cada estrategia de INTRADIA8 e INTERDIA3:
- la caída desde su máximo de 2026 hasta el 2026-09-30;
- el percentil de esa caída entre todas las caídas de su historia;
- la duración;
- la correlación de los P&L diarios entre estrategias en ese tramo frente al resto (¿es un factor común?);
- el retorno y la volatilidad de NQ en el tramo.

**B. Mitigaciones (fijas, walk-forward mensual, sólo información pasada; evaluación 2020-07 → 2026-09):**
- M0: pesos iguales (1 micro cada una, la línea base);
- M1: inverso de la volatilidad diaria de 63 días, normalizado a la misma volatilidad total que M0;
- M2: freno por curva: una estrategia se pausa el mes siguiente si su P&L de los últimos 3 meses (sombra) es < 0, y vuelve cuando lo es ≥ 0;
- M3: poda: fuera el mes siguiente si su t de los últimos 12 meses es < 0.

Se publican Sharpe anual, caída máxima, peor mes, % de meses positivos y el resultado en el tramo 2026-05 → 2026-09.

**C. Candidatas.** Cada serie de las fuentes que no esté ya en la cartera base, más las de INTERDIA3 sumadas a INTRADIA8 y viceversa.
- **Se publica:** su t mensual, % de años positivos, correlación mensual con la base y cambio en Sharpe y en caída máxima al sumarla a 1 micro.
- **Criterio declarado de «aporta estabilidad»:** t propia ≥ 2, ≥ 70 % de años positivos, correlación con la base ≤ 0,3 y que no empeore la
  caída máxima de la base.
- **Advertencia:** todo esto se elige sobre datos ya vistos. La confirmación es el forward.

**D. Corridas a lanzar:** lista razonada, sin lanzar nada en este paso.

## Cómo podría refutarse
- La caída del final está dentro del rango histórico (percentil < 90) y es común a todas: es un tramo malo de mercado y no hay qué mitigar
  por estrategia.
- Ninguna mitigación mejora el Sharpe walk-forward en ≥ 0,2 con la caída máxima igual o menor: no se adopta ninguna.
- Ninguna candidata cumple el criterio C.
