# Dos indicadores para el mismo objeto — por qué el mío no dibuja nada

> Disparado por Nico el 2026-09-08: *«fijate la diferencia entre el tuyo y el de
> antigravity. además el tuyo se crashea un poco y demora más en cargar (y no marca
> ninguna zona). en cambio el de antigravity demora 1 segundo»*.

---

## Causa raíz de la pantalla vacía

`HFTClusterZonesNQ.cs` trae **`OcultarInvalidados = true`** por defecto. El ciclo de vida
ya está medido sobre el log real de eventos: **el 99,4 % de los clusters muere
`INVALIDATED`**. Ese default esconde casi todo el objeto.

No es un bug del motor: el motor calcula los clusters igual. Es un default de dibujo que
oculta el 99 % de lo que calcula.

## Diff de defaults, medido sobre los dos archivos

| parámetro | mío (`HFTClusterZonesNQ`) | Antigravity (`…NQDx`) | consecuencia |
| :-- | --: | --: | :-- |
| `OcultarInvalidados` | **true** | false | **la pantalla vacía** |
| `UsarSharpDX` | no existe | **true** | render por GPU: 1 s contra decenas |
| `MinCapacityVolume` | 1200 | 400 | mío exige 3× más volumen para agotarse |
| `CapacityMultiplier` | 2.5 | 1.0 | combinado con el anterior, 7,5× |
| `MaxClusterAgeBars` | 800 | 2500 | vidas distintas |
| `MinClusterDensity` | 3.0 | 3.5 | poblaciones distintas |
| `MinContributingZones` | 3 | 2 | poblaciones distintas |
| `OpacidadCluster` / `OpacidadMinima` | 60 / 8 | 30 / 4 | sólo estética |
| `SoloLogEnVivo` / `LogOnlyRealtime` | mismo concepto, **nombre distinto** | | |

Las dos últimas filas de sustancia (`MinClusterDensity`, `MinContributingZones`) importan
más de lo que parecen: **no son el mismo objeto**. Cualquier observación visual hecha
sobre el chart de Dx describe una población que el espejo Python no está generando.

## Lo que hay que hacer, y no es «unificar» a medias

**El archivo que Nico mira no está en el repo.** `HFTClusterZonesNQDx.cs` vive sólo en
`Documents\NinjaTrader 8\bin\Custom\Indicators\`. Es la misma familia de falla que la
divergencia de ramas del 2026-08-05 y la del 2026-08-15: **lo que se usa no es lo que
está registrado**, y cada lado es internamente coherente.

Orden propuesto:

1. **Traer `HFTClusterZonesNQDx.cs` al repo** y versionarlo. Es la versión viva.
2. **Retirar `HFTClusterZonesNQ.cs`** o dejarlo declarado explícitamente como espejo de
   paridad congelado, sin uso en chart. Dos indicadores del mismo objeto es peor que uno.
3. **Re-alinear `hftclusterzones.py`** contra los defaults de Dx, y volver a medir
   paridad — la capa de clusters todavía no tiene oráculo comparado, así que hoy no hay
   certificado que se rompa, pero tampoco hay ninguno que ampare al espejo.

Hasta el punto 3, cualquier medición Python sobre clusters describe una configuración
que **no es la que Nico ve**.

---

**Aporte al referente:** identifica en una línea por qué el objeto no se veía —un default
de dibujo contra un ciclo de vida ya medido— y deja asentado que la versión en uso no
está versionada, que es la precondición para que cualquier observación de chart sea
citable.
