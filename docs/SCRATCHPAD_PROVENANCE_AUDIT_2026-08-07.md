# Acta de procedencia — barrido del directorio temporal

**Fecha:** 2026-08-07 · **Alcance:** los 92 archivos del scratchpad de la sesión
**Pedido por:** el auditor, tras aceptar `bc56d1b` + `5b4d9ac`
**Reproducible:** `python tools/auditar_procedencia.py <dir_temporal>`

> **Por qué se hizo.** Un barrido parcial —el de los dos documentos de entrega—
> ya había encontrado **dos afirmaciones publicadas cuya evidencia vivía sólo en
> un directorio temporal**. Encontrar dos eleva la probabilidad de que haya más,
> no la baja. Este es el barrido completo.
>
> **Y el barrido tuvo que ser auditado a su vez.** Reportó dos hallazgos —«RSS
> sin origen recuperable» y «99/97 no reproducible»— que **el auditor rechazó y
> con razón**: los dos eran errores de lectura míos, no defectos del registro.
> Están rectificados en §3 y §4, **con el error a la vista**. Borrarlos sería
> exactamente lo que esta acta persigue.

## 0. Criterio de cierre

| criterio | resultado |
|---|---|
| afirmaciones vivas con evidencia sólo temporal | **0** |
| rutas citadas no versionadas | **0** |
| temporales sin clasificar | **0** |

92 archivos inventariados, 92 clasificados, **ninguno en clase E**.

| clase | qué significa | n |
|---|---|---:|
| **A** | sostiene una afirmación viva → versionar + hash + verificador | **4** |
| **B** | reproducible desde el repo → registrar comando, temporal descartable | **10** |
| **C** | supersedido o diagnóstico descartado → registrar motivo, no versionar | **43** |
| **D** | sin referente publicado vivo → descartable | **35** |
| **E** | dudoso → **bloquea el traspaso** | **0** |

## 1. Clase A — lo que se rescató

### 1.1 `tmp:e1.json` / `tmp:e2.json` — ya estaban rescatados

Los dos artefactos de la equivalencia 1-vs-2. Versionados en `bc56d1b` como
`diag/tasa_senales/equivalencia_workers__w1_70s.json` y
`diag/tasa_senales/equivalencia_workers__w2_70s.json`, con
acta de `sha256` y `verificar_equivalencia_workers.py` fail-closed.

### 1.2 `tmp:rss.log` / `tmp:rss2.py` — **hallazgo nuevo de este barrido**

Son la **única evidencia preservada** del RSS pico y del veredicto EXACTA que el
artefacto publica. El instrumento está ahora versionado como
`diag/tasa_senales/medir_rss_y_equivalencia.py` y su salida como
`diag/tasa_senales/rss_y_equivalencia_70s.log`.

## 2. Lo que NO se encontró, y conviene decirlo

**No apareció ninguna afirmación viva sin respaldo.** El RSS y el 99/97 parecían
serlo y **no lo eran** (§3 y §4): en los dos casos el error fue de lectura mío,
no del registro. Los 43 de clase C son
pilotos supersedidos por la corrida de 201 sesiones, checkpoints de reanudación
y scripts de parche cuyo efecto ya está commiteado. Los 35 de clase D son
borradores con gemelo exacto versionado, material de la delegación a Grok
—cancelada— y diagnósticos de julio ya cerrados en su acta.

### 2.1 Una alarma que se revisó y NO era

`tmp:tick25_junio.csv` y `tmp:tick25_julio.csv` son capturas NT8 con cabecera
`# meta indicator=BigTrap2,version=2.2`, y la de julio tiene eventos del
**2026-07-12 → 07-17, dentro del holdout sellado**. No están en
`docs/oraculos_manifiesto.json`.

**Revisado: no es material sin declarar.** Los eventos de las dos son
**subconjuntos** del oráculo `oracles/BigTrap2_tick25_6E_0926_v22.csv` —que está
gitignoreado **por política**, no por olvido, y declarado en
`docs/oraculos_manifiesto.json`—; y el acceso a esa ventana está registrado en
`docs/holdout_access_log.md` como apertura no planificada (nota 3, 2026-07-27).

**Pero es una observación de higiene que vale registrar:** rebanadas derivadas
de datos de ventana sellada salieron del store y quedaron sueltas en un
temporal. No es una brecha —el original está declarado y gateado— pero el store
dejó de ser el único lugar donde vive ese material. Destino: **borrar del
temporal**, no versionar.

## 3. El RSS publicado — nomenclatura, no medición fantasma

> **RECTIFICACIÓN.** La primera versión de esta sección afirmaba que los valores
> publicados «no coinciden» con la medición preservada y que su **origen no era
> recuperable**, con la hipótesis de que vinieran de una corrida inválida de 12
> sesiones. **Eso era falso, y lo corrigió el auditor.** Se deja el error a la
> vista: borrarlo sería exactamente lo que esta acta persigue.

`curva_excursion_ticks.json` publica, dentro de `equivalencia_workers`:

> `"… RSS pico 1.925 vs 2.734 MB."`

Y la medición preservada dice:

```
workers=1: rss_pico_gb 1.88     workers=2: rss_pico_gb 2.67
```

**Son los mismos números.** El punto es separador de **miles** —notación es-AR,
la misma que usa todo el repo («84.000 s de CPU», «144.511 zonas»)—:

```
1,88 GiB x 1024 = 1925,1 MiB  ->  1.925
2,67 GiB x 1024 = 2734,1 MiB  ->  2.734
```

**El defecto real es uno solo: nomenclatura.** El instrumento divide por `2**30`,
así que son unidades **binarias** — **GiB**, no GB; **MiB**, no MB. Nada más.

### Qué salió mal en mi diagnóstico, que es lo que hay que registrar

Leí `1.925` como un decimal inglés —1,925 MB— y de ahí saqué que el valor era
mil veces menor que la medición, que por lo tanto no coincidían, y que el origen
era irrecuperable. **Una sola cifra mal leída produjo tres conclusiones falsas
encadenadas**, y ninguna de las tres era verificable sin releer el número.

Es exactamente el modo de falla que esta sesión persigue —**dos notaciones que
se leen igual**— cometido por mí, sobre mi propia convención, dentro de la
auditoría que lo persigue.

### Qué se corrige, entonces

| | |
|---|---|
| veredicto de equivalencia | **intacto** — re-verificado, 12 campos × 6 unidades |
| valores de RSS | **intactos** — 1925 MiB y 2734 MiB, la misma medición |
| nomenclatura | **corregida** — MiB/GiB, y se publican **las dos** representaciones |
| hipótesis de las 12 sesiones | **retirada** |

En la fuente, el campo `rss_pico` publica `1925 MiB = 1,88 GiB` y
`2734 MiB = 2,67 GiB`, y dice por qué existen las dos: para que nadie tenga que
convertir ni adivinar qué separador es el punto.

### Y una limitación del medidor, que sí hay que declarar

`medir_rss_y_equivalencia.py` suma el `WorkingSet64` de **todos** los procesos
`python` de la máquina y le resta una línea de base. **No es el árbol del PID.**
Si durante la medición arranca o termina cualquier otro Python, contamina el
pico. La corrida preservada se hizo sin nada más corriendo, pero eso fue una
**condición del entorno, no una garantía del instrumento** — y ahora está
escrito al lado del código, con la función renombrada a
`rss_de_todos_los_python()` para que el nombre no prometa lo que no hace.

> El artefacto ya emitido (`76e1c876…`) conserva el texto viejo. **No se
> reescribe**: es el registro de lo medido, y tocarlo invalidaría su
> `output_sha256`. Mismo tratamiento que `autoritativo`.

## 4. El 99 % / 97 % — definición reproducible, resultado replicado

> **SEGUNDA RECTIFICACIÓN, del mismo tipo que la §3.** Yo afirmé que la medición
> original «no registró muestra ni definición operacional». **Sí las registró**,
> en la tabla del docstring de `curva_excursion_ticks.py`: *«Medido sobre 6E
> 03-26 (10 días), fracción de zonas con `created_ms > bar_end[created_bar]`»*.
> Miré sólo el comentario suelto de la línea 411 y no la tabla que lo documenta.

Con la muestra y la definición a la vista, la comparación se puede hacer bien — y
el resultado **replica en otra muestra**. Que no es lo mismo que «reproduce»:
**la muestra original no se volvió a correr**, y para decir «reproducida
exactamente» habría que rerunear 6E 03-26, 10 días, con la definición original.

| | muestra | definición | `Gaps2` | `HFTZones2` |
|---|---|---|---:|---:|
| **original** | 6E 03-26, 10 días | cualquier adelanto | **99 %** (21,5 s) | **97 %** (27,5 s) |
| **réplica** | 6E 09-26, 8 sesiones | **la misma** | **100 %** (27,7 s) | **96,4 %** (28,2 s) |
| réplica | 6E 09-26, 8 sesiones | umbral > 1 s | 96,7 % | 92,9 % |

Las fracciones replican sobre **otro contrato y otro trimestre**. Lo que yo
había leído como «no reproduce» era el renglón de abajo comparado contra el de
arriba: **una métrica con umbral material contra una sin umbral**. Dos
definiciones distintas dando números distintos no es una falla de reproducción.

Lo único que difiere de verdad es el **p50 de `Gaps2`**: 21,5 s contra 27,7 s,
~6 s entre contratos. El de `HFTZones2` no se mueve (27,5 → 28,2). No lo
explico; es una diferencia entre períodos, y queda registrada como tal.

### Por qué NO se marcó la tabla como «histórica no reproducible»

El punto 6 del auditor pedía anotarla así. **No se hizo, porque la premisa era
mía y era falsa.** Se anotó lo que la evidencia dice: **`DEFINICIÓN REPRODUCIBLE Y RESULTADO
REPLICADO EN OTRA MUESTRA`**, con la muestra, la definición y las dos réplicas.

Y se agregó el matiz que sí importa: el `0 %` de los tres `bar_close` **sólo vale
con umbral material**. Sin umbral dan 100 %, porque para un kernel que crea al
cierre el `created_ms + 1` deja 1 ms de diferencia **por la propia convención**.
Ese control cayendo a 0,0 % con umbral es lo que confirma que el efecto es **de
clase**, no de medición.

El registro histórico **no se borra**: la tabla original queda con sus cifras, y
el estatus se marca al lado.

## 5. Puerta permanente de citas

`tools/verificar_citas_entrega.py`, fail-closed. Exige de cada ruta citada por
un documento de entrega: **existe**, **está trackeada por git**, y **no está
abreviada**. La segunda regla es la que detecta evidencia que vive sólo en una
máquina; la tercera es la que atrapó una abreviatura de la forma `«__w2_70s.json»`,
que *parecía* bien.

No valida que el archivo citado **diga** lo que el documento afirma. Eso es
lectura, y no lo hace un script.

## 6. Inventario completo — los 92

`sha256` truncado a 12; el completo está en la salida de
`tools/auditar_procedencia.py`.

> **Notación:** el prefijo `tmp:` marca un archivo del **directorio temporal**,
> no una ruta del repo. La distinción no es cosmética — sin ella, el log del
> temporal (que ya no existe) y el log versionado que lo reemplaza (§1.2) se
> leen igual.
>
> Lo hizo evidente la puerta de citas: reportó **92 rutas rotas** que eran, en
> realidad, el objeto de estudio mal tipografiado. Y en el mismo pasaje encontró
> **cuatro reales**, entre ellas que el log rescatado **no se había versionado**
> — lo bloqueaba un `*.log` del `.gitignore`, en silencio.

| clase | archivo | bytes | sha256 | referente / motivo | destino |
|---|---|---:|---|---|---|
| **A** | `tmp:e1.json` | 686791 | `014f0c412d95` | los dos artefactos de la equivalencia 1-vs-2 que publica el manifiesto | YA versionado, ver §1.1 |
| **A** | `tmp:e2.json` | 686791 | `08ac319146d8` | los dos artefactos de la equivalencia 1-vs-2 que publica el manifiesto | YA versionado, ver §1.1 |
| **A** | `tmp:rss.log` | 405 | `da9cd2c678de` | unica evidencia de `RSS pico` y del veredicto EXACTA que publica curva_excursion_ticks.json | versionado en diag/tasa_senales/ |
| **A** | `tmp:rss2.py` | 3964 | `080a273e58ad` | unica evidencia de `RSS pico` y del veredicto EXACTA que publica curva_excursion_ticks.json | versionado en diag/tasa_senales/ |
| **B** | `tmp:compila.json` | 2578 | `cd9f90dad75d` | salida de tools/compilar_nt8_cs.py, regenerable | comando registrado |
| **B** | `tmp:curva.log` | 68 | `9ba9bf29b40d` | logs de corridas cuyas conclusiones ya estan en docs/ o en un artefacto | comando registrado |
| **B** | `tmp:curva_full.log` | 3100 | `2b83569f43dd` | salida de consola de la curva; sus cifras estan en curva_excursion_ticks.json | comando registrado |
| **B** | `tmp:donde.log` | 141 | `4c691bfbaad0` | logs de corridas cuyas conclusiones ya estan en docs/ o en un artefacto | comando registrado |
| **B** | `tmp:lentos.log` | 47 | `358d8e189868` | logs de corridas cuyas conclusiones ya estan en docs/ o en un artefacto | comando registrado |
| **B** | `tmp:p20c.log` | 3325 | `61ff8b820c50` | logs de corridas cuyas conclusiones ya estan en docs/ o en un artefacto | comando registrado |
| **B** | `tmp:s08b.log` | 1657 | `2ffed2860264` | salida de la sonda; sus cifras estan en los dos sonda_alejamiento_cero__*.json | comando registrado |
| **B** | `tmp:s40b.log` | 1658 | `4a0da9cd11b1` | salida de la sonda; sus cifras estan en los dos sonda_alejamiento_cero__*.json | comando registrado |
| **B** | `tmp:sonda40.log` | 1368 | `3234c9d8797b` | salida de la sonda; sus cifras estan en los dos sonda_alejamiento_cero__*.json | comando registrado |
| **B** | `tmp:verif.log` | 1791 | `c226b4b03519` | logs de corridas cuyas conclusiones ya estan en docs/ o en un artefacto | comando registrado |
| **C** | `tmp:antes.py` | 29616 | `1c2419a7b449` | optimizacion de eventos_de_zona que se REVIRTIO: 1,1x medido contra 20-50x predicho, y ademas introducia un bug en el maximo | no versionar |
| **C** | `tmp:c1.json` | 51555 | `8b7d1bd0acf5` | checkpoints de reanudacion, no resultados | no versionar |
| **C** | `tmp:c2.json` | 51555 | `8b7d1bd0acf5` | checkpoints de reanudacion, no resultados | no versionar |
| **C** | `tmp:cb.py` | 7069 | `4b15bfa55aaa` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:ck.json` | 25193 | `3833d7077d63` | checkpoints de reanudacion, no resultados | no versionar |
| **C** | `tmp:ck_viejo.json` | 130595 | `dcb817e3a4e3` | checkpoints de reanudacion, no resultados | no versionar |
| **C** | `tmp:ckpt.py` | 7868 | `e2004b0a7ff6` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:clases.py` | 7606 | `c1f27958cbb4` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:curva.json` | 5957 | `029a28f757ea` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:curva2.json` | 30426 | `7cc57fa84b7c` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:d1_d6.py` | 6190 | `72444a789fbb` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:donde.py` | 2014 | `794cc56ef405` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:extractor_v3.py` | 6855 | `761dd6d645f1` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:fix_1360.py` | 6056 | `847976f7335b` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:fix_refasm.py` | 1761 | `a537dd235e25` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:fix_regresiones.py` | 4133 | `eac7782a20a5` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:fix_tests.py` | 8182 | `5dfd905f7018` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:hp.py` | 8588 | `4f35c13234a8` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:hp004.py` | 5603 | `13503d395902` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:lentos.py` | 2871 | `d5462268e67d` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:opt.py` | 5469 | `5b60b9799d47` | optimizacion de eventos_de_zona que se REVIRTIO: 1,1x medido contra 20-50x predicho, y ademas introducia un bug en el maximo | no versionar |
| **C** | `tmp:p20c.json` | 381610 | `5bb628c6c6f9` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:par_ckpt.py` | 2372 | `0c187f1eeabf` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:patch_curva.py` | 8692 | `8dd77f11be5b` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:piloto20.json` | 394645 | `315b8d4c3872` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:piloto30.json` | 6892 | `33d13e5dca4b` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:piloto_ft.json` | 2491 | `5635bd5dbce5` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:rojos.py` | 4640 | `049e42c89d29` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:rss.py` | 3061 | `96dbfb0ec63b` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:rss2_ck_1.json` | 350186 | `fb83625e5d11` | checkpoints de reanudacion, no resultados | no versionar |
| **C** | `tmp:rss2_ck_2.json` | 350186 | `a6832efa27fd` | checkpoints de reanudacion, no resultados | no versionar |
| **C** | `tmp:rss_ck_1.json` | 114047 | `ee37345d9e1b` | PRIMERA equivalencia, 12 sesiones = UN SOLO contrato: el segundo worker no tenia trabajo. La declaro invalida rss2.py y la reemplaza la de 70 sesiones | no versionar |
| **C** | `tmp:sistema.py` | 8118 | `5cb132e12652` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:t.json` | 11736 | `fe4a4c4529c1` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:t2.json` | 43788 | `bef9ac39b584` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:ticks_piloto.json` | 78767 | `e4dc064e60d4` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:v2.json` | 2833 | `9c8cfdba325a` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:v3.json` | 31919 | `280846a5d9f2` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:v4.json` | 1517 | `c965ecbf63ad` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:v5.json` | 1519 | `fa1100a14afd` | pilotos de la curva, supersedidos por la corrida de 201 sesiones | no versionar |
| **C** | `tmp:verif.py` | 1845 | `bb74cd5859a6` | scripts de parche: su efecto esta commiteado, el script es un medio | no versionar |
| **C** | `tmp:w1.json` | 226926 | `ee22b2072af9` | PRIMERA equivalencia, 12 sesiones = UN SOLO contrato: el segundo worker no tenia trabajo. La declaro invalida rss2.py y la reemplaza la de 70 sesiones | no versionar |
| **C** | `tmp:w2.json` | 226924 | `79ff375ae8a1` | PRIMERA equivalencia, 12 sesiones = UN SOLO contrato: el segundo worker no tenia trabajo. La declaro invalida rss2.py y la reemplaza la de 70 sesiones | no versionar |
| **D** | `tmp:ADDENDUM_GROK.md` | 5021 | `6a41d9e02560` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:GROK_CORTO.md` | 4032 | `12f899f71f70` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:HANDOFF_GROK.md` | 34984 | `76a0f11f54d9` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:build_grok.py` | 4047 | `91ceb4fbad16` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:censo.md` | 4956 | `c88f378e7235` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:cierre_mde.py` | 5216 | `73d166a8e290` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:contrato_v4.md` | 5593 | `40d1fbcc3c71` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:eje34_ancla_vs_clave.py` | 6588 | `2056296abb08` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:eje34_v2.py` | 6008 | `d3c4d9709eb9` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:freeze_actual.txt` | 568 | `93fac0d6a761` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:g0_repro.py` | 7648 | `7ad83dfda002` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:grok.md` | 6856 | `c80da88a5122` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:iter1.md` | 14375 | `fcddd0edffc4` | borradores con GEMELO EXACTO ya versionado (mismo sha256) | descartable |
| **D** | `tmp:iter2.md` | 19291 | `64f7e7f03d79` | borradores con GEMELO EXACTO ya versionado (mismo sha256) | descartable |
| **D** | `tmp:iter3.md` | 24658 | `a48f494c3d41` | borradores con GEMELO EXACTO ya versionado (mismo sha256) | descartable |
| **D** | `tmp:m1_m2_m3.py` | 8158 | `b5336d1ad1fd` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:msg.txt` | 2583 | `730706569a57` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:msg4.txt` | 2028 | `1a41b99ad807` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:msg_rojos.txt` | 1826 | `3754b60eff88` | material de la delegacion a Grok, CANCELADA por falta de creditos; y mensajes de commit ya aplicados | descartable |
| **D** | `tmp:n1.md` | 6793 | `2e11314d6cf3` | borradores con GEMELO EXACTO ya versionado (mismo sha256) | descartable |
| **D** | `tmp:pb_particion.py` | 5612 | `83c3dab5442f` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:r3_r4_r5.py` | 5492 | `01fded2b464f` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:refina_mde.py` | 1345 | `8a5d9d0ea4ac` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:run_paridad_unidad2.py` | 4929 | `fefd718e98f6` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:t4_residuo.py` | 4539 | `82aa39948b99` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:tick25_julio.csv` | 824930 | `2e1d3ee25be8` | REBANADAS de oraculos que ya estan en oracles/ y declarados en el manifiesto; el acceso a la ventana de julio esta registrado (nota 3) | BORRAR del temporal: son datos de ventana sellada fuera del store |
| **D** | `tmp:tick25_junio.csv` | 217211 | `1c19ebc99b1d` | REBANADAS de oraculos que ya estan en oracles/ y declarados en el manifiesto; el acceso a la ventana de julio esta registrado (nota 3) | BORRAR del temporal: son datos de ventana sellada fuera del store |
| **D** | `tmp:u1_rematch.py` | 7467 | `9b7cd5f34709` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:u2_spike.py` | 2724 | `29ae00a8fc2d` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:unidad1_identidad.py` | 7344 | `579dfb29ef16` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:unidad2_duracion.py` | 5642 | `7c7b9aa2ac09` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:unidad2_reemparejar.py` | 6479 | `69f8343be302` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:x3_memoria_larga.py` | 7318 | `b9d56ec1c937` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:x4_control_generador.py` | 2429 | `75ca114af471` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |
| **D** | `tmp:x4_sensibilidad.py` | 4865 | `7df02c5a7f72` | diagnosticos de julio ya cerrados en su acta o expediente correspondiente | descartable |

## 7. Lo que el barrido encontró, ya rectificado

| hallazgo | veredicto final |
|---|---|
| `tmp:rss.log` / `tmp:rss2.py` sin versionar | **real** — clase A, rescatados |
| el log rescatado **no se versionó**: lo bloqueaba `*.log` del `.gitignore` | **real** — lo detectó la puerta de citas, no una lectura |
| dos citas abreviadas en los documentos de entrega | **real** — corregidas |
| notación MB/GB donde el instrumento produce MiB/GiB | **real** — corregida |
| «RSS sin origen recuperable, quizá de la corrida de 12 sesiones» | **RETIRADO** (§3) |
| «99 %/97 % no reproducible» | **RETIRADO** (§4) — está especificada y replicada |
| rebanadas de ventana sellada fuera del store | **higiene** — borradas; no era brecha |

Cuatro reales, **dos retirados**. Los dos retirados eran del mismo tipo: yo leí
mal un registro que estaba completo, y publiqué la mala lectura como defecto
ajeno.

## Aporte al referente

Cierra la última reserva de traspaso: ninguna afirmación viva del expediente
depende de un archivo que se borra solo. Pero el resultado más útil no es ese —
es que **un barrido de procedencia también necesita ser auditado**. Este produjo
dos falsos positivos y los dos apuntaban a que alguien más había sido descuidado.
Un edge que no se puede verificar de forma independiente no es un edge; una
auditoría que no se puede refutar tampoco es una auditoría.
