# BONOS-ROTACION: la técnica swing de la charla, con comisión cero, no deja ventaja explotable (resultado, 2026-11-27)

Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (6 pruebas, `RATIOS_BONOS_AR`). HOLDOUT A5 sellado.
Herramienta: `python tools/bonos_rotacion.py correr` (`RESULTADO.json`).

## 1. Qué se tomó de la charla (relectura) y del broker
**Técnicas de Gus Lucioni:**
- ratio entre bonos del mismo flujo y distinta ley;
- referencia al promedio (en intradía, el de la rueda anterior y la media de 200; en swing, el de 7 y 15 días);
- bandas de Bollinger: «cuando está muy lejos del promedio amerita rotar»;
- rotar en tandas y nunca todo: mitad y mitad en el promedio, 80/20 en los extremos, siempre un 20–25 % remanente;
- historial corto (1–2 meses);
- operar en pesos (más líquido);
- elegir pares con la misma duration y liquidez pareja;
- objetivos: 0,15–0,5 % en intradía y 0,7–1 % en swing de 2–3 días.

**Broker (Veta Capital, plan VetaFLAT):**
- 0 % de aranceles (incluidos los de mercado) a cambio de un abono de $85.000, $160.000 o $285.000 por mes, más IVA;
- saldos y bonos de aire hasta 175 %, 250 % o 400 % de la cartera;
- los bonos de aire se recompran al día siguiente en contado inmediato, así que el corto es de un día;
- tope de 10.000 órdenes por mes;
- bots sólo con aprobación.

## 2. Resultado (versión swing; ejecución al cierre de t+1; spreads de la foto posterior al cierre)
| Serie (ventana 15) | DESC: exceso/mes (t) | REP: exceso/mes (t) | Bruto DESC (t) | Rotación diaria |
|---|---|---|---|---|
| **Canasta de 4 pares (primaria)** | **−0,59 % (−8,1)** | −0,45 % (−2,41) | — | — |
| GD30/AL30 | +0,08 % (+0,63) | −0,31 % (−2,08) | **+0,37 % (+2,88)** | 10,5 % |
| GD35/AL35 | −0,66 % (−6,27) | −0,68 % (−2,53) | +0,22 % (+2,48) | 10,7 % |
| GD38/AE38 | −0,81 % (−6,63) | −0,17 % (−0,43) | +0,19 % (+1,76) | 11,0 % |
| GD41/AL41 | −0,96 % (−7,44) | −0,62 % (−2,47) | +0,06 % (+0,67) | 11,1 % |

- **Veredicto pre-registrado: EN_CONTRA.** Ningún par queda nominado por BH en DESC.
- La ventana de 7 ruedas es peor: rota más (13–14 % por día).

**Por qué falla:**
- **La señal existe antes de costos:** bruto positivo en 3 de 4 pares en DESC.
- **El spread se la come.** El costo de equilibrio por unidad rotada es de 0,17 % en GD30/AL30 y de 0,03–0,10 % en los otros pares;
  el medido es de 0,17–0,79 %.
- **Lo más favorable no alcanza.** GD30/AL30, el par más líquido, con la mitad o un cuarto del spread de la foto, da +0,22 % o +0,29 %
  por mes en DESC, pero en la réplica da **−0,15 % / −0,07 %**, y **≈ 0 bruto** (+0,01 %, t 0,04).
- Coincide con BONOS-RATIOS: GD30/AL30 no replica la reversión y, desde la salida del cepo, ningún par revierte de forma significativa.
- **El abono no se cubre.** Aun con el mejor caso de DESC (+0,22 %/mes), el plan PRO necesita ≈ $47 millones de capital propio rotando
  sólo para pagarlo. La rotación con bonos propios no usa el cupo de bonos de aire.

## 3. Qué queda sin medir
La **versión intradía** de la charla (velas de 5 s a 30 min, varias veces por día, con bonos de aire) es su argumento principal y la
única que el abono y el cupo hacen viable. No se puede medir: no hay intradía histórico accesible desde el entorno (el endpoint de Open
BYMA Data no fue autorizado). La única forma limpia es **grabar puntas y operaciones hacia adelante** (data912 `/live`, IOL o la cuenta
del broker) y medir con el spread real.

Diagnóstico de grilla: sin grilla. Ventanas, 80/20 y z = 2 tomados de la charla; se publican costo ×0,5/×1/×2, ventana 7/15, el bruto y la
rotación.
Episodios: en REP, el bruto de GD30/AL30 se apaga (+0,01 %/mes) después de dar +0,37 % en DESC; coincide con la salida del cepo
(`bonos_ratios_20261127`).

Aporte al referente: con las técnicas concretas de la charla y las condiciones reales del broker (comisión cero), la versión swing no es
explotable: la señal bruta existe, pero es más chica que el spread y no replica en el par más líquido. Si hay algo explotable, está en el
intradía, que hay que grabar.
