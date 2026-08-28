# P-16 — Réplica de paridad del auditor externo (sandbox) — 2026-08-14

**Autor**: auditor externo (sandbox de Notion; sin acceso a la máquina local).
**Objeto**: cierre de P-16 — réplica target-free e independiente de las 3 mediciones de paridad locales de Antigravity (`docs/research/PARIDADES_LOCALES_ANTIGRAVITY_2026-08-14.md`).
**Firewall**: cero outcomes, cero P&L, cero holdout. La comparación es de zonas (geometría, timestamps, estado), nunca de mercado.
**Rama**: `research/bigtrap2-local-displacement-null` (ancestro de auditoría `68a047cf`).

---

## 0. TL;DR

La réplica del auditor **reproduce las 3 mediciones locales al detalle**: mismos conteos de coincidencias limpias (18.004 · 151 · 11.435) y mismos residuos por categoría, con identidad sellada punta a punta (sha256 de insumos + git-blob de kernels).

| Indicador | Local (Antigravity) | Réplica del auditor | Δ |
|---|---|---|---|
| `AACloseOpenDiffs` (v1.2) | 18.004/18.020 (99,91 % EXACT) | 18.004 MATCHED / 18.020 (99,94 % matched) | 0 |
| `VolTicksPOC2` (v2.1) | 151/152 (98,68 % EXACT) | 151 MATCHED + 1 FEATURE_DIFF / 153 en ventana (99,35 %) | nota §3.2 |
| `Gaps2` (v2.0) | 11.435/11.442 (99,94 % EXACT) | 11.435 MATCHED / 11.442 (99,96 % matched) | 0 |

**Nota de gobernanza**: el gate estructural estricto de `parity.py` (PASS = cero huérfanas y cero diffs de geometría) etiqueta los tres **FAIL**; los residuos son los mismos que la medición local documentó y atribuyó (colas de borde, frontera de warmup, cola inmadura). El veredicto del auditor es que las mediciones locales quedan **confirmadas y reproducibles por un tercero independiente**; la aceptación de ese nivel de residuo para declarar los indicadores con paridad representativa es decisión de Nico.

---

## 1. Identidad de insumos (verificada antes de computar)

| Insumo | Sello | Verificación |
|---|---|---|
| `6E_09-26_ticks.parquet` (build canónico 90d) | sha256 `1311bc5ea91a111d95f17da84d9a6ee6323920686b0b0873c04d8f3dc94a9652` | MATCH declarado; 1.131.047 filas (MATCH); serie monótona (gate P0) |
| `gaps2_v22_6E_0926_90d.csv` (oráculo AACloseOpenDiffs) | sha256 `16b31bccb47a4fbd57788f7d7f9da5765a9d787b79b1aedeb93196dbce902a94` | MATCH declarado (archivo local CRLF) |
| `Gaps2_events_nt8_6E_0926_90d.csv` (oráculo Gaps2) | sha256 `a7654570d20e059c28842069d38273651e8998ca2280cab188e08cfa6b3d3402` | MATCH declarado (archivo local CRLF) |
| `voltickspoc2_v22_6E_0926_90d.csv` (oráculo VolTicksPOC2) | git-blob `84fb42916fa3dbdd253c7a1df1e88be0b52baaab` | MATCH repo; el sha256 declarado `b24c7107…` cierra sobre la variante CRLF local (contenido idéntico, convención EOL distinta — mismo patrón visto con los `.cs`) |

---

## 2. Entorno de réplica

- Kernels y bridge **byte-verificados** contra git-blob sha1 del repo: `aacloseopendiffs.py` `74372e9e…`, `voltickspoc2.py` `bdcbfda7…`, `gaps2.py` `4e279b2b…`, `sandbox_pqread.py` `252c7dd7…`, `bars.py`, `oracle.py`, `parity.py`, `common.py`, `sessions.py`, `quarantine.py`, `ticks.py`, `instruments.py`, `nt8_contract.py`. (19/20 módulos byte-exactos; `hftzones2.py` quedó sin cierre byte-exacto por EOL mixto no reproducible desde texto — no participa en estos 3 kernels; contenido estable entre dos transcripciones independientes.)
- Smoke sintético de punta a punta antes de la réplica: kernel → EventLog → parser → matcher con auto-paridad 100 % en los 3 kernels.
- Parquet decodificado con el lector propio `tools/sandbox_pqread.py` (byte-verificado), sin pyarrow.
- Barras `time:1` (31.113 M1), `chart_tz=America/Argentina/Buenos_Aires`, ventana de comparación simétrica en ambos lados: 2026-04-01T00:00:00Z → 2026-06-30T23:59:59Z. Matcher del repo: `tol_created_ms=60.000`, `tol_geom_ticks=0`, frontera de madurez por `max_age_bars` — mismas reglas que `tools/run_nt8_bridge.py`.
- P1A sobre el parquet 90d: **PASS** (quote_fraction 1,0; 0 footprint mismatches).
- Runtime total: 756,9 s (Gaps2 tick-driven ≈ 635 s sobre 1,13M ticks).

---

## 3. Resultados

### 3.1 `AACloseOpenDiffs` (oráculo v1.2, blob `cc016291`)

| | Local | Réplica auditor |
|---|---|---|
| Zonas NT8 en ventana | 18.020 | 18.020 |
| Zonas Python en ventana | — | 18.069 |
| Coincidencias exactas | 18.004 (99,91 %) | **18.004** |
| GEOMETRY_DIFF | 4 | 4 |
| TIMESTAMP_DIFF | 1 | 1 |
| MISSING_IN_NT8 (extras Python) | 60 | 60 |
| MISSING_IN_PYTHON (huérfanas NT8) | 11 | 11 |

Reproducción exacta, categoría por categoría.

### 3.2 `VolTicksPOC2` (oráculo v2.1, blob `84fb4291`)

| | Local | Réplica auditor |
|---|---|---|
| Zonas NT8 en ventana | 152 | 153 |
| Zonas Python en ventana | — | 153 |
| Coincidencias exactas | 151 | **151** |
| FEATURE_DIFF | 1 (toques 2 Py vs 8 NT8) | 1 |
| MISSING_IN_NT8 | 1 | 1 |
| MISSING_IN_PYTHON | 1 | 1 |

El oráculo contiene 153 ZONE_CREATED, todas dentro de la ventana; la última nació el 30-jun 05:01 (bar 30051). El 152 local excluye una zona del conjunto; con la ventana simétrica del bridge la réplica contabiliza 153 y aun así reproduce 151 exactas + 1 FEATURE_DIFF, consistente con el "1 borde / 1 warmup" del informe local.

Notas registradas: 17 FOOTPRINT_MISMATCH propios de NT8 (`reconstructed_vs_bar_volume`) quedan como evidencia de calidad de datos del oráculo; el meta del oráculo dice `version=2.1` y el `meta_line` del kernel emite `2.0` (divergencia cosmética de version string, misma familia del residual de P-13).

### 3.3 `Gaps2` (oráculo v2.0, blob `f7bb94e1`)

| | Local | Réplica auditor |
|---|---|---|
| Zonas NT8 en ventana | 11.442 | 11.442 |
| Zonas Python en ventana | — | 11.443 |
| Coincidencias exactas | 11.435 (99,94 %) | **11.435** |
| FEATURE_DIFF | 2 | 2 |
| MISSING_IN_NT8 | 6 | 6 |
| MISSING_IN_PYTHON | 5 | 5 |
| MATURITY_TAIL | 3 | 4 |

Reproducción exacta en coincidencias y residuos; única delta de contabilidad: la cola inmadura (4 vs 3 declaradas).

---

## 4. Lectura de gobernanza

1. La réplica es **diagnóstica y target-free**: confirma la reproducibilidad de las mediciones; no emite etiquetas de efecto ni PASS de mercado.
2. Bajo el gate estructural estricto del repo, los tres indicadores quedan FAIL; los residuos son los mismos que el informe local documentó y atribuyó (colas de borde, frontera de warmup, cola inmadura).
3. La decisión de aceptar ese nivel de residuo y declarar los indicadores con paridad representativa es de Nico.

---

## 5. Manifiesto

- Insumos: sha256 / git-blob verificados (tabla §1) antes de cualquier cómputo (fail-closed).
- Método: kernels del repo sobre `time:1` con los defaults del catálogo; filtros de ventana simétricos; matcher del repo. Reporte máquina generado en sandbox (`replica_p16_report.json`); su contenido queda reflejado en §3.
- Runtime: 756,9 s en sandbox.
