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
   Estado: `HYPOTHESIS_REFINED_NOT_RUN` — manifiesto v1 redactado y **suspendido**.
2. **La ruta crítica, ahora:** el fix del censo **está en origin** (`d7ae642`, HEAD
   `2d8533c`) y el auditor lo pasó (entrada 025): el `argmin` ya no mata near-misses;
   C-A 8/8; memoria neutra 120/120. **GO condicional** al censo v2 — falta:
   (a) `SCHEMA_VERSION` a v2 (sigue diciendo v1 y la definición cambió),
   (b) declarar celdas independientes en δ (hay marginales negativos),
   (c) Nico confirma máquina estable.
   Después: censo v2 (`supersedes` el blob `8bd29ed9…`) → manifiesto v2 → STOP → F4.
   `docs/audits/ENTRADA_025_AUDITORIA_FIX_GO_CONDICIONAL_2026-08-18.md`
3. **El censo v1 queda como evidencia-con-defecto:** `docs/research/censo_hz2a_superficie_2026-08-18.json`
   Manifiesto v1: `docs/research/H_Z2A_MANIFIESTO_NUMERICO_2026-08-18.md` (`SUSPENDIDO_PENDIENTE_CENSO_V2`).
4. **El crash NO fue el censo.** Culpable: la matriz de kernels. Regla: `filas × 48 B`;
   si pasa de 2 GB, avisar. Esa matriz no se re-corre como está.
5. **Board:** P-41 resuelta. **P-42 abierta** — C2 estima memoria antes de lanzar.
   P-43 medida. **P-44 abierta.** Board: `PENDIENTE.md`.
6. **Capítulo 3 (costos) v1 vigente:** `docs/research/LEDGER_COSTOS_CAP3_2026-08-18.md`.
7. **Canal:** `docs/audits/CANAL_AUDITOR.md` (entradas 001→025).
   Contrato: `docs/TRACEABILITY.md`. Catálogo: `docs/notion/CATALOG.md`.
   Mapa: `docs/README.md`.

## Qué no tocar

Holdout · P&L · F4 sin STOP · `features.py` · `fix/g2-a1-*` · `COVERAGE_NEUTRAL` ·
la matriz de kernels como está. Firewall: outcomes `false`, holdout sellado
2026-07-01 → 2026-12-31; la sesión del 01-07 abre 17:00 CT del 30-06
(`1782856800000000000` ns).

## Dónde está el resto

| Necesitás | Ir a |
|---|---|
| Punto de entrada frío | `README.md` + este archivo |
| Auditoría del fix (GO condicional) | `docs/audits/ENTRADA_025_AUDITORIA_FIX_GO_CONDICIONAL_2026-08-18.md` |
| Orden y bug del censo | `docs/audits/ENTRADA_023_CENSO_V1_CON_BUG_Y_MANIFIESTO_SUSPENDIDO_2026-08-18.md` |
| Censo v1 (evidencia con defecto) | `docs/research/censo_hz2a_superficie_2026-08-18.json` |
| Manifiesto v1 (suspendido) | `docs/research/H_Z2A_MANIFIESTO_NUMERICO_2026-08-18.md` |
| Ledger de costos | `docs/research/LEDGER_COSTOS_CAP3_2026-08-18.md` |
| Contrato de trazabilidad | `docs/TRACEABILITY.md` |
| Mapa de `docs/` | `docs/README.md` |
| Acta D-1…D-8 | `docs/DECISIONES_2026-08-15.md` |

**Aporte al referente:** el instrumento se verificó en origin antes de re-medir.
El censo v2 todavía no corre: nueva definición, nueva etiqueta.
