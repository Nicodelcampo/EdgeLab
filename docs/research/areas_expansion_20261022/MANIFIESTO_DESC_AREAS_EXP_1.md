# Manifiesto — AREAS-EXP-1, corrida de descubrimiento con desenlaces (DESC)

Estado: VIGENTE — OK de Nico el 2026-10-22 («ya te doy el OK»). La réplica queda por decidir; no afecta al descubrimiento.

- **Spec:** `SPEC_AREAS_EXPANSION_V1.md` (v1.1). **Código:** commit `3b077192`. El kernel autocontenido lleva sus SHA embebidos.
- **Referente:** `docs/NORTH_STAR.md` (cuerpo `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`).
- **Etapa del embudo:** EF2 (tamiz) → E2 (sobrevivientes) → hasta 3 celdas por fuente a réplica pre-registrada (EF5).

## Qué se corre
Dos kernels de Kaggle, uno por fuente, en modo `DESC`:

| Fuente | Datos | Período |
|---|---|---|
| Futuro NQ | release `liquid_tick_v1`, ticks reales con volumen | 2025-08-05 → 2026-03-31 (descubrimiento HOLDOUT-A3) |
| Índice USATECH | Dukascopy, ticks; volumen cotizado | mismo período |

## Corrida descartada (v1.2) — NO SE MIRA
- El kernel `edgelab-areas-desc-usatech` (versión 1) se lanzó con el código v1.2.
- La revisión posterior encontró errores que afectan desenlaces: entrada a mercado sólo al cierre, v_rel faltante en el tercio «bajo» y condiciones del manifiesto sin aplicar.
- **Sus resultados no se descargan ni se miran.** Las pruebas siguen contadas (`areas_exp_1/desc_*`).
- Se relanza con v1.3.

## Número de pruebas (contador global, antes de correr)
- **v1.3: 995.328 celdas por fuente.** Se registran como `areas_exp_1_v13/desc_nq` y `areas_exp_1_v13/desc_usatech`, sumadas a las de v1.2. Contar de más es conservador.
- 746.496 celdas por fuente, **1.492.992 en total**.
- Las celdas están anidadas: los umbrales «≥» y «≤» comparten operaciones. El número efectivo se estima sobre las sobrevivientes, y el recorte de Harvey-Liu se cobra con ese N_eff.
- Se registran en `TRIAL_REGISTRY_GLOBAL.jsonl` como `areas_exp_1/desc_nq` y `areas_exp_1/desc_usatech`.

## Regla de decisión (fija)
- **Tamiz:** FDR BH-Storey a q = 0,10 sobre todas las celdas. Las que tienen menos de 30 operaciones cuentan con p = 1.
- **E2, por celda nominada** (hasta 1.000, por t), tienen que pasar las tres condiciones:
  - IC 90 % por sesiones con cota inferior > 0 neta de fricción canónica (1,545 pts por viaje);
  - meseta: ≥ 2/3 de los vecinos ±1 en x, A/H, comercio y stop positivos, con mediana ≥ 50 %;
  - económico: sin las 5 mejores, ningún mes > 80 %, sin colapso con +0,5 pts de costo.
- **A réplica:** hasta 3 celdas por fuente, por cota inferior del IC (no por P&L máximo).
- **Si no pasa ninguna:** se informa el MDE por zona de la grilla. La familia no se declara muerta si es un nulo sin potencia.

## Réplica (a decidir por Nico ANTES de correr DESC)
- **(a) USATECH 2023-01 → 2025-07.** Nunca mirado y con mucha potencia. Sirve sólo para la fuente índice.
- **(b) NQ abr–sep 2026.** Es la única apertura de la familia. Esos meses ya se vieron en el visor para otras preguntas LUX-IMB, así que la réplica no es limpia para esta familia.
- **(c) ES u otro índice como réplica entre activos.**

## Riesgos y datos faltantes
- **USATECH es un CFD:** no tiene costo canónico (se usa el de NQ como referencia) y su volumen es cotizado, no negociado. **Nada de USATECH es operable tal cual.**
- **Huecos de NQ:** ES y NQ terminan el 25-sep. Afecta sólo a la réplica (b).
- **La definición de área es una elección:** W, G y los ciclos están congelados en v1.1.
- **Ejecución:** la ambigüedad de M1 se resuelve con ticks, pero los límites suponen que no hay cola (se exige atravesar el nivel por 1 tick).

## E0 (target-free, ya corrido)
**USATECH (kernel `edgelab-areas-e0-usatech`):**
- 4.766 áreas y 59.754 disparos en 169 sesiones, unas 28 áreas por día.
- La configuración más escasa (N ≥ 8, W = 40) tiene unos 450 disparos.
- A/H: p10 1,1 y p90 6,7. p_vol: mediana 0,35.

**Corrección v1.2, decidida sin desenlaces:**
- El comercio real tiene mediana de 9,7 visitas por zona y p10 = 4, así que los cortes fijos 0/1/3 dejaban la perilla sin efecto.
- Ahora los cortes son los **cuartiles del E0 de cada fuente**, como en v_rel. Se guardan en el resultado.
- Control de ruido: sigue en 0 nominadas.

**NQ:** se completa cuando termine el kernel `edgelab-areas-e0-nq`.
