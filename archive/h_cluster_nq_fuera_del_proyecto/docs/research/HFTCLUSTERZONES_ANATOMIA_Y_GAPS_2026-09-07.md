# HFTClusterZonesNQ — anatomía del objeto y lo que falta para medirlo

> Leído sobre `nt8/HFTClusterZonesNQ.cs` (1.522 líneas, commit `89da325`).
> Espejo Python: `edgelab/bridge/indicators/hftclusterzones.py` (21 tests).
> Se lee junto a `docs/research/deep_research/DEEP_RESEARCH_HFT_CLUSTER_MAGNETISMO_2026-09-07.md`
> y `docs/research/PLAN_MODULAR_HFT_CLUSTER_FUNNEL_2026-09-07.md`.

---

## 1. Es un objeto mucho mejor que el anterior

Contra `HFTZonesNQPureV4`, que era el que se iba a medir hasta ayer:

| | V4 (clusters de caja) | **HFTClusterZonesNQ** |
| :-- | :-- | :-- |
| Pertenencia | histograma de cajas, binario | **kernel gaussiano** con `σ` barrible |
| Vigencia de una zona | `ExtensionDibujo` (**cosmético**) | `MaxClusterAgeBars` (**de investigación**) |
| Muerte del cluster | no tiene | cuatro desenlaces distintos |
| Persistencia | ninguna | **log de eventos append-only** |

Los dos primeros defectos del deep research (**D1**, vigencia cosmética; **D3**, dibujo
proyectado al futuro como fuente de la impresión visual) dejan de aplicar: la vigencia
es ahora un parámetro de investigación, y el ciclo de vida no depende del dibujo.

**D2 sigue vivo pero acotado.** La expansión usa marcas de agua (`peak_density`,
`seed_volume`, `capacity_volume`, `contributing_zones` sólo suben; la geometría es la
unión histórica y nunca se encoge). La diferencia es que ahora **cada expansión emite
un evento con el estado completo**, así que el censo as-of *sí* es reconstruible —
reproduciendo el flujo de eventos, no leyendo el objeto final. Leer el objeto final
sigue estando prohibido.

## 2. Los seis eventos son riesgos competitivos de verdad

`CLUSTER_CREATED`, `CLUSTER_EXPANDED`, `CLUSTER_TOUCHED_POC`, `CLUSTER_DEPLETED`,
`CLUSTER_INVALIDATED`, `CLUSTER_EXPIRED`.

Es exactamente lo que el escalón 2 del embudo necesita. Y confirma la advertencia del
deep research: **Kaplan-Meier está prohibido acá**. Tratar la invalidación o la
expiración como censura simple sobreestima la incidencia de toque. Va CIF.

## 3. Cinco hallazgos del código que cambian la interpretación

Todos medidos contra el fuente, y clavados con test en el espejo.

**3.1 — El POC no es el nivel de más volumen.** Con `σ` ancho el campo es unimodal y
el POC cae en el **centro geométrico** de las zonas. El desempate por volumen ponderado
sólo actúa cuando dos ticks empatan en densidad dentro de `1e-4`. Interpretar el POC
como "el nivel donde está el dinero" sería un error de lectura, no del indicador.

**3.2 — La envolvente recorta el kernel antes que su propio corte.** La grilla se
construye con `±3σ` alrededor de las zonas, pero el kernel declara aportar hasta
`3.5σ`. Los `0.5σ` exteriores nunca se evalúan. Afecta el ancho de los clusters de
borde.

**3.3 — Un cluster `EXPIRED` todavía puede absorber expansiones.** El filtro de
`matching` excluye `Depleted` e `Invalidated`, pero no `Expired`. Su geometría se
actualiza y se emite `CLUSTER_EXPANDED`, aunque no revive ni vuelve a consumir.
Cualquier análisis de supervivencia tiene que decidir explícitamente qué hace con esos
eventos post-mortem.

**3.4 — La invalidación exige que la capacidad NO estuviera casi agotada** (`<80 %`).
Un cluster muy operado que después se perfora **no** entra en la incidencia de
invalidación. Si nadie lo declara, esa incidencia sale sesgada hacia abajo.

**3.5 — Con más de 300 clusters se descarta el más viejo en silencio**, sin evento
terminal. Es un agujero en el censo: el cluster simplemente desaparece. El espejo emite
`CLUSTER_EVICTED` para taparlo; **el `.cs` no**.

## 4. Lo que el log de eventos todavía no permite medir

El header actual es:

```
timestamp,event,cluster_id,start_ts,end_ts,lower,upper,poc,peak_density,
seed_vol,seed_cvd,cap_vol,vol_inside,delta_inside,remaining_cap_pct,state
```

Falta, y cada faltante bloquea un escalón concreto:

| Falta | Bloquea |
| :-- | :-- |
| **índice de barra** del evento | todo: hoy sólo hay timestamp, y las poblaciones del embudo se definen por barra |
| **precio en el instante del evento** | escalón 1: sin él no hay distancia `d` al POC, que es la variable del nulo browniano |
| **σ local** (volatilidad realizada de una ventana previa) | escalón 1: el nulo `2(1−Φ(d/(σ√t)))` es **condicional a σ**; con σ global el efecto de volatilidad se confunde con atracción |
| **ids de las zonas contribuyentes** | escalón 5: sin ellos no se puede condicionar por la intensidad que creó el cluster |
| **13 parámetros del motor de zonas** | reproducibilidad: la línea `# params` sólo publica `sigma`, `minDensity`, `capMult`, `invalTicks` |
| **`run_id`** | el archivo se abre en `FileMode.Append`: dos corridas se concatenan sin separador |
| evento terminal en la evicción FIFO | censo completo (ver 3.5) |

**Nada de esto es reconstruible después.** Es el cuello de botella que el deep research
anticipó, y es el contenido real del módulo M0.

## 5. `hftzones2.py` NO sirve como espejo de la capa de zonas

Parecía que sí —mismos nombres de parámetros, mismos defaults (`min_pasos=8`,
`min_sweep_ticks=4`, `retro_pct_height=50`, `max_avg_ms=25`)— y habría ahorrado la
mitad del trabajo de paridad. **No sirve**, por dos diferencias verificadas en el
fuente:

1. **Le falta la compuerta de retroceso.** El `.cs` exige
   `limpioOk = isAbsorb || (maxRetroceso <= max(MaxRetrocesoTicks, pct·sweepTicks))`.
   La aceptación de `hftzones2.py` (`ok = structural and avg_ms… and total_vol…`) no
   la tiene.
2. **Sus umbrales son derivados, no fijos.** `hftzones2` calibra por sesión
   (`eff["max_total"] = eff["max_avg"] · min_pasos · total_ms_mult`,
   `eff["min_total_vol"] = vol_mult_median_tick · med_v · min_pasos`), mientras el `.cs`
   usa `MaxTotalMs=500` y `MinTotalVolume=50` fijos.

Validar paridad contra él habría dado "paridad" contra **otro objeto**. Es la misma
familia de error que el proyecto ya documentó: un validador que devuelve verde sobre la
cosa equivocada.

## 6. Estado de la paridad ULP

Se triaron las 20 expresiones nuevas (`HFTClusterZonesNQ.cs` 10, `CleanImpulses.cs` 10)
en `tools/ulp_sweep_baseline.json`, con evidencia por cada una:

- **Los bordes del cluster son inmunes por medio tick**: `cLower` y `cUpper` se
  construyen como `tick·TickSize ∓ TickSize·0.5`, así que ningún precio operado puede
  caer sobre el umbral.
- **Las comparaciones de grilla son inmunes por monotonía**, y esto vale **porque el
  tick de NQ es `0.25 = 2⁻²`** y todo precio `k·0.25` es exacto en `double`.
  **El argumento no se transporta a GC (`0.10`) ni a ZB (`1/32`).** Si el indicador se
  corre ahí, hay que re-triar.

Quedan 39 candidatos sin triar en archivos que este trabajo no tocó
(`BigTrap2Universal*`, `BigTrap2Absorption`, `AVolZone*`, `Gaps2`).

## 7. Por qué el espejo no entró al REGISTRY

`edgelab/bridge/indicators/__init__.py` declara un contrato:
`run(ticks, bars[, footprints], params, chart_tz) -> dict(indicator, params, header,
csv_lines, events, zones, params_line)`, y su docstring dice que el REGISTRY es la única
fuente de verdad de qué indicadores existen.

`hftclusterzones.py` es un **motor con estado**, no un kernel por barra: no cumple esa
firma y no pasó smoke sintético contra oráculo real. Agregarlo habría hecho que el
REGISTRY afirmara una cobertura inexistente.

## 8. Lo que sigue

1. **Enriquecer el log del `.cs`** con los siete faltantes de §4. Es la pieza que
   convierte el indicador en instrumento de medición.
2. **Portar la capa de zonas** con la compuerta de retroceso y los umbrales fijos
   (§5), que es lo único que falta para que el espejo sea completo punta a punta.
3. **Correr una sesión de NQ y validar paridad** contra el log de eventos — no contra
   el estado final, que por §1 no es comparable.
4. Recién entonces, M1: distancia al POC contra el nulo browniano y el placebo
   emparejado. Ése es el escalón que replicó la muerte del 6E y el que puede cerrar
   esta línea temprano.

---

**Aporte al referente:** deja el objeto a medir caracterizado con precisión —incluidas
cinco rarezas que habrían sesgado la interpretación y un espejo falso que habría dado
paridad verde sobre otro objeto— y reduce el módulo M0 a una lista cerrada de siete
campos faltantes.
