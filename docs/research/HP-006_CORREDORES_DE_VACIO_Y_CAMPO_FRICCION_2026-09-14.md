# HP-006: Corredores de Vacío y Campo de Fricción As-Of (Fast-Travel Liquidity Pockets)

> **ID de Investigación:** `HP-006`  
> **Nombre del Concepto:** Detección de Corredores de Vacío de Liquidez y Campo de Fricción Microestructural As-Of  
> **Fecha de Registro:** 2026-09-14  
> **Origen:** Propuesta y observación de Nico del Campo en sesión de diseño (gráfico 6E Continuo 25 ticks con `BigTrap2Absorption` Alta Sensibilidad)  
> **Rama Responsable:** `foundation/f0b-compatibility-probe`  
> **Instrumentos Aplicables:** 6E, NQ, ES, GC y cualquier activo con detectores de zonas (BigTrap2, HFT Clusters, LuxAlgo Imbalance, Gaps)  
> **Estatus:** `DESIGN_REGISTERED_NOT_EXECUTED` (Diseño formal registrado, listo para prototipado)  
> **Firewall de Holdout:** No toca outcomes de campañas activas; respeta estrictamente el holdout `2026-07-01 → 2026-12-31`.

---

## 1. Planteo del Problema y Tesis Microestructural

### Observación Empírica del Trader
Al utilizar detectores de zonas de alta sensibilidad (donde el gráfico se puebla con cientos o miles de niveles de absorción, desbalance o volumen), el espacio de precios queda saturado en ciertas áreas, pero simultáneamente se forman **claros "espacios en blanco" o vacíos de precio** donde no hay presencia de zonas activas.

### Tesis Económica
1. **Los Congestionamientos (Clusters Densos):**  
   Son zonas donde el mercado ha depositado abundante liquidez pasiva, absorción y órdenes limitadas. El precio experimenta una **alta fricción de desplazamiento**: el avance es lento, con continuos testeos, mechas adversas (alto MAE) y alto consumo de volumen.
2. **Los Vacíos de Zonas (Corredores de Baja Fricción / Fast-Travel):**  
   Son bolsas de precio donde no existen órdenes de absorción registradas ni niveles descansados relevantes. Cuando el precio es expulsado de un cluster denso con momentum direccional, **el vacío actúa como un canal de baja resistencia**: el precio se desplaza con alta velocidad, mínimo retroceso adverso y nula fricción hasta impactar contra el siguiente cluster denso.
3. **El Desafío Técnico Central:**  
   Un área de precios puede no haber generado ninguna zona nueva en la última hora, pero estar atravesada por zonas viejas que vienen proyectadas desde la izquierda del gráfico. Por lo tanto, la "carencia de zonas" **no puede medirse como ausencia de nacimientos locales**, sino como **ausencia de cobertura activa ponderada en el eje vertical as-of**.

---

## 2. Formulación Matemática del Campo de Fricción As-Of

A cualquier barra o instante temporal $t$, sea $\mathcal{Z}(t)$ el conjunto de todas las zonas activas en el sistema:
$$\mathcal{Z}(t) = \{ Z_k : t_{0, k} \le t \le t_{\text{end}, k}, \text{no invalidada definitivamente} \}$$
Cada zona $k$ está delimitada verticalmente por el intervalo $[y_{\min, k}, y_{\max, k}]$.

### A. Función de Relevancia Dinámica $W_k(t)$
No todas las zonas que atraviesan un nivel de precio tienen el mismo poder de frenado. El peso dinámico $W_k(t) \in [0, 1]$ de la zona $k$ en el instante $t$ se define como:

$$W_k(t) = W_{\text{base}} \times f_{\text{antigüedad}}(t - t_{0, k}) \times f_{\text{desgaste}}(\text{toques}_k(t)) \times f_{\text{fuerza}}(\text{score}_k)$$

1. **Factor de Antigüedad ($f_{\text{antigüedad}}$):**  
   Una zona recién creada posee mayor frescura institucional. A medida que envejece (en barras), su poder predictivo decae:
   $$f_{\text{antigüedad}}(\Delta b) = \max\left(0.05, 1.0 - \frac{\Delta b}{\text{MaxAgeBars}}\right)$$
   *(donde $\Delta b = t - t_{0, k}$; zonas más allá de 500 barras en 25t decaen al piso residual).*
2. **Factor de Desgaste / Virginidad ($f_{\text{desgaste}}$):**  
   La liquidez pasiva se consume con el comercio:
   * **Zona Virgen (0 testeos previos):** $f_{\text{desgaste}} = 1.0$ (toda su liquidez intacta).
   * **Zona Mitigada / Atravesada:** Cada vez que el precio penetra o atraviesa la zona, las órdenes pasivas son ejecutadas o retiradas. Para $n$ cruces previos:
     $$f_{\text{desgaste}}(n) = \frac{1}{1 + \alpha \cdot n} \quad (\text{con } \alpha \approx 0.5 \text{ a } 1.0)$$
     Una zona cruzada 3 veces reduce su peso efectivo a $\approx 0.25$ (se vuelve virtualmente transparente).
3. **Factor de Fuerza Microestructural ($f_{\text{fuerza}}$):**  
   Pondera la magnitud de la ineficiencia original (número de filas apiladas `MinStackedRows`, volumen atrapado `vol`, o ratio de desbalance `ImbalanceRatio` normalizado entre 0.5 y 1.5).

### B. Densidad de Oposición Vertical $D(p, t)$
Discretizando el eje de precios en ticks $p \in [P_{\min}, P_{\max}]$, la densidad de fricción microestructural en el nivel $p$ en el tiempo $t$ es la superposición de todas las zonas activas:

$$D(p, t) = \sum_{k \in \mathcal{Z}(t)} W_k(t) \cdot \mathbf{1}_{\{ y_{\min, k} \le p \le y_{\max, k} \}}$$

* Si aplicamos un halo de influencia suave (para modelar el efecto de atracción/dispersión alrededor de los bordes):
$$D(p, t) = \sum_{k \in \mathcal{Z}(t)} W_k(t) \cdot \exp\left( - \frac{(p - \text{center}_k)^2}{2\sigma^2} \right)$$
*(con $\sigma \approx 2 \text{ a } 4 \text{ ticks}$).*

---

## 3. Algoritmo Formal de Detección de "Corredores de Vacío"

Un intervalo de precios continuo $\mathcal{C} = [P_{\text{inf}}, P_{\text{sup}}]$ se clasifica formalmente como un **Corredor de Vacío (Área de Fácil Desplazamiento)** en el tiempo $t$ si satisface tres axiomas:

```text
Eje de Precios (p)
  ▲
  │   [████████████████████████████]  <-- Cluster Denso Superior: D(p, t) >= Theta_pared
  │─────────────────────────────────── P_sup
  │                                
  │        CORREDOR DE VACÍO          <-- D(p, t) <= Theta_vacio  (Fricción Nula)
  │    (Área de Fácil Desplazamiento)      Amplitud: (P_sup - P_inf) >= H_min
  │                                        Sin órdenes pasivas descansadas
  │                                
  │─────────────────────────────────── P_inf
  │   [████████████████████████████]  <-- Cluster Denso Inferior: D(p, t) >= Theta_pared
──┴──────────────────────────────────────► Tiempo (t)
```

1. **Axioma de Vacío Interior:**  
   La densidad de fricción en todos los puntos del interior del corredor debe ser inferior a un umbral de corte $\theta_{\text{vacío}}$:
   $$\forall p \in (P_{\text{inf}}, P_{\text{sup}}): \quad D(p, t) \le \theta_{\text{vacío}}$$
   *(Típicamente $\theta_{\text{vacío}} = 0$ para vacío absoluto, o $\le 0.15$ para admitir zonas completamente agotadas/viejas).*
2. **Axioma de Amplitud Mínima Económica ($H_{\min}$):**  
   El espacio libre debe ser suficiente para justificar los costos de spread y comisiones de CME Globex:
   $$P_{\text{sup}} - P_{\text{inf}} \ge H_{\min} \quad (\text{ej. } \ge 12 \text{ ticks en 6E, es decir } \$75.00 \text{ brutos por contrato})$$
3. **Axioma de Delimitación Estructural (Paredes de Confinamiento):**  
   El corredor debe estar acotado por verdaderas barreras de absorción (no por el fin arbitrario del gráfico):
   $$D(P_{\text{inf}}, t) \ge \theta_{\text{pared}} \quad \land \quad D(P_{\text{sup}}, t) \ge \theta_{\text{pared}}$$
   *(donde $\theta_{\text{pared}} \ge 1.0$, indicando presencia de al menos un cluster denso o múltiples zonas vivas).*

---

## 4. Lógica Operativa y de Ejecución

El modelo transforma la información estática del gráfico en un **sistema de transporte rápido**:

| Parámetro Operativo | Definición Causal | Justificación Microestructural |
|---|---|---|
| **Disparador (Gatillo)** | Ruptura con volumen agresivo de la pared $P_{\text{inf}}$ hacia el corredor | El precio escapa de la congestión y entra al vacío |
| **Punto de Entrada** | $P_{\text{inf}} + 1 \text{ tick}$ (en compra) o $P_{\text{sup}} - 1 \text{ tick}$ (en venta) | Confirmación de penetración en el área sin fricción |
| **Stop Loss (Riesgo)** | $P_{\text{inf}} - 3 \text{ ticks}$ (estructural, tras la pared) | El cluster denso recién quebrado actúa como soporte; si reingresa, la hipótesis falla |
| **Take Profit (Target)**| $P_{\text{sup}} - 1 \text{ tick}$ (inmediatamente antes de la pared opuesta)| El precio viaja libre hasta que la siguiente muralla de liquidez absorbe el avance |
| **Relación Beneficio/Riesgo**| Típicamente $\ge 2.5 : 1$ | Riesgo pequeño ($\approx 3-4$ ticks) vs recorrido completo del corredor ($\ge 12-16$ ticks) |

---

## 5. Comparador No Nulo y Criterio de Falsación Científica

Para que este concepto sea admitido en el canon de EdgeLab, debe superar un contraste formal contra el azar:

### Comparador No Nulo
Se comparan dos poblaciones de tramos de precio de idéntica amplitud $\Delta P$:
1. **Población Tratamiento ($\mathcal{P}_{\text{vacío}}$):** Tramos recorridos dentro de un Corredor de Vacío ($D \le \theta_{\text{vacío}}$).
2. **Población Control ($\mathcal{P}_{\text{congestión}}$):** Tramos recorridos de igual amplitud dentro de un Cluster Denso ($D \ge \theta_{\text{pared}}$).

### Métricas a Medir
- **Velocidad de Tránsito ($v$):** Ticks avanzados por unidad de tiempo o por barra:
  $$v = \frac{\Delta P}{\Delta \text{barras}}$$
- **Excursión Adversa Máxima (MAE):** Retroceso mediano sufrido durante el trayecto.
- **Tasa de Culminación Limpia ($\% \text{Full Traverse}$):** Porcentaje de veces que el precio cruza de $P_{\text{inf}}$ a $P_{\text{sup}}$ sin retroceder más de 3 ticks.

### Criterio de Falsación
La hipótesis $H_0$ (el vacío no reduce la fricción) se rechazará si y sólo si:
$$v_{\text{vacío}} > v_{\text{congestión}} \quad (\text{con } p < 0.01)$$
$$\text{MAE}_{\text{vacío}} < \text{MAE}_{\text{congestión}} \quad (\text{con } p < 0.01)$$
$$\% \text{Full Traverse}_{\text{vacío}} > 60.0\%$$
Si la velocidad o la tasa de llegada no muestran diferencia estadísticamente significativa frente a tramos congestionados, la hipótesis se declara **VOID POR FALTA DE ASIMETRÍA DE FLUJO** y se archiva.

---

## 6. Plan de Implementación Modular

### Fase A: Runner Python de Extracción y Validación (Offline)
- Archivo propuesto: `tools/test_corredores_vacio.py`.
- Insumo: Bundles de zonas existentes (`bundles/6E_CONT.json` o parquets canónicos).
- Funcionalidad: Calcular $D(p, t)$ barra a barra, aislar los intervalos de vacío y contrastar las velocidades de tránsito frente a clusters densos.

### Fase B: Capa Visual en el Visor NT8 Bridge
- Modificación en `viewer/nt8_bridge/index.html`:
  - Agregar checkbox en la barra superior: `[ ] Corredores de Vacío (Fast Travel)`.
  - Renderizar rectángulos sombreados suaves (color cyan traslúcido `#00e5ff12`) en los intervalos $[P_{\text{inf}}, P_{\text{sup}}]$ donde $D(p, t) == 0$.
  - Agregar histograma vertical a la derecha mostrando la curva $D(p, t)$ viva.

### Fase C: Indicador / Estrategia NinjaTrader 8
- Archivo propuesto: `nt8/FastTravelCorridors.cs`.
- Mantiene un buffer circular de zonas activas con decaimiento temporal y emite alertas en tiempo real cuando el precio penetra un corredor de vacío delimitado por dos clusters institucionales.

---

## 7. Registro de Procedencia

- Documento creado en cumplimiento de la solicitud de Nico del Campo del 2026-09-14.
- Indexado en `docs/OPEN_IDEAS_INDEX_2026-09-02.md` bajo la designación **HP-006**.
- No modifica código productivo ni altera el estado de las 60 ramas de EdgeLab.
- Sirve como especificación técnica completa y autosuficiente para que cualquier agente de IA o investigador retome el trabajo sin pérdida de contexto.

---

## Aporte al referente

Se formalizó y registró la propuesta **HP-006: Corredores de Vacío y Campo de Fricción As-Of**, traduciendo la observación visual de "espacios en blanco entre zonas de alta sensibilidad" en un modelo matemático computable basado en la superposición ponderada de zonas vivas (antigüedad, desgaste por toques y fuerza). Se establecieron los tres axiomas de delimitación del corredor, las reglas de entrada/riesgo con R:R asimétrico, el comparador no nulo contra tramos congestionados y los criterios estrictos de falsación científica antes de cualquier implementación operativa.
