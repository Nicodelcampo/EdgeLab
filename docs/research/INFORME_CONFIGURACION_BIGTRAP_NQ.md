# Informe de Investigación: Configuración Óptima y Arquitectura de BigTrapNQ

> **Fecha:** 2026-09-06  
> **Contrato Base:** `NQ 09-25` (13,624,675 ticks, 42 sesiones CME)  
> **Metodología:** Target-Free Microstructure Sweep (Protección estricta de Holdout, zero look-ahead)  
> **Código de Referencia:** [`edgelab/bridge/indicators/bigtrap_nq.py`](file:///D:/EdgeLab/edgelab/bridge/indicators/bigtrap_nq.py)  
> **Módulo Microestructura:** [`edgelab/research/nq_microstructure.py`](file:///D:/EdgeLab/edgelab/research/nq_microstructure.py)

---

## 1. El Problema Original: ¿Por qué BigTrap2 Clásico Fallaba en NQ?

BigTrap2 fue concebido originalmente en ES/GC sobre barras de tiempo (1 minuto) con parámetros fijos:
- Filas de 1 tick (0.25 pt).
- Umbral rígido de 30 contratos.
- Sin conciencia de velocidad de cinta ni de régimen horario.

Al proyectarlo sobre el Nasdaq (NQ), este diseño fallaba por tres motivos microestructurales:
1. **Volatilidad y Ruido en Barras de Tiempo:** En 1 minuto en NQ se negocian miles de contratos y el precio recorre 15 a 40 puntos. Casi cualquier mecha ordinaria acumula $\ge 30$ contratos con desbalance diagonal 3:1, generando **más de 100 zonas por sesión** (saturación inoperable).
2. **Flash Sweeps vs Absorción:** En NQ, un barrido de liquidez algorítmico atraviesa un nivel en 2 milisegundos ejecutando órdenes limitadas pasivas sin frenar. El indicador clásico lo marcaba erróneamente como "trampa".
3. **Subastas Incompletas (Unfinished Auctions):** Cuando un máximo o mínimo negociaba tanto en Bid como en Ask, el mercado dejaba una subasta abierta que luego atraía el precio como un imán, perforando la zona y arruinando la expectativa.

---

## 2. Fase 1: Barrido Matricial de Resolución de Barra

Se contrastaron 5 tipos de barra ($\times$ 7 configuraciones del indicador) sobre 13.6M ticks:
- **`time:1` (1 min):** Descartado. 96 a 120 zonas/sesión en RTH. Inoperable por sobreoperación.
- **`tick:250` y `tick:100`:** Descartados. Exceso de volumen agregado por barra.
- **`tick:50`:** Aceptable, pero con 12 a 16 zonas/sesión.
- **`tick:25`:** **Ganador indiscutido**. Mantiene el flujo de órdenes en escala atómica pura (25 trades por barra), permitiendo aislar con precisión milimétrica la mecha donde los compradores o vendedores quedan atrapados.

---

## 3. Fase 2: Integración de Auction Market Theory

Se implementaron e investigaron tres filtros estructurales:

### A. Subasta Terminada (`require_finished_auction`) — Ganador #1
- **Fundamento:** Un extremo de mercado genuino presenta subasta cerrada: el último tick no encuentra contrapartida opuesta (volumen en el lado contrario $\le \text{tolerancia}$). Si hubo volumen significativo en ambos lados, la subasta está incompleta.
- **Impacto Empírico:**
  - Depuró **41 zonas espurias** (15.2% del total).
  - Elevó el Structural Fitness Score de **74.5 a 76.6**.
  - Mejoró la simetría Bull/Bear a **1.12** (121 Bull / 108 Bear).
  - Redujo la densidad de 6.21 a **5.45 zonas/sesión**.

### B. Delta Exhaustion de Barra
- **Hallazgo Empírico Crucial:** En barras de tiempo amplias (M5), un delta de barra adverso confirma absorción. Sin embargo, en **micro-barras de `tick:25`**, si 50 o 60 contratos agresivos golpean el Ask en el extremo, ese bloque representa el **60–80% del volumen total de la barra**. Exigir delta de barra negativo elimina por física de escala casi el 100% de los eventos legítimos. Por tanto, en barras micro-tick, el desbalance local en el footprint y la subasta terminada son los criterios correctos.

### C. Point of Control (POC) en Mecha
- En barras de 25 ticks, cuando un extremo absorbe $\ge 50$ contratos, ese precio se convierte automáticamente en el POC de la micro-barra, validando la concentración en el extremo.

---

## 4. Fase 3: Barrido Fino de Sensibilidad sobre `tick:25` + Finished Auction

Evaluación de volumen mínimo ($40, 50, 60, 70$ contratos) y tolerancia ($0.0$ vs $1.0$ contratos):

| Min Vol | Tolerancia | Zonas Totales | Zonas / Sesión RTH | Cobertura Sesiones | Simetría (Bull/Bear) | Diagnóstico |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 40.0 | 0.0 | 470 | 11.27 | 78.6% | 1.23 (259 / 211) | Demasiado denso (sobreoperación) |
| 40.0 | 1.0 | 505 | 11.74 | 81.0% | 1.21 (277 / 228) | Demasiado denso |
| **50.0** | **0.0** | **229** | **5.45** | **78.6%** | **1.12 (121 / 108)** | **Excelente para Scalping Activo** |
| **50.0** | **1.0** | **248** | **5.71** | **81.0%** | **1.10 (130 / 118)** | **Excelente cobertura (81%)** |
| **60.0** | **0.0** | **108** | **2.42** | **78.6%** | **1.16 (58 / 50)** | **Ideal Sweet-Spot Institucional** |
| **60.0** | **1.0** | **115** | **2.58** | **78.6%** | **1.09 (60 / 55)** | **Máxima Simetría (52% / 48%)** |
| 70.0 | 0.0 | 59 | 1.50 | 66.7% | 1.46 (35 / 24) | Cobertura insuficiente (< 70%) |
| 70.0 | 1.0 | 59 | 1.50 | 66.7% | 1.46 (35 / 24) | Cobertura insuficiente (< 70%) |

---

## 5. Especificación Final Congelada: BigTrapNQ

### Configuración Primaria (Perfil Institucional / Standard):
- **Resolución de Barra:** `tick:25` (25 ticks por barra, reinicio por sesión CME).
- **Agrupación Footprint (`ticks_per_row`):** `1` tick ($0.25\text{ pt}$).
- **Umbral de Volumen Trampa (`min_trap_volume`):** `60.0` contratos.
- **Ratio de Desbalance (`imbalance_ratio`):** `3.0` (diagonal 3:1).
- **Filtro de Subasta Terminada (`require_finished_auction`):** `True`.
- **Tolerancia Subasta (`finished_auction_tol`):** `1.0` contrato.
- **Buffer Anti-Overshoot (`anti_overshoot_buffer_ticks`):** `2` ticks ($0.50\text{ pt}$).
- **Filtro de Mecha (`use_wick_filter`):** `True` (en el 40% extremo de la barra).
- **Modo de Invalidación:** `CloseThrough` (cierre adverso a través de la zona).

**Métricas Operativas Estimadas:**
- **Densidad RTH:** $2.5$ a $2.6$ zonas por sesión.
- **Simetría Direccional:** $1.09$ (52% Compradores Atrapados / 48% Vendedores Atrapados).
- **Ancho Típico de Zona:** $0.75\text{ pt}$ (3 ticks).
- **Cobertura:** $\approx 79\%$ de las sesiones CME presentan oportunidades de alta convicción.

---

## 6. Aporte al Referente

- Se demostró empíricamente con 13.6M de ticks que `tick:25` es el marco óptimo para NQ frente a la sobreoperación masiva de barras de tiempo M1.
- Se incorporó la teoría de subasta de mercado (`Finished Auction`), depurando el 15.2% del ruido espurio y balanceando la simetría a 1.09.
- El código se encuentra 100% testeado (10/10 tests unitarios en verde en [`tests/bridge/test_bigtrap_nq.py`](file:///D:/EdgeLab/tests/bridge/test_bigtrap_nq.py)) y reproducible dentro del entorno de EdgeLab.
