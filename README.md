# EdgeLab

> **Estado canónico:** [`docs/ESTADO_2026-08-10_EMPEZAR_ACA.md`](docs/ESTADO_2026-08-10_EMPEZAR_ACA.md)
>
> **Incidente P0 abierto:** [`docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md`](docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md)

Infraestructura de investigación cuantitativa orientada a encontrar edges netos, robustos y ejecutables sin confundir paridad, información descriptiva o un backtest positivo con un edge.

## Estado actual

- **Remoto verificado:** `foundation/f0b-compatibility-probe` continúa en `5f1b65d` (muerte de H1).
- **H1:** muerta; corrió sobre 6E, no NQ/ES.
- **BigTrap2 como soporte/resistencia:** fuertemente refutado.
- **Atracción/revisita:** hipótesis provisional en cuarentena.
- **Trabajo local posterior:** se reportaron reruns corregidos, réplica `tick:25`, barrido target-free de 11 celdas y una generalización ES, pero todavía no están en GitHub.
- **Incidente:** un artefacto declaró `code_commit=6a2c08a` mientras el fix se referencia como `5a143da`, y hubo procesos concurrentes sobre el mismo directorio.
- **F4 constitucional (información condicional):** no ejecutada.
- **Holdout 2026-07-01 → 2026-12-31:** intacto.

## Leer en este orden

1. [`docs/ESTADO_2026-08-10_EMPEZAR_ACA.md`](docs/ESTADO_2026-08-10_EMPEZAR_ACA.md)
2. [`docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md`](docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md)
3. [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md)
4. [`CLAUDE.md`](CLAUDE.md)
5. [`PLAN.md`](PLAN.md)
6. [`docs/research/FUTURAS_INVESTIGACIONES_E_IMPLEMENTACIONES_2026-08-10.md`](docs/research/FUTURAS_INVESTIGACIONES_E_IMPLEMENTACIONES_2026-08-10.md)
7. [`docs/edge_validation_contract.md`](docs/edge_validation_contract.md)

## P0 actual

1. Congelar interpretación y reconciliar repo/worktree/procesos/artefactos.
2. Reemitir desde una worktree limpia cualquier resultado cuya procedencia no sea unívoca.
3. Resolver drift BigTrap2 `.cs` v2.5.1 ↔ Python v2.2.
4. Publicar y verificar los commits locales.
5. Integrar el fix `/data/` sin mezclar la sesión separada de `.gitignore`.

## Regla de interpretación

H1 muerta ≠ BigTrap2 muerto. Proceso terminado ≠ resultado válido. SHA de `HEAD` ≠ identidad del código si el árbol estaba dirty.

## Rama

El trabajo canónico continúa en `foundation/f0b-compatibility-probe`; `main` conserva el baseline histórico.
