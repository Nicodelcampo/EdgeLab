# IDEA (registrada, NO ejecutada): IPC — Entrada en creación inmediata y entrada por confirmación V-Shape — 2026-09-29

**Origen:** Nico (29/09/2026), tras calibrar el detector de picos consecutivos sobre MYM con 52 juicios (21 ✓ / 31 ✗).
**Estado:** PENDIENTE DE DISEÑO FORMAL Y PRE-REGISTRO. NO EJECUTADA (regla STOP: mira retornos).

---

## 1. Dos lógicas de entrada propuestas

### A. Entrada inmediata al crearse la zona (`ENTRADA-CREACION`)
- **Mecánica:** Apenas se confirma el $N$-ésimo pico que valida la zona (vela causal del pico $+ w$), se gatilla una orden en la dirección de la absorción (piso $\rightarrow$ compra, techo $\rightarrow$ venta) o en la dirección de la pendiente de la escalera.
- **Diferencia con el imán clásico:** El diseño original de IPC (`MANIFIESTO_IPC_IMAN_20260926.md`) esperaba a que el precio se alejara una distancia $D = k \cdot R$ para luego medir el regreso al nivel. Esta variante no espera alejamiento: entra inmediatamente al formarse el soporte/resistencia.
- **Hipótesis:** La confirmación del $N$-ésimo pico concentra liquidez pasiva fresca; si la absorción se completó, el movimiento expansivo subsiguiente ofrece una asimetría de recorrido antes de la ruptura del nivel.
- **Justificación económica:** Quien defiende el nivel ya absorbió el flujo opuesto en los $N$ toques. La vela que confirma el último pico es el punto de menor riesgo relativo respecto del stop estructural (justo detrás del nivel).
- **Cómo podría refutarse:** La expectativa matemática neta no supera a un control de entrada aleatoria con el mismo SL/TP a la misma hora y régimen, o el precio perfora el nivel en la vela siguiente más veces de lo esperado por la ruina del jugador.

---

### B. Entrada al retorno con rechazo en V (`ENTRADA-VSHAPE`)
- **Mecánica:** Tras el alejamiento previo de la zona, el precio regresa al nivel del IPC pero no se entra con orden límite pasiva ni ciega. Se exige que el toque al nivel produzca un **V-Shape** (rechazo violento en pocas velas, mecha de absorción pronunciada y cierre rápido fuera de la zona).
- **Hipótesis:** Las zonas IPC que rebotan con forma de V tienen menor probabilidad de ruptura que aquellas donde el precio "se estaciona" o consolida dentro de la banda.
- **Justificación económica:** Un retorno con V-Shape evidencia que al tocar el nivel se activaron órdenes agresivas de defensa o absorción rápida (institucionales o barrido de liquidez local). La permanencia corta en el nivel indica falta de interés vendedor en techos o comprador en pisos.
- **Cómo podría refutarse:** El filtro V-Shape reduce la cantidad de eventos sin aumentar la tasa de ganancia neta (acierto de V-Shape $\le$ acierto sin filtro de forma, o la pérdida de trades ganadores no compensa la reducción de falsos positivos tras descontar comisiones y spread).

---

## 2. Alertas y precauciones metodológicas antes de medir
1. **Definición cuantitativa causal de V-Shape:**  
   No se puede medir "a ojo" en backtest. Debe pre-registrarse una fórmula exacta:
   - Número máximo de velas dentro de la banda de precio de la zona (ej. $\le 2$ o $3$ velas).
   - Relación mecha/cuerpo o velocidad de alejamiento en ticks por vela tras el toque.
   - Momento causal exacto de la entrada: al cierre de la vela que confirma el pico de retorno o al superar el extremo opuesto.
2. **Control emparejado obligatorio:**  
   Tanto `ENTRADA-CREACION` como `ENTRADA-VSHAPE` deben compararse contra:
   - Control sin zona a la misma hora y con la misma volatilidad previa.
   - Control de entrada con SL/TP idénticos en momentos donde no hay V-Shape.
3. **Costos en MYM:**  
   En MYM (tick de 1.0 pt = \$0.50), las comisiones fijas por contrato pesan más en términos de ticks que en YM grande. La relación TP/SL debe ser lo bastante holgada para superar la fricción sin destruir la tasa de acierto.

---

## 3. Condiciones para pasar a experimentación
- Manifiesto formal de pre-registro aprobado por Nico.
- Regla causal implementada en Python con paridad verificable.
- Datos de descubrimiento: hasta enero 2026 (o marzo 2026 según enmienda HOLDOUT-A3). Replicación sellada fuera de muestra.
