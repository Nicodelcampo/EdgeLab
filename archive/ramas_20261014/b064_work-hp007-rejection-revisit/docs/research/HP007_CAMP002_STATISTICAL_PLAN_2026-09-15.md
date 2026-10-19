# Plan Estadístico Formal — HP007-CAMP-002
## Medición Causal de Revisitación y Traversa de Vacíos de Liquidez

**Fecha:** 2026-09-15  
**Campaña:** `HP007-CAMP-002`  
**Autor:** Antigravity (Advanced Agentic Coding / EdgeLab)  
**Documento Rector:** `docs/research/PROMPT_ANTIGRAVITY_HP007_CAMP002_REJECTION_REVISIT_2026-09-15.md`  
**Rama:** `work/hp007-rejection-revisit-campaign-v2-20260915`

---

## 1. Pregunta Primaria de Investigación Estructural

> **Dado que un vacío microestructural fue inicialmente rechazado, ¿un regreso posterior —tras suficiente distancia, tiempo y volumen negociado— presenta una probabilidad mayor de penetrarlo o atravesarlo completamente que un acercamiento comparable a un vacío fresco?**

Esta investigación es de carácter estrictamente estructural y mecanístico. **No es una optimización de reglas de trading, ni una búsqueda de P&L, Sharpe, stops o targets comerciales.**

---

## 2. Máquina de Estados Causal y Riesgos Competitivos

Para cada vacío con geometría congelada en el primer acercamiento $[L, U]$ de ancho $W = U - L$:
1. **Primer Acercamiento ($a$):** El precio llega a una distancia $\le \text{approach\_ticks}$ de la frontera cercana ($L$ para compras / $+1$, $U$ para ventas / $-1$).
2. **Rechazo Confirmado ($\text{reject}$):** Sin haber atravesado el vacío en el primer acercamiento y sin haber penetrado más de `max_first_penetration_ratio` ($50\%$ de $W$), el precio se aleja en dirección contraria al menos $\text{rejection\_excursion\_ticks}$ ticks.
3. **Alejamiento Calificado ($\text{qualified}$):** El precio permanece fuera de la zona de acercamiento hasta acumular:
   - Tiempo de reloj $\ge \text{min\_away\_seconds}$;
   - Volumen negociado $\ge \text{min\_away\_volume}$;
   - Cantidad de transacciones $\ge \text{min\_away\_trades}$.
   Si el precio regresa a la frontera antes de calificar, el episodio se descarta por retorno prematuro.
4. **Segundo Acercamiento ($r$):** Tras calificar, el precio vuelve a alcanzar la frontera cercana.
5. **Terminales Competitivos ($q$):**
   - `TRAVERSED`: El precio alcanza la frontera lejana más `crossing_buffer_ticks`.
   - `REJECTED_AGAIN`: El precio vuelve a alejarse $\ge \text{rejection\_excursion\_ticks}$ de la frontera cercana antes de cruzar.
   - `CENSORED`: Finaliza la sesión, se agota el horizonte máximo de $3,600$ segundos o finalizan los datos sin alcanzar ninguno de los dos estados anteriores.

---

## 3. Estimandos Principales

### Estimando 1: Probabilidad Condicional de Traversa en Revisitación
$$\pi_{\text{revisit}} = \frac{N(\text{TRAVERSED})}{N(\text{Total Episodios Revisitados})}$$

### Estimando 2: Diferencia de Riesgo frente a Acercamientos Frescos Emparejados (Matched Control)
$$\Delta \pi = \pi_{\text{revisit}} - \pi_{\text{fresh\_matched}}$$
Donde cada episodio de revisitación se empareja $1:1$ sin reemplazo con un acercamiento fresco (primera aproximación a un vacío con geometría, ancho, dirección, bucket horario y régimen de volatilidad equivalentes).

### Estimando 3: Curva de Respuesta a Dosis (Dose-Response)
Comparación de tasa de traversa según:
- Tiempo alejado: Alto ($> \text{mediana}$) vs Bajo ($< \text{mediana}$).
- Volumen alejado: Alto ($> \text{mediana}$) vs Bajo ($< \text{mediana}$).
- Excursión máxima alejada.

### Estimando 4: Contrastes de Ablación Mecanística
Comparación del campo de resistencia bajo 4 configuraciones deterministas:
- `FULL`: fuerza $\times$ maduración $\times$ decaimiento temporal $\times$ desgaste por toques.
- `NO_MATURATION`: excluye la maduración.
- `NO_TIME_DECAY`: excluye el decaimiento por tiempo.
- `NO_WEAR`: excluye el desgaste por toques físicos.

---

## 4. Inferencia Estadística y Corrección de Multiplicidad

- **Nivel de Conglomerado:** Sesión CME (`America/Chicago`), respetando pausas de mantenimiento (16:00-17:00 CT).
- **Muestreo:** Permutación sign-flip y remuestreo bootstrap con $\ge 100,000$ extracciones deterministas (semilla `42`).
- **Control de FWER:** Corrección de Holm-Bonferroni sobre la familia pre-registrada de 24 variantes.
- **Resolución Holm:** Para $K = 24$ y $\alpha = 0.05$, el mínimo de remuestreos requerido es $24 / 0.05 = 480 \ll 100,000$.

---

## 5. Partición Walk-Forward por Contrato

- **Train (IS):** `6E 03-26` (2026-01-01 a 2026-03-15).
- **Test (OOS):** `6E 06-26` (2026-03-16 a 2026-06-30).
- **Holdout (SELLADO):** $\ge 2026-07-01$ (**0** filas procesadas).

---

## 6. Reglas de Abstención y Veredictos Permitidos

1. Si $N_{\text{episodios}} < 20 \implies$ `ABSTAIN_INSUFFICIENT_EPISODES`.
2. Para Gaps2, si no hay certificado real de paridad NT8 en contratos IS $\implies$ `ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN`.
3. Veredictos de fondo autorizados:
   - `BASE_LOGIC_STRUCTURALLY_SUPPORTED`
   - `BASE_LOGIC_PROMISING_BUT_UNSTABLE`
   - `BASE_LOGIC_NOT_SUPPORTED`
   - `INVALIDATED_EXECUTION`
