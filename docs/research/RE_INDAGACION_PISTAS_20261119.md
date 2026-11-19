# Re-indagación de Z y de las pistas SIN_EVIDENCIA: qué se apaga, qué sube y qué se puede confirmar (2026-11-19)

Estado: VIGENTE — análisis descriptivo sobre operaciones ya medidas en DESC (no abre REP, holdout ni datos nuevos; no cuenta pruebas).
Pedido de Nico: «indagá también en Z … cuando llegás a pistas sin evidencia como en el caso del VIX y muchos otros, indagá nuevamente».
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Datos: `neto_pistas_20261119/RZ_OPS.csv.gz` (Z), `carril2_20261119/OPS*.csv.gz`, `mejora_sf_20261119/TABLA.csv.gz`, `flujos_macro_20261119/
OPS_DESC_REP.csv.gz` (FM7/FM7N). Potencia: n necesario para 0,8 con la mitad del efecto 2018–2025 y α 0,01 (≈ nivel LORD++ de las familias).

## 1. Z (ZetaTrend, FundedSync), con stop 0,25 × ATR20, en R neto
- **Por época (todas las variantes de la grilla):** NQ 2008–2017 −0,095 R (bruto +0,043), 2018–2026 +0,135 (bruto +0,165); ES −0,131 → +0,010.
  El bruto es positivo en las dos épocas: lo que cambió es la fricción relativa (mismo patrón que T, SOM y Franklin).
- **Meseta:** en NQ 2018+ 23/27 variantes positivas (mediana +0,146), en ES 18/27 (mediana +0,05). Las perillas rápidas (cubeta 10 min, EMA 10)
  rinden más en las dos épocas y en los dos instrumentos; el umbral de eficiencia casi no importa.
- **Pero:** en el tramo comparable 2018 → jul-2025, la grilla promedia +0,073 R por sesión en NQ y −0,05 en ES, mientras la fábrica en NQ da
  +0,30. La fábrica es un pico; el corte en 2018 se eligió mirando. Veredicto sin cambios: **INTERMEDIO**, más fuerte de lo que decía el número
  de toda la ventana, pero sin confirmación posible.
- **Datos limpios:** Z nunca se midió en RTY ni EMD (YM sí, 2012–19). Con la mitad del efecto la potencia en RTY+EMD 2018–2025 sería ≈ 0,17 (α 0,05)
  y ≈ 0,05 al nivel LORD: no se abre (K49). Si alguna vez se quiere sumar Z a la canasta forward, debería ser la variante rápida central
  (cubeta 10, EMA 10), declarada antes, y como versión nueva con su pre-registro: hoy no se agrega.

## 2. Pistas SIN_EVIDENCIA: efecto por época (R neto por operación, meses DESC)
| Pista | n DESC | Total | 2006–11 | 2012–17 | **2018–25** | Tendencia | Ops/mes | n para potencia 0,8 | Meses de forward | ¿Lucid? |
|---|---|---|---|---|---|---|---|---|---|---|
| IBS + VIX | 542 | +0,017 | +0,066 | +0,135 | **−0,098** | se apaga | 4,1 | — | — | no (varios días) |
| Double Seven | 612 | +0,079 | +0,171 | +0,130 | **+0,001** | se apaga | 4,9 | — | — | no |
| Turnaround Tuesday | 650 | +0,059 | +0,137 | +0,092 | **−0,019** | se apaga | 4,6 | — | — | no |
| Cambio de mes | 353 | +0,034 | +0,070 | +0,059 | **−0,001** | se apaga | 2,5 | — | — | no |
| Pico de VIX (BB 2σ) | 360 | +0,136 | +0,208 | +0,306 | **−0,022** | se apaga | 2,6 | — | — | no |
| VIX > P80 | 309 | −0,094 | −0,114 | +0,062 | −0,149 | negativa | 2,5 | — | — | no |
| eVRP + contango | 323 | +0,066 | −0,011 | +0,042 | **+0,098** | sube | 3,1 | ≈ 3.000 | ≈ 560 | no |
| Compresión VIX+VIX9D | 459 | +0,089 | −0,010 | +0,051 | **+0,134** | sube | 4,4 | ≈ 1.100 | ≈ 145 | no |
| Rotación ES/GC | 68 | +0,080 | +0,646 | −0,069 | +0,006 | se apaga | 0,6 | — | — | no |
| Franklin, días de ATR alto | 691 | +0,103 | +0,162 | +0,001 | +0,135 | estable | 4,4 | ≈ 5.500 | ≈ 620 | sí |
| Franklin, días de VIX alto | 627 | +0,152 | +0,215 | +0,156 | +0,110 | estable | 4,0 | ≈ 8.700 | ≈ 1.130 | sí |
| SOM con fricción ≤ 0,08 R | 5.660 | +0,013 | +0,057 | −0,038 | +0,019 | ≈ 0 | 36 | ≈ 97.000 | ≈ 1.400 | sí |

(«—»: efecto 2018–2025 ≤ 0, no hay nada que confirmar en el régimen actual.)

## 3. Mecanismo de las dos pistas de volatilidad
- **El pico de VIX se apagó:** parejo entre ES, NQ e YM, pero +0,21 / +0,31 / −0,02 por época. Comprar el pico de miedo se volvió una operación
  concurrida (desde 2018 la cubren fondos de vol-control y CTA rápidos); en el régimen actual no paga. Bien medido: no es una muerte por falta
  de potencia sino un efecto que desaparece con N decente en cada época (96 / 106 / 158 operaciones).
- **La compresión crece:** −0,01 / +0,05 / +0,13. Coherente con el flujo vanna / vol-control que compra índice cuando cae la volatilidad
  implícita (más grande con 0DTE). La ganancia llega entre el día 2 y el 4 (salidas en la barra 1–2: −0,04 R; en 3–4: +0,55 R).
- **Versión intradía (operable en Lucid): no existe.** El control FM7N de FLUJOS-MACRO (compresión, compra a las 09:35 y cierre en el día)
  da +0,008 R en DESC (+0,021 / +0,002 / +0,003 por época, 3.644 operaciones). El mecanismo necesita días, no horas.
- Los eventos de pico y compresión no se superponen (0 entradas en común).

## 4. Qué cambia en la manera de trabajar
1. **«SIN_EVIDENCIA» se desarma por época antes de archivarse.** Cinco de las nueve pistas de Carril 2 tenían su R positivo en 2006–2017 y
   ≈ 0 o negativo desde 2018: el promedio de 20 años las hacía parecer vivas. Con el criterio «edges actuales» (Nico, 2026-10-22) no se
   persiguen. No se dan por refutadas (el efecto viejo fue real), sino por **apagadas en el régimen actual**.
2. **La confirmabilidad depende del efecto por operación.** Con α ≈ 0,01 y la mitad del efecto reciente, una regla de +0,10–0,15 R por
   operación con ≈ 4 operaciones por mes necesita décadas de forward. Ni la canasta T + R decide rápido: ≈ 15 meses de forward con su media de
   desarrollo y ≈ 33 con la mitad (`regimen_forward_20261119/ADENDA_POTENCIA.md`). **La búsqueda debería priorizar mecanismos de efecto grande por operación o de alta frecuencia con efecto medio**, no filtros que
   suben +0,05 R.
3. **eVRP y compresión** (las únicas que suben) quedan como pistas para una cuenta de broker y sólo en canasta: solas no se confirman.

Aporte al referente: separa lo que se apagó de lo que crece, descarta para el régimen actual cinco pistas que el promedio largo hacía
parecer vivas, y fija una regla de priorización (efecto por operación × frecuencia) que dice dónde sí se puede llegar a un edge confirmado.


> **Corrección (2026-11-19, después):** la «variante rápida» (cubeta 10, EMA 10) que recomienda §1 es degenerada (4 operaciones en NQ en 18 años); los promedios marginales incluían celdas casi vacías. Recomendación retirada; ver `z_pico_20261119/RESULTADO_RAPIDA_Y_SEVERIDAD.md` (el parámetro real es la severidad del filtro y la fábrica está en una meseta de 9 configuraciones).
