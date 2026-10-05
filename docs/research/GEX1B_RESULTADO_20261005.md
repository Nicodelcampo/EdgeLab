# GEX-1b — resultado (2026-10-05)

Pre-registro: `GEX1B_PREREGISTRO_20261005.md` (commit `4730ed62`, antes de correr). Resultados crudos: `GEX1B_RESULTADOS_20261005.json` (kernel `nicolasbuttaro/edgelab-gex1b-20261005`, 128 s). Mismas fuentes que GEX-1: MES NT8 (248 sesiones; **8 sesiones omitidas por falta de fuente** y 50 leídas de una alternativa consistente, ver `GEX1_EJECUCION_KAGGLE_20261005.md`) y spot USA500 (757 sesiones). Holm sobre **24** pruebas, 20.000 permutaciones en bloques de 20, semilla 20261007, unilateral. Solo información.

## Potencia ganada
Con el percentil 20 hay **14 sesiones «bajas» en MES** (antes 9) y **87 en el spot** (antes 39). La definición continua usa todas las sesiones.

## Pruebas con Holm ≤ 0,05 (todas en el spot, signo esperado)
| Definición | Métrica | Estadístico | p | Holm |
|---|---|---:|---:|---:|
| Continua | **I1b** (desvío de r5 / σ previo) | +0,161 | 0,00015 | **0,0036** |
| Continua | **I1a** (rango / rango previo) | +0,135 | 0,0006 | **0,0138** |
| Continua | **ac1** (autocorrelación lag-1 de r5) | +0,105 | 0,0010 | **0,0220** |
| Cuantil 20 | **I1b** | +0,342 | 0,0010 | **0,0220** |

Casi pasa (Holm 0,054): spot cuantil I1a (+0,345) y **MES continua ac1abs (+0,173)**.

## Lectura
1. **Más amplitud con menos gamma, confirmada con más potencia.** En el spot, I1a e I1b pasan con la gamma continua y I1b también con el cuantil: menor gex_{t-1}, mayor rango y desvío intradía respecto de los 20 días previos, también tras controlar por σ previo (+0,20 a +0,47 según métrica y definición). En MES el signo coincide (+0,12 a +0,18) y sin pasar (Holm 0,6 a 1,0): con 14 sesiones bajas el MDE sigue siendo 0,5 a 0,6.
2. **Autocorrelación (ac1) en el spot** sube con menos gamma (+0,105, Holm 0,022); en MES también es positiva (+0,07 a +0,10) sin pasar. Es un resultado nuevo respecto de GEX-1, que no lo mostraba.
3. **Inconsistencia en ac1abs:** en MES es positiva y casi pasa (+0,17); en el spot es **negativa** (−0,05 y −0,16, p ≈ 1). No hay un patrón común en la autocorrelación de los retornos absolutos.
4. **Continuación de cierre (I2n, I2d): nada** en ninguna fuente.
5. **Límites.** No son pruebas independientes de GEX-1 (mismos días) ni entre Q y C. El resultado más sólido sigue siendo el de amplitud en el spot; en futuros MES no hay potencia suficiente. Para ganar potencia de verdad hace falta un histórico más largo del S&P intradía (días de gamma negativa se concentran en 2018-2022: no están en los datos actuales), no otra definición.
- Contador global de pruebas: +24.
