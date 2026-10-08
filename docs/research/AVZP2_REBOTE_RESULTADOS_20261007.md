# AVZP2-REBOTE — resultados (MNQ 200t) — 2026-10-07

Manifiesto: `AVZP2_REBOTE_MANIFIESTO_20261007.md`. Kernels `edgelab-avzp2-k1..k3`. La v1 falló al arrancar porque el
módulo no estaba en el dataset de código; se incrustó en el script sin cambios de lógica. JSON:
`avzp2_rebote_20261007/`.

**Muestra:**
- Descubrimiento (09-25 → 06-26): 205 sesiones, 8.760 primeros regresos a zonas AVZP2 y 8.294 a zonas AVCL.
- Confirmación (09-26, 12-26): 56 sesiones.

## Formal (Holm 4), canal direccional: P(rebote de 2 alturas antes de romper 2 alturas)
| familia | real | pseudo | β (FE) | MDE | p Holm |
|---|---|---|---|---|---|
| AVZP2, todas | 50,6 % | 50,6 % | −0,1 pp | 1,7 pp | 1,0 |
| AVZP2, azules | 49,0 % | 50,8 % | **−1,8 pp** | 2,0 pp | 0,035 (lado opuesto) |
| **AVZP2, rojas (OB)** | **56,0 %** | 50,1 % | **+5,8 pp** | 3,8 pp | **0,0001** |
| AVCL | 50,6 % | 50,4 % | +0,2 pp | 1,8 pp | 1,0 |

**Confirmación de las rojas** (única prueba, contratos vírgenes para esta familia): +2,9 pp (53,0 % contra 50,6 %),
p = 0,097, MDE 4,9 pp, n = 807. **No confirma.** El efecto va en la misma dirección, pero es la mitad y la prueba
tiene poca potencia.

## Canal no direccional
Todas las familias llegan a ±D en 50 barras un 1,5–1,9 pp más que las pseudo (99,4 % contra 97,9 %). Las zonas están
en lugares donde el precio se mueve, pero sin lado. Es un efecto chico y esperable: las zonas nacen donde hubo
actividad.

## Descriptivos
- **AVZP2 contra AVCL** (exceso sobre su propio nulo): −0,2 pp, IC [−1,1; +0,8]. **No hay diferencia**: ninguno de
  los dos rebota más que el azar.
- **Rojas contra azules:** +7,7 pp, IC [+4,2; +10,7].

## Lectura
1. **"El precio rebota más en estos clusters": no, en general.** Las zonas de AVZP2, tomadas todas juntas, rebotan
   igual que una banda al azar. Las azules incluso un poco menos: tienden a romperse.
2. **"¿Es mejor que aVolClusterPOI?": iguales.** Ninguno le gana al azar en el rebote.
3. **Las rojas (orderblock) sí muestran algo**: +5,8 pp en descubrimiento y +2,9 pp en confirmación. Pero **no
   confirma**, y hay un problema de diseño que hay que cerrar antes de creerlo (ver "No medido", punto A).

## NO MEDIDO (además de la lista del manifiesto, que sigue vigente)
- **A. Un nulo apareado para las rojas.** La pseudo-zona copia la altura y la posición, pero **no** la condición que
  define a una roja: el precio se alejó 3 alturas dejando ≤ 2 % del volumen adentro. Entonces el +5,8 pp puede ser
  propiedad de **cualquier nivel del que el precio se alejó rápido y limpio**, no del cluster de volumen. Es la misma
  clase de error que la memoria `grupo-comparacion-sin-lookahead` advierte, del lado de la población. Hasta medirlo
  con pseudo-zonas que también cumplan la regla OB, **el efecto rojo no es atribuible a la zona**.
- **B. Potencia de la confirmación.** MDE 4,9 pp con 807 regresos. Hacen falta más contratos (por ejemplo NQ, o MNQ
  de años anteriores) para decidir.
- C. Rebote con otro D (1 altura) o con otro horizonte, para las rojas.
- D. P&L de entrar en el regreso a una roja.

## Estado
- `AVZP2 (todas / azules) Y AVCL: SIN REBOTE MAYOR QUE EL AZAR` (MNQ 200t, primer regreso, D = 2 alturas).
- `AVZP2 rojas: PROVISIONAL, NO CONFIRMADO`, pendiente del nulo apareado (A) y de más datos (B).

## Enmienda 1 — nulo apareado por la regla OB (2026-10-08)
Kernels `edgelab-avzpob-k1..k3`: k2 y k3 fallaron al arrancar y se relanzaron sin cambios. El análisis se hizo con
los 6 contratos; el resultado parcial con un solo kernel no se interpretó. JSON: `avzp2_rebote_20261007/AVZP2_OB_APAREADO_RESULTADOS.json`.

| | real (rojas) | pseudo | β | MDE | p |
|---|---|---|---|---|---|
| nulo simple (antes) | 56,0 % | 50,1 % | +5,8 pp | 3,8 pp | 0,0001 |
| **nulo apareado OB** | 56,0 % | **53,3 %** | **+2,5 pp** | 3,8 pp | **0,068** |

- Con el nulo apareado, las pseudo-zonas que también se alejaron limpio rebotan 53,3 %. **Más de la mitad del efecto
  rojo (3,3 de 5,8 pp) era del alejamiento limpio**, no del cluster de volumen.
- Lo que queda (+2,5 pp) **no pasa** (p = 0,068) y está por debajo del MDE (3,8 pp). La confirmación no se corre.
- Canal no direccional: +1,7 pp (igual que todas las familias, sin lado).

**Estado:** `AVZP2 rojas: SIN EFECTO PROPIO DETECTADO` contra el nulo apareado. El rebote de las rojas es, sobre todo,
el de cualquier nivel del que el precio se alejó rápido y limpio. Queda abierta una diferencia de ≤ 3,8 pp que esta
muestra no puede ver (ver NO MEDIDO B: más datos).
