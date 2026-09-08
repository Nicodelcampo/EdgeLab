# NT8 no compila nada: CS0579 por artefactos de build metidos como fuente

> 2026-09-08. **No es código del usuario.** Apareció al compilar después de desplegar
> `HFTClusterZonesNQDx` v1.7.0, pero ningún indicador puede causarlo ni arreglarlo.
> Herramienta: `tools/nt8_limpiar_csproj.py` (idempotente, con tests).

---

## Síntoma

Al compilar, NinjaTrader devuelve decenas de errores y **no compila nada**:

```
NinjaTrader\Custom\resources.cs   Duplicate 'System.Reflection.AssemblyCompanyAttribute'   CS0579   13
NinjaTrader\Custom\resources.cs   Duplicate 'System.Reflection.AssemblyCopyrightAttribute' CS0579   14
...
```

La pista está en las líneas: **13 a 20, repetidas en bloques**. No es un error que se
propaga; es **el mismo archivo contado muchas veces**.

## Causa

`NinjaTrader.Custom.csproj` arma su lista de fuentes por glob, y se llevó puestos los
ocho archivos que MSBuild genera para las assemblies satélite:

```
obj\Debug\de-DE\NinjaTrader.Custom.resources.cs
obj\Debug\es-ES\...   fr-FR   it-IT   ko-KR   pt-PT   ru-RU   zh-Hans
```

Cada uno declara, en sus líneas 13–20, los mismos ocho atributos de assembly
(`AssemblyCompany`, `AssemblyCopyright`, `AssemblyFileVersion`, …). Ocho copias del
mismo atributo → `CS0579` ocho veces por atributo.

El proyecto **ya excluía `obj\**`** de `None` y de `Page`:

```xml
<None Remove="obj\**" />
<Page Remove="obj\**" />
```

Faltaba exactamente una línea: la de `Compile`. La exclusión estaba escrita para dos de
los tres tipos de item y nadie lo notó, porque sólo falla cuando `obj\` ya tiene una
build previa **y** NT8 regenera el proyecto.

## Corrección

1. Se borraron los ocho `<Compile Include="obj\...">` (491 → 483 fuentes).
2. Se agregó `<Compile Remove="obj\**" />` junto a los otros dos, para que no vuelvan.

Respaldo en `NinjaTrader.Custom.csproj.bak_20260908`.

## Si vuelve

NT8 regenera el `.csproj` cuando detecta cambios en el árbol de `Custom`, así que puede
volver a barrer `obj\`. Se corre de nuevo:

```
.venv\Scripts\python tools\nt8_limpiar_csproj.py
```

Es idempotente y no toca ninguna fuente real. Con `--dry-run` dice qué haría.

## Lo que deja como aprendizaje

Un gate escrito para dos de tres casos no protege: protege hasta que aparece el tercero,
y hasta entonces se ve igual que uno completo. Es la misma forma que la banda de
cobertura de P-72 y que la escala de H2 — la diferencia acá es que el compilador avisa.

---

**Aporte al referente:** desbloquea la compilación de NT8, sin la cual no hay oráculo,
no hay captura contrastable y no hay paridad que medir.
