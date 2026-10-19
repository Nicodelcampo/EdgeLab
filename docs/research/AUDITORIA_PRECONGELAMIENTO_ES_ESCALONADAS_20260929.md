# ES-ESCALONADAS — auditoría de precongelamiento

Continuación del traspaso de la Entrada 076. Rama
`foundation/f0b-compatibility-probe`; código leído en
`258ca9969556e0a5b8cd17c976c6cf75704aa9d4`.

**Veredicto: snapshot de código/parámetros registrado; certificación de
entrada y congelamiento operativo PENDIENTES. No se autoriza un test de retornos.**

## Hecho, sin modificar detectores ni visor

Se leyeron `tools/escalonadas_det.py` y `tools/peaks_rule.py`.
Los parámetros de PLANAS v2 y EMPINADAS v2, tick ES 0,25 y confirmación por
precio de 2 ticks quedan capturados en
`ES_ESCALONADAS_SNAPSHOT_PRECONGELAMIENTO_20260929.json`.
Incluye SHA-256 de ambos códigos y hash de la configuración conjunta.
No se ajustó un parámetro.

Se ejecutaron las funciones originales, extraídas por AST, sobre 64 trayectorias
sintéticas para cada familia: **128 casos, 101 detecciones comprobadas,
0 discrepancias de campos de detección al reconstruir sólo el prefijo**.
Una geometría sintética de tres techos confirma además el caso mínimo.
Esto prueba esos casos, no todos los caminos posibles ni la certificación
de fills intravela.

La ejecución de referencia omite el decorador numba y las importaciones
de entrenamiento ajenas a las funciones usadas. No es una prueba integral
del CLI, de JIT, del entorno con pins ni de los ticks reales.
Evidencia sintética publicable:
`artifacts/es_escalonadas_audit_20260929/synthetic_evidence.json`.

## Bloqueos que deben viajar con el snapshot

### 1. `det_t` no identifica todavía el instante operable

El código asigna `det_t = cd["t"][det_i]`, y `cd["t"]` viene de
`candles[].time`. No publica si es apertura, cierre o un tiempo representativo.
La confirmación por precio mira los extremos completos de la vela.

`det_precio` es el nivel propuesto de disparo a 2 ticks del pico, **no un fill
observado**. Dentro de una vela que cruza el pico y el umbral opuesto, el OHLC
no identifica qué ocurrió primero. El código rechaza la confirmación si esa
vela supera el pico; no se debe interpretar el rechazo ni la aceptación como
replay de una orden stop.

Antes del manifiesto: separar `bar_i`, `bar_time`, `available_at_close` y,
si se pretende entrar intravela, `trigger_tick_ts`/precio y orden temporal
de invalidación/confirmación. Verificarlo desde ticks canónicos.
Si se cambia a entrada al cierre, requiere decisión explícita de Nico:
no sustituir silenciosamente la entrada elegida.

### 2. La geometría final no es el estado al disparar

`picos`, `toques`, `p0/p1` y `fin_serie_i` pueden incorporar continuación
posterior a la detección. El código calcula `det_pico`, `det_nivel` y
`det_idx` por separado: esos campos no hacen causal el resto del snapshot.

Para el futuro runner o un visor ciego, usar sólo los picos disponibles al
disparo y una copia inmutable de sus bordes. No filtrar eventos ni fijar
stop/target a partir del último pico del archivo completo. Un dibujo de toda
la serie sirve para revisión retrospectiva, no como test ciego.

### 3. Procedencia y sesiones: todavía sin certificación

El paquete adjunto contiene capas y juicios, no el bundle de velas fuente ni
los ticks. No aporta por sí solo proveedor, hash del bundle, manifiesto de
sesiones CME, reloj o hash del código que generó cada capa.

La pausa heurística >1.800 segundos no sustituye un ID de sesión canónico,
ni el conteo de fechas UTC sirve para afirmar zonas por sesión CME.
Faltan el reset explícito de sesión y la verificación de reloj/duplicados.

Por esta brecha de proveedor y la regla «nada derivado de Lucid al repo»,
**no se subieron capas, juicios, velas, sus CSV de perfil ni evidencia
cuantitativa derivada de esas geometrías**. El resultado privado queda
local. Lo publicado aquí es código, configuración ya existente y sintético.

### 4. Juicios de Nico: identificar la versión juzgada

El archivo principal agrupa juicios acumulados; su campo `model` identifica
el esquema, no un hash de detector/parámetros. No atribuir todos sus juicios
a PLANAS v2 ni reemplazar los denominadores del traspaso sin reconstruir
qué tanda/version se juzgó.

Congelar manifiesto de juicios con hash, detector y criterio de inclusión;
si se hace nueva tanda, ocultar toda vela posterior al momento revisado,
incluyendo estados derivados futuros.

## Orden de continuidad

1. **Pedir bundle ES febrero + manifest/hash/proveedor**, y contrato de reloj.
   Para certificar disparos stop intravela se necesitan los ticks de las
   ventanas o un replay local con informe trazable.
2. Reconciliar fuente → detector → capa → visor; contar por sesión/hora CME
   y medir solapamiento usando geometría **as-of**, no el dibujo final.
3. Cerrar las brechas anteriores y ratificar el snapshot operativo.
   No es un rechazo de la idea ni un cambio de parámetros.
4. Redactar manifiesto de pocas celdas, MDE, control emparejado, costos
   diferidos y réplica. **STOP hasta OK explícito de Nico.**
5. L2 ES jul–sep permanece otra campaña: conseguir velas 25t correspondientes
   antes de emparejar defensas, y no reutilizar climas ES rechazados.

Los otros pendientes del traspaso (extracción MNQ, MES, purga git, cambios
del visor) no se ejecutaron ni se modificaron en esta auditoría.
No hay acceso al estado de procesos de la PC de Nico desde este sandbox.

## Reproducir localmente, sólo target-free

Desde una copia aislada con el código correspondiente al snapshot:

```bash
python tools/audit_es_escalonadas_targetfree.py --input-root RUTA_PAQUETE_EXTRAIDO --source-root tools --out RUTA_LOCAL_AUDITORIA --source-commit 258ca9969556e0a5b8cd17c976c6cf75704aa9d4
```

No escribir `--out` sobre datos originales. La herramienta produce perfiles
geométricos, copia del código analizado y evidencia; **los outputs del
paquete privado no son material para subir al repo**.
El hash de commit declarado debe verificarse con la worktree real.

## Aporte al referente

Las dos geometrías tienen un snapshot reproducible y un chequeo sintético
de detección por prefijos, pero se evita confundir un nivel dibujado y la
hora de una vela con una entrada ejecutable.