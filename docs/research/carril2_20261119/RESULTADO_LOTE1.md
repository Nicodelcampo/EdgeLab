# CARRIL2-LOTE1: IBS+VIX, Double Seven, Turnaround Tuesday y cambio de mes — ninguna pasa DESC; nulos sin potencia para efectos < 0,14 R (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO_LOTE1.md` (8 pruebas en `CARRIL2_A5`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `OPS.csv.gz`, `DESC.json`. Motor `sqx_catalogo.simular` (K28) con
camino M1; operaciones con salida en HOLDOUT/EMBARGO descartadas (verificado en la herramienta). REP no se leyó (sin nominadas).

| Regla (ES+NQ+YM+RTY; D7 también GC) | n DESC | R neto | ee | p | R bruto | fricción R (mediana) | ops/mes | Contraste con control (p) |
|---|---|---|---|---|---|---|---|---|
| IBS + VIX | 542 | +0,017 | 0,057 | 0,38 | +0,034 | 0,015 | 6,9 | +0,066 (0,17) |
| Double Seven | 612 | +0,079 | 0,047 | 0,047 | +0,096 | 0,017 | 5,2 | +0,045 (0,29) |
| Turnaround Tuesday | 650 | +0,059 | 0,051 | 0,13 | +0,077 | 0,017 | 5,0 | +0,057 (0,20) |
| Cambio de mes (T−5 → 8 barras) | 353 | +0,034 | 0,076 | 0,33 | +0,048 | 0,012 | 3,3 | −0,074 (0,75; el control rinde más) |

- **Ninguna pasa BH q 0,10** (8 pruebas). La fricción en R es mínima (≈ 0,015): el límite no es el costo sino el ruido de pocas operaciones
  con resultados grandes en R.
- **MDE (regla de EdgeLab: todo nulo publica su potencia):** con ee ≈ 0,05–0,08 R, el efecto mínimo detectable al 80 % (α 0,05) es ≈ 0,14–0,21 R
  por operación. No se puede descartar un efecto real de +0,05–0,10 R: el veredicto es **SIN_EVIDENCIA**, no refutación.
- Double Seven repite la dirección de F-CONNORS-INDICES-SQX (+0,079 R) pero no supera la multiplicidad; el cambio de mes rinde menos que su control.
- **Siguiente (si se quiere insistir):** sólo con más N por mecanismo (canasta de las cuatro como una sola señal de «reversión de corto plazo
  en índices» pre-registrada, o más instrumentos), nunca eligiendo la mejor de estas cuatro.
