# Encargos para Antigravity (2026-11-17)

Estado: VIGENTE — dos prompts listos para pegar en la sesión de Antigravity. Rama: `claude/vibrant-clarke-s9z6e2` (repo `nicodelcampo/edgelab`).

---

## Prompt 1 — Revisión cruzada de lo que hizo Claude sobre tu traducción de QuantLab MT5

```
Contexto: el 2026-11-16 subiste a la rama claude/vibrant-clarke-s9z6e2 (commit 74e1cdb7) la traducción Python de dos EAs de QuantLab
(SessionOpenMomentum v2.2 y QLB_K_XAUUSD_3x v1.8) en edgelab/research/quantlab_mt5/. Después Claude la midió y le hizo cambios. Necesito que
revises ese trabajo con el MT5 Tester como árbitro y me digas qué está bien, qué está mal y qué no se puede saber. Hacé `git pull` de la
rama y leé primero:
- docs/research/quantlab_mt5_eas_20261116/PREREGISTRO_MEDICION.md (con las enmiendas 1 y 2) y RESULTADO_SOM.md
- docs/research/quantlab_mt5_eas_20261116/ACTA_HOLDOUT_SOM.md
- docs/research/mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md (secciones 5–17)
- docs/research/auditoria_corridas_20261116/CRITERIOS_AUDITORIA.md
- el diff desde 74e1cdb7 en edgelab/research/quantlab_mt5/ (git diff 74e1cdb7 -- edgelab/research/quantlab_mt5/)

Qué cambió Claude y tenés que verificar contra el EA real en el Strategy Tester (no contra la traducción):
1. Llenado del stop con gap: la traducción llenaba el stop a su precio aunque la vela abriera más allá; ahora llena a la apertura.
   ¿Qué hace el EA real cuando el precio abre más allá del SL (lunes, noticias)? Mostralo con trades concretos del Tester.
2. Stop en la vela de entrada: ahora se revisa también en la vela M5 de entrada. ¿El EA puede salir por SL en esa misma vela?
3. Opciones agregadas por EdgeLab (no existen en el EA): close_weekend (cierra el viernes 15:55 NY = 22:55 servidor), rotar y permitir.
   Confirmá que con las tres apagadas el resultado de la traducción no cambió: re-corré tu suite (tests/research/test_quantlab_mt5_traduccion.py)
   y la comparación contra som_tester_trades_189.csv.
4. Corte anti-holdout: load_ohlc_data ahora corta en 2026-09-30 22:00 UTC (apertura de la sesión CME del 1-oct, edgelab/holdout.py), no en
   2026-10-01 00:00 UTC. Confirmá que ningún dato tuyo de referencia cruza esa frontera.
5. Medición: SOM se midió en NQ/ES/YM con el M1 de Dukascopy (USATECH, USA500, USA30) 2012–2026, costos de futuros, en R. Pasa en NQ, ES sólo
   desde 2020, YM no. Pedido: corré el EA REAL en el MT5 Tester sobre USATECH (o el NAS100 de tu broker) M5, 2024-01 → 2026-09-29, inputs de
   fábrica, y compará operación por operación con la traducción en el mismo período (fecha, lado, entrada, SL inicial, salida, motivo). Reportá
   el % de operaciones idénticas y explicá cada diferencia. No uses nada desde 2026-09-30 22:00 UTC.
6. QLB no se midió porque los gatillos de los slots 0 y 1 son inferidos (EMA10/50 + ATR5/ATR20 ≥ 0,85 no salen del EA). ¿Podés verificarlos?
   Si no, decilo explícitamente; no inventes reglas. Para el slot 2 (inicio de mes, sólo largos), ¿cuál es el gatillo exacto?

Hallazgos de la auditoría que tocan datos y traducciones tuyas (confirmá o refutá con evidencia):
7. En los datasets edgelab-sqx-m1 y edgelab-sqx-barras (exportados de SQX) sólo los archivos *_M1_dukas vienen en hora del servidor (NY + 7);
   USSC2000IDXUSD, DEUIDXEUR, EUSIDXEUR, GBRIDXGBP, JPNIDXJPY y LIGHTCMDUSD vienen en UTC. ¿Es así en la configuración de exportación/zona horaria
   de esos símbolos en SQX? ¿Hay otros símbolos con otra zona? Mostrá la configuración.
8. En la traducción de FUNDEDSYNCSTACK (edgelab/research/fundedsyncstack/), stop_price en las operaciones es el stop ACTIVO al salir (se mueve
   a la entrada al activarse el stop administrado de T), no el inicial. ¿El original hace lo mismo? Si es útil, proponé (sin cambiar resultados)
   una columna initial_stop_price en la salida.

Reglas: no cambies reglas ni parámetros congelados (SOM sin_finde está en holdout y forward); cualquier corrección va en un commit propio con
explicación y no se mezcla con otra cosa. Nada de dinero real. MT5 sólo lectura/Tester. Entregable: docs/research/quantlab_mt5_eas_20261116/
REVISION_ANTIGRAVITY_20261117.md con una tabla por punto (verificado / refutado / no verificable, evidencia, archivo) y los CSV del Tester que
uses, en la misma rama. Si encontrás un error de Claude, decilo directo con la operación o la línea que lo muestra.
```

---

## Prompt 2 — Búsqueda en el catálogo de StrategyQuant X

```
Objetivo: encontrar en el catálogo de StrategyQuant X (estrategias de ejemplo, plantillas, estrategias compartidas/descargables y
cualquier biblioteca que tenga la instalación en C:\StrategyQuantX145 o su sitio) estrategias COMPLETAS que puedan sumar a la cartera de
EdgeLab sin repetir lo que ya tenemos. Lo vamos a medir nosotros con nuestra cadena (costos de futuros, R, holdout); acá sólo hay que
encontrar, documentar y exportar las reglas.

Qué buscamos (prioridad en este orden):
1. Diversificación: que NO operen la apertura de NY en NQ/ES (eso ya lo cubren SOM, T, Franklin y la cartera v2). Sirven: otras sesiones (Asia,
   Londres, cierre de EE. UU.), otros activos (oro, petróleo, bonos/tasas, FX mayores, DAX), tenencia de varios días entre semana, reversión.
2. Reglas completas y legibles: entrada, salida, stop, objetivo y tamaño explícitos (pseudocódigo de SQX o export a MQL5/EasyLanguage).
   Nada que dependa de una caja negra.
3. Que operen lo suficiente: idealmente ≥ 200 operaciones en 10+ años.
4. Stop grande frente al costo: que el stop típico sea ≥ 12 veces el costo de ida y vuelta del futuro equivalente.
5. Sin nada abierto el fin de semana, o que se pueda cerrar el viernes sin cambiar la idea.

Qué evitar (ya probado sin resultado en EdgeLab): estrategias generadas por el builder de SQX (genético/aleatorio) y sus resultados (data
mining); ORB directo en NQ; mecha en VWAP con salida por EMA9; ruptura del rango de Londres en oro; gap grande de continuación; TSMOM semanal
lunes→viernes; cambio de mes; deriva nocturna simple; momentum intradía de 1 h; noche/rango 08:12 en YM. Si una del catálogo es eso, anotala
como «ya probada» y seguí.

Para cada candidata, entregá:
- nombre, origen (ruta en la instalación o URL), autor/fecha, instrumento y timeframe originales;
- reglas completas (pseudocódigo + export a MQL5 si SQX lo permite), parámetros por defecto;
- el backtest que traiga el catálogo (período, operaciones, PF, drawdown) si existe, marcando que NO es evidencia para nosotros;
- tu lectura de por qué podría funcionar (mecanismo) y cómo podría refutarse;
- a qué hueco de diversificación apunta (sesión / activo / horizonte / estilo).

Reglas de trabajo: no corras optimizaciones ni builders. Si corrés un backtest de referencia en SQX, que termine antes de 2026-09-30 y no
use datos desde 2026-10-01 (holdout). Los datos de SQX (los «@») no salen de la aplicación: exportá sólo reglas y metadatos, nunca series de
precio. No uses execute_shell/run_python del MCP de SQX. No borres proyectos ni datos de SQX. Nada de dinero real.
Entregable: carpeta docs/research/sqx_catalogo_20261117/ en la rama claude/vibrant-clarke-s9z6e2 con INDICE.md (tabla de todas las revisadas:
candidata / ya probada / descartada y por qué) y un archivo por candidata con reglas y export. Máximo 10 candidatas, ordenadas por cuánto
diversifican. Commit propio, sin tocar otros archivos.
```
