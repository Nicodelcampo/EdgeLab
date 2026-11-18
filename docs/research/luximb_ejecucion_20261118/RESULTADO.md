# LUXIMB-EJECUCION: rediseño de la ejecución del fade de impulsos (punto 2) — resultado (2026-11-18)

Estado: RESULTADO — **REFUTADA_ECONOMICA. Ninguna de las 22 ejecuciones (stop amplio, objetivo más lejos, BE, parcial, rescate de
Nico) tiene R neto positivo en DESC. El holdout A5 del linaje no se abre y queda sellado.**
- **Pre-registro:** `PREREGISTRO.md`. **Datos:** `CALIBRACION.json` (35/44), `DESC.json`, `RESCATE_PAREADO.json` y
  `OPS_DESC_REP.csv.gz`.
- **Motor:** único, con la ejecución nueva `RESCATE` (tests y calibración sin optimismo). **Herramientas:**
  `edgelab/research/luximb_ejecucion.py` y `tools/a5_campana.py`.
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Lo que hace el stop amplio (DESC, NQ 2006–2022; R por operación)
| Stop | z1 bruto | z1 neto | z0 bruto | z0 neto | Fricción en R |
|---|---|---|---|---|---|
| 0,5·D | **+0,043** | −0,524 | +0,017 | −0,564 | 0,57–0,58 |
| 1·D | +0,015 | −0,269 | +0,002 | −0,289 | 0,28–0,29 |
| 1,5·D | +0,012 | −0,177 | +0,004 | −0,190 | 0,19 |
| 2·D | ≈ 0,000 | −0,141 | −0,002 | −0,147 | 0,14 |

- **La fricción en R baja al ensanchar, pero el bruto baja a la par.** La reversión vive en el tramo corto (timing fino), no en la
  distancia. Se cumple la cláusula 2 de «cómo podría refutarse».
- **Neto:** negativo en las 44 celdas. El subconjunto operable (fricción ≤ 0,08 R) da −0,04 a −0,07 en todas.
- **Objetivo más allá de A, BE y parcial:** no cambian el cuadro (BE es el peor: corta las que vuelven).
- **Nominadas por bruto (BH):** 15, todas con neto ≤ −0,17. La compuerta económica no deja pasar ninguna.

## 2. El rescate de Nico (pareado contra MERCADO con el mismo stop, mismos eventos)
Interpretación pre-registrada: al adentrarse d del riesgo hacia el stop, salida límite a −x del riesgo.

| | DESC | REP |
|---|---|---|
| d 0,5, x 0 | **+0,004 a +0,010 R** (p ≤ 0,03, salvo z1 1,5·D) | +0,001 a +0,003 en z0 (n.s.); −0,008 a +0,003 en z1 |
| d 0,75, x 0,25 | +0,001 a +0,005 | −0,001 a −0,009 |

- **Lectura:** en DESC el rescate suma un poco (convierte stops enteros en salidas cerca de la entrada), pero no replica en REP. Lo
  que salva en las que se van se compensa con las que habrían vuelto al objetivo.
- **Tamaño:** en todo caso es diez veces menor que la fricción.
- **Queda en el motor como ejecución estándar** (`RESCATE`) para otras familias. En una regla con ventaja neta podría servir como
  control de cola, pero eso es otra hipótesis.

## 3. Consecuencias
- **El fade de impulsos LUX-IMB en NQ queda cerrado en lo económico** con stop corto, stop amplio y salidas alternativas. El holdout
  A5 del linaje sigue sellado: no vale gastarlo en una regla sin neto.
- **Para el resto de los mecanismos con bruto real (ORB 5 min, Franklin, T, SOM):** su holdout ya está mirado. Un rediseño de
  ejecución sólo se podría confirmar en forward. ORB tiene stop estructural (`PRECIOS`) y el rescate necesitaría una versión por
  precios: queda propuesto, no medido.
- **Lección transferible:** antes de ensanchar el stop para bajar la fricción en R, medir si el bruto por R se sostiene con la
  distancia (curva bruto–stop). Si cae a la par, la señal es de timing y ninguna ejecución la salva.
