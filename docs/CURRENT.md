# CURRENT — empezar acá

> Punto de entrada único. Una sesión nueva (Claude, auditor o Nico) lee esto
> antes de cualquier otra página. Si este archivo y Notion divergen, **manda
> el repo**.

**Rama viva:** `foundation/f0b-compatibility-probe`
**Fecha:** 2026-08-17
**Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Qué está vivo hoy

1. **Línea científica:** H-Z2A v4 — segunda aproximación a una zona tras near-miss.
   `docs/research/H_Z2A_V4_DEPURACION_EPISTEMICA_Y_DISENO_FINAL_2026-08-16.md`
   Portadores: BigTrap2 = fixture · aVolClusterPOI v0.5 = ciencia · Gaps2 = control.
2. **P-41 resuelta (entrada 015).** Leak medido: **5.319 ticks**, 7,0 h. Corte por
   trade date vía `sessions_cme`. El censo-superficie ya no está bloqueado por eso.
   `docs/audits/ENTRADA_015_P41_RESUELTA_Y_MEDIDA_2026-08-17.md`
2c. **`HFTZones2` transporta entre exchanges (P-43).** Primera paridad fuera de 6E:
   GC 06-26 (COMEX, `tick_size=0.1` no binario) da **3.626/3.630 = 99,89 %**, y el
   residual **no escala** con la ventana. El kernel no ramifica por instrumento:
   un segundo activo no re-testea el porteo, testea el calendario.
2b. **P-42 abierta: `aVolCellPOI2` NO tiene paridad.** 16 divergencias reales sobre
   678 zonas en 6E (warmup ya descontado). Es el único de los 7 kernels con paridad
   formal medida y fallada. `HFTZones2` sí pasó: 4.821/4.821. No transportar
   `aVolCellPOI2` a otros activos hasta cerrarla.
3. **Orden:** censo-superficie (60 celdas × 2 predicados) → manifiesto numérico →
   STOP de Nico → F4. G2-A1 sanea **en paralelo**, no es la ruta crítica.
4. **Board:** `PENDIENTE.md`. El board es el registro; Notion es publicación.
5. **Acta:** `docs/DECISIONES_2026-08-15.md` (D-1…D-8).
6. **Canal:** `docs/audits/CANAL_AUDITOR.md` (índice). Entradas 006+ viven en el repo.
7. **Trazabilidad:** `docs/TRACEABILITY.md` · catálogo `docs/notion/CATALOG.md`.

## Qué no tocar

Holdout · P&L · F4 sin STOP · `features.py` · `fix/g2-a1-*` · `COVERAGE_NEUTRAL`.
Firewall: outcomes `false`, holdout sellado 2026-07-01 → 2026-12-31; la sesión del
01-07 abre 17:00 CT del 30-06 (`1782856800000000000` ns).

## Dónde está el resto

| Necesitás | Ir a |
|---|---|
| Contrato de trazabilidad (Notion ↔ repo) | `docs/TRACEABILITY.md` |
| Catálogo de páginas por fecha / categoría / actualidad | `docs/notion/CATALOG.md` |
| Índice vivo en Notion | «EdgeLab · Índice de trazabilidad» |
| Handoff para la sesión que quedó al 14-ago | página Notion del 17-ago |

**Aporte al referente:** una sesión nueva deja de reconstruir el estado a partir
de 200 markdowns y 20 páginas sueltas. Lee L0 y trabaja.
