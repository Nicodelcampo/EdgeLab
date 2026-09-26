# CAMP-001 — RESULTADO (intento 1, 2026-07-25)

> Este documento sirve al referente rector: ver [`../NORTH_STAR.md`](../NORTH_STAR.md).
> Manifiesto **SEALED v1.1** sha256 `46533c0a4c6ff69ee0ddcb1435e47595a9b5ff86594c63019d5a6c7347b304be`.
> **Resultado NEGATIVO.** Se registra igual que uno positivo (NORTH_STAR: "un
> resultado negativo se registra, no relaja gates ni abre el holdout").

## Trazabilidad

| | |
|---|---|
| commit | `86f02a9714a5` (working tree limpio) |
| preflight | `runs/nt8_bridge/camp001/preflight.json`, **PASS 17/17** |
| crudos | `attempt_01/raw_results.jsonl`, sha256 `01cc1856d6cdc92c1166d62ae3e666410a003b6ea41a823bd7b2db7baa31a0ec` |
| digest | `a2f4f200e3ec34fd` |
| integridad | **INTEGRITY_PASS 16/16** |
| reporte | `attempt_01/report_A4.txt` |
| escenario | `base` · fricción round-turn **USD 16,90 = 2,7040 ticks** |

Comando reproducible:

```bash
python tools/camp001_preflight.py && python tools/camp001_run.py --attempt 1 && python tools/camp001_integrity.py --attempt 1 && python tools/camp001_report.py --attempt 1
```

## Reproducibilidad VERIFICADA (2026-07-25)

El intento 2, corrido con el simulador optimizado (búsqueda binaria en vez de
escaneo lineal), produjo la **misma salida byte a byte**:

| | intento 1 | intento 2 |
|---|---|---|
| sha256 de los crudos | `01cc1856d6cdc92c…` | **idéntico** |
| digest | `a2f4f200e3ec34fd` | **idéntico** |
| tiempo | 1h 35m | **1m 15s** (76×) |

Prueba dos cosas a la vez: que la optimización es semánticamente neutral —no
sólo pasan los 7 golden, coincide la salida completa sobre 209.738 trades— y que
**este resultado negativo es reproducible**, no un artefacto de una corrida.

## La respuesta

**No hay efecto bruto que supere la fricción en ninguna de las 48 hipótesis.**

| magnitud | valor |
|---|---|
| trades ejecutados | **209.738** (de 608.328 señales, 34,5 %) |
| E\[bruto\] agregado | **−0,1479 ticks/trade** |
| E\[neto\] agregado | **−2,6984 ticks/trade** |
| configs con E\[bruto\] > 0 | 15/48 |
| configs con E\[bruto\] > fricción | **0/48** |
| configs con E\[neto\] > 0 | **0/48** |

Todas las celdas superaron los umbrales de E6.6: **48/48 `elegible_para_G1`**,
ninguna `insufficient_n`. El temor de E6.4 sobre `zone_min_size=5` no se
materializó (166–337 trades por celda, por encima del mínimo de 100 de G1). La
muestra alcanzó; la respuesta es que no hay efecto.

### El matiz que importa

**Esto NO es "hay un edge y los costos se lo comen".** El bruto agregado es
−0,15 ticks: prácticamente cero, y del lado equivocado. No hay efecto
direccional que monetizar, ni siquiera antes de pagar un centavo de fricción. Si
el bruto hubiera dado, digamos, +2 ticks contra una fricción de 2,7, la
conclusión sería "el efecto existe pero no paga costos" (`failed (uneconomic)`,
§G3) y la línea de trabajo sería reducir fricción. **No es el caso.**

## Los "ganadores" son ruido, y se puede demostrar

Los ganadores por familia son `zmin=5` en **3 de 4** familias — el estrato con
menos muestra. Eso solo ya es sospechoso; la dispersión lo confirma:

| `zone_min_size` | n mediano | rango de E\[bruto\] | dispersión |
|---|---:|---|---:|
| 2 | 9.849 | −0,435 … +0,000 | **0,435** |
| 3 | 1.603 | −0,506 … +0,106 | **0,612** |
| 5 | 253 | −0,928 … **+1,636** | **2,564** |

La dispersión crece al achicarse la muestra en la proporción que predice el
**ruido puro** (≈ 1/√n), no un efecto real: si hubiera señal en los gaps grandes,
la esperaríamos como un desplazamiento del centro, no como un ensanchamiento
simétrico del rango. Elegir el máximo sobre 12 configs cuando las más ruidosas
tienen 6× la dispersión selecciona ruido por construcción.

**Por eso el +1,64 de `F1-z5-p4-R2` no se reporta como hallazgo.** Está muy
dentro del ruido de n=275, y aun así queda **1,84 ticks por debajo** de su propia
fricción (3,48). Ninguna lectura lo salva.

## Refutación estructural, según el criterio pre-registrado

§2 del manifiesto declaró de antemano:

> Refutación estructural: si las 4 familias fallan G1 en el agregado, la
> hipótesis "los micro-gaps de 6E llevan información accionable en m1" queda
> registrada como negativa; NO se amplía la grilla dentro de esta campaña.

Las 4 familias fallan G1 (expectancy neta ≤ 0 en las 48 celdas). **La hipótesis
queda registrada como negativa** y no se amplía la grilla.

**Alcance exacto de lo refutado** (ni más ni menos): que *estas 4 familias de
reglas*, sobre *barras de 1 minuto*, con *estas salidas* (stop/target R/time stop
240), en *6E*, en *este período de desarrollo*, produzcan expectativa neta
positiva. **No** queda refutado que los gaps lleven información en otra
resolución, con otras salidas, en otro instrumento, o como *feature* dentro de un
modelo en vez de como regla mecánica.

## Limitaciones honestas

- **La regla de una posición simultánea rechazó el 65,5 % de las señales**
  (397.062 `position_open`). Los trades ejecutados **no son una muestra aleatoria**
  de las señales: son los que llegaron con la cuenta libre. Es una regla sellada y
  económicamente correcta (1 contrato), pero condiciona la lectura.
- La comisión (USD 2,20/pata) es **estimación pre-registrada**, no dato real del
  broker (dato faltante #1). Con el bruto en ≈0, un costo distinto no cambia el
  signo, pero el número exacto sigue pendiente.
- **No se corrió G2** (MCPT, PBO, walk-forward). No hace falta para este
  veredicto: G2 sirve para descartar que un resultado *positivo* sea selección.
  Con 0/48 positivos no hay nada que descartar.
- No se aplicó corrección por múltiples pruebas: sería relevante si hubiera algún
  candidato positivo.
- Salidas: 138.909 stops vs 65.578 targets (2,1:1), con 3.012 cierres de sesión y
  1.278 time stops. Consistente con recorrido aleatorio más fricción.
- 1.304 señales descartadas por `invalid_stop` (el open ya estaba más allá del
  stop: el trade no existe) y 92 por borde de datos. 0,051 % de las barras usaron
  libro sustituto de 1 tick por quote degradado.

## Qué NO se hizo

- **No se recomienda ninguna promoción.**
- **No se abrió el holdout.** Sigue sellado 2026-07-01 → 2026-12-31.
- **No se cambió ninguna regla después de ver el resultado**: ni umbrales, ni
  grilla, ni costos, ni folds, ni tratamiento estadístico.
- No se amplió la grilla ni se probó "una variante más".

## Decisión pendiente de Nico

El resultado es una respuesta válida, no un fracaso: orienta capital y tiempo
igual que un sí. Las continuaciones posibles —**ninguna elegida ni iniciada**—
serían campañas **nuevas** con manifiesto propio, no extensiones de ésta:

1. **Otra resolución.** Es la línea que TICKBAR-001 desbloquea para BigTrap2, y
   el mismo argumento aplica a Gaps2: m1 puede ser demasiado grueso para una
   señal de microestructura.
2. **Gaps como *feature*, no como regla.** Esta campaña probó reglas mecánicas
   de entrada/salida. Que una regla no tenga expectativa no implica que la
   variable no tenga información condicional.
3. **Aceptar el negativo y mover el foco** al segundo candidato (BigTrap2, vía
   TICKBAR-001).
