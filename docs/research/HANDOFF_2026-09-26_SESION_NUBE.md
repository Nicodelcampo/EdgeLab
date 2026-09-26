# HANDOFF 2026-09-26 — sesión en la nube (Claude Code web): TBZX-R3, mapa IVC e IVC-L

**Para:** cualquier sesión local de Claude (o Nico) que retome sin acceso a la conversación que produjo esto.
**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Rama:** `claude/focused-fermat-qjt805` (contiene un merge de `feat/unified-nt8-viewer-20260920`; se trabaja sobre ella).
**PR:** https://github.com/Nicodelcampo/EdgeLab/pull/59 (borrador, base `feat/unified-nt8-viewer-20260920`, CI en verde
al 2026-09-26 11:30 UTC).

```
git fetch origin claude/focused-fermat-qjt805
git checkout claude/focused-fermat-qjt805
python tools/estado.py        # la rama declarada en CLAUDE.md sigue siendo otra: esta es una rama auxiliar
```

## 1. Resumen en tres líneas

1. **TBZX-R3 (reingreso a la franja TBZX, ES) — CERRADA.** La zona tiene ~+2 a +3 pp de dirección sobre un control
   fantasma (~0,2 t), pero con costo realista (~1,5 t) no hay nada operable: 0 de 66.000 celdas, 0 de 14.464 escenarios macro.
2. **IVC (mapa información contra costo, ES/NQ/YM, 9 meses) — 0 prometedoras.** En horizonte corto la información existe
   y no paga el costo (2,4–7 t). En horizonte largo el borde se acerca al costo pero sin potencia.
3. **IVC-L (horizonte largo con años: SPY/QQQ/DIA diario 1993–2026, SPY 1 min 2008–2021) — 0 prometedoras.** El gap
   diario no predice el día; queda una sola pista (gap → continuación 10:00–cierre) sin margen en validación.

**Conclusión operativa:** con precio, flujo, VWAP, gap, zonas y hora, en ningún horizonte probado hay una celda que
justifique pre-registrar una regla sobre estos índices. Próxima línea sugerida (no empezada): cambiar de fuente de
información, por ejemplo eventos macro programados (CPI, FOMC, NFP) o spreads entre mercados.

## 2. Documentos a leer (en este orden)

| Documento | Qué tiene |
|---|---|
| `docs/CURRENT.md` (líneas 13–15) | estado vivo resumido |
| `docs/research/TBZX_R3_ACTA_CIERRE_20260926.md` | acta de cierre de TBZX-R3 con alcance preciso |
| `docs/research/MANIFIESTO_TBZX_REINGRESO_3T_20260925.md` | pre-registro + enmiendas §8–§10 (iteraciones 2–4) |
| `docs/research/IVC_RESULTADOS_20260926.md` | mapa información vs costo (ES/NQ/YM) |
| `docs/research/MANIFIESTO_MAPA_INFO_COSTO_20260926.md` | pre-registro IVC + enmienda §8 |
| `docs/research/IVC_LARGO_RESULTADOS_20260926.md` | horizonte largo con años de historia |
| `docs/research/MANIFIESTO_IVC_LARGO_20260926.md` | pre-registro IVC-L |

## 3. Cerebro (edge_brain)

| Ledger | Contenido |
|---|---|
| `artifacts/hippocampus/tbzx_r3_20260926.jsonl` | partición `P-TBZX-R3-EXP` (181 sesiones ES), lecciones de método `LES-R3-ENTRY-AT-LEVEL-GAP`, `LES-R3-TRADE-PRICE-BOUNCE`, observación `OBS-TBZX-R3-IT3-LOCAL46` (auditoría CTRL_TIMING_V1 PASS), evidencias IT1, IT2 e IT4 |
| `artifacts/hippocampus/ivc_20260926.jsonl` | particiones `P-IVC-EXP` y `P-IVCL-EXP`, observaciones `OBS-IVC-MAPA-20260926` y `OBS-IVCL-20260926`, 4 lecciones |

Notas del cerebro aprendidas en la sesión:
- Sólo acepta lecciones `PROPOSED`/`LOW` (la adjudicación es aparte).
- Una observación `RESPONSE_PROFILE` con `design="EVENT_VS_CONTROL"` exige una auditoría de controles PASS. Las
  corridas sin pares de control guardados (IT1, IT2, IT4) quedaron como **lecciones de evidencia**, no como observaciones.
- IVC e IVC-L usan `design="OTHER"` (estado en grilla contra nulo entre sesiones o por desplazamiento circular).
- Los ledgers están en `.gitignore`: se agregan con `git add -f`.

## 4. Código nuevo

| Archivo | Uso |
|---|---|
| `tools/tbzx_reingreso_kaggle.py` | kernel TBZX-R3 (modo `eventos` por defecto = iteración 4; `R3_MODE=agg` = iteraciones 1–3). Autocontenido para Kaggle. Variables `R3_DATA`, `R3_OUT`, `R3_MAXSESS`, `R3_WORKERS` |
| `tools/tbzx_r3_macro.py` | análisis de escenarios macro (iteración 4) |
| `tools/tbzx_r3_brain.py` | `declare` / `ingest` / `evidence` en el cerebro para TBZX-R3 |
| `tools/mapa_info_costo_kaggle.py` | kernel IVC: grilla de 5 min con estados causales y retornos futuros (`IVC_INST`, `IVC_INSTS`) |
| `tools/mapa_info_costo_analisis.py` | análisis IVC (IC, borde por apuesta, margen, nulo entre sesiones, FDR) |
| `tools/ivc_largo.py` | IVC-L sobre proxies ETF; `--selftest` corre la prueba nula |

Todas las herramientas se validaron sobre un random walk sintético antes de medir. Errores que la prueba nula atrapó y
que ya están corregidos (vale la pena conocerlos): entrada «perfecta» al precio del nivel cuando el trade lo saltó
(+2,5 pp falsos); medir dirección al precio de trade (rebote bid/ask); celdas con < 20 sesiones (nulo degenerado);
signo de validación elegido en la propia validación.

**Para Kaggle**, el kernel IVC se empaqueta concatenando los dos archivos:

```
{ sed '/^if __name__ == "__main__":/,$d' tools/tbzx_reingreso_kaggle.py; echo 'R = None';
  sed -n '/^NS_ = /,$p' tools/mapa_info_costo_kaggle.py | sed 's/^    R.INST = inst/    global INST; INST = inst/; s/R\.\(bars25\|detect\|E0\|R_END\|load_sessions\)/\1/g'; } > ivc_kernel.py
```

## 5. Datos y artefactos que NO están en el repo

| Qué | Dónde | Cómo reproducir |
|---|---|---|
| Ticks ES/NQ/YM pre-holdout | Kaggle `nicolasbuttaro/edgelab-ticks-{es,nq,ym}-preholdout` (privados) | `kaggle datasets download ...` |
| Salidas de los kernels | Kaggle: `edgelab-tbzx-r3`, `-v2`, `-v3`, `-v4`, `edgelab-ivc-mapa` | `kaggle kernels output nicolasbuttaro/<slug> -p <dir>` |
| SPY/QQQ/DIA diario | Yahoo chart API (`/v8/finance/chart/<T>?period1=0&period2=1775001600&interval=1d&events=div`) | sha256 en `artifacts/ivc/ivcl_resumen.json` |
| SPY 1 min 2008–2021 | Kaggle público `rockinbrock/spy-1-minute-data` (tercero, sin licencia declarada: sólo uso interno) | sha256 `81d936c7…c49b`; tiene 638.054 filas duplicadas idénticas que `ivc_largo.py` elimina |

En el repo sí están: `artifacts/ivc/ivc_mapa.csv`, `ivcl_celdas.csv` y sus resúmenes (citados por el cerebro).

## 6. Pendientes

1. **Kernel `edgelab-tbzx-r3-v3`**: terminó CANCEL_ACKNOWLEDGED a las ~15:30 UTC del 26/09, sin salida (registrado en el cerebro como `LES-TBZX-R3-IT3-KAGGLE181-CANCEL`; no se relanza). Texto original: Si
   terminó: `kaggle kernels output nicolasbuttaro/edgelab-tbzx-r3-v3 -p kout3` y
   `python tools/tbzx_r3_brain.py ingest --tag IT3-KAGGLE181 --dir kout3 --ctrl kout3`. Sólo reabre el acta si contradice
   a la corrida local de 46 sesiones (0 FDR realista). Si murió por tiempo, no relanzar sin decisión de Nico.
2. **Token de Kaggle:** se pegó en el chat de la sesión; **regenerarlo** en Kaggle. No está en el repo.
3. **Historia de 1 min de ES/NQ/YM de varios años (NT8/Tradovate):** sólo tiene sentido si se quiere re-medir en
   futuros la pista «gap → continuación 10:00–cierre». Con IVC-L, la prioridad bajó.
4. **Corpus SSRN:** no está accesible en sesiones en la nube (el `.rar` vive en la PC de Nico). Sugerido: dataset privado
   en Kaggle para que la corteza bibliográfica funcione en la nube.
5. **Próxima línea (propuesta, sin empezar):** familia de eventos macro programados (CPI/FOMC/NFP) u otras fuentes de
   información; requiere registro de familia, manifiesto y OK de Nico (regla STOP).

## 7. Decisiones de Nico tomadas en esta sesión

- Diseño TBZX-R3: zona → se aleja D → vuelve → penetra p → retrocede r (espera 30 s, se cancela en el borde opuesto),
  medido con ejecución perfecta y realista; excluir configuraciones con pocas zonas; «que todo pase por el cerebro».
- Iterar hacia escenarios macro que le ganen a la fricción; luego mapa información/costo («Primero iterá y luego lanzalo»).
- «Ok a todo» y «Hacé lo necesario ahora»: autorizó actualizar el hash de `NORTH_STAR` fijado en los `diag/tasa_senales/F*`.
  Ojo: `tools/bt2_absorption_param_sweep.py` **no** se toca: compara contra su spec congelado (commit `5b9beef`).
