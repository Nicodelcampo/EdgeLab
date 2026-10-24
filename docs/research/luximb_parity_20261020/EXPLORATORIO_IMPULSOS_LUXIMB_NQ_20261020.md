# Exploratorio sin resultados: impulsos que atraviesan zonas LUX-IMB (NQ 09-26, M1/25t)

Estado: MEDIDO (descriptivo, target-free; NO se miro nada posterior a la marca)
Fecha: 2026-10-20
Fuente: `viewer/nt8_bridge/bundles/luximb_imp/NQ_09-26_M1_LUXIMB.json` (spec `LUXIMB-IMPULSOS-v5-reparto`),
`tools/luximb_parity/luximb_impulsos.py` con valores por defecto. Ventana 2026-06-16 a 2026-09-15 (pre-holdout).

## Definicion congelada (v5)
Impulso ESPEJO-IND en M1 (3·ATR14, <= 20 velas, eficiencia >= 0,3), seguido vela a vela; se marca en la primera vela M1
en curso que cumple, con umbrales causales (2.000 impulsos cerrados previos, minimo 500): amplitud >= p80; zonas OG/VI
vivas (vida 500 velas) atravesadas enteras >= p80; reparto en tercios del rango sin tercio vacio ni > 60 %;
sin filtro de rapidez. Velas contadas en 25t.

## Que son los 151
| medida | p10 | p50 | p90 |
|---|---|---|---|
| amplitud (pts) | 61 | 96,5 | 140 |
| velas 25t | 60 | 156 | 630 |
| velas M1 | 2 | 10 | 17 |
| pts por vela 25t | 0,19 | 0,61 | 1,48 |
| zonas atravesadas | 7 | 10 | 21 |
| minutos de A a la marca | 2 | 10 | 17 |
| fraccion OG (resto VI) | 0,10 | 0,28 | 0,44 |
| fraccion de zonas de direccion opuesta al impulso | 0,29 | 0,50 | 0,78 |
| edad de las zonas al marcar (min) | 66 | 255 | 457 |
| alto de las zonas (ticks) | 1 | 4 | 10 |

- Direccion: 78 suben, 73 bajan.
- Horario (NY): 61 de 151 entre 09:30 y 11:00 (apertura cash); 26 entre 03:00 y 08:00; 20 en la sesion de la tarde/noche (17-24 h); casi nada 12-17 h.
- **Agrupamiento fuerte:** 151 marcas en **52 dias**; un dia tiene hasta 11 (27-ago 11, 28-jul 10, 15-sep 9). 40 marcas caen a < 30 min de la anterior. La N efectiva para inferencia es mas cercana a 52 que a 151.

## Lectura para elegir que medir
1. La N efectiva (~52 dias) es chica: con clustering por dia, un MDE de proporcion ronda +/-15-20 pp. Antes de P&L
   conviene ampliar a NQ 12-25, 03-26 y 06-26 (descubrimiento pre-holdout, mismo detector; ~4x eventos).
2. La mitad de las zonas atravesadas son de direccion opuesta: el impulso cruza tanto "soportes" como "resistencias";
   la hipotesis de rebalanceo de Nico no puede depender del signo de la zona sin separarlo.
3. Mucha concentracion en la apertura cash: cualquier efecto hay que controlarlo contra impulsos de igual hora.
4. Las zonas son finas (mediana 4 ticks) y viejas (mediana ~4 h): "zona" aca es mayormente un nivel.

## Mediciones candidatas con P&L (NO ejecutadas — requieren OK de Nico, STOP)
Desenlace desde el cierre de la vela de marca, sin mirar holdout. Dos canales (direccional y no direccional) y MDE publicado.
- **M1 (hipotesis de Nico, rebalanceo):** P(el precio recorre el 50 % del impulso de vuelta hacia A antes de extenderse
  +25 % mas alla del extremo) y P&L neto de un fade con stop en extremo+25 % y objetivo 50 %.
- **M2 (control clave):** lo mismo en impulsos de amplitud y hora comparables **sin** el requisito de zonas (o con <= 2
  zonas). Si M1 ~ M2, el efecto es de "impulso grande", no de las zonas.
- **M3 (alternativa):** continuacion: P(+25 % antes que -50 %); es el complemento de M1 y se reporta junto.
- Estratos pre-registrados (no seleccion): direccion, apertura cash vs resto, fraccion de zonas opuestas (< / >= 0,5).
- Numero efectivo de hipotesis: 2 desenlaces x 2 grupos + 3 estratos = ~7; correccion por multiples pruebas.
- Costos NQ propios (no transportar los de 6E/ES).

Como podria refutarse: M1 sin diferencia contra M2 (con MDE suficiente), o P&L neto <= 0 tras costos en descubrimiento.

Aporte al referente: describe la muestra sin tocar resultados y deja escrito el contraste que separa "efecto de zonas"
de "efecto de impulso grande", que es lo que decide si hay algo que medir con P&L.

## Variante pedida por Nico: vida de zonas 200 velas (en vez de 500)
Mismo detector y cortes; solo cambia `--vida 200`. Salida: `impulsos_vida200.json`; descriptor `tools/luximb_parity/describir_impulsos.py`.
| medida | vida 500 | vida 200 |
|---|---|---|
| marcados | 151 | **51** |
| dias distintos / max por dia | 52 / 11 | 33 / 5 |
| marcas a < 30 min de la anterior | 40 | 5 |
| sube / baja | 78 / 73 | 34 / 17 |
| apertura cash 9:30-11 NY | 61 (40 %) | 13 (25 %) |
| umbral de zonas (causal) | 5-7 | 4-5 |
| zonas atravesadas p50 | 10 | 6 |
| pts por vela 25t p50 | 0,61 | 1,14 |
| velas 25t p50 | 156 | 84 |
| amplitud p50 | 96,5 | 97 |
| edad de zonas al marcar p50 (min) | 255 | 100 |
Coinciden 43 impulsos; 108 solo con 500, 8 solo con 200.

Lectura: con vida 200 la muestra cae a un tercio y queda casi sin agrupamiento (5 marcas encadenadas contra 40). Los que
sobreviven son mas rapidos (casi el doble de pts por vela 25t) con la misma amplitud, y pesan menos en la apertura cash.
Gran parte de los 151 con vida 500 se apoya en zonas de 2-7 h de antiguedad, frecuentes en dias de mucho recorrido.
Con 51 eventos en 33 dias no hay potencia para P&L en un solo contrato; la vida 200 solo es usable ampliando contratos.
