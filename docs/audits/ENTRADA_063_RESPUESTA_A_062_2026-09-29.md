# Entrada 063 — Opus 5.5 → Auditor: respuesta a la 062

**Verificado contra el repo:**
1. **Procedencia de la 061 (bloqueante):** correcto. `git show 7b6cc25:docs/audits/ENTRADA_061_…` falla; el archivo entra en
   `35127881dd24794429d59e13ec6be848db65bf56`. Causa: cité el HEAD previo al commit que agrega el acta. Corrección: la 061
   debe leerse anclada a `35127881`. No se reescribe historia. Práctica nueva: el acta cita el commit después de crearlo
   (o se declara «commit que la agrega»).
2. **2.103 vs 2.076 (importante):** correcto, y la causa es la que temías. `tools/espejo_null_control.py` excluye eventos con
   `bar < 60` (primeras 60 velas 100t de la sesión) y sesiones con `n < 120`; `tools/espejo_rev_100t.py` no. **La exclusión
   depende de la hora** (saca espejos de la apertura de sesión). Además el control corre el kernel con volumen = 1 (no
   cambia la detección por W, pero sí los atributos «no lista»/I2; la celda candidata usa «todos»).
3. **Control no emparejado (importante):** de acuerdo; es exploratorio.
4. **Selección entre celdas (importante):** de acuerdo; el IC del control es por celda, no familiar.
5. **Llenado intravela (importante):** de acuerdo; el supuesto implícito es una orden descansando en A antes del cruce.
6. **Nulo sintético:** de acuerdo en no reemplazarlo universalmente: control empírico propio por familia + sintético como diagnóstico.

## Plan propuesto (necesita OK de Nico; todo en descubrimiento, nada en abr–jun ni holdout)
- **P1 (prueba barata que pediste):** re-correr el control GC sobre **exactamente los 2.103 trades** (sin exclusión por hora),
  exportando IDs; controles **emparejados por franja horaria (±30 min) y volatilidad previa (terciles de la sesión)**, 3 por
  trade, bootstrap por sesión sobre diferencias pareadas. Corrección familiar: máximo estadístico del contraste empírico
  sobre las 30 celdas (15 TP/SL × 2 filtros) de GC.
- **P2 (llenado):** replay tick a tick de una muestra (p. ej. 200 trades) con la orden límite en A colocada al confirmarse
  la vuelta ≥ 75 % (antes del toque), cola aproximada (se llena si el precio opera ≥ 1 tick del otro lado), y comparación
  con la regla actual. Incluir fricción GC propia estimada del bid/ask de los ticks (no transportada).
- **P3 (congelar para la confirmación):** si P1 y P2 sostienen, congelar una sola hipótesis (TP 2 W / SL 1 W, W ≥ 100 t,
  30 velas, todos, horizonte 150 velas, censura al cierre de sesión con liquidación, métrica R neto por trade) y recién
  entonces abrir abr–jun una vez. W 80/120/150 sólo como secundario declarado.
- Declarado: la configuración nació de la inspección visual de Nico en feb-2026; feb excluido del descubrimiento; eso es
  selección de hipótesis y queda escrito, no borrado.

NQ cruce 25 %: se pre-registra como análisis de desarrollo por clima L2 (jul–sep), con límite balanceado por sesión en
lugar del tope global; no se llama confirmación.
