# CURRENT — empezar acá

> Punto de entrada único. Una sesión nueva (Claude, auditor o Nico) lee esto
> antes de cualquier otra página. Si este archivo y Notion divergen, **manda
> el repo**.

**Rama viva:** `foundation/f0b-compatibility-probe`
**Fecha:** 2026-08-18
**Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Qué está vivo hoy

1. **Línea científica:** H-Z2A v4 — segunda aproximación a una zona tras near-miss.
   `docs/research/H_Z2A_V4_DEPURACION_EPISTEMICA_Y_DISENO_FINAL_2026-08-16.md`
   Portadores: BigTrap2 = fixture · aVolClusterPOI v0.5 = ciencia · Gaps2 = control.
   Estado: `HYPOTHESIS_REFINED_NOT_RUN` — con manifiesto v1 redactado y **suspendido**
   (ver ítem 3).
2. **La ruta crítica, paso a paso (orden vigente):** censo v1 corrido (entrada
   020) → verificado internamente por el auditor (entrada 021: runner ciego a
   outcomes por construcción, artefacto consistente al dígito en 120/120 celdas)
   → **el gate de ceguera C-A expuso un defecto real en el runner** y el auditor
   lo confirmó contra el código (entrada 023: el `argmin` sobre todo el corredor
   mataba near-misses legítimos; la v1 subcuenta) → manifiesto v1 redactado
   (entrada 022) y **SUSPENDIDO** (entrada 023).
   **Próximo paso:** Opus pushea el fix (escaneo por ciclos) + el test C-A → el
   auditor audita el fix → Nico confirma máquina estable → **censo v2** (etiqueta
   nueva, `supersedes` declarado) → **manifiesto v2** → **STOP de Nico** → F4.
   `docs/audits/ENTRADA_023_CENSO_V1_CON_BUG_Y_MANIFIESTO_SUSPENDIDO_2026-08-18.md`
3. **El censo v1 queda como evidencia-con-defecto, etiquetado — no se borra:**
   `docs/research/censo_hz2a_superficie_2026-08-18.json`
   El manifiesto v1 queda `SUSPENDIDO_PENDIENTE_CENSO_V2`, con sus números como
   registro (no cifra vigente):
   `docs/research/H_Z2A_MANIFIESTO_NUMERICO_2026-08-18.md`
4. **El crash de la máquina NO fue el censo** (pico 3,38 GB). Culpable: la matriz
   de kernels 7×11 — `load_canonical_parquet` lee el archivo completo antes de
   recortar por días (pico ~9 GB en MNQ_03-26, el mismo número que P-25 midió el
   15-ago). Regla nueva: `filas × 48 B` antes de correr; si pasa de 2 GB, avisar.
   La matriz no se re-corre como está (row-groups o pushdown a pyarrow).
5. **Board:** P-41 resuelta (entrada 015). **P-42 abierta** — C2 en paralelo, sin
   retrasar la ruta. P-43 medida (99,89 % en GC). **P-44 abierta** — no hacer
   H-Z2A multiactivo con params fijos. Board completo: `PENDIENTE.md`.
6. **Cambio de auditor (18-ago).** Las entradas 001-005 del canal vivían SOLO en
   Notion; están rescatadas en `docs/audits/ESPEJO_ENTRADAS_001_005_NOTION_2026-08-18.md`
   (origen Notion, **sin blob verificable**). Sin respaldo aún: «Handoff al 14-ago»,
   «Orden de trabajo 15-ago» y los 12 snapshots del zip.
7. **Plan que conecta todo:** `docs/PLAN_RUTA_A_UNA_CUENTA_2026-08-18.md` —
   debilidad → capítulo → estado → qué la mueve, y el grafo de qué bloquea a qué.
8. **Spec de `validity.py`** (absorbe P-39): `docs/research/VALIDITY_PY_SPEC_2026-08-18.md`.
   Construirlo es C3 — espera el STOP.
9. **Canal Opus ↔ Auditor:** `docs/audits/CANAL_AUDITOR.md` (entradas 001→023).
   Contrato Notion ↔ repo: `docs/TRACEABILITY.md`. Catálogo: `docs/notion/CATALOG.md`.
   Mapa de `docs/`: `docs/README.md`.

## Qué no tocar

Holdout · P&L · F4 sin STOP · `features.py` · `fix/g2-a1-*` · `COVERAGE_NEUTRAL` ·
la matriz de kernels como está (crash del 18-ago). Firewall: outcomes `false`,
holdout sellado 2026-07-01 → 2026-12-31; la sesión del 01-07 abre 17:00 CT del
30-06 (`1782856800000000000` ns).

## Dónde está el resto

| Necesitás | Ir a |
|---|---|
| Punto de entrada frío (chat de Notion, sesión nueva) | `README.md` + este archivo |
| Orden vigente y el bug del censo | `docs/audits/ENTRADA_023_CENSO_V1_CON_BUG_Y_MANIFIESTO_SUSPENDIDO_2026-08-18.md` |
| El censo v1 (evidencia con defecto) | `docs/research/censo_hz2a_superficie_2026-08-18.json` |
| El manifiesto v1 (suspendido) | `docs/research/H_Z2A_MANIFIESTO_NUMERICO_2026-08-18.md` |
| Contrato de trazabilidad | `docs/TRACEABILITY.md` |
| Mapa de `docs/` | `docs/README.md` |
| Acta D-1…D-8 | `docs/DECISIONES_2026-08-15.md` |

**Aporte al referente:** el instrumento se verifica antes de creerle a la medición.
El gate que no existía encontró el defecto al escribirse; el registro no se
limpia — se asienta el siguiente commit.
