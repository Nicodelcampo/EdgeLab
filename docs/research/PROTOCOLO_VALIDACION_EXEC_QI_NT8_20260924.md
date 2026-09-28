# Protocolo: validación de fills de EXEC-QI en NT8 (2026-09-24)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Familia:** EXEC-QI (`MANIFIESTO_EJECUCION_QI_L2_20260924.md` §10). **Pedido de Nico:** "escribí el script de NT8 y el protocolo".

## Qué se valida y qué no

El resultado de EXEC-QI sale de un **modelo** de cola (pesimista) sobre el libro L1 de NT8. Este protocolo lo contrasta con **otros motores de fill**. Ninguno de los disponibles hoy es la cola real del exchange:

| Cuenta | Quién decide el fill | Qué mide |
|---|---|---|
| **Playback101** (Market Replay de NT8) | simulador local de NT8, sobre datos grabados | qué tan optimista o pesimista es NT8 frente al modelo, **en días donde también tenemos el L2** (comparación exacta en los mismos instantes) |
| **Sim101** (demo de NT8, datos en vivo) | simulador local de NT8 | lo mismo, pero en vivo |
| **Cuenta de evaluación de Lucid** | simulador del servidor del prop (Tradovate o Rithmic) | un motor **independiente** del nuestro y del de NT8 |
| Cuenta real con micros (MNQ/MES) | **el exchange** | la única validación definitiva. Cuesta plata: decisión de Nico, más adelante |

**La estrategia sólo necesita L1** (bid/ask y sus tamaños). Por eso corre igual en la conexión de NT8 (con L2) y en la de Lucid (sin L2). El L2 hace falta después, para comparar contra el modelo en los mismos instantes. Se baja con el Replay Downloader de ese día.

## El script: `nt8_tools/EdgeLabExecQIProbe.cs`

Copiado a `Documents\NinjaTrader 8\bin\Custom\Strategies\`. Es una **estrategia**, no un add-on, y se compila con F5 en el editor de NinjaScript.

**Experimento aleatorizado:** cada 90 s (+ jitter de 0 a 30 s), si está flat:
1. sortea la dirección (compra o venta);
2. sortea la política: **A** (orden a mercado) o **P** (límite en el mejor precio propio; si no se llena en 30 s, cancela y cruza);
3. sale a mercado 60 s después del fill.

Política y dirección **no** dependen del QI. El QI se anota y se usa después para condicionar. Así la comparación A vs P no tiene sesgo de selección.

**Seguridad:**
- 1 contrato.
- Sólo corre en cuentas listadas en `AllowedAccounts` (por defecto `Sim101;Playback101`). Para Lucid hay que **agregar la cuenta a la lista y poner `AllowNonSimAccount = true`**.
- Topes: `MaxDecisions` (400) y `MaxLossTicks` (400).
- No decide con un spread mayor a 12 ticks, ni entre 17:50 y 19:10 ART (pausa de CME).
- Sale al cierre de sesión.

**Salida:** `Documents\NinjaTrader 8\EdgeLab\execqi\<cuenta>_<instrumento>_<fecha>.csv`, una fila por decisión.

**Análisis:** `tools/exec_qi_nt8_compare.py --csv "<ruta>\*.csv" [--base NQ_09-26]`.
- **Ahorro realizado:** A − P por tercil de QI, con IC por día.
- Con `--base`, si existe el L2 del día: acuerdo de fill y diferencia de precio contra el modelo pesimista en los **mismos** instantes.

## Etapas

**Etapa 1: Playback (hoy, sin riesgo, rápido).**
- **Qué preparar:** copiar de vuelta `E:\nrd_archive\NQ 09-26\20260820.nrd` a `Documents\NinjaTrader 8\db\replay\NQ 09-26\`. Es un día de `P-NQL2-EXP`, con L2 ya convertido.
- **Cómo correrlo:** conexión Playback, 20/08, `NQ 09-26`, gráfico de 1 minuto. Estrategia `EdgeLabExecQIProbe` en `Playback101`, velocidad de 10× a 50×.
- **Qué deja:** ~800 decisiones en un día completo y la comparación exacta contra el modelo.

**Etapa 2: en vivo, en paralelo (una sesión RTH completa o más).**
- Mismo instrumento y mismo horario en **Sim101** y en la **cuenta de Lucid**. En Lucid, **MNQ** (micro) para no consumir el drawdown de la evaluación.
- Al día siguiente se baja el L2 de ese día y se corre `--base` para comparar los dos motores contra el modelo.

**Etapa 3 (decisión futura de Nico):** cuenta real con micros. Es la única que valida la cola de verdad.

## Criterios (fijados ahora)

- **El modelo es conservador** si, en los mismos instantes, el fill de P del modelo ≤ el fill de P de cada motor, y el ahorro realizado A − P de cada motor ≥ el ahorro del modelo (dentro del IC).
- **El modelo es optimista** (alerta) si algún motor da un ahorro realizado menor que el del modelo, con el IC entero por debajo. En ese caso EXEC-QI se reescala con el motor más pesimista antes de usarlo como costo.
- **El orden por QI** (el ahorro con "contra" mayor que con "a favor") tiene que aparecer en los motores. Si no aparece en ninguno, la parte condicional de EXEC-QI queda en duda.

## Riesgos y advertencias

- **Lucid:**
  - el experimento pierde en promedio ~medio spread por operación más comisiones;
  - las salidas a 60 s agregan varianza (en MNQ, ~USD 15 de desvío por operación).
  - Con 200 operaciones, **revisá el límite de pérdida diaria y las reglas de la evaluación** (consistencia, mínimo o máximo de operaciones, prohibición de scalping o de automatización). Ajustá `MaxLossTicks` y `MaxDecisions` a esas reglas.
  - Si las reglas de Lucid prohíben estrategias automáticas o tenencias tan cortas, **no se corre ahí**.
- **Motores simulados:** ninguno modela la cola real. Validan la **dirección** y el **orden de magnitud**, no el número final.
- **Etapa 2 en vivo:** usa días que después hay que bajar como L2. Caen en el tramo de desarrollo (hasta el 31/10) si se corre antes de noviembre. Después de esa fecha sería holdout L2: **no correr la etapa 2 en noviembre o diciembre** sin decidirlo antes.

## Decisión de Nico (24/09): no se corre en Lucid

Riesgo de romper las reglas de la evaluación. Queda **sólo NT8**:
- **Playback101** como etapa principal: varios días con L2 ya bajado, comparación exacta contra el modelo.
- **Sim101** en vivo como chequeo de latencia y feed en vivo. Es el **mismo motor** que Playback, así que no aporta un motor independiente.

Se pierde el motor independiente del prop. La validación de la cola real sigue siendo la etapa 3 (cuenta real con micros).

## Resultado de la etapa 1, día 1: Playback NQ 09-26, 20/08/2026 (24/09)

Datos: `artifacts/exec_qi_nt8/Playback101_NQ_SEP26_20260820.csv`, 684 decisiones (350 A, 334 P), velocidad 500x. Las decisiones se separaron por una mediana de 106 s, sin huecos salvo la pausa de CME y el reinicio por el tope de pérdida. Comparación: `artifacts/exec_qi_nt8/compare.json`. Bloque del bootstrap: la hora, porque hay menos de 5 días.

| Qué | NT8 (Playback) | Modelo pesimista, mismos instantes |
|---|---|---|
| Fill de P antes de T = 30 s | **90 %** | 79 % (acuerdo por decisión: 87 %) |
| Precio de P (NT8 − modelo, en la dirección) | **−0,59 ticks**: NT8 llena mejor | — |
| Precio de A (NT8 − cotización en t0) | **+0,23 ticks**: NT8 llena peor, ~0,5 s después | — |
| Ahorro A − P realizado | +0,93 [−0,91; +2,36] | −0,43 (ese día el promedio de la grilla completa fue +0,09) |

**Lectura (un solo día):**
- **El modelo es conservador frente al motor de NT8**, en los dos sentidos:
  - NT8 llena más la orden pasiva y a mejor precio (no tiene cola);
  - NT8 cobra más en la orden a mercado.
- Juntos, **NT8 favorece a la orden pasiva ~0,8 ticks más que nuestro modelo**. Se cumple el criterio "modelo conservador" en fill (79 % ≤ 90 %).
- **El ahorro realizado no se puede juzgar todavía:** el IC es de ±1,6 ticks con un día. Hacen falta unos 8 a 10 días para bajarlo a ±0,5.
- **El orden por QI no se puede ver:** en NQ el tope tiene 1 a 3 contratos, el QI casi siempre da 0 y 573 de 684 decisiones cayeron en "neutral".
- **Paridad** de `simulate_passive` con el loop de `exec_qi.py` en el mismo día: 0,13 ± 0,20 contra 0,09. Coinciden.

**Siguiente:** 8 días más de NQ (21, 22, 23 y 28/07; 5, 6, 13 y 18/08, todos de `P-NQL2-EXP`), con la misma configuración, `MaxLossTicks` = 100000 y `MaxDecisions` = 2000.

## Evidencia externa (búsqueda del 24/09, a pedido de Nico: "¿no hay manera de investigar eso en internet?")

- **Motor de NT8, según el soporte de NinjaTrader:** para una compra límite en el bid, anota el tamaño del bid (X), sigue los trades en ese precio (Y) y llena cuando Y > X. Suma componentes aleatorios y demoras simuladas, y Playback usa la misma configuración que Sim101. **En la regla es igual a nuestro modelo pesimista**, pero:
  - usuarios reportan fills "on touch" en la demo en vivo;
  - también reportan que muchas órdenes que en la demo se llenan **no se llenan en cuentas reales o de prop**.

  Encaja con lo medido: NT8 llena el 90 % y nuestro modelo el 79 %. **Conclusión:** la demo de NT8 es optimista frente al mercado, y el modelo pesimista es el lado correcto para usar como costo.
- **Literatura:**
  - el valor de la posición en la cola es del orden de medio spread en activos de tick grande (Moallemi y Yuan 2016, calibrado en NASDAQ);
  - la probabilidad de fill depende de la posición en la cola y del estado del libro (Lokin y Yu 2024; trabajos con MBO de CME).

  No se encontraron **números públicos de fill para NQ o ES** que reemplacen una medición propia. Harían falta datos MBO de CME (Databento), que hoy no están disponibles.
- **Qué no puede resolver internet:** el fill de *nuestras* órdenes, con nuestra latencia y nuestro broker. Eso sigue saliendo sólo de órdenes reales (etapa 3).

Fuentes: foro de soporte de NinjaTrader (hilos 97305, 104492, 1121714, 1323152, 1255422); Moallemi y Yuan, *A Model for Queue Position Valuation in a Limit Order Book* (SSRN 2996221); Lokin y Yu, arXiv 2403.02572.

## Resultado de la etapa 1 cerrada: 3 días de Playback NQ (20/08, 21/07 y 22/07), 24/09

Datos: `artifacts/exec_qi_nt8/Playback101_NQ_SEP26_all.csv`, con 2.238 decisiones después de descartar 2 duplicadas por re-arranque. Comparación: `artifacts/exec_qi_nt8/compare.json`. El IC usa bootstrap por bloque de hora porque hay menos de 5 días. Por decisión de Nico, la etapa se corta en 3 días: alcanzan para el fill.

| Qué | NT8 (Playback) | Modelo pesimista, mismos instantes |
|---|---|---|
| Fill de P antes de T = 30 s | **90 %** | **79 %** (acuerdo por decisión: 87 %) |
| Precio de P (NT8 − modelo, en la dirección) | **−1,20 ticks**: NT8 llena mejor | — |
| Precio de A (NT8 − cotización en t0) | **+0,39 ticks**: NT8 llena peor | — |
| Ahorro A − P, todos | **+1,49** [0,96; 2,17] | **+0,18** |
| Ahorro con QI "contra" / "neutral" / "a favor" | +1,89 / +1,60 / +0,03 | +0,41 / +0,13 / +0,39 |

**Conclusiones:**
1. **El modelo pesimista es conservador frente a NT8**, en fill y en precio. Se cumple el criterio "modelo conservador".
2. **El simulador de NT8 infla la ventaja de la orden pasiva en ~1,3 ticks por lado en NQ** (≈ USD 6,5 por lado), y lo hace por los dos lados: llena mejor la pasiva y peor la agresiva. Coincide con los reportes de usuarios citados arriba.
3. **Lección para todo el proyecto:** ningún backtest ni ninguna prueba en demo o Playback de NT8 con órdenes límite es admisible como costo sin corregirla. El costo oficial es el del modelo pesimista (`tools/exec_qi.py`).
4. **Orden por QI:** en NT8 aparece monótono (+1,89 > +1,60 > +0,03). En el modelo, en estos mismos 2.238 instantes, no se ve, porque "contra" y "a favor" tienen n chico (~180 y ~220). En la grilla completa sí era monótono. Nada de esto cambia la regla.
5. **Lo que sigue sin medirse:** el fill real (etapa 3, órdenes reales) y la sesión en vivo en Sim101, que Nico descartó por ser el mismo motor.
