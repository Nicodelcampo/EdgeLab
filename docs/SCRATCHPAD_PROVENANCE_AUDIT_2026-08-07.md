# Acta de procedencia — barrido del directorio temporal

**Fecha:** 2026-08-07 · **Alcance:** los 92 archivos del scratchpad de la sesión
**Pedido por:** el auditor, tras aceptar `bc56d1b` + `5b4d9ac`
**Reproducible:** `python tools/auditar_procedencia.py <dir_temporal>`

> **Por qué se hizo.** Un barrido parcial —el de los dos documentos de entrega—
> ya había encontrado **dos afirmaciones publicadas cuya evidencia vivía sólo en
> un directorio temporal**. Encontrar dos eleva la probabilidad de que haya más,
> no la baja. Este es el barrido completo.

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

**No apareció ninguna otra afirmación viva sin respaldo.** Los 43 de clase C son
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

## 3. El defecto que encontró el barrido — el RSS publicado

`curva_excursion_ticks.json` publica, dentro de `equivalencia_workers`:

> `"… RSS pico 1.925 vs 2.734 MB."`

La única medición preservada dice otra cosa:

```
workers=1: rss_pico_gb 1.88     workers=2: rss_pico_gb 2.67
```

**Dos defectos, y el primero es seguro:**

1. **La unidad está mal.** El instrumento calcula `round(pico / 2**30, 2)`: son
   **gigabytes**. «1.925 MB» sería un consumo trivial; 1,88 GB no lo es. Esto no
   es interpretable — está en el código.
2. **Los valores no coinciden** con la única medición preservada, y **el origen
   de `1.925` / `2.734` no es recuperable.** La hipótesis más probable es que
   vengan de la primera corrida —12 sesiones, que caen enteras dentro de
   `6E_03-26`, o sea **un solo contrato**— que el propio `tmp:rss2.py` declara
   inválida porque el segundo worker no tenía trabajo. Si es así, la frase
   describía la corrida de 70 sesiones mientras los números venían de la de 12.
   **No lo puedo confirmar: esa corrida no dejó log.**

**Qué cambia y qué no.** El **veredicto de equivalencia no se toca**: está
re-verificado desde artefactos versionados, 12 campos × 6 unidades. Lo que se
corrige es la cifra de memoria, que es un dato de operación, no de validez.

Corregido en la fuente (`curva_excursion_ticks.py`): `equivalencia_workers`
conserva el veredicto y remite al verificador, y un campo nuevo `rss_pico`
publica **1,88 / 2,67 GB** declarando explícitamente que corrige la cifra
anterior y que el origen de la vieja no es recuperable.

> El artefacto ya emitido (`76e1c876…`) conserva el texto viejo. **No se
> reescribe**: es el registro de lo medido, y tocarlo invalidaría su
> `output_sha256`. Mismo tratamiento que `autoritativo`.

## 4. El 99 % / 97 % — anotado donde nace

Punto 6 del auditor. `curva_excursion_ticks.py` ya no cita esas cifras sin
estatus. Ahora dice, en el mismo lugar:

- **medición original (histórica):** ~21-27 s, 99 % `Gaps2` / 97 % `HFTZones2`;
  **no reproducible exactamente**, porque no registró muestra ni definición
  operacional;
- **corroboración versionada (2026-08-07):** `Gaps2` 96,7 %, `HFTZones2` 92,9 %,
  controles `bar_close` 0,0 %, sobre 8 sesiones de `6E_09-26`, umbral material
  > 1 s;
- **la conclusión se sostiene**, el split por clase está justificado, y las
  cifras 99/97 **no deben volver a citarse como medición reproducible**.

El registro histórico **no se borra**. Se le marca el estatus en el mismo lugar
para que nadie lo vuelva a citar como si fuera reproducible.

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

## Aporte al referente

Cierra la última reserva de traspaso: ninguna afirmación viva del expediente
depende de un archivo que se borra solo. Un edge que no se puede verificar de
forma independiente no es un edge — y el barrido encontró, además de las dos ya
conocidas, **una cifra publicada en la unidad equivocada** que ninguna lectura
del documento habría detectado, porque sólo el instrumento sabía que dividía por
2³⁰.
