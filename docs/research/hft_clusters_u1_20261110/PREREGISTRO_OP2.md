# OP-2 — continuación en el primer regreso a un cluster HFT grande (desarrollo)

Estado: PRE-REGISTRO (2026-11-11, antes de generar la tabla). Familia `HFT_RUPTURA` (OP-2 es la traducción operable de
`F-HFT-CLUSTER-GRANDE-NO-DEFIENDE-C`; hereda su multiplicidad). Etapa: EF3 (desarrollo con P&L; la confirmación sería el holdout).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Expectativa declarada ANTES (consulta sobre tablas ya miradas)
«No defiende» es real − control: el efecto sale casi entero de que el control REBOTA (−0,06…−0,08), no de que el cluster empuje.
Ruptura absoluta del cluster (carrera ±X): NQ +0,010 (DESC) / −0,002 (réplica); ES +0,026 / +0,050; RTY −0,012 / −0,166;
**YM +0,133 / +0,143**. Con fricción 0,08 R se espera R neto ≈ −0,08 en el conjunto; YM es la única candidata.

## Regla (congelada)
Evento D0 sobre los clusters del E0-b (NQ K8_A050, ES K12_A100, RTY K12_A050, YM K4_A025), real y control. Entrada a mercado en el
tick del toque, a favor de la llegada; stop X; objetivos X/2, X (primaria) y 2X; salida a 900 s; empate stop. R neto = bruto − fricción / X.
Código: `edgelab/research/op2_clusters.py`, `fill_pasivo.operar_mercado`. Datos: DESC jul-2025 → mar-2026 + réplica abr → sep 2026
(ambas ya miradas para esta línea: esto es DESARROLLO, no confirma nada). Análisis congelado: `tools/op2_clusters.py`.

## Pruebas
- Primaria: NQ + ES + RTY + YM, objetivo X, R neto medio por sesión, estabilidad en 5 sub-bloques, p por inversión de signo.
- Secundaria: YM sola, objetivo X (la candidata declarada arriba).
- Descriptivas: por activo × período × geometría, y real − control con la misma operación.
Contadas: 2 + 24 descriptivas = 26 (`hft_ruptura/op2_desarrollo`).

## Decisión
Pasa a la canasta del holdout (modo exploratorio, una apertura de la familia) sólo si la primaria o YM dan R neto > 0 con ≥ 4/5 bloques
y p < 0,10 **en los dos períodos por separado**. Si no: OP-2 NO_REPETIR con esta geometría, y la cuerda queda como veto/diagnóstico.

## Cómo podría refutarse
R neto ≤ 0 en la primaria y en YM, o positivo en un solo período.
