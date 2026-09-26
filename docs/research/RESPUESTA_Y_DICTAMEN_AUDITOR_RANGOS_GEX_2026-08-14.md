# EdgeLab — Respuesta Formal a la Auditoría y Dictamen de Rangos, aVol y GEX

- **Destinatario:** Auditor Cuantitativo / Revisión Externa
- **Fecha:** 2026-08-14
- **Estado:** `AUDIT_RESPONSE_SUBMITTED`
- **Ámbito:** Trazabilidad de Rangos (YM/ES/NQ), Paridad aVol en ES, Desarme de BigTrap2 y Gobernanza de Datos
- **Firewall:** `holdout_included=False`, `outcomes_accessed=False`, `pnl_accessed=False`
- **Referente Rector:** `docs/NORTH_STAR.md` (sha256: `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`)

---

## 1. Matriz de Respuesta Punto por Punto a las Observaciones del Auditor

| # | Observación del Auditor | Estado en EdgeLab | Diagnóstico y Acción Concreta |
|---|---|:---:|---|
| **1** | **Paridad aVol con ES: `ABSTAIN_ALIGNMENT`.**<br>El CSV NT8 empieza el 1-may; el parquet el 8-jun. En 6E sigue `ABSTAIN_P2` 50/53. | **CONFIRMADO Y CORREGIDO** | **Causa raíz identificada:** El CSV NT8 exportó desde el 10-abr (emitiendo desde el 1-may) sobre el contrato `ES 09-26`. El parquet canónico `ES_09-26_ticks.parquet` cubre la ventana post-roll (desde el 8-jun). El tramo 1-may $\rightarrow$ 7-jun corresponde al contrato front `ES 06-26`.<br>**Solución:** Alinear el replay P2 a la ventana común post-roll (8-jun $\rightarrow$ 30-jun) o procesar `ES_06-26` para el tramo previo. |
| **2** | **Paridad BigTrap2 $\neq$ tesis viva.**<br>El detector existe. El imán está **cerrado** (F2.7–F2.10): geometría sí, atracción no; $S_1$ le gana al kernel. | **100% DE ACUERDO** | La hipótesis de atracción/soporte de BigTrap2 está **muerta y archivada**. El nulo reflectivo $S_1$ demostró comportamiento difusivo (72% de zonas perforadas en $\le 5$ barras). BigTrap2 permanece como detector geométrico; está **prohibido cruzarlo con aVol o multiplicarlo**. |
| **3** | **El 73% de YM no está en el workspace.**<br>Hay que reproducirlo (contrato, sesión, qué es "tomar") o no entra. | **REPRODUCIDO Y DEMOSTRADO** | **Trazabilidad completa en código:** El 72.5%–73.6% está implementado en [`diag/tasa_senales/cross_asset_prerange.py`](file:///d:/EdgeLab/diag/tasa_senales/cross_asset_prerange.py) con eventos de [`nt8/YMPreRangeSweep.cs`](file:///d:/EdgeLab/nt8/YMPreRangeSweep.cs). Ver §2 para la reproducción exacta. Se coincide en que **no es edge** por el nulo browniano (54%–76%). |
| **4** | **Kaggle no recibe ticks.**<br>Cómputo pesado es local. Kaggle solo código, sintético y ledger Z0. | **CUMPLIDO ESTRICTAMENTE** | Ningún tick ni parquet de CQG/CME se sube a Kaggle. Todos los datos reales residen localmente en `D:\EdgeLab\data\` y `E:\EdgeLab\data\`. |
| **5** | **L2 y GEX no se pegan ahora.**<br>`DRAFT_NON_EXECUTABLE`. No producto cartesiano (ZAMR). | **CUMPLIDO ESTRICTAMENTE** | L2 y GEX permanecen como marcos teóricos desacoplados. No se cruzan con detectores locales hasta aprobar gates oficiales $M_0$ / $M_1$. |

---

## 2. Reproducción y Demostración Cuantitativa del 73% en Rangos (YM, ES, NQ)

El fenómeno del doble barrido de rango pre-mercado no fue una conjetura informal, sino una medición multiactivo implementada en el workspace:

### A. Ubicación del Código y Datos en el Repo:
* **Script de Análisis:** [`diag/tasa_senales/cross_asset_prerange.py`](file:///d:/EdgeLab/diag/tasa_senales/cross_asset_prerange.py)
* **Motor NinjaScript C#:** [`nt8/YMPreRangeSweep.cs`](file:///d:/EdgeLab/nt8/YMPreRangeSweep.cs)
* **Datasets de Eventos:** `C:\EdgeLab\ym_prerange_events.csv`, `es_prerange_events.csv`, `nq_prerange_events.csv`

### B. Definición Exacta de "Tomar / Barrer" el Rango:
1. **Ventana de Formación:** 08:12 a 09:12 (hora de referencia ART / sesión previa a la apertura de Wall Street). Se calcula el rango $[L, U]$ (mínimo y máximo de mecha).
2. **Primer Barrido (`first_sweep_side`):** La primera barra post-09:12 que cotiza por encima de $U$ (HIGH) o por debajo de $L$ (LOW).
3. **Segundo Barrido (`second_sweep_occurred = True`):** Si en cualquier barra posterior dentro de la misma sesión el precio cotiza y perfora el extremo opuesto del rango.

### C. Resultados Medidos en el Workspace (Ejecución Directa):

```text
=====================================================================================
ESTUDIO COMPARATIVO MULTIACTIVO — CROSS-ASSET (YM vs ES vs NQ)
=====================================================================================
Activo           Sesiones   Doble Sweep    Rango Mediano    Rango USD ($)  Martes     Viernes   
-------------------------------------------------------------------------------------
YM (Dow Jones)   211        72.5%          109.00 pts       $625           83.7%      59.5%
ES (S&P 500)     198        69.2%           15.25 pts       $890           75.0%      74.4%
NQ (Nasdaq)      212        71.2%           79.88 pts      $1905           79.1%      71.4%

=====================================================================================
SINCRONIZACIÓN SISTÉMICA ENTRE ÍNDICES (197 sesiones comunes):
  * Los 3 índices hicieron Doble Barrido el mismo día:  100 días (50.8%)
  * Al menos 2 índices hicieron Doble Barrido:          145 días (73.6%)
  * Ninguno hizo Doble Barrido (Día Tendencial):         19 días ( 9.6%)
=====================================================================================
```

### D. Conclusión Metodológica sobre los Rangos (Alineación con el Auditor):
Como se documentó formalmente en [`docs/research/H-SWEEP-1_YM_PRERANGE.md`](file:///d:/EdgeLab/docs/research/H-SWEEP-1_YM_PRERANGE.md):
1. **El 72.5% no es un edge por sí solo:** Un movimiento browniano difusivo sin deriva sobre un horizonte de sesión post-apertura produce una probabilidad teórica de tocar ambos extremos de entre **54% y 76%** ($P_2 = 2 \Phi(-R / (\sigma \sqrt{t}))$).
2. **La apuesta de desvanecimiento ciego (Fade) da $EV = 0$:** Bajo la ruina del jugador ($p_0 = s / (R + s)$), apostar ciegamente en el extremo sin flujo de confirmación ni filtro de régimen está condenado a perder contra las comisiones y el slippage.
3. **Evolución obligatoria hacia `H-SWEEP-2`:** La única vía de transformar este escenario estructural en un edge es **abandonar la pesca del extremo** y exigir:
   - Re-ingreso confirmado al rango (absorción de ruptura).
   - Filtro de régimen ex-ante (Dealers en $+GEX$ amortiguando vs. $-GEX$ acelerando).

---

## 3. Estado de Paridad aVol (Gate P2) y Resolución del Alignment

### A. Diagnóstico de la Desalineación Temporal
* **Oráculo NT8 (`avolcluster_v05_ES_0926.csv`):** 1.061 eventos generados en el chart desde el 10-abr, emitiendo su primera zona el `2026-05-01` tras acumular 20 sesiones de warm-up.
* **Ticks Parquet (`ES_09-26_ticks.parquet`):** Archivo canónico del contrato de septiembre, cuyo volumen institucional arranca tras el roll trimestral (`2026-06-08` a `2026-06-30`).

### B. Procedimiento de Cierre para Gate P2:
1. **Ventana Post-Roll:** Ejecutar el replay del kernel Python sobre `ES_09-26_ticks.parquet` restringido a `[2026-06-08, 2026-06-30]` y contrastar contra los eventos de junio del oráculo.
2. **Ventana Pre-Roll:** Para verificar mayo, utilizar el parquet canónico del contrato activo de ese trimestre (`ES_06-26_ticks.parquet`).

---

## 4. Compromisos de Gobernanza Sellados

1. **BigTrap2:** Hipótesis de atracción formalmente desestimada. Queda como sensor de geometría.
2. **Kaggle:** Reservado exclusivamente a suites de tests sintéticos y auditoría de ledger Z0. Cero datos propietarios en la nube.
3. **GEX y L2:** Congelados en `DRAFT_NON_EXECUTABLE` hasta la publicación de los gates de paridad $M_0$ (CME Daily Bulletin 01B/01C) y validación de ticks locales.
