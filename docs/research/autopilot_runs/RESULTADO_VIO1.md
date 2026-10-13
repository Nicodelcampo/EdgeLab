# VIO-1 — zonas violeta (lógica aVolClusterPOI) sobre zonas aVolZonePOI2, MGC 25 ticks

Resultado: **NULO. No hay distancia D con ventaja. Sin hit, sin consumo de alfa.**
Datos: MGC 6 contratos, sesiones 2025-10-08..2026-09-30 (holdout ≥ 2026-10-01 no leído). Pre-registro `docs/research/autopilot/drafts/VIO-1.md`, 36 configuraciones (D ∈ {10,16,20,30,40,60} × TP a ∈ {D/2,D} × SL b ∈ {D/2,D,2D}), costo 6,8 ticks.

## Pregunta
Tras alejarse de una zona violeta y volver a distancia D, ¿llega a la zona antes de alejarse otros b ticks más que lo que da el azar (P(TP) > b/(a+b))? ¿Hay TP/SL con esperanza neta positiva?

## Resultados
- Descubrimiento (60 % de sesiones, 126 sesiones): máximo z = 2,17 vs. cuantil 95 del nulo (máx. sobre 36 configs) = 2,77 → **p = 0,23** (Holm sobre 4: 0,92). No significativo.
- Replicación (40 % final) de las 3 mejores: bruto −0,01 a +0,64 ticks por evento, **neto −6,2 a −6,8 ticks** (costo 6,8). Ninguna replica.
- Tabla descriptiva: P(TP) violeta ≈ break-even en todas las configs (p. ej. D=20 a=b: 0,493 vs 0,500; D=40 a=b: 0,503 vs 0,500). Esperanza bruta máxima en violeta: +1,0 tick (D=40, a=b=20) — 7 veces menor que el costo.
- Control (zonas que se alejaron pero no violeta, ~820 eventos por config): brutos algo mayores (hasta +1,9) pero también muy por debajo del costo y sin significancia; no hay diferencia violeta-vs-control útil.
- Eventos: ~11 por sesión en violeta (mucho volumen, nada de borde): el costo domina.

## Lectura
La zona violeta no da retorno hacia la zona estadísticamente distinguible de un paseo aleatorio en MGC 25T, a ninguna distancia probada, ni simétrica ni asimétrica. Con 6,8 ticks de fricción, el mejor bruto no alcanza. Lo que se ve en el gráfico es compatible con sesgo de selección visual.

## Notas de calidad
- Violeta con umbral adaptativo: en MGC 12-25/02-26 casi todas las zonas "alejadas" salen violeta (405/409, 188/191) por el umbral de arranque 0,35 (calentamiento <20 resueltas); el resto de contratos ~65–70 %. Puede diluir la señal en la primera parte. Variante con umbral calibrado y descarte del calentamiento: no probada (sería un trial nuevo, requiere pre-registro).
- Datos crudos MGC: timestamps "UTC declarados por exportador, no certificados"; bid/ask crudos poco fiables (no usados).
- Un tick mal enraizado del autopilot (`--root .`) lanzó una corrida duplicada de slot-1 en Kaggle; la ignorada, no entra al registro.
