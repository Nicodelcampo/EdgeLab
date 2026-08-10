# H-COND-1 — Familia LUX-IMB (OG/VI) y protocolo de efectos condicionales

**Fecha:** 2026-08-10
**Estado:** protocolo escrito. Nada ejecutado.
**Gate:** bloqueado hasta cerrar el incidente P0 de procedencia.

> **Familia registrada:** `LUX-IMB` — indicador `Imbalance Detector [LuxAlgo]`, restringido a **Opening Gap (OG)** y **Volume Imbalance (VI)**. Fair Value Gap queda **fuera de alcance** por decisión del operador.
>
> **Esta familia es independiente de BigTrap2.** No hereda resultados, poblaciones, costos, oráculos ni presupuesto de multiplicidad. El costo `2,768 ticks` pertenece a H1/6E y no aplica acá.

Nada de este documento afirma un edge ni autoriza outcomes.

---

## Función de este documento

Definir una estructura falsable para responder una sola pregunta:

> ¿El precio reacciona en las zonas OG/VI más de lo que reaccionaría en niveles comparables, y esa reacción existe únicamente bajo ciertas condiciones?

El documento no afirma que exista un efecto, no autoriza tocar retornos monetizados y no abre el holdout.

---

## 1. Por qué el análisis marginal puede dar nulo aunque el efecto exista

### 1.1 Dilución

Si los encuentros se reparten en condiciones $c$ con pesos $\pi_c$ y efectos $\Delta_c$:

$$\Delta_{\text{marginal}}=\sum_c \pi_c\,\Delta_c$$

Un efecto de $0{,}20$ presente en el 10% de los casos produce un marginal de $0{,}02$.

### 1.2 Cancelación

Si las zonas producen rechazo en un régimen y aceleración en otro:

$$\Delta = 0{,}3\,(+0{,}15) + 0{,}3\,(-0{,}15) + 0{,}4\,(0) = 0$$

Un efecto real, fuerte y bidireccional da **exactamente cero** bajo un test de medias. Es el modo de falla más peligroso del diseño ingenuo.

### 1.3 Consecuencia

Un nulo sin MDE publicado es ininterpretable. Ver sección 11.

---

## 2. Amenaza principal: sesgo de supervivencia por mitigación

La documentación del indicador establece que una vez que el precio atraviesa un área de desequilibrio, esta se considera **mitigada y desaparece automáticamente** del gráfico.

### 2.1 Formalización

Sea $D_z(T)=1$ el evento *la zona $z$ sigue dibujada en el instante de observación $T$*. Si la regla de render elimina toda zona mitigada, entonces para cualquier zona visible que ya fue tocada antes de $T$:

$$\Pr\big(\text{no atravesada}\mid\text{tocada},\,D_z(T)=1\big)=1$$

No por una propiedad del mercado, sino por definición del renderizado.

> **El gráfico observado está compuesto casi por construcción de zonas que no fueron atravesadas.** Observar que "el precio respeta esas zonas" es, en parte, observar la regla de dibujo.

### 2.2 Segunda vía de desaparición

El parámetro `Extend` dibuja la zona una cantidad fija de barras hacia la derecha. Una zona puede desaparecer por vencimiento de `Extend` sin haber sido mitigada. Son dos causas distintas de ausencia visual y deben separarse en el ledger.

### 2.3 Regla derivada

**Ningún análisis puede usar el estado renderizado del gráfico.** Toda la evidencia debe provenir de un ledger reconstruido causalmente barra a barra que incluya las zonas muertas.

### 2.4 Entregable: medir el sesgo en lugar de suponerlo

Se calculan dos estimaciones del mismo estimand: $\hat\theta_{\text{visible}}$ usando solo zonas vivas, y $\hat\theta_{\text{ledger}}$ usando el censo completo. La diferencia

$$B=\hat\theta_{\text{visible}}-\hat\theta_{\text{ledger}}$$

es una medición directa del sesgo de supervivencia y es un resultado publicable por sí mismo.

---

## 3. OG y VI son mecanismos distintos y no se agrupan

| Aspecto | Opening Gap (OG) | Volume Imbalance (VI) |
| --- | --- | --- |
| Geometría | Mechas de dos velas adyacentes que no se solapan | Cuerpos que no se solapan mientras las mechas sí |
| Contenido del área | Intervalo sin negociación: vacío real | Hubo negociación; no hubo consenso entre apertura y cierre |
| Frecuencia esperada en ES 1m | Baja y concentrada | Alta |
| Confusor dominante | Hora, liquidez y noticias | Densidad: cobertura alta del eje de precio |
| Mecanismo candidato | Hueco de liquidez y reversión hacia precio negociado | Desacuerdo transitorio entre agresores pasivos y activos |

Ambas se detectan al **cierre de la segunda vela**, no de la tercera. La latencia de detección es de una barra y debe respetarse sin excepción.

**Regla:** OG y VI se estiman por separado, con su propio matching, su propio nulo y su propio presupuesto de multiplicidad. Agruparlas requeriría un test de equivalencia previo.

---

## 4. Amenaza específica de OG: colinealidad con hora y liquidez

En un contrato líquido, dos velas de un minuto con mechas disjuntas requieren un salto de precio. Eso ocurre casi exclusivamente en cortes y reaperturas de sesión, publicaciones macro, horario nocturno delgado y eventos de baja profundidad.

Sin controlar la fase de sesión, cualquier efecto encontrado sería atribuible al horario y no a la zona. En OG el emparejamiento por hora, profundidad y volatilidad es la condición de validez del estimand.

Observación de muestreo: las capturas que originaron la hipótesis cubren ventanas nocturnas y de mañana europea, precisamente el régimen donde OG es más frecuente y el ruido microestructural es mayor.

---

## 5. Amenaza específica de VI: densidad y cobertura

$$C(k)=\frac{1}{T}\sum_{t=1}^{T}\mathbf{1}\Big(\exists\, z\in A(t):\ \operatorname{dist}\big(P_t,z\big)\le k\Big)$$

Si $C(k)$ es alta, la observación "el giro estaba cerca de una zona" deja de ser informativa. El denominador correcto no es la cobertura cruda sino el nulo emparejado de la sección 8.

---

## 6. Ledger as-of: censo obligatorio de zonas

Campos por zona:

- `zone_id`, `instrument`, `session`, `bar_spec`
- `subfamily` en OG o VI, y `direction`
- barra y timestamp de creación
- límites `L` y `U`, ancho en ticks y ancho normalizado por volatilidad
- volumen y profundidad al crearse
- pendiente de formación del desequilibrio
- valor y modo de `Min Width`
- valor de `Extend`
- método de mitigación declarado
- barra y tipo de fin: mitigada, vencida por `Extend`, o viva
- historial completo de toques con ordinal
- hash del conjunto de parámetros

**Auditoría antirepintado:** se recorre la serie truncando los datos en $t$ y se verifica que el conjunto de zonas reconstruido coincide exactamente con el ledger. Toda discrepancia descalifica el campo afectado.

---

## 7. Parámetros a exportar del chart

La población no queda definida hasta tener, del gráfico real del operador:

- [ ] modo y valor de `Min Width` en puntos, porcentaje o múltiplos de ATR
- [ ] valor de `Extend`
- [ ] umbral de volatilidad si está activo
- [ ] timeframe de detección
- [ ] método de mitigación
- [ ] toggles activos: confirmar OG y VI encendidos y FVG apagado
- [ ] contrato y calendario de sesión usados

---

## 8. Controles: tres niveles de nulo

1. **C1 — niveles aleatorios emparejados** por sesión, hora, distancia inicial al precio, ancho y volatilidad.
2. **C2 — intervalos sintéticos de geometría idéntica** que replican la distribución de anchos y posiciones, sin cumplir el criterio de desequilibrio.
3. **C3 — casi-zonas.** Candidatos que fallaron el criterio por un margen mínimo: cuerpos que se solapan apenas para VI, o mechas que se tocan por un tick para OG. Es el control más fuerte porque todo lo demás es continuo alrededor del umbral.

**Test de falsación:** no debe existir discontinuidad en la respuesta al cruzar el valor de `Min Width` elegido por el usuario. Ese umbral es una preferencia de visualización. Un salto ahí indicaría un artefacto del pipeline.

---

## 9. Canales de resultado

1. **Direccional:** movimiento con signo. Puede cancelarse.
2. **No direccional:** magnitud absoluta, volatilidad realizada y tasa de giro. Inmune a la cancelación.
3. **Distribucional:** Kolmogorov–Smirnov, Anderson–Darling y distancia de energía contra el nulo.
4. **Primera llegada:** riesgos competitivos entre rechazo y continuación.

### 9.1 Tiempos de primera llegada

$$T_R=\inf\{u>0:\ s_i(P_{\tau_i+u}-b_{\text{near}})\le -a_i\}$$

$$T_C=\inf\{u>0:\ s_i(P_{\tau_i+u}-b_{\text{far}})\ge a_i\}$$

$$D_H=\frac{1}{H}\sum_{u=1}^{H}\mathbf{1}\big(P_{\tau_i+u}\in[L-a_i,\ U+a_i]\big)$$

Un resultado posible y honesto: las zonas marcan lugares donde pasa algo, sin predecir hacia dónde. Eso es información, no un edge.

---

## 10. Protocolo de heterogeneidad

El orden es obligatorio y no puede alterarse después de ver resultados.

- **Paso A — contraste dirigido.** Moderadores pre-registrados con signo predicho, como un único contraste de un grado de libertad.
- **Paso B — omnibus.** $H_0:\ \Delta_c=\Delta\ \forall c$, permutando la etiqueta real/nulo dentro de cada conjunto emparejado. Si no rechaza, no hay licencia para inspeccionar subgrupos.
- **Paso C — CATE con cross-fitting.** Estimación honesta y mejor predictor lineal:

$$Y_i=\alpha+\beta_1\bar\tau+\beta_2\big(\hat\tau(X_i)-\bar\tau\big)+\varepsilon_i$$

  $\beta_1$ es el efecto promedio y $\beta_2$ indica si la heterogeneidad es real. Con $\beta_2\approx 0$ las condiciones eran ruido. Se usan múltiples particiones con agregación por mediana y se reporta la variabilidad entre particiones.
- **Paso D — requisito de forma.** Un efecto real es una región suave, no una celda aislada.
- **Paso E — multiplicidad.** Romano–Wolf en escalones.
- **Paso F — particiones.** Descubrimiento y confirmación disjuntas. El holdout permanece cerrado.

---

## 11. Moderadores pre-registrados

| Moderador | Mecanismo | Signo predicho |
| --- | --- | --- |
| Ancho de zona sobre volatilidad | Un área comparable al ruido no puede ser un punto de decisión | Reacción crece con el ancho relativo |
| Pendiente de formación | Propuesto en literatura externa sobre desequilibrios | Formación más lenta implica reacción más fuerte |
| Velocidad de aproximación | Llegar con impulso frente a llegar agotado | Rechazo mayor si llega lento |
| Ordinal del toque | Depleción de liquidez | Rechazo decrece con el ordinal |
| Confluencia y apilamiento | Varias zonas superpuestas frente a marca aislada | Reacción mayor |
| Edad de la zona | La información caduca | Reacción decrece |
| Fase de sesión y profundidad | Liquidez y composición de participantes | Crítico en OG, secundario en VI |
| Volumen de creación | Intensidad del desequilibrio original | Reacción mayor |

La pendiente de formación proviene de literatura externa y no fue derivada de estos datos, lo que reduce el riesgo de que sea un moderador inventado a posteriori.

---

## 12. Regla MDE

$$\text{MDE}=(z_{1-\alpha/2}+z_{\text{poder}})\cdot\frac{\sigma_D}{\sqrt{S}}$$

Ejemplo ilustrativo con $S=201$, $\sigma_D=0{,}25$ y 80% de poder:

$$\text{MDE}\approx 2{,}80\cdot\frac{0{,}25}{\sqrt{201}}\approx 0{,}049$$

El diseño marginal no puede detectar nada menor a unos 5 puntos porcentuales, y un efecto diluido de $0{,}02$ sería invisible por construcción. Dentro de un subgrupo con efecto de $0{,}20$ y $\sigma_D=0{,}40$ sobre 180 sesiones, el MDE cae a $\approx 0{,}083$ y el efecto sí es detectable. Ese contraste es la justificación cuantitativa del análisis condicional.

---

## 13. Presupuesto de multiplicidad declarado

- **Primarios: 2.** Un omnibus de heterogeneidad por subfamilia, sobre el canal no direccional en el primer toque.
- **Secundarios: 16.** Ocho moderadores por dos subfamilias, bajo Romano–Wolf.
- Todo lo demás es exploratorio y no puede adjudicar nada.
- Horizontes, anchos de tolerancia y ventanas se publican como curvas completas, nunca como celda elegida.

---

## 14. Test ciego de percepción — H-PERCEPT-1

- **Brazo A:** fragmentos renderizados como los muestra la plataforma, con las zonas mitigadas ya desaparecidas.
- **Brazo B:** fragmentos renderizados desde el ledger completo, mostrando también las zonas que murieron.

En ambos brazos, mitad reales y mitad nulos, sin nombre de indicador, sin fecha y sin escala identificable. Con $c$ aciertos en $N$ comparaciones pareadas:

$$p=\sum_{k=c}^{N}\binom{N}{k}\left(\tfrac{1}{2}\right)^{N}$$

Se reportan además intervalo de Wilson, calibración y puntaje de Brier.

**Si el acierto es alto en el brazo A y colapsa en el brazo B, la intuición estaba leyendo la supervivencia por mitigación y no el comportamiento del mercado.**

Una segunda ronda muestra únicamente información previa al toque, para separar percepción predictiva de percepción retrospectiva. Si el desempeño supera al azar, se entrena un modelo sobre las etiquetas del operador para recuperar el moderador implícito, se congela la regla y se prueba en datos intactos.

---

## 15. Criterios de muerte

- El omnibus de heterogeneidad no rechaza en ninguna subfamilia.
- $\beta_2\approx 0$: la heterogeneidad predicha no está calibrada.
- El efecto vive en una celda aislada sin región suave alrededor.
- Desaparece al pasar de zonas visibles al ledger completo: era supervivencia.
- En OG, desaparece al emparejar por fase de sesión: era horario.
- No replica en la partición de confirmación.
- Sobrevive pero queda por debajo de costos: `informativo pero sub-fee`.

---

## 16. Implementación

1. Reimplementación causal del detector OG/VI con reproducción barra a barra y prohibición de lookahead.
2. Ledger as-of con auditoría antirepintado automática.
3. Generador de nulos en tres niveles con semilla reproducible y pruebas de invariantes.
4. Extractor de event-space completo: creación, aproximación, primer toque, toque n-ésimo, entrada, llenado parcial, mitigación, vencimiento por `Extend`, solapamiento y estado continuo.
5. Motor de resultados con los cuatro canales.
6. Módulo de heterogeneidad con cross-fitting y particiones múltiples.
7. Corrección de multiplicidad con Romano–Wolf.
8. Banco de imágenes ciego para H-PERCEPT-1, con los dos brazos de render.
9. Artefactos con procedencia dirty-aware completa, en worktree aislada.

---

## 17. Gate de ejecución

**Nada de este protocolo se ejecuta hasta cerrar el incidente P0 de procedencia Git/worktree.** La corrida ES del 10 de agosto está en cuarentena, y ES es justamente el contrato observado.

Orden: cerrar P0, exportar parámetros del chart, construir ledger, auditar repintado, medir el sesgo de supervivencia, y recién entonces abrir el protocolo condicional.

---

## 18. Referencias externas

- Documentación de conceptos de desequilibrio y mitigación: <https://docs.luxalgo.com/docs/algos/price-action-concepts/imbalances>
- Script y parámetros de ancho mínimo y extensión: <https://www.tradingview.com/script/C0cC294Q-Imbalance-Detector-LuxAlgo>
- Inferencia genérica sobre efectos heterogéneos: <https://arxiv.org/abs/1712.04802>
- Bosques causales generalizados y estimación honesta: <https://grf-labs.github.io/grf/reference/causal_forest.html>
- Corrección de Romano–Wolf: <https://ftp.iza.org/dp12845.pdf>
- Impacto de precio del desequilibrio de flujo de órdenes: <https://arxiv.org/abs/1011.6402>
