# aVolClusterPOI — protocolo congelado de compresión y gatillo direccional V1

**Estado:** `FROZEN_METHOD`  
**Fecha:** 2026-08-27  
**Spec:** `specs/avolcluster_poi_compression_v1.json`  
**Runner:** `tools/run_avolcluster_measurement.py`  
**Base:** `foundation/f0b-compatibility-probe@8ebda7840bc3f0a7e39f3561db75a2c9090fd55f`

## 0. Veredicto epistemológico previo

El diseño, el detector y la selección de features son **target-free**. La ejecución formal **sí abre trayectorias futuras de precio** para medir rango, MFE, MAE y primer pasaje:

```text
DESIGN_TARGET_FREE=true
FUTURE_PRICE_PATH_ACCESSED=true
PNL_ACCESSED=false
HOLDOUT_TOUCHED=false
```

`Range_H`, MFE, MAE y primer pasaje son outcomes de trayectoria aunque no sean P&L. Las barreras geométricas no se interpretan como SL/TP.

## 1. Autoridad y objeto congelado

El repo contiene kernel Python v0.5 y contrato C# con cabecera/defaults v0.5; la referencia anterior a “C# v0.4” queda sustituida por el contenido versionado.

Detector inmutable:

- M1, bloques disjuntos de 10 barras desde inicio de sesión;
- tick hot si volumen `>=2×` mediana superior;
- cluster con gap máximo 1 tick y mínimo 2 ticks hot;
- un cluster de máxima masa por bloque;
- percentil empírico 98, sin interpolar, bucket session-relative de 30 minutos;
- 20 sesiones completas previas, FIFO por sesión, mínimo 20 muestras, sin fallback global;
- disponible al cierre de la creadora; primer toque desde B+1;
- `OFF_PRICE` es nivel; `AT_PRICE` es ocupación y queda fuera del primario;
- sin `QualityScore`, filtro predictivo, target, stop ni selección por outcome.

## 2. Universo y unidad

V1 queda fijado a **NQ**, cinco contratos, 234 sesiones esperadas y `session_id<=20260630`. El agente local debe vincular registro y parquets por SHA-256 en el manifest.

Cualquier `session_id>=20260701`, rango abierto, instrumento distinto, número de contratos distinto de cinco o identidad no registrable falla antes de calcular outcomes.

Unidad: **episodio de primer toque** `OFF_PRICE`.

1. una zona aporta como máximo un primer toque;
2. la creadora no puede tocar;
3. zonas del mismo contrato tocadas en la misma barra se colapsan;
4. representante: creación más antigua, mayor `zone_score`, menor `zone_id`;
5. dependencia agrupada por `contract×session_id`.

Se exige `N>=400` y al menos 40 clusters-sesión por hipótesis primaria. Si el compuesto H2 queda debajo, H1 puede informar y H2 abstiene.

**Corrección:** 400 eventos/40 sesiones no garantizan incondicionalmente 80% de potencia. El objetivo corresponde a MDE estandarizado 0.20 e ICC `<=0.05`. Dependencia o attrition adversas producen `ABSTAIN_POWER`.

## 3. Panel causal

El runner consume panel M1, una fila por `contract×session_id×bar_index_in_session`, con OHLC en ticks y features as-of al cierre. Primer toque: `is_zone_touch=1`.

- `pre_touch_vol_ticks`: mediana del true range de las 30 barras terminadas en `t-1`;
- VWAP/VAL/VAH: expanding/as-of, nunca finales de sesión;
- `delta_z`: estandarización causal con historia previa;
- direcciones BT2A/BT2: sólo tras match espacial con la zona y temporal en la barra del toque;
- índices únicos y contiguos en cada ventana forward;
- se rechazan columnas P&L, costos, target/stop o winner.

Modos:

1. `--preflight-only`: integridad/firewall sin outcomes.
2. ejecución formal: outcomes preregistrados, auditoría y manifest con hashes.

## 4. H1 — expansión no direccional

Para toque en `t`:

```text
Range_H = max(high_tick[t+1:t+H]) - min(low_tick[t+1:t+H])
Y_H     = log1p(Range_H / pre_touch_vol_ticks[t])
```

Se excluye la barra del toque. Ventana incompleta/no contigua dentro de la sesión: evento no elegible y contabilizado.

- Primario: H=30 M1.
- Secundarios: H={5,15,60}; Holm entre ellos; nunca rescatan H=30.

### N_RAND

Hasta 20 controles por evento:

- mismo contrato, sesión y bucket de 30 minutos;
- no son primeros toques;
- blackout de 60 barras de cualquier primer toque;
- preferencia `|log(vol_control/vol_zone)|<=log(1.25)`; fallback a vecinos de pre-vol del mismo estrato;
- mínimo cinco controles;
- seed `2026082701`;
- match rate mínimo 80%.

```text
D_i(H)=Y_zone,i(H)-mean_j(Y_NRAND,ij(H))
```

Estimand: media con igual peso por sesión de la media de `D_i(30)` dentro de cada `contract×session_id`.

Inferencia: Wild Cluster Bootstrap Rademacher, 9.999 réplicas, seed `2026082703`, IC95%, p unilateral.

- `H1_COMPRESSION_SUPPORTED`: gate N/sesiones/match, IC inferior >0 y p<=0.05.
- `H1_COMPRESSION_REFUTED`: IC superior <=0.
- resto: `H1_COMPRESSION_INCONCLUSIVE`.
- N insuficiente: `ABSTAIN_POWER_H1`.

Esto significa rango normalizado mayor que controles, no dirección, P&L ni ejecutabilidad.

## 5. H2 — gatillo contemporáneo

La dirección `OFF_PRICE` original se excluye de los votos.

### A. Absorción de delta

```text
eligible = abs(delta_z)>=2
           and penetration_ticks>=1
           and abs(displacement_ticks)<=1
vote = -sign(delta_z)
```

Compra agresiva absorbida vota short; venta agresiva absorbida vota long.

### B. Confluencia BigTrap

Cada `bt2a_direction`/`bt2_direction` en `{-1,+1}` aporta voto sólo si el builder impuso coincidencia espacial y temporal.

### C. Contexto as-of

- `close<VAL` y `<VWAP`: long.
- `close>VAH` y `>VWAP`: short.
- dentro de value/caso mixto: cero.

### Compuesto primario

Mínimo dos votos no nulos y unanimidad. Conflicto/empate: `ABSTAIN_EVENT`. Familias individuales: secundarias con Holm; no rescatan al compuesto.

### Excursión

Anchor: close de la barra del primer toque; trayectoria desde `t+1`; H=30.

```text
MFE = máxima excursión favorable
aMAE = máxima excursión adversa
d_hat_global = median(MFE)-median(MAE)
```

`d_hat_global` es descriptivo. Para inferencia con peso igual:

```text
d_s=median_s(MFE)-median_s(MAE)
theta_d=mean_s(d_s)
```

Ratio secundario: media geométrica por sesión de `(median MFE+0.5)/(median MAE+0.5)`.

### Primer pasaje

`b_i=max(1,ceil(pre_touch_vol_ticks_i))`. Score +1 predicha primero, −1 adversa, 0 ambas en misma barra o ninguna antes de H. Es barrera diagnóstica, no SL/TP.

### Nulls

- **Mirror:** invertir dirección sobre mismo evento/path; reportar observado, espejo y contraste.
- **Time-Shuffle:** shift circular no nulo de direcciones dentro de `contract×session_id`, 9.999 réplicas, seed `2026082702`; al menos 80% de sesiones permutables.

Decisión:

- `H2_DIRECTION_SUPPORTED`: N>=400, sesiones>=40, IC inferior de `theta_d`>0, IC inferior de primer pasaje>0, shuffle p<=0.05.
- `H2_DIRECTION_REFUTED`: ambos IC superiores <=0.
- resto: `H2_DIRECTION_INCONCLUSIVE`.
- población compuesta insuficiente: `ABSTAIN_POWER_H2`.

## 6. Tests obligatorios

1. rechazo de `session_id>=20260701`;
2. rechazo de columnas P&L/target/stop/winner;
3. features as-of y no look-ahead;
4. creadora no elegible;
5. episodios únicos;
6. forward dentro de sesión y contiguo;
7. blackout/match determinista;
8. signos de votos;
9. conflicto abstiene;
10. doble pasaje misma barra vale cero;
11. Mirror invierte;
12. shuffle reproducible;
13. WCB reproducible y `allow_nan=false`;
14. SHA-256 de spec, panel, resultados y manifest.

## 7. Salidas y lenguaje

- `avolcluster_measurement_result.json`
- `avolcluster_measurement_event_audit.csv`
- `avolcluster_measurement_manifest.json`

Máximo permitido: soporte/no soporte para expansión de rango normalizada y para asimetría de trayectoria condicionada. Prohibidos: edge, alfa demostrado, ticks netos, rentable, SL/TP óptimo y promoción.

## 8. Comandos previstos

```powershell
.venv\Scripts\python tools\run_avolcluster_measurement.py `
  --spec specs\avolcluster_poi_compression_v1.json `
  --panel E:\DatosNT8\avolcluster_nq_measurement_panel_v1.parquet `
  --output-dir E:\DatosNT8\avolcluster_nq_measurement_v1 `
  --preflight-only
```

Sólo tras `READY` y autorización explícita para abrir outcomes de trayectoria:

```powershell
.venv\Scripts\python tools\run_avolcluster_measurement.py `
  --spec specs\avolcluster_poi_compression_v1.json `
  --panel E:\DatosNT8\avolcluster_nq_measurement_panel_v1.parquet `
  --output-dir E:\DatosNT8\avolcluster_nq_measurement_v1
```

## Aporte al referente

El protocolo separa detector target-free de outcomes de trayectoria, fija un primario con controles e inferencia clusterizada y vuelve refutable la hipótesis de microestructura sin abrir holdout ni optimizar SL/TP.
