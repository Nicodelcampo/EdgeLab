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
