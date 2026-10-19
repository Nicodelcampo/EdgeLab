# HP-007 — corrección de invariancia del visor por rango visible

## Alcance

Corrección exclusivamente target-free del visor. No mide revisitas, retornos, P&L ni abre holdout para selección.

## Causa raíz

`drawCorredoresDemo()` construía el dominio de precios desde las velas visibles y además seleccionaba zonas por intersección con ese rango visible. Por eso zoom, paneo o autoescala podían cambiar el perfil `D(p)` y la segmentación de franjas aun manteniendo el mismo `tRef`.

Se sumaban tres defectos:

1. fallback implícito al run `bt2a_25t_sensible`;
2. filtro temporal por `z.t0`, no por disponibilidad causal;
3. pesos que maduraban con el tiempo aunque no nacieran zonas nuevas.

## Solución conservadora

Se agregó `viewer/nt8_bridge/index_invariant.html`, un loader fail-closed que aplica sobre `index.html`:

- dominio de precios sobre todas las velas disponibles hasta `tRef`, no sobre el viewport;
- zonas independientes del rango visible;
- run exactamente seleccionado;
- prioridad a `available_ts`/`availableTime`;
- modo `RAW_STATIC` sin maduración, decaimiento, desgaste o penalización;
- advertencia visible con el número de zonas que todavía usan fallback legado `t0`.

El loader exige que cada ancla aparezca exactamente una vez. Si `index.html` cambia, aborta antes de aplicar un parche parcial.

## Uso

```text
http://localhost:8088/index_invariant.html?asset=6E_CONT
```

## Invariante exigida

Con idénticos `bundle`, `run` y `tRef`, el valor de `D(p)` para cada precio debe permanecer idéntico ante:

- zoom horizontal;
- paneo horizontal;
- zoom vertical;
- cambio del rango de precios visible;
- autoescala.

Si aparece una diferencia, es un FAIL del visor, no evidencia del mercado.

## Limitación explícita

Los bundles antiguos pueden no publicar `available_ts`. En ese caso el visor permite abrirlos usando `t0`, pero muestra `fallback t0: N`. Esos bundles son diagnósticos y no tienen condición causal certificada.

## Aporte al referente

La corrección elimina una dependencia visual del viewport y evita interpretar como estructura de mercado un artefacto de renderizado.
