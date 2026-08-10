# EMPEZAR ACÁ — estado canónico al 2026-08-10

**Documentación remota:** sincronizada en `foundation/f0b-compatibility-probe` mediante los PR #1 y #2  
**Código y artefactos de research posteriores:** locales, todavía no publicados  
**Holdout:** intacto  
**P0:** incidente de procedencia Git/worktree

## 1. Lo que no cambia

- H1 corrió sobre 6E y murió: 424 eventos, bruto `+0,2995`, fricción `−2,7680`, neto `−2,4685`, IC 99,9535% `[-5,2370; +4,9780]`.
- La función soporte/resistencia de BigTrap2 está fuertemente refutada.
- BigTrap2 no es un edge demostrado.
- F4 constitucional de información condicional no fue ejecutada.
- El holdout `2026-07-01 → 2026-12-31` no fue abierto.

## 2. Evidencia target-free previa

- F0.2: 15.947 zonas, 15.608 tocadas, 48.768 toques, 33.160 posteriores.
- F2: ruptura 95,8–96,9% en 12 celdas.
- F1.1 inicial: revisita 97,9% real vs ~51,4% nulo, luego puesto en cuarentena por dos bugs de geometría.
- F0.3: estado continuo con ~99,3% de cobertura.

## 3. Nuevo checkpoint local reportado

La sesión local informó:

- commit del fix de nulos y cuarentena;
- commit del seguimiento F1.1;
- commit de la réplica `tick:25`;
- actualización de REGISTRO_NO_MEDIDO;
- barrido target-free de 11 celdas restantes de `PARAM_SPEC`;
- invariancia general y cruce `max_touches=1`: 29,9% de ruptura vs 30,3% de F1.3;
- alta local de `InstrumentSpec` para ES/NQ;
- suite limpia salvo dos fallas preexistentes;
- cobertura ES de 201 sesiones, smoke test limpio y proceso completo finalizado.

El archivo `F4_PARAMETROS_RESTANTES` es un barrido target-free; no es la F4 constitucional.

## 4. Incidente de procedencia

- El fix de `.gitignore` pertenecía al proceso separado `task_e4c25dc3` y quedó fuera del staging de research.
- Archivos atribuidos al commit `5a143da` reaparecieron modificados.
- Un artefacto corregido declaró `code_commit=6a2c08a`, anterior al turno.
- Había procesos concurrentes y saturación de I/O sobre el mismo directorio.

Posibilidades abiertas: árbol dirty ejecutado antes del commit, `git_head()` usando otra raíz/worktree, reescritura concurrente o artefacto de corrida anterior.

**Consecuencia:** reruns corregidos, barrido de 11 celdas y salida ES quedan en cuarentena hasta reconciliar bytes de código, datos, entorno, timestamps y run ID.

## 5. Estado de sincronización

- El reemplazo documental fue publicado mediante PR #1.
- La corrección de estado post-merge fue publicada mediante PR #2.
- `.gitignore` canónico ya usa `/data/`, por lo que no oculta `edgelab/data/`.
- Los commits, fuentes y artefactos locales de research del 10 de agosto todavía no están en GitHub.

## 6. Próximo paso obligatorio

Seguir `docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md`, reemitir desde una worktree limpia lo que resulte ambiguo y recién después adjudicar resultados.

No elegir estrategia. No interpretar ES. No ejecutar F4 constitucional.
