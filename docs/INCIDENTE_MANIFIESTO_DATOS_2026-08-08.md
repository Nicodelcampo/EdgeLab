# Incidente — el manifiesto de datos declaraba un estado anterior al arreglo

**Fecha:** 2026-08-08 · **Detectado por:** Nico, al preguntar por qué los 6E
figuraban como discrepantes si ya se habían reexportado.
**Severidad:** baja — **no dejó secuelas en ningún resultado publicado.**

---

## 1. Qué pasó

`docs/datos_manifiesto.json` se creó el 2026-08-07 (commit `cdfa212`, identidad
`EdgeLab Baseline`) desde **la otra máquina**, declarando 31 parquets.

Al verificarlo en esta máquina, `tools/manifiesto_datos.py` salió con **exit 1**:
20 archivos ausentes y **los 5 de 6E marcados como `DIFIERE`**.

La lectura inicial —mía— fue que los datos de esta máquina eran sospechosos. **Era
al revés.**

## 2. La evidencia

### 2.1 Los datos de esta máquina son los limpios, medido hoy

```
tools/censo_integridad.py
6E_03-26   87 dias  APTO=66  dup_bloque=0
6E_06-26   86 dias  APTO=77  dup_bloque=0
6E_09-25   47 dias  APTO=0   dup_bloque=0
6E_09-26   51 dias  APTO=45  dup_bloque=0
6E_12-25   89 dias  APTO=68  dup_bloque=0
universo: 256 dias aptos
```

`dup_bloque=0` en los cinco, y **256 días aptos** — el número del universo
limpio. La corrida sobre datos sucios daba **236** y `dup_bloque` de 36 y 40.

### 2.2 Prueba directa: el manifiesto declara un archivo pre-fix

`6E_all_contracts.parquet` declarado en el manifiesto:

```
declarado en manifiesto : 8b144a54a85b1fb75b2a068bc5ae0171f846aa5c084070685770770687780f46
sucio archivado (21-jul): 8b144a54a85b1fb75b2a068bc5ae0171f846aa5c084070685770770687780f46
```

**Byte por byte el mismo archivo.** No es una aproximación: el manifiesto
declara como canónico un artefacto anterior a la reexportación.

### 2.3 Los cinco individuales, en tres estados (MB)

| archivo | sucio (21-jul) | declarado (manifiesto) | limpio (en disco) |
|---|---:|---:|---:|
| 6E_03-26 | 43,7 | 85,7 | **85,7** |
| 6E_06-26 | 47,3 | 92,5 | **93,0** |
| 6E_09-25 | 23,7 | 33,7 | **44,4** |
| 6E_09-26 | 16,8 | 37,6 | **45,4** |
| 6E_12-25 | 38,5 | 76,8 | **77,0** |

Los declarados son ~2× los sucios y coinciden con los limpios dentro de 0,6 % en
tres de cinco. O sea: **los individuales de la otra máquina NO son los sucios**;
son post-fix con otra ventana de descarga. Sólo `all_contracts` quedó sin
regenerar.

Las dos diferencias grandes tienen lectura distinta:

- **`6E_09-26`** es el **front month activo**. Su rango medido acá llega hasta
  `2026-08-04 05:05:58 UTC`, el día mismo de la reexportación. Crece cada día:
  la diferencia es cola nueva, no defecto.
- **`6E_09-25`** es un contrato **cerrado desde septiembre de 2025** y no debería
  crecer. La diferencia es de ventana de descarga —acá se purgó y bajó de nuevo,
  trayendo más historia—. **No se pudo verificar la causa desde esta máquina**;
  queda declarado como no explicado.

## 3. Por qué NO dejó secuelas

### 3.1 En esta máquina — ninguna

Todo lo calculado acá (censo de 201 sesiones, TICKBAR-001, PRED-004, la
comparación de ambigüedad de stop) usó los parquets con `dup_bloque=0`
verificado. El manifiesto viejo nunca fue una entrada de cómputo: es un
verificador, y fallar abierto no era posible porque sale con exit 1.

### 3.2 `all_contracts` no lo consume nadie

Única referencia en todo el código:

```
tools/censo_integridad.py:252  ap.add_argument("--skip", default="6E_all_contracts.parquet", ...)
```

Aparece **para excluirlo por default**. Ningún kernel, censo ni sonda lo lee.
Que la otra máquina tenga la versión sucia de ese archivo es inerte.

### 3.3 `6E_09-25` no entra al universo

```
6E_09-25_ticks.parquet   47 dias   APTO=0   DEF=47
```

**Cero días de ese contrato entran alguna vez al universo de investigación.** Es
rechazado entero por los gates, sea cual sea su tamaño. La diferencia no
explicada del §2.3 es real pero no puede haber afectado ningún resultado.

### 3.4 Las sondas de la otra máquina — consistentes, y a regenerar de todos modos

`sonda_alejamiento_cero__6E_09-26_08s.json` y `..._12-25_40s.json` declaran:

```
input_parquet_sha256 (09-26) = 654e006e483f6272...   == el declarado en el manifiesto
input_parquet_sha256 (12-25) = fa0ee010af08edc6...   == el declarado en el manifiesto
```

Manifiesto y sondas son **mutuamente consistentes**: misma máquina, mismos
datos, sin mezcla. Y `docs/ESTADO_2026-08-07_TRASPASO.md` §1 ya ordena
regenerar esa pareja por otro motivo —es de `5ef3498`, anterior a los siete
arreglos de `d6b0495`—. Se regenerarán igual.

## 4. Qué se hizo

1. Se preservó el manifiesto anterior como
   `docs/datos_manifiesto_OTRA_MAQUINA_2026-08-07.json`. **No se perdió la
   identidad de los 20 parquets de ES/GC/MES/MNQ/NQ**, que sólo existen allá.
2. Se regeneró `docs/datos_manifiesto.json` desde esta máquina:
   **11 archivos, 683,7 MB**, `exit=0`, *"todo coincide"*.

### Consecuencia que hay que tener presente

`--emitir` hace **reemplazo destructivo**: escanea el disco y reescribe entero,
sin fusionar. Por eso el manifiesto vigente ahora describe **sólo el subconjunto
6E de esta máquina**. Cuando la otra máquina lo verifique va a reportar sus 20
parquets como `FALTA` — correcto y esperado, pero hay que saberlo.

**La reconciliación sigue abierta y es decisión de Nico:** cuál conjunto es el
canónico, o si el manifiesto debe fusionar ambos. Este documento no la resuelve.

## 5. Lección — y es la que el propio commit `cdfa212` anticipaba

El commit que creó el manifiesto decía:

> *«dos máquinas pueden tener archivos distintos con el mismo nombre y nadie se
> entera»*

Es exactamente lo que pasó — **con el instrumento construido para evitarlo**. El
manifiesto no falló: hizo su trabajo y gritó. Lo que falló fue *cuándo* se
generó: se emitió desde la máquina que no tenía la reexportación, y quedó
fijando como canónico un estado anterior al arreglo.

**Regla que se desprende:** un manifiesto de identidad debe emitirse desde la
máquina que produjo el artefacto canónico, y el commit que lo crea debe declarar
**desde dónde** se emitió y **qué corrida** lo respalda. Un hash correcto de un
archivo equivocado es indistinguible de un hash correcto del archivo bueno.

Vale el paralelo con el otro incidente del día: el pin de `sha256` de
`BigTrap2.cs` no detectó que el archivo **no compilaba**. La misma forma —
*verificar identidad no es verificar validez*.
