# IPC híbrido para MNQ — borrador v0.1

Pedido de Nico, 29/09/2026: una lógica intermedia entre acumulaciones de muchos
picos cercanos y niveles con menos picos en visitas separadas, que conserve varias zonas.

**Estado: IMPLEMENTADO, PRUEBAS SINTÉTICAS PASS; SIN CALIBRACIÓN NI CENSO REAL MNQ.**
No es señal de entrada, imán demostrado, filtro de trades ni modelo L2.

## 1. Qué se leyó y qué no se modifica

Fuentes leídas en el commit `4c29eed7afdc4d89ab054c39a1f66bff01150b6c`:

- `tools/peaks_rule.py`: picos monótonos; techo que no hace un máximo mayor que
  el anterior / piso que no hace un mínimo menor; sin mecha que cruce el último
  pico; límites de separación, paso y retroceso; pivote centrado confirmado con
  `w` velas posteriores. La geometría histórica completa no equivale a una zona
  disponible desde el primer pico.
- `tools/ipc.py`: configuración NQ `w=1`, `maxgap=30`, `maxstep=14`,
  `minpull=7`, `nmin=5`; filtro standard de al menos 7 picos y 40 velas,
  strict de 10 picos y 40 velas. Su cálculo de eventos distingue confirmación
  del pivote y origen de la geometría.
- `tools/ipc_nivel.py`: una nueva visita requiere alejamiento de 14 ticks;
  agrupa picos cercanos de una misma visita, exige al menos 3 visitas y admite
  hasta 200 velas entre picos. **La referencia de la segunda familia está
  trabajada en MES, no es una segunda calibración NQ ni MNQ.**

Los tres archivos y los parámetros congelados quedan intactos.
MNQ no hereda automáticamente resultados, costos ni parámetros calibrados de NQ/MES.

## 2. La lógica nueva

Un único detector, con evidencia combinada:

`evidencia = cantidad_de_picos + 2 × (cantidad_de_visitas − 1)`

Se crea zona con **al menos 3 picos y evidencia >= 6**:

| Ruta al confirmarse | Ejemplo mínimo | Sentido |
|---|---|---|
| DENSE | 6 picos, 1 visita | muchos picos cercanos |
| MIXED | 4 picos, 2 visitas | el punto intermedio |
| SPACED | 3 picos, 3 visitas | menos picos, con salidas claras |

La ruta se actualiza si la zona acumula nuevas visitas. No son tres backtests
ni tres motores diferentes. Dos picos, aunque estén muy separados, no alcanzan.

### Parámetros iniciales, propuestos para revisión visual

`docs/research/IPC_MNQ_HYBRID_DRAFT_20260929.json` contiene los valores:

- Pivote local: `w=1`; requiere una vela cerrada a cada lado.
  Una meseta de máximos iguales cuenta por su último extremo.
- Retroceso entre picos: al menos **7 ticks**. De 7 a menos de 14 ticks
  cuenta otro pico de la misma visita; desde **14 ticks** cuenta otra visita.
  La excursión usa sólo velas estrictamente entre los dos picos: no se inventa
  el orden intravela de dos mechas.
- Paso hacia adentro entre picos: máximo **7 ticks**.
  Techo no sube; piso no baja. Igualdad admitida.
- Ancho total máximo: **21 ticks**; no permite una escalera sin fin.
- Separación máxima: **60 velas**; corte por hueco temporal > **1.800 segundos**.
- Tick MNQ explícito: **0,25 puntos**. No confundir ticks de precio con
  la cantidad de operaciones de una vela 25t.
- Sin duración mínima de 40 velas: no se transporta ese filtro NQ.

Estos valores **no provienen de una optimización ni de juicios MNQ**. Tampoco
garantizan que aparezcan muchas zonas: eso se debe contar sobre datos reales.
El híbrido no es simplemente un promedio de todos los parámetros antiguos.

### Varias zonas y vida de cada una

Cada zona tiene ID propio. Un nuevo grupo a otro nivel puede crear otra zona;
no se elimina por solaparse temporalmente con una anterior.
Se conservan dos niveles simultáneos en la prueba sintética correspondiente.

Una mecha que supera el último pico rompe su zona (BROKEN). También termina
por separación excesiva (EXPIRED), cambio de sesión (SESSION_END) o hueco
de datos (DATA_GAP). No se rescata con picos de la sesión siguiente.

## 3. Causalidad y salida

`events` registra CREATE, UPDATE y CLOSE, con `available_i` y `available_at`.
Cada CREATE/UPDATE lleva una copia del estado conocido entonces.
La misma secuencia de eventos debe obtenerse leyendo sólo el prefijo disponible;
esa invariancia se prueba sin desenlaces.

`zonas` ofrece geometría compatible con la capa de picos del visor existente:
`kind`, `i0/i1`, `t0/t1`, `p0/p1`, `toques`, `picos`, además de `visitas`,
`route`, `creation_i`, `available_at`, confirmaciones y estado.

**`i0` no significa que la zona ya existiera.** El snapshot final está marcado
`final_geometry_visual_only=true`: contiene los picos acumulados después de crearla.
Para cualquier cruce con A o una entrada hay que reconstruir el estado desde
`events` hasta esa hora; jamás usar el snapshot final como filtro histórico.

## 4. Ejecutar en la PC

Python 3.10+; sólo biblioteca estándar, sin instalar paquetes.
Desde la raíz del repo:

```bash
python -m unittest discover -s tests/research -p "test_ipc_mnq_hybrid.py" -v
python tools/ipc_mnq_hybrid.py --input "RUTA/MNQ_BUNDLE.json" --output "RUTA/MNQ_IPC_HYBRID_REVIEW.json" --series tick_25 --config docs/research/IPC_MNQ_HYBRID_DRAFT_20260929.json
```

El bundle debe contener:

- identidad MNQ (`asset` o `meta.asset` o `meta.instrument`);
- `meta.tick_size=0.25`;
- `bar_series.tick_25.candles`, con `time`, `high`, `low`;
- `session` por vela, o `--sessions-json` con un array de IDs de sesión,
  de igual longitud y orden que las velas. Para una sola sesión conocida,
  se admite `--session-id ID` (span <= 24 h).

No se adivinan sesiones CME desde medianoche UTC. Usar el manifiesto/calendario
canónico con DST y feriados. Un bundle mensual sin sesiones explícitas se rechaza.

Si hay `closed_at` por vela, se respeta. Si falta, se usa conservadoramente el
inicio de la siguiente vela de la misma sesión y se omite la última de esa
sesión. Puede quedar un último pico sin confirmar: no se confirma al llegar al EOF.
Los índices exportados conservan su correspondencia con las velas originales.
No se ordenan ni deduplican timestamps iguales; inversión de reloj o precio
fuera de la grilla se rechazan. El bundle original no se modifica.

Se imprimen cantidad de zonas y velas cerradas. Guardar esos conteos y la salida,
que contiene hashes del bundle, código y configuración.

## 5. Antigravity / visor único

Instrucción para la sesión local:

> Ejecutá el detector sobre un bundle MNQ real, únicamente en desarrollo.
> No leas trades, retornos ni holdout. No cambies parámetros para mejorar P&L.
> Reportá conteos por DENSE/MIXED/SPACED y sesión. Verificá IDs de sesión y
> disponibilidad de cada pivote. Usá el visor canónico
> `viewer/nt8_bridge/index.html`, no construyas otro motor de precio.
> Para revisión geométrica, hacé backup de la capa local
> `bundles/peaks_det/<asset>.json` si existe y cargá la salida híbrida allí,
> con identidad de activo y serie 25t coincidentes. No subas bundles al repo.
> Mostrá explícitamente BORRADOR NO VALIDADO y las horas de confirmación.
> El dibujo final sirve sólo para juicio de geometría; no certifiques IPC
> “antes de A” hasta que el replay use events/available_at en vez del snapshot.
> Preservá los indicadores originales y documentá cualquier cambio del visor.

La integración temporal completa del visor **queda pendiente**. Compatibilidad
del formato no equivale a paridad visual certificada. No se ha corrido un censo
MNQ real en este sandbox: no hay aquí un bundle canónico de sus velas.

## 6. Evidencia y siguiente compuerta

18/18 pruebas sintéticas PASS, también con la disposición de archivos del repo:
rutas densa/mixta/separada, insuficiencia de dos visitas, rechazo de retrocesos
pequeños, confirmación tardía, invariancia por prefijos, simetría piso/techo,
reset de sesión/huecos, timestamps duplicados, anchura limitada, varias zonas,
conservación del bundle e índices.

Evidencia: `artifacts/ipc_mnq_hybrid_20260929/evidence.json`.

**NO MEDIDO:** cantidad real MNQ, acuerdo con Nico, sensibilidad de parámetros,
paridad visual causal, vínculo con espejo, veto de imbalance, atracción,
rentabilidad y costos. Holdout intacto; no se calcularon outcomes.

Próximo paso: tanda de geometrías reales para juicio ✓/✗, incluyendo ejemplos
de las tres rutas y casos rechazados. Congelar parámetros sólo después de esa
revisión. La tesis “sin picos el trade falla” sigue siendo una hipótesis, no
una regla demostrada.