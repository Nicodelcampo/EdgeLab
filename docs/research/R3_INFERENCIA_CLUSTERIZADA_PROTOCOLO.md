# R3 — protocolo de inferencia clusterizada y equivalencia

- **Congelado 2026-08-21** · estado `PROTOCOL_FROZEN_NOT_EXECUTED`
- Se escribe **antes** de re-medir retorno o costo condicionado, como exige
  `D-HFT-CTX-05` y el playbook (ATJ-13: discovery, freeze y confirmación separados).
- Insumos: R1 sellado (`run_id 0e16a11b81dcb865`) y **R2 ejecutado**
  (`docs/research/r2_matchability_es.json`).

---

## 0. Lo que R2 obliga a cambiar antes de congelar nada

R2 midió que **el emparejamiento no es neutral**: el 18,3 % sin control está sesgado a
zonas **anchas** (SMD del ancho **−1,067**), y por eso a **Asia** (cobertura 0,448) y
**Europa** (0,531) frente a RTH (0,86).

**Consecuencia directa sobre el estimando**: no existe un estimando único sobre «las
zonas HFT». Existe uno sobre el **soporte común**, y ese soporte es angosto en el sentido
literal. R3 lo declara en vez de disimularlo.

---

## 1. Estimando primario — uno solo, y con su soporte escrito

> **Diferencia pareada de `ticks_por_ancho`** en el cruce borde a borde, entre cada zona
> y **su** casi-zona emparejada, **restringida al soporte común**:
> zonas con control emparejado por ancho exacto y separación ≤ 30 min.

**Población del estimando** (`P_SOPORTE_COMUN`): 7.543 de 9.235 zonas, 81,7 %.
**Ancho mediano 3,28 ticks contra 7,76 de las excluidas.**

Esto **no** es «el efecto de la zona». Es el efecto **sobre las zonas angostas que
consiguen control**. Cualquier lectura que lo extienda a zonas anchas o a Asia/Europa está
fuera del estimando y debe rechazarse en revisión.

Las otras cuatro métricas —`ticks`, `ms`, `volumen`, `vol_por_ancho`— son **secundarias**
y se rotulan como tales.

## 2. Unidad de dependencia y esquema de remuestreo

La unidad es la **sesión**. Nunca se publica un CI IID por zona
(`iid_event_ci_forbidden`). Justificación medida, no supuesta: Fano **7,78**, solape
**81,1 %**, m = **156** zonas por sesión.

**Bootstrap no paramétrico de sesiones completas** (Cameron & Miller):

| parámetro | valor congelado |
|---|---|
| unidad de remuestreo | la sesión entera, con todos sus pares |
| **B** | **10.000** |
| **seed** | **20260821** |
| estadístico por réplica | mediana de las diferencias pareadas **agrupadas** de las sesiones remuestreadas |
| intervalo | percentil 2,5 / 97,5 |
| sesiones con `< 8` pares | **entran igual** al remuestreo; no se descartan |

### La ponderación, decidida y justificada

`r3.items_to_freeze` exige elegir entre zona-ponderada y sesión-ponderada. **Primaria:
zona-ponderada dentro de la réplica**, es decir, se agrupan todos los pares de las
sesiones sorteadas y se toma una sola mediana.

Motivo: la ponderación por sesión da el mismo peso a una sesión de 4 pares que a una de
300, y R2 mostró que el número de pares por sesión **no es aleatorio** — depende de la
composición por ancho. Ponderar por sesión introduciría el mismo sesgo que R2 acaba de
medir, por la puerta de atrás.

**Secundaria, publicada al lado**: mediana de medianas por sesión. Si las dos difieren en
signo, eso **es** el resultado y se reporta como tal.

## 3. Margen de equivalencia — y por qué NO es económico

Un nulo sin margen no distingue «no hay efecto» de «no hubo potencia». Se declara antes:

> **Margen: |Δ| < 5 % de la mediana del control**, en `ticks_por_ancho`.
> Sobre la base observada de 158,2 → **±7,9**.

**TOST**: se declara equivalencia sólo si el IC del 90 % (bilateral, equivalente a dos
pruebas unilaterales al 5 %) queda **enteramente dentro** de ±7,9.

### La aclaración que este proyecto exige

**Este margen NO es económico, y no puede serlo.** `ticks_por_ancho` cuenta **operaciones
consumidas al atravesar la banda por unidad de ancho**: no está denominado en dinero. Una
diferencia de 7,9 no se traduce a expectativa sin un modelo de ejecución que no existe.

Es un **margen de relevancia práctica**, elegido antes de mirar, no un umbral de
rentabilidad. Para un margen económico haría falta: reglas de entrada y salida, sizing,
fricción estimada **para ES** (nunca transportada de 6E) y fills realistas. Nada de eso
existe hoy, y por eso **ningún resultado de R3 autoriza pasar a P&L**.

## 4. Multiplicidad

| familia | contenido | corrección |
|---|---|---|
| **primaria** | `ticks_por_ancho` sobre `P_SOPORTE_COMUN` | 1 prueba, sin corrección |
| secundaria | las otras 4 métricas | Holm sobre 4 |
| exploratoria | heterogeneidad por fase, ancho, episodio | **sin inferencia**, sólo descriptivo |

No se promueve un corte exploratorio a primario sin un pre-registro nuevo. El registro de
lo explorado forma parte de la credibilidad de cualquier selección posterior; el número
efectivo de pruebas **considera dependencia entre métricas**, que están fuertemente
correlacionadas entre sí, y no es un conteo bruto.

## 5. Sensibilidades obligatorias, todas derivadas de R2

R2 midió tres propiedades del emparejamiento que pueden mover el resultado. Las tres se
re-corren y se publican **junto** al primario, no en lugar de él:

| # | qué | por qué |
|---|---|---|
| S1 | re-emparejar en **orden inverso** y en **permutación con semilla** | el greedy cambia el 38,1 % / 27,1 % de las asignaciones |
| S2 | restringir a controles **anteriores** a la zona | el 60,9 % de los controles es posterior |
| S3 | emparejar **con reemplazo** | recupera 525 pares; reutilización máxima 11 |
| S4 | separación ≤ **5 min** en vez de 30 | el p95 es 17,2 min |

**Si el signo del primario cambia en alguna, el resultado es esa inestabilidad**, no el
número puntual.

## 6. Heterogeneidad: se reporta, no se promueve

Se publica la diferencia pareada por fase, por ancho y por estado de episodio **con su CI
clusterizado**, y explícitamente rotulada `EXPLORATORY_NOT_CONFIRMATORY`.

**Prohibido**: elegir el corte que da significancia y presentarlo como hallazgo. Si una
celda aparece interesante, va a un pre-registro propio con su propia potencia.

## 7. Qué NO decide R3

- No decide si la zona sirve: mide un contraste de microestructura sobre una
  subpoblación declarada.
- No autoriza outcomes direccionales, MAE/MFE, barreras ni P&L.
- No toca el holdout.
- No modifica `HFTZonesESPureV2Flat`.

## 8. Condición de cierre por la negativa

Si el IC del primario queda dentro de ±7,9 **y** las cuatro sensibilidades coinciden en
signo, el costo de cruce queda **cerrado por equivalencia sobre el soporte común** — con
la aclaración permanente de que las zonas anchas y Asia/Europa **nunca entraron**, y que
para esas hace falta otro control.
