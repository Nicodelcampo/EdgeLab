# INC-002 — El atlas nulo consumió 10 días del holdout sellado

**Fecha del hecho**: 2026-07-27, corrida de la madrugada (00:24 → 03:01).
**Detectado**: 2026-07-27 ~11:05, al escribir el filtro de tipo de día.
**Severidad**: alta — contaminación del holdout, irreversible.
**Estado**: cerrado con candado estructural y test.

---

## Qué pasó

El atlas de excursiones nulas corrió sobre **163 días efectivos**, de los cuales
**10 pertenecían al holdout sellado** (2026-07-01 → 2026-12-31):

```
2026-07-06  07-07  07-08  07-09  07-13  07-14  07-15  07-16  07-20  07-21
```

El atlas mide **MFE/MAE sobre horizontes futuros**. Eso es retorno. No es
`target_free_validation` — que cubre paridad, determinismo, geometría e
integridad, no distribuciones de excursión. La regla sellada dice, textual:
*"ningún placebo pisa el holdout"*.

## Causa raíz

**El filtro existía sólo en el docstring del atlas.**

```python
# tools/atlas_excursiones_nulas.py, línea 19, antes del fix
- optimizar estrategias; tocar el holdout; presentar esto como edge.
```

Eso era todo. No había una línea de código que lo hiciera cumplir.

Y no fue un descuido puntual, que es lo que lo hace importante:

1. `universe.py` **no filtra por fecha**, y hace bien: el censo debe cubrir todo
   el rango porque verificar integridad no gasta nada.
2. `check_holdout` **ya existía**, centralizado y bien escrito, en
   `edgelab/research/holdout_guard.py`. Nadie lo llamaba desde el camino de los
   estudios: se invocaba sólo desde `sim.simulate` y `camp001_dryrun`.
3. El atlas asumía que el filtrado pasaba aguas arriba.

**Ninguna capa era responsable, así que ninguna lo hizo.** La regla estaba
escrita en tres documentos y en cero condicionales.

## Por qué el atlas asimétrico habría repetido exactamente lo mismo

`tools/atlas_asimetrico.py` tampoco filtraba: heredaba la config de A0 y daba
por hecho el filtro. Se corrigió **antes** de su primera corrida del día — pero
sólo porque el defecto acababa de encontrarse en su hermano. Con un día de
diferencia, habría contaminado los mismos 15 días.

## Impacto declarado

- **No se declaró ningún edge** a partir del atlas contaminado, así que ninguna
  conclusión publicada depende de él.
- El daño real: **esos 10 días quedaron vistos**. El holdout ya no es virgen
  para 2026-07-06 → 07-21 en lo que hace a distribuciones de excursión. La
  próxima apertura formal **no cuenta como primera mirada** sobre ese rango.
- El atlas contaminado se **preservó entero** en
  `runs/atlas_CONTAMINADO_holdout_2026-07-27/`. No se borró: es la evidencia.

## Corrección estructural

Poner el filtro dentro de cada estudio repite el error con más superficie — el
estudio número once se escribe sin él y nadie se entera. Por eso:

### 1. Puerta única

`edgelab/research/universo_estudio.py::cargar_dias_de_estudio()` es el **único
camino sancionado** para obtener los días de un estudio.

- Con los parámetros por defecto **nunca** devuelve días `>= 2026-07-01`.
- Para incluirlos hay que pasar `incluir_holdout=True` **y** un `purpose`
  válido; entonces llama a `check_holdout`, que registra la apertura en
  `docs/holdout_access_log.md` y levanta si el propósito no la autoriza.
- Ningún código de investigación setea ese flag.

### 2. Test estructural

`tests/research/test_puerta_unica_holdout.py` **falla si existe cualquier camino
que lea el manifiesto de días sin pasar por la puerta**. No verifica que el
atlas filtre bien — el atlas *tenía* la regla escrita, en prosa. Verifica que no
haya una segunda puerta.

Al escribirlo denunció los cuatro consumidores que había:

```
tools/atlas_asimetrico.py
tools/atlas_excursiones_nulas.py
tools/correr_gates.py
tools/razon_de_varianzas.py
```

Los cuatro quedaron migrados. `correr_gates` pasa por la puerta con
`incluir_holdout=True, purpose="target_free_validation"` — la paridad **sí** es
uso permitido — y con eso su registro en el log dejó de ser manual, que era la
deuda anotada en la nota 2 de ese archivo.

### 3. Excepciones explícitas y chicas

La lista `EXENTOS` del test tiene exactamente dos entradas: los censos, que
**escriben** el manifiesto en vez de consumirlo. Agregar una excepción es un
cambio visible en el test, no una omisión silenciosa.

---

## Lección

La lección no es "hay que filtrar el holdout" — eso ya estaba escrito en el
NORTH STAR, en el contrato de validación y en el docstring del propio atlas.

La lección es que **una regla que vive en prosa no es una regla, es una
intención**. El proyecto ya aplica ese criterio a los datos: el censo no
confía en que el parquet esté bien, lo mide. Faltaba aplicárselo al proceso.

Comparación útil: el defecto de duplicación de bloque en el parquet se encontró
**por accidente**, porque cayó en una ventana donde no debía haber nada. Este se
encontró igual — por accidente, escribiendo otra cosa. En los dos casos, el
arreglo no fue tapar el caso conocido sino construir el detector que lo habría
encontrado a propósito.
