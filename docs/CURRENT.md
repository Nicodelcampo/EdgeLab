# CURRENT — empezar acá

> Punto de entrada único. Una sesión nueva (Claude, auditor o Nico) lee esto
> antes de cualquier otra página. Si este archivo y Notion divergen, **manda
> el repo**.

**Rama viva:** `foundation/f0b-compatibility-probe`
**Fecha:** 2026-08-19
**Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Qué está vivo hoy

1. **Línea científica:** H-Z2A v4. Manifiesto v1 **SUSPENDIDO**.
2. **Ruta crítica:** P-45 **(c) implementada** en origin (`a0d8dece…`). Schema
   `censo_hz2a_superficie_v2_episodio`. Tres tests de episodio PASS (recomputados).
   **Censo v2 corriendo** en la máquina de Nico — artefacto **aún no verificado**.
   21 y 49 **no son eventos**: son pares no monótonos sobre 19.200 series sintéticas.
   `docs/audits/ENTRADA_030_C_EN_ORIGIN_Y_21_NO_SON_EVENTOS_2026-08-19.md`
3. **Camino a PASS de los 7:** `docs/research/CAMINO_A_PASS_PARIDAD_2026-08-19.md`.
   El único FAIL real que falta es P-42 (`aVolCellPOI2`). Se retoma **después** de v2.
4. **P-46:** denominador 45. Censo v1: `docs/research/censo_hz2a_superficie_2026-08-18.json`.
5. **Crash:** no fue el censo. Matriz de kernels no se re-corre. C2 no lanzado.
6. **Board:** P-41 resuelta. P-42 abierta. P-43 medida. P-44 abierta. P-45 decidida (c).
   P-46 abierta (denominador 45). `PENDIENTE.md`.
7. **Ledger v1:** `docs/research/LEDGER_COSTOS_CAP3_2026-08-18.md`.
8. **Canal:** `docs/audits/CANAL_AUDITOR.md` (001→030).
   Intake Nico: `docs/research/INTAKE_NICO_HZ2A_EXPLORATORIO_2026-08-18.md`.

## Qué no tocar

Holdout · P&L · F4 sin STOP · MAE/MFE en el censo · `features.py` · `fix/g2-a1-*` ·
`COVERAGE_NEUTRAL` · la matriz de kernels · HFTZones2 en la misma corrida que v2.
Firewall: outcomes `false`, holdout 2026-07-01 → 2026-12-31
(`1782856800000000000` ns).

**Aporte al referente:** (c) quedó fijado por test antes de medir. Los 21/49 no son N.
