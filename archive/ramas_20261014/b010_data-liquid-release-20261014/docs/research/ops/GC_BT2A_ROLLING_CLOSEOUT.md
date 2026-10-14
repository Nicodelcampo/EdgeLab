# Percentil BT2A: aceleración real del subpaso con paridad exacta

Job `138574550/v1`, `edgelab-gc-bt2a-rolling-percentile-v1`, COMPLETE; una intención cerrada y dos polls. Source benchmark `bf9b95ed2970639f92e107deacebceab27752f9e`, plan `c91b12d689ceeaa62ee0cb130e563814f15d40edb13855dd5c2e15475f4471ba`. Datos sóloKaggle, recibos y hashes públicos. No reenvíos ni nuevas auditorías de dataset.

## Resultado medido
Mismos470.027 ticksGC/cuatro sesiones consecutivas3–6 de agosto, tres perfiles BigTrap2Absorption originales. Scheduler secuencial idéntico para aislar el cambio de percentil. Historia y parámetros intactos.

| Modo producción | Repetición1(s) | Repetición2(s) | Mediana(s) |
|---|---:|---:|---:|
| Original |19,42211|19,78583|**19,60397**|
| Percentil incremental |13,06107|13,48988|**13,27547**|

**1,47671× de velocidad /32,28171% menos duración** del subpaso nativo push+finish. Ambos tiempos nuevos menores que ambos originales. Son repeticionesABBA del mismo tape, NO sesiones independientes ni experimento estadístico de mercado. No afirmar aceleración equivalente del pipeline completo, otros instrumentos o servicio24x7.

El host113,84900s incluye todos los pases, diagnósticos, descarga y entorno; no confundirlo con un pase13,28s. RSS muestreada~185MiB. Los dos pases diagnósticos no entran en el speedup de producción.

## Paridad observada y límites
- Cuatro pases de producción: fingerprints de estado semántico tras cada sesión yEOF, capturas, conteos, residuos y tamaños exactos.
- Dos pases diagnósticos(original,incremental): umbrales/a_thr, capturas y logs nativos completos exactos a través de hashes vinculados a la misma fuente.
- FIFO y orden estable de cache comparados mediante representación hex de los floats contra historia nativa tras cada sesión; sin acortar lookback, compartir estados o modificar scores.
- Tests sintéticos de cuatro tamaños de tick, tres perfiles, buffers/residuos ysame-ns. Esto certifica equivalencia del Python evaluado en esas entradas, NO paridad100%NT8 ni todas las configuraciones posibles.

## Integración deliberadamente explícita
BT2AStream dispone de `rolling_percentile=False` por defecto. El constructor de escena ahora puede reenviar `rolling_bt2a_percentiles=True` **en nuevos planes explícitos**, manteniendoFalse en los existentes. Roster/hash de parámetros nativos no cambia.

Los planes congelados anteriores no se editaron ni habilitaron: sus validadores rechazan añadir campos libremente. Para una corrida futura, crear plan nuevo con SHA permitido, registrar el opt-in en plan/recibo, incluir `rolling_native_percentile.py` en bundle y preservar presupuesto/custodia. La capacidad está integrada, pero no se cambió default de producción, desplegó enDebian ni promovió automáticamente un modelo.

## Pruebas y aprendizajes
Regresión933PASS en309,500s antes de reparar la actualización de argumentos del helper del benchmark. Un script local de edición falló por comillas y dejó ese helper sin nuevoskwargs; se corrigió **antes de cualquier envío**, se añadió test de caller que ejecuta ambos modos y ambosdiagnósticos. Después:4 tests focales +3 compatibilidadPASS; después del forwarding de escena:5 tests focalesPASS. No presentar la snapshot933 como ejecución sobre cambios posteriores.

Fuente nativa pinneada intacta; hooksAST validan censo1 sustitución de umbral/2 actualizaciones de cache. La optimización elimina trabajo repetido en vez de reducir rigurosidad. Firmas del detector, límites, calendario y retención no cambian.

Siguiente: usar opt-in en un nuevo plan científico/operacional acotado cuando corresponda y medir wall total; otro activo sería evidencia de transportabilidad de rendimiento, no otra auditoría de fuente. Retomar hipótesisA→E/E→A con base de historia continua equivalente; construir estado antes de filtrar labels futuros. Preservar el negativoGC previo y densidad como comparador. Holdout cerrado, sin P&L ni canonicalBrainwriter/merge/deployment.
