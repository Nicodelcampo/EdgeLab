# Manifiesto ESPEJO-CONT-TPSL: ¿después de completar el espejo, el precio sigue de largo más allá de A? — PRE-REGISTRO (2026-09-28)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PRE-REGISTRO. **Es una búsqueda sobre P&L: STOP hasta el OK de Nico.** Nada corrido.
**Familia:** ESPEJO-IND, sub-familia nueva **CONT** (continuación), presupuesto de multiplicidad propio.

## 1. Hipótesis, justificación y refutación
- **Hipótesis (Nico, 28/09, ejemplos #1033, #1043, #1065):** cuando la vuelta completa el espejo (toca A), el precio sigue
  en la dirección de la vuelta (B → A → más allá) más de lo que daría el azar. Existe alguna combinación TP/SL, medida en
  fracciones de W, con esperanza **bruta** positiva por encima del nulo, aunque no pague costos a esta escala.
- **Justificación económica:** la vuelta que deshizo la ida entera demuestra que el empuje del impulso se agotó; A es el
  origen del impulso, donde quedaron órdenes de quienes lo iniciaron (stops del lado contrario). Tocarlo puede disparar esa
  liquidez y extender el movimiento.
- **Cómo podría refutarse:** ninguna celda de la grilla supera al nulo después de corregir por haber probado la grilla
  entera; o la ventaja aparente es la de cualquier ruptura de un extremo reciente (control C-RUP, §4).
- **Aviso de Nico (efectos que se anulan):** el precio puede seguir cuando hay X y darse vuelta cuando hay Y; el promedio
  puede ser ~0 con dos efectos reales. Se registra como **riesgo explícito y pendiente**: se publican los dos canales
  (sigue / se da vuelta hacia B) y la distribución completa de la excursión después de A; la separación por contexto
  (L2, BigTrap2 absorción, semejanza, volumen) queda para análisis posteriores, **no** se busca en esta corrida.

## 2. Población (regla de población)
Eventos del espejo enumerados: creación, confirmación en B, cruce de x, **completado (toque de A)**, fracaso, vencimiento,
estado continuo. **Se congela: el completado**, que es donde Nico propone entrar.

## 3. Configuraciones (parametrizadas, todas publicadas)
| Id | Instrumento | Velas | Impulso |
|---|---|---|---|
| C1 | ES | 25t | calibración base de Nico: W ≥ 17 t, ≤ 20 velas (nivel 3 del visor) |
| C2 | ES | 100t | W ≥ 34 t, ≤ 20 velas (la de ESPEJO-NICO) |
| C3 | MNQ | 25t | W ≥ 17 t, ≤ 20 velas (donde la semejanza sí se sostuvo, ESPEJO-SIM) |
Estratos: TBZ (eficiencia ≥ 0,6) y otros (0,3–0,6).

**Enmienda 1 (28/09, antes de mirar resultados, pedido de Nico: «es necesario que haya muchos más trades»).**
El nivel 3 daba ~0,8 completados por sesión en ES 25t (~144 en el descubrimiento) y ~0,2 en 100t. Se reemplazan las
configuraciones por los niveles 4 y 5 del slider de permisividad del visor: **C1N4** ES 25t 13 t/25 velas (~1.000 trades),
**C1N5** ES 25t 9 t/30 velas (~10.000), **C2N5** ES 100t 18 t/30 velas (~1.900), **C3N4** y **C3N5** MNQ 25t. Son 150 celdas;
la prueba primaria sigue siendo el máximo estadístico por configuración y estrato. En N5 la fricción es ~1/3 de W: se
reporta la señal bruta; la viabilidad a mayor escala queda para después (Nico).

## 4. Entrada, salida, nulo y control
- **Entrada:** orden stop en A en la dirección de la vuelta; llenado = A + 1 tick de deslizamiento en contra (se toca A
  con la mecha; el stop se dispara ahí).
- **Salida:** TP ∈ {0,25; 0,5; 1; 1,5; 2} × W más allá de A; SL ∈ {0,25; 0,5; 1} × W hacia B. **15 combinaciones.**
  Si una vela toca TP y SL, cuenta **SL** (conservador). Cierre forzado a fin de sesión al último precio.
- **Resultado:** R bruto en W y en ticks por trade; también neto con la fricción propia de cada instrumento (no se
  transporta la de ES a MNQ).
- **Nulo:** para cada trade, `simulate_null` (ternas 25t estrictamente anteriores a la vela de entrada, centradas) da
  p(TP), p(SL), p(cierre) con las mismas barreras y horizonte; esperanza nula = p(TP)·TP − p(SL)·SL + cierre. Exceso =
  R realizado − esperanza nula. Controla la asimetría de la geometría TP/SL (una grilla siempre tiene celdas «positivas»
  por la forma del pago).
- **Control C-RUP:** ruptura de un máximo/mínimo reciente sin espejo, a la misma distancia en W y hora parecida, con la
  misma grilla. Separa «continuación después de un espejo» de «continuación después de cualquier ruptura».

## 5. Multiplicidad
3 configuraciones × 2 estratos × 15 celdas = **90 celdas**. Primaria: **máximo estadístico de la grilla con bootstrap
por sesión** (tipo White Reality Check / SPA): se rechaza el nulo global si el mejor exceso estandarizado supera el
percentil 95 de su distribución bootstrap. Secundaria: BH q = 0,10 por celda. Se publica el **landscape completo**
(las 90 celdas), nunca sólo la mejor.

## 6. Datos y particiones
- **Descubrimiento:** ES y MNQ jul-2025 → mar-2026, Lucid (research-v2). El completado de espejos ya se miró en
  ESPEJO-SIM (MNQ) y ESPEJO-NICO (ES) para **otra** pregunta (llegar a A); lo que pasa **después** de A no se miró.
- **Confirmación (una vez, sólo celdas o configuraciones sobrevivientes):** abr–jun 2026, Lucid. **Holdout:** oct+.

## 7. Componentes registrados, no probados acá
Semejanza (MNQ, métrica vieja; ES, modelo de Nico), VOLLIMP (pista −12 pp), contextos L2 (en construcción),
BigTrap2 absorción. Se guardan por trade para el análisis siguiente, sin mirarlos como filtro en esta corrida.

## 8. Riesgos
- Grilla TP/SL = búsqueda sobre P&L: el control del nulo por trade y el máximo estadístico existen por eso.
- Precio de trade (sin caché de midquote en MNQ): el deslizamiento de 1 tick y la regla «SL primero» lo compensan en parte.
- ES 25t tiene pocas vueltas que completan (lección de las tríadas); C1 puede quedar sin potencia: se publica el MDE.
- Trades superpuestos del mismo impulso: uno por impulso (el primer toque de A); bootstrap por sesión.
