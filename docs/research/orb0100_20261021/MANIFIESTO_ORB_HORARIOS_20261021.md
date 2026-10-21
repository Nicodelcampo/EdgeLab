# Manifiesto ORB-HORARIOS — barrido de horarios del rango de 15 min en 8 activos, con embudo de confirmacion

Estado: PRE-REGISTRADO antes de correr. Pedido de Nico 2026-10-21: "hace pruebas en distintos horarios (muchos) y en los que
salgan buenos aplicales todo lo necesario para confirmarlos o descartarlos". Familia NUEVA (ORB-HORARIOS), distinta de ORB0100
(cuya replicacion ya se uso); la ventana 01:00 se reporta pero queda marcada como contaminada.
Referente sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

## Barrido (descubrimiento: sesiones hasta 2026-03-31)
- Activos: NQ, ES, MYM, GC, 6E, 6B, 6J, MBT (costos propios, como V2).
- Ventanas: rango de 15 min que empieza cada 30 min desde las 18:00 ET hasta las 15:30 ET (**44 ventanas**). Entrada: primera
  vela de 5 min que cierra fuera del rango; salida forzada 6 h despues del fin del rango o a las 16:55 ET, lo que ocurra antes.
- Reglas (2): **R0** = original (TP 0,5R, sin filtro); **R1** = TP 1,5R + VWAP a favor. SL otro lado del rango, mercado +1 tick.
- Total: 44 x 2 x 8 = **704 celdas**. Metrica: R neto por operacion. IS = 2025, OOS = 2026 T1.

## Embudo (fijado ahora)
1. **Cribado**: celda "buena" si R/op > 0 en IS **y** en OOS, n >= 60 en descubrimiento, y p (bootstrap del descubrimiento
   completo) supera **Benjamini-Hochberg al 10 %** sobre las 704 celdas.
2. **Confirmacion** de cada buena (debe pasar todas):
   a. Robustez de costo: con 1 tick extra por lado sigue > 0.
   b. Vecindad: al menos una ventana vecina (+/- 30 min, misma regla y activo) tambien con R/op > 0 en descubrimiento.
   c. Nulo de direccion: mismas entradas con direccion aleatoria (2.000 sorteos): p < 0,05.
   d. Sin dependencia de pocos dias: quitando el 5 % de mejores dias sigue > 0.
3. **Replicacion abr-sep 2026** (una vez por celda que pase 1-2, con OK de Nico antes de usarla).
Se publican las 704 celdas. Nada se elige fuera de estas reglas.
## Justificacion economica
Algunas aperturas (Asia, Londres, datos de 8:30, cash 9:30) concentran flujo informado; una ruptura del primer rango podria
tener continuacion en esas ventanas y no en otras.
## Como podria refutarse
Ninguna celda pasa el cribado, o ninguna pasa la confirmacion.
