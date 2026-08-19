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
   Estado: `HYPOTHESIS_REFINED_NOT_RUN` — manifiesto v1 **SUSPENDIDO**.
2. **La ruta crítica, ahora:** el `break` del escaneo por ciclos está corregido en
   origin (`ac45ff5c…`, HEAD `27d5d9b…`). Schema del runner = `censo_hz2a_superficie_v2`.
   **P-45 bloquea el censo v2** — Nico elige segmentación (a) golosa o (b) ciclos
   independientes de δ. Sin esa decisión el artefacto v2 nacería con estimand no escrito.
   Después: censo v2 (`supersedes` `8bd29ed9…`) → manifiesto v2 → STOP → F4.
   `docs/audits/ENTRADA_027_AUDITORIA_026_P45_P46_2026-08-18.md`
3. **P-46, leída bien:** 15 celdas de 60 son nulas por aritmética (30/30 ceros en v1).
   2 están recortadas, no muertas — en v1 son las más ricas (1.505) y 2 de las 8 vivas.
   Denominador que puede producir N: **45**, no 43. El «8 de 60» de la 020 es 8 de 45.
4. **El censo v1 queda como evidencia-con-defecto:** `docs/research/censo_hz2a_superficie_2026-08-18.json`
   (`argmin`). Manifiesto v1: `docs/research/H_Z2A_MANIFIESTO_NUMERICO_2026-08-18.md`.
5. **El crash NO fue el censo.** Culpable: la matriz de kernels. Regla: `filas × 48 B`;
   si pasa de 2 GB, avisar. Esa matriz no se re-corre como está. C2 no lanzado.
6. **Board:** P-41 resuelta. **P-42 abierta** (C2). P-43 medida. **P-44 abierta.**
   **P-45 abierta — bloquea v2.** **P-46 abierta — no bloquea; obliga a releer N.**
   Board: `PENDIENTE.md`.
7. **Capítulo 3 (costos) v1 vigente:** `docs/research/LEDGER_COSTOS_CAP3_2026-08-18.md`.
8. **Canal:** `docs/audits/CANAL_AUDITOR.md` (entradas 001→027).
   Contrato: `docs/TRACEABILITY.md`. Catálogo: `docs/notion/CATALOG.md`.
   Mapa: `docs/README.md`.

## Qué no tocar

Holdout · P&L · F4 sin STOP · `features.py` · `fix/g2-a1-*` · `COVERAGE_NEUTRAL` ·
la matriz de kernels como está · censo v2 antes de P-45. Firewall: outcomes `false`,
holdout sellado 2026-07-01 → 2026-12-31; la sesión del 01-07 abre 17:00 CT del 30-06
(`1782856800000000000` ns).

## Dónde está el resto

| Necesitás | Ir a |
|---|---|
| Punto de entrada frío | `README.md` + este archivo |
| Auditoría 026 (break, P-45, P-46) | `docs/audits/ENTRADA_027_AUDITORIA_026_P45_P46_2026-08-18.md` |
| Entrada 026 (Opus: dos causas) | `docs/audits/ENTRADA_026_DOS_CAUSAS_DE_LA_NO_ANIDACION_2026-08-18.md` |
| Auditoría del primer fix | `docs/audits/ENTRADA_025_AUDITORIA_FIX_GO_CONDICIONAL_2026-08-18.md` |
| Censo v1 (evidencia con defecto) | `docs/research/censo_hz2a_superficie_2026-08-18.json` |
| Manifiesto v1 (suspendido) | `docs/research/H_Z2A_MANIFIESTO_NUMERICO_2026-08-18.md` |
| Ledger de costos | `docs/research/LEDGER_COSTOS_CAP3_2026-08-18.md` |
| Contrato de trazabilidad | `docs/TRACEABILITY.md` |
| Mapa de `docs/` | `docs/README.md` |
| Acta D-1…D-8 | `docs/DECISIONES_2026-08-15.md` |

**Aporte al referente:** el instrumento se calibró otra vez antes de re-medir.
Falta la decisión de Nico sobre P-45; sin eso no hay superficie que elegir.
