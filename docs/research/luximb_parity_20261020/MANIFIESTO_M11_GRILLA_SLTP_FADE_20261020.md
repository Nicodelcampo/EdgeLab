# Manifiesto M11 — grilla SL/TP/BE del fade "fin de caja -> inicio de zona" (exploratorio con IS/OOS)

Estado: PRE-REGISTRADO antes de correr. Pedido de Nico 2026-10-20: "proba algunas variantes, con mas sl, mas tp, break even,
menos sl, menos tp, IS y OOS" (tras la simulacion visual del visor). Referente sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

## Poblacion (la del visor)
Impulsos `--modo inicio --p-rango 60 --min-ini 3 --share-ini 0.5`, piso 60 pts en NQ (`desc_m5/imp_NQ_*`, sin control) y
1,3 x mediana en ES. **NQ 09-26 se excluye** (periodo de diseno y replicacion).
- **IS** = NQ 09-25 + 12-25 (ago-dic 2025). **OOS** = NQ 03-26 + 06-26 hasta 31-mar-2026. **Externo** = ES mismo periodo
  (09-25..06-26/31-mar). Todo descubrimiento HOLDOUT-A3.

## Operacion (fade hacia A)
- Entrada **realista**: cierre de la vela M1 de marca (E) con 1 tick en contra. Referencia **optimista** (entrar en X, sin
  costos) solo para comparar con el visor.
- Distancia de referencia D = |E - A| (si E ya paso A: sin operacion).
- **TP** = fraccion f_tp de D: {0,5; 0,75; 1,0 (= A); 1,25}. **SL** = fraccion f_sl del TP: {0,1; 0,2 (= visor); 0,33; 0,5; 1,0}.
- **BE**: sin / con (al recorrer el 50 % del TP, el stop pasa a la entrada).
- Velas 25t, tope 240 min o fin de sesion (cierre a mercado +1 tick). Misma vela toca SL y TP -> SL. BE se actualiza al cierre
  de la vela que lo dispara.
- Costos: NQ $4,50 RT = 0,225 pts; ES 0,09 pts; 1 tick de slippage en entrada, stop y cierre por tiempo; TP limite sin slippage.
- Grilla 4 x 5 x 2 = **40 celdas**, todas publicadas.

## Lectura (fijada antes)
- Metricas por celda: n, acierto, media neta en pts y en R (R = distancia al SL), IC 95 % bootstrap por dia, factor de beneficio.
- Seleccion SOLO en IS: las 3 mejores celdas por media neta en IS; su OOS y su ES se reportan tal cual.
- Una celda "sobrevive" si: IC de OOS > 0 **y** ES media > 0. Con 40 celdas, la mejor de IS esta sesgada al alza (se informa
  la mediana de las 40 y la correlacion IS-OOS entre celdas como diagnostico de sobreajuste).
- Nada de esto se promueve sin replicacion/holdout.

## Como podria refutarse
Ninguna celda con OOS > 0 y ES > 0; o correlacion IS-OOS ~ 0 (el ranking de IS es ruido).
