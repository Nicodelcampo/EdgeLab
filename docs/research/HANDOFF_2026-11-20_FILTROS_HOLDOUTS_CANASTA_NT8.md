# Handoff 2026-11-19/20: Lucid, PICOS-DEFENDIDOS, lo descartado por épocas, RQ5, A20, filtros de contexto, holdouts, correlación y NT8

Estado: VIGENTE — punto de entrada de esta etapa, escrito para seguir sin la conversación.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Rama:** `claude/vibrant-clarke-s9z6e2`; PR borrador [Nicodelcampo/EdgeLab#202](https://github.com/Nicodelcampo/EdgeLab/pull/202). `foundation`
  recibió lo anterior por [Nicodelcampo/EdgeLab#201](https://github.com/Nicodelcampo/EdgeLab/pull/201).
- **Seguimos con 0 edges promovidos.** Nada habilita tamaño real. Operar con dinero real lo decide Nico.

## 1. Qué se hizo y qué dio (en orden)

| # | Trabajo | Resultado | Dónde |
|---|---|---|---|
| 1 | LucidFlex con la guía de RobotEdge: EV por examen, tiempos para pasar o quemar, máximo 5 fondeadas, cumplimiento de reglas | Cascada por cuenta; prohibido cubrirse entre cuentas o contratos correlacionados; plano a las 16:45 ET | `lucid_guia_20261119/` (RESULTADO, CUMPLIMIENTO, RESULTADO_PERIODO_Y_MINIS) |
| 2 | Plan de Lucid que más gana y su repetición en el holdout | Ningún plan llega a P(neto 12 m > 0) ≥ 0,8. Plan A (150K, T+R+ZB, 9 MNQ) y B (50K, T+R, 5 MNQ). En el holdout, T sola pierde y con R y Z sin stop A gana +10,9k | `lucid_plan_20261119/` |
| 3 | Auditoría de PICOS-DEFENDIDOS (otro agente) y conducción del embudo | ES: SIN_CANDIDATAS (réplica −0,141 R con potencia). NQ: una sola variante nominada (≈ 36 operaciones), OOS −0,04 NO_CONCLUYENTE; en CONTEO del holdout, 16 de 150 operaciones | `agente/AUDITORIA_PICOS_DEFENDIDOS_20261119.md`, `picos_defendidos_20261119/` |
| 4 | Revisión de lo descartado por promedios de época (la fricción relativa bajó ≈ 2018) | RQ5 neto 2018–25 +0,05; A20 positiva desde 2022; FM2/RQ6/FM1 por época | `REVISION_DESCARTADAS_20261119.md` |
| 5 | RQ5-REGIMEN: grilla de 324 celdas, cinco índices, calibración M1 contra ticks | **REGIMEN_ROBUSTO**: fábrica +0,050 R (p 0,045), 310/310 celdas calibradas positivas, 10/10 vecinos, NQ/ES/RTY positivas (YM −0,022), 54,7 ops/mes | `rq5_regimen_20261119/RESULTADO.md` |
| 6 | Holdout A5 de RQ5 (hasta 2026-09-30, autorizado por Nico con K27 levantada) | **NO_CONCLUYENTE**: +0,027 R, n 1.871, p 0,23, Fisher 0,057; NQ +0,077 | `rq5_regimen_20261119/RESULTADO_HOLDOUT.md` |
| 7 | A20-MULTIACTIVO (YM, RTY, EMD) | **NO_TRANSFIERE** (−0,03 a −0,08 R; 0/24 vecinos) | `a20_multiactivo_20261119/` |
| 8 | Holdout A5 de A20 NQ | No limpio (A20-REGIMEN ya usó esos meses); sin apertura | `a20_regimen_20261119/NOTA_HOLDOUT_A5.md` |
| 9 | FILTROS-CONTEXTO: VIX, VVIX, GEX, DIX, SKEW, VIX9D/VIX y COT × A20, T, R, Z-banda, RQ5 (35 pruebas) | **SIN_FILTRO**: 0/35 por BH (p mín. 0,023, ajustada 0,59). T y RQ5 planos; A20 peor en días calmos de gamma larga (un solo eje, sin significancia) | `filtros_contexto_20261120/RESULTADO.md` |
| 10 | Holdout terminal de A20 NQ (1-oct → 16-nov; pedido de Nico, K27 y «una apertura por familia» levantadas) | **NO_CONCLUYENTE**: n 29, +1,10 R/op, p 0,072, potencia 0,08. **A20 es sólo corta**: −1 R por cada 1 % de NQ, intercepto +3 a +5 R/mes | `filtros_contexto_20261120/RESULTADO_HOLDOUT_TERMINAL_A20.md` |
| 11 | CANASTA-CORRELACION | T, R, Z-banda y RQ5 NQ diversifican (mensual −0,05 a 0,27). **T+R+ZB+RQ5 NQ: +4,98 R/mes, t 5,17, 71 % meses +, caída −23 R.** A20 no cubre: correlación +0,25 a +0,38 con las demás y caída −90 R | `canasta_correlacion_20261120/RESULTADO.md` |
| 12 | Estrategias NT8 | `nt8/strategies/EdgeLabRQ5.cs` y `nt8/strategies/EdgeLabCanasta.cs` (RQ5 + guarda de cuenta). T, Z y A20 **no** se portaron (ver §3) | `nt8_rq5_20261120/LEEME.md` |

## 2. Errores de la etapa y cómo quedaron
- **REP de RQ5 mirada** aunque el acta de ROBOQUANT decía que no: se declaró contaminada en el pre-registro de RQ5-REGIMEN.
- **Fin de la operación de RQ5** usaba la última vela de la sesión (mirada adelante): el preflight de causalidad la cazó; se pasó a una
  salida por reloj y se recalibró.
- **«8 vecinos» eran 10:** se aclaró en la herramienta antes de ver resultados (umbral ≥ 8/10).
- **EMD sin spread medido:** costos estimados declarados (K33) y fuera de la calibración.
- **`_replay` de Lucid no respetaba el tope de 5 fondeadas:** corregido con un estado «aprobada en espera».
- **Cadena de hash del registro global** rota en merges: se re-encadenó con `TrialRegistry.ensure` (verify válido).
- **Pre-registro de CANASTA-CORRELACION** decía 91 meses: son 70 (DESC + REP); corregido antes de leer.

## 3. Por qué T, Z y A20 no tienen estrategia NT8 propia
- Su lógica (`edgelab/research/fundedsyncstack/`) es una traducción del IL desensamblado de FundedSync, un producto comercial con licencia
  por huella de hardware (`fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md`).
- Reimplementarla como estrategia propia la haría correr sin esa licencia. Eso no se hace.
- **Cómo se usan:** se corren en el producto original con su licencia.
  - `EdgeLabCanasta.cs` agrega RQ5 y protege la **cuenta entera** (DLL, piso y plano a las 16:45 ET), incluidas las operaciones de FundedSync
    en la misma cuenta.
  - `EdgeLabAtrPhaseStop.cs` (R con stop de catástrofe) es anterior a esta etapa y no se tocó.

## 4. Decisiones abiertas para Nico
1. **Forward de la canasta T + R + Z-banda + RQ5 NQ:** la mejor combinación medida en desarrollo. RQ5 todavía no está en el forward.
2. **A20:** ¿fuera de la canasta, o adentro con un tamaño mucho menor? Ese tamaño no está medido.
3. **Paridad NT8 de RQ5:** correrla en Market Replay de NQ entre 2025-01 y 2025-07 y comparar contra
   `nt8_rq5_20261120/RQ5_NQ_REFERENCIA_PARIDAD.csv` (88 señales) antes de usarla en sim.
4. **PICOS-DEFENDIDOS-NQ:** el conteo del holdout sigue al ritmo de los datos (≈ 10 operaciones por mes).

## 5. Qué no repetir (factores nuevos)
- **F-FILTROS-CONTEXTO-SIN-FILTRO:** VIX, VVIX, GEX, DIX, SKEW, VIX9D/VIX y COT no filtran T ni RQ5.
- **F-A20-SOLO-CORTA-HOLDOUT-TERMINAL:** leer A20 siempre junto con el retorno de NQ.
- **F-CANASTA-T-R-Z-RQ5-DIVERSIFICA.**
- **F-RQ5-HOLDOUT-NO-CONCLUYENTE.**
