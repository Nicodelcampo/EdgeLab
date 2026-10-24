# Pre-registro — Recálculo del candidato LUX-IMB (regla del visor) sobre el release de Kaggle con costos canónicos

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-24.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia: `LUXIMB_FADE_VISOR`. Etapa del embudo: **EF2** (desarrollo con desenlaces; genera o descarta, nunca confirma).
Pedido: revisión del 2026-10-24 (`docs/research/revision_20261024/REVISION_20261024.md` §4: «recalcular el candidato con la fricción canónica»), relevado por Nico en el proyecto.

## 1. Qué se mide y por qué
La regla del visor congelada el 2026-10-21 (`tools/luximb_parity/luximb_holdout_regla_visor.py`, sha256 `3c44bc32c5d3bbdf6a13c51579366532f5b391fc18995844b406ae13c370e3f7`) es el candidato vivo de LUX-IMB. Su +4,95 pts/op se calculó con 0,225 pts de comisión más 1 tick por pata (≈ 0,725 pts por viaje), no con la fricción canónica de NQ (1,5455 pts base).

La escalera del 2026-10-22 (`tools/escalera_candidatos_20261022.py`) ya hizo esa cuenta, pero sobre bundles locales de la máquina de Nico que no están versionados ni en Kaggle. Este recálculo hace la **misma cuenta** sobre el **release canónico de Kaggle**, para que el número sea reproducible por cualquiera y no dependa de archivos locales.

No es una prueba nueva ni una elección: la regla, la geometría, la contabilidad y la escalera son las ya publicadas. Lo único que cambia es la fuente de los datos.

## 2. Datos (únicamente estos)
- Dataset privado `nicolasbuttaro/edgelab-liquid-ticks-20261014`, release `liquid_tick_v1` v4, archivo `data/NQ_ticks.parquet`.
- sha256 `cccc7c807ead85389aa48a2eaff728106f5c9cd1a9e67f74f69c7f272ea78a89`, 1.312.201.079 bytes, 291 sesiones, trade dates 20250805 → 20260925. **Sin holdout** (el script aborta si aparece una sesión ≥ 2026-10-01).
- Ventanas por contrato que asigna el release (estadísticas de row group): 09-25 20250805–20250916 · 12-25 20250917–20251215 · 03-26 20251216–20260316 · 06-26 20260317–20260612 · 09-26 20260616–20260915 · 12-26 20260918–20260925.
- El release es `CANDIDATE_NOT_RESEARCH_APPROVED`: **todo resultado de acá es PROVISIONAL**.
- Si estos datos no estuvieran, el pedido era informar y parar. Están y el sha256 coincide con `release_manifest.json`.

## 3. Regla y contabilidad (sin cambios)
- Operaciones: `escalera_candidatos_20261022.lux_trades` (impulsos `--modo inicio --p-rango 60 --min-ini 3 --share-ini 0.5 --rango-min-abs 60`; zonas OG+VI M1, vida 500 min; fade al cierre de la confirmación; TP = A; SL = 0,2·D; tope 240 min; velas 25t; misma vela → SL).
- Bruto por operación: llenados en el precio de referencia (entrada al cierre de la vela de confirmación, salida en el nivel o en el último precio), sin los ticks de deslizamiento ni la comisión de la campaña.
- Neto = bruto − `costos.friccion_rt_puntos("NQ")` (base, 1,5455 pts) y − `costos.friccion_rt_puntos("NQ", "adverso")` (2,0455 pts). Ningún costo sale de otro lado.
- Unidades de la escalera: R = neto / (0,2·D), como el 22/10.

## 4. Decisión (fijada ahora)
- Escalera `edgelab/funnel/escalera.py` con los mismos argumentos que el 22/10: `nominada=False`, `efecto_util=0.0`, `n_pruebas_familia` leído del registro global (incluye esta prueba). Bootstrap por sesiones, confianza 0,90.
- Salidas posibles: REFUTADA, SIN_POTENCIA o lo que la escalera devuelva. **Ninguna salida confirma**: esto es EF2 y todos los períodos ya se miraron.
- Comparación obligatoria con el 22/10: n por período y neto canónico. Si n difiere, se documenta la causa (fuente o ventana), no se ajusta nada para que coincida.

## 5. Justificación económica
Un fade de impulsos que atraviesan muchas zonas de desbalance recién nacidas apuesta a que el impulso agotó la liquidez de un lado y el precio vuelve al origen. Si existe, debería sobrevivir a la fricción real de NQ (≈ 6,2 ticks por viaje), que es el doble de la que cobró la campaña.

## 6. Cómo podría refutarse
- Si el neto canónico medio por operación es ≤ 0, o la cota superior del IC90 no llega a lo útil, la escalera la marca REFUTADA en descubrimiento.
- Si el resultado depende de los bundles locales (n o signo cambian de forma material con el release), el número del 22/10 deja de ser evidencia reproducible.

## 7. Riesgos y datos faltantes
- Selección: la regla salió de ~46 pruebas en su familia y ~105 en el programa; todos los períodos se miraron antes de congelarla. El efecto esperado tras selección ya era ~0 (DSR 0,33).
- La mirada al holdout del 21/10 (n=14, 14 SL) quedó consumida fuera de protocolo y **no se usa acá**.
- Release candidato: política de liquidez sin aprobar (D07) y calendario derivado (D06).

## 8. Registro
- Global: `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl`, campaña `luximb_20261024/recalculo_canonico_release`, familia `LUXIMB_FADE_VISOR`, **1 prueba**, antes de correr.
- Código (sha256 al pre-registrar): `tools/luximb_parity/luximb_recalculo_canonico_release.py` `b50769e8a04d96e1cb7186f474d76592765b8421cee82621ffc299c7ccdab917`; `tools/escalera_candidatos_20261022.py` `b68a8a655c7f04242ae3871e546ba200d7f69d778297ace6ed9e78665d227f23`; `tools/luximb_parity/build_luximb_nq_m1_bundle.py` `f74462641f0607a3a0993cd85006c11eb648aefebd32abb533e25d989a9ba78c`; `edgelab/costos.py` `0237ceb56c42635e3d016fc4d20a90eacbc0c4179088bd8eb6c58a5b02855654`; `config/costos/costos_canonicos.json` `b77f1519631339f0bd350c676345bccbcd7674bc4f47f6e084ce9d39b4f804b7`; `edgelab/funnel/escalera.py` `7d1a8adcecad9ceb7082a2099227bee5439638fff3b546f36be6de33e48ff592`.
- Salida: `docs/research/luximb_parity_20261020/RECALCULO_CANONICO_RELEASE_20261024.json` y su informe `RESULTADOS_RECALCULO_CANONICO_RELEASE_20261024.md`.
