# Franklin en años limpios, y SOM y R en índices no mirados (resultado, 2026-11-18)

Estado: RESULTADO — pre-registros `PREREGISTRO_FRANKLIN.md` y `PREREGISTRO_INDICES.md`. North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `RESULTADO_FRANKLIN.json`, `RESULTADO_INDICES.json`,
`FRANKLIN_OPS_*.csv.gz`, `SOM_OPS_{EMD,RTY}.csv.gz`, `FS_OPS_{EMD,RTY}.csv.gz`.

## 1. Franklin (NQ + ES, futuros): A_FAVOR en bruto en los años limpios
| Período | Bruto R/op [IC90] | Neto R/op [IC90] | Fricción R |
|---|---|---|---|
| **2006–2011 (prueba)** | **+0,195 [+0,095, +0,296]**, 991 ops, 83 % de años + | +0,020 [−0,080, +0,121] | 0,175 |
| 2012–2019 | +0,063 [−0,005, +0,130] | −0,067 | 0,129 |
| 2020–2025 | +0,125 [+0,038, +0,210] | +0,082 [−0,004, +0,168] | 0,042 |

La señal bruta está en los tres períodos; el neto dependió de la fricción, que bajó de 0,175 a 0,042 R. El patrón es el mismo de SOM y la
misma lección: es una señal estable y hoy es rentable neta porque la fricción relativa es baja.

## 2. SOM en el MidCap (EMD) y el Russell (RTY): A_FAVOR en bruto (la señal transfiere)
- **Prueba (bruto, ventanas limpias):** +0,030 R por operación, IC90 [+0,006, +0,055], 4.801 operaciones, 70 % de años positivos.
- **Por índice y período:**
  - EMD: +0,009 / +0,047 / +0,028;
  - RTY: +0,062 (2017–2019) / −0,009 (2020–2025).
- **Neto ≈ 0** en estos índices (EMD con costo estimado): la señal es la mitad que en NQ y la fricción en R es mayor.
- **Lectura:** el impulso de la apertura de NY es un mecanismo común a los índices de EE. UU., no una casualidad del Nasdaq. Neto, hoy
  sólo es rentable donde la fricción relativa es más baja (NQ).

## 3. R AtrPhase en EMD + RTY: NO_CONCLUYENTE (no transfiere con fuerza)
- **Resultado:** bruto +0,011 ATR, IC90 [−0,018, +0,040], 55 % de años positivos, 1.090 operaciones.
- **Potencia 0,93** para la mitad del efecto de referencia: el efecto fuera del Nasdaq, si existe, es menor que esa mitad.
- **Contexto:** junto con el decaimiento en ES y YM después de 2011, R parece una propiedad del NQ.
- **Para la canasta:** sigue en SEÑAL_ESTABLE sólo en NQ y con su stop de catástrofe, con menos peso que SOM.

## 4. Qué cambia en el veredicto (`docs/research/VEREDICTO_M1_20261117.md`)
- **Franklin:** pasa de «sin medir» a **señal bruta estable confirmada en años limpios**. Se suma a SOM como candidata con mejor base.
- **SOM:** la confirmación en índices no mirados refuerza que el mecanismo es real; se opera donde la fricción en R es baja.
- **R:** queda como pista sólo NQ.
