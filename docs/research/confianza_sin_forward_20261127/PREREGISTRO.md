# CONFIANZA-SIN-FORWARD: subir o bajar la confianza en Carril 2 con datos que nadie miró (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO — antes de calcular cualquier R. Lo único mirado: calidad de datos y cantidad de señales (sin retornos).

- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (réplica externa en mercados y períodos no usados). **Familia:** `CARRIL2_CONFIANZA` (hija de `CARRIL2_A5`).
  **Pruebas:** 3 (H1, H2, H3); el resto es diagnóstico.
- Pedido de Nico: «de qué manera, habiendo visto los datos, se puede aumentar o descartar la confianza de cada estrategia sin ir a
  forward, y ejecutar esos análisis».

Cambio respecto a falla previa:
- Carril 2 sólo se midió en futuros de EE. UU. y oro (ES, NQ, YM, RTY, GC) desde 2006, y su HOLDOUT A5 ya está abierto (t 2,42).
- Lo que no se probó:
  1. si las mismas reglas, sin tocarlas, ganan en **mercados donde EdgeLab nunca las corrió**;
  2. si ganaban **antes de 2006**, en EE. UU.;
  3. si la ventaja es de la **señal** o sólo de estar comprado en índices que subieron (deriva).
- Son las tres vías que la literatura usa para validar sin datos nuevos:
  - réplica fuera de mercado y de período (Falck, Rej y Thesmar 2021, arXiv 2105.01380: el Sharpe fuera de la muestra queda en
    ≈ 0,57 del original y entre 50 % y 75 % en otros mercados);
  - controles de placebo;
  - corrección por la cantidad de pruebas (Bailey y López de Prado, Sharpe deflactado; Harvey, Liu y Zhu, t ≥ 3).

Antecedentes:
- `canasta_amplia_20261127/RESULTADO.md` (Carril 2: DESC+REP Sharpe 0,86);
- `holdout_a5_nocme_20261127/RESULTADO.md` y `REVISION_CLAUDE.md` (HOLDOUT A5: Sharpe 1,06, t 2,42);
- `carril2_20261119/PREREGISTRO_LOTE1.md` y `PREREGISTRO_LOTE2.md` (reglas y controles N);
- `F-CANASTA-CARRIL2-HOLDOUT-A5`.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7:
- K32: todo con EdgeLab, motor `sqx_catalogo.simular` calibrado y reglas de `carril2.py` sin cambios;
- K34: costos estimados y declarados;
- K35–K39: R por operación sobre el riesgo inicial;
- K36: señal al cierre de t, entrada a la apertura de t+1.

Potencia previa:
- Efecto esperado: Sharpe anual de la canasta 0,86 con un recorte de 50 % por cambio de mercado → 0,43 (mensual 0,124).
- H1: ≈ 441 meses (1990-01 → 2026-09) → t esperada 2,6, potencia ≈ 0,83 (0,97 con el efecto completo).
- H2: 192 meses (1990 → 2005) → potencia ≈ 0,53 con el recorte y 0,96 con el efecto completo.
- H3: placebo en 249 meses; el tamaño de la diferencia regla − control no tiene antecedente; se publica con su error estándar.

Diagnóstico de mecanismo: sin grilla y sin perillas.
- Se usan las mismas cinco reglas de Carril 2 (IBS con régimen de VIX, Double 7, Turnaround Tuesday, cambio de mes, VBB) con sus
  stops, topes y salidas.
- ROT queda afuera: es la razón ES/GC, propia de esos dos contratos.
- Cada regla corre junto a su control N, que tiene la misma exposición y la condición opuesta.
- Se publican por regla, por índice y por época, con costos ×2.

## Datos (descargados antes de este pre-registro; `data/confianza_sf/PROCEDENCIA.json` con sha256)
- **Diarios OHLC de Yahoo sin ajustar, cortados antes del 2026-10-01:**
  - extranjeros: DAX, FTSE, CAC, EuroStoxx 50, Nikkei 225, Hang Seng, ASX 200 y TSX;
  - EE. UU. cash: S&P 500, Nasdaq 100, Dow y Russell 2000;
  - ^VIX.
- **Calidad:** se descartan las barras con rango nulo. Cada índice empieza el primer mes desde el que ≥ 95 % de las barras tienen
  rango: DAX 1997-06, EuroStoxx 2011-08, ASX 2000-04, TSX 2006-08 y el resto 1990–1992.
- **VIX:** el de EE. UU. para todos los índices, como en la regla original.
  - IBS usa el régimen VIX(t−1) > SMA100.
  - VBB usa el VIX del cierre de t; la entrada es a la apertura siguiente del índice, posterior a las 16:15 de NY.
- **Costos:** ESTIMADOS y declarados, porque no hay componente canónico para estos índices: 3 pb ida y vuelta de base y 6 pb de estrés.
  Como referencia, ES canónico hoy ≈ 1,3 pb.
- **Motor:** `sqx_catalogo.simular` sin M1. Es el peor caso: si el rango de la barra de entrada toca el stop, sale por stop, y el stop
  va antes que el objetivo.

## Hipótesis y lectura (decididas antes)
Medida común: suma mensual del R de cada serie (regla × índice) y promedio entre las series con datos ese mes, en pesos iguales.

| Prueba | Universo | CONFIRMA |
|---|---|---|
| **H1** transferencia | 5 reglas × 8 índices extranjeros, desde su inicio con calidad hasta 2026-09-30 | t mensual de una cola ≥ 1,645 con 3 pb |
| **H2** período anterior | 5 reglas × 4 índices de EE. UU. cash, 1990-01 → 2005-12-31 | t ≥ 1,645 con 3 pb |
| **H3** placebo | Canasta sellada de 16 (pesos fijos), regla − su control N, 2006 → 2026-09 en DESC, REP y HOLDOUT | t ≥ 1,645 de la diferencia mensual |

- **Resultados posibles:** NO_CONCLUYENTE si la media es > 0 y t < 1,645; EN_CONTRA si la media es ≤ 0.
- **Familia:** BH q 0,10 sobre las 3 pruebas.
- **Advertencias declaradas:**
  - H2 es la muestra con la que se publicaron varias de estas reglas (Connors, 1993–2008). Si da a favor, suma poco; si da en contra,
    resta mucho.
  - H3 lee los meses HOLDOUT de `CARRIL2_A5`, cuya única apertura ya se hizo. No es una apertura nueva ni elige nada; es la auditoría
    del resultado ya abierto.
- **Descriptivo, sin pruebas nuevas:** Sharpe deflactado (Bailey y López de Prado) y p con Bonferroni por las pruebas contadas de cada
  familia, para todas las estrategias vigentes (`DSR_HAIRCUT.json`).

## Justificación económica
- Las reglas de Carril 2 explotan reversión de corto plazo, efectos de calendario (cambio de mes) y primas de volatilidad. Esos
  mecanismos los generan flujos de inversores (rebalanceo, pagos de fin de mes, cobertura) que existen en todos los mercados de
  acciones grandes.
- Si la ventaja es del mecanismo, tiene que aparecer, más chica, en índices extranjeros y en otro período, y superar a su control
  con la misma exposición.

## Cómo podría refutarse
- **Transferencia:** H1 con media ≤ 0, o positiva sólo por un índice o una época, deja a Carril 2 como un efecto de los futuros de
  EE. UU. en 2006–2026. Esa es la clase de resultado que la literatura muestra que se borra.
- **Placebo:** H3 con diferencia ≤ 0 significa que la canasta gana por estar comprada (deriva), no por la señal. En ese caso, el
  mismo resultado se consigue más barato comprando y manteniendo el índice.
