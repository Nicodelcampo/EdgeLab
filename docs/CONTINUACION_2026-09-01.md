# CONTINUACIÓN — cambio de máquina (2026-09-01)

**Motivo:** Nico cambia de computadora; el historial local de Claude de los últimos
3 días no migra. Este documento es el punto de entrada único para retomar el
trabajo desde el repo, sin depender de memoria de chat. Si algo acá contradice
otro archivo, gana el git log y los hashes.

## Orden de lectura para un agente nuevo

1. `CLAUDE.md` y `AGENTS.md` (raíz) — convenciones del repo y del proyecto.
2. `docs/DECISIONES_NICO_2026-08-30.md` — D1 a D7, las decisiones de Nico con
   fecha y alcance (última: D7 = freeze de power inputs Gate 1 NQ).
3. `PENDIENTE.md` (esta rama) — tablero de hipótesis P-49…P-59 (restaurado e
   íntegro desde `bca71898`).
4. `docs/audits/CANAL_NOTION_AI_2026-08-30_*.md` y `CANAL_NOTION_AI_2026-09-01_*.md`
   (entradas 013 a 027, esta rama) — el registro corrido de los últimos 3 días:
   corrigendum D6, spec SL/TP, handoff Antigravity, T2, freeze de poder, las 3
   palancas, ML/LightGBM, y la auditoría de paridad aVolClusterPOI (022 a 026).
5. Este documento.

## Mapa de ramas vivas (qué hay en cada una, tip al 2026-09-01)

| Rama | Contenido | Tip |
|---|---|---|
| `audit/notion-ai-sltp-p2b-provenance-20260830` | Canal del auditor (001-027), DECISIONES, PENDIENTE.md (restaurado), registro de hipótesis | `bca71898`+ |
| `research/bt2a-nq-gate1-nrand-capacity-t2-20260830` | **Linaje canónico Gate 1 NQ**: specs, evidencia T2, módulo de capacidad, **freeze de power inputs (`d45d3943`)** | `6d585e3` + freeze |
| `research/bt2a-nq-gate1-power-closure-20260830` | Specs fusionadas + suite preflight + módulo de contratos (corrigendum D6 `cb844244`) | — |
| `research/bt2a-nq-gate1-outcomes-runner-v1-20260830` | Motores de Claude (outcomes runner) | `d229bbb2` |
| `research/bt2a-gc-sltp-breakeven-design-v1-20260830` | Spec de campaña SL/TP+breakeven GC (`5dd58f29`, sha256 `6d504492…`) | `5dd58f29` |
| `research/avolcluster-nq-parity-oracle-20260901` | Línea de paridad aVolClusterPOI NQ: oráculos (`data/nt8_oracles/`), doc de causa raíz, reportes JSON del gate, adaptador `run()`, lanzadores Kaggle, test de invariante del auditor | `eb40171c` |
| `research/avolcluster-nq-lifecycle-v1-20260830` | Spec del runner de ciclo de vida AVol en NQ (post-Gate-1) | — |

## Estado de tokens (Gate 1 NQ)

Secuencia de 4 tokens; **1/4 hecho**:

1. ✅ `APPROVE_FREEZE_BT2A_NQ_GATE1_POWER_V1` (2026-08-30 23:49 ART) — aplicado en
   `d45d3943` @ `research/bt2a-nq-gate1-nrand-capacity-t2-20260830`:
   power design `FROZEN_POWER_INPUTS`, payload `285e5fb1…`, archivo
   `05fb1d72…`; spec principal repineado `980176d6…`. Verificado byte-exacto por
   el auditor.
2. ⬜ `APPROVE_FREEZE_BT2A_NQ_GATE1_V1` (freeze del spec completo) — **requiere
   antes la consolidación de ramas** (la hace el auditor: el linaje canónico hoy
   está en la rama T2; preflight/tests en power-closure; motores en
   outcomes-runner).
3. ⬜ `AUTHORIZE_IMPLEMENT_BT2A_NQ_GATE1_16CELL_V1` (Claude escribe el CLI).
4. ⬜ `AUTHORIZE_RUN_BT2A_NQ_GATE1_V1` (la corrida).

**Power inputs congelados:** MDE 2,90 / SD 11,528529 / 228 de 234 sesiones /
N_RAND capacity OK (152.695 eventos, 2.359 estratos, 0 failing, 65
INSUFFICIENT_HISTORY; kernel Kaggle `bt2a-nq-n-rand-capacity-check-t2` v3,
580,58 s, ~95M ticks; reporte sha256 `f1777c66…`).

## Líneas abiertas y próximo paso de cada una

### A. Gate 1 NQ (prioridad D3)
- **Bloqueo actual:** consolidación de ramas (auditor) → token 2 (Nico).
- **Deuda registrada:** Claude debe el artefacto P2B o retracción escrita;
  el auditor detectó que la suite preflight no verifica que los pins de
  dependencias re-hasheen sus archivos (agregar el chequeo — el "42/42 PASS"
  de Antigravity pasó con un pin roto).

### B. Campaña SL/TP + breakeven (GC)
- Spec escrito y pineado; **freeze bloqueado** hasta que exista la suite de
  verdad conocida Romano-Wolf + MCS (candidata a primer uso de GitHub Actions
  según P-58) + artifacto P2B + auditoría de la capa store.

### C. Paridad aVolClusterPOI NQ 06-26 (rama propia)
- Gate en **FAIL, con mapa causal completo** (canal 022-026): lógica idéntica
  línea por línea (Claude), build Python auto-consistente (test de invariante
  del auditor, `eb40171c`), divergencia residual asignada al oráculo NT8
  (doble serie interna, clase TICKBAR-001). La caracterización "siempre borde
  superior, 1-2 ticks" del doc de causa raíz fue corregida por recomputo:
  ambos bordes, ambas direcciones, outliers de 3 y 8 ticks.
- **Tareas de Claude (canal 025/026):** (1) alinear secuencias tickbar y
  re-clasificar TICKBAR-001; (2) instrumentación Python por bloque
  (bucket/score/threshold/n_samples) + dump de geometrías de zonas Python;
  (3) outlier de 8 ticks (nt8=413/py=372) individual; (4) rerun del gate.
- **Tolerancia: decisión de Nico, SOLO con el residual medido** después de (1)-(4).

### D. Infraestructura (P-58, decidida por Nico)
- Las 3 palancas: TPU-VM Kaggle como CPU (96c/330GB) para lo data-bound;
  GitHub Actions para lo data-free (primer uso: suite RW/MCS); Polars/DuckDB
  con puerta de determinismo byte-idéntico.
- P-59 (ML/LightGBM como generador de hipótesis): research hecho, adopción
  pendiente de Nico; sin código todavía.

## Entorno externo (no está en el repo)

- Kernels Kaggle (cuenta `nicolasbuttaro`): `bt2a-nq-n-rand-capacity-check-t2`
  v3 (T2, completado), lanzadores de paridad en `kaggle/` de la rama de paridad.
- Datasets Kaggle: `edgelab-avolcluster-nq-oracle`, `edgelab-tickbar-diag-nq0626`,
  `edgelab-ticks-nq-preholdout` (parquet NQ 06-26, sha256 `3de249b9…`).
- Handoff de Antigravity (Google): `docs/research/HANDOFF_ANTIGRAVITY_T2_NRAND_CAPACITY_2026-08-30.md`.

## Incidentes del período (registrados, no escondidos)

- El board `PENDIENTE.md` estuvo roto (placeholder) entre `b3ffe800` y
  `bca71898` por errores del auditor; las entradas de canal 019/021/022/023
  contienen afirmaciones falsas sobre su restauración, corregidas en las
  propias entradas 023/024 y cerradas con la restauración verificada
  (15.003 bytes, blob `f924a60d…`). Lección permanente: las etiquetas no son
  contenido; verificar antes de afirmar.
- Antigravity cerró T2 con un pin de dependencia roto y un payload mal citado
  (datos y cómputo correctos; etiquetas no) — corregido por el acto de freeze.

*Escrito por el auditor (Notion AI) el 2026-09-01, verificado contra el repo
al momento de escribir.*
