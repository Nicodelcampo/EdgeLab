# ORB-CFD — MEDIDO / NO MEDIDO (Dukascopy USA500, USATECH, USA30)
Registro vivo. Manifiesto: `ORB_CFD_FASE0B_MANIFIESTO_20261017.md`.

## Censo 0A (target-free) — MEDIDO (2026-10-17)
Kernel `edgelab-orb-cfd-census-v1`, `orb_cfd_results_20261017/EXP_ORB_CFD_0A_CENSUS.json`. Sin retornos ni precios posteriores al cierre del rango de 15 min. Mid = (bid+ask)/2, RTH por reloj 09:30-16:00 ET.
- **Días RTH:** USA500 2.257 (2018-01-02..2026-09-30); USATECH 966 y USA30 966 (2023-01-03..2026-09-30). Contra 173/161 de ORB_FUT.
- **Densidad:** mediana de cotizaciones en el rango de 15 min: USA500 ~1.000 (2018) a 2.900-4.100 (2020-26); USATECH 5.200-8.700; USA30 3.800-6.400. Primera cotización <= 300 s en >99 % de los días. Huecos > 120 s: USA500 8/4/4/5/0/1/2/0/1 por año; USATECH y USA30 <= 7.
- **Ancho y fricción:** ancho mediano del rango de 15 min USA500 6.3-19.7 pts, spread mediano 0.46-0.51 pts (spread/ancho 6.7 % en 2018 → 2.7 % en 2026); USATECH spread/ancho 2.3 % → 0.8 %. El spread del CFD **no es** el del futuro.
- **Guardas propuestas** (en el manifiesto): días válidos M/R = USA500 1.865/300, USATECH 628/296.

## NO MEDIDO
Cualquier extensión, ruptura o retorno sobre el CFD (esperando STOP); equivalencia CFD↔futuro; costos reales (futuros); USA30 (fuera de alcance); todo ≥ 2026-10-01 (no existe en los datasets).
