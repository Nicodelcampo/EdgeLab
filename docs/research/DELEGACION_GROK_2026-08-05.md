# Delegación a Grok 4.5 — PRED-004, ronda posterior a G1

**Tip a auditar:** `ab91dce` en `fix/capture-probe-v2-contract`
**Quién escribe:** Claude, que implementó G0 (`2da4c41`) y G1 (`ab91dce`).
**Grok no puede leer el repo:** todo el código necesario está pegado en el
Anexo A, con número de línea real.
**Por qué existe este documento:** el auditor se quedó sin créditos. La regla
*"el que implementa no aprueba su propia reparación"* —que las tres iteraciones
declararon— queda sin cumplir si nadie ocupa ese rol.

> **Ninguna de las tres iteraciones ni este documento son autoridad.** Verificá
> contra el código y citá archivo:línea. Si algo acá es falso, decilo: ya pasó
> dos veces en este expediente que una afirmación mía resultara falsa
> (el inventario vencido, y el "menor 3" declarado corregido a medias).

## Reglas duras, heredadas y no negociables

- **No abras NT8, ni el holdout, ni outcomes.** No muevas el pin del `.cs`.
- **No uses `run_nt8_bridge.py` ni `correr_gates.py`** para PRED-004: está
  verificado en código que miden otra cosa (paridad Python↔NT8, no
  v2.1-log vs v2.4-log).
- **No edites `tools/pred004_analyze.py` ni `tests/bridge/test_pred004_analyze.py`.**
  Yo sigo trabajando ahí; si los tocás vamos a chocar. Escribí hallazgos, no parches.
- Todo test que se proponga **cita la línea del `.cs`** que emite el evento que
  fabrica, y declara **`emisor_fiel`** o **`emisor_adversarial`**.
- Toda tasa que se proponga **declara su población**.

---

## G-1 · Inventario de N1 — `seq` *(el más bloqueante, empezá por acá)*

**Por qué importa.** P5 compara `seq` **absoluto**, y `eventSeq++` es un
contador **único y compartido** (`BigTrap2.cs:892`, dentro de `LogEvent`) entre
los **12 puntos de emisión**. Un diagnóstico agregado en v2.4 puede **correr el
`seq`** de un evento económico sin cambiar una coma de su contenido económico, y
P5 lo leería como diferencia. N1 bloquea G2, y Kimi mostró que además bloquea la
doble contabilidad emisor/analizador (H-KIMI-5).

**Entregable — una tabla, sin opinión adosada:**

| # | línea `.cs` | tipo `LogEvent` | ¿económico? | camino: tiempo / tick / ambos | ¿existía en 2.1? |
|---|---|---|---|---|---|

Los 12 sitios están en el **Anexo A.1**, con su método contenedor. "Camino" = si es alcanzable con
`fpTicksPerBar <= 0` (tiempo), con `> 0` (tick), o los dos. **Ese es el dato
central**: si el camino de **tiempo** no ganó ni perdió emisiones entre 2.1 y
2.4, el `seq` absoluto es comparable y P5 queda intacto. Si las ganó o perdió,
P5 tiene que cambiar y **eso es cambio de contrato, que sólo aprueba Nico**.

**No propongas la reparación todavía.** Primero la tabla. Grok-2 ya recomendó
"identidad económica + reportar `delta_seq`"; puede ser correcto, pero sin el
inventario es elegir por conveniencia.

## G-2 · La pregunta que decide P3 *(chica y de alto rendimiento)*

Descubrí en G1 que hay **dos emisores de `FOOTPRINT_MISMATCH` con esquemas
distintos**:

- `BigTrap2.cs:541` (`ReportarMismatch`) → **5 pares, con `vol_blk`/`vol_bar`**
- `BigTrap2.cs:601` (rotura de bloque) → **4 pares, SIN volumen**

Con la regla fail-closed que dejé, basta un par procesado sin esquema completo
para que **P3 = `NO_APLICA`**. Si `.cs:601` es alcanzable en capturas reales, P3
podría no dar veredicto **nunca**.

**Contestá dos cosas, con línea:**

1. ¿`.cs:601` es alcanzable en el camino de **tiempo**, o sólo en el de tick?
2. ¿El bloque de `.cs:601` tiene el volumen **disponible** para emitirlo, o
   habría que calcularlo?

De (1) depende si agregarle volumen toca P5. Si toca P5, es N1 y no se hace acá.

## G-3 · K1 — admisibilidad del oráculo de P5 frente a INC-005

El hallazgo bloqueante de Kimi, que yo **verifiqué y es cierto**:
`edgelab/research/universo_estudio.py:85` nombra literalmente
`BigTrap2_time1_v2` entre las tres extracciones que quemaron
2026-07-01→07-24, y las líneas 124-128 dicen que *"ni siquiera una apertura
sancionada entrega días quemados"*.

**Lo que falta, y es lo que te toca:**

1. ¿`BigTrap2_time1_v2` (comentario de cuarentena) **es** el
   `oracles/BigTrap2_time1_6E_0926_v2.csv` del preflight? Comparar **nombre,
   ventana e instrumento**. La coincidencia del extremo superior
   (`17:59:20` vs `17:59`) es fuerte pero **no es prueba**.
2. **Localizar el código o el reporte del censo** que produjo esa lista de tres
   oráculos, y citar la línea. Kimi no lo encontró.

**PROHIBIDO** abrir el CSV para "ver si se parece". Es un archivo íntegramente
dentro del holdout sellado y de la cuarentena. Metadatos de sistema de archivos
y lo que digan los documentos: nada más.

Mi lectura, para que la puedas atacar: **P5 sí es admisible**, porque la
cuarentena quema días como **muestra inferencial** y P5 compara bytes de
EventLog para detectar una regresión del `.cs` — no lee el mercado. Pero no está
escrito en ningún lado, y **la ausencia se está tratando como permiso**.

## G-4 · Adjudicación de mi parche G1

Revisá `ab91dce` como si no supieras qué buscaba. En particular:

- La rama `denom == 0`: ¿es **alcanzable de verdad** ahora, y publica el mismo
  conjunto de claves que la salida normal? El defecto original sobrevivió porque
  el test que la nombraba **abstenía antes de llegar**.
- `--exigir-version`: ¿se puede llegar a una **medición** con procedencia
  incoherente por algún camino que no cubrí?
- Las poblaciones nuevas (`mismatch_total_en_procesadas` vs
  `mismatch_total_todas_las_barras`): ¿**cierra** ahora la reconciliación, o
  quedó otro par de nombres hermanos con poblaciones distintas?
- **La pregunta que más me importa:** ¿queda alguna **cuarta** instancia del
  modo de falla de B3/H2/H-GPT-1 — una rama o un veredicto cuyo test lo nombra
  pero no lo alcanza? Ya aparecieron tres. Asumí que hay una cuarta.

## Lo que NO te toca

`tools/pred004_analyze.py`, `tests/bridge/test_pred004_analyze.py`,
`nt8/BigTrap2.cs`, el preflight y el gate de compilación (T6/G3). Eso lo hago yo
en paralelo, y si los dos escribimos ahí chocamos.

## Formato de entrega

**Grok no tiene acceso al repo ni puede commitear**, así que devolvé el
contenido en markdown y yo lo commiteo como
`docs/research/ITERATION_4_GROK_2026-08-05.md` sin editarlo, con autoría
declarada.

Clasificá cada ítem como **confirmación / refutación / extensión / hallazgo
independiente**, con archivo:línea (las líneas del anexo son las reales). Los
desacuerdos se **registran**, no se resuelven por mayoría.

Si algo que necesitás no está en el anexo, **pedilo por nombre y línea** en vez
de suponerlo. Suponer es exactamente como se coló el `verif` inexistente.
