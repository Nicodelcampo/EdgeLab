# Actualización para el auditor — 30 commits desde `80f59dd`

**Desde:** `80f59dd` (tu iteración 3) · **Hasta:** `d5cf05b`
**Rama:** `foundation/f0b-compatibility-probe` — **cambió, ver §0**
**Nada ejecutado en NT8. Holdout sin abrir. Outcomes sin abrir.**

---

## 0. Antes que nada: tres correcciones de encuadre

**La rama cambió.** `fix/capture-probe-v2-contract` se mergeó a
`foundation/f0b-compatibility-probe`, que es la que `CLAUDE.md` declara. La causa
raíz de que dos máquinas midieran cosas distintas era ésa: 70 commits vivían en
una rama que el documento rector no mencionaba. Hay un comando que lo vigila:

```
python tools/estado.py
```

**Tenés razón en que las tres capas no son evidencia independiente.** Leyeron el
mismo repo con el mismo encuadre; su coincidencia no confirma nada. Lo utilizable
fueron **las reproducciones concretas**, y así se trataron: de los ítems del
backlog, los que se aplicaron son los que pude **reproducir en el código antes de
tocarlo**, y hay uno que **refuté**.

**K1 sigue abierto y sigue siendo tuyo.** No lo toqué. Coincido con tu lectura
preliminar —P5 es admisible por ser target-free, porque la cuarentena quema días
como *muestra inferencial* y P5 compara bytes de EventLog— pero **no está escrito
en ningún lado y la ausencia se está tratando como permiso**.

## 1. G0 y G1 — reproducir antes de corregir

`2da4c41` — **ocho reproducciones, las ocho en rojo**, antes de tocar nada.
`ab91dce` — el parche.

Lo peor era **H-GPT-1**: `verif` no existía en el módulo, la rama `denom == 0`
tiraba `NameError`, y el test que la nombraba **abstenía antes de alcanzarla**.
Tercera instancia del patrón B3/H2.

**Hallazgo propio, que ninguna de las tres capas vio:** hay **dos emisores de
`FOOTPRINT_MISMATCH` con esquemas distintos** — `.cs:541` con los 5 pares,
`.cs:601` con 4, **sin volumen**. GPT-6 escribió *"ReportarMismatch parece emitir
los cinco pares"*: cierto e incompleto. Consecuencia: el fixture que GPT-6
propuso como **adversarial** es en realidad **fiel** a `.cs:601`, y **tres
fixtures míos eran infieles**.

## 2. N1 — cerrado, y el riesgo no era el que se vigilaba

`99bf88e`. Comparé **dos fuentes**: v2.4 contra
`archive/nt8_cs_backup/BigTrap2_v2.1_20260727_102239.cs`, la que produjo el
oráculo. Sin abrir ningún oráculo.

Las cuatro emisiones nuevas **no tocan el camino de tiempo** (`DrainReadyBars:387`
hace `return` antes de `DrenarPorOHLCV`). Pero **el predicado de
`FOOTPRINT_MISMATCH` cambió y los dos son disjuntos**: v2.1 (`.cs:218`) mira
**volumen**, v2.4 (`VerificarOHLC`) mira **OHLC**. El conteo difiere, `eventSeq`
es compartido, y **P5 habría dado FAIL por el contador**.

De las cuatro salidas de GPT-5 sólo la 2 es defendible. Nico la aprobó:
**identidad económica en orden, `seq` reportado y no juzgado** (`506c598`,
contrato **v5** `23981e56…`).

**Y esa relajación la adjudicó Grok** (`6c1bbb0`,
`docs/research/ITERATION_4_GROK_2026-08-06.md`). No la refutó, pero encontró tres
cosas y **las tres eran ciertas**:

- **Overclaim mío:** el docstring decía *"bit-idéntico… cualquier otra diferencia
  = FAIL"*. Falso — P5 nunca cubrió regresiones de sólo-diagnóstico, ni antes ni
  después.
- `delta_seq_distintos[:20]` **truncaba el catálogo** (se perdía la cardinalidad).
- `footprint_mismatch_por_lado` es conteo global, no emparejado con la
  comparación económica.

**Desacuerdo registrado para Nico, no votado:** si `seq_corrido=true` con
económicos idénticos debe ser PASS, ABSTAIN o FAIL de política.

## 3. P3 se resolvió sola — y una modificación se descartó

Con el mismo grafo: `.cs:601` es **exclusivo del camino de tiempo**; `.cs:541`,
exclusivo del de tick. En capturas de tick **todo mismatch trae los cinco pares**.

**Y agregarle volumen a `.cs:601` habría roto P5**, porque es el payload del
camino que P5 exige idéntico. La «salida B» quedó descartada.

## 4. T6 — el gate de compilación, **ejecutado**

`d5cf05b`. **`BigTrap2.cs` v2.4 COMPILA.** Primera vez que alguien lo verifica.

```
csc 4.8.9232.0 · 28 referencias desde NinjaTrader.Custom.csproj
real exit=0 · control negativo exit=1 (CS0103) · fuente_intacto True
runs/pred004/compila_v24.json  resultado_sha256 73a573b7…
```

NT8 **no se abrió**; todo en un temporal. Equivalencia y no aproximación: las
referencias salen del proyecto que NT8 usa. El control negativo reproduce el
defecto **real** de v2.3 —identificador sin declarar—, no un error trivial.

Tres defectos **míos** encontrados al correrlo: reportaba `NO_COMPILA` cuando la
causa era una referencia sin resolver (ahora **ABSTAIN**); el parser perdía los
errores sin prefijo de archivo; la ruta de reference assemblies estaba
hardcodeada.

## 5. EXPLORE-001 — el contrato de eventos y la curva

**Cinco de seis indicadores no podían producir la población autoritativa.** La
enmienda congelada de primeros toques declara que las tasas de **creaciones** son
diagnósticas; la maquinaria correcta existía con 10 tests en verde y **ningún
programa la llamaba**. Se agregó el runner (`censo_primeros_toques.py`) y se
normalizó el contrato de eventos (`1f0f62d`, `ff59472`).

**Verificado que no puede romper paridad:** `parity.py::match_zones` consume
`zones`, no `events` (`grep -c zone_id parity.py` → 0).

**Hallazgo:** `Gaps2` y `HFTZones2` **registran un toque en la barra que creó la
zona**. No se parcheó: es decisión de regla de entrada.

**Y un fail-open del censo:** `AACloseOpenDiffs` producía `status=COMPLETE` con
`raw_count=0` por no tener concepto de toque. **Un rechazo grita; un cero parece
un dato.**

`curva_excursion.py` mide, por umbral de alejamiento previo, cuántas señales
sobreviven — **en dos arquetipos** (retorno y ruptura) y desglosado por `kind`.
Nico objetó la v1 con razón: *"no es lo mismo una entrada en un gap que en una
burbuja de absorción"*.

## 6. Costos — G3 destrabado

`18c3da9`. Comisión real confirmada en la fuente de Lucid: **$2,40/pata**, no los
$2,20 pre-registrados como estimación. La fricción pasa de **2,704 a 2,768**.

**CAMP-001 no se re-abre:** dio negativo con los costos **subestimados**.

Dos acoplamientos aparecieron al tocarla: los **golden de la spec sellada leían
la constante de producción** (un hecho de mercado rompía un contrato sellado), y
había **tres copias hardcodeadas** del 2,704, una de ellas la que calcula el MDE
(`938a8f8`).

## 7. Cuatro errores míos, por si sirven para calibrarme

1. **Inventario vencido:** afirmé que faltaban walk-forward y desglose de costos.
   Los dos existían desde el 2026-07-25.
2. **Clon viejo:** dije «falta el 90 % del censo» mirando `E:\EdgeLab`, que estaba
   atrasado.
3. **Manifiesto no versionado:** dije que EXPLORE-001 estaba **bloqueado por 3
   sesiones**. Falso — son 201 y **pasa**. Mi 197 salía de un manifiesto del
   27-jul. **`runs/censo/manifiesto_universo.json` estaba gitignoreado**, y los
   dos clones daban veredictos **opuestos** sobre si el estudio puede empezar.
   Ahora está versionado y `estado.py` publica su huella (`438804e`).
4. Y con eso **se retira** el «200 → 197 por los viernes de roll»: con el
   manifiesto actual son **201 → 201**. Ese tramo del linaje **vuelve a estar
   abierto**, junto con `256 → 201`.

Las cuatro son la misma familia: **una fuente local desactualizada produciendo una
conclusión falsa**. La tercera es la peor porque no es un documento, es **el
denominador del estudio**.

## 8. Abierto

| # | qué | de quién |
|---|---|---|
| 1 | **K1 / T3c — admisibilidad del oráculo de P5 frente a INC-005** | **auditor** |
| 2 | Sellar el espacio de reglas de entrada (enmienda pre-outcome) | Nico |
| 3 | `seq_corrido=true` ⇒ ¿PASS, ABSTAIN o FAIL de política? | Nico |
| 4 | Definición de toque para Gaps2 / HFTZones2 / AACloseOpenDiffs | Nico |
| 5 | Linaje `256 → 201` y `197 → 193` | abierto |
| 6 | El MDE 1,14 **no lo pude reproducir** desde los insumos documentados | abierto |
| 7 | Reemitir la tabla de 40 geometrías con fricción 2,768 | Claude |
| 8 | Capturar PRED-004 (`time:1 → K25 → K10`) — bloqueado por (1) | Nico + Claude |

**Van seis instancias del mismo modo de falla en un día** —B3, H2, H-GPT-1, el
cero silencioso, la fricción duplicada, y el truncamiento que encontró Grok—.
Asumí que hay una séptima.
