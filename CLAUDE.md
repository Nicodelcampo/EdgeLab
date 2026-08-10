# EdgeLab — instrucciones permanentes de sesión

> Fuente rectora: `docs/NORTH_STAR.md`. Punto de entrada: `docs/ESTADO_2026-08-10_EMPEZAR_ACA.md`.

## Objetivo

Encontrar edges válidos y aplicables con expectativa económica neta, validación fuera de muestra y ejecución controlable. Paridad, infraestructura, zonas, información y backtests son niveles intermedios, no edges.

## Estado vigente

- H1 está muerta y fue 6E.
- Resistencia BigTrap2 está refutada.
- Atracción/revisita permanece provisional en cuarentena.
- Reruns corregidos y generalización ES fueron reportados localmente, no adjudicados.
- F4 constitucional no fue ejecutada.
- Holdout intacto.

## Regla P0 por incidente de procedencia

Hasta cerrar `docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md`:

- no interpretar artefactos afectados;
- no correr dos sesiones sobre la misma worktree mutable;
- no considerar `code_commit` suficiente si el árbol estaba dirty;
- no mezclar el fix de `.gitignore` del proceso separado con commits de research;
- reemitir desde un commit limpio cualquier salida sin identidad unívoca.

## Primer comando de cada sesión

```powershell
.venv\Scripts\python tools\estado.py
```

Después verificar raíz, HEAD, worktree y dirty state antes de ejecutar research.

## Reglas permanentes

1. Fuente antes que recuerdo.
2. Una worktree por sesión/campaña; un solo escritor por directorio.
3. Procedencia dirty-aware: `repo_root`, `git_dir`, worktree, `head_start/end`, status, diff hash, fuentes cargadas, datos, entorno y run ID.
4. Enumerar creación, aproximación, primer toque, toque n-ésimo, invalidación, expiración, confluencia y estado continuo antes de congelar población.
5. Separar evento de estado.
6. Separar geometría/lifecycle → información → P&L bruto → edge neto/replicado.
7. Target-free publica landscapes completos, semillas y nulos; no selecciona por P&L.
8. STOP antes de retornos/P&L: manifiesto + `M_eff` + riesgos + datos faltantes + aprobación explícita.
9. No transportar costos entre instrumentos o ejecuciones.
10. `ticks_per_row` y `bar_spec` son ejes distintos.
11. Integridad precede a interpretación.
12. Toda muerte tiene alcance preciso.
13. Holdout sellado.
14. Independencia material entre simuladores.
15. Registro MEDIDO/NO MEDIDO en el mismo commit que cada resultado.
16. El barrido local `F4_PARAMETROS_RESTANTES` es target-free y no debe confundirse con la F4 constitucional de información condicional.

## Rituales

- Todo checkpoint termina con `Aporte al referente: ...`.
- Toda campaña cita el hash vigente de `docs/NORTH_STAR.md`.
- Toda hipótesis declara justificación económica y condición de refutación.
- Toda población declara el event-space del que fue extraída.

## Entorno y rama

- Usar `.venv` del repo.
- Rama canónica: `foundation/f0b-compatibility-probe`.
- No tocar holdout, F4 constitucional ni P&L sin autorización.
- `/data/` es dato local; `edgelab/data/` es código.
