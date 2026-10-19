# Exploración — asimetría de la excursión posterior a la zona (hipótesis de Nico) — 2026-10-06

Descriptivo, sin regla de decisión. Script: `tools/explo_asimetria_excursion.py`. Datos: MNQ 12-26 (50t y 200t) y
MGC 12-26 (50t), re-export, hasta el 2026-09-30.

**Hipótesis (Nico, capturas de MGC):** en las X velas posteriores a la zona, el precio se extiende mucho hacia un lado y
apenas visita el otro, lo que daría RR altos.

**Métrica:** sin escala, así que no la afecta el artefacto de AVCL-PRE.
- U = máx(high) − close de creación; D = close de creación − mín(low), en H ∈ {10, 20, 50, 100} velas.
- Cociente = lado grande / lado chico.
- Controles: barras al azar a más de 100 velas de cualquier evento, reponderadas a la franja horaria de los eventos.

**Resultado:**
- P(cociente ≥ 3) es del **55–60 %** y P(≥ 5) del **36–45 %** tanto en eventos (AVCL AT, OFF, VTD) como en
  **controles al azar**, en MNQ y MGC y en las cuatro ventanas.
- Las diferencias entre eventos y controles son de ±0–3 pp, sin patrón consistente.

**Lectura:** la asimetría que se ve en el chart es **real pero universal**. Es una propiedad del recorrido del precio
(ley del arcoseno): desde cualquier punto, el máximo y el mínimo posteriores suelen ser muy desiguales. **No es propia
de las zonas.** Para capturarla como RR hay que predecir el lado del tramo largo, y eso no lo hizo ninguna variable
probada (lado, delta, salida).

Coherente con lo anterior:
- Alrededor de las zonas AVCL las excursiones son *menores* que en los controles (compresión; AVCL-PRE).
- Alrededor de VTD son *mayores* (MNQ 50t H10: tramo grande de 52 contra 24 ticks; expansión real).

**Siguiente:** buscar predictores del lado del tramo largo (estado de mercado, estructura previa, vela VTD), no más
mediciones de asimetría.
