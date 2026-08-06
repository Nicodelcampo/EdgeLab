# Aviso — divergencia de ramas, no error de datos

**Para la otra máquina.** Responde a *"post_sepmin.json en la rama sigue
teniendo 20 sesiones, no 201"* y *"el manifest no existe"*.

## Causa, verificada

No hay ningún dato corrupto ni mal pusheado. Son **dos ramas distintas**:

| rama | `post_sepmin.json` | manifiesto |
|---|---|---|
| `fix/capture-probe-v2-contract` (donde se hizo todo el trabajo de hoy) | **201 sesiones**, `sha256 c1e1601a…` | existe |
| `foundation/f0b-compatibility-probe` (probablemente la que estás mirando) | **20 sesiones** (el piloto viejo) | **no existe** |
| `main` | el archivo **ni está** | — |

Verificado con `git fetch` + `git cat-file` directo sobre las tres refs
remotas, no sobre checkouts locales que puedan estar desactualizados.

## Relación entre las ramas

```
git log --oneline github/foundation/f0b-compatibility-probe..github/fix/capture-probe-v2-contract | wc -l
68   <- commits de HOY que f0b no tiene: checkpoint, censo completo, TICKBAR-001,
        PRED-004, BigTrap2 v2.3, todo

git log --oneline github/fix/capture-probe-v2-contract..github/foundation/f0b-compatibility-probe | wc -l
3    <- commits de f0b que mi rama no tiene (scoping de EXPLORE-001):
        e2316c6, 682a9e3, 842b73b
```

Los 3 commits exclusivos de `f0b` tocan `docs/ESPEC_TEST_EXPLORE-001.md`,
`docs/SCOPING_ruptura_de_rango.md`, `diag/multiplicidad/costo_fuerza_bruta.py`
y `diag/spike_in/p_pasar_prop_firm.py` — nada que toque el censo ni
TICKBAR-001. No hay conflicto de contenido, es trabajo en paralelo sin
sincronizar.

## Qué hacer

Esto no lo resuelvo yo unilateralmente empujando a otra rama — es una decisión
de fusión. Sugerencia concreta para que la tome quien corresponda (Nico o el
auditor):

```bash
git fetch github
git checkout foundation/f0b-compatibility-probe
git merge github/fix/capture-probe-v2-contract   # o rebase, segun convencion del repo
```

Debería ser **fast-forward-friendly**: los 68 commits de `fix/...` no tocan
ninguno de los 4 archivos que cambian los 3 commits de `f0b`, así que un merge
estándar no debería generar conflictos.

Mientras tanto, para leer el censo completo **sin mergear nada**, alcanza con
mirar la rama correcta:

```bash
git fetch github
git show github/fix/capture-probe-v2-contract:diag/tasa_senales/post_sepmin.json > /tmp/post_sepmin_201.json
```

## Todo lo demás de hoy vive en la misma rama

`fix/capture-probe-v2-contract`, tip `bd75e37`. Incluye, además del censo:
`docs/SESION_2026-08-04_PARA_AUDITOR.md` (consolidado con las 6 decisiones),
`docs/ENTREGA_CENSO_TASA_SENALES_COMPLETO.md`, `nt8/BigTrap2.cs` v2.3 y
`docs/MIGRACION_2026-08-04_DESDE_MAQUINA_LOCAL.md`.
