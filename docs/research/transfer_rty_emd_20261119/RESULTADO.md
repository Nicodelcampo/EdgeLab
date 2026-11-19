# TRANSFER-RTY-EMD: Z y la compresión de VIX tienen el mismo signo en Russell y MidCap, pero sin significancia en DESC (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (1 prueba en `FUNDEDSYNC`, 1 en `CARRIL2_A5`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `Z.json`, `Z_OPS.csv.gz`, `VZ.json`, `VZ_OPS.csv.gz`. Sólo meses DESC
de A5 (VZ: entrada y salida en DESC); **REP de RTY y EMD sigue sellado** para estas reglas.

| Regla | Ventana | n | R neto | ee | p | MDE 80 % | Bruto | Control / otra época | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| Z (fábrica, stop 0,25 × ATR20) | 2018-01 → 2025-07 | 97 (RTY 87, EMD 10) | **+0,146** | 0,106 | 0,085 | 0,26 | +0,197 | antes de 2018: −0,049 (n 29) | SIN_TRANSFERENCIA (no significativa) |
| VZ (compresión VIX/RVX + VIX9D) | 2011 → 2025-07 | 348 (EMD 230, RTY 118) | +0,035 | 0,043 | 0,21 | 0,11 | +0,049 | control VZN −0,066; desde 2018 +0,054 | SIN_TRANSFERENCIA |

- **Z repite el patrón de NQ** (negativa antes de 2018, positiva después, bruto +0,20 R) en un índice donde nunca se midió, pero con 97
  operaciones no alcanza (p 0,085). **Limitación de datos, no de código:** el M1 de RTY empieza en 2017-07 y el de EMD tiene menos de la
  mitad de los minutos (≈ 150 mil velas por año contra ≈ 340 mil de RTY): Z exige sesiones completas y en EMD casi no dispara (68
  operaciones en 20 años). La prueba es, en la práctica, sólo RTY.
- **VZ** mantiene el signo y su control negativo, pero el efecto es menor que en ES/NQ (+0,035 contra +0,089).
- **Lectura:** ninguna queda refutada (MDE 0,26 y 0,11 R); las dos suman evidencia direccional coherente. La confirmación queda en REP de
  RTY (sellado) y en el forward, con la potencia que da cada uno (K49): hoy ninguna de las dos la alcanza.
