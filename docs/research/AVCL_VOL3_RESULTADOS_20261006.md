# AVCL-VOL-3 — resultados MNQ — 2026-10-06

- Manifiesto: `AVCL_VOL3_ROBUSTEZ_MANIFIESTO_20261006.md`. Kernel `edgelab-avcl-vol3-20261006`, 229 s, sobre el cache
  de VOL-2.
- JSON: `avcl_vol1_20261005/AVCL_VOL3_RESULTADOS.json`. 8 pruebas más en el registro.
- Nota de procedimiento: el manifiesto decía que se presentaba antes de correr, pero se lanzó directo con el "Si" de
  Nico a lanzarlo.

## Formal (8, Holm, bilaterales): las 8 significativas
| prueba | AT | OFF |
|---|---|---|
| H-a dosis: pendiente por 1 SD de log `anomaly_ratio` (`y_rg` H10) | **+0,014** (Holm 1e-4) | **+0,021** (Holm <1e-4) |
| H-c compresión `y_rv` H50 | −0,027 | −0,021 |
| H-c compresión `y_rv` H200 | −0,042 | −0,034 |
| H-d ETH `y_rg` H10 | +0,063 | +0,046 |

## Dosis-respuesta, por quintil de anomaly_ratio (β `y_rg` H10, RTH)
| quintil (mediana del ratio) | AT | OFF |
|---|---|---|
| Q1 (≈1,02) | 0,066 | 0,027 |
| Q2 (≈1,06) | 0,064 | 0,037 |
| Q3 (≈1,10) | 0,085 | 0,057 |
| Q4 (≈1,17) | 0,092 | 0,067 |
| Q5 (≈1,28) | 0,098 | **0,087** |

Es monótona. En OFF el efecto se **triplica** de Q1 a Q5: es la prueba mecanística de que el efecto es de la
anomalía detectada.

Otras dosis (descriptivas, por 1 SD):
- **Ancho de zona: −0,075 (AT) y −0,067 (OFF). Cuanto más angosta la zona, más expansión.** Es el modulador más
  fuerte.
- `cluster_share` +0,02 y densidad +0,02.
- `quality_score`: +0,012 en AT y **−0,020 en OFF**. El puntaje de calidad del indicador no sirve para ordenar esto en
  OFF.
- Ráfaga (`burst_count`) −0,01: las zonas aisladas expanden más que las que llegan en ráfaga (AT 0,089 contra 0,071).

## Estabilidad (descriptivo)
- Por contrato: AT entre 0,067 y 0,097, OFF entre 0,044 y 0,068. **Los 6 contratos tienen el mismo signo y orden de
  magnitud.**
- Por franja RTH: AT 0,085 / 0,072 / 0,089 (apertura / mediodía / cierre). Estable.
- SE sesión × hora ≈ SE sesión: la inferencia no depende del nivel de clusterización.

## Magnitud contra costo (H-l)
- Exceso de rango a 10 barras: **AT +2,0 ticks, OFF +1,4 ticks** (sobre un rango previo de unos 24 ticks).
- A 50 barras: +0,6 / +0,2.
- El costo de ida y vuelta en MNQ es de unos 5,8 ticks. **En promedio el exceso no paga el costo.** Si llegara a
  servir, sería en la cola de alta dosis (Q5, zona angosta) o con instrumentos/barras más grandes.

## Lectura
La expansión post-zona es **real, propia de la zona, monótona en la intensidad de la anomalía, estable entre contratos,
franjas y ETH, y seguida de compresión**. En promedio es chica en ticks.

Falta (decidido con Nico): la **distribución completa del desplazamiento con signo**. SR-DIR midió sólo la media del
canal direccional, y una media ≈ 0 puede esconder colas engordadas hacia los dos lados (las capturas de Nico muestran
alejamientos grandes). Va como prueba formal en la próxima corrida.
