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
