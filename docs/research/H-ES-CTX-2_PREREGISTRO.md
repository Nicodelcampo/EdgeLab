# H-ES-CTX-2 — contextos congelados para el costo de cruce

- **Congelado 2026-08-21** · estado `PREREGISTERED_READY_TO_RUN`
- **Reemplaza a `H-ES-CTX-1`**, que queda `SUPERSEDED` (seguía en `DRAFT_NOT_FROZEN`).
- Decisión delegada explícitamente por Nico. Los contextos se eligieron con el **atlas F1**
  (target-free) y la literatura — **nunca mirando outcomes**.
- Insumos: R1 sellado · R2 ejecutado · R3 congelado y ejecutado · Atlas F1.

---

## 0. El criterio de elección, escrito antes que la elección

R2 midió que el emparejamiento **descarta las zonas anchas** (SMD del ancho −1,067). Por
lo tanto, **cualquier contexto correlacionado con el ancho reintroduce ese sesgo** dentro
de sus celdas.

Ese es el filtro dominante. Un contexto se acepta si cumple **las cuatro**:

1. tiene apoyo externo en literatura, preferentemente **sobre ES**;
2. está disponible en el atlas y es **PRE** (nunca POST);
3. deja **≥ 40 sesiones** por celda;
4. su correlación con `ancho_ticks` es **baja** — el filtro que R2 impuso.

## 1. Los tres candidatos, medidos

| candidato | corr. con ancho | celdas | sesiones por celda | veredicto |
|---|---|---|---|---|
| **régimen de volatilidad** `pct_rv` | **+0,085** | 1.108 / 2.748 / 5.346 | **60 / 61 / 60** | ✅ **primario** |
| **episodio por hueco** 5 s | +0,113 | 6.354 / 2.877 | 62 / 62 | ✅ secundario |
| fase de sesión (RTH vs FUERA) | **−0,255** | — | — | ❌ **rechazado** |

## 2. `C-A` PRIMARIO — régimen de volatilidad previa, normalizado intradía

`pct_rv`: percentil **expansivo** de la volatilidad realizada de los 5 min anteriores,
contra el historial acumulado del **mismo bucket de 15 min**. Terciles: `bajo` < 0,33 ≤
`medio` < 0,67 ≤ `alto`.

**Por qué este.** Andersen, Bondarenko, Kyle y Obizhaeva documentan patrones intradiarios
sistemáticos de volumen, volatilidad y liquidez **sobre ES con datos BBO de CME**;
Takahashi estima el impacto de precio de ES cada 15 minutos y encuentra variación
intradiaria marcada. La consecuencia metodológica de ambos es la misma: **toda magnitud
debe expresarse contra la distribución de su propio horario**, porque un umbral global
mezcla estados que no son comparables.

Además, en la elección práctica gana en las cuatro dimensiones: disponible en el
**99,7 %** de las zonas, **60+ sesiones en cada tercil**, **ancho mediano 3,0 idéntico en
los tres** — y **sin parámetro libre** que elegir.

## 3. `C-B` SECUNDARIO — posición en el episodio, hueco de 5 s

`es_primera_5s` = no hubo zona en los 5 s anteriores. 6.354 primeras contra 2.877 del
resto, 62 sesiones en ambas.

**Por qué.** Es el mecanismo con mejor apoyo teórico: en el fraccionamiento de
metaórdenes, **la primera operación tiene impacto mayor que las siguientes**, porque el
libro se vacía y los proveedores de liquidez reconocen el patrón. El agrupamiento que
medimos —Fano **7,78**— es la firma de ese fenómeno.

**Por qué secundario y no primario.** La evidencia externa es de acciones y LOB general,
no de ES. Y el hueco es un **parámetro libre**: se fija en **5 s** porque es el único
valor de la grilla probada (5 s, 30 s, 60 s, 5 min, 15 min) donde el ancho mediano de
«primeras» y «resto» coincide exactamente (3,0 contra 3,0). **Esa elección se hizo sobre
un diagnóstico target-free —el ancho—, jamás sobre un resultado**, y queda declarada acá
para que se pueda auditar.

## 4. Lo que se RECHAZA, y por qué importa decirlo

**Fase de sesión (`RTH` vs `FUERA`) queda fuera como contexto.** Era el contexto primario
de `H-ES-CTX-1`. Tres razones, todas medidas:

- **corr con el ancho −0,255**, tres veces la de los aceptados: es el candidato **más**
  contaminado por la variable que R2 mostró que sesga.
- R2 midió que la cobertura de emparejamiento cae a **0,448 en Asia** y **0,531 en
  Europa** contra 0,86 en RTH. La celda `FUERA` es justo donde el control falta más.
- Andersen et al. implica que el horario debe ser el **eje de normalización**, no el
  contexto. Y ya lo es: `pct_rv` se normaliza por bucket de 15 min.

**El horario no desaparece: cambia de rol.** De variable de corte a variable de control.

**Memoria de nivel** tampoco entra: no sobrevivió a su nulo corregido (p mediana 0,1796).

## 5. Estimando, inferencia y potencia

Idénticos a `R3_INFERENCIA_CLUSTERIZADA_PROTOCOLO.md`, aplicados **dentro de cada celda**:

| | |
|---|---|
| estimando | diferencia pareada de `ticks_por_ancho`, zona menos **su** casi-zona |
| soporte | **común**: sólo zonas con control. R2: 81,7 %, sesgado a angostas |
| unidad | **sesión completa** |
| B / seed | **10.000 / 20260821** |
| ponderación | zona-ponderada dentro de la réplica; mediana de medianas al lado |
| margen | ±7,91 `ticks/ancho` (5 % de la mediana del control) |

**El MDE por celda se calcula con el MISMO bootstrap y se publica ANTES de interpretar
el punto.** No se deriva analíticamente: la versión `IQR/1,349` de `H-ES-CTX-1` asumía
normalidad sobre una distribución sesgada, mezclaba dispersión full-sample con n de
celda, y trataba una mediana de medianas como si fuera una media. Ese error no se repite.

## 6. Multiplicidad

| familia | pruebas | corrección |
|---|---|---|
| **primaria** | `C-A` × 3 terciles | **Holm sobre 3** |
| secundaria | `C-B` × 2 celdas | Holm sobre 2, rotulada secundaria |
| exploratoria | las otras 4 métricas, y `C-A × C-B` | **sin inferencia**, descriptivo |

La interacción `C-A × C-B` **no** se promueve a primaria sin un pre-registro nuevo.

## 7. Cómo se refutaría

- Los tres terciles dan equivalencia dentro de ±7,91 → **el contexto no separa nada**, y
  la familia queda cerrada también en su forma condicional.
- Un tercil se sale del margen pero **cambia de signo entre las sensibilidades S1–S4** →
  es inestabilidad del emparejamiento, no régimen.
- El efecto aparece en `C-A` pero desaparece al estratificar por ancho **dentro** de la
  celda → era ancho otra vez.
- El efecto sólo aparece en la métrica primaria y en ninguna secundaria → conteo, no
  mecanismo.

## 8. Lo que esto NO decide

Aunque un tercil salga del margen, **no es un edge**. Sigue siendo información
condicional sobre el eslabón 2 de `geometría → información → P&L bruto → edge neto`.

`ticks_por_ancho` **no está denominado en dinero**. No hay reglas de entrada ni salida,
ni sizing, ni fricción estimada para ES, ni fills. **Ningún resultado autoriza pasar a
P&L**: eso necesita su propio manifiesto y el OK explícito de Nico.

El holdout `2026-07-01 → 2026-12-31` permanece intacto.
