# Paridad forense BigTrap2Absorption — GC 02-26, calendario irregular

```
PARITY_GC0226_FAIL
```

- **Fecha:** 2026-08-24 · **Rol:** auditor forense adversarial
- **Rama:** `foundation/f0b-compatibility-probe` · **tip:** `96416062c25ff39a4d0fe08c96358660d571d06c`
- **Harness:** `tools/verify_parity_gc0226.py`
- **Artefacto:** `docs/research/PARIDAD_BT2_ABSORPTION_GC0226_2026-08-24.json`
- **`OUTCOMES_NOT_OPENED`** — no se calculó MFE, MAE, `d_hat` ni resultado económico alguno.

> El FAIL es **de cobertura**, no de aritmética. La aritmética **no llegó a ser
> comparable**: a partir de la cubeta 1.428 las cubetas de un lado y del otro no
> contienen los mismos ticks. No se parcheó nada en esta corrida.

---

## 1. Veredicto y numeradores

| capa | numerador / denominador | estado |
|---|---:|---|
| cobertura post-ancla | **1.427 / 185.697 = 0,768456 %** | **FAIL** |
| aritmética (`signed_flow`, `d_ticks`, `a_score`, `n_ticks`) | 0 / 0 | **NO EVALUADO** |
| anillo causal (`a_thr`, `a_pass`, `n_hist`) | 0 / 0 | **NO EVALUADO** |
| política de residuales | 0 / 0 | **NO EVALUADO** |
| zonas | 0 / 0 | **NO EVALUADO** |
| fills / pairing | 0 / 0 | **NO EVALUADO** |
| sesión / calendario | 0 / 0 | **NO EVALUADO** |

Las seis capas marcadas `NO EVALUADO` están **bloqueadas por la primera**. Declararlas
`EXACT` sobre el 0,77 % de cobertura sería exactamente lo que el protocolo prohíbe.

---

## 2. Fase 1 — higiene y reproducibilidad

| ítem | valor | verificación |
|---|---|---|
| tip local = remoto = esperado | `96416062c25ff39a4d0fe08c96358660d571d06c` | ✅ |
| `9641606` es ancestro | sí | ✅ |
| árbol | 0 archivos modificados | ✅ limpio |
| research GATE `9ad3db7` | existe | ✅ |

### Inputs congelados

| artefacto | bytes | sha256 |
|---|---:|---|
| oráculo | **128.331.787** ✅ esperado | `7c14ebd1463f4d17d4db7957e4fe729a6d1d48b46b3395bc7334a505cf9fce4d` ✅ **coincide** |
| cinta `GC 02-26.Last.txt` | 366.776.487 | `6206881c59c6a31265379be8e7241e6e0d15d339e70491714cd439137e598013` |

### Hashes históricos — **ambos vigentes, sin diff**

```
kernel Python  0d162a6092c31228ec0f4f9539b4afc0cb5031737263db4369dea2ad03697ab2   VIGENTE
.cs            18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641   VIGENTE
```

### Entorno y comando

```
Python 3.12.10 | numpy 2.4.6 | pandas 3.0.3 | Windows

python tools/verify_parity_gc0226.py \
  --csv  "C:\Users\nicoc\Documents\NinjaTrader 8\exports\bt2_absorption__AbsMagnitude__GC0226dic__TW25.csv" \
  --tape "C:\Users\nicoc\OneDrive\Documentos\DataNT8\GC 02-26.Last.txt" \
  --out-json docs/research/PARIDAD_BT2_ABSORPTION_GC0226_2026-08-24.json
```

**Zona horaria:** el oráculo se emite en la hora del chart de NT8 —Argentina, UTC−3, sin
DST— y la cinta está en UTC. La conversión es un desplazamiento fijo **derivado de la zona
declarada**, no un offset elegido para alinear. Es la única transformación temporal del
harness; no hay offsets de número de barra ni de índice de cinta.

---

## 3. Auto-chequeo del oráculo — **100 % reproducido**

Se reproduce **todo** lo declarado, sin excepción:

| magnitud | medido | esperado |
|---|---:|---:|
| `BARRA_PROCESADA` | 185.697 | 185.697 ✅ |
| `ABS_SCORE` | 185.697 | 185.697 ✅ |
| `TRAP` | 97.391 | 97.391 ✅ |
| `ZONE_CREATED` | 2.702 | 2.702 ✅ |
| `FILL` | 2.702 | 2.702 ✅ |
| `ZONE_INVALIDATED` | 2.639 | 2.639 ✅ |
| `ZONE_EXPIRED` | 62 | 62 ✅ |
| sesiones CME | 30 | 30 ✅ |
| cubetas residuales | 28 | 28 ✅ |
| ticks en residuales | 328 | 328 ✅ |
| **identidad** | **185.669 × 25 + 328 = 4.642.053** | 4.642.053 ✅ |
| metas / malformadas | 1 / 0 | 1 / 0 ✅ |
| `seq` monótona, sin huecos | sí, 0 huecos en 476.890 | ✅ |
| `zone_id` únicos | 2.702 / 2.702 | ✅ |

**El oráculo es internamente perfecto.** Todo lo que sigue es sobre la relación entre el
oráculo y la cinta, no sobre el oráculo.

### Auditoría del parser de la cinta

```
lineas validas            7.755.426
malformadas                       0
timestamps hacia atras            0
ts repetido consecutivo   3.833.051   <-- 49,4 % de los ticks comparten instante
primera                   2025-11-05 03:01:31.632 UTC
ultima                    2026-02-25 11:41:04.200 UTC
```

El 49,4 % de colisión de timestamps es la razón por la que **el ancla no puede elegirse
por coincidencia de timestamp sola** — y es lo que hace indispensable la corrida de
validación.

---

## 4. Fase 2 — el ancla

`t_start` de la primera cubeta: `2025-11-23 23:00:30.148000 UTC`.

**5 candidatos** con ese timestamp exacto. Corrida consecutiva de validación:

| índice de cinta | cubetas consecutivas con `t_start` exacto |
|---:|---:|
| 92.271 | 1 |
| 92.272 | 1 |
| 92.273 | 1 |
| 92.274 | 1 |
| **92.275** | **1.427** |

La elección es **algorítmica y no ambigua**: 1.427 contra 1. No se usó offset fijo, no se
buscó el que maximiza paridad de campos — el criterio es identidad de la partición, medido
antes de mirar un solo campo aritmético.

```
primera barra del oraculo : 1
barra elegida como ancla  : 1
indice exacto de tape     : 92.275
filas pre-ancla           : 92.275
razon de exclusion        : ticks de la cinta anteriores al inicio de carga del chart
cobertura post-ancla      : 1.427 / 185.697 = 0,768456 %
```

---

## 5. El primer contraejemplo reproducible

```
cubeta ordinal   1.428
bar              1428
td               20251124
largo            8
residual         True        <-- es la cubeta residual de la primera sesion
t_start oraculo  2025-11-24 21:59:55.016000 UTC
indice esperado  127.950
ts de la cinta   2025-11-24 23:00:02.612000 UTC
delta            +3.607,596 s  (1 h 0 min 7,6 s)
```

### Qué muestra la cinta en ese punto

```
linea 127.933   20251124 215955 0160000;4170.2;4169.6;4170.2;1
linea 127.934   20251124 215955 0160000;4170.2;4168.5;4172.5;1   <-- ultimo tick de la sesion
linea 127.935   20251124 230000 1640000;4170.3;4170.3;4171.3;1   <-- reapertura, 1 h despues
```

La cinta **cierra la sesión en la línea 127.934** y no vuelve hasta las 23:00 UTC. No hay
un solo tick entre 22:00 y 23:00.

### La cuenta

```
ancla (0-based)                                   92.275
ultimo tick de la sesion en la cinta (0-based)   127.933
ticks de la cinta en la sesion                    35.659

NT8 declara para td=20251124:  1.427 x 25 + 8  =  35.683
                                                  ------
                              FALTAN EN LA CINTA      24
```

**La cinta tiene 24 ticks menos que los que el chart cargó en esa sesión.** Las cubetas
1 a 1.427 sobreviven porque la partición todavía coincide; la residual de 8 ticks, que
NT8 ubica en `21:59:55.016`, no tiene contrapartida en la cinta, y de ahí en adelante el
índice acumulado queda corrido para siempre.

---

## 6. Corrección de un diagnóstico previo mío

En la pasada anterior de esta misma sesión afirmé:

> *«la cinta tiene +431 ticks en Thanksgiving y +25 en la apertura del domingo que NT8 no
> cargó»*

**Es falso, y el error fue mío.** Esa medición asignaba sesiones CME con una heurística
propia de `±7 h` sobre UTC — exactamente el offset manual que este protocolo prohíbe. La
prueba de que estaba mal estaba a la vista y no la leí: aquella tabla reportaba ticks en
**20251206 y 20251221, que son sábado y domingo**, y 5 ticks en **20260104, domingo**. Un
calendario que produce sesiones en fin de semana está roto.

Medido correctamente, con el `td` que el propio oráculo declara y sin heurística:

| afirmación anterior | medición correcta |
|---|---|
| cinta con **+431** en Thanksgiving | no verificable: la cobertura se corta el 24-nov, antes de llegar |
| cinta con **+25** en la primera sesión | **la cinta tiene −24**, en dirección contraria |
| «28 de 33 sesiones coinciden tick por tick» | artefacto de la heurística; la cobertura real es de 1 sesión parcial |

---

## 7. Fases 3 a 6 — no ejecutadas, y por qué

Las fases de aritmética, residuales/calendario, zonas/fills y tests adversariales
**requieren cobertura**. Con 0,77 % no hay sobre qué medirlas: cualquier número que
publicara sería sobre 1.427 cubetas de una sola sesión parcial, y presentarlo al lado de
un denominador de 185.697 sería engañoso.

La única de esas fases parcialmente ejecutable es la de residuales, y sólo **del lado del
oráculo**: las 28 residuales se reproducen exactamente, incluidas las cuatro que el
protocolo nombra.

| fecha | residual esperada | medida en el oráculo |
|---|---:|---:|
| 2025-11-27 Thanksgiving | 3 | **3** ✅ |
| 2025-11-28 post-Thanksgiving | 16 | **16** ✅ |
| 2025-12-24 Nochebuena | 17 | **17** ✅ |
| 2025-12-25 Navidad | sesión ausente | **ausente** ✅ |
| 2025-12-31 fin de año | 22 | **22** ✅ |
| 2026-01-01 Año Nuevo | sesión ausente | **ausente** ✅ |

Eso dice que **el `.cs` maneja el calendario irregular como se esperaba**. No dice que el
kernel Python lo reproduzca: eso es justo lo que quedó sin medir.

---

## 8. Limitaciones reales de esta auditoría

1. **No sé por qué faltan los 24 ticks.** Tengo la medición, no la causa. Las dos
   hipótesis vivas —que el export de la base de ticks y el chart usen plantillas de
   sesión distintas, o que el export haya recortado el borde de sesión— **no las
   distinguí**, y no voy a elegir una sin evidencia.
2. **La cobertura se corta en la primera sesión**, así que esta corrida no dice nada
   sobre Thanksgiving, Navidad ni Año Nuevo del lado de la cinta. El objetivo declarado
   del export —estresar el calendario irregular— **no se alcanzó**.
3. **No se probó ningún campo aritmético.** El kernel Python no queda ni validado ni
   invalidado sobre este par.
4. `calendar_hash` queda `null`: el harness no llegó a instanciar un calendario efectivo
   porque no llegó a la fase que lo usa.

---

## 9. Lo que esto NO invalida

`FINAL_PUERTA0_SIGNED` sigue en pie **con su alcance original**: GC 12-26 en agosto y
GC 08-26 en junio, semanas de calendario regular, donde la cinta y el chart sí contenían
el mismo flujo. Este FAIL **no las contradice** — agrega que la paridad tiene una
precondición que hasta hoy no estaba escrita:

> **La cinta y el chart tienen que contener el mismo flujo de ticks.** Cuando difieren, el
> harness no puede medir el kernel: mide la diferencia de los insumos.

Y esa precondición **falla** en el primer borde de sesión de este par.

---

## Aporte al referente

Queda un harness que **falla ruidosamente en la capa correcta** en vez de reportar
porcentajes altos sobre un conjunto común pequeño. La corrida anterior de este mismo par
informó «97,89 % en `signed_flow`» sobre 14.480 claves comunes de 185.697 — un número
tranquilizador construido sobre una comparación que ya estaba rota. Este harness dice
0,768456 % de cobertura y se detiene, que es lo que había que decir.

## Nota de método

El defecto que encontré hoy en mi propio trabajo es el mismo que vengo marcando en el
ajeno: **una etiqueta que no verifica su contenido.** Escribí una función llamada `cme()`
que no calculaba sesiones CME, la usé para medir, y publiqué la conclusión. La señal de
que estaba rota —sesiones en sábado y domingo— estaba impresa en mi propia tabla. La
diferencia entre esto y los cuatro rechazos de Puerta 0 no es la clase de error: es que
esta vez el que lo encontró primero fue el protocolo, al prohibir los offsets manuales.
