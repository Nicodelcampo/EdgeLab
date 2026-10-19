# Auditoría del builder del bundle de Kaggle — 2026-08-14

**Artefacto auditado**: `tools/build_kaggle_bundle.py`, commit `56184a3`, blob
`df383c0685e5e46a806fb9b650a370bf529928c3`.
**Auditor**: externo (sandbox de Notion). **Método**: lectura del blob exacto del
repo + medición en sandbox. No se tocó ningún dato real, ningún outcome, ningún
holdout.
**Veredicto**: cinco defectos. Uno es un riesgo legal, otro hace que el script
**no pueda fallar**, y un tercero implica que el upload de 17,97 GB que hoy vive
en Kaggle **no lo produjo este script**.
**Reemplazo**: v2 fail-closed, blob `33b39364afb31da576a26500ea90dde5a2a9954f`
(47.692 B), verificado contra el commit `fb3ab8f2`: son byte a byte los mismos
bytes que pasaron el self-test (26 checks, 0 fallas).

---

## 1. Los cinco defectos, con su evidencia literal

### D-1 · Declaraba `CC0-1.0` sobre datos de mercado de terceros

```python
"licenses": [{"name": "CC0-1.0"}],
```

CC0 es dedicación al dominio público: afirma que cualquiera puede copiar,
redistribuir y explotar los datos sin restricción. Los términos de CME dicen lo
contrario de forma explícita ("license, sublicense, transfer, sell, resell,
publish, reproduce, or otherwise distribute or redistribute" están prohibidos).
No era un typo de metadata: era una afirmación de derechos que EdgeLab no tiene,
emitida por código, sin ningún gate humano en el medio, y con **P-07 abierta**
desde el 2026-08-14 justamente por no tener esa decisión tomada.

### D-2 · El encabezado prometía una identidad que el código no calculaba

El docstring anunciaba sha256 y rangos de fechas por archivo. Lo que el código
escribía por archivo era `num_rows` y el tamaño en bytes. Sin sha256 no hay
forma de verificar que lo subido es lo medido; sin min/max de `ts_utc_ns` no hay
forma de certificar **ausencia de holdout**. El manifiesto se leía como
evidencia y no lo era.

### D-3 · `id` y `OUT_DIR` no correspondían al upload real

```python
BASE = Path("E:/EdgeLab/data/nt8")
OUT_DIR = Path("E:/EdgeLab/kaggle_dataset")
...
"id": "nicodelcampo/edgelab-cme-futures-ticks",
"dataset_name": "edgelab-cme-futures-tick-universe",
```

El dataset que existe es `nicolasbuttaro/edgelab-cme-futures-universe`. Y en
`OUT_DIR` el script sólo escribía el JSON de metadata: **ningún parquet se
copiaba ni se enlazaba ahí**. Conclusión forzosa: los 57 archivos / 17,97 GB de
la v1 los subió otro procedimiento, no versionado. Es exactamente el patrón D9
de la auditoría externa (informes que citan artefactos que nadie puede
reproducir), esta vez del lado de los datos.

### D-4 · Fail-open: el script no podía fallar

```python
if not folder_path.exists():
    continue
...
except Exception as e:
    print(f"  Error en {f.name}: {e}")
```

Una carpeta ausente o un footer ilegible no cambiaban el resultado: el bundle
salía "bien" con un activo entero de menos. Además el filtro
`"all" not in f.name and "prev" not in f.name` excluía archivos en silencio, sin
dejar registro de qué quedó afuera ni por qué.

### D-5 · Tabla de cantidades duplicada a mano

Los 11 `tick_size` / `multiplier` estaban escritos en el script, en paralelo a
`edgelab/instruments.py`. Dos fuentes para el mismo número es una fuente que
driftea sin que nadie lo note.

### Y lo que faltaba por completo

El builder **no sabía nada del sello del holdout**. Se corrió el 14-ago-2026
sobre contratos 09-26 que contienen julio y agosto. Medición del auditor sobre
el parquet ancla `6E 09-26` (sha256 `1311bc5e…`): **871 filas** pertenecen al
trade date `2026-07-01`. Un corte en `2026-07-01T00:00:00Z` — el ingenuo — deja
pasar **7.200 s** de esa sesión, porque la sesión CME del 1-jul abre a las 17:00
CT del 30-jun (`2026-06-30T22:00:00Z`).

---

## 2. El reemplazo (v2)

| Gate | Regla | Falla → veredicto |
| --- | --- | --- |
| `G-INSTRUMENT` | el layout local y `CME_UNIVERSE` deben coincidir; multiplicadores sin drift contra el fixture v1 | `FAIL_INSTRUMENTS` |
| `G-LAYOUT` | toda carpeta declarada existe y es legible; hay candidatos | `FAIL_LAYOUT` |
| `G-IDENTITY` | sha256 + blob sha1 + filas + rango temporal real por archivo | `FAIL_INTEGRITY` |
| `G-HOLDOUT` | ningún archivo publicable alcanza la apertura de la sesión 2026-07-01 | `ABSTAIN_HOLDOUT` |
| `G-BUDGET` | `inventory.budget_gates` (10 GB / 20 archivos del contrato + límites de plataforma) | `ABSTAIN_CAPACITY` |
| `G-LIC` | decisión de licencia aprobada y legible por máquina | `ABSTAIN_LICENSE` |

Exit codes: `0` PASS, `2` ABSTAIN_*, `1` FAIL_*. Cuarentena con causa nombrada:
`MISSING_FOLDER`, `UNREADABLE_FOLDER`, `FILENAME_UNPARSEABLE`,
`ASSET_FOLDER_MISMATCH`, `CENSUS_ERROR`, `UNCERTIFIABLE`, `HOLDOUT_OVERLAP`.

Decisiones de diseño que importan:

1. **El sello se mide por trade date CME, no por UTC.** Un archivo es elegible
   sólo si `ts_max < 2026-06-30T22:00:00Z`. El corte ingenuo se calcula igual,
   pero sólo para **reportar** el leak que produciría (`naive_utc_overlap`).
2. **La licencia es un gate de código.** Lee el bloque `EDGELAB-LICENSE-GATE` de
   `docs/research/DATA_LICENSE_DECISION.md`. Sin `status: APPROVED` no hay
   metadata ni staging. Si el documento declarara una licencia que afirme
   redistribución (`CC0-1.0`, `CC-BY-*`, `PDDL`, `ODbL`, `MIT`…) **aborta**, no
   abstiene.
3. **`bundle_index.json` se escribe siempre**, incluso cuando el veredicto no es
   PASS: es el rastro de auditoría. Lo que sólo ocurre con PASS es el staging,
   `dataset-metadata.json` (con `isPrivate: True` y `--dataset-id` obligatorio) y
   el `README.md` con la restricción de uso.
4. **El índice sella su propio contenido**: `index_sha256` es el sha256 canónico
   del índice sin ese campo — el defecto H1 del dictamen AVOLT (sello que no
   cierra contra su propio contenido) no puede repetirse acá.
5. **El staging re-verifica**: después de enlazar o copiar cada archivo vuelve a
   calcular su sha256 y aborta si difiere, y emite `files.sha256` para que el
   upload sea verificable con `sha256sum -c`.

---

## 3. Evidencia del self-test (26 checks, 0 fallas)

`python tools/build_kaggle_bundle.py --selftest`, cableado en
`tests/test_kaggle_bundle_builder.py`. No requiere pyarrow ni datos reales: usa
árboles temporales y un censo de footer simulado.

| # | Qué prueba | Medición |
| --- | --- | --- |
| T1 | apertura del holdout | `2026-06-30T22:00:00+00:00` |
| T1b | leak del corte UTC ingenuo | `7200 s` |
| T1c | el trade date cambia en ese ns exacto | `20260630 → 20260701` a ±1 ns |
| T2 | los 11 multiplicadores derivados de `instruments.py` reproducen la tabla del v1 | sin drift |
| T2b | layout == `CME_UNIVERSE` | 11 == 11 |
| T3 | `sha256_file` contra `hashlib` | igual |
| T4 | licencia `PENDING` | `ABSTAIN_LICENSE`, exit 2, sin staging |
| T5 | licencia `CC0-1.0` en el documento | aborta |
| T6 | 09-26 sin cortar | `ABSTAIN_HOLDOUT` + `RECUT_REQUIRED` |
| T6d | archivo cuyo `ts_max` = apertura − 1 ns | elegible |
| T7 | bundle limpio | `PASS` |
| T7b | `index_sha256` cierra contra su propio contenido | sí |
| T7c | metadata | `isPrivate: True`, licencia no prohibida |
| T7d/e | staging | 2/2 con sha256 idéntico + `files.sha256` |
| T7f | README | trae la restricción de uso |
| T8 | carpeta ausente (el v1 hacía `continue`) | `FAIL_LAYOUT` |
| T9 | footer ilegible (el v1 hacía `print`) | `FAIL_INTEGRITY` |
| T9b | sin min/max de `ts_utc_ns` | `FAIL_INTEGRITY` (`UNCERTIFIABLE`) |
| T10 | 12 GiB de input | `ABSTAIN_CAPACITY` |
| T11 | auxiliares `_all` / `prev` | listados con su regla, sin romper el PASS |
| T12 | nombre de archivo inválido | `FAIL_INTEGRITY` |

---

## 4. Lo que el código NO resuelve

1. **La v1 ya está subida y no la produjo un script versionado.** El builder v2
   impide repetirlo, pero no explica retroactivamente qué generó esos 57
   archivos. Su identidad sigue sin cerrar.
2. **Falta la herramienta de re-corte físico.** v2 detecta y excluye los parquets
   que contienen holdout (`RECUT_REQUIRED`); no los corta. Sin esa herramienta no
   existe `edgelab-cme-research-v2` (P-18).
3. **57 vs 56 archivos sin reconciliar.** El censo local declara 11 activos / 56
   contratos; Kaggle muestra 57 archivos. Un archivo de diferencia es exactamente
   el tipo de cosa que hay que explicar antes de confiar en un inventario.
4. **Costo de hashing.** sha256 sobre 16,74 GiB en la máquina local tarda. Existe
   `--no-hash`, y está prohibido para publicar: sin sha256 `G-IDENTITY` falla.
5. **El gate no es una decisión.** P-07 sigue siendo humana. Lo único que cambió
   es que ahora el proyecto no puede publicar por accidente mientras no exista.

---

## 5. Criterio de cierre (P-23)

1. Una corrida real del builder v2 sobre `E:/EdgeLab/data/nt8` desde la máquina
   local gobernada, con su `bundle_index.json` commiteado (cualquier veredicto:
   si es `ABSTAIN_*`, se registra tal cual).
2. Que el contenido que quede en Kaggle sea **exactamente** el staging que
   produjo el script, verificable con `sha256sum -c files.sha256`.

Hasta que (1) y (2) existan, el dataset de Kaggle es `raw_custody`: custodia de
datos crudos, no un dataset de investigación.
