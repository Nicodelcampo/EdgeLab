# AVZP2-RACIMO-GRILLA — enmienda 2: O5 con control de volumen e intensidad previos — resultados — 2026-10-09

Pre-registro: enmienda 2 de `AVZP2_RACIMO_GRILLA_MANIFIESTO_20261008.md` (commit `bf9a606d`, anterior a la corrida).
Kernels `edgelab-avzvol-k1..k3` v1, código `4e1e2693`, árbol limpio (procedencia en el JSON). MNQ 25t, 6 contratos.
JSON: `avzp2_racimo_grilla_vol_20261009/AVZP2_RACIMO_GRILLA_VOL_RESULTADOS.json`. **Información, no P&L.**

## 0. Integridad
Sin el control, la corrida reproduce los 23 β de O5 publicados el 08/10 (diferencia máxima 7e-17) y las mismas 23
celdas evaluables. Mismos datos, mismos pseudo.

## 1. Resultado: la compresión no se explica por la actividad previa
- Con FE por decil de `vol_occ`, `vol_100`, `dur_occ` y `dur_100`: **23 de 23 celdas** siguen negativas con Holm ≤ 0,05
  en descubrimiento, y **23 de 23** en confirmación. Lectura pre-registrada: **«robusta»**.
- β controlado entre −0,043 y −0,099 de log-rango. Razón β controlado / β sin control: entre 0,94 y 1,20 (mediana
  ≈ 1,04). El control casi no mueve el efecto.
- MDE por celda entre 0,012 y 0,060; en todas las celdas |β| supera o iguala el MDE salvo 6/1.000/20 (β −0,048, MDE
  0,058) y 5/500/20 (β −0,059, MDE 0,060), que pasan Holm con poco margen (p 0,020 y 0,011).
- Las dos celdas que el 08/10 no confirmaban (5/1.000/20 y 6/1.000/20) ahora confirman con el control (p Holm 0,009 y
  0,038). Son las de menor margen; no se leen como más fuertes que antes.

## 2. Descriptivo: los racimos reales sí venían con otra actividad que sus pseudo
- **Volumen:** +1 a +3 % en las 500 y 100 velas previas, en todas las celdas (z entre +8 y +18). El desbalance que
  motivó la enmienda existe, pero es chico.
- **Tiempo:** en ventanas de 1.000 velas las 500 velas previas tardaron +7 a +23 % más (z +9 a +12), o sea **menos**
  intensidad, no más. En 250–500 la diferencia es de +2 a +6 %.
- La hipótesis rival era una ráfaga previa que decae. Los datos muestran poco volumen extra y una intensidad igual o
  menor, y controlar por ambas no cambia β.

## 3. Informativo: O1 con los controles de la enmienda 1 más actividad
En las celdas de ventana 1.000 el β de O1 baja entre 0,001 y 0,012 al agregar actividad (p. ej. 4/1.000/45: +7,5 →
+7,1 pp; 6/1.000/45: +6,1 → +5,4 pp). 6/1.000/20 queda en +0,3 pp (ya era no significativa). No suma pruebas formales.

## Límites
- Controlar por deciles no es aparear: queda heterogeneidad dentro de cada decil.
- Los contratos de confirmación ya se habían mirado para O5: esto sostiene el hallazgo frente a una rival concreta, no
  es una confirmación nueva.
- No descarta otras rivales (p. ej. que el pseudo, elegido en cualquier vela de la misma franja horaria, difiera del
  racimo en algo que no sea ocupación, amplitud ni actividad).

## NO MEDIDO
- P&L. Otros instrumentos (NQ, ES) y otras escalas. Control **apareado** por actividad. Ventanas > 1.000.
- El pseudo contra su propio censo (`LES-CONTROL-EVENT-SELECTION-20260928`).
