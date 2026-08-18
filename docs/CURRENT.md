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
2. **P-41 resuelta (entrada 015).** Leak medido: **5.319 ticks**, 7,0 h.
   `docs/audits/ENTRADA_015_P41_RESUELTA_Y_MEDIDA_2026-08-17.md`
3. **P-42 abierta (entrada 016): `aVolCellPOI2` NO tiene paridad.** 16 divergencias
   reales sobre 678 zonas en 6E. Causa acotada al umbral de anomalía. Es lo que
   rompe «los 6». No transportar a otros activos hasta cerrarla.
   `docs/audits/ENTRADA_016_P42_AVOLCELLPOI2_SIN_PARIDAD_2026-08-17.md`
4. **P-43 medida (entrada 017): HFTZones2 transporta a GC.** 3.626/3.630 = 99,89 %.
   Residual de 2 ABSORB que no escala. El porteo es costo por familia, no por activo.
   `docs/audits/ENTRADA_017_P43_HFTZONES2_TRANSPORTA_GC_2026-08-17.md`
5. **P-44 abierta (entrada 018): dos catálogos y params que no transportan.**
   Bridge 6 vs universo 11. gaps2: 10 zonas en ZB, 113.298 en NQ.
   `docs/audits/ENTRADA_018_P44_DOS_CATALOGOS_Y_PARAMS_2026-08-17.md`
6. **Orden:** P-42 (paridad del conjunto) · censo-superficie → manifiesto → STOP
   de Nico → F4. G2-A1 sanea **en paralelo**. Multiactivo espera decisión P-44b.
7. **Procedencia dirty-aware.** Las cuatro paridades se re-corrieron con el árbol
   limpio y se re-versionaron: `medicion_comprometida: false` en las cuatro. El
   driver ahora registra **qué** estaba sucio, no un booleano suelto — el campo
   que hay que mirar se **deriva** de si hay `edgelab/`, `diag/` o el propio
   driver sin commitear, no de la presencia de un README sin trackear.
8. **Board:** `PENDIENTE.md`. El board es el registro; Notion es publicación.
9. **Canal:** `docs/audits/CANAL_AUDITOR.md` (índice). Entradas 006+ viven en el repo.

## Qué no tocar

Holdout · P&L · F4 sin STOP · `features.py` · `fix/g2-a1-*` · `COVERAGE_NEUTRAL`.
Firewall: outcomes `false`, holdout sellado 2026-07-01 → 2026-12-31; la sesión del
01-07 abre 17:00 CT del 30-06 (`1782856800000000000` ns).

## Dónde está el resto

| Necesitás | Ir a |
|---|---|
| Contrato de trazabilidad | `docs/TRACEABILITY.md` |
| Catálogo Notion ↔ repo | `docs/notion/CATALOG.md` |
| Acta D-1…D-8 | `docs/DECISIONES_2026-08-15.md` |

**Aporte al referente:** una sesión nueva lee L0 y trabaja. P-42 es el camino corto.
