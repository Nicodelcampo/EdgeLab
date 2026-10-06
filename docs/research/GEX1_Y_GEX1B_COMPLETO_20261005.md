# GEX-1 y GEX-1b con datos completos (2026-10-05) — corrida definitiva

Reemplaza a las corridas provisionales (`GEX1_EJECUCION_KAGGLE_20261005.md`, `GEX1B_RESULTADO_20261005.md`), que omitieron 8 sesiones de MES y leyeron 50 de una fuente alternativa. Esta vez el re-export está en Kaggle (23 parquet verificados por sha256) y el lanzador (`tools/kaggle_launch.py`, sin `--allow-missing`) comprobó que **todas** las sesiones aprobadas tienen su fuente primaria: **0 sesiones omitidas, 0 lecturas de alternativas**. Kernels `edgelab-gex1-20261006` (v6) y `edgelab-gex1b-20261005` (v2); resultados crudos `GEX1_RESULTADOS_20261006_COMPLETO.json` y `GEX1B_RESULTADOS_20261005_COMPLETO.json`. Scripts sin cambios de análisis (GEX-1: manifiesto; GEX-1b: `GEX1B_PREREGISTRO_20261005.md`).

## Qué cambió respecto de las corridas provisionales
- **Spot USA500: idéntico** (757 sesiones; no dependía del re-export).
- **MES: 256 sesiones** (antes 248): entran las 8 que faltaban. Sesiones con gex < 0: siguen siendo 9.

## GEX-1 (12 pruebas, gex_{t-1} < 0)
- **Spot:** I1a (rango/rango previo) Holm **0,0135** e I1b (desvío/σ previo) Holm **0,0055**: más amplitud con gamma negativa (+0,54 y +0,59). El resto sin señal.
- **MES:** ninguna prueba válida pasa (menor Holm 0,595). **`I2d` sigue dando estadístico NaN** (9 sesiones negativas) con un p falso de 0,0001: pendiente la decisión sobre cómo trata el manifiesto un NaN; no cambia las otras 11.

## GEX-1b (24 pruebas, Holm sobre 24)
| Fuente | Definición | Métrica | Estadístico | Holm |
|---|---|---|---:|---:|
| Spot | continua | I1b | +0,161 | **0,0036** |
| Spot | continua | I1a | +0,135 | **0,0138** |
| Spot | continua | ac1 | +0,105 | **0,0220** |
| Spot | cuantil 20 | I1b | +0,342 | **0,0220** |
- **Casi pasa:** spot cuantil 20, I1a (+0,345, Holm 0,056).
- **MES:** ninguna pasa. Con las 8 sesiones completas, `ac1abs` continua (+0,149) pasó de Holm 0,054 a **0,177**: el casi-resultado de la corrida provisional se debía a las sesiones faltantes y no se sostiene.
- Sin señal en la continuación de cierre (I2n, I2d) en ninguna fuente; `ac1abs` en el spot es negativa (−0,05 y −0,16).

## Lectura
La conclusión no cambia y queda más sólida: **más amplitud intradía con menos gamma en el spot del S&P**, que se sostiene con la gamma continua y el cuantil, y que en MES (futuros) tiene el mismo signo pero **no hay potencia** (9 y 14 sesiones bajas). Solo información, no una regla operable. Para ganar potencia hace falta más historia de gamma negativa (USA500 2018-2022, en descarga). Contador global: GEX-1b ya registrado (+24); esta repetición no agrega pruebas nuevas (misma familia pre-registrada).
