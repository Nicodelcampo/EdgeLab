# Auditoría de veracidad — estrategias del tablero de régimen corto

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `CANASTA_REGIMEN` / `regimen_corto_20261106`
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`
Procedencia: series `series_diarias_regimen_20261106.json` del parche `befcd4bc85e279df254ad84c2e07d686f1708fbfa5ca30321c91889223a4c885`. Generadores restaurados desde `parche_12_familias_programa_r_20261103.patch` y `artifacts/req_20261103_delta_origin_vibrant/delta.patch`.

## Veredicto

El libro diario es aritméticamente consistente y no contiene sesiones de holdout. El resultado económico **no está verificado contra ticks** en esta máquina, y el nombre público de `ABSORCION-NQ-3R` no coincide con la celda que declara. Por eso **el holdout no se abrió**.

## Lo que sí cierra

Sobre las 26 series de `series_cand` y las 21 de `series_p4`:

- la suma del R diario coincide con `R_total` (tolerancia 0,05 R);
- la suma de operaciones coincide con `total.n`;
- `m * n` coincide con `r` en cada día;
- ninguna sesión es `>= 20261001`.

## Lo que no cierra

1. Esos generadores no estaban en el checkout. Se restauraron `absorcion_climax.py`, `compresion_nr.py`, `rango_preapertura.py`, `rango_ruptura.py` y `regimen_sesion.py`. Sin cache de tensores y sin ticks locales no se puede recomputar un solo día.
2. `ABSORCION-NQ-3R` declara `celda_coord = [1, 2, 0, 3]` y el texto «Stop 1.3 ATR · TP 3.0R». En `EJECUCIONES` el índice 3 es `("ATR", 1.3, 3.5)`: stop 1,3 ATR y objetivo **3,5R**. No existe la tupla `(1.3, 3.0)`. El rótulo 3,0R es falso respecto del código.
3. `COMPRESION-NR-GC` con coord `[2, 2, 2, 1]` cae en `("CAJA", 1.0, 4.0)`. El texto «NR7» no es lo que mide el módulo: mide el rango de 30 velas contra los tres bloques previos de 30.
4. `tests/research/test_absorcion_climax.py` y `test_compresion_nr.py` no corren en esta rama: `sintetico.bloques` no acepta `t0_s`. La causalidad quedó leída en el código (el disparo usa la vela `k` y la entrada es el tick siguiente) y no ejecutada.
5. No hay directorio de ticks en esta máquina. El puente prohíbe bajar `edgelab-holdout-sellado` (`_check_not_sealed`). Abrir octubre para confirmar una serie no recomputada gastaría el sello.

## Decisión de apertura

Pedido de Nico el 2026-11-07: abrir el holdout después de auditar si el resultado es verídico. La auditoría no llega a «verídico». La apertura queda **sin hacer** y sin fila nueva en `docs/holdout_access_log.md`.
