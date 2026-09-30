# GC C2 y presión dentro del espejo — target-free

## Decisión de investigación
Se continúa con C2_EXACT4_DENSAS por soporte de frecuencia y disponibilidad de features, NO por rendimiento. No modifica C0 ni el visor calibrado por Nico. Perfil congelado: cuatro picos exactos disjuntos, w1, gap23, step49, pull19, confirmación28 ticks, dmax1.000.000, total_min0 y step_min0. Los cuatro miembros se congelan al disparo: un quinto pico no rescata ni prolonga esa zona.

## Frecuencia
Recuento independiente del ZIP privado original: 1.817 zonas en 21 session_ids del censo de febrero; 20 cumplen ≥4. Mínimo positivo20/máximo152. 20260201 figura con cero: se conserva; integridad/cobertura del bundle de esa entrada no certificada. No se garantiza ≥4 en cada día futuro ni ≥4 eventos con L2 fresco o independientes. El censo histórico no certifica publicación raw.

## Soporte de presión (captura May31, GC08-26)
Plan escrito antes del cómputo de este gate: book estructural PASS, publicación estrictamente anterior por fila Y tiempo, snapshot ≤1.000ms y ventana histórica completa de10s. Las dos primarias son QI en touch y OFI de extremos de ventana normalizado por profundidad touch, ambas orientadas por dirección. No son un clasificador ni se suman a un score aprendido.

- C2:10 candidatos,10 con ambas primarias/frescura válidas. Signos:1 ambas a favor,1 ambas en contra,4 discordantes y4 con alguna neutral. QI tiene5 valores distintos; OFI10.
- Espejo50%:58 cruces prospectivos;53 válidos y5 excluidos por edad>1s. En53:14 ambas a favor,2 en contra,14 discordantes y23 con alguna neutral. QI13 valores distintos; OFI38.
- Se retienen33 observaciones no prospectivas y todos los161 receipts de intentos; no se convierten en cero o pérdidas. No se agregan los cohorts como muestras independientes.
- Baseline sólo histórico: movimiento, recorrido, cantidad y volumen de prints en10s; cotización y distancia a nivel conocido. Auditoría independiente contra raw de101 filas PASS;9 tests PASS.

## Lectura y límites
Hay un panel causal para evaluar más adelante si L2 agrega información al precio. Aún NO sabemos si define predictibilidad dentro del espejo: no hay etiquetas posteriores, modelo, probabilidades, retorno, P&L, fills, potencia ni estimación de efecto. No se interpreta concordancia de signos como éxito. Una captura expuesta, no58 sesiones ni58 trades iid.

Permanece Junio15 ABSTAIN por cinco timestamps de tape discrepantes; sin nearest/rounding. No se toca holdout. Para prueba predictiva: manifiesto con resultado y horizonte exactos, baseline precio, split por sesiones, costos y multiplicidad, más datos emparejados; OK separado de Nico antes de abrir resultados.

## Entregables
Código `tools/gc_pressure_panel.py`; tests `tests/research/test_gc_pressure_panel.py`; evidencia agregada `artifacts/gc_pressure_c2_20260930/evidence.json`; config resuelta en el mismo directorio. Datos, precios y panel privado quedan fuera del repo. Acta y MEDIDO/NO MEDIDO se publican juntos.
