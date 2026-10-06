# VTD-VOL-1 — VolTicksDef: resultados MNQ, cara a cara con aVolClusterPOI — 2026-10-06

- Manifiesto: `VTD_VOL1_MANIFIESTO_20261006.md`. Paridad: `docs/parity/PARIDAD_VOLTICKSDEF_MNQ1226_150T_20261006.md`.
- Kernels `edgelab-vtd-mnq-k1..k4` + `edgelab-vtd-vol1-20261006` (157 s).
- JSON: `vtd_vol1_20261006/VTD_VOL1_RESULTADOS.json`. Registro: 8 pruebas, familia `VTD_VOL` (propia).

## Formal (8, Holm, bilaterales): las 8 significativas
| prueba | 150t | 50t |
|---|---|---|
| `y_rg` H10 A1 | **+0,052** (MDE 0,023) | **+0,037** (MDE 0,016) |
| `y_rg` H10 A2 (contra volumen alto sin marca) | **+0,051** | **+0,039** |
| cola sin signo H10 (\|mov\| ≥ 1R) | **+2,5 pp** (base 15,8 %) | **+2,3 pp** (base 17,4 %) |

**Cara a cara en 50t (`y_rg` H10 A1):**
| | β | n |
|---|---|---|
| AVCL **sin** marca VTD en el bloque | **+0,065** (MDE 0,006) | 32.032 |
| VTD **sin** bloque AVCL | **+0,038** (MDE 0,017) | 13.241 |

Solapamiento: sólo el 5,4 % de las zonas AVCL contiene una marca VTD, y sólo el 12,8 % de las marcas VTD cae en un bloque
AVCL.

## Lectura pre-registrada: **señales complementarias**
Las dos tienen efecto propio, sin la otra:
- **AVCL es más fuerte:** +0,065 contra +0,038, unas 1,7 veces.
- **VTD también sobrevive al control de volumen alto** (A2 ≈ A1). Para VTD, ese control es casi tautológico, pero el
  efecto se sostiene.
- Como casi no se solapan, **son eventos distintos**: AVCL marca "concentración de volumen en un precio"; VTD,
  "barra con lotes grandes". Combinados cubren más momentos de expansión.

## Descriptivos que importan
- **Ancho de zona, OPUESTO a AVCL.** En VTD, las barras **anchas** expanden más: Q1 −0,04 → Q5 +0,12 (50t);
  −0,03 → +0,11 (150t). En AVCL las zonas **angostas** expanden más. Probable lectura: una barra VTD ancha ya es un
  movimiento con lotes grandes, y continúa la expansión; en AVCL, la concentración en pocos precios es el sello.
  Cuidado: el rango de la barra marcada entra en la ventana "previa" de `y_rg`. Es hipótesis, no medido.
- **Dosis (ratio/umbral):** sube en 50t hasta Q4 (0,017 → 0,057); en 150t es plana o no monótona. Más débil que la
  dosis de AVCL.
- **ETH:** ≈ 0 en 150t, +0,026 en 50t. Más débil que AVCL (cuyo ETH era +0,06).
- **H50:** +0,03 (150t), +0,01 (50t). Decae igual que AVCL.

## Estado
`VTD: EXPANSIÓN PROPIA, MÁS DÉBIL QUE AVCL Y COMPLEMENTARIA`. No es edge: es información de rango, sin dirección
medida. Siguientes pasos naturales:
- (a) la señal combinada (AVCL ∪ VTD) como contexto;
- (b) en VTD, ¿la vela marcada da dirección? (colas con signo por close − open; registrado, no medido);
- (c) la prueba del ancho con una ventana previa que excluya la barra marcada.
