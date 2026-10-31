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
