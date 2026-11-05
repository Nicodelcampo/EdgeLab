# Variante τ de las reglas con acta — pre-registro (2026-10-31)

Estado: VIGENTE (antes de correr; aprobado por Nico en la sesión en la nube, 31-oct).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa: EF2 (descubrimiento sobre DESC), confirmación forward.

## Qué
Las 10 reglas con acta que operan en su propio instrumento (todas salvo CVGAP-CFD-NQ y U1-ORO, que ejecutan en otro y donde las
líneas del sensor no valen): **mismas entradas, mismas celdas, mismo tope**, y tres salidas τ adicionales (primer cierre del lado
equivocado de la línea por los dos últimos pivotes de orden 3, 5 u 8; δ = 0; stop y objetivo originales siguen activos).
Módulos `edgelab/research/variante_tau.py` + `vtau_*.py`; herramienta `tools/variante_tau_actas.py`.

## Por qué
Auditoría externa del PR #162: 10 de las 12 reglas tienen W/L 0,23–0,35 (ganan poco y seguido, pierden de a mucho) y la canasta se
aplanó en jul–sep. Si la salida estructural mejora el pago con las mismas entradas, el riesgo de cola baja sin buscar entradas nuevas.

## Cómo se mide
- Sólo el período DESC de cada regla (desarrollo). Nada del OOS ni del holdout: el OOS de esas entradas ya se miró, y el holdout de
  octubre es de la canasta de 7 (`docs/research/canasta_7_20261030/PREREGISTRO.md`), que **no cambia** por este estudio.
- Por regla y variante: diferencia por sesión del neto (τ − original), IC90 y p unilateral por bootstrap de sesiones; W/L de cada salida.
- 30 comparaciones (10 reglas × 3 órdenes) con BH q ≤ 0,10. Se registran 3 pruebas por regla en el contador global.

## Decisión
- Nominada: diferencia > 0 y BH q ≤ 0,10. Una variante nominada **no** entra a la canasta de 7 ni consume su holdout: se mide forward
  desde el 2026-11-02 como regla nueva, con su propio pre-registro.
- Ninguna nominada: la salida τ no mejora estas entradas; queda registrado como resultado negativo con su MDE.

## Cómo se refuta
Diferencia ≤ 0 o sin rechazo BH en las 30 comparaciones. La salida τ de la familia TAU-TENDENCIA es otra hipótesis y no se refuta acá.

## Resultado (2026-10-31, `variante_tau/COMPARACION.json`)
**REFUTADA para las 10 reglas.** 30 comparaciones (10 reglas × pivotes 3/5/8), BH q 0,10: **0 nominadas**. En 27 la diferencia
τ − original es negativa y en 21 el IC90 queda entero por debajo de 0. Las 3 positivas son U1-ZONAS-BT2-NQ (+0,4 a +1,8 por sesión,
IC90 que cruza 0; es además una regla excluida de la canasta de 7).
- Lo que pasa: la salida τ sube el cociente ganancia/pérdida en la mayoría (por ejemplo, CVGAP-NQ 0,75 → 1,2–1,6), pero corta antes
  operaciones que la regla original deja madurar, y la media cae (CVGAP-NQ +15,2 → −0,6/+2,7; U1-ZONAS-NQ +30,6 → −1,4/+0,9;
  U1-ZONAS-ES +10,3 → ≈0). Estas reglas son de reversión hacia una zona: el pago está en llegar al objetivo, no en seguir una
  tendencia, y la línea de estructura se rompe antes de que llegue.
- Alcance de la refutación: la salida τ con δ = 0 sobre estas entradas congeladas, en DESC. No refuta la salida τ en reglas de
  tendencia (TAU-TENDENCIA, que se mide aparte) ni dice nada del OOS o del holdout de estas reglas, que no se tocaron.
- MDE: con 28–220 sesiones por regla, el semiancho del IC90 de la diferencia va de 1,2 (U1-ZONAS-BT2-ES) a 19 puntos por sesión
  (U1-ZONAS-NQ); las diferencias observadas en contra superan ese MDE en 21 de 30.
