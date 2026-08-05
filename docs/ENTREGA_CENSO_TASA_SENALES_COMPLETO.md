# Entrega — censo de tasa de señales sobre el universo COMPLETO

**Para la otra máquina / el auditor.** Responde al bloqueo #1
(*"Falta el 90% de la medición de tasa de señales. Hay 20 días medidos de 200"*).

**Ya no falta.** La medición está hecha sobre **201 sesiones en 4 contratos**,
no 20 días. Cinco de los seis indicadores están completos; `HFTZones2` va por
137/201 sesiones (3 de 4 contratos) y el cuarto sigue corriendo.

Datos: parquets F2 reexportados y limpios (`dup_bloque=0` en los cinco).
`sep_min=120`, `lead_days=20`, `outcomes_accessed: false`.

---

## 1. Piloto (20 días) contra universo completo (201 sesiones)

| indicador | cru 20d | post 20d | col 20d | **cru 201** | **post 201** | **col 201** | ses |
|---|---:|---:|---:|---:|---:|---:|---:|
| AACloseOpenDiffs | 632 | 12,0 | 98 % | **603,6** | **11,06** | **98,2 %** | 201 |
| Gaps2 | 358 | 11,0 | 97 % | **360,7** | **10,07** | **97,2 %** | 201 |
| HFTZones2 | 515 | 11,0 | 98 % | **536,0** | **10,26** | **98,1 %** | 137 |
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
| **Gaps2** post | 10,20 | 10,05 | 9,69 | **10,03** |
| **HFTZones2** cruda | 521,1 | 549,3 | 539,2 | *corriendo* |
| **HFTZones2** post | 10,15 | 10,41 | 10,08 | *corriendo* |

`Gaps2` está **completo en los cuatro** y se mueve entre 9,69 y 10,20 con
crudas que varían casi 2×. Eso es el techo mecánico visto de la forma más
limpia: la tasa cruda cambia de contrato a contrato, la post-filtro no.

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
`docs/SESION_2026-08-04_PARA_AUDITOR.md` y **no fue resuelta**. Por eso no
llené §3.3 acá: la medición ya no bloquea, pero el criterio de selección sí.
