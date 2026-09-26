# Entrada 022 — Aud → canal · A1 y A2 entregados: el manifiesto numérico queda para el STOP de Nico

- **Fecha:** 2026-08-18
- **Dirección:** Auditor → canal (el destinatario del manifiesto es Nico)
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · sin ejecución

**Commits leídos (40 caracteres):** `eb096b5cc9f7241278f106acd2dcdf6cad0fe74a` (entrada 021 + índice) · `96e64e9e2411fb4055eb078a18d23cea2aa27b30` (HEAD al redactar)

**Evidencia (path + blob, regla 3):**

| artefacto | path | blob |
|---|---|---|
| manifiesto numérico (A1) | `docs/research/H_Z2A_MANIFIESTO_NUMERICO_2026-08-18.md` | (este commit) |
| spec de `validity.py` (A2) | `docs/research/VALIDITY_PY_SPEC_2026-08-18.md` | (este commit) |
| insumo verificado | `docs/research/censo_hz2a_superficie_2026-08-18.json` | `8bd29ed95b1756d6a11dee7c5d6a1b69c5c09144` |

---

## Lo que queda entregado

**A1 — el manifiesto numérico H-Z2A** (`DRAFT_FOR_STOP`). Escrito con la tabla del
censo delante, verificada en la 021. Lo que fija, en números:

- **Estimand**: `Δ_historia` como landmark predictivo en `t2` — no causal. La
  subpregunta que entra a F4 es H-A2ACCESS.
- **Configuración central**: `D_far=10 · δ_nm=5 · R_min=5 · trade`, con la razón
  escrita por número (`R=5` lo fija el censo — con 10 y 20 la fila es cero; δ=5 es
  4,38 spreads; δ=8 tiene marginal 0 en D=10; D=80 vive por eventos, no por
  cobertura — 21 sesiones — y queda fuera del primario).
- **Sensibilidad declarada**: `D_far ∈ {10,20}` · `δ ∈ {3,8}` · eje quote — ya
  censuada, no se re-corre después de outcomes.
- **Potencia honesta**: la celda central (1.505 eventos / **139 sesiones**) limpia
  el piso de Δ=10 pp con holgura y queda **justo por debajo** del piso de 5 pp a
  nivel evento (1.505 < 1.566); con la sesión como unidad, el MDE₈₀ es ≈ 16,8 pp.
  Está escrito así, sin esconderlo.
- **Presupuesto**: **N_eff = 71** declarado (60 del censo ya gastado y público +
  11 de la fase de test) — el dato «8 testeables, no 60» incorporado.
- **Limitaciones del censo v1 escritas**: «disponible ≈ misma sesión» (C-B la
  mide; si importa, censo v2 con otra etiqueta **antes** de F4) · A1 sin filtro de
  actividad (cota superior) · P-28 permanente.
- **Grafo causal + mecanismo + lo que lo refutaría** (addendum 007 §3) y la matriz
  de refutación variante/core (objeción de Nico integrada).
- **STOP (§11)**: cuatro puntos numéricos que Nico aprueba o rechaza.

**A2 — el spec de `validity.py`** (`SPEC_NOT_BUILT`): la cadena `constructo →
observable → **unidad+reloj** → estimador → chequeo` hecha módulo; absorbe P-39
con los tres casos (`gex_dollar`, `zone_age`, `distance_to_nearest_zone`) pasando
o fallando **explícitamente**. Construirlo es C3 — espera el STOP.

## Estado

La línea pasa de «censo corrido» a «**manifiesto redactado, esperando STOP**».
F4 no arranca sin el STOP de Nico. Lo que sigue del lado de la máquina, sin
tocar nada de esto: **C-A** (test de ceguera) · **C-B** (ciclo de vida) · **C2**
(P-42) — la asignación de la 021 §5 sigue vigente.

**A5 continuo:** ningún uso de «agotamiento» sin L2 apareció en esta tanda.

## Lo que NO hago

No ejecuto nada. No fijo nada por fuera del manifiesto. No abro P-NN (las dos
limitaciones del censo quedan escritas en el manifiesto, que es donde se
declaran). No mergeo nada. El manifiesto no se toca después del STOP sin otra
versión.
