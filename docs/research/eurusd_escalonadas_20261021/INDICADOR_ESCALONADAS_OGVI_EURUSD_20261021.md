# Indicador de picos escalonados sobre area cargada de OG/VI — EURUSD (Dukascopy), visor

Estado: CONSTRUIDO (target-free; sin desenlaces). Pedido de Nico 2026-10-21: "disena un indicador de picos sobre og y vi para el eurusd".
- Datos: `EURUSD_DUKAS_M1_LUXIMB` (Dukascopy, precio medio, 2026-03-17 .. 2026-06-17), velas 25t = 25 cotizaciones; zonas
  LUX-IMB OG+VI en M1 (detector con paridad medida en NQ, no en FX), vida 500 min.
- Detector: `escalonadas_det.detectar_px` (familia IPC, 5 picos, confirmacion por precio) via `tools/luximb_parity/luximb_escalonadas.py`.
- **Escala FX (target-free)**: la vela 25t de EURUSD mide p50 8 ticks (0,00001) vs 12 en NQ -> umbrales x 0,67:
  escalon <= 9 ticks, retroceso >= 5, confirmacion 5 ticks (NQ: 14 / 7 / 8).
- **Area cargada**: zonas vivas que se superponen con el rango recorrido por la escalonada hasta la deteccion; minimo
  **4 zonas**, elegido para igualar la frecuencia de NQ (4,5 por dia). Frecuencias: >=2: 7,1/dia; >=3: 5,7; >=4: 4,5; >=5: 3,6.
- Resultado: 939 escalonadas en 75 dias, **337 marcadas** (area mediana 3,9 pips).
- Capa del visor: `bundles/peaks_det/EURUSD_DUKAS_M1_LUXIMB__luxesc.json`, se ve con `&det=luxesc`.
Pendiente si se quiere medir: preregistro propio (familia nueva, no transporta nada de NQ/LUX-IMB) y los controles de
volatilidad previa y precio ya visitado aprendidos en M7b/M10b.

Comando: `python tools/luximb_parity/luximb_escalonadas.py viewer/nt8_bridge/bundles/EURUSD_DUKAS_M1_LUXIMB.json viewer/nt8_bridge/bundles/peaks_det/EURUSD_DUKAS_M1_LUXIMB__luxesc.json --max-step 9 --min-pull 5 --conf 5 --min-zonas 4`

## Capas sin filtro de zonas y simulacion visual (2026-10-21, exploracion; sin costos en el visor)
- `__picos` (25t, 9/5/5), `__picos150` (150t = 6x25t, parametros NQ 150t 42/14/16), `__picosm1` (velas M1, 13/7/7 = 25t x 1,43 por
  rango medio M1 13,1 vs 25t 9,2 ticks). Comando: `luximb_escalonadas.py ... --serie time_1m` para M1.
- Visor: `&sl=mitad` (SL a mitad entre deteccion y 1.er pico) y `&sl=ult2` (SL = 2x distancia deteccion -> ultimo pico =
  2x la confirmacion: 10 / 32 / 14 ticks en 25t / 150t / M1). Las capas de otra escala usan `i25_post` para simular en 25t.
- Tablero (sin costos), SL ult2 / TP 2R: 25t 939 op, 47 %, +0,40 R/op; 150t 308 op, 39 %, +0,16 R/op; M1 543 op, 39 %, +0,18 R/op.
  Costo aprox (spread 0,4 + comision 0,35 pip = 7,5 ticks) en R: 0,75 / 0,23 / 0,54 -> neto aprox -0,35 / -0,07 / -0,36 R/op.
