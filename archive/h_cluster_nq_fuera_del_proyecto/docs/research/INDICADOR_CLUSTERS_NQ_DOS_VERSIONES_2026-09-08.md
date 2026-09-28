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

## Decisión tomada: se adopta Dx

`HFTClusterZonesNQDx` no es una variante: es un **superconjunto**. Tiene integrado todo
lo que estaba del otro lado y además lo que faltaba.

| pieza | ¿está en Dx? |
| :-- | :-- |
| peso continuo en la densidad (`weight = expLookup[d] * pesoZona`) | sí |
| `MinContributingZones` | sí |
| tabla exponencial precalculada + scatter | sí |
| fix de canibalización (`EXPIRED` en el filtro de fusión) | sí |
| procedencia en el CSV (`# meta` / `# params`) | sí |
| modo `SoloMuertePorBarras` + `BarrasExtensionMuerte` | sí |
| render por GPU (SharpDX) con culling de viewport | **sólo Dx** |
| defaults que no esconden el objeto | **sólo Dx** |

Mantener dos archivos del mismo objeto sólo agrega superficie para que diverjan. Se
adopta Dx y `HFTClusterZonesNQ` queda **retirado**: se conserva en el repo como registro
de lo que corrió, sin uso en chart.

## Lo que se arregló al adoptarlo (v1.6.0 → v1.7.0)

**Etiquetas ilegibles.** El texto de cada cluster se dibujaba en `yTop - 14f`, es decir
14 px sobre su propio techo. Como los clusters se solapan todo el tiempo, varias
etiquetas caían en la misma coordenada y se escribían encima —es el amasijo que se ve en
la captura del 08-09—. Ahora `BuscarHuecoEtiqueta` baja de a 14 px hasta encontrar lugar
libre, comparando solape vertical **y** horizontal.

Importa más de lo que parece para lo que viene: las capturas con hora que Nico va a
mandar se contrastan contra el espejo Python leyendo **esas etiquetas** (estado, densidad
pico, capacidad, POC). Ilegibles, no hay contraste posible.

No se tocó ningún parámetro de comportamiento. El objeto que dibuja es el mismo.

## Lo que sigue, y no es «unificar» a medias

**El archivo que Nico mira no está en el repo.** `HFTClusterZonesNQDx.cs` vive sólo en
`Documents\NinjaTrader 8\bin\Custom\Indicators\`. Es la misma familia de falla que la
divergencia de ramas del 2026-08-05 y la del 2026-08-15: **lo que se usa no es lo que
está registrado**, y cada lado es internamente coherente.

Orden propuesto:

1. **HECHO** — `HFTClusterZonesNQDx.cs` v1.7.0 está en `nt8/` y desplegado en NT8, con
   respaldo del anterior en `HFTClusterZonesNQDx.cs.bak_20260908`.
2. **HECHO** — `nt8/HFTClusterZonesNQ.cs` se sincronizó con lo que realmente corría en la
   máquina (el repo estaba 87 líneas atrás: le faltaban `SoloMuertePorBarras`, la muerte
   contada desde `EndBar` y el `EXPIRED` del filtro de fusión) y queda **retirado**.
   Borrarlo de la carpeta de NinjaTrader es decisión de Nico, no se toca su instalación.
3. **PENDIENTE, y es lo próximo** — re-alinear `hftclusterzones.py` contra los defaults
   de Dx y medir paridad de la capa de clusters, que **nunca tuvo oráculo comparado**.
   Recién ahí una captura con hora se puede contrastar contra el espejo.

Hasta el punto 3, cualquier medición Python sobre clusters describe una configuración
que **no es la que Nico ve**.

---

**Aporte al referente:** identifica en una línea por qué el objeto no se veía —un default
de dibujo contra un ciclo de vida ya medido— y deja asentado que la versión en uso no
está versionada, que es la precondición para que cualquier observación de chart sea
citable.
