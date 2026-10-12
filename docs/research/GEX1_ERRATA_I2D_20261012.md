# GEX-1: erratum del p de MES `I2d` (estadístico no evaluable)

**Error:** en MES (9 sesiones de gamma negativo) el estadístico `I2d` es NaN (pendiente sin datos suficientes), pero el script de GEX-1 comparaba `nulo >= NaN` y devolvía p = 0,0001 y Holm 0,0007–0,0009. Ese p **no es válido** y MES `I2d` **no se evaluó**. GEX-1b ya lo trataba bien (no evaluable).

**Corrección (2026-10-12):** `tools/gex1_run_kaggle.py` ahora marca `evaluable=false`, `p=None`, y no lo incluye en el ranking de Holm; el denominador sigue siendo 12 (las pruebas planeadas). Los resultados publicados no se reescriben: los Holm corregidos se recalcularon desde los JSON guardados, sin volver a correr.

**Efecto:** ninguna conclusión cambia. Sin el p inválido, los Holm de las demás pruebas suben apenas (el p inválido les quitaba un lugar en el ranking). Con USA500 desde 2018, `I1a`, `I1b` e `I2n` siguen pasando Holm (0,0006; 0,0006; 0,0015); con la ventana 2023+, `I1a` 0,0148 e `I1b` 0,0060. Ninguna prueba de MES pasa.

### GEX1_RESULTADOS_20261006_COMPLETO.json
| fuente | prueba | p | Holm publicado | Holm corregido (12, sin I2d NaN) |
|---|---|---:|---:|---:|
| MES_NT8 | I1a | 0.0744 | 0.5952 | 0.6696 |
| MES_NT8 | I1b | 0.2399 | 0.6957 | 0.9276 |
| MES_NT8 | I2n | 0.1139 | 0.6837 | 0.7976 |
| MES_NT8 | ac1 | 0.0883 | 0.6181 | 0.7064 |
| MES_NT8 | ac1abs | 0.1250 | 0.6837 | 0.7976 |
| MES_NT8 | I2d | 0.0001 | 0.0009 | no evaluable |
| USA500_spot | I1a | 0.0013 | 0.0135 | 0.0148 |
| USA500_spot | I1b | 0.0005 | 0.0055 | 0.0060 |
| USA500_spot | I2n | 0.1304 | 0.6837 | 0.7976 |
| USA500_spot | ac1 | 0.2319 | 0.6957 | 0.9276 |
| USA500_spot | ac1abs | 0.9802 | 0.9802 | 1.0000 |
| USA500_spot | I2d | 0.0308 | 0.2772 | 0.3080 |

### GEX1_USA500_2018_COMPLETO_20261006.json
| fuente | prueba | p | Holm publicado | Holm corregido (12, sin I2d NaN) |
|---|---|---:|---:|---:|
| MES_NT8 | I1a | 0.0744 | 0.5208 | 0.5952 |
| MES_NT8 | I1b | 0.2399 | 0.5697 | 0.7197 |
| MES_NT8 | I2n | 0.1139 | 0.5697 | 0.6837 |
| MES_NT8 | ac1 | 0.0883 | 0.5298 | 0.6181 |
| MES_NT8 | ac1abs | 0.1250 | 0.5697 | 0.6837 |
| MES_NT8 | I2d | 0.0001 | 0.0007 | no evaluable |
| USA500_spot | I1a | 0.0000 | 0.0006 | 0.0006 |
| USA500_spot | I1b | 0.0000 | 0.0006 | 0.0006 |
| USA500_spot | I2n | 0.0001 | 0.0013 | 0.0015 |
| USA500_spot | ac1 | 0.1147 | 0.5697 | 0.6837 |
| USA500_spot | ac1abs | 1.0000 | 1.0000 | 1.0000 |
| USA500_spot | I2d | 0.0535 | 0.4284 | 0.4819 |