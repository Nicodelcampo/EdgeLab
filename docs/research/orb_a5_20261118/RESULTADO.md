# ORB-A5: resultado (2026-11-18)

Estado: RESULTADO — pre-registro `PREREGISTRO.md`, diseño `DISENO.md`. North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `CALIBRACION.json` (9/11), `DESC.json`, `REP.json` y
`OPS_DESC_REP.csv.gz`. Corrida con el código corregido de O1 (vela de 5 min completa).

## Veredicto: 5 nominadas en DESC, 0 confirmadas en REP (SIN_POTENCIA, no refutadas). Holdout NO abierto (E8). O1 pasa al forward
| Variante | DESC bruto (R) | p | años + | REP bruto | p REP |
|---|---|---|---|---|---|
| O1 ORB 5 min (Zarattini-Aziz) | **+0,118** | 0,001 | 85 % | +0,090 | 0,10 |
| O4 ORB 15 a favor del gap | **+0,103** | 0,004 | 70 % | +0,082 | 0,12 |
| O4 − O4N (contraste del gap) | +0,136 | 0,002 | — | +0,029 | 0,38 |
| O6 momentum de la 1.ª media hora | +0,024 | 0,03 | 60 % | +0,012 | 0,33 |
| O7 Noise Area | +0,498 | 0,02 | 60 % | +1,5 | 0,03 |
| O2 ORB 15 / O3 Crabel / O5 volumen / O8 fallido | +0,02 / +0,00 / −0,00 / +0,07 | > 0,1 o no calibran | — | — | — |

**Lectura de la tabla:**
- **REP** (LORD++ 0,011, Simes 0,15): ninguna confirma, pero las 5 conservan el signo. REP tiene 2 meses por año, y su EE de O1 (0,07) no
  distingue 0,1 R.
- **Stouffer DESC+REP de O1:** p ≈ 0,001. Es descriptivo, no reemplaza la confirmación.
- **O7** tiene el stop en el VWAP pegado al precio: el R explota (fricción 3,3 R). No es operable aunque nomine (K35).

## O1 (ORB de 5 min): la candidata para prop firms
**Bruto estable en las tres épocas (DESC + REP):** +0,122 (2006–11), +0,117 (2012–19) y +0,094 (2020–25).

**Con costos de MICROS, el rango de 5 min es chico frente a la fricción:**

| Época | Fricción en R (mediana) |
|---|---|
| 2006–11 | 0,53 |
| 2012–19 | 0,37 |
| 2020–25 | 0,11 |

**Subconjunto operable (fricción ≤ 0,08 R, declarado):**
- **2020–25:** 1.138 operaciones, 190 por año, neto micro **+0,095 R** (EE 0,076), 6/6 años positivos.
  - Por índice: NQ 769, YM 261 y ES 108 operaciones.
- **Antes de 2020 casi no hay operaciones en el subconjunto:** la fricción no lo deja.

**Por qué no se abre el holdout:**
- **Potencia:** O1 en bruto tendría ≈ 0,45 con la mitad del efecto (E8: no se gasta la única apertura).
- **Subconjunto operable:** tendría ≈ 380 operaciones en el holdout, sin potencia.
- **Destino:** al forward (terminal, desde la sesión del 2026-10-01) con e-proceso, como candidata a prop firm, en MNQ con el filtro de
  fricción.

## O4 (ORB 15 a favor del gap)
Bruto +0,215 / +0,029 / +0,085 por época: menos estable. Operable 2020–25 neto micro +0,044 (EE 0,057). Queda en seguimiento por detrás
de O1.
