# Auditoría de veracidad — estrategias del tablero de régimen corto

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `CANASTA_REGIMEN` / `regimen_corto_20261106`
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`
Procedencia: series `series_diarias_regimen_20261106.json` del parche `befcd4bc85e279df254ad84c2e07d686f1708fbfa5ca30321c91889223a4c885`. Generadores restaurados desde `parche_12_familias_programa_r_20261103.patch` y `artifacts/req_20261103_delta_origin_vibrant/delta.patch`.

## Veredicto

El libro diario es aritméticamente consistente y no contiene sesiones de holdout. Los rótulos del tablero quedaron alineados con `EJECUCIONES` y los tests de causalidad de absorción y compresión pasan. El R diario publicado sigue sin recomputarse contra ticks: los cortes por cuantiles no están archivados y `DOBLE_RETROCESO` no está en el checkout. Por eso **el holdout no se abrió**.

## Lo que sí cierra

Sobre las 26 series de `series_cand` y las 21 de `series_p4`:

- la suma del R diario coincide con `R_total` (tolerancia 0,05 R);
- la suma de operaciones coincide con `total.n`;
- `m * n` coincide con `r` en cada día;
- ninguna sesión es `>= 20261001`.

## Lo que no cierra

1. Los generadores se restauraron y quedaron registrados como `NATIVO_AGENTE` en `config/autopilot/grillas/indicadores_agente.json`. `tests/research/test_absorcion_climax.py` y `test_compresion_nr.py` pasan, incluido `test_causal`. Eso verifica que el disparo no mira velas futuras en el sintético. No verifica que el R diario publicado salga de esos disparos sobre los ticks.
2. El tablero decía «Stop 1.3 ATR · TP 3.0R». En `EJECUCIONES` el índice 3 es `("ATR", 1.3, 3.5)`. No existe `(1.3, 3.0)`. El texto del HTML quedó en 3,5R. El id `ABSORCION-NQ-3R` no se renombró.
3. `COMPRESION-NR-GC` con coord `[2, 2, 2, 1]` es `("CAJA", 1.0, 4.0)`. El texto «NR7» del tablero quedó en «NR 30 barras»: el módulo compara el rango de 30 velas con los tres bloques previos de 30. Sus cortes son fijos, así que esta celda sí se podría recomputar si se corre el simulador sobre el GC de pre-holdout. Esa corrida no está hecha.
4. `extension_previa` de absorción y `ancho_rango` de preapertura salen de cuantiles del E0. Esos cortes no están en la serie ni en el módulo. Sin ellos la coordenada no recupera los mismos disparos. `DRC-YM-4` (`DOBLE_RETROCESO`) no tiene módulo en el checkout.
5. No se bajó `edgelab-holdout-sellado`. Los ticks de pre-holdout que se usen para H-REG-2 no reemplazan este hueco: el rango de la sesión no identifica la celda.

## Decisión de apertura

Pedido de Nico el 2026-11-07: abrir el holdout después de auditar si el resultado es verídico. La auditoría no llega a «el R publicado sale de estos ticks». La apertura queda **sin hacer** y sin fila nueva en `docs/holdout_access_log.md`. La canasta estática queda en `RESULTADO_CANASTA_ESTATICA_20261107.md` con el mismo cierre.
