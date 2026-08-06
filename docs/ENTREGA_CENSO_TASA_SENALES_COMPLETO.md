# Entrega — censo de tasa de señales sobre el universo COMPLETO

**Para la otra máquina / el auditor.** Responde al bloqueo #1
(*"Falta el 90% de la medición de tasa de señales. Hay 20 días medidos de 200"*).

**Ya no falta, y ya no falta nada.** La medición está hecha sobre **201 sesiones
en 4 contratos**, con los **seis** indicadores completos.

> **Actualización 2026-08-06 01:16 UTC — la corrida terminó.** 44,1 h de
> cómputo (158.721 s). `diag/tasa_senales/post_sepmin.json` ahora tiene el
> detalle **por día** de los 6 indicadores sobre las 201 sesiones.
> Manifiesto: `session_count=201`, sin `indicadores_parciales`,
> `outcomes_accessed: false`, `output_sha256 c1e1601a33e1877d`.
> Ese archivo **reemplaza** la versión de 20 sesiones que estaba publicada; la
> anterior sigue en el historial de git.

Datos: parquets F2 reexportados y limpios (`dup_bloque=0` en los cinco).
`sep_min=120`, `lead_days=20`, `outcomes_accessed: false`.

---

## 1. Piloto (20 días) contra universo completo (201 sesiones)

| indicador | cru 20d | post 20d | col 20d | **cru 201** | **post 201** | **col 201** | ses |
|---|---:|---:|---:|---:|---:|---:|---:|
| AACloseOpenDiffs | 632 | 12,0 | 98 % | **603,6** | **11,06** | **98,2 %** | 201 |
| Gaps2 | 358 | 11,0 | 97 % | **360,7** | **10,06** | **97,2 %** | 201 |
| HFTZones2 | 515 | 11,0 | 98 % | **508,6** | **10,22** | **98,0 %** | 201 |
| BigTrap2 | 75 | 9,0 | 88 % | **79,4** | **8,84** | **88,9 %** | 201 |
| aVolCellPOI2 | 44 | 7,5 | 83 % | **42,3** | **6,50** | **84,6 %** | 201 |
| VolTicksPOC2 | 7 | 3,0 | 57 % | **7,3** | **3,41** | **53,4 %** | 201 |

**El piloto generalizó.** Los porcentajes de colapso coinciden a menos de un
punto en los seis. Las tasas post-`sep_min` bajan un poco en el universo
completo (el caso mayor es `aVolCellPOI2`: 7,5 → 6,50).

## 2. Lo que confirma y lo que corrige

**Confirma el régimen f≈10.** Cinco de los seis caen entre 6,50 y 11,06 con
tasas crudas que van de 42 a 604. La saturación de `sep_min` es real y está
medida sobre el universo entero, no inferida de 20 días.

**Corrige una cosa:** `VolTicksPOC2` queda en **3,41**, fuera de la banda
f ≈ 7–12. Ya estaba fuera en el piloto (3,0), así que la frase *"todos caen en
f ≈ 7-12"* no aplica a los seis sino a los cinco de tasa cruda alta. En
`VolTicksPOC2` `sep_min` **no satura**: sobrevive el 46,6 % de las señales
contra el 1,8 % de `AACloseOpenDiffs`. Es el único que no está contra el techo
mecánico, y por eso es el único cuya tasa post-filtro dice algo del indicador y
no de la estructura de la sesión.

**`MIN_STUDENTIZED_SESSIONS=160`**: los seis lo superan. El peor caso es
`aVolCellPOI2` con **177** sesiones con al menos una señal (24 días en cero,
6 de ellos en un solo contrato de 13 sesiones — anomalía registrada, sin
interpretar).

## 3. Detalle por contrato de los dos caros

| | c1 `03-26` (60) | c2 `06-26` (64) | c3 `09-26` (13) | c4 `12-25` (64) |
|---|---:|---:|---:|---:|
| **Gaps2** cruda | 440,0 | 381,6 | 219,9 | 294,1 |
| **Gaps2** post | 10,20 | 10,05 | 9,69 | 10,03 |
| **HFTZones2** cruda | 521,1 | 549,3 | 539,2 | 450,0 |
| **HFTZones2** post | 10,15 | 10,41 | 10,08 | 10,14 |

**Los dos caros están completos en los cuatro contratos.** `Gaps2` se mueve
entre 9,69 y 10,20 con crudas que varían **2×** (219,9 a 440,0); `HFTZones2`
entre 10,08 y 10,41 con crudas de 450,0 a 549,3. Es el techo mecánico visto de
la forma más limpia que hay: la tasa cruda cambia de contrato a contrato, la
post-filtro no se mueve.

### Sesiones con al menos una señal (para `MIN_STUDENTIZED_SESSIONS=160`)

| indicador | sesiones con señal | días en cero |
|---|---:|---:|
| AACloseOpenDiffs · HFTZones2 · Gaps2 · BigTrap2 | **201** | 0 |
| VolTicksPOC2 | 199 | 2 |
| aVolCellPOI2 | **177** | 24 |

Los seis superan el mínimo. Cuatro no tienen un solo día en cero.

## 4. Artefactos

| qué | dónde |
|---|---|
| JSON de los 4 rápidos, universo completo | `diag/tasa_senales/post_sepmin_rapidos.json` |
| manifiesto de esa corrida | `...post_sepmin_rapidos.run_manifest.json` |
| detalle y método | `docs/REPORTE_LOCAL_2026-08-04f.md` |
| checkpoint (contrato × indicador) | `diag/tasa_senales/post_sepmin.py`, commit `887c6f5` |

El manifiesto declara `indicadores_parciales: true` y
`faltan_indicadores: [Gaps2, HFTZones2]` porque esa corrida fue del subconjunto
rápido; los dos lentos vienen de la corrida completa que sigue en curso y sus
agregados están arriba.

---

## 5. DOS ADVERTENCIAS antes de llenar §3.3

**(a) Estos números son de `time:1`.** Por el marco de TICKBAR-001 —*"`time:1`
fue el laboratorio donde se verificó la fidelidad del traductor, no el hábitat
de la hipótesis"*— la tasa de `BigTrap2` es la del laboratorio. `BigTrap2` es
un detector de microestructura y su hábitat son las barras de tick, donde **la
paridad todavía está rota**: PRED-003 refutada con 3,91 % de mismatch en K=25 y
81,78 % en K=10. El fix (v2.3, atribución por OHLCV único) está implementado y
pusheado pero **sin compilar ni validar en NT8**.

Para `Gaps2` no aplica: su campaña CAMP-001 es `time:1` por diseño y su oráculo
está en PASS 1316/1316.

**(b) La tasa post-`sep_min` casi no discrimina entre indicadores.** Las crudas
abarcan un factor de 83 y las post-filtro colapsan a 3,2. Elegir hipótesis
comparando tasas post-filtro es comparar la estructura de la sesión, no los
indicadores. Si §3.3 va a usar la tasa como criterio de selección, conviene
hacerlo **antes** del anti-solapamiento o con un `sep_min` que no sature.

Esto está registrado como decisión **D3** en
`docs/SESION_2026-08-04_PARA_AUDITOR.md` y **no fue resuelta**.

**(c) CORRECCIÓN — esto NO desbloquea §3.3.** *(agregada 2026-08-06, tras leer
`efe0397` de la otra máquina.)*

Escribí más arriba que *"la medición ya no bloquea, pero el criterio de
selección sí"*. **Es falso, y la corrección es importante.**

Este censo mide **creaciones de zona**, no primeros toques. Está declarado en
el manifiesto desde el principio —`event_anchor_policy: zone_created_ms`,
`population_note: "cuenta creaciones; no equivale automaticamente a
first_touch"`— pero mi redacción no cargó esa distinción con la fuerza que
correspondía. La población autoritativa para §3.3 es el **primer toque**, y ésa
es **otra medición**.

El censo de primeros toques de la otra máquina encontró además que cuatro de
los seis indicadores no pueden entrar por contrato de evento, y que
`AACloseOpenDiffs` produce un **fail-open**: emite 23.629 `ZONE_CREATED` y
**cero** `ZONE_TOUCHED`, con lo cual el censo salía `status=COMPLETE` y
`raw_count=0`. Un cero con formato de medición, cuando la verdad es que el
indicador no tiene concepto de toque.

**Lo que este documento sí sostiene**: el censo de tasa de señales
*outcome-free* está completo sobre el universo entero, y la saturación de
`sep_min` está medida y confirmada en los seis indicadores.

**Lo que NO sostiene**: que §3.3 pueda llenarse. Por `efe0397`, hoy no puede
llenarse por ningún camino — solo `BigTrap2` produce la población autoritativa
y está bloqueado por PRED-004, cuyo hábitat son las barras de tick donde la
paridad sigue rota.
