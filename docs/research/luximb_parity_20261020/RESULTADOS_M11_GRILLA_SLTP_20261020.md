# Resultados M11 — grilla SL/TP/BE del fade "fin de caja -> inicio de zona" (IS / OOS / ES)

Estado: MEDIDO (exploratorio pre-registrado). Veredicto: **NINGUNA CELDA SOBREVIVE**. Manifiesto
`MANIFIESTO_M11_GRILLA_SLTP_FADE_20261020.md` (antes de correr). Codigo `luximb_m11.py`; todas las operaciones en
`RESULTADOS_M11.csv`; las 40 celdas en `RESULTADOS_M11.json`.
IS = NQ ago-dic 2025 (119 operaciones); OOS = NQ dic 2025-mar 2026 (114); ES = mismo periodo (247, puntos de ES).

## Entrada del visor vs entrada realista (TP en A, SL 1/5, sin BE)
| | IS | OOS | ES |
|---|---|---|---|
| optimista (entra en X, sin costos — lo que muestra el visor) | +7,0 pts | +14,4 | +1,5 |
| realista (cierre de la vela de marca, 1 tick, comision) | +2,0 [-5,8, +10,3] | +5,8 [-1,9, +13,4] | +0,09 [-0,65, +0,90] |
Entrar en X explica ~5-9 pts NQ por operacion: casi todo lo que se veia en el visor.

## Diagnostico de la grilla (40 celdas realistas)
- Correlacion entre celdas IS vs OOS: **-0,04**; IS vs ES: **-0,02** -> el orden de las variantes es ruido: ninguna
  combinacion SL/TP/BE es mejor de forma estable.
- OOS: **40/40 celdas positivas** (mediana +5,7 pts) mientras IS mediana +0,36 y ES mediana -0,21 (9/40 positivas): el OOS
  positivo es **efecto del periodo** (NQ ene-mar 2026), no de la configuracion. ES (mismo periodo) no lo acompana.
- Mejor de IS (TP 0,75 D, SL 0,2 del TP, con BE): IS +5,3 [-1,2, +12,1]; OOS +6,7 [+0,4, +13,1]; ES **-0,16** [-0,68, +0,40]
  -> falla la condicion ES > 0.
- Patrones generales: SL chico (0,1) -> acierto 4-14 %, pierde; SL = TP -> acierto ~50 %, media ~0 con IC anchisimos;
  BE no mejora de forma consistente.

## Alcance
Muere: el fade "fin de caja -> inicio" con cualquiera de las 40 combinaciones SL/TP/BE como estrategia transportable
NQ -> ES en descubrimiento. El +0,8 R/operacion del visor era sobre todo entrada optimista y periodo de diseno.

Aporte al referente: convierte la impresion visual en un numero con entrada realista y costos, y muestra que la eleccion
de SL/TP no estabiliza nada (ranking IS no predice OOS).
