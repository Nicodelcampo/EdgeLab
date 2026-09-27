# Idea de Nico: el espejo como intento fallido de llegar a una zona de liquidez (2026-09-27)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** IDEA. **Nada medido.** Nico pide entender y definir cada parte antes de pre-registrar.

## La idea (palabras de Nico, ordenadas)
- Un espejo (A→B→A) puede ser **un intento fallido de llegar a una zona de alta liquidez** que estaba más allá de B.
- Si el espejo se produce **justo antes** de llegar a esa zona, probar si **el siguiente intento la atraviesa más fácilmente**.
- La zona de liquidez puede ser, por ejemplo:
  - una **acumulación de picos** como la que detecta el modelo entrenado con las marcas de Nico (familia IPC);
  - una **acumulación de zonas HFT**.
- Puede haber **distintos tipos de espejo**, con características distintas.

## Piezas a definir (con alternativas, para discutir)
1. **Zona objetivo:** acumulación de picos (detector IPC congelado), confluencia de zonas HFT (cuántas, en qué ancho) u otras (POC, máximos de sesión). Cada una es una familia de zona distinta y no transporta resultados de las otras.
2. **«Justo antes»:** distancia de B a la zona (en W, en ticks o en R de la zona) y si la zona ya existía **antes** del impulso (causalidad: la zona tiene que ser conocida en A).
3. **«Siguiente intento»:** el próximo movimiento que vuelve a acercarse a la zona (¿desde A?, ¿cualquier aproximación?, ¿dentro de cuánto tiempo?).
4. **«La atraviesa más fácilmente»:** probabilidad de atravesarla, velocidad, volumen o L2 consumido para cruzarla, profundidad de penetración.
5. **Tipos de espejo:** velocidad y semejanza de la vuelta, completo o parcial, eficiencia del impulso, qué pasó en B (absorción, poca profundidad en L2, rechazo rápido).

## Mecanismos que compiten (hay que poder distinguirlos)
- **Absorción consumida:** el primer intento gastó la liquidez que frenaba → el segundo pasa más fácil (la idea de Nico).
- **Rechazo / resistencia:** la zona defiende → el segundo intento también falla (doble techo).
- **Imán:** la zona atrae igual con o sin espejo previo → el espejo no agrega nada.
Un diseño válido tiene que poder dar cualquiera de los tres resultados.

## Controles que va a necesitar
- Intentos hacia la misma clase de zona **sin espejo previo** (¿el espejo agrega algo?).
- Espejos **sin zona** cerca de B (¿la zona agrega algo?).
- Zona fantasma a la misma distancia (el control C-SZ de IPC) y pico reciente (C-SW).

## Relación con lo ya medido
- IPC 25t: las acumulaciones de picos atraen más que un nivel sin zona y más que un pico reciente (descubrimiento; replicación en curso).
- ESPEJO-SIM / ESPEJO-MACRO: completar el espejo; nunca se miró qué había más allá de B.
- L2 (ES 09-26, 78 días de Market Replay, jul–sep): permitiría ver si en B se consumió liquidez; cae en la ventana de replicación de HOLDOUT-A3.
