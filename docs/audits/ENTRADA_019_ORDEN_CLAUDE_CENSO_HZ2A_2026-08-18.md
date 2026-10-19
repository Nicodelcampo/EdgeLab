# Entrada 019 · Auditor → Opus · Orden de trabajo: censo H-Z2A (2026-08-18)

**Rama:** `foundation/f0b-compatibility-probe`.
**HEAD de referencia al redactar:** `eed104383d624133ad1246d6b191d0f05869d500`.
**Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.
**Línea:** `docs/research/H_Z2A_V4_DEPURACION_EPISTEMICA_Y_DISENO_FINAL_2026-08-16.md`.
**Grilla y predicado:** entrada 014.
**Firewall:** entrada 015 (P-41 resuelta).

Nico pidió preparar las tareas. Esta entrada **es** la orden. No es un P-NN nuevo.
Si Notion y el repo divergen, **manda el repo**.

---

## Determinación

H-Z2A está `HYPOTHESIS_REFINED_NOT_RUN`. El papel avanzó; el objeto no.
P-41 ya no bloquea. El addendum 007 manda población (cap. 5) **antes** de F4
(cap. 1). Por eso el censo va primero y el manifiesto espera al N del censo.

P-42 (paridad de `aVolCellPOI2`) es higiene del conjunto de P-32. **No** es la
ruta crítica hacia una cuenta. Corre en paralelo **solo si no retrasa el censo**.

P-43 ya midió que el porteo transporta. P-44 bloquea H-Z2A **multiactivo** con
params fijos — no bloquea el censo en 6E.

---

## Máquina

Esta orden es para la máquina **con** `research-v2` (la que midió P-41 / P-42 /
P-43). El censo necesita los parquets. La máquina que sólo tiene `C:` no puede
correr C1.

Confirmar antes de medir, y anclar en el artefacto:

- parquet 6E canónico y su sha256
- `FIREWALL_CUTOFF_NS` del runner = `session_bounds_utc_ns(20260701)[0]`
- `holdout_included` **computado**
- outcomes `false`

---

## C1 — censo-superficie (ruta crítica, ahora)

Correr el censo outcome-free de H-Z2A v4 sobre el portador real:
`aVolClusterPOI` v0.5 vía `diag/tasa_senales/avolcluster_tick_formal.py`.
Control: `Gaps2`. BigTrap2 no entra como ciencia.

Condiciones de la 014, no negociarlas acá:

1. Grilla de 60 celdas.
2. Dos predicados (near-miss primario = **ningún trade** dentro de `[L,U]`;
   quote como sensibilidad declarada, no mezclada).
3. `δ_nm` también en unidades de spread del contrato.
4. Anillos marginales **y** acumulados.
5. `n` = sesiones por celda, no sólo eventos.
6. Ciego a outcomes / MFE / MAE / P&L. Si el runner los toca, el artefacto no
   entra.

**Entregable, mismo commit:**

- JSON de censo en `docs/research/` con procedencia (parquet sha256, blob del
  runner, HEAD, `firewall` computado, predicado, grilla).
- Entrada de canal que cite ese path. Si abre un `P-NN`, `PENDIENTE.md` en el
  mismo commit.
- `docs/CURRENT.md` actualizado en el mismo commit (`test_current_md.py`).

**Qué cuenta como éxito de C1:** una tabla de población por celda, o la muerte
de variantes por N insuficiente. No un edge. No un manifiesto.

---

## C2 — P-42, paralelo, no bloquea C1

Comparar umbral por bucket y sesión: `threshold`, `empirical_pct`, `robust_z`,
`sample_count`, `session_count` del oráculo (`OBS`) contra el kernel.
Criterio de cierre ya escrito en P-42.

No transportar `aVolCellPOI2` a otro activo. Si C1 y C2 compiten por la
máquina, **gana C1**.

Corregir de paso el path falso del board:
`runs/paridad_avolcellpoi2_30d_w12.json` no existe; el artefacto es
`docs/research/paridad_avolcellpoi2_30d_2026-08-17.json`.

---

## C3 — después del STOP de Nico, no ahora

Módulos z2a / `validity.py` / Q-DINÁMICA. El manifiesto lo redacta el auditor
cuando exista el N del censo. F4 no arranca sin STOP explícito de Nico.

---

## Fuera de esta orden

| Cosa | Por qué no |
|---|---|
| F4, outcomes, P&L, holdout | STOP no dado; firewall sigue cerrado |
| `features.py` | API del censo; no se cambia durante la medición (P-39) |
| `fix/g2-a1-*`, `COVERAGE_NEUTRAL` | semántica de gates; no es cap. 5 |
| H-Z2A en ES/NQ/YM/GC | P-44b: params fijos no comparan el mismo fenómeno |
| Inventarios L2/GEX | C4; no bloquean el censo-superficie |
| P-33(a), matriz kernels×activos | higiene; no retrasa C1 |

---

## Lo que no decide Claude

W7 (comisión broker). STOP del manifiesto. Borrar V1 de Kaggle. Semántica
P-35 / P-37. Normalizar umbrales vs pre-registrar por activo (P-44b).

## Aporte al referente

Convierte «H-Z2A está diseñada» en una población medida o en una muerte de
variantes. Eso es capítulo 5. No es otro P-NN de paridad.
