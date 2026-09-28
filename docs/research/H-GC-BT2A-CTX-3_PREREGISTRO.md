# H-GC-BT2A-CTX-3 — contexto GATE L2 sobre BigTrap2Absorption

- **Estado:** `DRAFT_TARGET_FREE_NOT_FROZEN`
- **Fecha:** 2026-08-25
- **Instrumento de construcción:** `GC 06-26`, `NON_FRONT_MONTH_DIAGNOSTIC`
- **Modelo:** `gate_gc_l2_hmm3_toxic_forward_v1` — el `model_id` exacto se completa sólo después de la corrida real.
- **Firewall:** `CAMPAIGN_OUTCOMES_OPENED=false`, `PREEXISTING_OUTCOME_EXPOSURE=YES`, `EDGE_DECLARED=false`.

## Pregunta

¿El estimando ya vigente de la familia BigTrap2Absorption cambia entre el contexto
**G-operable** (`calm|normal`) y **G-stress** (`volatile|toxic`) cuando la etiqueta se
conoce causalmente antes del evento?

Los estados no son cuatro estrategias. Son cuatro climas para evaluar la misma geometría.
Una diferencia condicionada tampoco es un edge: después siguen inferencia, costos,
replicación y holdout.

## Compuertas target-free anteriores a cualquier outcome

El trial no puede congelarse ni ejecutarse hasta que todas pasen:

1. checkpoint real, hash-qualified, entrenado sólo hasta `20260617`;
2. labels de evaluación sólo en `20260619, 20260621–24` mediante
   `available_source_row < event_source_row`;
3. cobertura de contexto ≥ 99 % en la población de eventos;
4. publicación de minutos por estado, persistencia, flip rate, fallos de libro y cobertura;
5. `|corr(contexto, ancho_ticks)| < 0,20`, medido sin outcomes;
6. al menos 40 sesiones distintas en cada celda primaria;
7. identidad exacta de eventos, detector, parámetros, datos y modelo;
8. autorización escrita de Nico después del STOP target-free.

Con cinco sesiones de evaluación en el bundle actual, la compuerta 6 **no puede pasar**.
El bundle sirve para construir y auditar el mecanismo, no para abrir CTX-3.

## Población

- Eventos reales de BigTrap2Absorption producidos por una configuración congelada.
- Sólo sesiones posteriores al cutoff del checkpoint.
- Excluir `context_as_of_ok=false` con causa publicada; no imputar contexto.
- `20260618` está prohibida y no se abre.
- `GC 06-26.Last.parquet` no se une: carece de `source_row` y el reloj absoluto no está resuelto.
- Unidad mínima de inferencia: sesión, nunca evento IID.

## Contexto primario

| Celda | Estados | Lectura |
|---|---|---|
| G-operable | `calm`, `normal` | libro/volatilidad compatibles con operación potencial |
| G-stress | `volatile`, `toxic` | amplitud o flujo hostil; cautela |

`toxic` es un overlay de estrés L2 basado en OFI BBO, flujo agresivo, spread,
remociones/depleción y sticky. **No se llama VPIN**: implementar VPIN real exigiría otra
versión, buckets de volumen congelados y una prueba incremental target-free.

## Hipótesis primaria

- **H0:** el estimando primario de la familia es igual entre G-operable y G-stress.
- **H1 bilateral:** el estimando difiere entre ambas celdas.

No se fija dirección después de observar resultados. Si la familia base conserva un
estimando de equivalencia, CTX-3 prueba heterogeneidad de ese mismo estimando; no inventa
una métrica nueva.

## Campos todavía obligatorios antes de congelar

- `model_id` y hashes de corrida;
- snapshot exacto del indicador/configuración;
- nombre y definición literal del estimando primario copiado del acta viva;
- margen económico/equivalencia;
- población y MDE por celda;
- B y seed del bootstrap por sesiones;
- una prueba primaria G-operable − G-stress; cualquier familia adicional paga Holm aparte.

Mientras falte cualquiera: `DRAFT_TARGET_FREE_NOT_FROZEN`.

## Criterios de lectura futura

- Diferencia robusta: contexto informa condicionalmente, pero aún no demuestra edge.
- Sin diferencia con potencia suficiente: estos cuatro climas no rescatan el nulo.
- Sin potencia: inconcluso; no se relajan celdas ni thresholds.
- Corr con ancho o cobertura fallida: el trial no se ejecuta.

## Aporte al referente

CTX-3 queda convertido de intuición a compuertas falsables. Evita rescatar post hoc un
indicador nulo y deja explícito que el bundle actual sólo alcanza para construir el
mecanismo causal, no para inferencia económica.
