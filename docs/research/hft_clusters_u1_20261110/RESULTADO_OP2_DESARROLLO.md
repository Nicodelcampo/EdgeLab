# OP-2 — continuación a mercado en el primer regreso a un cluster HFT grande: resultado (desarrollo)

Estado: RESULTADO (2026-11-11). Pre-registro: `PREREGISTRO_OP2.md` (con la expectativa escrita ANTES). Análisis congelado:
`tools/op2_clusters.py` (corrido una vez). Tabla: `HFTC_op2.csv` (DESC + réplica, NQ/ES/RTY/YM, 5.927 operaciones reales).
Cifras: `RESULTADO_OP2_DESARROLLO.json`.

## Primaria (4 activos, objetivo X): **R neto −0,079** (bruto 0,000), 0/5 bloques en los dos períodos — se cumplió la expectativa
| Período | n | R bruto | R neto | Bloques + | Real − control (mismo R) |
|---|---|---|---|---|---|
| DESC | 3.682 | +0,010 | −0,069 | 0/5 | +0,118 (4/5) |
| Réplica | 2.245 | −0,016 | −0,095 | 0/5 | +0,060 |

## YM (secundaria declarada): neto positivo en los dos períodos, pero sin significancia → NO pasa al holdout por la regla
| Período | n | R bruto | R neto | Bloques + | p |
|---|---|---|---|---|---|
| DESC | 150 | +0,114 | +0,035 | 3/5 | 0,29 |
| Réplica | 112 | +0,104 | +0,025 | 3/5 | 0,38 |
Con objetivo 2X (descriptivo): DESC +0,125 neto (4/5, p 0,06), réplica −0,017. No se elige geometría mirando esto.

## Lectura
1. Se confirma lo que la consulta previa anticipó: «no defiende» (real − control +0,09, también en R operable) es una diferencia
   contra un nivel que rebota, no un empuje del cluster. Operar la continuación en NQ/ES/RTY paga ≈ 0 en bruto y pierde la fricción.
   OP-2 queda **NO_REPETIR** con esta geometría en esos activos.
2. YM es la única con bruto ≈ +0,11 estable en los dos períodos (262 operaciones): pista chica, sin potencia (MDE ≈ 0,2). Se sigue
   sólo como hipótesis previa en datos nuevos (holdout/forward), junto con las condiciones C1 (stops del otro lado) y C2 (veto de huida)
   de `OP2_CONDICIONES_CANDIDATAS.md`.
3. La cuerda «las zonas HFT no son soporte» sigue en pie como hecho de mercado; su uso operable más probable es como VETO
   (OP-3: no hacer fades cerca de actividad HFT reciente), no como señal de entrada.
