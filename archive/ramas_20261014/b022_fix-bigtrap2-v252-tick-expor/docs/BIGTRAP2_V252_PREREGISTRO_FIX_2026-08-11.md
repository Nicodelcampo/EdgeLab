# Pre-registro: BigTrap2 v2.5.2 — fix del export en `tick:25`

> Rama: `fix/bigtrap2-v252-tick-export`, desde `audit/p0-bigtrap2-drift@1916ffa890a6eba132566826beb9f513663d7b79`.
> Hash `docs/NORTH_STAR.md` (cuerpo hasta `SHA256-BODY-ABOVE`):
> `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.

## Contexto

`docs/P0.1_BIGTRAP2_DRIFT_ADJUDICACION_2026-08-11.md` documentó el drift entre
`nt8/BigTrap2.cs` v2.5.1 y el kernel Python en la interrupción por oráculos del
2026-08-11: `time:1` PASS limpio (230/230, dt=0ms en todas), `tick:25` FAIL
(293/322 matched_pairs; MISSING_IN_NT8=29, TIMESTAMP_DIFF=253, MATCHED=40,
FEATURE_DIFF=1, MISSING_IN_PYTHON=29).

Una auditoría independiente sobre los logs completos (no solo la ventana del
gate) y la reproducción propia de esta campaña (Fase 1, read-only, sobre el
mismo HEAD) confirmaron, número por número, que la geometría y el ciclo de
vida son **idénticos**: 413/413 zonas, cero ids exclusivos, cero mismatches de
`created_bar`/`side`/geometría en medio-ticks, cero mismatches de estado final
o `touches`, 2.329/2.329 eventos de lifecycle exactos como multiset y en
secuencia por zona. El único faltante real es 1 `TRAP` (`bar=12398`,
`vol=9 < MinTrapVolume=30`, no genera zona, pero viola `MinExportVolume=1`).
El FAIL de `tick:25` **no es un defecto de detección — es un defecto de
exportación de timestamp**, confirmado leyendo directamente el código fuente,
no solo por patrón estadístico.

## Defectos identificados (verificados contra el código fuente)

### D1 — atribución temporal: `LogEvent` usa `Time[0]`, no `s.Time`

`LogEvent(string type, string payload)` (`BigTrap2.cs:904`) estampa cada línea
con `Time[0]` (`BigTrap2.cs:946`) — el reloj **vivo** del callback donde se
invoca `LogEvent`, no el de la barra que el evento describe. Siete call sites
ya reciben un `BarSnap s` (con `s.Time` correcto, capturado inmutablemente en
`OnBarUpdate` al cerrar cada barra primaria, `BigTrap2.cs:304-306`) y no lo
usan: `ANCLAJE_VERIFICADO` (L499), `BARRA_PROCESADA` (L528), `TRAP` (L810),
`ZONE_CREATED` (L827), `ZONE_EXPIRED` (L843), `ZONE_TOUCHED` (L855),
`ZONE_INVALIDATED` (L866).

En `time:1`, `DrainReadyBars()` (camino de tiempo, `BigTrap2.cs:390-404`)
drena sincrónicamente dentro del mismo `OnBarUpdate` que encoló el snapshot
(`BigTrap2.cs:304-315`): `Time[0]` todavía no avanzó, el bug queda **dormido**
(dt=0ms en 230/230, confirmado). En `tick:25`, `DrenarPorOHLCV`
(`BigTrap2.cs:413-545`) puede dejar un snapshot en `snapQ` durante varios
callbacks BIP0 más mientras el ancla o el bloque no están listos; para cuando
`LogEvent` finalmente corre, `Time[0]` ya avanzó N barras. Consistente con la
distribución medida: 40/322 dt≤1.000ms, 253/322 en (1.000, 60.000]ms, 29/322
>60.000ms, todos **positivos** (NT8 siempre después de Python), máximo
460.340ms.

### D2 — drenaje de cola: nada drena al final del stream

`DrainReadyBars()` solo se alcanza desde `OnBarUpdate` cuando
`BarsInProgress==0` (`BigTrap2.cs:275,315`). Cuando `BarsInProgress==1`,
`AccumulateTick()` corre y **retorna sin drenar** (`BigTrap2.cs:270-273`).
`State.Terminated` (`BigTrap2.cs:257-264`) solo hace
`eventWriter.Flush()/Dispose()` — cero llamado a drenaje. Si el stream termina
con snapshots ya cerrados pendientes en `snapQ` o bloques ya completos en
`curBlock`, quedan atrapados para siempre. Consistente con: NT8
`BARRA_PROCESADA` termina en `bar=12397` mientras Python (`p1a_report.json`,
misma ventana) cuenta `n_bars=12400` — 3 barras residuales nunca exportadas.
Consistente con el único `TRAP` exclusivo de Python en `bar=12398`, fuera del
rango que NT8 alcanzó a drenar.

### D3 — blind spot del matcher de paridad (síntoma de D1, no defecto propio)

El matcher de `tools/run_nt8_bridge.py` empareja primero por proximidad
temporal dentro de `tol_created_ms`. Con timestamps corrompidos por D1, puede
preferir un par cercano en tiempo pero de identidad distinta sobre el par
correcto. Confirmado numéricamente: `py 6095_S` (delta propio a
`nt8 6095_S` = 47.544ms) fue emparejado por el gate con `nt8 6093_S` (delta
cruzado = −34.040ms, con menor valor absoluto) — produce el único
`FEATURE_DIFF` (`touches py=5 nt8=6`, que son dos zonas **distintas**, no una
discrepancia real de detección). **No se toca el matcher en este fix**: D3 es
un síntoma esperado de D1: la expectativa declarada es que se disuelva solo al
corregir D1 y recapturar oráculos frescos, no que requiera cambio de código en
el matcher.

### D4 — blind spot de cobertura `BARRA_PROCESADA`/`TRAP`

El gate de paridad actual compara zonas, no cobertura de barras procesadas ni
de eventos `TRAP` exportados. La pérdida de 3 barras (D2) y de 1 `TRAP`
(`bar=12398`) no dispara ningún FAIL de paridad hoy porque esa barra no
alcanzó a producir una zona con volumen ≥ `MinTrapVolume`. **No se cambia el
gate de paridad en este fix** (fuera del alcance del fix mínimo declarado);
se documenta como brecha de cobertura conocida vía T6.

## Justificación económica

Ninguna directa — esto es integridad de instrumentación, no un edge. Indirecta:
P0.1 es un bloqueo de procedencia que impide cerrar la adjudicación NT8↔Python
de BigTrap2 en `tick:25`; sin resolverlo, ningún hallazgo target-free medido en
`tick:25` tiene procedencia de paridad limpia. La campaña estadística activa
(`research/bigtrap2-distance-matched-null`, PR #11) usa exclusivamente
`time:1` — ya PASS, no depende de este fix.

## Cómo podría refutarse

- Si tras el fix + recompilación + recaptura de oráculos frescos v2.5.2,
  `tick:25` sigue en FAIL con un patrón de diagnóstico **no** dominado por
  `TIMESTAMP_DIFF`, D1/D2 no eran la causa completa.
- Si el conteo de residuales al final del stream no es exactamente 3 tras el
  fix (debería drenar hasta el último snapshot con bloque verificable), D2 no
  está bien caracterizado.
- Si T1-T4 no pueden expresarse como aserciones estáticas verificables sobre
  el texto fuente sin ejecutar NinjaScript real, la verificación de este fix
  queda incompleta hasta que Nico corra la recaptura manual en NT8 — esa
  verificación en tiempo de ejecución no es sustituible desde este entorno.

## Criterios de aceptación

1. Los 7 call sites D1 usan `s.Time` (vía un nuevo `LogEventAt`), no `Time[0]`.
2. `SESION_RESINCRONIZADA` (único diagnóstico nacido de un tick, no de un
   `BarSnap`) usa `tEv`, no `Time[0]`.
3. BIP1 intenta drenar snapshots ya listos sin exigir otro callback BIP0
   (FIFO, sin reanclar, sin adivinar, sin alterar OHLCV).
4. `State.Terminated` drena snapshots de barras primarias cerradas con bloque
   verificable; no fabrica ni procesa una barra primaria incompleta.
5. `time:1` mantiene payloads semánticos bit-idénticos (dt=0ms en 230/230)
   tras el fix — el camino de tiempo no se toca.
6. Ningún parámetro, tolerancia, geometría o campo de lifecycle del kernel
   Python se modifica.
7. Bump de versión a v2.5.2 en el único literal que la declara
   (`BigTrap2.cs:927`, meta-línea del export).

## Fuera de alcance (explícito, para decisión posterior de Nico/auditor)

- Cambios al matcher/gate de paridad (`tools/run_nt8_bridge.py`): D3/D4 quedan
  como blind spots **documentados**, no resueltos en este fix.
- `FOOTPRINT_MISMATCH` (`BigTrap2.cs:595,655`) y `ANCLAJE_AMBIGUO`
  (`BigTrap2.cs:557`) también reciben un `BarSnap s` y comparten la misma
  exposición estructural a D1 (mismo patrón: `Time[0]` en vez de `s.Time`),
  pero no están nombrados explícitamente en la instrucción de fix mínimo. Se
  dejan sin tocar (`Time[0]`) — no es una decisión unilateral de alcance, se
  señala aquí para que se decida explícitamente.
- Recompilación en NT8 y recaptura de oráculos frescos: manual, fuera del
  alcance de esta sesión (instrucciones exactas al final de la entrega).

## Aporte al referente

Reduce distancia hacia un edge operable en la dimensión de ejecutabilidad
real / trazabilidad (jerarquía #4/#6): cierra el bloqueo de procedencia P0.1
sobre `tick:25` sin tocar geometría, kernel Python ni el `time:1` que ya
sostiene la campaña estadística activa. No mide P&L ni retornos — permanece
fuera del alcance del STOP.
