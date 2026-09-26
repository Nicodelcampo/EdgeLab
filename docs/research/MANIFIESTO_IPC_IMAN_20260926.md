# Manifiesto IPC: ¿las acumulaciones de picos consecutivos son imanes? — ES y NQ, exploración, 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PROPUESTO. Mira retornos: **STOP**, corre sólo con el OK explícito de Nico a este manifiesto.
**Diseño y decisiones:** `docs/research/DISENO_IMAN_PICOS_20260926.md`. Herramienta a escribir: `tools/ipc.py`. Ledger propio: `artifacts/hippocampus/ipc_20260926.jsonl`.
**Regla de alcance:** conclusiones por celda (INFO+ / INFO− / SIN_INFO con MDE / SIN_POTENCIA) y lista de lo no medido.

## 1. Registro de la familia IPC
- **Objeto:** acumulación de picos consecutivos según la regla de Nico: highs donde cada pico no supera al anterior, o lows donde ninguno perfora al anterior. Detector `tools/peaks_rule.py`, parámetros **congelados**:
  - **ES:** w 2, separación ≤ 60 velas, escalón ≤ 2 t, retroceso ≥ 2 t, tope de pendiente = p90 de las marcas;
  - **NQ:** w 1, separación ≤ 30, escalón ≤ 14 t, retroceso ≥ 7 t, tope p90 de las marcas de NQ.
- **Validación del detector (target-free, sobre juicios de Nico):**
  - ES: **69 %** de precisión fuera de muestra (100 juicios);
  - NQ: 40 % sin filtro, fuera de muestra; el filtro ≥ 7 picos y ≥ 40 velas llega a 70 % en muestra y **todavía no está validado**.
- **Justificación económica:** una serie de máximos que no se superan deja stops acumulados justo por encima del último pico, y uno de mínimos, justo por debajo. Si esa liquidez atrae al precio (para llenar órdenes grandes o barrer stops), cuando el precio se aleja debería volver al nivel con más frecuencia que a un nivel cualquiera a la misma distancia.
- **Cómo podría refutarse:** la tasa de regreso al nivel no supera a la del **mismo cálculo hacia un nivel sin zona** (misma distancia relativa, misma hora, mismo estado y actividad, en otra sesión).
- **Antecedente que obliga a este control:** «BigTrap2 como imán» murió el 13/08 (F2.8) justamente contra un control sin zona con la misma geometría.

## 2. Espacio de eventos (enumerado antes de elegir)
creación · alejamiento · primera aproximación · primer toque · toque n-ésimo · ruptura · vencimiento · estado continuo.
**Se congela:** **alejamiento → ¿toca el nivel antes de alejarse otro tanto?** Es la definición de imán acordada con Nico. El estado continuo («zona virgen a distancia x») queda anotado como no medido.

## 3. Definiciones (causales)
- **Creación:** la vela en que se confirma el pico que completa el mínimo de picos (vela del pico + w).
- **Nivel:** último pico (**primario**) o primer pico (**secundario**).
- **Tamaño de la zona:** R = retroceso medio entre sus picos (ticks).
- **Alejamiento (evento):** después de la creación, la primera vela cuyo cierre queda a ≥ D = k·R del último pico, del lado contrario a los picos (debajo de un techo, arriba de un piso). La zona tiene que seguir **sin romperse**.
- **Resultado:** la vela **toca** el nivel (máximo ≥ nivel en un techo, mínimo ≤ nivel en un piso) **antes** de que el precio se aleje otros D (a 2D del nivel). Horizonte máximo de 2.000 velas o fin de sesión. Se mide también el tiempo hasta tocar.
- **Virginidad:** ninguna vela tocó el nivel entre la creación y el alejamiento.
- **Volumen antes de acercarse:** volumen negociado desde la creación hasta el alejamiento (lo que se conoce en el evento), relativo al normal de la sesión, en terciles por activo.

## 4. Grilla (celdas de la prueba primaria)
Por activo, sobre sesiones de exploración (jul-2025 a mar-2026, contrato canónico):
- **detector:** estándar (ES ≥ 8 picos; NQ ≥ 7 picos y ≥ 40 velas) / estricto (ES ≥ 12; NQ ≥ 10) — **2**;
- **virginidad:** virgen / no virgen — **2**;
- **k:** 2, 4, 8 — **3**;
- **volumen antes del alejamiento:** todos / tercil bajo / tercil alto — **3**;
- **nivel:** último pico / primer pico — **2**.

**72 celdas por activo × 2 activos = 144 pruebas**, BH q = 0,10.

## 5. Controles
- **C-SZ, sin zona (primario):** para cada evento, 3 barras de otras sesiones a la misma hora (± 1 h) con el mismo estado (distancia al VWAP y pendiente de la EMA(21), en ATR) y la misma actividad (rango y duración de las últimas 20 velas), ±50 % o ±0,15 ATR. En cada una se pone un **nivel fantasma** a la misma distancia D del cierre, en la misma dirección, **sin ninguna zona detectada a menos de R**, y se mide la misma carrera.
- **N1 geométrico:** con la convención «tocar antes de alejarse otro tanto», p0 ≈ 0,5. Es descriptivo.
- **Dos canales:** acierto (direccional) y tiempo hasta tocar; se publica la distribución completa.
- **Auditoría CTRL_TIMING_V1:** los controles son de otra sesión (exentos), y se audita igual.

## 6. Embudo
- **A (información):** acierto real − control C-SZ, pareado y con bootstrap por sesión. Pasa si es INFO+ con FDR y con el mismo signo en las dos mitades.
- **B (economía, sólo con sobrevivientes de A):** entrada al confirmarse el alejamiento, TP en el nivel (atravesado por 1 tick), SL a otros D, costos propios de cada activo, y control de entrada al azar con las mismas salidas.
- **C:** PBO/DSR con el número real de variantes, y mesetas.
- La reserva abr–jun queda para 1–3 configuraciones, una sola vez. El holdout, intacto.

## 7. Riesgos
- **Detector ajustado sobre enero con las marcas de Nico:** es target-free (no mira resultados), pero su calidad es de ~70 %. Por eso la variante estricta es un parámetro: si el efecto existe, debería crecer con la calidad de la detección.
- **NQ sin validar:** su filtro todavía no tiene una tanda fuera de muestra. Si NQ da INFO+, antes de seguir hay que validar el detector.
- **Eventos solapados** (varios k de la misma zona): cada k es otra celda, y el bootstrap por sesión cubre la dependencia.
- **Potencia:** con ~25–60 zonas por día puede haber celdas SIN_POTENCIA; se publica el MDE de cada una.

## 8. No medido (queda abierto)
El estado continuo (zona virgen a distancia x); otros niveles (banda completa, POC de la zona); relación con el volumen del libro (L2); otros activos (YM, MYM, 6E); detectores de otras formas.

### Corrección antes de interpretar (26/09)
La primera corrida (reporte sha `daa3b0f3bbd3`, 32 INFO+) aplicaba el tope de pendiente y, en NQ, la duración mínima **con la serie completa**, que incluye picos formados después del evento. Si el precio volvía y armaba más picos, cambiaba qué zonas entraban: mirada al futuro. Se corrige usando sólo los picos conocidos en la creación, y **se descarta esa corrida sin interpretarla**; queda en el Cerebro como invalidada.

### Segundo control, más estricto (26/09, tras la corrida corregida `f156dc68d907` y antes de pasar a B)
Riesgo detectado: el nivel real es un pico **recién negociado**; el fantasma de C-SZ es un precio cualquiera a la misma distancia, que puede estar fuera del rango reciente. Parte del efecto podría ser «volver al rango reciente». **C-SW:** el nivel de control es un **máximo o mínimo reciente real** (pivote en las últimas 300 velas), todavía no superado, a la misma distancia (± R), que **no** es parte de una acumulación; misma hora, estado y actividad, en otra sesión. **Para pasar a B una celda tiene que ganarles a C-SZ y a C-SW** (IC inferior > 0 contra C-SW).
