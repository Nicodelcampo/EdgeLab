# BigTrap2Absorption — corrida target-free nocturna

**Estado:** `FROZEN_TARGET_FREE_NOT_RUN`  
**Commit de implementación:** `dc99def521d37d26899baae07077ba7fd2a8e5d9`  
**Outcomes:** `NOT_OPENED`  
**Bloque sellado:** outcomes `NOT_OPENED`

## Qué se congela

La campaña deja de tratar un único headline como veredicto sobre toda la familia.
Cubre los 21 parámetros declarados por `DEFAULTS/PARAM_SPEC`:

- 51 configuraciones únicas: headline + OAT completo;
- 48 configuraciones de screening mixto para interacciones;
- total determinista: **99 configuraciones**;
- ningún retorno, MFE, MAE, P&L, hit-rate ni `d_hat`.

`MinExportVolume` y `DrawZoneBand` se auditan explícitamente como posibles no-op.
El solapamiento se usa para describir redundancia; **no** se convierte en un
“número efectivo de tests”. La multiplicidad de outcomes se resolverá después
sobre una familia congelada mediante resampling que preserve la dependencia.

## Universo y las 19 selladas

El kernel procesa cronológicamente las 152 sesiones target-free porque `abs_ring`
cruza fronteras de sesión. Quitar las 19 alteraría `a_thr` de sesiones posteriores.
Sin embargo:

- sólo las 133 de Puerta 1 aportan métricas, fingerprints y solapamientos;
- las 19 no participan en selección ni resumen;
- no se calcula ningún outcome sobre ninguna de las 152.

## Fail-closed incorporado

- Prohíbe `td` crudo y deriva `cme_session` desde timestamp.
- Verifica exactamente 152/133/19.
- Exige cobertura de cinta para cada sesión esperada de la cadena.
- Aborta en árbol dirty, archivo ausente o sesión faltante.
- Registra SHA-256 de cada cinta, commit inicial/final y estado del worktree.
- Escribe parciales atómicos y reanuda sólo si input, config y commit coinciden.
- Si llega a 8,5 horas, sale `PAUSED_BY_MAX_HOURS` sin perder parciales.

## Comandos nocturnos

Desde el clon correcto de EdgeLab:

```powershell
python tools/estado.py
git status --short
python -m pytest tests/bridge/test_bt2_absorption_param_sweep.py -q

$OUT = "C:\Users\nicoc\OneDrive\Documentos\DataNT8\bt2a_sweep_20260824"
python tools/bt2_absorption_param_sweep.py plan --stage all --output $OUT
python tools/bt2_absorption_param_sweep.py run `
  --stage all `
  --resume `
  --max-hours 8.5 `
  --data-dir "C:\Users\nicoc\OneDrive\Documentos\DataNT8" `
  --output $OUT
```

Resultado completo esperado:

```text
summary.json
exact_overlap_matrix.json
session_metrics.jsonl
input_manifest.json
expanded_grid.json
universe.json
run_status.json
partials/
```

Si termina por tiempo, se repite exactamente el mismo comando con `--resume`.
No cambiar código, spec, input ni rama entre corridas.

## Interpretación autorizada

Sí puede decirse:

- “este parámetro no activa ningún cambio”;
- “estas configuraciones generan poblaciones equivalentes”;
- “este eje cambia score, geometría, lifecycle o concentración”.

No puede decirse:

- “esta configuración gana”;
- “el indicador tiene/no tiene edge”;
- “95 % de eventos compartidos equivale a N tests efectivos”;
- “el headline plano refuta toda la familia”.

Puerta 1 y cualquier barrido de outcomes siguen bloqueados hasta revisar el
landscape, congelar la familia outcome-level y recibir el `dale` explícito.

## Aporte al referente

La corrida reduce el riesgo de matar o promover toda una familia por un solo
punto paramétrico, sin gastar outcomes ni tocar el bloque sellado. También deja
trazabilidad suficiente para que una selección posterior pague toda su
multiplicidad real.
