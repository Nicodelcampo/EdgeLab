# AUDITOR START HERE — EdgeLab

> **Punto de entrada operativo actualizado al 2026-09-17.**  
> Rama de continuidad / integración: `fix/hft-parity-corridor-viewer-complete-v1-20260916` (sincronizada en `foundation/f0b-compatibility-probe`).  
> Resolver el HEAD remoto al comenzar; no copiar un hash desde un handoff.

## Lectura obligatoria

1. [`PROJECT_INDEX.md`](PROJECT_INDEX.md)
2. [`docs/CURRENT.md`](docs/CURRENT.md)
3. **[`docs/research/HFT_CAUSAL_CERTIFICATION_HARDENING_2026-09-17.md`](docs/research/HFT_CAUSAL_CERTIFICATION_HARDENING_2026-09-17.md)** — **[NUEVO 2026-09-17]** Certificación Completa de Paridad V2 (38 campos, 5.438 zonas, 0ns drift, monotonía temporal y blindaje causal downstream).
4. **[`docs/research/INFORME_FALSACION_ABSORCION_HFT_EMA_2026-09-17.md`](docs/research/INFORME_FALSACION_ABSORCION_HFT_EMA_2026-09-17.md)** — Falsación de Absorción HFT con Reversión a la Media (EMA) y Vuelo Libre en Corredores de Vacío (HP-008).
5. **[`docs/research/HP-007_DOSSIER_TECNICO_Y_AUDITORIA_CORREDORES_VACIO.md`](docs/research/HP-007_DOSSIER_TECNICO_Y_AUDITORIA_CORREDORES_VACIO.md)** — Dossier de Auditoría Completa de Corredores de Vacío y Campo de Resistencia Microestructural.
6. [`docs/HIPOTESIS_PENDIENTES.md`](docs/HIPOTESIS_PENDIENTES.md) — Registro canónico de hipótesis (ver HP-007 y HP-008).
7. [`docs/OPEN_IDEAS_INDEX_2026-09-02.md`](docs/OPEN_IDEAS_INDEX_2026-09-02.md)
8. [`docs/BRANCH_REGISTRY_2026-09-02.md`](docs/BRANCH_REGISTRY_2026-09-02.md)
9. [`PENDIENTE.md`](PENDIENTE.md)
10. [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md)

Para la historia completa: `docs/PROJECT_CHRONOLOGY_2026-09-02.md`. Para material local-only: `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`.

No empezar por el árbol completo de `docs/research/`: mezcla evidencia vigente, material sustituido y familias distintas.

## Estado en 90 segundos

```text
HFT_V2_PARITY_STATUS                PASS_CERTIFIED_FULL_FIELD_PARITY (38 campos, 5.438 zonas, 0 discrepancias)
HFT_CORRIDOR_INTEGRATION            PASS_CAUSAL (available_ts_ns estricto, fail-closed)
VIEWER_HP007_INVARIANCE             PASS_AUTOMATED (Playwright Chromium: zoom, pan, resize y autoscale invariantes)
HP-008_HFT_EMA_REVERSION            FALSADO INCONDICIONAL / SOBREVIVE EN ROTACIONAL Y VACIO
HP-008_LO_MACKINLAY_VR              CONFIRMADO (VR=0.9645 a H=20-50 barras 25t, reversión genuina)
HP-008_VACUUM_FREE_FLIGHT           CONFIRMADO (+7.30 pt / +29.2 ticks, 63.6% WinRate, MFE/MAE 1.45x)
HP-008_CME_FRICTION_BARRIER         CONFIRMADO (Micro-scalping destruido por fricción; requiere target amplio)
HP-007_VOID_CORRIDORS               CONFIRMADO (Velocidad 3.03x en tiempo real, p < 1e-9, Z_mc = 5.65)
HP-007_VECTORIAL_BACKSTOP           CONFIRMADO (+0.156 R en cortos, +0.076 R en largos vs -0.409 R contra pared)
HP-007_WALL_TO_WALL_4_7T            CONFIRMADO (42.54% hit, +0.160 R con R:R 1.73:1)
HP-007_WALL_COLLISION               CONFIRMADO (52.27% rebote limpio >= 3t, rebote medio 5.15t)
HOLDOUT_INTEGRITY                   INTACTO Y SELLADO (2026-07-01 -> 2026-12-31)
--------------------------------------------------------------------------------
PRIMARY_BRANCH                      foundation/f0b-compatibility-probe
ACTIVE_RESEARCH_BRANCH              fix/hft-parity-corridor-viewer-complete-v1-20260916
NQ_SCAN_V2_ROWS                     119153201
NQ_MANIFEST_STATUS                  ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED
CALENDAR_STATUS                     RESUELTO 4f365bf -- 322 sesiones con evidencia hasheada
CAMPAIGN_OUTCOMES_OPENED            false (holdout preservado)
PREEXISTING_OUTCOME_EXPOSURE        YES
```


Los cuatro rolls sobreviven al diagnóstico con y sin nueve feriados y con ratios idénticos a 6 decimales. Eso reduce el riesgo de que cambien, pero no certifica el calendario, la completitud ni el manifiesto.

## Primeros comandos

```powershell
git remote -v
git fetch --all --prune
git switch foundation/f0b-compatibility-probe
git pull --ff-only <remote-real> foundation/f0b-compatibility-probe
git rev-parse --show-toplevel
git rev-parse HEAD
git worktree list
git status --short --untracked-files=all
.venv\Scripts\python tools\estado.py
```

En clones recientes el remoto se llamó `github`, no `origin`. Detectarlo.

## Orden de reanudación

1. Capturar y hashear horarios oficiales CME Equity Index.
2. Construir cobertura de fuente por contrato/trade date.
3. Aprobar evidencia de completitud por vía explícita; no por minutos activos.
4. Reconstruir y verificar el manifiesto NQ.
5. Reconstruir intervalos contractuales con reset en el roll.
6. Alinear el borde de ~3 ticks y resolver paridad/lifecycle aVolClusterPOI.
7. Sólo entonces evaluar autorización de EF0.

## STOP

No abrir outcomes, P&L, holdout, EF0 ni tolerancias. No certificar los cuatro rolls por el análisis de sensibilidad. No mergear la rama de auditoría divergente. No recortar post hoc el trace existente.

## Reproducción y Falsación Autónoma de HP-008

Para reproducir y falsar de forma determinista los resultados de absorción HFT con reversión a la media:

```powershell
# 1. Batería de 10 pruebas de falsación (placebo, simetría, fricción, estabilidad interdiaria)
python tools/falsification_battery.py

# 2. Razón de Varianzas de Lo-MacKinlay, Corredores de Vacío y Z-Score VWAP
python tools/deep_falsification_probe.py

# 3. Sonda analítica de trayectorias MFE/MAE de absorción
python tools/research_hft_absorption_probe.py
```

## Aporte al referente

El siguiente auditor entra por el estado del 17-sep, dispone del informe de falsación completo (HP-008), herramientas ejecutables para falsar de forma autónoma la absorción HFT con EMA, y mantiene intacta la partición de holdout.