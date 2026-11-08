# Pre-registro: SEGUNDO-INTENTO (03/11/2026)

Estado: PRE-REGISTRO (commiteado antes de correr). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2 exploratorio**.
Código: `edgelab/research/segundo_intento.py` (+ `_avcl`); tests `tests/research/test_segundo_intento.py`.

## Pedido de Nico

«Tomá lo que mejor funciona de la idea, encargate de que aparezcan muchas más operaciones, sobre todo por la potencia, y aplicalo a otras
familias porque necesito muchas variantes para diversificar.»

## Qué se toma, qué se saca

- **Se toma:** de INTENTO-FALLIDO-HACIA, lo único que repitió en las 3 fuentes y en las 2 ventanas (`RESULTADO_IF_HACIA.md`): entrar
  **hacia la zona** tras el intento fallido, con **confirmación**, y la primera pierna larga (que queda como variable).
- **Se saca:** lo que dejaba la muestra en 10 sesiones en 19 meses. El racimo obligatorio de ≥ 3 zonas pasa a ser la variable N ∈
  {1, 2, 3}, con zona individual incluida, y el piso de A/H baja de 4 a 2. Con datos sintéticos salen ~100 veces más eventos que en la
  versión anterior (10.095 contra 105).
- **Variables**: N, r (50/80/100 % de recuperación del rechazo), A/H y `dur_ida` (terciles; bajo, alto o cualquiera).
- **Ejecuciones**: CONF × TP {Z1, Z2, Z3, 2R}.
- **Celdas**: 3 × 3 × 3 × 3 × 4 = **324 por canal**. Pocas celdas a propósito: la potencia por celda es el objetivo.
- **Stop**: un tick más allá del extremo del rechazo. Noticias: sin entradas a ±5 min de un dato tier1 y salida forzada antes de cada dato.

## Campañas (diversificación por instrumento y por tipo de zona)

| Campaña | Zonas | Señal → ejecución (costo) | DESC |
|---|---|---|---|
| SI-USATECH-R | LUX-IMB | USATECH CFD → CFD (NQ) | 2024-01 → 2026-03 |
| SI-USA500-R | LUX-IMB | USA500 → CFD (ES) | 2024-01 → 2026-03 |
| SI-USA30-R | LUX-IMB | USA30 → CFD (YM) | 2024-01 → 2026-03 |
| SI-XAU-R | LUX-IMB | XAUUSD → spot (GC) | 2024-01 → 2026-03 |
| SI-EURUSD-R | LUX-IMB | EURUSD → spot (6E) | 2024-01 → 2026-03 |
| SI-GBPUSD-R | LUX-IMB | GBPUSD → spot (6B) | 2024-01 → 2026-03 |
| SI-NQ-R, SI-ES-R, SI-YM-R, SI-GC-R | LUX-IMB | futuro → futuro | 2025-08 → 2026-03 |
| SI-AVCL-NQ-R, SI-AVCL-ES-R | aVolClusterPOI | futuro → futuro | 2025-08 → 2026-03 |

La réplica es abr–sep 2026 en todas. Holdout: frontera única HOLDOUT-A4. Spot y CFD llevan la fricción canónica del futuro como
proxy, igual que las grillas U1 sobre CFD. Linaje: cada campaña es hija de la grilla U1 de su instrumento y de INTENTO-FALLIDO-HACIA, y
hereda su multiplicidad.

## Justificación económica y cómo podría refutarse

- **Justificación:** la zona que el precio no alcanzó sigue siendo liquidez sin tomar. El segundo intento, confirmado y después de un
  alejamiento largo, es la parte de la idea que se sostuvo entre fuentes.
- **Refutación:**
  - ninguna celda nominada por FDR q 0,10 (cola t) ni pista que replique en ningún instrumento;
  - `dur_ida` alto no supera a «cualquiera»;
  - falla de integridad.
