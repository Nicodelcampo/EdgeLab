# IDEA — L2 durante el segundo impulso del espejo

**Estado: NO MEDIDO; semántica por confirmar con Nico.** Línea separada de
MNQ escalonadas × L2. Si «segundo impulso» es el regreso desde B hacia A,
propuesta primaria: landmark50 % de |B−A|, llegada a A frente a invalidación/timeout.
No es continuación después de A ni rebote desde A: son preguntas diferentes.

## Qué podría aportar L2

Presión/consumo reciente, reposición/persistencia y retirada visible, asimetría
del libro y spread a la altura del landmark. Son candidatos provisionales, no
predicciones probadas. MBP10 ve el entorno inmediato, no todo el trayecto a A si
A está lejos de los diez niveles. Liquidez que desaparece no prueba cancelación
ni manipulación. Agresor inferido de L1 sería heurístico, no ground truth.

## Evento causal imprescindible

- A y B registrados con sus instantes disponibles. B final observado a posteriori
  no se puede usar para decidir antes de conocerlo.
- Congelar A/B y anchura W antes del landmark, sin mover extremos para que cuadre.
- Registrar TODOS los intentos desde B confirmado, no sólo espejos completados.
  Si el50 % se alcanzó antes de confirmar B, no backdate: marcar overshoot conocido
  en B-confirmación y separarlo de una observación genuina al cruzar50 %.
- `tools/mirror_landmark.py` provee emisión/dirección, no detector A/B ni outcome.
  Su `snapshot()` se guarda por cada intento, incluidos fallidos. Intentos sin
  landmark se cuentan; no entrenar como si nunca hubieran existido.

## Contraste que respondería la pregunta

Baseline con precio/anchura/progreso, tiempo desde B, velocidad/volatilidad y spread
previos. Comparar contra el mismo baseline + pocas features L2 conocidas al evento.
Que L2 distinga trayectorias no basta: exigir mejora incremental fuera de muestra,
calibración de probabilidad y finalmente margen neto con ejecución propia.
No elegir25/40/50/75 % mirando qué porcentaje da mayor P&L. 50 % es propuesta,
no aprobación; horizonte e invalidación requieren pre-registro propio.

La muestra anterior de80 espejos completos con juicios de picos antes de A
responde a otra población/pregunta. No certifica predicción de formación ni autoriza
esta búsqueda. No se abrió aquí ningún resultado de precio.

## Aporte al referente

Separa el landmark disponible durante un intento del espejo que sólo sabemos que
existió después; así una eventual señal L2 puede falsarse sin selección retrospectiva.