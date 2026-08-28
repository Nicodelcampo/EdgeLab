# Auditoría del censo §4 y pre-registro de Puerta 1 — BigTrap2Absorption

- **Fecha:** 2026-08-23 (ART)
- **Rama:** `foundation/f0b-compatibility-probe`
- **Base auditada:** `5aede17fb487cdc122f1d7c70c561041bfb347c4`
- **Commit base verificado:** `files[]=1`, `+171/-0`
- **Firewall:** no se abrió junio; no se abrieron outcomes nuevos; no se declara edge.
- **Headline congelado:** `AbsMagnitude`, TW=25, pct=90, lookback=500, min_history=200.

Este documento corrige dos puntos load-bearing: qué puede inferirse de la mezcla
direccional en cinco sesiones y qué significa realmente «~113 sesiones». También
congela el control `N_RAND` y la política del umbral antes de que exista el panel de
enero-junio.

---

## 1. Dictamen sobre la lectura de la mezcla 54,6/45,4

### 1.1 Lo que se confirma

Sobre el export correcto del headline (`c521ef99…`, 18.804.897 bytes):

- 377 zonas: **206 long / 171 short = 54,64 % / 45,36 %**.
- Por sesión: 51,22 %, 56,36 %, 52,99 %, 54,55 %, 57,47 % long.
- `corr(%long, drift) = -0,2617`, con `n=5`: descriptivo, no inferencial.
- Test de homogeneidad de proporciones: `Q=0,6694`, 4 gl, `p=0,9550`.

No hay evidencia de heterogeneidad gruesa del mix. Tampoco hay señal de que el
portador elija más long precisamente en las sesiones alcistas.

### 1.2 Lo que se refuta

**Eso no descarta que el indicador mida régimen.** Sólo descarta, débilmente, un canal
muy específico: «mix direccional de las señales ↔ drift neto de la sesión».

Las desviaciones binomiales de una proporción ~0,55 con 41–117 eventos por sesión son
de aproximadamente 4,6–7,8 puntos porcentuales. Con cinco sesiones no se probó
equivalencia dentro de un margen; sólo no se rechazó homogeneidad.

Más importante: el censo §4.3 encuentra adaptación de régimen en el propio umbral.
Entre sesiones, la mediana de `a_thr` parece estable (5,000–5,410; 1,08x), pero dentro
de sesión cambia materialmente:

| sesión | p10 | p50 | p90 | p90/p10 | min–max | max/min |
|---|---:|---:|---:|---:|---:|---:|
| 20260817 | 4,340 | 5,000 | 6,700 | 1,54x | 3,500–7,675 | 2,19x |
| 20260818 | 4,500 | 5,000 | 5,667 | 1,26x | 4,258–6,517 | 1,53x |
| 20260819 | 4,775 | 5,410 | 7,040 | 1,47x | 4,333–10,550 | **2,43x** |
| 20260820 | 4,581 | 5,000 | 6,000 | 1,31x | 3,820–6,550 | 1,71x |
| 20260821 | 4,350 | 5,275 | 7,000 | **1,61x** | 3,836–8,000 | 2,09x |

**Conclusión:** la frase de `5aede17` que da por descartada «la versión grave de
P-39» es demasiado fuerte. Queda descartado sólo el seguimiento direccional evidente.
La sensibilidad de `a_thr` al régimen intradía sigue viva y ya está medida.

Se abre **B-9**: el §4.3 original miraba sólo entre sesiones. En el panel pre-outcome
se reportarán también p10/p50/p90 por sesión y por bloque horario. Esto no autoriza
condicionar outcomes.

---

## 2. Censo §4 target-free reproducido

Antes de calcular el headline se reconstruyó el modo fuente `AbsDirectional` desde
`signed_flow` y `d_ticks`.

| hipótesis del anillo | `a_score` | `n_hist` | `a_thr` | `a_pass` |
|---|---:|---:|---:|---:|
| residuales entran | 28.042/28.042 | 28.042/28.042 | 27.955/28.042 | 28.039/28.042 |
| residuales no entran | **28.042/28.042** | **28.042/28.042** | **28.042/28.042** | **28.042/28.042** |

Esto prueba empíricamente que los residuales no alimentan el anillo.

- **§4.1:** `dFav <= 0`: 9.193/28.042 = **32,78 %**.
- **§4.2, todas:** denominador=1: 1.689/28.042 = **6,02 %**.
- **§4.2, a_pass:** denominador=1: 1.071/2.902 = **36,91 %**.
- Mediana del denominador entre `a_pass`: **2,0**.
- `corr(a_score, |signed_flow|)`: 0,6434 global; 0,5813 entre `a_pass`.

El falsador «es volumen con otro nombre» no se dispara. Sí queda una lectura precisa:
el decil alto está enriquecido en **quietud con flujo**; es un estado
microestructural, todavía no una predicción.

### 2.1 Nulo diagnóstico con el mix exacto del headline

Repetido con 206/171, no interpolado:

| sesión | %long | nulo al mix | nulo 50/50 |
|---|---:|---:|---:|
| 20260817 | 51,22 % | 1,0063 | 1,0028 |
| 20260818 | 56,36 % | 0,9766 | 1,0044 |
| 20260819 | 52,99 % | 1,0271 | 1,0012 |
| 20260820 | 54,55 % | 1,0084 | 1,0040 |
| 20260821 | 57,47 % | 1,0371 | 0,9998 |
| **global** | **54,64 %** | **1,0191** | **1,0003** |

El sesgo direccional agrega **+0,0189** de ratio en este tape. El 1,25 queda a
+0,2309 del nulo, equivalente a ~8,39 ticks bajo la escala diagnóstica de agosto.
Este 1,0191 no se transporta a enero-junio: sólo demuestra por qué hay que medir el
nulo dentro del universo de ejecución.

---

## 3. Diseño exacto de `N_RAND` — precondición de Puerta 1

### Respuesta corta

**No se sortea el mix y no se usa 54,6/45,4 como constante.** Se copia exactamente el
mix que `K_ABS` produzca en cada sesión del panel. El control es pareado por sesión;
pooled está prohibido.

### 3.1 Unidad y elegibilidad

Para cada fill válido de `K_ABS` se define un evento `(sesión, contrato, dirección,
bloque horario, cap_driver)`:

- sesión CME `[17:00, 16:00)` America/Chicago;
- bloque horario fijo de 30 minutos desde las 17:00 CT;
- `cap_driver ∈ {ticks, clock}` se calcula sólo con timestamps: qué liga primero,
  2.000 ticks o 900 segundos;
- se excluye y etiqueta `EXCLUDED_FILL_CROSSES_SESSION` si ninguno de los dos caps
  liga antes del fin de sesión.

### 3.2 Generación

Para cada réplica `b=1…10.000` y cada evento real:

1. copiar **la misma dirección** del evento real;
2. muestrear un tick-ancla elegible en la misma sesión, contrato, bloque de 30 minutos
   y `cap_driver`;
3. muestrear sin reemplazo dentro de la réplica; entre réplicas sí se reutiliza;
4. excluir sólo los índices que sean anchors reales exactos; no excluir ventanas
   vecinas, porque la dependencia se absorbe a nivel sesión;
5. si un estrato no tiene capacidad, fallar con
   `PRECONDITION_FAILED_SPARSE_STRATUM`; no ampliar bins en silencio.

Semilla congelada: `20260821`. Así `N_RAND` preserva exactamente por sesión:
`n`, `n_long`, `n_short`, contrato, distribución horaria y mezcla de caps.

### 3.3 Pareo e inferencia

- Se calcula un contraste por sesión; cada sesión pesa 1, no su número de eventos.
- Estimando principal: `Δ_s = d_hat(K_ABS,s) - mediana_b[d_hat(N_RAND,b,s)]`.
- IC 95 %: wild cluster bootstrap Webb six-point, 10.000 réplicas, más referencia
  `t(G-1)`; cluster = sesión.
- `K_ABS_SHUFFLE` es control secundario obligatorio: mismos anchors reales y
  permutación de las direcciones dentro de sesión preservando sus conteos. Aísla la
  información direccional del timing elegido por el indicador.
- `K_BT2` se corre en las mismas sesiones para la comparación incremental.

---

## 4. Potencia: corrección de un error load-bearing

El número **~113** no era 80 % de potencia. Sale de igualar el efecto +0,053 al
semiancho esperado del IC 95 % con `sd_sesión≈0,282`:

`1,96 * 0,282 / sqrt(113) ≈ 0,052`.

Eso deja el límite inferior alrededor de cero cuando el estimador cae justo en su
esperanza. La probabilidad de pasar es apenas **51,5 %**, no 80 %.

| G | semiancho IC95 ratio | MDE 80 % ratio | MDE 80 % ticks |
|---:|---:|---:|---:|
| 113 | 0,0520 | 0,0743 | 2,70 |
| **120** | **0,0505** | **0,0721** | **2,62** |
| **132** | 0,0481 | 0,0688 | **2,50** |
| 201 | 0,0390 | 0,0557 | 2,03 |
| 223 aprox. | 0,0370 | 0,0529 | 1,92 |

Con G=120:

- efecto legacy +0,053: **53,9 %** de potencia; requiere **223** sesiones para 80 %;
- efecto ilustrativo ajustado por nulo +0,0369: ~30 %; requiere del orden de **450**;
- efecto económicamente declarado de 2,5 ticks (~0,06875 ratio): **76,1 %**;
  requiere **133** sesiones para 80 %.

La `sd=0,282` viene de cinco sesiones y es una hipótesis de planificación, no una
constante conocida.

### Decisión

Se acepta correr el bloque completo único de ~120 sesiones, pero **no se baja la vara
económica de 2,5 ticks**. Si el número final de sesiones únicas completas es menor que
133, se adjunta `P1_UNDERPOWERED_FOR_2P5T`; un resultado positivo puede pasar los gates,
pero un no-pass no se vende como refutación de efectos de tamaño BigTrap2.

---

## 5. Umbral: se congela el procedimiento, no un número de agosto

Un número fijo basado en `1,0191` sería más simple y metodológicamente incorrecto:
mezclaría contratos, sesiones, drift y tasa de ticks de agosto con enero-junio.

Se congela antes de correr:

1. generar `N_RAND` con el algoritmo del §3;
2. obtener el nulo en las mismas sesiones y con el mix realizado por sesión;
3. expresar el resultado primario como `Δd_hat` en ticks, pareado contra ese nulo;
4. mantener **2,5 ticks** como vara económica fija;
5. reportar el ratio nulo y el ratio equivalente sólo como traducción descriptiva.

Por lo tanto, **1,25 deja de ser gate primario**. No se reemplaza por otro ratio
inventado. El nuisance baseline sale de los datos por un procedimiento congelado; eso
es randomization inference, no tuning.

### Estados

- `P1_PASS`: `Δd_hat(K_ABS−N_RAND) >= 2,5`, L95>0 y `K_ABS` no queda por debajo de
  `K_BT2` en el contraste pre-registrado.
- `P1_FAIL_BUT_REAL_SIGNAL`: L95 contra `N_RAND` >0, pero no alcanza 2,5 ticks o no
  demuestra mejora sobre `K_BT2`.
- `P1_FAIL_WORSE_THAN_BT2`: U95 de `K_ABS−K_BT2` <0.
- `P1_INCONCLUSIVE`: los demás casos; si G<133, adjuntar la etiqueta de potencia.

---

## 6. Universo, roll y deuda de paridad

Se conservan completos los tapes GC 04-26, 06-26 y 08-26. El panel analítico contiene
una sola observación por sesión.

Regla de roll pre-outcome:

1. sumar volumen impreso por sesión para cada contrato en el solapamiento;
2. exigir dos sesiones completas consecutivas con volumen del sucesor mayor;
3. hacer efectivo el roll en la sesión siguiente a la segunda confirmación;
4. una vez hecho el roll, no volver atrás;
5. conservar tabla de decisión y ambos tapes para auditoría.

Antes de cualquier outcome, el oráculo NT8 de GC 08-26 (2026-06-18 a 2026-06-30) debe
reproducirse con su tape. Cualquier mismatch no explicado en `a_score`, `a_thr`,
`a_pass`, zonas o fills bloquea Puerta 1.

---

## 7. Hipótesis de contexto

No hay contexto outcome-conditioned autorizado. Antes de abrir MFE/MAE:

- completar B-9 target-free sobre las ~120 sesiones;
- cualquier contexto candidato debe ser único, pre-registrado y tener control con el
  mismo contexto sin el indicador;
- debe demostrarse que no es una reexpresión de `a_thr`, hora o tasa de ticks;
- el headline plano se informa siempre, aunque el condicionado salga mejor.

---

## 8. El antes y después

| antes | después de esta auditoría |
|---|---|
| ratio 1,25 contra cero | `Δd_hat` contra `N_RAND` pareado + vara fija 2,5 ticks |
| mix global 54,6 % | conteos exactos por sesión, copiados evento a evento |
| pooled posible | sesión es cluster y pesa 1 |
| ~113 = potencia suficiente | ~113 = sólo semiancho≈efecto; potencia ~51,5 % |
| régimen descartado por mix estable | sólo se descarta seguimiento direccional grueso; `a_thr` intradía sigue vivo |
| roll «por volumen» informal | regla monotónica de dos confirmaciones congelada |
| §4.3 entre sesiones | B-9 agrega dinámica intradía robusta |

```text
PUERTA_0                = FINAL_PUERTA0_SIGNED (GC 12-26 agosto)
PUERTA_0_GC08_JUNIO     = BLOCKED_PENDING_ORACLE
CENSO_SECCION_4         = COMPLETE_TARGET_FREE
B-9                     = OPEN_TARGET_FREE_INTRADAY_THRESHOLD
N_RAND                  = PREREGISTERED_NOT_RUN
POWER_G120_2P5T         = 0.761_APPROX
SESSIONS_FOR_80PCT_2P5T = 133_APPROX
OUTCOMES_JUNIO          = NOT_OPENED
EDGE                     = NOT_DECLARED
```
