# Campaña multi-instrumento sobre ticks: resultados (2026-09-23/24)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

**Pre-registro:** `PREREG_CAMPANA_TICKS_MULTIINSTRUMENTO_20260923.md`, aprobado por Nico, con la enmienda A1 (`60154b9`) escrita antes de ejecutar.

**Código y procedencia:**
- Corrida principal: `tools/campaign_ticks_multi.py` (`24a1e56`).
- Re-corrida corregida de F3/F4: `tools/campaign_ticks_multi_rerun.py` (commit del fix).
- Rama: `integ/viewer-brain-20260923`.

**Brain:** `artifacts/hippocampus/campaign_ticks_multi_20260923.jsonl`, con 151 registros, anclado en `ANCHORS.json`. Contiene:
- 5 campañas aprobadas por `human:Nico`.
- 100 pruebas.
- 40 invalidaciones: F3/F4 con el bug.
- La falla del episodio.
- 1 contraejemplo y 2 lecciones PROPOSED/LOW.

## Incidentes de ejecución (causa raíz)

1. **Bug de F3/F4.** La sesión CME empieza a las 18:00 ET del día anterior, y "la primera barra con hora ≥ apertura RTH" tomaba la barra de las 18:00 de la noche previa:
   - F3 no generó trades.
   - F4 entraba de noche, con números absurdos (+1.115 ticks por trade).
   - Las 40 pruebas quedaron **invalidadas en el Brain**. Se re-corrieron con el fix; mismas hipótesis, datos, costos y estadística.
   - **La re-corrida no se registró como pruebas.** El presupuesto de C-TICKS-F3/F4 ya estaba consumido, y una campaña nueva requiere aprobación humana (NO_SELF_APPROVAL). Pendiente P-81.
2. **Segundo escritor.** El script abría un segundo `DurableHippocampus` sobre el ledger del episodio, y el lock nuevo lo rechazó al cierre. Corregido: se usa `ep.store`. Las 100 pruebas sí quedaron registradas.
3. **Revisado sin cambios.** Un arreglo que intenté sobre la salida de F2 no llegó a aplicarse. La lógica original ya era correcta (sale cuando una barra cierra del otro lado del VWAP), así que F1, F2 y F5 son válidos tal como corrieron.

## Resultado

**0 de 100 variantes sobreviven los criterios 1 a 3, y ninguna se replica en 2 instrumentos.** Esto usa F1, F2 y F5 de la corrida principal, y F3 y F4 de la re-corrida corregida.

| Familia | MCPT de descubrimiento (p < 0,05) | Validación neta | Lectura |
|---|---|---|---|
| F1 Momentum | 0/5 | mayormente negativa | sin timing ni margen |
| F2 Reversión al VWAP | **5/5** | negativa en todos | hay timing y no cubre costos (salvedad: la salida al VWAP vs un nulo de duración fija) |
| F3 Ruptura de apertura (corregida) | 0/5 | mixta, en torno a 0 | sin señal |
| F4 Cierre de gap (corregida) | **ES, NQ, YM** (0,001; 0,001; 0,019); GC 0,10; 6E 0,074 | ES positiva en 4/4 variantes; NQ y YM mixtas; IC enormes | **sin potencia**: 25–56 trades en 4 meses, NQ ±300 ticks |
| F5 Ruptura por volatilidad | 0/5 | mixta | sin señal |

**Una sola variante tiene IC de validación > 0**, incluso con costo × 1,5: 6E F4 v3 (+18,9 ticks, IC [6,0; 31,8]). Pero su familia no pasó el MCPT (p = 0,074) y su DSR con N = 100 es 0,68. Destacarla sería elegir el máximo de 100 pruebas: **no sobrevive** y no se rescata.

## Veredicto (con alcance preciso)

Las cinco familias simples, con estas 20 variantes, **no muestran edge neto robusto** en GC, ES, NQ, YM y 6E, para ago-2025 a jun-2026, barras de 5 min, costos del feed NT8 y comisión supuesta de USD 4,50.

**Lo que queda abierto, como hipótesis nueva que requiere su propio pre-registro:** **el cierre de gap nocturno en índices de acciones.** Pasó el nulo en 3/3 índices en descubrimiento, pero es un efecto de **una observación por día**, y 11 meses de ticks no alcanzan. Para testearlo con potencia hacen falta **varios años de datos diarios o de 1 minuto** de ES/NQ/YM, que son baratos y no requieren ticks. Es la mejor pista que dejó la campaña, y **no es un sobreviviente**.

## Cómo podría refutarse este veredicto

Con más historia, las mismas 100 pruebas, sin cambios, darían sobrevivientes replicados en ≥ 2 instrumentos.
