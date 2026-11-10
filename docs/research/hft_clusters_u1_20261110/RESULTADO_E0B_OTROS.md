# HFT-RUPTURA-OTROS — E0-b sin retornos en RTY, 6E, 6B y MBT

Estado: RESULTADO (2026-11-10). Pre-registro: `PREREGISTRO_RUPTURA_OTROS.md` §3. Datos: `HFTC_e0b_otros.json` / `.csv` (DESC jul-2025 →
mar-2026, 40 definiciones de cluster por activo, sin retornos). Regla mecánica: `hft_clusters_info.elegir_equilibrio` (CV mensual ≤ 0,5
y mínimo `2,49/√N + fricción / ancho`).

| Activo | Definición elegida | Eventos | Por sesión | Ancho mediano | CV mensual | Fricción / ancho | Borde detectable |
|---|---|---|---|---|---|---|---|
| RTY | K12_A050_V1800 | 625 | 5,1 | 5,8 pts | 0,20 | 0,076 | 0,176 |
| 6E | K16_A025_V1800 | 1.082 | 6,6 | 0,00125 | 0,36 | 0,166 | 0,242 |
| 6B | K12_A025_V1800 | 416 | 2,5 | 0,0020 | 0,34 | 0,194 | 0,316 |
| MBT | — (ninguna con CV ≤ 0,5: la mejor, 0,58) | — | — | — | — | — | — |

Con YM (K4_A025_V1800 del E0-b original, 275 eventos) la tabla del generador cubre cuatro activos. MBT queda afuera por la regla.
La fricción frente al ancho es alta en 6E y 6B (0,17–0,19): la carrera usa X = fricción / 0,08 igual, así que la medición de
información es válida, pero cualquier P&L futuro en esos activos necesita stop ≥ X.
