# Manifiesto: comprar el retroceso tras un extremo confirmado (familia RETRO-PIV), ES · NQ, 2026-09-25

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PROPUESTO. Es una prueba sobre P&L que **abre la reserva**: STOP, necesita el OK de Nico. Además hace falta la **spec confirmada en revisión ciega** y la campaña aprobada en el Brain (`record_campaign`, 2 pruebas).
**Ledger:** `artifacts/hippocampus/retro_piv_20260925.jsonl` (familia nueva). No usa F9: no abre indicadores nuevos (pivotes de zigzag, sin osciladores).

## 1. De dónde sale (y por qué esto es una CONFIRMACIÓN, no una exploración)

AGOT-EXT (§10) midió en exploración (jul-2025 a mar-2026) que **ir contra un extremo nuevo ya confirmado acierta menos que el azar**:
- ES 1 min: acierto 0,394 contra 0,446 esperado por N1 (1R);
- NQ 1 min: 0,43 contra 0,475.

Después de un máximo más alto confirmado (retroceso del 30 %), el precio tiende a volver a buscar el máximo. TREND-MICRO B3 dio el espejo: entrar en el impulso falla más que el azar. El patrón candidato es **"vender el impulso, comprar el retroceso"**.

**La hipótesis nació mirando esos datos**, así que volver a medirla ahí es circular. **La única prueba válida es fuera de muestra:** abr–jun 2026, que ninguna familia miró con resultados.

**Justificación económica:** en un tramo que hace extremos nuevos, el retroceso lo ejecutan los que toman ganancia y los que llegaron tarde, no un cambio de opinión del flujo que empujó. Cuando ese retroceso se agota, el flujo de fondo retoma la dirección y el precio vuelve a buscar el extremo (persistencia a la escala del pivote).

**Cómo podría refutarse:** en la reserva, el acierto de "volver al extremo antes de caer 1R" no supera a N1, o lo supera pero el R neto (con costos) no es > 0.

## 2. Regla (fija: es el espejo exacto de AGOT-EXT, sin grados de libertad nuevos)

- **Evento:** confirmación (V-CONF) de un pivote nuevo que supera al pivote previo del mismo lado. Mismo zigzag que AGOT-EXT: retroceso ≥ max(2 t, 0,3 · tramo), tramo ≥ 1,5 · ATR20 causal, pivote previo a ≤ 60 barras. Barras de **1 minuto**.
- **Todos los eventos**, con o sin divergencia: la divergencia ya se descartó.
- **Operación a favor del extremo** (comprar el retroceso tras un máximo más alto; vender el rebote tras un mínimo más bajo):
  - **entrada:** agresiva en el primer trade posterior a la confirmación + 250 ms;
  - **target:** el extremo + max(2 t, 0,25 · tramo) (el stop de AGOT-EXT), como límite que hay que atravesar por 1 tick;
  - **stop:** entrada − 1 · (target − entrada), simétrico 1:1, a mercado al tocarlo;
  - **tiempo máximo:** 30 barras (30 min);
  - **costo:** spread observado más comisión por lado (ES 0,2 t y NQ 0,5 t).
- **Descriptivo, no decide:** la misma regla en 5 min.

## 3. Datos y particiones

- Ticks de `research-v2`. Sesiones y contrato del día desde los manifiestos de los bundles (como AGOT-EXT).
- **Particiones nuevas, declaradas antes de medir:**
  - `P-RETRO-ES-EXP` y `P-RETRO-NQ-EXP`: jul-2025 a mar-2026 (ya vistas por AGOT-EXT; sólo para reproducir el número de origen con esta regla);
  - `P-RETRO-ES-CONF` y `P-RETRO-NQ-CONF`: **abr–jun 2026, una sola apertura, por protocolo**.
- **Aviso de multiplicidad entre familias:** abr–jun también está reservado por TBZ, TREND-MICRO y AGOT-EXT. Abrirlo acá con resultados lo **gasta para esta pregunta**. Las otras familias no pierden su reserva, pero el proyecto suma una mirada más sobre esos meses, y se anota en el Brain.
- **Holdout de ticks** (jul–dic 2026): intacto.

## 4. Prueba y criterio (fijados ahora)

- **2 pruebas** (ES 1 min y NQ 1 min), **Bonferroni α = 0,05 / 2**, bootstrap por sesión.
- **Pasa un instrumento** si:
  - el acierto supera a N1 (misma convención: camino de trades, target atravesado por 1 tick), con IC unilateral;
  - **y** el R neto por evento es > 0 con IC unilateral.
- **Resultado de la familia:**
  - **CONFIRMADA** si pasa en al menos un instrumento y en el otro el signo coincide;
  - **MUERTA** en su alcance declarado si no pasa en ninguno;
  - **SEÑAL SIN COSTO** si el acierto supera a N1 pero el R neto no: el fenómeno es real, pero no paga.
- **Advertencia económica escrita antes:** con 1:1, un exceso de acierto de ~5 pts equivale a ~+0,10 R bruto. Los costos a 1 min pueden comerse eso; se reporta tal cual, sin cambiar la regla.

## 5. Antes de abrir la reserva (orden obligatorio)

1. Implementar la regla en `tools/retro_piv.py`, reusando el zigzag y la simulación de `tools/agotamiento.py` y sus tests de causalidad.
2. **Reproducir en exploración** (`P-RETRO-*-EXP`) el número de origen con la regla de §2. Si no aparece, se para acá y no se abre la reserva.
3. Spec en `docs/specs/SPEC_RETRO_PIV_20260925.json` con su vista previa ciega (`tools/build_spec_preview.py`). Nico la confirma: "confirmo SPEC_RETRO_PIV <hash12>".
4. Campaña en el Brain: `human:Nico`, 2 pruebas, `partition_id = P-RETRO-*-CONF`.
5. Una sola corrida sobre la reserva, reporte y registro, sin re-corridas.

## 6. Riesgos

- **Circularidad:** la mitiga que la prueba sea sólo fuera de muestra.
- **Costos a 1 min:** pueden anular un exceso de acierto real. Es la primera cosa que mira el reporte.
- **Deriva de régimen:** abr–jun puede tener otra volatilidad. La regla es relativa al ATR, así que se adapta, pero el resultado vale para ese período.
- **Una sola apertura:** si la corrida tiene un error de construcción, la reserva queda gastada. Por eso el paso 2 (reproducir en exploración) va antes y es obligatorio.
