# Firma final — Puerta 0 · BigTrap2Absorption

```
FINAL_PUERTA0_SIGNED
```

- **Fecha:** 2026-08-23 · **Auditor:** Claude Opus 5, pasada independiente y adversarial
- **Rama:** `foundation/f0b-compatibility-probe` · **Commit auditado:** `457387a247fb991f52471db348baf5540b8d5861`
- **Árbol:** limpio en todo lo auditado
- **Firewall:** outcomes `false` · junio **no abierto** · MFE/MAE/retornos/barreras/SL/TP/P&L **no abiertos**
- **Supersede:** el `ABIERTO` de `PARIDAD_BT2_ABSORPTION_2026-08-22.md` §«La única discrepancia»
- **Continúa:** `AUDITORIA_INDEPENDIENTE_PUERTA0_BT2_ABSORPTION_2026-08-23.md` (D-1…D-4, C-1…C-8)

> No acepté «ahora da exacto». El fill `11537_B` queda cerrado con la línea cruda
> del CSV, el índice absoluto de la cinta y la causa raíz nombrada.

---

## 1. Verificación mecánica del commit `457387a`

| chequeo | resultado |
|---|:-:|
| `files[]` | **5** ✅ |
| cambios en `edgelab/bridge/indicators/bigtrap2absorption.py` | **ninguno** ✅ |
| cambios en `nt8/BigTrap2Absorption.cs` | **ninguno** ✅ |
| meta fail-closed | ✅ 8 asserts (§1.2) |
| conversión temporal entera (D-1) | ✅ |
| assertions zona↔fill (D-3) | ✅ 4 asserts |
| capa residual 4/4 (D-2) | ✅ capa separada `residual_session_cuts_d2` |
| conjuntos laterales vacíos | ✅ `only_nt8 = only_python = 0` en todas las capas |
| visor | ⚠ correcto en número, **no derivado** (§6) |

Los 5 archivos: `docs/parity_coverage/BigTrap2Absorption.md`,
`docs/research/PARIDAD_BT2_ABSORPTION_PUERTA0.json`,
`docs/research/PARIDAD_BT2_ABSORPTION_PUERTA0_ABSMAGNITUDE.json`,
`tools/verify_layer_parity.py`, `tools/visor_server.py`.

### 1.1 Hashes — todos recalculados por mí, no leídos del artefacto

| componente | sha256 |
|---|---|
| `.cs` repo (892 L CRLF) | `18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641` |
| `.cs` instalado NT8 (949 L) | `0af1f759aacea2913e2e2c8f46fe5579453fb37738359c44cdf499eaebae57a3` |
| **`.cs` instalado, líneas 1–892** | **`18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641`** |
| kernel Python | `0d162a6092c31228ec0f4f9539b4afc0cb5031737263db4369dea2ad03697ab2` |
| export AbsDirectional | `c6eaeb210eeb029930f8157ac76380954700eed80dd5bf5b05df18a5ee9c19d7` |
| export AbsMagnitude | `c521ef990fdce5c495de89f359d19e53dc7416a3701f902aa791f6ff9eb88755` |
| **cinta GC 12-26.Last.txt** | **`dd67cacbc877739f3643235ab89ed4fab358c02c799aa06c274a45f757d581aa`** |

**C-7 confirmado**: la diferencia del `.cs` instalado se explica **exclusivamente** por
las 57 líneas de región generada. El kernel que corrió es el kernel del repo.

### 1.2 Los hardenings, verificados en fuente

- **D-1** `parse_art_to_utc_ns` (l. 42-48): *«Conversión temporal entera (D-1) sin paso
  por float»*. Descompone la cadena y arma el entero; `datetime.timestamp()` ya no
  aparece en el camino.
- **Fail-closed** (l. 169-177): `score_mode` presente **y** igual al esperado, más
  `tape_window`, `absorption_pct`, `absorption_lookback`, `min_history`,
  `min_stacked_rows`, `min_trap_frac`, `require_flow_side_match`. Más estricto que lo
  pedido en C-6. `run_params["ScoreMode"] = expected_score_mode` (l. 246) toma del CLI,
  no del meta, después de haberlos igualado por assert.
- **D-3** (l. 181, 196-198): `len(zones) == len(fills)`, `signal_at == available_at`,
  `side` idéntico, `seq` compatible. Los cuatro detienen la corrida.
- **D-2** (l. 353-370, 744-751): `residual_session_keys` es una **rama separada** del
  `if`, no una exclusión.

---

## 2. FILL `11537_B` — **CERRADO. Fue un error de auditoría.**

### 2.A Las líneas crudas del CSV direccional (`c6eaeb21…`)

```
29597|2026-08-19T10:01:27.1160000|ZONE_CREATED|zone_id=11537_B;created_bar=11537;
      side=trapped_buyers;dir=short;lo=4497.95;hi=4498.15;vol=8;rows=2;
      frac=0.307692307692308;a_score=12;a_thr=11;
      available_at=2026-08-19T10:01:27.1160000;td=20260819

29598|2026-08-19T10:01:27.1160000|FILL|side=trapped_buyers;dir=short;
      fill_px=4497.9;fill_at=2026-08-19T10:01:27.1160000;
      signal_at=2026-08-19T10:01:27.1160000;a_score=12;fill_bar=144222

29602|2026-08-19T10:01:27.1160000|ZONE_CREATED|zone_id=11538_B;created_bar=11538;
      side=trapped_buyers;dir=short;lo=4498.15;hi=4498.35;vol=10;rows=2;frac=0.4;
      a_score=12.5;a_thr=11;available_at=2026-08-19T10:01:27.1160000;td=20260819

29603|2026-08-19T10:01:27.1160000|FILL|side=trapped_buyers;dir=short;
      fill_px=4498.3;fill_at=2026-08-19T10:01:27.1160000;
      signal_at=2026-08-19T10:01:27.1160000;a_score=12.5;fill_bar=144232
```

> **Hay DOS fills en el mismo nanosegundo, con el mismo `side`, el mismo `dir`, el
> mismo `signal_at` y el mismo `fill_at`.** Sólo los distinguen `a_score`
> (12 vs 12,5), `fill_bar` (144222 vs 144232) y el orden de `seq`.
>
> El fill de `11537_B` es **`fill_px = 4497.9`** (seq 29598, `a_score=12`, que coincide
> con el `a_score=12` de su ZONE_CREATED).
> El `4498.3` pertenece a **`11538_B`** (seq 29603, `a_score=12.5`).

### 2.B El kernel actual sobre la vista alineada (`tape_slice=12`, ancla bar 715)

| global_created_bar | local | side | lo / hi | a_score | sig_ts (ART) | fill_ts (ART) | fill_px | idx abs. cinta |
|---:|---:|---|---|---:|---|---|---:|---:|
| 11536 | 10822 | trapped_sellers | 4497.45 / 4497.65 | 17,0 | 10:01:25.176 | 10:01:25.176 | **4498.2** | 270548 |
| **11537** | **10823** | **trapped_buyers** | **4497.95 / 4498.15** | **12,0** | **10:01:27.116** | **10:01:27.116** | **4497.9** | **270573** |
| 11538 | 10824 | trapped_buyers | 4498.15 / 4498.35 | 12,5 | 10:01:27.116 | 10:01:27.116 | **4498.3** | 270598 |

`270598 − 270573 = 25` — exactamente una cubeta. La partición es coherente.

**Python y NT8 coinciden en los tres fills**, campo por campo.

### 2.C / 2.D La cinta en la frontera (UTC `13:01:27.116` = ART `10:01:27.116`)

Orden estable completo del bloque que comparte el nanosegundo (índice = línea 1-based
del `.Last.txt`; `vol=1` en todos):

```
270564   13:01:27.068  last=4497.5  bid=4497.5  ask=4497.9   <- ultimo tick del ns anterior
270565   13:01:27.116  last=4497.4  bid=4497.2  ask=4497.4
270566   13:01:27.116  last=4497.7  bid=4497.2  ask=4497.7
270567   13:01:27.116  last=4497.7  bid=4497.2  ask=4497.7
270568   13:01:27.116  last=4497.7  bid=4497.2  ask=4497.7
270569   13:01:27.116  last=4497.7  bid=4497.2  ask=4497.7
270570   13:01:27.116  last=4497.7  bid=4497.2  ask=4497.7
270571   13:01:27.116  last=4497.8  bid=4497.2  ask=4497.8
270572   13:01:27.116  last=4497.8  bid=4497.2  ask=4497.8
270573   13:01:27.116  last=4497.8  bid=4497.2  ask=4497.8
270574   13:01:27.116  last=4497.9  bid=4497.2  ask=4497.9   <== FILL de 11537_B
270575   13:01:27.116  last=4497.9  bid=4497.2  ask=4497.9
270576   13:01:27.116  last=4497.9  bid=4497.2  ask=4497.9
...
270589   13:01:27.116  last=4498.3  bid=4497.2  ask=4498.3   <- el 4498,3 SI existe
270594   13:01:27.116  last=4498.3  bid=4497.2  ask=4498.3
...
270599   13:01:27.116  last=4498.3  bid=4497.7  ask=4498.3   <== FILL de 11538_B
```

*(El índice `270573` del kernel es 0-based sobre el array de la cinta; corresponde a la
línea 1-based `270574` del archivo. Misma tick.)*

### 2.E Las cinco respuestas exigidas

**¿Cuál es el primer tick de la cubeta siguiente?**
El tick en índice absoluto **270573** (0-based) / línea **270574**, UTC
`2026-08-19T13:01:27.116`, ART `10:01:27.116`, `last=4497.9`, `bid=4497.2`,
`ask=4497.9`, `vol=1`.

**¿Su `last` es 4498,3 o 4497,9?**
**`4497.9`.** El `4498.3` es el primer tick de la cubeta 11539, índice 270598 — el fill
de la zona **11538_B**, no de la 11537_B.

**¿Por qué el harness anterior obtuvo el otro valor?**
Emparejó la zona `11537_B` con el fill de `11538_B`. Los dos fills comparten
nanosegundo, `side`, `dir`, `signal_at` y `fill_at`: **cualquier clave construida sólo
con (timestamp, side) es ambigua y colisiona**. El acta tuvo la prueba delante y la
descartó — escribió *«ZONE_CREATED loguea a_score=12 y el FILL loguea a_score=12,5.
Inconsistencia de log, no de detección»*. **No era una inconsistencia de log: era la
firma exacta de la mala atribución.** El log es internamente consistente; cada
ZONE_CREATED va seguido de su FILL con el mismo `a_score`.

Segunda afirmación del acta también desmentida: *«en el tramo inspeccionado el 4498,3
no aparece ni en `last` ni en `bid` ni en `ask`»*. **Aparece** — líneas 270589-270594 y
270599. El tramo inspeccionado fue demasiado angosto.

**¿El arnés nuevo compara realmente la misma zona/fill?**
Sí, verificado en tres niveles:
1. `11537` está en el set de zonas de **NT8** (`True`) y en el de **Python** (`True`).
2. `burnin_bar_limit = 715 + 500 = 1215`; `11537 > 1215` ⇒ **no es excluible** por
   ancla ni por burn-in.
3. El comparador evalúa `fill_px` con `math.isclose(..., abs_tol=1e-4)` (l. 563): una
   diferencia de 0,4 sería imposible de absorber. Da match porque **es** match.

**¿Error de auditoría, cambio de cinta o diferencia real?**

> **ERROR DE AUDITORÍA.** Mala atribución de fill a zona, corrida en uno.
> La cinta **no cambió** (§3: byte-idéntica). **No hay ninguna diferencia real** entre
> el `.cs` y el kernel Python en ese punto: los dos dan `4497.9` para `11537_B` y
> `4498.3` para `11538_B`.

### 2.F El invariante que lo habría atrapado, y que hoy no se verifica

Las cuatro assertions de D-3 (`count`, `signal_at`, `side`, `seq`) **no habrían
detectado** este error: los dos pares los cumplen. El invariante que lo distingue es

```
a_score(FILL[i]) == a_score(ZONE_CREATED[i])
```

Lo medí sobre los dos exports: **0 violaciones en 647/647 y en 377/377**. El
emparejamiento posicional es correcto. **Recomiendo agregarlo como quinta assertion de
D-3** — es la única de las cinco que discrimina fills homónimos dentro del mismo
nanosegundo, y es exactamente la clase de evento que produjo este falso positivo.
No bloquea la firma: está medido en 0.

---

## 3. Identidad de la cinta

| campo | valor |
|---|---|
| ruta | `C:\Users\nicoc\OneDrive\Documentos\DataNT8\GC 12-26.Last.txt` |
| **sha256** | **`dd67cacbc877739f3643235ab89ed4fab358c02c799aa06c274a45f757d581aa`** |
| **bytes** | **32.325.488** |
| ticks / líneas | **683.188** |
| primer tick | `20260817 030000 1600000;4450.2;4450;4450.2;1` |
| último tick | `20260821 205958 0800000;4661.6;4661.6;4662.2;1` |
| rango UTC | `2026-08-17T03:00:00.16` → `2026-08-21T20:59:58.08` |
| suma de volumen | **779.249** |

**Contraste con el archivo original del chat: 32.325.488 bytes y 683.188 ticks.
Coincidencia exacta en ambos. La cinta NO cambió.** Queda descartado como causa
del `11537_B`.

`docs/parity_coverage/BigTrap2Absorption.md` §1 tiene hoy la celda de sha256 de la
cinta **vacía**. Se completa en el commit 2.

---

## 4. Residuales — cierre explícito

Los 4 cortes de sesión son las barras globales **3947, 8287, 15960, 21841**
(coinciden con las que ya listaba el acta del 22).

| magnitud | AbsDirectional | AbsMagnitude |
|---|:-:|:-:|
| `residual = True` | **4/4** | **4/4** |
| `a_pass = False` | **4/4** | **4/4** |
| `n_hist` | **4/4** | **4/4** |
| `a_thr` | **4/4** | **4/4** |
| **zonas creadas por NT8** | **0/4** | **0/4** |
| **zonas creadas por Python** | **0/4** | **0/4** |

Los dos últimos renglones los derivé de los sets de zonas —intersección de
`created_bar` con las 4 barras residuales— sin tocar el kernel, como corresponde.
Hoy `residual_session_cuts_d2` no publica ese campo; se agrega en el commit 2.

---

## 5. Headline AbsMagnitude — confirmación independiente

Re-corrí el harness con `--expected-score-mode AbsMagnitude`. **Todo reproduce:**

| exigido | medido | |
|---|---|:-:|
| export sha `c521ef99…8755` | `c521ef990fdce5c495de89f359d19e53dc7416a3701f902aa791f6ff9eb88755` | ✅ |
| `score_mode=AbsMagnitude` | sí | ✅ |
| una sola meta | 1 | ✅ |
| 28.042 cubetas | 28.042 | ✅ |
| 377 zonas / 377 fills | 377 / 377 | ✅ |
| 27.328 comparables | 27.328 (714 pre-ancla, 1 post-export) | ✅ |
| aritmética 27.328/27.328 | `signed_flow`, `d_ticks`, `a_score`, `n_ticks`, `residual` | ✅ |
| umbral 26.824/26.824 | `a_pass`, `n_hist`, `a_thr` | ✅ |
| residuales 4/4 | los cuatro campos | ✅ |
| zonas/fills 365/365 | 365/365 (7 pre-ancla, 5 pre-burnin) | ✅ |
| `only_nt8 = only_python = 0` | 0 / 0 en todas las capas | ✅ |
| cero discrepancias | 0 | ✅ |

Verificado además, sin que se pidiera: el export AbsMagnitude ve **701.002 ticks**,
idéntico al direccional ⇒ **es la misma cinta cargada en NT8**, no otra ventana.

También reproduje el direccional en el harness nuevo: **626/626 zonas y fills**,
`only_*` en 0, aritmética y umbral al 100 %, residuales 4/4.

---

## 6. Observación residual — el visor no es derivado

`tools/visor_server.py:68` es una **cadena escrita a mano**:

```python
"BigTrap2Absorption": ("EXACT", "Headline AbsMagnitude: GC DEC26 27.328/27.328 cubetas
 (100%), 365/365 zonas/fills post-burnin (100%), 26.824/26.824 umbral causal (100%),
 4/4 residuales - PASS Puerta 0"),
```

**Verifiqué uno por uno que los seis números son correctos** contra mi propia
re-corrida. Pero no se leen del artefacto: si el JSON cambiara, el visor no se entera.
Es la misma familia que P-35 (`WARN` sellado como `parity_exact`) y P-39 (el nombre no
verificado contra el contenido).

**No bloquea la firma** —los números son ciertos hoy y están medidos—, pero queda
anotado como deuda: el visor debería leer `regression_verdict` y los conteos del JSON.

---

## 7. Veredicto

```
FINAL_PUERTA0_SIGNED
```

**Las dos condiciones de firma se cumplen:**

1. **El fill `11537_B` queda explicado con evidencia**: línea cruda del CSV, índice
   absoluto de la cinta, causa raíz nombrada (mala atribución de fill a zona por clave
   ambigua dentro del mismo nanosegundo), y las dos afirmaciones fácticas del acta
   —`4497.9` no era el fill correcto, y el `4498.3` no estaba en la cinta— desmentidas
   contra la fuente.
2. **La cinta queda identificada** por sha256, bytes, ticks, rango y volumen, y es
   byte-idéntica a la original.

### Lo que la firma cubre

Paridad `.cs` ↔ Python de **BigTrap2Absorption v1.1.1**, headline `AbsMagnitude`,
sobre GC DEC26 17–21 ago 2026, en las 27.328 cubetas comparables (97,45 % del export):
aritmética, umbral causal post-burn-in, capa residual de los 4 cortes, zonas y fills,
con conjuntos laterales vacíos y cero claves duplicadas. Más la regresión
`AbsDirectional` sobre la misma cinta.

### Lo que la firma NO cubre

- Las **714 cubetas pre-ancla** (domingo 19:00 → lunes 00:00 ART, 17.814 ticks): la
  cinta no las trae. Es una limitación del insumo, no del kernel.
- Otros instrumentos, otras ventanas, otros valores de parámetro. **No hay barrido
  paramétrico.**
- Cualquier cosa aguas abajo de la identidad de implementaciones: **esto no declara
  edge**, no abre outcomes y no toca junio.
- La deuda del visor (§6) y la quinta assertion recomendada (§2.F).

---

## Aporte al referente

Se cierra el último `ABIERTO` de Puerta 0 mostrando que no era un defecto del
indicador sino del instrumento de medición, y se nombra la causa exacta: **dos fills
legítimos en el mismo nanosegundo con todos los campos de matcheo idénticos salvo el
`a_score`**. El aporte que sobrevive a este caso puntual es el criterio: en un log de
eventos de alta frecuencia, una clave de emparejamiento hecha de timestamp y lado **no
es una clave** — y el campo que la desambigua ya estaba impreso en el archivo, visible,
descartado como cosmético.

## Nota de método

El acta del 22 registró la anomalía correcta (`a_score` 12 vs 12,5) y sacó la
conclusión equivocada. No falló la observación: falló tratar una contradicción interna
como ruido de log en vez de como evidencia. Es el mismo patrón que esta auditoría ya
había encontrado en D-3 —un invariante del que el harness depende sin verificarlo— y
acá se ve el costo: mantuvo Puerta 0 abierta un día sobre un defecto que no existía.
