# Resultados M10 + M10b — LUX-IMB en MYM, GC, 6E, 6B, 6J, MBT (descubrimiento)

Estado: MEDIDO. Veredicto: **NADA TRANSPORTA; el unico efecto fuerte (H3) era "precio ya visitado"**.
Manifiesto `MANIFIESTO_M10_MULTIACTIVO_LUXIMB_20261020.md` (+ enmienda M10b escrita antes del control). Codigo
`luximb_m10.py`, `luximb_m10b.py`, `m10_construir.sh`; salidas `RESULTADOS_M10.json`, `RESULTADOS_M10B.json`.

## M10 (combinado de 6 activos, inverso de la varianza; Holm sobre 3)
| hipotesis | combinado | IC 95 % | mismo signo que NQ | transporta |
|---|---|---|---|---|
| H1 otro lado vacio tras vuelta rapida (M9) | +1,8 pp | [-0,2, +3,7] | 4/6 | no (Holm 0,17) |
| H2 inicio cargado vs control (M5) | +0,8 pp | [-0,9, +2,5] | 3/6 | no |
| H3 desbalance adelante-atras vida 200 (M8) | **-4,7 pp** | [-6,4, -2,9] | **0/6** | no (signo opuesto a NQ) |

## M10b — H3 controlando cobertura previa (precio ya visitado en las 500 velas previas)
Cobertura media de la franja adelante: grupo "adelante" 0,96-0,99 vs grupo "atras" 0,35-0,51 en todos los activos: tener
zonas adelante es casi sinonimo de que el precio ya opero ahi.
| activo | H3 sin control | H3b con control de cobertura |
|---|---|---|
| MYM | -0,8 pp | +0,8 [-6,6, +10,3] |
| GC | -9,5 | -4,8 [-14,7, +2,6] |
| 6E | -5,0 | -5,1 [-13,9, +4,0] |
| 6B | -4,2 | +4,4 [-4,1, +11,4] |
| 6J | -6,1 | +0,2 [-8,5, +7,6] |
| MBT | 0,0 | +8,1 [-7,9, +15,7] |
| **combinado 6 activos** | **-4,7 [-6,4, -2,9]** | **+0,2 [-3,4, +3,8]** (p 0,91) |
| NQ (descriptivo) | +2,9 | +9,5 [+0,4, +15,9] |
| ES (descriptivo) | -0,5 | +0,8 [-5,8, +6,0] |

## Lectura
- El -4,7 pp de M10 era **confusion por precio ya visitado** (impulsos que vuelven a un rango previo siguen mas), no un
  efecto de las zonas: con el control, el combinado cae a +0,2 pp con IC simetrico alrededor de 0.
- Es la tercera vez en la familia que un "efecto de zonas" resulta un proxy (M7 -> volatilidad; M10 -> precio visitado).
  **Regla para cualquier familia de zonas**: controlar volatilidad previa y cobertura previa antes de atribuir efecto.
- El +9,5 pp de NQ con control es un solo activo, descriptivo, y signo distinto al resto: no se interpreta.

## Estado de la familia
Con M1-M11 (14 mediciones, 9 activos) ninguna senal de LUX-IMB (OG+VI) sobrevive. Recomendacion: **cerrar la familia en
su definicion actual**. Replicaciones abr-sep y holdout intactos para todos los activos.

Aporte al referente: descarta con 6 activos el ultimo efecto fuerte de la familia (era precio ya visitado) y deja una
regla de control reutilizable para cualquier indicador de zonas.
