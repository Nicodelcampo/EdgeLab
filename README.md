# EdgeLab

> **Estado canónico:** [`docs/ESTADO_2026-08-10_EMPEZAR_ACA.md`](docs/ESTADO_2026-08-10_EMPEZAR_ACA.md)
>
> **Incidente P0 abierto:** [`docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md`](docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md)

Infraestructura de investigación cuantitativa orientada a encontrar edges netos, robustos y ejecutables sin confundir paridad, información descriptiva o un backtest positivo con un edge.

## Estado actual

- **Documentación remota:** sincronizada en la rama canónica mediante los PR #1, #2, #3 y #4.
- **Código y artefactos posteriores:** siguen locales y todavía no están publicados ni adjudicados.
- **H1:** muerta; corrió sobre 6E, no NQ/ES.
- **BigTrap2 como soporte/resistencia:** fuertemente refutado.
- **Atracción/revisita:** hipótesis provisional en cuarentena.
- **Familia LUX-IMB (OG/VI):** registrada como línea independiente de BigTrap2. Protocolo corregido: las zonas no desaparecen por mitigación y no existe input `Mitigation Method`; nada ejecutado.
- **Familia YM-PRERANGE:** registrada como tercera línea independiente. Protocolo escrito, nada ejecutado, bloqueada por P0 y por la falta de calendario de research para YM.
- **Trabajo local posterior:** se reportaron reruns corregidos, réplica `tick:25`, barrido target-free de 11 celdas y una generalización ES.
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
7. [`docs/research/H-COND-1_LUX-IMB_PROTOCOLO.md`](docs/research/H-COND-1_LUX-IMB_PROTOCOLO.md)
8. [`docs/research/H-SWEEP-1_YM_PRERANGE.md`](docs/research/H-SWEEP-1_YM_PRERANGE.md)
9. [`docs/edge_validation_contract.md`](docs/edge_validation_contract.md)

## Familias registradas

| Familia | Alcance | Estado |
| --- | --- | --- |
| BigTrap2 | Indicador propio, 6E | H1 muerta; soporte/resistencia refutado; atracción en cuarentena |
| LUX-IMB | `Imbalance Detector [LuxAlgo]`, solo OG y VI, ES 1m | Protocolo corregido, parámetros y paridad pendientes |
| YM-PRERANGE | Ventana temporal 08:12–09:12 sobre YM, sin indicador | Protocolo escrito, nada ejecutado |

Las familias no comparten resultados, poblaciones, costos, oráculos ni presupuesto de multiplicidad. YM-PRERANGE no es una familia de zonas: es una ventana temporal fija, y se registra igual porque las mismas reglas de adjudicación aplican.

## P0 actual

1. Congelar interpretación y reconciliar repo/worktree/procesos/artefactos.
2. Reemitir desde una worktree limpia cualquier resultado cuya procedencia no sea unívoca.
3. Resolver drift BigTrap2 `.cs` v2.5.1 ↔ Python v2.2.
4. Publicar y verificar los commits y artefactos locales de research.
5. Reconciliar el cambio local concurrente de `.gitignore` con el fix canónico `/data/`.

## Regla de interpretación

H1 muerta ≠ BigTrap2 muerto. Proceso terminado ≠ resultado válido. SHA de `HEAD` ≠ identidad del código si el árbol estaba dirty. Zona visible en pantalla ≠ evidencia: incluso cuando el indicador conserva las zonas, las capturas permiten hindsight, selección de ejemplos y tolerancias móviles.

Una racha observada ≠ evidencia: antes de comparar cualquier conteo hay que derivar la tasa esperada bajo el nulo apropiado, porque casi ningún baseline relevante es 50%. Y justificar una **medición** no es lo mismo que justificar una **operación**: las dos decisiones se registran por separado.

## Rama

El trabajo canónico continúa en `foundation/f0b-compatibility-probe`; `main` conserva el baseline histórico.
