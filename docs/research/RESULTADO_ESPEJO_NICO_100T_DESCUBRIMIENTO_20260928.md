# ESPEJO-NICO-100T — resultado del descubrimiento (2026-09-28)

**Veredicto: SIN EFECTO DETECTADO. 0 de 8 pruebas primarias sobreviven (BH q = 0,10). No hay celdas para replicar.**
Corrido con el OK de Nico (28/09) sobre el manifiesto `MANIFIESTO_ESPEJO_SEMEJANZA_NICO_100T_20260928.md` con la
enmienda N1 (nulo simulado). Código `tools/espejo_nico_descubrimiento.py`, commit `95d676e7`; el árbol figura dirty sólo por
archivos sin trackear ajenos a la corrida (`tools/apply_viewer_*.py`, `tools/run_h2_and_suspend.ps1`). Artefactos:
`artifacts/espejo/nico_100t/{eventos,reporte}.json`.

**Datos:** ES, research-v2 (Lucid), 181 sesiones jul-2025 → mar-2026, velas 100t (4 × 25t dentro de la sesión).
1.942 eventos (x = 0,50 y 0,75), todos con nulo estimable. Primario sobre midquote.

## Pruebas primarias (exceso = completa − p0; IC 90 % bootstrap por sesión)
| Prueba | x | Estrato | n (más / menos) | Estimado | IC 90 % | p | MDE 80 % |
|---|---|---|---|---|---|---|---|
| P1 | 0,50 | TBZ | 265 / 187 | +0,040 | [−0,027; +0,103] | 0,17 | 0,10 |
| P2 | 0,50 | TBZ | | +0,040 | [−0,051; +0,127] | 0,24 | 0,13 |
| P1 | 0,50 | otros | 114 / 191 | +0,069 | [−0,001; +0,135] | 0,054 | 0,10 |
| P2 | 0,50 | otros | | −0,033 | [−0,106; +0,048] | 0,77 | 0,12 |
| P1 | 0,75 | TBZ | 185 / 156 | 0,000 | [−0,053; +0,045] | 0,52 | 0,07 |
| P2 | 0,75 | TBZ | | −0,035 | [−0,117; +0,043] | 0,79 | 0,12 |
| P1 | 0,75 | otros | 84 / 113 | −0,075 | [−0,159; +0,008] | 0,93 | 0,13 |
| P2 | 0,75 | otros | | −0,071 | [−0,188; +0,033] | 0,89 | 0,16 |

## Lectura
- **La semejanza «a lo Nico» no ordena el desenlace.** P2 (más parecido − menos parecido) es negativa en 3 de 4 celdas.
  Lo que refutaba la hipótesis según el manifiesto (el tercil más parecido no supera al menos parecido) es lo que se observa.
- P1 x=0,50 «otros» (+0,069, p 0,054) no sobrevive a la corrección y **no es de semejanza**: el tercil menos parecido completa
  más todavía (0,576 contra p0 0,475). Es un descriptivo del estrato, no del mecanismo; no se promueve ni se rescata.
- **Potencia:** MDE 0,07–0,16. Un efecto de semejanza menor que eso no se puede descartar; lo que queda descartado es uno
  del tamaño necesario para cubrir la fricción de ES (≈ 0,064 sobre p0) en x = 0,75 TBZ, la celda con más potencia
  (IC superior +0,045).
- **Censura:** la observada queda por debajo de p0 en casi todas las celdas (p. ej. x=0,50 otros: 0,06–0,12 contra
  0,13–0,18). El mercado resuelve antes que el paseo sin memoria: descriptivo, no contado en la multiplicidad.
- Trade contra midquote: mismas conclusiones (completa por trade 0,01–0,04 más alta, el rebote del precio de trade).

## Alcance de la muerte
Muere exactamente: «las vueltas más parecidas según el modelo congelado (73 % de acuerdo con Nico) completan el espejo más
que el nulo y más que las menos parecidas», en ES 100t, impulso ≥ 34 t, evento al cierre en x = 0,50/0,75, horizonte 3×,
datos Lucid jul-25 → mar-26. **No** muere: la semejanza juzgada por Nico (el modelo acierta 73 %, no 100 %), otras escalas,
otros instrumentos, ni el espejo como fenómeno (ESPEJO-SIM/MACRO son familias aparte).
Pendiente de la auditoría 056 que no cambia esto: refit sin los 2 gráficos contaminados (sensibilidad del score).

**Aporte al referente:** se descartó con nulo correcto y potencia publicada que la forma de la vuelta, tal como se la midió,
sea una señal operable en ES; el presupuesto no se gasta en replicarla.
