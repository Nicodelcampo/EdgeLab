# D2 — ¿versionar los oráculos? Análisis para decisión de Nico

**Fecha:** 2026-08-06 · **Origen:** D2 del auditor
**Estado:** análisis, **no** decisión. Preparado mientras corre la curva.

> **El hallazgo levantado:** `oracles/*.csv` no está versionado, así que en un
> clon limpio el oráculo de P5 no existe y **T3a vuelve a fallar**. Sin copia
> local hasheada, P5 es imposible.

## 1. Los hechos, medidos

```
oracles/            78 MB · 28 archivos
mayores             12,5 MB · 9,3 MB · 6,2 MB
oráculo de P5       1,1 MB   sha256 7d0f464f…de27
                    ventana 2026-07-07 → 2026-07-24
```

Esa ventana está **entera dentro del holdout sellado** (≥ 2026-07-01) **y entera
dentro de la cuarentena INC-005** (07-01 → 07-24).

### Y hay tres CSV YA versionados, por un agujero de la regla

```
oracles/split/BigTrap2_v22_6E_0926__Tick10_run2.csv
oracles/split/BigTrap2_v22_6E_0926__Tick10_run3.csv
oracles/split/BigTrap2_v22_6E_0926__Tick25_run1.csv
```

**Causa:** `.gitignore:107` dice `oracles/*.csv`, y ese patrón **no matchea
subdirectorios**. `oracles/split/` quedó afuera de la regla.

**Ventana de los tres: `2026-06-14 → 2026-06-18`.** Es decir, **anteriores al
holdout: no hay material sellado en git**. Pero eso salió bien **por suerte, no
por diseño** — si esas capturas hubieran sido de julio, hoy habría EventLogs del
holdout en el repo, y git no olvida.

## 2. La pregunta no es una, son dos

Conviene separarlas porque tienen respuestas distintas:

| pregunta | qué necesita |
|---|---|
| **T3a** — «¿tengo el archivo correcto?» | **un hash**. No el contenido. |
| **P5** — «comparar los dos EventLogs» | **el contenido**. |

**T3a se resuelve sin versionar nada.** Es una pregunta de identidad, y un
`sha256` la contesta. P5 sí necesita el archivo — pero P5 **ya** es una operación
con permiso: exige la fila en `holdout_access_log.md`, porque su ventana está
sellada.

## 3. Las opciones

### A · Versionar todo (78 MB)

Reproducible de punta a punta. **Pero mete EventLogs de ventana sellada en el
repo de forma permanente:** git no olvida, así que borrarlos después no los saca
del historial. Cualquiera con acceso al repo se lleva material del holdout en un
`clone`. Contradice `oracles/README.md` y la política vigente.

### B · Dejar como está

Cero riesgo de distribución. **Pero T3a no es verificable en un clon limpio**, y
—peor— **dos máquinas pueden tener archivos distintos con el mismo nombre y nadie
se entera**. Es exactamente la falla del manifiesto del universo, que ya produjo
dos veredictos opuestos sobre si el estudio podía empezar.

### C · Versionar un MANIFIESTO, no el contenido **(recomendada)**

Un JSON con, por archivo: nombre, bytes, `sha256`, ventana temporal y la línea
`# meta`. **Sin una sola fila de eventos.**

Qué resuelve:

- **T3a pasa a ser verificable en cualquier clon**: se compara el hash del
  archivo local contra el manifiesto.
- **La deriva entre máquinas se vuelve detectable**, que es el problema que
  realmente muerde.
- **No entra material sellado a git.** La línea `# meta` es configuración del
  indicador, no mercado — y su lectura ya está registrada como
  `target_free_validation` en el log de holdout (2026-07-29).

Qué **no** resuelve: P5 sigue necesitando el archivo en la máquina. Pero eso ya
era cierto y ya estaba gateado por el log de accesos.

### D · Git LFS o repo privado aparte

Resuelve las dos, pero agrega infraestructura, credenciales y un segundo lugar
donde algo puede desincronizarse. **Desproporcionado para 78 MB** que ya están
respaldados fuera de git.

## 4. Lo que sí conviene arreglar, decida lo que decida

**El patrón de `.gitignore` está roto y es fail-open.** Hoy, dejar una captura
del holdout en cualquier subdirectorio de `oracles/` la commitea sin aviso.

```
oracles/*.csv        ->  oracles/**/*.csv
```

Eso **no desversiona** los tres que ya están —git no lo hace por cambiar una
regla— así que no toca nada existente: sólo cierra la puerta para lo próximo.
**Es independiente de la decisión D2** y no requiere aprobación de política:
hace que la política vigente funcione como está escrita.

## 5. Recomendación

**C, más el arreglo del patrón.** Razón corta: **T3a es una pregunta de
identidad y se contesta con un hash; P5 es una pregunta de contenido y ya está
gateada por el firewall.** Versionar el contenido paga el costo permanente de
tener el holdout en el historial para resolver un problema —la deriva— que un
manifiesto resuelve gratis.

**Lo que NO recomiendo, y lo digo explícito:** dejarlo como está. El riesgo real
no es perder los archivos —están respaldados— es que **dos máquinas midan contra
oráculos distintos creyendo que son el mismo**. Ya pasó con el manifiesto del
universo, y ahí no había hash que lo delatara.

**La decisión es de Nico.** El arreglo del patrón lo puedo hacer sin esperar; el
manifiesto también, pero conviene que lo apruebe antes de agregar un artefacto
nuevo al repo.
