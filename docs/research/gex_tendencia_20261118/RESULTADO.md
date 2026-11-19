# GEX a fondo: resultado (exploración DESC + confirmación única en REP + HOLDOUT A5, 2026-11-18)

Estado: RESULTADO — **filtro de gamma en las reglas de tendencia: NO_CONFIRMADA por estabilidad (53 % de años contra el 60 %),
con el contraste significativo al nivel LORD (p 0,0102 < 0,0109). No refutado. Lo robusto: con gamma ALTA las tres reglas pierden, en
DESC y en REP + HOLDOUT.**
- **Pre-registro:** `PREREGISTRO.md` (fase 1 + apéndice 1, con la decisión de Nico «REP+HOLDOUT, una vez»).
- **Datos:** `RESULTADO_EXPLORACION.md` (fase 1), `APERTURA_FILTRO.json` y `CONFIRMACION_FILTRO.json`.
- **Herramienta:** `tools/gex_tendencia.py`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Confirmación (una lectura; cortes de DESC congelados; canasta T + Franklin + SOM, R neto por día)
| | Gamma baja | Media | Alta |
|---|---|---|---|
| **DESC** (exploración) | +0,305 | +0,033 | **−0,569** |
| **REP + HOLDOUT** (confirmación) | +0,133 | +0,255 | **−0,519** |
| Días en REP + HOLDOUT | 425 | 496 | 507 |

- **Contraste baja − alta:** +0,652 R/día (EE 0,281), p 0,0102. LORD rechaza al nivel 0,0109. Potencia planeada 0,86.
- **Años con el contraste positivo:** 8 de 15 (53 %) → **NO_CONFIRMADA** por la regla pre-registrada. REFUTADA no aplica: la cota
  inferior está lejos de 0.
- **Por regla, R por operación en REP + HOLDOUT** (baja / media / alta):
  - T: +0,010 / +0,002 / **−0,121**;
  - Franklin: +0,001 / +0,099 / **−0,135**;
  - SOM: +0,037 / +0,062 / **−0,037**.
- **Canasta sin los días de gamma alta:** +0,199 R/día (p 0,09), contra −0,056 operando siempre.

## Lectura
- **Lo que replica es el extremo, no la dosis:** con gamma alta (los dealers anclan el precio) las reglas de ruptura pierden. Pasa en
  las tres reglas, en DESC y en REP + HOLDOUT, en el mismo tamaño (≈ −0,5 R/día en la canasta).
- **Entre gamma baja y media el orden no se sostiene.** Por eso el contraste baja − alta pasa el nivel pero no la estabilidad por año:
  algunos años el tercil bajo rinde menos que el medio.
- **La forma operable es una regla de exclusión** («no operar reglas de tendencia el día después de gamma alta»), no un ranking de
  gamma. Esa forma no es la que se pre-registró como prueba. No se re-prueba en estos datos: va al forward.

## Además (fase 1)
- La gamma anticipa la magnitud del día más allá de la volatilidad (Spearman parcial 0,23 con rango/ATR).
- Las reglas direccionales con gamma (continuación desde las 10:00, momentum del cierre de Baltussen) no pagan neto.

## Siguiente
1. **Forward con el filtro de exclusión** (hipótesis nueva, pre-registro aparte): T + Franklin + SOM, con y sin días de gamma alta,
   desde la frontera. Necesita GEX diario: SqueezeMetrics publica el dato gratis; hoy el archivo llega al 2026-11-06.
2. **No darle tamaño real** hasta que el forward decida.
3. **En una prop firm**, el filtro reduce días de pérdida (−0,5 R/día con gamma alta): candidato a simulación Lucid una vez
   confirmado.

## Apéndice 2: tres pruebas más del mecanismo (2026-11-18, `MECANISMO.json`)
LORD++ nivel 0,0145, tres pruebas pre-registradas. Corte congelado de DESC: gamma alta = `g_rank250` ≥ 0,739.

| Prueba | Alta | Resto | Contraste (EE) | p | Años con el signo de H1 | Veredicto |
|---|---|---|---|---|---|---|
| P1 exclusión en EMD + RTY (T + Franklin + SOM, R/día) | −0,040 | +0,029 | −0,069 (0,099) | 0,24 | 40 % | no confirma |
| P2 fade LUX-IMB NQ (signo opuesto, R/op bruto) | +0,024 | +0,005 | **+0,018** (0,009) | 0,026 | **75 %** | dirección correcta, no llega al nivel |
| P3 ORB O1 (confirmación, R/op bruto) | +0,075 | +0,079 | −0,005 (0,075) | 0,48 | 53 % | sin efecto |

**Lectura:**
- **El filtro de gamma es más angosto de lo que sugería DESC.** Su evidencia sigue concentrada en T, Franklin y SOM en NQ/ES/YM (DESC
  y REP + HOLDOUT). No aparece en EMD/RTY, donde esas reglas además son débiles, ni en ORB O1.
- **La predicción opuesta va en la dirección del mecanismo:** con gamma alta el fade de impulsos revierte algo más, +0,018 R, en el
  75 % de los años. Es chica y no pasa el nivel.
- **Mecanismo (anclaje con gamma alta, amplificación con baja): NO confirmado.** Hay señales consistentes en DESC, REP + HOLDOUT y el
  fade, pero no transfiere a otros índices ni al ORB.
- **Lo que queda operable como hipótesis de forward:** excluir los días de gamma alta en T, Franklin y SOM en NQ/ES/YM. Con eso, el
  historial pasa de perder a ganar en dos muestras. Alcance acotado a esas reglas e índices.
