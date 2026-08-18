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
   Estado: `HYPOTHESIS_REFINED_NOT_RUN`.
2. **C1 CORRIDO (entrada 020).** Censo-superficie: 228 sesiones, 575 zonas,
   **8 de 60 celdas viven por N (>= 403)**; 52 mueren. `holdout_included` false
   computado, `medicion_comprometida` false, 4 parquets canonicos verificados.
   `docs/research/censo_hz2a_superficie_2026-08-18.json`
   Siguiente: manifiesto (auditor, con este N) -> STOP de Nico -> F4.
2b. **Orden vigente (entrada 019):** **C1 censo-superficie ahora** → manifiesto
   (auditor, con el N del censo) → STOP de Nico → F4.
   P-42 en paralelo **solo si no retrasa C1**. G2-A1 sanea en paralelo.
   `docs/audits/ENTRADA_019_ORDEN_CLAUDE_CENSO_HZ2A_2026-08-18.md`
3. **P-41 resuelta (entrada 015).** Leak 5.319 ticks. El censo ya no está bloqueado.
4. **P-42 abierta.** `aVolCellPOI2` FAIL. Higiene del conjunto, no la ruta crítica.
5. **P-43 medida.** HFTZones2 en GC: 3.626/3.630. El porteo transporta.
6. **P-44 abierta.** No hacer H-Z2A multiactivo con params fijos.
7. **Cambio de auditor (18-ago).** Las entradas 001-005 del canal vivian SOLO en
   Notion; estan rescatadas en `docs/audits/ESPEJO_ENTRADAS_001_005_NOTION_2026-08-18.md`
   (origen Notion, **sin blob verificable** — la regla 3 no se puede cumplir con
   ellas). La cadena `P-31 -> diferencial -> merge B -> P-38 -> G2` quedo asentada en
   el board; no estaba en ningun lado. Sin respaldo aun: «Handoff al 14-ago», «Orden
   de trabajo 15-ago» y los 12 snapshots del zip.
7b. **Procedencia dirty-aware.** Las 4 paridades re-corridas con árbol limpio:
   `medicion_comprometida: false` en las cuatro, y se versionaron **las dos**
   ventanas de warmup de aVolCellPOI2 (w=1 y w=12) para que la resta la pueda
   hacer un tercero. El driver registra **qué** estaba sucio, no un booleano.
8. **Plan que conecta todo:** `docs/PLAN_RUTA_A_UNA_CUENTA_2026-08-18.md` —
   debilidad → capítulo → estado → qué la mueve, el grafo de qué bloquea a qué,
   y la grilla de C1 congelada antes de correr.
9. **Board:** `PENDIENTE.md`. **Canal:** `docs/audits/CANAL_AUDITOR.md`.

## Qué no tocar

Holdout · P&L · F4 sin STOP · `features.py` · `fix/g2-a1-*` · `COVERAGE_NEUTRAL`.
Firewall: outcomes `false`, holdout sellado 2026-07-01 → 2026-12-31; la sesión del
01-07 abre 17:00 CT del 30-06 (`1782856800000000000` ns).

## Dónde está el resto

| Necesitás | Ir a |
|---|---|
| Orden Claude (esta tanda) | `docs/audits/ENTRADA_019_ORDEN_CLAUDE_CENSO_HZ2A_2026-08-18.md` |
| Contrato de trazabilidad | `docs/TRACEABILITY.md` |
| Acta D-1…D-8 | `docs/DECISIONES_2026-08-15.md` |

**Aporte al referente:** una sesión nueva lee L0 y corre C1. El censo es el camino.
