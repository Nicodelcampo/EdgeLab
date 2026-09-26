# Handoff 2026-09-26 (sesión nube): reversión en zonas HFT y ESPEJO-SIM — para auditar en una sesión local

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Rama:** `claude/focused-fermat-qjt805` (PR #60, base `feat/unified-nt8-viewer-20260920`).
El CI del PR está rojo por un test del visor que ya falla en la base: el commit `9f5f6c4` de picos NQ inserta código
entre `zoneAvailableSec` y `drawZones`. No es de este trabajo; está comentado en el PR.
**Estado:** los dos estudios son **exploratorios** (sin P&L, sin selección). Holdout y abr–jun intactos: todo corta en
2026-04-01.

## 1. Datos (Kaggle `nicolasbuttaro/edgelab-ticks-mnq-preholdout`, verificados contra `files.sha256`)

| Archivo | sha256 (del dataset) | Rol |
|---|---|---|
| `MNQ_09-25_ticks.parquet` | `ae98f789…b927` | descubrimiento |
| `MNQ_12-25_ticks.parquet` | en `files.sha256` | replicación |
| `MNQ_03-26_ticks.parquet` | en `files.sha256` | replicación (recortado a 2026-04-01) |

Bajar: `kaggle datasets download nicolasbuttaro/edgelab-ticks-mnq-preholdout -f <archivo> -p <dir>`.
**Regenerar el token de Kaggle:** se pegó en el chat de esta sesión. No quedó en el repo.

## 2. Estudio A — HFT-REV-EXP: ¿la zona HFTZonesNQPureV4 anticipa la reversión?

- **Pre-registro y resultados:** `docs/research/HFT_REVERSION_EXPLORATORIA_MNQ_20260926.md` (incluye la enmienda 1,
  cortes por contexto).
- **Herramientas:**
  - `tools/hft_reversion_explore.py`: censo, controles de nivel, polaridad y caminata aleatoria;
  - `tools/hft_reversion_cortes.py`: cortes por contexto, BH-FDR, límites de terciles fijados en 09-25.
- **Artefactos:**
  - `artifacts/research/hft_rev_exp/MNQ_09-25/reporte.*` (censo);
  - `artifacts/research/hft_rev_exp/cortes/MNQ_{09-25,03-26}/`.
- **Resultado del censo (09-25, 29.635 zonas):** revierte 40 t el 26 % de las que vuelven, contra 25 % de la caminata
  aleatoria. Exceso sobre el control de nivel de +1 a +2,5 pp. Penetración mediana 6 t.
- **Cortes 09-25:** exceso difuso (+1 a +3 pp en casi todos los cortes). Los que pasan FDR son terciles del medio o
  cortes que son casi toda la muestra; no hay un «cuándo».
- **Pendiente:**
  - **replicación en 12-25** (murió dos veces por memoria; ver §4);
  - la de 03-26 está hecha y falta leerla contra la regla de sostenido;
  - la variable `confluencia` sale degenerada (≈ todo «2+» con ~820 zonas por sesión).

## 3. Estudio B — ESPEJO-SIM: ¿la vuelta que se parece al impulso completa el espejo?

- **Pre-registro:** `docs/research/MANIFIESTO_ESPEJO_SEMEJANZA_MNQ_20260926.md` (commit `fa7b3bc`, antes de medir).
  - Enmienda 1 (`21a9a9f`): nulo al cierre de la vela, agregado **después** de ver datos. No reemplaza al original.
  - Enmienda 2 (`ea491a2`): grilla 3 × 5 del detector, pedida por Nico para ganar muestra, fijada antes de correrla.
- **Herramienta:** `tools/espejo_semejanza.py`. `--grilla` corre las 15 configuraciones en una pasada. El nulo exacto
  se validó sobre una caminata aleatoria (exceso ≈ 0).
- **Artefactos:** `artifacts/research/espejo_sim/MNQ_09-25_cfg20_68/` y `artifacts/research/espejo_sim/grilla_MNQ_09-25/`.

**Resultado del descubrimiento (09-25):**

1. **El nulo original (f al extremo de la vela) está sesgado:** da −10 a −14 pp en todo. Con f al cierre, el exceso
   general queda en −1 a −3 pp, compatible con el azar.
2. **Configuración de Nico (20, 68):** sólo x = 0,75 muestra diferencia, T3 − T1 = +16 pp [+2,5, +26,7], con 60
   eventos por tercil.
3. **Grilla:**

| Configuración | Eventos por tercil | S T3 − T1 (prueba principal) | Tercil parecido vs nulo al cierre |
|---|---|---|---|
| `minW` = 17 (las tres `maxBars`) | 5.000 a 13.000 | **+1,5 a +4,9 pp, casi todas pasan FDR** | +1 a +2,6 pp |
| `minW` 34–68 | pocos | ruido | ruido |

   **Si replica, las vueltas parecidas al impulso completan el espejo unos 2–4 pp más.** Falta replicar, y hay dos
   cuidados:
   - los eventos se superponen (el bootstrap por sesión lo cubre, pero hay que revisarlo);
   - S incluye la velocidad. El pre-registro dice que si sólo sostiene `vel`, es momentum y no espejo.

4. **Economía:** con W = 17 t, el exceso necesario para pagar la fricción es costo/W ≈ 2,4/17 = 14 pp. **No es
   operable en esta escala.** Eso motiva la versión macro (§5).

**Pendiente:** replicación de la configuración (20, 68) y de la grilla en 12-25 y 03-26, con los comandos de §4.

## 4. Cómo reproducir (sesión local)

```
# A — censo, cortes y replicación
python tools/hft_reversion_explore.py --parquet <dir>/MNQ_09-25_ticks.parquet --contract "MNQ 09-25" --out out/A
python tools/hft_reversion_cortes.py --parquet <dir>/MNQ_09-25_ticks.parquet --contract "MNQ 09-25" --out out/cortes/0925
python tools/hft_reversion_cortes.py --parquet <dir>/MNQ_12-25_ticks.parquet --contract "MNQ 12-25" \
    --limites out/cortes/0925/limites.json --out out/cortes/1225
# B — espejo (una configuración y grilla), descubrimiento y replicación
python tools/espejo_semejanza.py --grilla --parquet <dir>/MNQ_09-25_ticks.parquet --contract "MNQ 09-25" --out out/g/0925
python tools/espejo_semejanza.py --grilla --parquet <dir>/MNQ_12-25_ticks.parquet --contract "MNQ 12-25" \
    --referencia out/g/0925/referencia_grilla.json --out out/g/1225
```

**Memoria:** los contratos 12-25 y 03-26 (≈ 1,8 GB cada uno) necesitan varios GB por proceso. En esta nube (15 GB)
murieron al correr 3 o 4 a la vez: **correr de a uno**. Las corridas de 09-25 tardan 10–20 min; las de 12-25 y 03-26,
~1 h.

**Qué auditar primero:**
1. que la zona reproducida por `hftzones_universal` SCALED_FUNNEL_V1 coincida con lo que dibuja el visor en MNQ (hoy
   `PARITY_ABSTAIN`);
2. el sesgo del nulo de espejo al extremo contra al cierre (enmienda 1);
3. que los terciles de replicación reusan los de 09-25 (`--limites` / `--referencia`);
4. la superposición de eventos en la grilla con `minW` = 17.

## 5. Propuesta ESPEJO-MACRO en ES (discutida con Nico, todavía no pre-registrada)

**La cuenta que la justifica:** entrar en la fracción f de la vuelta, con objetivo en A y stop en B, da
EV = W · (p − f) − costo. **El exceso mínimo sobre el nulo es costo / W:**

| W | Exceso necesario |
|---|---|
| 60 t | 4 pp |
| 120 t | 2 pp |
| 200 t | 1,2 pp |

**Estructura:**
- **Velas:** de tiempo de 5 min, con 15 min como segunda escala.
- **Detector:** el mismo, con `minW` en múltiplos de ATR(14) ∈ {3, 4, 6} y `maxBars` ∈ {12, 24, 48}.
- **Evento, semejanza y nulo al cierre:** idénticos a ESPEJO-SIM.
- **Estimand:** exceso contra costo / W, no contra cero.
- **Muestra:**
  - descubrimiento en SPY de 1 min 2008–2021 (Kaggle público, con limpieza de duplicados) agregado a 5 min;
  - replicación en ES jul-2025 a mar-2026;
  - confirmación única en abr–jun sólo si replica;
  - en SPY se mide información, no P&L;
  - costos de ES medidos, no transportados.
- **Qué la mataría:** exceso ≈ 0 en SPY, que no replique en ES, o que replique por debajo de costo / W.
- **Pre-registro escrito:** `docs/research/MANIFIESTO_ESPEJO_MACRO_ES_20260926.md` (espera el OK de Nico).
