# Frentes abiertos (2026-11-19)

Estado: VIGENTE — tablero de frentes de la sesión de Claude; pedido de Nico: «no olvides ninguno de los frentes, realizá todos … sé riguroso
en los controles y que pasen por toda la cadena, sin falsos positivos». Se actualiza en el mismo commit que cambie un frente.

| # | Frente | Estado | Próximo paso | Bloqueo |
|---|---|---|---|---|
| 1 | EXTERNAS_A5 (114 variantes del catálogo externo) | CERRADO: 110/114 descartadas por fricción; 4 Dual Thrust con bruto real y neto ≈ 0 (DESC de Gemini), REP sin potencia (0,01) | — | — |
| 2 | FLUJOS-MACRO (FM1–FM8, Carril 1) | HECHO: FM1/FM2 bruto real, neto negativo; REP sin potencia (K49); K53 corregido | FM7: causa raíz K54 (sin VIX en el kernel de ticks); guardas en código; sin cambio de veredicto | — |
| 3 | Carril 2 (11 estrategias multi-sesión; **no operables en LucidFlex: cierre obligatorio 16:45 ET, sin overnight**: IBS, Double Seven, overnight, Turnaround Tuesday, cambio de mes, eVRP, VIX alto, pre-FOMC, Dynamic Breakout II, rotación ES/GC) | motor existente y calibrado (`sqx_catalogo.simular`, K28); diseño en `carril2_20261119/DISENO.md` con regla de partición para posiciones largas | lote 1: 0/8 (SIN_EVIDENCIA); lote 2 (pico de VIX, P80, eVRP, z-score, DBO, rotación): 0/12, pico y compresión de vol con p ≈ 0,02 sin pasar BH; faltan overnight (motor) y pre-FOMC (potencia) | CERRADO para Lucid (sin overnight); sólo cuenta de broker |
| 4 | T-NQ + R (AtrPhase) como canasta candidata | T REGIMEN_ROBUSTO; R REGIMEN_ROBUSTO en R; vigilancia de T escrita | REGIMEN-FORWARD pre-registrado (canasta T+R, vigilancia); prueba 2 resuelta: build del vendedor 2026-10-29 → sólo el forward es limpio | esperar datos sellados nuevos |
| 5 | A20 desde 2017 | A20-REGIMEN: INTERMEDIO (PBO 0,39; 2017–2021 0/81; ES negativo): efecto sólo 2022+ | sólo forward con vigilancia | — |
| 6 | SOM y Franklin: mejorar la curva | señales robustas; MEJORA-SF: Franklin en días volátiles y SOM-fricción pasan DESC; REP y otros índices sin potencia (K49) | curva bruto–stop: HECHA (descriptivo, grilla de régimen): bruto fijo en puntos, el stop no es palanca; tamaño sin sesgo K52: HECHO, no mejora (las ganancias de contrato fijo eran K52); queda sólo forward con vigilancia | potencia histórica insuficiente |
| 7 | RQ5/RQ6 (Roboquant) | bruto estable sin neto; el stop no es palanca | tamaño sin sesgo K52: HECHO, no mejora; cerrado | — |
| 8 | Guardas nuevas | K50, K51, K53 en código y guía | — | — |
