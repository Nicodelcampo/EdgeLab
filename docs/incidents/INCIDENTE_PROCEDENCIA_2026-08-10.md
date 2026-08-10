# Incidente de procedencia Git/worktree — 2026-08-10

## Estado

**ABIERTO / P0 / bloquea interpretación.**

## Hechos disponibles

1. Había al menos dos procesos sobre el mismo directorio: research y `task_e4c25dc3` para `.gitignore`.
2. La sesión de research usó `git add` explícito y dejó `.gitignore` fuera de staging.
3. Se reportaron commits separados para fix/cuarentena, seguimiento F1.1, `tick:25`, registro, catálogo ES/NQ y barrido de parámetros.
4. Archivos atribuidos a `5a143da` reaparecieron modificados.
5. Un artefacto corregido publicó `code_commit=6a2c08a`, anterior al turno.
6. El proceso completo de ES terminó, pero no se presentó su resumen.
7. La documentación y el fix canónico de `.gitignore` fueron publicados vía PR #1 en `0205cad`; el código y los artefactos locales de research siguen ausentes del remoto.

## Lo que todavía no se sabe

- si el artefacto corrió sobre un árbol dirty basado en `6a2c08a` y luego ese código se commiteó;
- si `git_head()` usó otra raíz o worktree;
- si otro proceso reescribió archivos después del commit;
- si se inspeccionó un artefacto de una corrida anterior;
- qué bytes exactos produjo cada resultado;
- qué resultado arrojó ES.

## Protocolo forense — no modificar antes de capturar

```powershell
git rev-parse --show-toplevel
git rev-parse --git-dir
git rev-parse HEAD
git status --porcelain=v2 --branch
git worktree list --porcelain
git log --all --graph --decorate --oneline --date-order -n 100
git reflog --date=iso -n 100
git diff --name-status HEAD
git diff --cached --name-status
```

Además:

1. registrar cwd, PID, comando y tiempos de cada proceso;
2. guardar hashes y mtimes de artefactos y fuentes afectadas;
3. cruzar creación del artefacto con commits/reflog;
4. inspeccionar `git_head()` y todos sus callers;
5. identificar qué proceso tocó cada archivo después de `5a143da`;
6. no hacer `reset`, `checkout`, `clean`, amend adicional ni commit hasta preservar esta evidencia.

## Contrato mínimo de procedencia nuevo

Cada corrida debe publicar:

- `repo_root` y `git_dir`;
- worktree/cwd;
- `head_start` y `head_end`;
- `status_porcelain_v2_start/end`;
- `dirty_start/end`;
- SHA-256 de `git diff --binary HEAD`;
- manifiesto nombre/tamaño/hash de untracked consumido;
- hashes de fuentes realmente importadas;
- identidad de datos y entorno;
- run ID, PID, comando, timestamps y código de salida.

Implementación recomendada: ejecutar Git siempre como `git -C <repo_root> ...`; nunca confiar en el cwd heredado.

## Árbol de decisión

1. **Artefacto anterior al commit y árbol dirty:** el SHA de HEAD es incompleto; reemitir desde commit limpio.
2. **Raíz/worktree incorrecta:** corregir `git_head()`, agregar test y reemitir.
3. **Reescritura concurrente:** aislar una worktree por sesión, comparar diffs y reemitir.
4. **Artefacto viejo:** retirarlo de la ruta vigente y conservarlo en cuarentena con acta.
5. **No reconstruible:** retractar el resultado afectado.

## Reemisión

Crear una worktree limpia en el commit adjudicado, confirmar status vacío, detener otros writers, correr smoke test y luego el universo completo. Verificar que `head_start=head_end`, `dirty_start=dirty_end=false` y hashes de fuentes coincidan.

## Gate de salida

El incidente se cierra cuando cada artefacto vigente se vincula unívocamente a código, datos, entorno y proceso, y los resultados reemitidos coinciden o quedan retractados. Hasta entonces, F1.1 corregido, `tick:25`, barrido de parámetros y ES son provisionales en cuarentena.
