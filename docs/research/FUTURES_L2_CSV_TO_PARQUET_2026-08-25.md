# Conversión L2 CSV → Parquet para contextos de futuros

- **Fecha:** 2026-08-25
- **Rama:** `work/futures-l2-context-foundation-20260825`
- **Base:** `foundation/f0b-compatibility-probe@7e8526e`
- **Herramienta:** `tools/convert_l2_to_parquet.py` v2.0.0
- **Alcance:** conversión de formato target-free; no calcula outcomes, retornos, P&L, MAE/MFE ni selecciona contextos.

## Por qué se reemplazó el wrapper anterior

El wrapper existente tenía dos riesgos para este uso:

1. cargaba cada CSV completo en memoria;
2. tenía `tick_size=0.00005` como default histórico de 6E, peligroso para GC.

La versión 2 procesa por chunks y exige declarar instrumento y tick size. No ordena,
no deduplica y no agrega eventos.

## Contrato CSV esperado

```text
L2;side;YYYYmmddHHMMSS;microsecond;operation;level;;price;size
L1;side;YYYYmmddHHMMSS;microsecond;price;size
```

Códigos:

- L2 `side`: `0=ASK`, `1=BID`.
- L2 `operation`: `0=ADD`, `1=UPDATE`, `2=REMOVE`.
- L1 `side`: `0=ASK`, `1=BID`, `2=LAST`, `5=DAILY_VOLUME`.

`source_row` es la línea 0-based del CSV original mezclado. Es la clave que preserva el
orden relativo entre L1 y L2 cuando muchos eventos comparten microsegundo.

## Instrucciones para Claude

Trabajar en otro worktree; no cambiar el HEAD ni el árbol que sostienen el sweep.
Detectar primero el nombre real del remoto (`github` u `origin`).

```powershell
git fetch --all --prune
git worktree add ..\EdgeLab-l2 <remote>/work/futures-l2-context-foundation-20260825
cd ..\EdgeLab-l2
git rev-parse HEAD
git status --short --untracked-files=all
```

El entorno canónico usa Python 3.12 y el lockfile del repo:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements\core-bridge-dev.lock
.venv\Scripts\python -m pytest tests\data\test_l2_source_row.py tests\data\test_convert_l2_to_parquet.py -q
```

### Piloto GC 08-26 · 2026-06-09

Para un CSV individual:

```powershell
.venv\Scripts\python tools\convert_l2_to_parquet.py `
  --input "E:\EdgeLab\data\l2_raw\GC 08-26\GC_08-26_20260609.csv" `
  --output-dir "E:\EdgeLab\data\l2_parquet\GC 08-26" `
  --instrument "GC 08-26" `
  --tick-size 0.1
```

Para todos los CSV de un directorio:

```powershell
.venv\Scripts\python tools\convert_l2_to_parquet.py `
  --input-dir "E:\EdgeLab\data\l2_raw\GC 08-26" `
  --output-dir "E:\EdgeLab\data\l2_parquet\GC 08-26" `
  --instrument "GC 08-26" `
  --tick-size 0.1 `
  --pattern "*.csv"
```

No usar `--overwrite`, `--allow-off-grid`, `--allow-time-inversions` ni `--allow-dirty`
en la primera corrida. Son overrides diagnósticos y quedan declarados en el manifiesto.

## Outputs por sesión

```text
<output-dir>/
  l2_depth/<session>.parquet
  l1_quotes/<session>.parquet
  manifests/<session>.manifest.json
```

El manifiesto se publica último y funciona como marcador de conversión completa. Incluye:

- SHA-256 y bytes del CSV;
- SHA-256, bytes y filas de ambos parquets;
- `head_start`, `head_end` y estado dirty;
- tick size e instrumento;
- cobertura exacta `L1 + L2 = raw`;
- primer/último timestamp y eventuales inversiones;
- precios fuera de grilla y overrides;
- versiones de Python, pandas y PyArrow.

La escritura usa temporales y `os.replace`. Una falla no publica el manifiesto ni deja
parquets `.part` de esa ejecución.

## Guardrails

- No procesar las sesiones selladas de GC 08-26: `20260608`, `20260618`, `20260630`.
- El reloj NT8 se conserva como wall-clock interpretado en microsegundos; su referencia
  absoluta contra `.Last.txt` sigue **no resuelta**. No unir por cercanía temporal.
- No inspeccionar ni derivar ventanas posteriores a señales.
- Los parquets son datos locales; no se commitean. Sólo código, manifests seleccionados
  y reportes de integridad pueden entrar al repo.
- La presencia de precios en el raw no autoriza outcomes.

## STOP de la corrida

Detenerse y entregar el error exacto si ocurre cualquiera:

- `record_type` desconocido;
- timestamp inválido o inversión temporal;
- precio fuera de tick;
- falta completa de L1 o L2;
- diferencia entre filas CSV y `L1 + L2`;
- cambio de HEAD o árbol dirty;
- hash/row count de Parquet distinto del manifiesto.

No corregirlo ampliando tolerancias ni reordenando filas.

## Aporte al referente

La conversión L2 deja de depender de cargar sesiones completas en RAM o de un tick size
heredado de otro instrumento. Cada Parquet conserva el orden mixto del CSV y queda ligado
a su raw, código y entorno mediante un manifiesto reproducible antes de construir
cualquier contexto causal.
