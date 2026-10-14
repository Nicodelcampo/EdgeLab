# R2 — Recorrido bruto vs fricción: resultados (PROVISIONAL)

Estado: PROVISIONAL (descriptivo, target-free; release v4 aprobada, `purpose=provisional_research`)
Fecha: 2026-10-14
Familia / módulo: research · roadmap R2
Manifiesto: `docs/research/R2_RECORRIDO_VS_FRICCION_MANIFIESTO_20261014.md` (congelado antes de medir)
Procedencia: `tools/r2_recorrido_vs_friccion.py`, release manifiesto `db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5`, 14 activos, sesión regular 08:30–15:00 CT, sin holdout. Tablas completas: `docs/research/r2_recorrido_vs_friccion_20261014/R2_<ACTIVO>.json` (cuantiles por horizonte y por hora de inicio CT).

## Qué se midió
Para cada activo, ventanas de 1/5/15/30/60 min que empiezan en cada minuto de la sesión regular: rango `R` (máx − mín) y desplazamiento neto `D = |fin − inicio|`, en ticks. Fricción `F` = spread medio RTH medido + comisión round-trip + 2 ticks de slippage declarado (extremo alto del rango de comisiones de `REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md`). **El N efectivo es el de sesiones (≈ 200–294 por activo), no el de ventanas, que se superponen.**

## Resultado principal
La fricción **no** es el obstáculo geométrico en índices y metales: el recorrido es muy superior a `F` en todo horizonte ≥ 5 min. Lo que falta no es tamaño del movimiento sino **predecir su dirección**. Acierto mínimo = `0,5 + F / (2·mediana|D|)`, el acierto direccional que haría falta apostando al movimiento neto del horizonte (aritmética de payoff, **no** evidencia de que exista ese acierto):

| Activo | F (ticks, alta) | 5 min: mediana \|D\| / acierto mín. | 15 min | 30 min | 60 min |
|---|---:|---|---|---|---|
| ES | 3.55 | 9 / 70 % | 16 / 61 % | 22 / 58 % | 32 / 56 % |
| MES | 4.62 | 9 / 76 % | 16 / 64 % | 22 / 60 % | 32 / 57 % |
| NQ | 6.18 | 49 / 56 % | 83 / 54 % | 116 / 53 % | 167 / 52 % |
| MNQ | 7.91 | 48 / 58 % | 81 / 55 % | 113 / 53 % | 162 / 52 % |
| GC | 6.05 | 19 / 66 % | 33 / 59 % | 46 / 57 % | 64 / 55 % |
| MGC | 6.92 | 22 / 66 % | 38 / 59 % | 53 / 57 % | 75 / 55 % |
| YM | 5.05 | 17 / 65 % | 29 / 59 % | 41 / 56 % | 59 / 54 % |
| MYM | 7.49 | 18 / 71 % | 31 / 62 % | 43 / 59 % | 61 / 56 % |
| RTY | 4.44 | 15 / 65 % | 25 / 59 % | 35 / 56 % | 49 / 55 % |
| 6E | 4.16 | 3 / >100 % | 5 / 92 % | 7 / 80 % | 10 / 71 % |
| 6B | 3.88 | 2 / >100 % | 3 / >100 % | 5 / 89 % | 7 / 78 % |
| 6J | 3.90 | 2 / >100 % | 3 / >100 % | 4 / 99 % | 6 / 82 % |
| MBT | 11.69 | 16 / 87 % | 27 / 72 % | 38 / 65 % | 53 / 61 % |
| ZB | 3.10 | 1 / >100 % | 1 / >100 % | 2 / >100 % | 2 / >100 % |

(Cada celda: mediana de `|D|` en ticks / acierto mínimo para cubrir `F`.)

## Lectura (con límites)
- **NQ/MNQ, YM, RTY, ES/MES, GC/MGC:** a 15–60 min bastan aciertos de ~52–62 % para cubrir la fricción. **NQ es el más favorable en proporción** (fricción ≈ 7 % de la mediana de `|D|` a 15 min; ES ≈ 22 %), aunque su fricción en ticks sea mayor: el movimiento en ticks es mucho mayor.
- **A 1–5 min** el acierto necesario sube a 70 % o más en ES/MES/GC: el microscalping sigue sin pagar, coherente con el MFE mediano de 3 ticks medido en AVZP2.
- **FX (6E/6B/6J) y ZB:** a ≤ 30 min el movimiento mediano es menor que la fricción (acierto > 80–100 %). Cerrados para intradía corto con esta fricción; sólo 60 min en 6E llega a 71 %.
- **MBT:** fricción alta (≈ 11,7 ticks con comisión de las tablas de Topstep y MFFU); requiere ≥ 60 % a 60 min.
- Esto es un **techo**, no un resultado: un sistema real con stops y salidas captura menos de `|D|`, y el acierto de 52–60 % sostenido y neto es justamente lo que ninguna medición previa del repo ha encontrado.

## Qué cierra y qué abre
- **Cierra** (con alcance preciso): scalping ≤ 5 min en ES/MES/MNQ y todo intradía ≤ 30 min en FX y ZB con esta estructura de costos.
- **Abre** (sin promover nada): el espacio de campañas de **dirección a 15–60 min en índices (NQ primero) y metales**, que requiere manifiesto, N efectivo de hipótesis y OK de Nico antes de usar retornos.

## Salvedades
Precios de trade con rebote bid/ask inflan `R` a 1 min. Comisión tomada de las tablas oficiales de Topstep/Lucid/MFFU para todos los activos salvo ZB (sólo Topstep, 2,76 USD RT) y MBT (Topstep y MFFU, sin Lucid). Un solo régimen de volatilidad (2025-08 a 2026-09). Spread medido sólo en sesión regular.
