# Pre-registro — tope de stop de U1-CRUZADO y densidad del feed (2026-10-23)

Estado: VIGENTE — registrado antes de correr. OK de Nico en el chat («Si») a los dos pasos que quedaban antes del holdout
(`REVISION_ERRORES_Y_PLAN_U1_CRUZADO.md`; el resultado del fuera de muestra está en `PREREGISTRO_INTEGRIDAD_Y_OOS_U1_CRUZADO.md`).

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Kernel `tools/kaggle_grilla/kernel_u1_cruzado.py`, modos `TOPES` y `DENSIDAD`. Tope: `u1_cruzado.aplicar_tope`.

## A. Densidad del feed (target-free, sin P&L)
- **Qué se mide** (USATECH 2023-01 → 2026-09):
  - por día: ticks, minutos con datos, velas M1 con hueco (OG/VI) y rango del día;
  - por trimestre: señales U1.
- **Pregunta:** el salto de ≈ 5 a ≈ 20 señales por mes, ¿acompaña a la volatilidad (mercado) o a la densidad del feed (ticks o
  minutos por día, sin cambio de rango)?
- **Lectura fijada:**
  - si las señales por mes siguen al rango del día y no a los ticks por día, es mercado;
  - si siguen a los ticks y no al rango, es feed: riesgo de que U1 dependa de cómo cotiza Dukascopy, y la paridad con el feed en
    vivo pasa a ser bloqueante.

## B. Tope de stop (sólo con datos ya usados)
- **Variantes** (`u1_cruzado.TOPES`): sin tope; tope en puntos 50 / 75 / 100 / 150; tope en múltiplos de la distancia al objetivo
  2× / 3× / 4×. Cada una con T1 y T3: 14 pruebas nuevas, `u1_cruzado/topes`.
- **Datos:**
  - **Para elegir:** NQ con la señal del CFD, desarrollo 2025-08 → 2026-03 (P1) y 2026-04 → 09 (P2).
  - **Sólo informativo:** USATECH 2023-01 → 2025-07, ya visto, con los mismos topes. No se usa para elegir.
- **Regla de elección (fijada ahora):**
  1. **Elegibles:** variantes con media neta > 0 en P1 y en P2, y en cada período al menos el 50 % de la media sin tope de esa
     misma ejecución.
  2. **Orden:** por P&L total de P1 + P2 dividido por |drawdown máximo| de P1 + P2 (retorno sobre drawdown).
  3. **Desempate:** el tope más amplio (menos ajuste), y T1 antes que T3.
  4. **Resultado:** UNA regla congelada (ejecución y tope) para el holdout. Si ninguna es elegible, no hay holdout: se informa.
- **Lo que no se hace:** elegir con 2023–2025, ni cambiar la grilla de topes al ver resultados.
