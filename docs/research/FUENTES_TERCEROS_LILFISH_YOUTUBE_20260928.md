# Fuentes de terceros: videos de «Lil Fish» (Luke) sobre trading con IA — información y adopciones (2026-09-28)

**North Star:** `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`
**Fuente:** investigación de Nico. Transcripciones y dossiers locales en `E:\youtube_analysis\dossiers\` (copia en Box `Lil_Fish_AI_Trading_Analysis`). Videos: `XLMG6-SATRk` (10.000 estrategias), `fi--3nBHsNg` (masterclass win rate), `GG_-LaLsNQk` (por qué falla el 90 %), `TtEKw8SKVKk` (prompting en vivo), `qtZmbfY3_d0` (prop farm).
**Estatus:** evidencia de terceros **no verificada** por EdgeLab. Sirve para hipótesis y priors, nunca como resultado. Los **dossiers** son una síntesis hecha por otra IA y agregan cosas que no están en las transcripciones (p. ej. «cost-in-R 0,083», «Opus 4.8», la regla exacta de «20×»): lo que no esté en las transcripciones se marca como tal.

## A. Adopciones propuestas para EdgeLab
1. **Filtro de fricción previo** a toda etapa económica: declarar y exigir costo/stop antes de correr (transcripción: estrategias con comisión < ~3 % del stop ganan más; coincide con IPC ES k 4, donde 4–8 t no pagan 2,5 t).
2. **Módulo de viabilidad prop:** Monte Carlo de P(pasar evaluación) y P(cobrar) bajo las reglas de la cuenta de Nico (límite de pérdida, trailing EOD/intradía, consistencia) para todo candidato que sobreviva a B.
3. **«Around the clock»** (el mismo setup anclado a cada media hora) como diagnóstico del atlas, contado en la multiplicidad.

## B. Información de valor (no adoptable como regla)
### B1. Priors empíricos (su estudio: 10.500 variantes, 7 años, datos **CFD**)
- NQ es el activo con más estrategias ganadoras; NY AM la mejor sesión; Asia y Londres las peores.
- A mayor temporalidad, más estrategias ganadoras (él operaba 30–60 min).
- Stops fijos ≥ estructurales; **salida por tiempo** (80 velas) entre las mejores; limit la peor entrada con fill por cruce (selección adversa).
- Las 50 familias retail con mediana negativa; «menos malas»: NR7/inside day, gap fade, ORB, gap fill; peores: barrida y recuperación de liquidez, clímax de volumen, divergencia de delta.
- La familia más rentable: **volume spike breakout** (acierto bajo, RR alto). La «#377» tiene **27 trades en 7 años**: anecdótica.
- De un backtest de un alumno (muestra chica): FOMC favorable, CPI y OPEX a evitar, noviembre-diciembre mejores, marzo-abril y agosto-octubre peores, quiebres en COVID y aranceles. Sugiere un **eje de calendario de eventos**, no reglas.

### B2. Economía de las prop firms
- Consistencia 20–40 % mata el acierto bajo con RR alto; el trailing intradía castiga la ganancia no realizada; la «cuenta real» es el límite de pérdida máximo (25k nominal ≈ 1.000 USD de riesgo).
- Diseñar al revés: reglas de la firma primero, estrategia después. Una estrategia rentable en cuenta propia puede tener 0 % de pasar evaluación (su «#1»: 14 % de acierto, rachas de 37 pérdidas).
- **Prop clustering:** la misma señal en muchas evaluaciones baratas; es un negocio con esperanza propia (costo de evaluación vs cobro), no un edge de mercado. Modelable.
- **Granja simulada:** cuentas de práctica con las mismas reglas antes de pagar evaluaciones.

### B3. Arquitectura operativa
- Señal automática → captura del gráfico por Telegram → botones comprar / limit / saltar → orden con stop, target y tamaño prefijados. El humano sólo decide sí/no; no puede romper reglas porque no está en la plataforma.
- Atribuye su mejor rendimiento al híbrido (juicio humano + ejecución automática), análogo a los juicios ✓/✗ de Nico.
- Claude no ejecuta «ahora», pero sí construye disparadores con reglas.

### B4. Datos y herramientas
- Bridge MCP de TradingView (limitado por velas), Databento (capa gratuita), CFD como relleno no idéntico.
- Sesgo de recencia («¿rentable en los últimos 6 meses?»): apunta a cambios de régimen; sugiere reportar estabilidad por año.

### B5. Señales de alerta
- Su propio **control aleatorio le ganó al 99 %** de las 10.000 estrategias: el ranking es mayormente ruido de selección.
- Búsqueda de 500 variantes elegidas por profit factor sin corrección por multiplicidad; OOS de 6 meses; CFD en vez de futuros.
- Consejo de no darle contexto a la IA para que no objete: opuesto a nuestra práctica (auditoría y objeción explícitas).
