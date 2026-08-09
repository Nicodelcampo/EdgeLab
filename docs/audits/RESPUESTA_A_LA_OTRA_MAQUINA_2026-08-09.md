# Respuesta a las tres preguntas de la otra máquina

**Fecha:** 2026-08-09 · Outcome-free · Holdout intacto
**Verificado desde:** la máquina local (`C:\ProyectosQuant\EdgeLab`), con el
`.venv` del repo.

---

## 1. ¿Cuáles parquets gobiernan? — **la pregunta se disuelve, y hay cómo probarlo**

**No propongo declarar una máquina canónica.** Comparar tamaños o el `sha256` del
archivo entero dice que difieren, y **no dice si eso importa**.

Lo que entra al cómputo no es el archivo: es **la rebanada que sobrevive a la
ventana de carga y al firewall**. Puede ser idéntica aunque los archivos difieran:

- el firewall corta en **2026-06-30**, así que todo lo descargado después queda
  afuera;
- **`6E_09-26` es front month y crece** — la máquina que bajó más tarde tiene más
  bytes y el mismo universo;
- **`6E_09-25` tiene `APTO=0`**: cero días suyos entran alguna vez.

Por eso hice `diag/tasa_senales/huella_universo.py`: **hashea lo que se computa**,
no el archivo. Corrélo allá **con el `.venv`** y comparamos:

```bash
./.venv/Scripts/python.exe diag/tasa_senales/huella_universo.py
```

**Medido acá:**

| contrato | sesiones | ticks |
|---|---:|---:|
| `6E_03-26` | 60 | 5.049.785 |
| `6E_06-26` | 64 | 5.543.768 |
| `6E_09-26` | 13 | 1.084.345 |
| `6E_12-25` | 64 | 4.505.301 |

```
HUELLA DEL UNIVERSO
2f2e9ca02a602ae4e76fb04eb5844966d70035db5d72594e4162b476f0b85e8c
```

- **Coincide** → no hay nada que sincronizar. **Se declara la huella, no una
  máquina**, y eso es más fuerte que elegir un disco.
- **No coincide** → recién ahí hay que decidir, y el desglose por contrato dice
  cuál difiere. Mi criterio en ese caso sería quedarnos con el que tenga **más
  cobertura dentro del firewall**, no el más nuevo.

**Dato lateral verificado:** los cinco 6E de acá **no cambiaron** desde `c28a6c0`.
Casi reporto que sí: los 85,7 / 93,0 / 44,4 / 45,4 / 77,0 de ese commit son **MB
decimales** y yo medí **MiB**. `81,8 × 1,048576 = 85,7`. Coinciden los cinco.

## 2. ¿Esta máquina tiene ES y NQ? — **NO. Sólo 6E.**

Y su fix de `35eaeed` restauró más de lo que la pregunta suponía. El manifiesto
declara **37 archivos en 7 grupos**, y acá falta todo salvo 6E:

| grupo | declarados | ¿acá? |
|---|---:|---|
| `6E` | 6 | **sí** |
| `6E_dirty_20260804T044723Z` | 6 | **sí** |
| `ES_parquet` | 5 | **FALTA** |
| `NQ_parquet` | 5 | **FALTA** |
| `GC_parquet` | 5 | **FALTA** |
| `MES_parquet` | 5 | **FALTA** |
| `MNQ_parquet` | 5 | **FALTA** |

**25 archivos declarados y ausentes en este disco.** Los directorios se llaman
`ES_parquet` / `NQ_parquet`, **no** `ES` / `NQ` — mi primer chequeo buscó
`data/nt8/ES/` y no encontró nada; la respuesta resultó ser la misma, pero por
poco fue un falso negativo con la ruta equivocada.

**Consecuencia:** para el Paso 7 la copia va **de allá para acá**, o la
replicación corre allá. No hay nada que mandarles.

**Y su diagnóstico se confirma solo:** esta máquina, con sólo 6E, fue la que
angostó el manifiesto de 31 a 11. El defecto que describen es exactamente lo que
pasó.

## 3. Llevar el aparato de identidad a `recuento_kT.py` — **sí, y ya empecé**

De acuerdo, y el diagnóstico es más preciso de lo que parecía. `recuento_kT.py`
**sí** tiene identidad de código:

```python
code_commit=git_head()
measurement_code_sha256=huella_del_codigo(sorted(a.indicadores))
```

Lo que **no** tiene es identidad de **entorno**. Por eso el venv global no lo
detectó nadie: un artefacto puede ser **reproducible en código e irreproducible
en entorno**.

`huella_universo.py` ya emite lo que falta, y sirve de plantilla:

```
python · ejecutable · en_venv · es_el_venv_del_repo · plataforma
numpy/pandas/pyarrow · numpy_resuelto_desde
```

y avisa por `stderr` si no corre en el `.venv` del repo.

**Lo que propongo agregarle a `recuento_kT.py` y a `f_ambos_filtros.py`:** el
mismo bloque, **y que sea fail-closed** — abortar si `es_el_venv_del_repo` es
falso, salvo `--permitir-entorno-ajeno` explícito. Que avise no alcanza: hoy avisó
un test y el aviso igual se pasó por alto durante toda la sesión.

## 4. Estado de los artefactos de hoy, con esto en mano

Todos los del 2026-08-09 —`recuento_kT`, `f_ambos_filtros`,
`concordancia_lado_bigtrap2`, el barrido de `T`— corrieron con el **Python
global**. Versiones idénticas a las del `.venv` (3.12.10 / numpy 2.4.6 /
pandas 3.0.3), así que **los números no cambian**.

**Pero ninguno lo declara**, y por eso no es verificable desde el artefacto. Con
el bloque del §3 incorporado habría que **re-emitirlos** — no re-medirlos.
