# Exploratorio sin resultados: impulsos "inicio cargado" LUX-IMB (NQ 09-26)

Estado: MEDIDO (descriptivo, target-free; nada posterior a la marca). Fecha 2026-10-20.
Definicion (`luximb_impulsos.py --modo inicio --p-rango 60 --min-ini 3 --share-ini 0.5 --rango-min-abs 60`): impulso ESPEJO-IND
en M1, marcado en la primera vela en curso con amplitud >= max(p60 causal, 60 pts), >= 3 zonas OG/VI vivas (vida 500)
atravesadas en el 25 % inicial y >= 50 % de las atravesadas en ese 25 %. Salida: `impulsos_inicio_piso60.json`.
Ojo: disenada mirando NQ 09-26 (replicacion HOLDOUT-A3): desenlaces solo en descubrimiento.

| medida | p10 | p50 | p90 |
|---|---|---|---|
| amplitud (pts) | 64 | 87 | 154 |
| velas 25t / M1 | 36 / 3 | 122 / 7 | 608 / 17 |
| pts por vela 25t | 0,18 | 0,79 | 2,13 |
| zonas en el 25 % inicial | 3 | 4,5 | 10 |
| zonas en el 75 % siguiente | 0 | 3 | 7 |
| densidad (zonas cada 100 pts): inicio / resto | | 21,3 / 4,3 | |
| fraccion OG en el inicio | 0 | 0,25 | 0,54 |
| fraccion de zonas opuestas al impulso en el inicio | 0,25 | 0,50 | 0,75 |
| edad de zonas al marcar (min) | 42 | 238 | 464 |
| minutos de A a la marca | 3 | 7 | 18 |

- 150 en 54 dias (max 11 el 28-jul); 14 marcas a < 30 min de la anterior (antes 40): menos encadenamiento.
- 72 suben / 78 bajan. Horario NY: 46 entre 9 y 11 h; 29 entre 3 y 8 h; 30 de 17 a 24 h.
- El inicio es ~5x mas denso que el resto (mediana). 21 de 150 tienen el resto vacio.
- Las zonas del inicio son mitad a favor, mitad en contra del impulso: "cargado" no tiene signo.

## Candidatas a medir con P&L (requieren OK; descubrimiento NQ 09-25..06-26/31-mar)
- **M5 (vuelta al inicio cargado):** desde la marca, P(el precio vuelve al borde del 25 % inicial, A + 0,25·R·s, antes de
  extender +25 %) y P&L neto de ese fade.
- **Control:** impulsos de la misma amplitud (mismo piso y percentil) con zonas NO concentradas (share < 0,5 o reparto
  parejo). Separa "inicio cargado" de "impulso grande".
- **Alternativa (dos canales):** continuacion (+25 % antes que volver al inicio) se reporta junto.
- Estratos: resto vacio vs no; direccion; apertura cash. ~6 hipotesis, Holm, MDE publicado. Con ~4 contratos de
  descubrimiento se esperan ~400-500 eventos.
- Como podria refutarse: T - C sin diferencia con MDE <= 10 pp, o P&L neto <= 0.

Aporte al referente: confirma que la definicion nueva separa de verdad un inicio denso (5x) de un recorrido limpio, y deja el
contraste listo para medir.
