# Handoff — sincronización de la computadora de mayor capacidad

**Fecha:** 2026-08-04  
**Rama que contiene este documento:** `work/repository-research-iterations`  
**Base:** `d53fdc5ff6b0501409708993467cc5b7e5c0fc0b`

## Objetivo

Preparar una copia limpia de EdgeLab en la computadora de mayor CPU/RAM sin sobrescribir la copia histórica ni interferir con la corrida que Claude mantiene en la laptop.

## Estado remoto al redactar este handoff

- `fix/capture-probe-v2-contract`: `d53fdc5ff6b0501409708993467cc5b7e5c0fc0b`.
- Último consolidado visible de Claude: `4db4bb33027add09fba09c35f2db4dd0d501d452`.
- No había todavía un reporte remoto posterior con integración/compilación de `BigTrap2.cs`, `time:1`, K=25 y K=10.
- Cualquier ejecución posterior en la laptop debe considerarse local hasta que exista commit, push, reporte y hashes.

## Regla principal

**No actualizar encima de la carpeta histórica. No usar `git reset --hard`. No copiar outputs mientras otro proceso los está escribiendo.**

## Clon limpio

```bash
cd C:/ProyectosQuant
git clone https://github.com/Nicodelcampo/EdgeLab.git EdgeLab-sync-desktop
cd EdgeLab-sync-desktop
git fetch origin --prune
git switch --track origin/fix/capture-probe-v2-contract
git rev-parse HEAD
```

Hasta que Claude publique un commit posterior, el SHA esperado es:

```text
d53fdc5ff6b0501409708993467cc5b7e5c0fc0b
```

Si la rama local ya existe:

```bash
git switch fix/capture-probe-v2-contract
git pull --ff-only origin fix/capture-probe-v2-contract
```

## Worktrees separados

No fusionar todavía los frentes.

```bash
cd C:/ProyectosQuant/EdgeLab-sync-desktop
git fetch origin --prune
git worktree add -b work/research-architecture-hardening ../EdgeLab-research origin/work/research-architecture-hardening
git worktree add -b work/repository-research-iterations ../EdgeLab-repo-research origin/work/repository-research-iterations
git worktree list
```

Uso previsto:

- `EdgeLab-sync-desktop`: TICKBAR/NT8 y trabajo operativo de Claude.
- `EdgeLab-research`: gates, censo y arquitectura científica.
- `EdgeLab-repo-research`: investigación en cuatro iteraciones sobre repositorios externos.
- carpeta vieja: respaldo sin modificar.

## Entorno

No copiar `.venv` entre computadoras. Reconstruirla desde el lock/procedimiento canónico del repo:

```bash
cd C:/ProyectosQuant/EdgeLab-sync-desktop
py -m venv .venv
```

Antes de ejecutar análisis, registrar Python, plataforma, lock, commit y resultado del preflight. No improvisar dependencias ni presentar una suite ejecutada bajo un entorno divergente como canónica.

## Lo que Git no sincroniza automáticamente

Verificar explícitamente:

- `data/` y Parquet;
- exports `.Last.txt`;
- `runs/`, outputs y manifests;
- oráculos locales;
- logs y `scratchpad`;
- historial/caché de NT8;
- indicadores instalados bajo Documentos/OneDrive;
- archivos ignorados;
- entorno virtual.

No copiar datos u outputs de la laptop mientras la corrida siga activa. Al finalizar, el reporte de Claude debe enumerar artefactos no versionados y aportar SHA-256.

## Protocolo al terminar Claude

Claude debe publicar, en este orden:

1. commit y push;
2. reporte local nuevo;
3. suite específica y completa;
4. estado de compilación NT8;
5. resultado bit-idéntico de `time:1`;
6. K=25;
7. K=10;
8. tasas de mismatch y abstención;
9. hashes de inputs/outputs;
10. inventario de archivos locales que deban transferirse.

En la computadora nueva:

```bash
cd C:/ProyectosQuant/EdgeLab-sync-desktop
git status --short --branch
git fetch origin --prune
git pull --ff-only
git log -5 --oneline --decorate
```

Si `pull --ff-only` falla, no forzar: auditar rama, commits locales y divergencia.

## Límites

- No mezclar ramas mientras Claude esté trabajando sobre la base `d53fdc5...`.
- No lanzar K=25/K=10 con datos viejos o no certificados.
- No tomar la copia anterior de `BigTrap2.cs` como autoritativa.
- No declarar completados los siete pasos sin reporte y hashes remotos.
