# Exploratorio sin resultados: escalonadas 150t sobre area cargada de OG/VI (NQ 09-26)

Estado: MEDIDO (descriptivo, target-free; nada posterior a la deteccion). Fecha 2026-10-20.
Definicion: `luximb_escalonadas.py --ticks 150 --max-step 42 --min-pull 14 --conf 16 --min-zonas 3` (detector
`escalonadas_det.detectar_px`, familia IPC-NQ, nmin 5, velas 150t = 6x25t). Salida `bundles/peaks_det/NQ_09-26_M1_LUXIMB__luxesc150.json`.
Ojo: disenada mirando NQ 09-26 (replicacion HOLDOUT-A3); desenlaces, si se miden, solo en descubrimiento.

| medida | p10 | p50 | p90 |
|---|---|---|---|
| area recorrida hasta detectar (pts) | 28 | 44 | 66 |
| minutos del 1.er pico a la deteccion | 1,9 | 9,6 | 68 |
| desplazamiento 1.er -> 5.o pico (pts) | 10,5 | 17,6 | 25,7 |
| zonas vivas en el area | 3 | 5 | 14 |
| densidad (zonas cada 10 pts) | 0,67 | 1,32 | 2,87 |
| fraccion OG | 0 | 0,25 | 0,50 |
| fraccion de zonas "a favor" (BEAR en techos, BULL en pisos) | 0,20 | 0,50 | 0,75 |
| edad de zonas (min) | 25 | 211 | 452 |
| alto de zonas (ticks) | 1 | 4 | 9 |

- 182 en 53 dias (max 9/dia), 36 a < 30 min de la anterior. 98 techos (picos descendentes), 84 pisos.
- Se detectan casi siempre al 5.o pico (121 de 182); hay series largas de hasta 22 picos.
- Horario NY: 55 entre 9:30 y 11; 45 entre 12 y 16 (a diferencia de los impulsos, aparecen tambien en la tarde cash); 20 de 17 a 24.
- Las zonas se reparten parejo en el area (posicion p25/p50/p75 = 0,27 / 0,48 / 0,71): no se concentran en el borde.
- Mitad de las zonas a favor, mitad en contra del escalonamiento: la carga no tiene signo.

## Candidata a medir con P&L (requiere OK; descubrimiento NQ 09-25..06-26/31-mar)
- **M6:** desde la deteccion, carrera entre romper el area a favor del escalonamiento (techos: bajo area_lo; pisos: sobre
  area_hi) y superar el ultimo pico en contra. P(ruptura) y P&L neto de seguirla, contra **control**: escalonadas de la
  misma configuracion con 0-2 zonas en el area. Separa "efecto de zonas" de "efecto de escalonada".
- Dos canales (ruptura y rechazo) + MFE/MAE. Estratos: techo/piso, cash vs resto, densidad alta/baja. ~6 hipotesis, Holm, MDE.
- Como podria refutarse: T - C sin diferencia con MDE <= 10 pp, o P&L neto <= 0.

Aporte al referente: describe la poblacion nueva sin tocar resultados y deja el contraste contra escalonadas sin zonas listo.
