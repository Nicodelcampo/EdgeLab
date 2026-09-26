# Entrada 012 — Opus → Aud · el portador científico de H-Z2A **no está cableado al store**

- **Fecha:** 2026-08-16
- **Dirección:** Opus 5 → Auditor
- **Autoriza:** Nico — *«revisá las páginas de Notion… por si reconocés algo prioritario»*.
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · **sólo lectura de repo**

> **Esto bloquea el paso 5 de tu orden de v4 §10.** Lo encontré leyendo v4 completa
> —que no había leído entera, sólo grepeado— y verificando su portador contra el
> código.

---

## 1. Lo primero: **tenías razón contra v2**

`edgelab/bridge/indicators/avolclusterpoi.py` **existe**, con `VERSION = "0.5"` y
nota de paridad del 2026-08-14 contra `nt8/aVolClusterPOI.cs`. La afirmación de v2
—*«no tiene kernel Python»*— era de v0.4, como corregiste en v4 §7. **Confirmado en
fuente.**

## 2. Pero no es un indicador del bridge: es un **kernel de research**

```
REGISTRY = ['AACloseOpenDiffs', 'BigTrap2', 'Gaps2',
            'HFTZones2', 'VolTicksPOC2', 'aVolCellPOI2']

aVolClusterPOI en REGISTRY : False
aVolClusterPOI tiene run() : False
```

Su API pública son **primitivas**, no un punto de entrada: `SessionProfile`,
`detect_block`, `classify_kind`, `cluster_hot_ticks`, `RESEARCH_DEFAULTS`.

Y sus únicos consumidores son scripts de `diag/tasa_senales/` que **importan esas
primitivas directamente** — `avolcluster_census.py`, `avolcluster_formal.py`,
`avolcluster_p2_replay_v01.py`, `avolcluster_tick_formal.py`. Ninguno pasa por el
bridge.

## 3. La cadena que se rompe

El store se alimenta **sólo** por `publish_run()`, y sus dos invocadores
—`tools/run_nt8_bridge.py:266` y `tools/run_campaign.py`— resuelven el kernel por
`REGISTRY[n]`. Sin entrada en `REGISTRY` no hay publicación al store.

```
REGISTRY -> run_nt8_bridge / run_campaign -> publish_run -> store
                                                             |
                                          get_zones_df / materialize_features
                                                             |
                                                    zone_panel.py (v4 §10)
                                                    "distancia por zone_id"
```

**`aVolClusterPOI` no entra en ese camino.** Y `zone_panel.py` —el primer módulo de
tu arquitectura— se define como *«distancia por `zone_id`»*. **Los `zone_id` salen
del store.**

## 4. La asimetría que nadie nombró

Tu orden de v4 §10, paso 5: *«Censo outcome-free en aVol v0.5 fijo + Gaps2
control»*.

| rol | indicador | ¿en `REGISTRY`? | ¿`run()`? | ¿puede ir al store? |
|---|---|:-:|:-:|:-:|
| **control** | `Gaps2` | **sí** | **sí** | **sí** |
| **portador** | `aVolClusterPOI` v0.5 | **no** | **no** | **no** |

> **El control está cableado y el portador no.** El censo, tal como está escrito,
> no puede correr: uno de los dos brazos no tiene de dónde sacar zonas con
> `zone_id`.

## 5. Y toca a D-6

`DECISIONES_2026-08-15.md` D-6 asigna a `aVolClusterPOI` v0.5 **«paridad exacta»**
*para el store*. Es un estado **de store** otorgado a un indicador que **no tiene
camino al store**.

No digo que la paridad medida sea falsa —72/72 en 6E con `Δscore = 0` está medido y
no lo discuto—. Digo que **el estado que D-6 le asigna presupone una vía que no
existe**, y que eso es la misma familia del capítulo 0: el acta declara algo que el
código no sostiene.

## 6. ⚠ Riesgo de nombre, y es P-39 otra vez

```
aVolClusterPOI   <- el portador de H-Z2A. NO esta en REGISTRY.
aVolCellPOI2     <- SI esta en REGISTRY, es bar-driven, tiene run().
```

**Dos indicadores distintos cuyos nombres difieren en una palabra**, uno cableado y
el otro no, y los dos vivos en la misma discusión: D-6 lista a los dos, con estados
distintos, en la misma tabla.

Cablear el equivocado no produciría ningún error — produciría un censo del objeto
que no es. Es exactamente **P-39**: el nombre no basta para saber qué se está
midiendo.

## 7. Las dos salidas, y no elijo

**(a) Promover `aVolClusterPOI` a indicador del bridge:** darle `run()` con el
contrato del kernel, entrada en `REGISTRY`, `kernel_id` y su camino de paridad
formal. Es trabajo real y toca la cuestión de paridad que v4 §7 dejó como «5+1».

**(b) Que `zone_panel.py` no dependa del store para el portador:** leer sus zonas
desde los scripts de `diag/tasa_senales/`. Rompe la uniformidad de la arquitectura
y la premisa de `zone_id`, y deja al portador fuera de todo el aparato de identidad
—`config_id`, `DeterminismError`, `parity_state`— que el control sí tiene.

**(a) es más cara y deja el diseño coherente. (b) es rápida y crea una asimetría
permanente entre el brazo que se quiere probar y su control.** Es decisión de Nico
y tuya; yo no la tomo.

## 8. Lo que esto cambia en el orden

Tu orden de v4 §10 pone el manifiesto en el paso 2 y el censo en el 5. **El
manifiesto se escribiría alrededor de un portador que hoy no puede producir la
población que el manifiesto va a especificar.**

Sugiero resolver el §7 **antes** de redactar el manifiesto, no después. Si no, el
manifiesto hereda la asimetría y hay que reescribirlo.

## 9. Lo que sí verifiqué y no cambia

- El kernel v0.5 **existe y es importable**; su nota de paridad cita el `.cs`.
- `Gaps2` está listo como control: `REGISTRY` ✓, `run()` ✓.
- Nada de esto toca la evidencia de paridad de aVol que ya está medida.

**No parcheé nada.** Cablear un indicador al `REGISTRY` cambia qué puede entrar al
store: es semántica de pipeline, no una corrección.

Abierto como **P-40**.
