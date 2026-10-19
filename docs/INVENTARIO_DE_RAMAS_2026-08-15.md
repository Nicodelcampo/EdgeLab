# Inventario de ramas — 2026-08-15

Qué rama es cuál, cuál está viva, cuál ya está contenida y cuál espera una decisión.
Se escribió porque `tools/estado.py` reporta 14 ramas remotas «con trabajo que ésta no
tiene» sin distinguir entre *superada* (su contenido ya está aplicado) y *pendiente*
(trae algo que no está en ningún lado). Las dos se ven igual en la lista y no lo son.

Medido con `git cherry HEAD origin/<rama>`: `-` = commit patch-equivalente, ya aplicado;
`+` = commit que no está.

Referencia: `research/bigtrap2-local-displacement-null` @ `4b9611a`.

---

## 1. Viva

| Rama | Estado |
| --- | --- |
| `research/bigtrap2-local-displacement-null` | **Acá se trabaja.** Contiene `foundation`, `soporte-balance-curve` y todo el hilo F2.7–F2.10 + Kaggle/holdout. |

## 2. Contenidas (son ancestros — no hay nada que mergear)

| Rama | Relación |
| --- | --- |
| `foundation/f0b-compatibility-probe` | Ancestro. Se mantiene por **fast-forward**, no se le commitea directo. |
| `research/bigtrap2-soporte-balance-curve` | Ancestro. |

## 3. Superadas (100 % patch-equivalente — mergearlas duplicaría historia)

| Rama | Commits | Nuevos |
| --- | --- | --- |
| `research/bigtrap2-distance-matched-null` | 14 | **0** |
| `docs/estado-real-2026-08-10` | 1 | **0** |
| `docs/h-sweep-1-ym-prerange` | 1 | **0** |

`research/bigtrap2-distance-matched-null` es la versión **pre-rebase** de la línea que
hoy vive en la rama activa; P-04 se cerró justamente rebasando sobre
`audit/p0-bigtrap2-drift@1916ffa`. Sus 14 commits están todos aplicados. **Mergearla
sería un error**: duplicaría la historia que el rebase acababa de limpiar. Corresponde
archivarla o borrarla del remoto, no integrarla. Es también la rama del **PR #11**, que
quedó sin editar por falta de `gh` autenticado y hoy apunta a una línea cerrada.

## 4. Bloqueadas por decisión explícita de Nico — **NO mergear** (P-10)

Cambian semántica de validación. La regla permanente de `CLAUDE.md` las reserva a Nico,
y P-10 pide una decisión merge/no-merge **por rama, registrada en el board**.

| Rama | Nuevos | Qué cambia |
| --- | --- | --- |
| `fix/g2-a1-calibration-hardening` | 12 | Reescribe `g2_decision.py`/`promotion.py`: calendario de sesiones elegibles obligatorio, `MIN_DSR_SESSIONS`, DSR V1/V2. |
| `fix/g2-a1-statistical-semantics` | 6 | Idem, misma línea. |
| `research/ym-prerange-session-window` | 6 | `minute_window_matrices` con calendario explícito obligatorio y cruce de medianoche. |
| `docs/lux-imb-source-correction` | 5 | Retracta la premisa de H-COND-1 («el render borra zonas mitigadas»). Mientras no se mergee, la razón vieja del bloqueo **sigue escrita y es falsa**. |

## 5. Con trabajo propio sin integrar — requieren una decisión, ninguna es urgente

| Rama | Nuevos | Qué trae |
| --- | --- | --- |
| `research/zamr1-zone-atlas` | 27 | Z0/Z1 (builder Z1, reloj CME, provenance Kaggle fail-closed). Su propio `ZAMR1_NEXT_IS_F28.md` **redirige el trabajo siguiente a la rama viva**, así que la línea sucesora ya está integrada; lo que queda sin integrar es el andamiaje Z1. |
| `prep/indicator-onboarding-registry` | 6 | Registry de onboarding de indicadores. F9 está PAUSADA, así que no corre prisa. |
| `research/bigtrap2-multiframe-ml` | 5 | Incluye los 2 de `fix/bigtrap2-v252-tick-export`. |
| `fix/bigtrap2-v252-tick-export` | 2 | Contenida en la anterior. |
| `docs/h-cond-1-lux-imb` | 2 | Docs de la familia LUX-IMB. |
| `docs/post-merge-sync-2026-08-10` | 2 | Docs de sync. |

## 6. Divergencias a propósito (no las marca `estado.py` como problema)

`main`, `backup/foundation-f0b-local`, `preserve/f0b-local-divergente-2026-08-04`.

---

## Por qué importa

El 2026-08-05 dos máquinas midieron cosas distintas creyendo mirar lo mismo, porque 70
commits vivían en una rama que `CLAUDE.md` no mencionaba
(`docs/AVISO_DIVERGENCIA_DE_RAMAS_2026-08-06.md`). El 2026-08-15 el archivo volvía a
declarar `foundation/f0b-compatibility-probe` como rama de trabajo mientras el trabajo
real vivía cinco días adelante en otra rama, y seguía afirmando viva una hipótesis que
`F2.8` había cerrado dos días antes.

La lección no es «actualizar el doc más seguido». Es que **una lista de ramas sin
clasificar no es información**: `estado.py` marcaba `MAL` tanto a una rama 100 %
contenida como a una que cambia la semántica de un gate, y las dos requieren acciones
opuestas. Este inventario es el que distingue.

Cuando cambie: regenerar con `git cherry HEAD origin/<rama>` y actualizar la fecha.
