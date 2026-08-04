# Reporte de importación — escritorio, 2026-08-04

> **DESVIACIÓN AUTORIZADA — rutas a `E:` en vez de `C:`.**
> El pedido de migración especificaba `C:\ProyectosQuant\*` en seis lugares. Nico
> instruyó de forma directa y repetida —"no mandes nada al disco C, todo al E"—
> antes de que se ejecutara nada. Todas las rutas se mapearon a
> `E:\ProyectosQuant\*`. La desviación queda **autorizada y registrada acá**, no
> es una decisión del ejecutor.
>
> **Nada se escribió en `C:`.** `C:\ProyectosQuant` no existe en esta máquina y no
> se creó. Alcance del commit: **exclusivamente este archivo.**

## 1. Resumen ejecutivo

Migración **completa y verificada**. Cero faltantes, cero diferencias de contenido,
cero operaciones destructivas. Los dos únicos fallos de test son los dos
documentados como rojos a propósito. La copia histórica `E:\EdgeLab` **no se tocó**.

| | |
|---|---|
| clon operativo | `E:\ProyectosQuant\EdgeLab-sync-desktop` |
| remoto | `origin` → `https://github.com/Nicodelcampo/EdgeLab.git` |
| rama · SHA | `fix/capture-probe-v2-contract` · **`953e009c993c5d831258a4f622c79a9a83e2f5e8`** |
| parquets | 5/5, **`dup_bloque=0` en los cinco** |
| hashes migración | 57/61 idénticos · 4 difieren **sólo por CRLF** · 0 faltantes |
| suite | **2 failed, 635 passed, 11 skipped, 3 deselected** |
| `BigTrap2.cs` | sha256 **coincide exacto** con el v2.3 publicado |
| NT8 | **no se tocó** |
| PRED-004 / K=25 / K=10 / censo pesado / DSR / outcomes | **no ejecutados** |

## 2. Clon y ramas

El tip **es exactamente** `953e009`, no posterior. `4a1ba55` (el del `.cs` v2.3)
es ancestro. Árbol limpio antes de importar artefactos.

| worktree | rama | SHA |
|---|---|---|
| `E:\ProyectosQuant\EdgeLab-sync-desktop` | `fix/capture-probe-v2-contract` | `953e009` |
| `E:\ProyectosQuant\EdgeLab-research` | `work/research-architecture-hardening` | `a2b3527` |
| `E:\ProyectosQuant\EdgeLab-repo-research` | `work/repository-research-iterations` | **`5abf9b6`** |

`5abf9b68ccc173d74d6315d9273d7b938d748d75` confirmado en repo-research. Ninguna
rama se mergeó en la operativa.

## 3. Inventario importado

Fuente: `E:\MIGRACION_EdgeLab_2026-08-04\MIGRACION_EdgeLab_2026-08-04`
Inventario: `E:\ProyectosQuant\EdgeLab_migration_source_sha256.csv` (61 filas)

| dir | archivos | tamaño |
|---|---|---|
| `data` | 29 | 943,8 MB |
| `oracles` | 8 | 54,6 MB |
| `archive` | 24 | 166,0 MB |
| **total** | **61** | **1.220.916.816 bytes** |

Copia con `robocopy /E /XC /XN /XO` — **sin `/MIR`**, y los flags garantizan que
no se sobrescribió ningún archivo preexistente.

### 3.1 Verificación SHA-256 origen → destino

| | |
|---|---|
| hash idéntico | **57** |
| difieren sólo por CRLF/LF | **4** (ver §3.2) |
| **subtotal verificado** | **57 + 4 = 61** |
| faltantes | **0** |
| truncados | **0** |
| diferencias de contenido | **0** |

**La aritmética cierra:** 61 archivos en el inventario de origen = 57 con hash
byte-idéntico + 4 que difieren **únicamente** en el fin de línea. No hay ningún
archivo sin explicar.

### 3.2 Los cuatro conflictos: son de fin de línea, no de contenido

Cuatro archivos **trackeados en git** existían ya en el destino tras el clon:

| archivo | destino (git) | migración |
|---|---|---|
| `oracles/README.md` | 1.868 B, CR=LF=39 | 1.829 B, **CR=0** |
| `oracles/split/…__Tick25_run1.csv` | 647.023 B, CR=LF=3.613 | 643.410 B, **CR=0** |
| `oracles/split/…__Tick10_run2.csv` | 5.482.169 B, CR=LF=25.351 | 5.456.818 B, **CR=0** |
| `oracles/split/…__Tick10_run3.csv` | 5.482.169 B, CR=LF=25.351 | 5.456.818 B, **CR=0** |

**Verificado por normalización: al convertir CRLF→LF en la copia de destino, los
cuatro hashes SHA-256 pasan a coincidir EXACTAMENTE con los del origen.** Es
decir: **la diferencia desaparece por completo al normalizar el fin de línea, y
no queda ninguna diferencia de contenido.** La causa es `core.autocrlf` de git,
que almacena LF en el objeto y materializa CRLF en el working tree de Windows.

**Acción tomada: se preservó la versión trackeada por Git; no se sobrescribió
ninguno de los cuatro.** Es consistente con la regla 3 del pedido ("el código y
la documentación vienen exclusivamente de GitHub") — los cuatro están bajo
control de versiones (`git ls-files oracles/` los lista). **No se perdió
información:** el contenido es el mismo byte a byte una vez normalizado, y las
copias del origen siguen intactas en la carpeta de migración.

### 3.3 Los cinco parquets canónicos

`E:\ProyectosQuant\EdgeLab-sync-desktop\data\nt8\6E\`

| archivo | MB | ticks | `dup_bloque` |
|---|---:|---:|---|
| `6E_03-26_ticks.parquet` | 81,8 | 5.064.128 | **0** |
| `6E_06-26_ticks.parquet` | 88,7 | 5.554.201 | **0** |
| `6E_09-25_ticks.parquet` | 42,3 | 2.539.857 | **0** |
| `6E_09-26_ticks.parquet` | 43,3 | 2.784.986 | **0** |
| `6E_12-25_ticks.parquet` | 73,4 | 4.512.656 | **0** |

Censo: **256 días aptos**, `config_hash=b92831e4cb3d59d3`, 80 s.

### 3.4 Oráculos — clasificación conservada, sin editar

| archivo | estado |
|---|---|
| `tickbar_frontera3_10t__Tick10.csv` | **VÁLIDO** — la captura que clasificó TICKBAR-001 |
| `BigTrap2_tick25_6E_0926_v22.csv` | **NO ES ORÁCULO** — tres corridas appendeadas |
| `oracles/split/*.csv` (3) | **NO SON ORÁCULOS** — derivados, con el `# meta` de la corrida 1 |

Ninguno editado, regenerado ni borrado.

### 3.5 Archive

`archive/parquets_v1_export_20260721` presente **sólo en `archive`**. Verificado
que **no existe** `data/parquets_v1_export_20260721`. No se mezcló ni enlazó.

## 4. Junctions de data

| junction | destino |
|---|---|
| `E:\ProyectosQuant\EdgeLab-research\data` | `E:\ProyectosQuant\EdgeLab-sync-desktop\data` |
| `E:\ProyectosQuant\EdgeLab-repo-research\data` | `E:\ProyectosQuant\EdgeLab-sync-desktop\data` |

Antes de crear cada uno se verificó que el path no existiera. Los 5 parquets se
ven desde ambos worktrees. **944 MB una sola vez.** `oracles` y `archive` **no**
se enlazaron, según el handoff.

## 5. Entorno

| | |
|---|---|
| Python | **3.12.7** 64-bit (`MSC v.1941 AMD64`) |
| plataforma | `Windows-10-10.0.19045-SP0` |
| intérprete | `E:\ProyectosQuant\EdgeLab-sync-desktop\.venv\Scripts\python.exe` |
| lock sha256 | `CABEA651C495A01BF6D94C2461C16C3A7ABD81B8D7FEE268138AB26E36F0E85F` |
| instalación | `--require-hashes --no-deps`, 31 paquetes |
| commit | `953e009` |

| paquete | versión | contrato |
|---|---|---|
| numpy | 2.4.6 | — |
| pandas | 3.0.3 | — |
| **pyarrow** | **25.0.0** | ≥ 25 ✅ |
| **duckdb** | **1.5.4** | presente ✅ |
| polars | 1.43.0 | — |

`.venv` creada de cero. No se copió ninguna anterior, no se instaló en editable,
no se tocó el Python global.

> Nota: el Python 3.12 global de esta máquina es el que INC-003 marcó como
> contaminado (numpy 1.26.4, pandas 2.2.2, scipy). **No afecta**: `venv` no
> hereda `site-packages` y la instalación fue exclusivamente desde el lock.

## 6. Tests

| fase | comando | resultado |
|---|---|---|
| 7.1 | `pytest tests\foundation\test_environment_contract.py -q` | **3 passed** |
| 7.2 | `python tools\censo_integridad.py` | **`dup_bloque=0` en 5/5** |
| 7.3 | `pytest tests\research -q` | **165 passed, 4 skipped** |
| 7.4 | `pytest tests -m "not vectorbt" -q` | **2 failed, 635 passed, 11 skipped, 3 deselected** |

`tests\research` da **exactamente** lo que predice `LEEME_ANTES_DE_USAR.md`
("165 passed, 4 skipped").

### 6.1 Los dos fallos — clasificados, NO parcheados

| test | causa | clasificación |
|---|---|---|
| `test_el_cs_canonico_es_el_declarado` | el pin del sha256 del `.cs` sigue en `75910484…`; el archivo es `e5dd810a…` | **decisión pendiente** — el pin se mueve cuando el `.cs` esté validado en NT8, no antes |
| `test_la_version_del_kernel_coincide_con_la_del_cs` | `.cs` declara 2.3, kernel Python declara 2.2 | **asimetría real y buscada** — el kernel Python nunca tuvo el defecto |

No se movió el pin ni se cambió ninguna versión.

### 6.2 Los 27+13 de la máquina de origen NO reproducen

El doc de migración §4 documenta **27 fallos + 13 errores** en la máquina de
origen por `pyarrow 22.0.0` y `duckdb` ausente. Acá **no aparecen**: pyarrow es
25.0.0 y duckdb 1.5.4. **Queda confirmado que eran ambientales, no regresiones**
— que es exactamente lo que ese documento pedía verificar.

## 7. `BigTrap2.cs` — sólo verificación

| chequeo | resultado |
|---|---|
| sha256 | `e5dd810a56e4883596d6a01cfffebdf9eda28bccb36cf69941589c7ba684e977` — **coincide exacto** |
| CRLF | **puro**: CR = LF = CRLF = 1.109 |
| líneas | **1.109** — coincide con el doc |
| metadata | `# meta indicator=BigTrap2,version=2.3` |
| procedencia | `git diff 4a1ba55 HEAD -- nt8/BigTrap2.cs` **vacío**: el `.cs` del tip **es** el de `4a1ba55` |
| working tree | limpio |
| PRED-004 en esta máquina | **NO ejecutado** (`runs\pred004` no existe; sólo `runs\censo`, generado por la verificación 7.2) |

> `git hash-object` sobre el archivo en disco da un blob distinto al de
> `4a1ba55:nt8/BigTrap2.cs`. **No es discrepancia**: es la normalización LF de
> git contra el CRLF del working tree, el mismo fenómeno de §3.2. El `git diff`
> vacío y el sha256 exacto son los chequeos que mandan.

## 8. Artefactos locales encontrados

`E:\MIGRACION_…` **no contiene `runs\`**. Sí existe en la copia histórica.

Copiados a **`E:\ProyectosQuant\EdgeLab-local-artifacts-staging`** con `cp -rn`
(no-clobber; el origen no se modificó): **685 archivos, 332.063.252 bytes**, con
`INVENTARIO_sha256.csv` y `PROCEDENCIA.md`.

| ruta | archivos | nota |
|---|---|---|
| `runs/nt8_bridge/` | 513 | incluye **`campaign_store` (152 arch., 26 MB)** |
| `runs/gates/` | 66 | gates de paridad |
| `runs/atlas_pnk/` + `runs/atlas/` | 8 | atlas sellado |
| `runs/censo/` | 4 | manifiestos |
| `runs/kronos/` | 3 | sidecar |

**Clasificación: DESCONOCIDO / CANDIDATO — ninguno es canónico para la rama nueva.**
Se generaron sobre `foundation/f0b-compatibility-probe` @ `6838f9b`, que divergió
de la operativa (119 commits, §1.1 del doc de migración). **No se mezclaron.**

`runs/nt8_bridge/campaign_store` **sí existe acá** — el doc §4 dice que en la
máquina de origen no existía. Es justamente el artefacto que faltaba.

## 9. Copia histórica — no se tocó

| | |
|---|---|
| ruta | `E:\EdgeLab` |
| es repo git | sí, mismo remoto |
| rama · SHA | `foundation/f0b-compatibility-probe` · `6838f9b` |
| estado | **no modificado** — sólo lectura y `cp -rn` desde ella |

`C:\ProyectosQuant` **no existe**: no había copias previas ahí.

Otros directorios en `E:\` con nombre EdgeLab (`EdgeLab_spike_H`,
`EdgeLab_spike_in`, `EdgeLab_spike_in_38`, `EdgeLab_worktrees`, `EdgeLab_export`,
`EdgeLab_entrega`, `EdgeLab_sonda`, `Edgelabexports`) — inventariados, **no
tocados**, pendientes de decisión.

## 10. Faltantes, conflictos y abstenciones

| # | asunto | estado |
|---|---|---|
| 1 | 4 archivos con CRLF vs LF | **resuelto sin pérdida** — contenido idéntico, se conservó git |
| 2 | `runs\` no venía en la migración | **resuelto** — recuperado de la copia histórica al staging |
| 3 | 2 tests en rojo | **clasificados**, no parcheados — decisión pendiente sobre el pin del `.cs` |
| 4 | `docs/HANDOFF_DESKTOP_SYNC_2026-08-04.md` | **NO es un faltante de migración.** Ubicación verificada: vive en la rama `work/repository-research-iterations` (añadido en `cf03f34`), no en la operativa. Ver §10.1. |
| 5 | rutas `C:` del pedido | **mapeadas a `E:`** — desviación **autorizada** por Nico antes de ejecutar |

### 10.1 `HANDOFF_DESKTOP_SYNC_2026-08-04.md` — ubicación, no ausencia

El pedido lo listaba entre los documentos a leer. **No está en la rama operativa
`fix/capture-probe-v2-contract`, y eso es correcto: pertenece a otra rama.**

| ref | ¿lo contiene? |
|---|---|
| `origin/fix/capture-probe-v2-contract` | no |
| **`origin/work/repository-research-iterations`** | **sí** |
| `origin/work/research-architecture-hardening` | no |
| `origin/main` | no |

Añadido en `cf03f34` (*"docs: add desktop sync handoff and repository research
iteration 1"*), y `git branch -r --contains cf03f34` devuelve **únicamente**
`origin/work/repository-research-iterations`.

**Queda accesible sin trabajo adicional:** esa rama está materializada como
worktree en `E:\ProyectosQuant\EdgeLab-repo-research` (§2). **No es un faltante
de migración** y no hay nada que recuperar. Sus SHAs se tratan como información
histórica, según el propio pedido.

### 10.2 Abstenciones

No se movió el pin del `.cs`. No se resolvió la asimetría 2.3/2.2. No se
reconcilió el README divergente (`preserve/f0b-local-divergente-2026-08-04`).
**No se integró el staging** — `campaign_store` y el resto de `runs/` quedan
como **DESCONOCIDO/CANDIDATO** fuera del clon, sin mezclar. No se tocó NT8, no se
instaló ningún indicador, no se inició PRED-004.

## 11. Confirmaciones

- ✅ **NinjaTrader no se tocó.** Ningún archivo copiado a `bin\Custom`, ningún
  indicador instalado, NT8 no se abrió.
- ✅ **No se ejecutaron:** PRED-004, K=25, K=10, DSR, outcomes, búsquedas sobre
  retornos, ni el censo pesado. Lo único corrido fue `censo_integridad.py`, que
  la Fase 7.2 exige explícitamente como verificación de datos.
- ✅ **Sin operaciones destructivas:** ni `git reset --hard`, ni `git clean`, ni
  `robocopy /MIR`, ni `Remove-Item`, ni sobrescritura de archivos existentes.
- ✅ **Nada escrito en `C:`.**

## 12. Plan posterior para NT8 / PRED-004 — no ejecutado

En este orden (PRED-004 §orden_de_ejecucion):

1. **Verificar la versión instalada en NT8 por sha256** contra `nt8/*.cs` antes de
   nada. El doc §7.1 documenta que `BigTrap2` estaba en v2.0 con el repo en v2.2,
   y que capturar con la vieja produce un FAIL sin información.
2. **Instalar `BigTrap2.cs` v2.3** (`e5dd810a…`) en CRLF.
3. **Compilar en NT8** (F5).
4. **`time:1` bit-idéntico** al oráculo previo — gate P5.
5. **Oráculo K=25** — P1, refuta si mismatch > 1 %.
6. **Oráculo K=10** — P2, mismo código sin reajustar nada.
7. Publicar hashes, tasas de mismatch y **abstenciones** (`ANCLAJE_AMBIGUO`).
8. Recién con el `.cs` validado en NT8: **mover el pin del sha256** y resolver la
   asimetría 2.3/2.2.

Trampas a no repetir (§7 del doc): **Tick Replay DESTILDADO**; `TickBarDiag` con
`SkipBars=0`/`MaxBars=40000`; ledger en hora del chart → `--tz-shift-hours 3`;
`MinExportVolume=1` ≠ `MinTrapVolume=30`; `.cs` en CRLF; PowerShell 5.1 sin `&&`.

---

**Aporte al referente:** deja el aparato de medición reproducible en esta máquina
con los datos canónicos verificados byte a byte (`dup_bloque=0` en los cinco
parquets) y el entorno que la máquina de origen no tenía — pyarrow 25 y duckdb —,
lo que convierte 27 fallos+13 errores de allá en 635 tests verdes acá y separa de
forma concluyente lo ambiental de lo real. No acorta por sí solo la distancia a un
edge, pero es la precondición de que cualquier número que se mida a partir de
ahora sea creíble, y desbloquea la única vía que hoy puede confirmar o refutar
PRED-004.
