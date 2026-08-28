# aVolClusterPOI — censo estructural NT8 (2026-08-13)

Objetivo: exportar lo que el detector **marca**, no si acierta.
No mirar target/stop, QualityScore ni el % del dashboard.

## Chart

- Instrumento: **6E** (front o continuo; anotá cuál).
- Primary: **1 minuto**. El indicador agrega solo la subserie tick:1.
- Cargar **≥ 20 sesiones de warmup** + las de estudio.
- Si podés llegar al universo F2.7: hasta **2026-06-30**, más ~20 sesiones antes.
- Recalculate **una vez**. El CSV **sobreescribe**.

## Parámetros (v0.4, modo censo)

Grupo 1 Deteccion — dejar:
- Window Bars = 10
- Median Multiplier = 2
- Max Gap Ticks = 1
- Min Cluster Ticks = 2

Grupo 2 Perfil horario — **cambiar**:
- Session Relative Buckets = true
- Time Bucket = 30
- Lookback Sessions = 20
- Detection Percentile = **98**
- Min Samples Per Bucket = **20**

Grupo 3 Ranking — **no filtra**:
- Enable Predictive Filter = **false**
- Min Quality Score = 0
- el resto no importa

Grupo 4 Ciclo de vida — default:
- Invalidation = CloseThrough
- Max Age = 2000
- Max Touches = 0

Grupo 6 Export:
- Event Log Path = `C:\EdgeLab\avolcluster_census_YYYYMMDD.csv`
- Show Outcome Labels = **false**
- Show Dashboard = true (ignorá “aciertos”)

## Qué mandar

1. El CSV (incluye la línea `# meta`).
2. Contrato / instrumento exacto.
3. Rango de fechas cargado.
4. Si el chart es 1 minuto sí o no.

No hace falta captura. Si mandás captura, no la usamos para decidir.
