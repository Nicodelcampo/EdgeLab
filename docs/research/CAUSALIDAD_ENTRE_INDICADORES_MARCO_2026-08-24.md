# Causalidad entre indicadores — qué aparato aplica y cuál no

- **Fecha:** 2026-08-24 · **Estado:** marco de referencia, **no hay medición acá**
- **Origen:** pregunta de Nico — *«al comparar dos indicadores, buscando correlaciones,
  determinar si uno es causa del otro, seguir la cadena hasta la causa inicial y darle
  más peso, dejando al resto como indicios»*
- **Firewall:** no toca outcomes · no declara edge

> Este documento **no mide nada**. Ordena qué herramienta sirve para qué, cuál no sirve
> acá y por qué, para no gastar tiempo en el aparato equivocado.

---

## 1. El vocabulario tiene casa formal, pero no en este dominio

**Necesaria / suficiente / contribuyente / INUS** es el núcleo de **QCA** (Qualitative
Comparative Analysis), su variante difusa **fsQCA**, y **NCA** para condiciones
necesarias. Aparato real y riguroso: calibra variables como conjuntos difusos y busca
*configuraciones* conjuntamente suficientes.

**Está construido para N chico.** La literatura es epidemiología, política pública,
emisiones. **Cero aplicaciones en microestructura de mercado**, y con ~10⁴ eventos por
configuración no es la herramienta.

Para series temporales financieras el aparato es otro: **Granger, transfer entropy,
convergent cross-mapping, PCMCI**.

---

## 2. La trampa que invalida la versión ingenua

**Principio de la causa común (Reichenbach):** si `X` e `Y` correlacionan, hay tres
opciones — `X→Y`, `Y→X`, **o una `Z` que causa a las dos**.

**Granger no distingue causación: mide mejora predictiva.** Dos indicadores que leen la
misma cinta tienen a la cinta como `Z`, y van a "Granger-causarse" mutuamente sin que
exista ninguna flecha entre ellos.

Estado del arte: **Runge et al., *Science Advances* 2019 · *Nature Communications*
2019** — algoritmo **PCMCI**, paquete `tigramite`. Existe justamente para descubrir
estructura causal en series temporales **controlando dependencias espurias por causa
común y por autocorrelación**. Su resultado central: las redes causales estimadas quedan
**mucho más ralas** que las de correlación.

Hallazgo empírico útil: hay **causalidad no lineal significativa** en índices
accionarios, o sea que la correlación de Pearson —buen proxy de la causalidad lineal—
**subestima la causalidad total** (*arxiv:2312.16185*).

---

## 3. Para BigTrap2 vs BigTrap2Absorption la pregunta está mal planteada

Verificado en fuente. `BigTrap2Absorption` **no es un indicador distinto**: es el kernel
de BigTrap2 más tres filtros encima —percentil causal `a_pass`, `MinStackedRows`,
`MinTrapFrac`.

```
zonas de Absorption  ⊆  traps de BigTrap2      por construcción
```

No hay causación: hay **contención de conjuntos**. Granger daría casi perfecto y no
significaría nada. Es error de categoría, no resultado.

**Dónde sí aplica:** entre indicadores que leen la misma cinta pero computan cosas
genuinamente distintas — `BigTrap2` · `Gaps2` · `HFTZones2` · `aVolClusterPOI`. Ahí la
causa común es el flujo de órdenes, y ése es el confundidor a controlar.

---

## 4. Solapamiento ≠ estructura de dependencia

`specs/bt2_absorption_target_free_sweep_v1.json` lleva escrito:

```json
"warning": "event overlap is descriptive; it is not an effective test count"
```

con la prohibición explícita de derivar «número efectivo de tests» del Jaccard. La razón,
en términos causales:

- **Solapamiento alto ≠ redundancia.** Dos configs pueden compartir el 95 % de los
  eventos y diferir justo en el 5 % que decide.
- **Solapamiento cero ≠ independencia.** Dos configs pueden particionar la misma señal y
  ser perfectamente redundantes sin compartir un solo evento.

El Jaccard mide **coincidencia de conjuntos**. La cadena causa-raíz/indicio requiere
**estructura de dependencia**, que es justo lo que el Jaccard no da.

---

## 5. Qué es implementable acá, y qué no

### Gratis y target-free — relacionar indicadores entre sí no mira outcomes

| técnica | qué contesta | costo |
|---|---|---|
| **análogo de NCA** | `P(evento │ C)` contra `P(evento)`: ¿`C` es necesaria? | barato |
| **PCMCI** (`tigramite`) | estructura causal controlando causa común y autocorrelación | medio |

Ambas sobre el store de coordenadas ya existente, sin recomputar kernels.

### Desaconsejado

- **QCA/fsQCA directo** — calibración difusa pensada para decenas de casos.
- **Granger crudo entre indicadores** — significativo casi siempre por la cinta compartida.

---

## 6. Dos problemas que no se resuelven guardando datos

**El binning no se puede diferir para siempre.** PCMCI, Granger y transfer entropy
necesitan series **regularmente muestreadas**. Un stream de eventos hay que binearlo, y
la elección no es neutra: muy grueso destruye el lead-lag que se busca, muy fino deja casi
todo en ceros. Causal discovery sobre series irregulares es **área abierta**
(*arxiv:2507.03310*), no algo resuelto que se aplica.

**El store facilita el fishing.** Tener todos los eventos de todos los indicadores en
disco hace barato correlacionar todo contra outcomes hasta que algo dé. La disciplina
tiene que ser **estructural, no de intención**: columnas de outcome físicamente ausentes,
como hace el sweep con `outcomes_opened=false` en sus siete salidas y como fija
`tests/bridge/test_bt2a_event_pit.py`.

---

## 7. La advertencia que ordena todo lo anterior

> Cualquier cadena causal entre indicadores es **entre indicadores**, no **hacia el
> retorno**.

Determinar que `A` causa `B` y que `A` es la raíz **no dice que `A` prediga nada**. Son
dos preguntas separadas, y la segunda sigue costando outcomes y multiplicidad. El
descubrimiento causal puede **reducir el espacio de hipótesis** a testear; no puede
sustituir el test.

---

## 8. Qué existe ya en el repo para esto

| pieza | dónde |
|---|---|
| store de coordenadas de evento | `partials/*.json` → `event_keys` |
| estado point-in-time por evento | rama `research/event-store-pit` → `event_pit` |
| condicionantes de causa común | `tape_rate_per_s`, `spread_p50/p90_ticks` en `event_pit` |
| garantía de no look-ahead | `tests/bridge/test_bt2a_event_pit.py` |
| ejes de contexto ya medidos | `docs/research/B9_Y_NRAND_SOBRE_152_2026-08-23.md` |

**El eslabón que falta** es el binning de §6, que es decisión de investigación y no de
implementación.

---

## Referencias

| ref | aporte |
|---|---|
| Runge et al., *Sci. Adv.* 2019 · *Nat. Commun.* 2019 | PCMCI; redes causales más ralas que las de correlación |
| *arxiv:2312.16185* | causalidad no lineal en mercados; Pearson subestima |
| *arxiv:1401.1457* | comparación Granger lineal / kernel / transfer entropy |
| *arxiv:2312.17375* | CD-NOTS, descubrimiento causal en series no estacionarias |
| *arxiv:2507.03310* | causal discovery en series irregulares — problema abierto |
| *arxiv:2501.02672* | Granger reinterpretado con redes bayesianas causales |
| QCA / fsQCA / NCA | INUS y condiciones necesarias; N chico, otro dominio |

## Aporte al referente

Queda separado lo que suena aplicable de lo que lo es. El vocabulario de condiciones
necesarias y suficientes tiene aparato formal, pero vive en un régimen de N que no es
éste; y la técnica que sí corresponde —descubrimiento causal en series temporales— tiene
un modo de fallar específico que la vuelve inútil justo en el caso de este proyecto: dos
indicadores sobre la misma cinta. Queda anotado antes de gastar tiempo en la herramienta
equivocada, y con el caso concreto donde la pregunta ni siquiera está bien formada,
porque `Absorption ⊆ BigTrap2` es contención, no causación.
