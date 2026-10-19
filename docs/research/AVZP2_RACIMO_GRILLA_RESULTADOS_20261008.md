# AVZP2-RACIMO-GRILLA — 36 definiciones de racimo — resultados (MNQ 25t) — 2026-10-08

Manifiesto: `AVZP2_RACIMO_GRILLA_MANIFIESTO_20261008.md` (+ enmienda 1, auditoría de O1). Kernels
`edgelab-avzgrid-k1..k3` v3: con magnitud de tendencia y **semilla estable** (crc32; antes `hash()` cambiaba por
proceso, ver más abajo). JSON: `avzp2_racimo_grilla_20261008/`.

Grilla: mínimo de zonas {4, 5, 6, 8} × ventana {250, 500, 1.000} × altura {20, 30, 45} ticks.
- **23 de 36 celdas evaluables** (≥ 300 racimos en descubrimiento).
- No evaluables, por pocos racimos: todas las de 8 zonas salvo 8/1.000/45, las de 6 zonas con ventana de 250, 6/500/20 y
  5/250/20.

## 1. Compresión (O5): propiedad robusta del racimo
- **23 de 23** celdas en descubrimiento, entre −0,04 y −0,10 de log-rango (**4–10 % menos movimiento** después de la
  salida), todas con Holm < 0,05.
- **21 de 23 confirman** (las dos que no, 5/1.000/20 y 6/1.000/20, van en el mismo signo).
- Es más fuerte en ventanas cortas (250–500: −8 a −10 %) que en 1.000 (−4 a −8 %).

## 2. Salida a favor de la tendencia (O1): real en ventanas largas, después de la auditoría
Sin control, O1 pasa en varias celdas. **Con FE por magnitud de la tendencia (500 velas) y momentum (100 velas)**:

| celda | real | pseudo | β controlado (desc.) | β controlado (conf.) |
|---|---|---|---|---|
| 4 / 1.000 / 45 | 67,4 % | 57,9 % | +7,5 pp | **+7,8 pp** |
| 5 / 1.000 / 45 | 67,0 % | 58,1 % | +7,0 pp | **+7,6 pp** |
| 6 / 1.000 / 45 | 66,2 % | 58,6 % | +6,1 pp | **+8,5 pp** |
| 6 / 1.000 / 30 | 62,8 % | 56,3 % | +6,5 pp | **+6,3 pp** |
| 5 / 1.000 / 30 | | | +4,9 pp | **+4,7 pp** |
| 4 / 1.000 / 30 | | | +4,1 pp | **+5,0 pp** |
| 4 / 500 / 45 | 65,1 % | 58,5 % | +3,4 pp | **+3,9 pp** |
| 4 / 1.000 / 20 | | | +3,3 pp | **+3,7 pp** |

Las celdas confirmadas tienen Holm ≤ 0,05 en descubrimiento y en confirmación.
- En **ventanas de 250–500 velas con alturas de 20–30, O1 ≈ 0**, y eso incluye la configuración de Nico (6/500/30).
- El patrón es monótono: cuanto más larga la ventana y más alta la franja, más continuación.
- **Lectura:** cuando las zonas se acumulan durante mucho tiempo (1.000 velas) en una franja ancha, la salida sigue
  la dirección de la tendencia previa ≈ 7–8 pp más que una consolidación de la misma ocupación, la misma magnitud de
  tendencia y el mismo momentum. Es una "pausa con inventario" que se resuelve a favor de la tendencia.
- **8 / 1.000 / 45** pasa en descubrimiento (+7,9 pp) pero **no confirma** (+2,8 pp, n más chico).

## 3. Lo que no aparece en ninguna celda
- **Seguimiento de la ruptura (O2):** en algunas celdas es negativo (las rupturas siguen menos), pero no confirma.
- **Rebote en el retest (O3b):** ≈ 0 en las 23 celdas.

## Para diseñar (información, no P&L)
- El racimo **amortigua**: después de salir, el precio se mueve menos. Eso vale para cualquier definición.
- Si la definición es **larga y ancha** (≥ 1.000 velas, 30–45 ticks), además **anticipa el lado de la salida**: a
  favor de la tendencia de 500 velas en ≈ 66 % de los casos (contra 58 % en una consolidación comparable).
- Combinación natural para estudiar: **salida de un racimo largo a favor de la tendencia, con objetivos cortos**,
  porque la compresión limita el recorrido. La excursión mediana después de salir es de ≈ 0,25 alturas. **El P&L no
  está medido** y requiere STOP + manifiesto.

## Reproducibilidad (hallazgo de integridad)
Los scripts de pseudo-zonas de AVZP2-REBOTE, del nulo OB, de AVZP2-RACIMO base y de HFTV4-RETORNO sembraban el RNG
con `hash(contrato)`. En Python, `hash()` de un string cambia por proceso, así que **los pseudo no son reproducibles
exactamente** entre corridas. No introduce sesgo (el muestreo sigue siendo al azar), pero viola el determinismo.
Corregido en la grilla (`zlib.crc32`). Los demás quedan pendientes; sus conclusiones no cambian, pero sus números
exactos no se reproducen.

## NO MEDIDO
- **P&L** de cualquier lógica (salida a favor de la tendencia, rango).
- **O1 en otros instrumentos.**
- **Ventanas > 1.000 velas y alturas > 45 ticks**, donde el patrón monótono sugiere más efecto: no medido, y requiere
  potencia.
- **La interacción O1 × compresión** (si la salida a favor sigue más que la salida en contra).
- **Persistencia más allá de 200 velas.**
- **La configuración de detección de zonas** (percentil, bloque, franja), que se mantuvo fija.
- Todo lo de la lista del manifiesto base.
