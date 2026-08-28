# H-ES-CTX-1 — pre-registro de contextos para las zonas HFT sobre ES

> ## ⬛ SUPERSEDED — 2026-08-21
>
> Reemplazado por **`H-ES-CTX-2_PREREGISTRO.md`**. Nunca se congeló ni se ejecutó.
> Se conserva sin editar como registro del camino (ATJ-16: una retractación agrega,
> no borra).
>
> **Las seis razones por las que no sirvió**, todas medidas después de escribirlo:
>
> 1. `C2` (solapada/limpia) usaba `abs(Δt) ≤ 30 min` — contaba zonas **futuras**.
>    Feature POST disfrazada de contexto.
> 2. El MDE `IQR/1,349` asumía normalidad sobre una distribución sesgada, mezclaba
>    dispersión full-sample con n de celda, y trataba una mediana de medianas como
>    una media.
> 3. Faltaban ponderación, `B`, `seed` y el test de equivalencia entero.
> 4. §0 descartaba memoria de nivel citando `0,1775`, que era un estimador inválido.
> 5. Se escribió antes de R2 y R3, que son sus insumos.
> 6. **`C1: RTH vs FUERA` es el contexto MÁS confundido con el ancho** —
>    corr **−0,255** contra +0,085 del que finalmente se eligió. Justo la variable
>    que R2 mostró que sesga el emparejamiento.

- **Congelado 2026-08-20** · estado `PREREGISTERED_NOT_RUN`
- Escrito **después** del censo descriptivo y **antes** de cualquier medición condicionada.
- Población: oráculo `HFTZonesESPureV2Flat`, ES 03-26, 62 sesiones pre-firewall,
  9.486 zonas, 51,8 % / 48,2 % por dirección. Snapshot `a7dec2ee382c32ea`.

---

## 0. Por qué estos contextos y no otros

Se descartaron dos candidatos que parecían fuertes:

- **Memoria de nivel.** Era el único hallazgo positivo de la familia. **No sobrevive**
  a un nulo bien especificado: el `p<0,05 en el 71 % de las sesiones` salió de que el
  estadístico observado redondeaba mids de medio tick sobre el nivel entero mientras el
  nulo eran enteros sin nada que colapsar. Con ambos lados en medios ticks y el mismo
  constructor de mid: **p mediana 0,1775**, `p<0,05` en el 31 %. No se congela un
  contexto sobre esto.
- **Números redondos.** Verificado sobre el dato en vez de citado: los ticks de ES por
  resto módulo 4 dan 0,2579 / 0,2465 / 0,2484 / 0,2473. Exceso de **0,79 pp** sobre la
  uniforme. El clustering masivo que documenta la literatura para otros índices **no está
  en ES**, así que no es ni contexto ni confundidor acá.

Los que quedan se congelan por **variación estructural medida**, no por resultado.

---

## 1. Contexto primario — `C1: RTH vs FUERA`

`RTH` = 09:30–16:00 hora de Nueva York (`rth_am` + `rth_pm`).
`FUERA` = el resto (`asia`, `europa`, `premarket`, `cierre`).
Hora con **DST real** vía `zoneinfo`, nunca offset fijo.

**Justificación estructural, del censo:**

| | RTH | FUERA |
|---|---|---|
| zonas | 7.935 | 1.551 |
| tasa (zonas / millón de ticks) | 129–193 | 70–306 |
| ancho mediano | 3–4 ticks | 5–6 ticks |
| fracción `Absorb` | 0,68–0,79 | 0,36–0,42 |

Fuera de RTH las zonas son **anchas y son barridos reales**; dentro son **angostas y son
absorción**. Es la misma etiqueta puesta sobre dos objetos distintos.

## 2. Contexto secundario — `C2: solapada vs limpia`, **sólo dentro de RTH**

Solapada = tiene ≥1 zona pisándola creada a <30 min. Limpia = ninguna.

**Se prueba únicamente dentro de RTH, y esto es deliberado**: fuera de RTH el solape
mediano es **0** en Asia y Europa, así que declararlo globalmente volvería a cortar por
fase con otro nombre. Dentro de RTH sí hay variación (mediana 2 en `rth_am`, 5 en `rth_pm`).

---

## 3. Estimando primario — uno solo

**Delta pareada de `ticks_por_ancho`** en el cruce borde a borde: cada zona contra **su**
casi-zona emparejada (misma sesión, ancho exacto, ≤30 min), mediana dentro de la sesión,
y la **sesión como unidad de análisis**.

La unidad es la sesión y no la zona porque las zonas **no son independientes**: Fano 7,78,
81 % de solape, y m = 156 zonas por sesión. Con `DEFF = 1 + (m−1)·ρ`, un ρ de apenas 0,05
da **DEFF 8,8** — las 9.486 zonas valen ~1.078 observaciones. Analizar por zona produciría
intervalos casi 3× más angostos de lo que corresponde.

**Todo lo demás es secundario y se rotula como tal**: `ticks`, `ms`, `volumen`,
`vol_por_ancho`, y el retorno a la zona re-medido con el control casi-zona.

## 4. Potencia, publicada antes de medir

Con la dispersión entre sesiones observada en la corrida agregada:

| celda | sesiones usables (≥8 zonas) | MDE (80 %, α=0,05, bilateral) |
|---|---|---|
| RTH | 59 de 62 | **±4,0** `ticks_por_ancho` |
| FUERA | 55 de 62 | **±4,1** `ticks_por_ancho` |

Sobre una base mediana de 167,6, eso es **±2,4 % relativo**. La medición agregada dio
+0,8 — bien por debajo del MDE, o sea que aquel nulo **no descartaba** efectos menores a
ese umbral. Ahora sí queda declarado cuánto se puede ver.

## 5. Multiplicidad

Un estimando primario × dos celdas de `C1` = **2 pruebas primarias**. Se corrige por
Holm. `C2` y las métricas secundarias **no entran** en la familia primaria y se publican
como exploratorias, explícitamente rotuladas.

## 6. Cómo se refutaría

- La delta pareada cruza cero **en las dos celdas** → el contexto no separa nada y la
  familia queda cerrada también en su forma condicional.
- El efecto aparece en `FUERA` pero desaparece al condicionar por ancho → era ancho, no
  fase. `FUERA` tiene zonas de 5–6 ticks contra 3–4 de RTH, así que **este es el
  confundidor más probable** y se prueba explícitamente con un análisis estratificado
  por ancho.
- El efecto aparece sólo en la métrica primaria y en ninguna secundaria → conteo, no
  mecanismo.
- El efecto desaparece con la sesión como unidad pero existía por zona → era el
  agrupamiento.

## 7. Lo que este estudio NO decide

Aunque diera positivo, **no es un edge**. Es información condicional: el eslabón 2 de la
cadena `geometría → información → P&L bruto → edge neto`. No hay reglas de entrada ni
salida, ni sizing, ni fricción estimada para ES, ni fills. Un resultado acá **no autoriza**
pasar a P&L: eso necesita su propio manifiesto y el OK de Nico.

## 8. Firewall

Holdout 2026-07-01 → 2026-12-31 intacto. Esta medición no lo toca. Todo el oráculo es
pre-firewall, con 0 zonas vivas al corte, verificado en la auditoría del 2026-08-20.
