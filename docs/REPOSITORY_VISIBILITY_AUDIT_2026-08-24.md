# Auditoría de visibilidad del repositorio — 2026-08-24

> **Audited base:** `foundation/f0b-compatibility-probe@9b23c307cb112cdd6392d98673e8ead2e8bc4698`  
> **Objetivo:** que ningún auditor confunda «no está en el checkout remoto» con «no existe».

## 1. Dictamen

- Las **26 ramas remotas** existen y sus tips son accesibles en GitHub.
- Las **26** informan `protected=false`.
- Hay **6 PRs abiertos**, todos draft, inventariados con sus checks.
- El remoto contiene el incidente, su manifest, los specs, el runner y los documentos de estado.
- **No se puede certificar ausencia absoluta de información local desde GitHub.** Sí se puede declarar todo lo conocido fuera del remoto y exigir manifest/hash para usarlo.

Por eso el dictamen no es «no hay información oculta». Es más preciso:

```text
REMOTE_REFS_ENUMERATED             = YES
KNOWN_LOCAL_ONLY_ARTIFACTS_DECLARED = YES
ABSENCE_OF_UNKNOWN_LOCAL_FILES      = NOT_PROVABLE_FROM_GITHUB
```

## 2. Información deliberadamente fuera de Git

La `.gitignore` excluye, entre otros:

- `/data/*`, salvo `/data/nt8_oracles/*`;
- `*.Last.txt` y archivos comprimidos;
- `runs/*`, con excepciones estrechas para censo/intake;
- `cache/`, `artifacts/`, `logs/`;
- oráculos reales `oracles/**/*.csv|txt|bak`;
- entornos, secretos y configuración local.

Consecuencia: un clon limpio **no contiene los datos ni todos los outputs** necesarios para reproducir cada medición. El auditor debe pedir el artefacto por ID/hash, no inferirlo por una ruta en un documento.

## 3. Cuarentena del incidente 2026-08-24

Ruta local reportada:

```text
C:\Users\nicoc\OneDrive\Documentos\DataNT8\quarantine\INC_OUTCOMES_UNTRACKED_20260824\
```

Autoridad remota:

- `docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md`;
- `docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.manifest.json`;
- `specs/bt2_absorption_gate1_exposure_amendment_2026-08-24.json`.

Contenido: 12 archivos del mismo drop, 11 con outcomes y 1 target-free. Se copiaron y verificaron bit a bit antes de retirar los originales del worktree. **Los bytes no se versionaron a propósito.** Para inspeccionarlos, el auditor necesita acceso de Nico a esa cuarentena y debe preservar timestamps/hashes; no debe copiar outcomes al repo.

## 4. Otros artefactos local-only conocidos

| Artefacto | Ubicación / identidad | Estado |
|---|---|---|
| piloto BTCUSDT BigTrap2 | `/data/BTCUSDT_BT2_PILOT_2024-03-30_bundle.zip` · sha256 `f5a38af8c60307a643ce89140901c2b4aad6ea5ac3eb29c279b04f32efaf4dd1` | local-only; no es evidencia de edge |
| cintas GC `.Last.txt` | ruta local bajo datos NT8; hashes en manifests de paridad | gitignored; necesarias para reruns |
| parquets L1/L2 | árboles locales `data/nt8*` y fuentes adjuntas | gitignored; verificar identidad por manifest |
| outputs runtime | `runs/*` salvo excepciones trackeadas | regenerables o locales; no citar un path sin hash |
| oráculos CSV/TXT | `oracles/` | ignorados por defecto; algunos TSV/GZ seleccionados sí están trackeados |
| Notion canal 001–005 | contenido completo sólo en Notion | el repo conserva resumen/correcciones, no el texto íntegro |

El manifiesto legible por máquina está en `docs/EXTERNAL_ARTIFACTS_MANIFEST_2026-08-24.json`.

## 5. Múltiples clones y worktrees

La historia del repo menciona, como mínimo:

- `E:\EdgeLab`;
- `E:\ProyectosQuant\EdgeLab-sync-desktop`;
- `D:\EdgeLab`;
- una operación reciente bajo `C:\Users\nicoc\OneDrive\Documentos\DataNT8`.

Además, el remoto del clon reciente se llamó `github`, no `origin`.

Antes de correr o escribir:

```powershell
git rev-parse --show-toplevel
git remote -v
git worktree list
git status --short --untracked-files=all
```

Una ruta absoluta en un script puede apuntar a otro clon con archivos de igual nombre y distinto contenido. No corregir rutas «a ojo»: resolver por root + hash.

## 6. Inventario de artefactos visibles en la raíz

No se movió ni borró nada en esta auditoría. Se clasificó lo suficiente para que no parezca invisible:

| Ruta | Qué se observó | Lectura |
|---|---|---|
| `=` | objeto raíz aparentemente vacío/accidental; el loader no pudo representarlo | candidato a limpieza futura, **no borrar aún** |
| `a44a..._ExportBlock.../` | contenedor ExportBlock con `Part-1` | export de Notion/adjunto; histórico |
| `f2fc..._ExportBlock.../` | segundo contenedor ExportBlock con `Part-1` | export de Notion/adjunto; histórico |
| `AMejorasIndicadoresVectorbt/` | seis TXT: BigTrap, Gaps2, Hftzones2, aVolCellPOI, VolTicksPOC y guía | material fuente/referencia; no canónico |
| `indicadores_nt8_revisados_2026-07-25 (1)/` | snapshot `nt8_reviewed/` | material histórico de intake |
| `kaggle_bundle_v2/` | `bundle_index.json` trackeado | manifest; no contiene el árbol raw |
| `kaggle_dataset/` | README, metadata y manifest | metadata histórica; Kaggle salió del programa |
| `archive/` | cuarentena, backups NT8, parquets v1 y tickbars invalidadas | archivo; parte del contenido puede estar ignorada |
| `data/` | sólo `nt8_oracles/` visible en Git | excepción explícita de `.gitignore` |
| `runs/` | `censo/`, `intake_l2/`, `pred004/` visibles parcialmente | no asumir que todo runtime está versionado |
| `oracles/` | README, dos TSV capture-event y `split/` | selección trackeada; CSV/TXT reales siguen ignorados |
| `patches/` | patch TICKBAR-001 | parche histórico explícito |

Ninguno se declara eliminable sólo por el nombre. Una limpieza posterior requiere: origen, vigencia, referencias entrantes, hash, reemplazo canónico y decisión de conservación.

## 7. Punteros obsoletos que el auditor no debe obedecer

Al audited base todavía existían estos desfasajes:

- `AGENTS.md` abría con fecha 2026-08-10, hash antiguo de NORTH STAR y estado «holdout intacto»;
- `docs/ESTADO_2026-08-10_EMPEZAR_ACA.md` es histórico, aunque el nombre sugiere vigencia;
- el encabezado de `PENDIENTE.md` apuntaba a un handoff del 14-ago;
- `docs/INVENTARIO_DE_RAMAS_2026-08-15.md` tenía 14 ramas relevantes, no las 26 actuales;
- `docs/research/LEER.md` aún declaraba H-Z2A como línea principal.

Los entrypoints se corrigen en el commit de handoff. Los documentos antiguos se conservan para no romper citas; no mandan sobre `AUDITOR_START_HERE.md`, `docs/CURRENT.md` ni este corte.

## 8. Contenido Notion que no sobrevivió íntegro

`docs/TRACEABILITY.md` y `docs/audits/CANAL_AUDITOR.md` declaran que las entradas 001–005 del canal vivieron sólo en Notion. El repo conserva:

- el índice con resumen;
- commits que registraron sus efectos;
- correcciones 006+;
- decisiones consolidadas en `PENDIENTE.md`.

No fabricar una transcripción retroactiva. Si el texto completo resulta necesario, Nico debe exportarlo y sellarlo; mientras tanto, cualquier afirmación depende de los artefactos/correcciones versionados, no del recuerdo del chat.

## 9. Protocolo contra nueva información oculta

1. `git status --short --untracked-files=all`, no sólo `git status --short`.
2. Enumerar recursivamente directorios `??`; el incidente perdió un archivo porque Git colapsó `scratch/`.
3. Para todo local-only: ruta, bytes, timestamps, sha256, productor, datos leídos, rango temporal y exposición a outcomes.
4. Copiar a cuarentena, verificar origen↔copia y recién después retirar del worktree.
5. No `git clean` durante forense.
6. No versionar secretos, credenciales ni outcomes sólo para «hacerlos visibles».
7. Hacer visible el **manifest**, no necesariamente el payload.
8. Una sola rama y un solo escritor por worktree.

## Aporte al referente

La visibilidad deja de equivaler a «está trackeado»: cada ausencia conocida tiene ahora categoría, autoridad, hash o limitación. Así un auditor puede distinguir material inexistente, local-only, ignorado, histórico y comprometido sin abrir outcomes ni depender de la máquina anterior.