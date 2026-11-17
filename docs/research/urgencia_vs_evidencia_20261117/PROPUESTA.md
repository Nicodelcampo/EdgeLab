# Urgencia (el régimen se apaga) contra evidencia (pocos días de forward): cómo balancearlas

Estado: VIGENTE — ACEPTADA por Nico el 2026-11-17 («dale con la propuesta»). Avance: paso 1 hecho (`RESULTADO_PASO1.md`); paso 1b hecho
(`RESULTADO_PASO1B.md`: sin régimen de mercado en el dominio de la cartera; la urgencia temporal no tiene sustento); paso 2 hecho
(`RESULTADO_PASO2.md`: media de partida ≈ 0 para lo elegido en una criba); pasos 3–4 pendientes. Pedido original de Nico (2026-11-17): «balancear el riesgo de que se apaguen los regímenes (urgencia) con el riesgo de
operar una cartera con pocos días de operación, y encontrar un equilibrio y una forma de estimar que considere los dos». No mide nada
todavía; lo que mide va con su pre-registro. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Los dos riesgos, en la misma unidad
- **Esperar** cuesta la ventaja que se deja de cobrar mientras se confirma, y si el régimen dura poco se confirma algo que ya se apagó.
  Escala: **L**, la vida media de una ventaja (meses hasta apagarse).
- **Operar sin evidencia** cuesta lo que se pierde si la ventaja no existe (selección, suerte) o ya se apagó, y en una prop eso es
  quemar la cuenta. Escala: **T**, los meses que tarda el forward en decidir (`holdout_ventanas.plan_potencia`, K27).
- El cociente **T / L** ordena todo: si T ≪ L, conviene confirmar y después operar fuerte; si T ≈ L o mayor, la confirmación llega
  tarde y la única forma de cobrar es operar desde el principio **con tamaño chico y acotado**, en canasta, con corte automático.

## 2. Lo que EdgeLab ya sabe y lo que falta
| Pieza | Estado | Dónde |
|---|---|---|
| T de cada regla y canasta | **medido** (cartera v2 ≈ 3–12 meses; B ≈ 5–44; Franklin ≈ 71; Turtles 196) | `tools/potencia_previa.py` |
| Contracción de lo elegido (lo mejor de muchas pruebas sobrestima) | parcial (mitad del efecto como regla) | K27, `afinidad.K_CONTRACCION` |
| Presupuesto de riesgo por día que no toca el piso de la prop | **existe** | `cartera/asignacion.py` |
| Probabilidad de pasar/quemar una prop con media contraída | **existe** | `cartera_20261116` (PROP.json) |
| Seguimiento válido mirando cada semana y futilidad | **existe** | `funnel/secuencial.py` (e-proceso) |
| **L: cuánto dura una ventaja** | **NO MEDIDO.** Lo único medido: no hay persistencia de rachas detectable (≤ 0,05–0,10 de ρ), sí calidad estática (`canasta_regimen_20261026`) | — |
| Detector de apagado (cambio de régimen en el forward) | NO MEDIDO | — |

## 3. Propuesta: tamaño que crece con la evidencia y se multiplica por la probabilidad de que siga viva
Para cada regla o canasta y cada semana del forward:

    tamaño = presupuesto_prop × min(1, f_evidencia) × P(viva)

- **f_evidencia** = fracción de Kelly con la incertidumbre adentro: media posterior / (varianza por operación + varianza de la media),
  partiendo de la media de desarrollo **contraída** (mitad, o la contracción empírica de §4) y actualizada con cada operación forward.
  Con pocos datos la varianza de la media domina y el tamaño es chico solo; crece sin que nadie decida «ya está confirmada».
- **P(viva)** = supervivencia del régimen dada su edad y las señales de apagado: S(edad) de la vida media L (§4), multiplicada por
  un detector secuencial de deterioro (CUSUM / e-proceso de futilidad sobre el R forward). Si el detector dispara, P(viva) → 0 y
  la regla vuelve a papel (no se retira: sigue juntando información).
- **Topes duros** (ya existen): presupuesto diario de `asignacion.py` (el piso de la prop no se toca en un día), peso máximo por
  estrategia e instrumento, y nada en REAL sin habilitación humana.
- **Equilibrio**: con T/L grande el tamaño queda chico mucho tiempo (la regla aporta poco y arriesga poco); con T/L chico crece
  rápido. El cociente no se elige a ojo: sale de L medido y T medido.

## 4. Qué hay que medir (pre-registro aparte, cadena K32)
1. **Vida de una ventaja (L)**, sin elegir nada: en las reglas con historia larga y regla fija (SOM 2012–2026, Franklin, el catálogo
   SQX 2004–2026, las fichas de la cartera desde su desarrollo), R neto móvil de 12 meses → duración de los tramos positivos y
   negativos → curva de supervivencia (Kaplan-Meier) y vida media, por familia de mecanismo. Control: las mismas reglas con el signo
   de los días permutado en bloques (cuánto «dura» una racha de azar). Si la vida medida no se distingue del control, L no existe
   como dato y la política queda solo con f_evidencia y el detector.
2. **Contracción empírica**: cuánto de la media de desarrollo de lo elegido sobrevivió en su réplica/holdout en las campañas ya
   cerradas del embudo (ya hay decenas), en vez de la «mitad» fija.
3. **Detector de apagado**: tasa de falsas alarmas y demora de detección del CUSUM/e-proceso sobre esas mismas historias.
4. **Simulación de la política** contra «esperar a confirmar» y «operar fijo desde el día 1», en cuentas de prop (pasar, quemar,
   USD por mes), con las historias reales.

## Justificación económica / cómo podría refutarse
Las ventajas de corto plazo que encontramos son de régimen (Franklin y SOM en ES positivas sólo desde 2020; Turtles en oro desde 2011),
así que esperar años a confirmarlas puede llegar tarde; pero lo elegido entre muchas pruebas se encoge fuera de muestra, así que operar
fuerte sin evidencia quema cuentas. Se refuta si la política del §3 no le gana en la simulación del §4.4 a la mejor de las dos
alternativas simples (en USD por mes con probabilidad de quemar ≤ la de esperar), o si L no se distingue del control (entonces la
urgencia no está medida y no debe pesar).
