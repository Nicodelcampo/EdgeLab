# Verificación del calendario de noticias contra el precio de ES (2008-2025)

Estado: VIGENTE (verificación target-free; no mira resultados de estrategias ni el holdout)  
Fecha: 2026-11-25  
Pedido de Nico: antes del veto en el motor y en NT8, comprobar en los datos de EdgeLab que las noticias del calendario
histórico coinciden con el movimiento del precio.  
Herramienta: `tools/verificar_calendario_precio.py` · datos: `edgelab-nt8-m1-futuros/ES_M1_nonadj_utc.parquet` (índice =
apertura de la vela; confirmado con el recorte de emergencia del 2008-01-22 08:20 ET, vela 13:20 UTC con 43.592 contratos)
· salida: `VERIFICACION_CALENDARIO_PRECIO.json`.

## Método

Para cada evento tier1: rango (máx − mín) de cada vela M1 en ±10 minutos, dividido por la mediana del rango de ese
minuto del día en las 20 sesiones previas. Si la hora es correcta, el pico de la ventana cae en el desfase 0 (o 1).
Placebo: mismos minutos del día en días sin evento (mismo período ±45 días).

## Resultado

| | pico en 0 | pico en 0 o 1 | ratio en 0 (mediana) |
|---|---|---|---|
| placebo (n 2.434) | 6,2 % | 9,7 % | 1,0 |
| NFP 2008-2022 (n 182) | 59,3 % | 68,7 % | 7,0 |
| FOMC decisión 2008-2022 (n 122) | 39,3 % | 58,2 % | 5,0 |
| ventas minoristas 2008-2022 (n 186) | 44,1 % | 56,5 % | 2,8 |
| CPI 2008-2022 (n 191) | 37,7 % | 45,0 % | 2,5 |
| JOLTS 2008-2022 (n 161) | 4,3 % | 8,1 % | 1,0 |

Tabla completa por evento, período y año en el JSON.

Lectura:
1. **Fechas y horas correctas.** Los eventos fuertes caen en el minuto anunciado entre 5 y 10 veces más que el azar,
   también la convención de la Fed (14:15 hasta 2012) y las reuniones de emergencia. En los eventos que fallan, el pico
   cae disperso (no en un desfase fijo): no hay una hora corrida sistemáticamente.
2. **La fuerza de cada noticia depende de la época.** JOLTS casi no movía ES antes de 2021 (≈ placebo), PCE y PPI se
   vuelven fuertes en 2022 (inflación), el ISM de 2017 (VIX ≈ 10) no movía nada aun con las fechas correctas (verificadas
   mes por mes). Que una noticia esté en el calendario no implica que haya movido el precio ese día.
3. **Las fechas extra de ALFRED no son noticias.** En los 155 meses con más de una fecha del mismo evento, las fechas
   que no son la publicación (revisiones) dan pico en 0/1 11,9 % y ratio 1,0, igual que el placebo. Quedan en el
   veto (conservador: sólo quitan operaciones) y quedan anotadas acá.
4. Conferencia de prensa del FOMC: sin pico en 0 en ningún período (no hay un dato que se publique en un minuto; el
   movimiento se reparte). Es esperable y no indica error.

## Consecuencia para el veto

El veto de ±2 min (±5 FOMC) sobre este calendario cubre las publicaciones reales. Las de baja reacción en su época
(JOLTS pre-2021, ISM en años calmos) se vetan igual: la regla de las firmas no distingue y el costo es chico.
