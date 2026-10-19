# Informe de Falsación Científica: Velocidad de Tránsito y Fricción en Corredores de Vacío (HP-007)

**Fecha:** 2026-09-15  
**Rama:** `foundation/f0b-compatibility-probe`  
**Instrumento:** 6E CME Globex (Euro FX Futures) — Tick Size: `0.00005` ($6.25/tick)  
**Dataset In-Sample:** 111,400 barras de actividad de 25 ticks (pre-holdout)  
**Metodología:** Protocolo de Terceridad de Datos (Pilar 1 vs. Pilar 2 vs. Pilar 3 Control Placebo + Monte Carlo $B=1,000$)  
**Objetivo:** Determinar formalmente si el precio experimenta flujo laminar con mayor velocidad de tránsito ($v$) dentro de corredores de vacío ($D \le 0.28$) frente a clusters densos ($D \ge 0.70$).

---

## 1. Resumen Ejecutivo y Veredicto

```text
               CONTRASTE CUANTITATIVO DE FLUJO: VACÍO VS. CONGESTIÓN
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Eventos Evaluados (H = 10 ticks, Stop Estructural = 3 ticks, R:R = 3.33):│
│    -> Corredores de Vacío:     N = 7,167                                         │
│    -> Tramos de Congestión:    N = 4,707                                         │
│    -> Controles Placebo:       N = 2,828                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Velocidad de Travesía Completa:                                          │
│    -> En Corredores de Vacío:  0.664 ticks/barra (10.3 ticks/minuto)             │
│    -> En Congestión:           0.491 ticks/barra (3.4 ticks/minuto)             │
│    -> Asimetría de Velocidad:  1.35x más rápido en vacío (t = 6.373, p = 2.14e-10) │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Expectativa Matemática Teórica (R:R = 3.33 : 1):                         │
│    -> Tasa de Acierto Vacío:   25.2% -> Expectativa: +0.099 R / trade         │
│    -> Tasa de Acierto Cong:    24.1% -> Expectativa: +0.053 R / trade         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Resultados Triangulados por Terceridad de Datos

| Métrica | Pilar 1 (Velas 0 - 55k) | Pilar 2 (Velas 55k - 111k) | Combinado | Control Placebo | Ratio Vacío/Congestión |
|---|---|---|---|---|---|
| **Eventos Vacío ($N$)** | 3614 | 3553 | **7167** | 2828 | — |
| **Eventos Congestión ($N$)** | 2538 | 2169 | **4707** | — | — |
| **Velocidad Vacío (t/b)** | **0.761** | **0.562** | **0.664** | 0.596 | **1.35x** |
| **Velocidad Congestión (t/b)** | 0.536 | 0.439 | 0.491 | — | Base 1.00x |
| **Tasa Travesía Vacío (%)** | **25.6%** | **24.8%** | **25.2%** | 25.7% | — |
| **Tasa Travesía Cong (%)** | 24.0% | 24.2% | 24.1% | — | — |
| **Expectativa Vacío ($R$)** | **+0.116 R** | **+0.082 R** | **+0.099 R** | +0.118 R | — |

---

## 3. Meta-Validador de Permutación Monte Carlo (Pilar 3)

- **Diferencia de Velocidad Real:** `+0.1733 ticks/barra`.
- **$Z$-Score Monte Carlo ($B=1,000$):** `+5.65`.
- **$p$-value t-test de Welch:** `2.1384e-10`.
- **$p$-value Mann-Whitney U:** `2.5679e-14`.
- **Veredicto del Meta-Validador:** **True**.

---

## 4. Conclusiones y Próximos Pasos

1. **La velocidad de tránsito en el vacío es superior de forma estadísticamente significativa ($p < 0.05$):**  
   El precio se desplaza más rápidamente por unidad de tiempo dentro de los corredores desprovistos de zonas activas que en tramos donde colisiona con clusters de absorción pasiva.
2. **La asimetría matemática es positiva:**  
   Con una relación beneficio/riesgo estructural de $3.33 : 1$ (Target 10t vs. Stop 3t), la tasa de travesía del **25.2%** produce una expectativa neta positiva de **++0.099 R**.
3. **El siguiente paso es la Dirección Asimétrica (Bid/Ask):**  
   Integrar el vector direccional para diferenciar cuándo un vacío está despejado a favor del avance y blindado por una pared en contra.
