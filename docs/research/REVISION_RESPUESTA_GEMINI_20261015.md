# Revisión de la respuesta de Gemini (corredor y grilla) — 2026-10-15

Estado: REVISIÓN — lectura de dos documentos y verificación puntual contra datos y código; no se re-ejecutó su kernel
Fecha: 2026-10-15
Familia / módulo: EXP-CORRIDOR y EXP-REV-GRID
Objetos: `RESPUESTA_GEMINI_REVISION_CRUZADA_CORREDOR_20261015.md` y `AUDITORIA_Y_PROPUESTA_VIABLE_EXP_REV_GRID_MULTIESCALA_20261015.md` (Drive `resultados_claude_local`).

## Veredicto
**Aceptables en lo central, con cinco reservas.** Confirma los 14 puntos sobre el corredor, reproduce la Adenda D (N=3.456, E_all −2,45, ΔE por herramienta) y coincide en que `HA` no es operable neta ni justifica abrir NQ/YM. En la grilla acierta en lo económico (etiqueta de 8 ticks inviable; 32 vs 32 baja el equilibrio a 55,5 %), pero propone congelar varias decisiones que todavía no tienen soporte medido.

## Qué verifiqué
- `p_eq = (Y+F)/(X+Y)`: 8/8 → 72,16 %; 32/32 → 55,54 %; 48 vs 32 → 44,4 % (contra un nulo browniano de 40 %). Correcto. Mi etiqueta de 8 ticks era mala: "X ≥ 2×fricción" no basta.
- `kernel_sources` existe en `tools/kaggle_drive_bridge.py` (líneas 361, 554): su solución para reutilizar la caché privada dentro de Kaggle es técnicamente posible. No la probé.

## Reservas
1. **"Reproducción bit a bit" prueba aritmética, no validez causal.** Usa mi script y mi tabla, y ésta sale de su propio código de carreras y detector. Confirma que no hay errores de cuenta; no valida el detector ni las carreras con una implementación independiente.
2. **Dos detalles menores que no verifico.** Su "matiz de la línea 63" no coincide: esa línea es `def session_blocks`, y `session_id` es un índice secuencial contiguo (1–299), no `trade_date*10+cid`; el embargo de ±1 sí es de una sesión. Y su bruto "~+3,8 ticks sobre resueltos" no lo reproduzco: calculo **+5,27** sobre 668 resueltos (el neto sobre todos, +1,54, sí coincide).
3. **32 vs 32 ticks a 300 s no está probado como viable.** Subir el recorrido baja el acierto necesario, pero mover 8 puntos de ES en 5 minutos es raro: es probable que la mayoría sean timeouts (en el corredor, con barreras de ~43 ticks, ya eran 55–61 %). Antes de congelarla hay que medir el soporte (qué fracción resuelve) en el calendario de entrenamiento y declarar una regla de parada; ese conteo ya usa precios y requiere OK.
4. **Particiones muy chicas para sintonizar y calibrar.** Tuning = 11 días hábiles y calibración = 12, con assessment ≈ 40 sesiones en un descubrimiento de 181. La selección de hiperparámetros y la calibración sobre ~10 sesiones son frágiles y el MDE del assessment es grande: hay que calcularlo antes. La confirmación en NQ exige reinterpretar barreras en su propia fricción (5,7–6,2 ticks) y no transporta costos.
5. **"Más resolución sin más parámetros" está sobrevendido.** `AdaptiveAvgPool2d((2,4))` mantiene fija la cabeza, pero también **promedia la resolución espacial fina a 2×4** antes de decidir: los nodos de volumen de 2–4 ticks que quiere distinguir se pierden en ese pooling. Hay que probar una cabeza con más resolución (por ejemplo 4×8) o canales de coordenada, como ablación. Además, la tabla de escalas es inconsistente (S3 ±192 a ±256).

## Lo que queda abierto
- Semillas: Gemini usa 3 y mi propuesta pedía ≥ 5; hay que decidir.
- La escalera M0–M5 es la pista de ticks; el panel decidido por Nico (DeepLOB, Transformer, fundacionales, RL) corre sobre la pista de L2 y no aparece integrado.
- Los 5 puntos que pide congelar necesitan el OK de Nico y, antes, el conteo de soporte (reserva 3), el MDE (reserva 4) y la regla de multiplicidad.

*Aporte al referente:* confirma por segunda lectura que el corredor no tiene efecto neto, y evita congelar una etiqueta y una partición cuya viabilidad económica y potencia todavía no están medidas.
