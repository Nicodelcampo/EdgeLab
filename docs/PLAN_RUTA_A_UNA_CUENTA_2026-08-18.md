# Plan · Ruta a una cuenta — 2026-08-18

> **Para qué existe.** Tres cosas vivían separadas y se leían como si fueran la misma:
> las **debilidades** (qué está mal), los **8 capítulos** (qué las salda) y **H-Z2A**
> (la hipótesis viva). Este documento las conecta y dice **qué paso viene ahora**.
>
> **Cómo se mide el progreso.** Distancia reducida hacia un edge neto y operable.
> No en `P-NN` cerrados, no en GiB podados, no en paridades verdes.
> `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.

---

## 1. El diagnóstico, en una línea

**Fuerte en no engañarse. Débil en acercarse a una cuenta.**

Eso no es una metáfora: es el resultado de la auditoría del 15-ago
(`docs/research/AUDITORIA_DEBILIDADES_Y_GATES_2026-08-15.md`), donde cada debilidad se
verificó contra el código.

---

## 2. Debilidad → capítulo → estado → qué la mueve

| # | Debilidad | Cap. | Estado hoy | Qué la mueve |
| --- | --- | --- | --- | --- |
| 1 | **Cero expectativa neta.** `EDGES_DISCOVERED` = ninguno. H1 murió −2,47 t/evento. F4 nunca corrió. | 1 | abierta | **C1 → manifiesto → STOP → F4** |
| 2 | **Sin OOS económico.** Holdout sano, pero sin candidato G3. | 7 | cerrada a propósito | nada hasta tener candidato |
| 3 | **Robustez ociosa.** G2 escrito, nunca ejercido. Allowlist vacía (P-38). | 6 | abierta | sanea en paralelo, **no es ruta crítica** |
| 4 | **Sin ejecutable.** Sin entrada/salida/sizing/kill switch. W7 incompleto. | 3, 4 | parcial | spread **medido**; falta comisión del broker (Nico) |
| 5 | **Sin control de riesgo de despliegue.** | 8 | no toca | — |
| 6 | **Los medios se volvieron el fin.** Progreso medido en infraestructura. | 0 | reabierta 16-ago | este documento, y no cerrar P-NN como sustituto |

**Regla de lectura**: cerrar un `P-NN` de paridad **no mueve ninguna fila de esta
tabla**. P-42, P-43 y P-44 son higiene. Valen — pero no son distancia recorrida.

---

## 3. El orden, y por qué es ése

Del addendum 007, no del 006:

```
0 ledgers ──> 3 costos ──> 5 población + 2 N_eff ──> 1 F4 ──> 4 simulador ──> 6 G2 ──> 7 OOS ──> 8 sombra
                                                                    │
                                            g2-a1 sanea EN PARALELO ┘
```

**Por qué población (cap. 5) antes que la pregunta económica (cap. 1):** un manifiesto
F4 necesita declarar N, MDE y presupuesto de multiplicidad **antes** de mirar nada.
Sin el N del censo, el manifiesto se escribe alrededor de números inventados.

**Por qué G2 no es la ruta crítica:** G2 adjudica un candidato. Todavía no hay
candidato. Sanear `g2-a1` mientras tanto no cuesta nada; ponerlo primero, sí.

---

## 4. H-Z2A — la hipótesis viva

**Qué es.** Segunda aproximación a una zona tras *near-miss* → rechazo → reset.

**Estado.** `HYPOTHESIS_REFINED_NOT_RUN`. Cuatro versiones en un día (16-ago);
**v4 manda**: `docs/research/H_Z2A_V4_DEPURACION_EPISTEMICA_Y_DISENO_FINAL_2026-08-16.md`.
v1–v3 se conservan como archivo, no se borran.

**Qué depuró v4.** La secuencia completa **no** tiene fuente primaria como una sola
ley. Las piezas sí (Osler, Chung & Bellotti, Xu et al., pinning/GEX). Por eso es
**hipótesis compuesta original, no replicación**, y cada pieza puede morir sola.
También corrigió sobre-afirmaciones de v3: `poor high ≠ near-miss`, se cayó la «regla
del 80 %», confluencia ≠ profundidad L2.

**Portadores** (decididos por Nico):

| Rol | Indicador | Por qué |
| --- | --- | --- |
| Ciencia | `aVolClusterPOI` v0.5 | paridad exacta, config fija, ciega a outcomes |
| Fixture | `BigTrap2` | sólo ingeniería — **no** entra como ciencia |
| Control | `Gaps2` | mecánico |

**Multiplicidad gastada hasta hoy: 0.** Ni un outcome, ni un P&L, holdout intacto.

---

## 5. El paso que viene: C1, censo-superficie

**Ruta crítica. Es lo único que mueve la fila 1 de la tabla.**

### La grilla — 60 celdas, congelada

```
D_far ∈ {10, 20, 40, 80}      4 valores
δ_nm  ∈ {1, 2, 3, 5, 8}       5 valores
R_min ∈ {5, 10, 20}           3 valores
                              ─────────
                              60 celdas
```

### Tres condiciones de lectura (entrada 014, no negociables acá)

1. **`δ_nm` también en unidades de spread.** En 6E el spread es 1 tick el **89,0 %**
   del tiempo (medido, 5.554.201 quotes), así que la columna `δ_nm = 1` está **sobre
   el spread**, no cerca. Eso hay que verlo en el reporte, no descubrirlo después.
2. **Anillos marginales, no sólo acumulados.** Los anillos anidan
   (`δ_nm=1 ⊂ δ_nm=2 ⊂ …`): publicar sólo conteos por celda **sobre-cuenta
   visualmente** la superficie.
3. **`n` = sesiones por celda**, no sólo eventos. Un N grande concentrado en tres
   sesiones no es N.

### Dos predicados, declarados y no mezclados

| | Definición | Rol |
| --- | --- | --- |
| **Primario** | `1 ≤ d_min ≤ δ_nm` **y ningún trade** dentro de `[L,U]` | el que manda |
| Sensibilidad | variante por quote | se reporta, **no se mezcla** |

Se publica **la brecha entre los dos** en la superficie: es información, no ruido.

### Firewall, anclado en el artefacto

- corte = `session_bounds_utc_ns(20260701)[0]` = `1782856800000000000` ns (P-41)
- `holdout_included` **computado**, no escrito
- `outcomes_accessed=false`, `pnl_accessed=false`

### Qué cuenta como éxito

**Una tabla de población por celda, o variantes muertas por N insuficiente.**
No un edge. No un manifiesto. No una interpretación.

### Entregable, en el mismo commit

- JSON en `docs/research/` con procedencia completa (sha256 del parquet, blob del
  runner, HEAD, `firewall` computado, predicado, grilla)
- entrada de canal que cite ese path
- `PENDIENTE.md` si abre un `P-NN`
- `docs/CURRENT.md` actualizado (lo exige `tests/test_current_md.py`)

---

## 6. Qué bloquea a qué (el grafo que faltaba)

```
C1 censo ──> N por celda ──> manifiesto (auditor) ──> STOP de Nico ──> F4
   │
   └── NO bloquea: P-42, P-43, P-44, C4 inventarios, P-33(a)

W7 costos ──> simulador (cap. 4) ──> G2 (cap. 6)
   └── falta SOLO la comisión del broker (Nico). Spread ya medido.

P-42 ──> canoniza el conjunto de P-32 ──> NO bloquea C1
P-44b ──> bloquea H-Z2A MULTIACTIVO ──> NO bloquea el censo en 6E
```

**Lo que más se confundió esta semana**: P-41 sí bloqueaba el censo (por eso se
resolvió primero). P-42/43/44 **no**. Cerrarlas es higiene del conjunto de
indicadores, no avance de la hipótesis.

---

## 7. Trabajo en paralelo, ordenado por si compite

| ID | Qué | Compite con C1 |
| --- | --- | --- |
| **C1** | censo-superficie | — **gana siempre** |
| C2 | P-42: comparar umbral `aVolCellPOI2` vs oráculo | sí, por máquina → cede |
| C4 | inventarios L2 / GEX | no |
| C5 | P-33(a): resolver fuente por hash | no |
| — | `g2-a1` saneo | no |

---

## 8. Lo que decide Nico, nadie más

| | Qué |
| --- | --- |
| **STOP** | del manifiesto F4. Sin eso F4 no arranca. |
| **W7** | comisión del broker (lo único que falta del cap. 3) |
| **P-35 / P-37** | semántica de gates (`WARN`≠exacta; `COVERAGE_NEUTRAL`) |
| **P-44b** | normalizar umbrales vs pre-registrar por activo |
| **Kaggle V1** | borrar el dataset con ticks crudos |

---

## 9. Fuera de alcance, explícito

Holdout · P&L · F4 sin STOP · `features.py` (P-39: no se cambia el instrumento
durante la medición) · `fix/g2-a1-*` y `COVERAGE_NEUTRAL` · H-Z2A en ES/NQ/YM/GC
(P-44b) · reabrir la literatura de H-Z2A (v4 cerró eso).

---

**Aporte al referente:** deja de existir la ambigüedad entre higiene y ruta crítica.
Cualquiera puede mirar §6 y decir si lo que está por hacer mueve la fila 1 de §2 o no.
Y el próximo paso queda con su grilla, su predicado y su criterio de éxito escritos
**antes** de correrlo, que es la condición para que el resultado no se elija después.
