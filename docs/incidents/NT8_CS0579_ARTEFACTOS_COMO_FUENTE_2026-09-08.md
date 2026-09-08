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

## Un detalle que cambia el diagnóstico

El proyecto declara `<EnableDefaultCompileItems>false</EnableDefaultCompileItems>`: el
SDK **no** hace glob, cada fuente está listada explícitamente. Así que esos ocho includes
**los escribió NT8**, recorriendo el árbol de `Custom\` sin saltear `obj\`.

Eso tiene una consecuencia práctica: **sacar los includes no alcanza**. Mientras los
archivos existan en disco, el próximo rescaneo de NT8 los vuelve a listar, y el
`<Compile Remove>` se pierde si NT8 reescribe el proyecto. Hay que hacer las dos cosas.

## Corrección

1. Se borraron los ocho `<Compile Include="obj\...">` (491 → 483 fuentes).
2. Se agregó `<Compile Remove="obj\**" />` junto a los otros dos, para que no vuelvan.
3. Se renombraron a `.apartado` los ocho `.resources.cs` bajo `obj\`, para que un
   rescaneo no los pueda encontrar. Se renombra en vez de borrar: es reversible y son
   artefactos que MSBuild regenera.

La carpeta `obj\` entera **no** se puede mover con NinjaTrader abierto —queda tomada—,
pero los archivos de adentro se renombran igual. Por eso la herramienta opera archivo por
archivo y avisa cuál quedó bloqueado en vez de fallar entera.

Respaldo en `NinjaTrader.Custom.csproj.bak_20260908`.

## Verificación

El proyecto completo compila **fuera del árbol** con **0 errores**, con el indicador nuevo
incluido:

```
dotnet build "...\NinjaTrader.Custom.csproj" -p:BaseIntermediateOutputPath=<tmp>/obj/ -p:OutputPath=<tmp>/bin/
```

Sólo quedan avisos `CS0436` preexistentes por tipos duplicados entre `GexLevelsAPI.dll` /
`NinjaTrader.Vendor.dll` y las fuentes de `Custom\` — son de antes y no bloquean.

Esto separa dos cosas que conviene no confundir: **el código compila**, y lo que fallaba
era la lista de fuentes que NT8 arma.

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
