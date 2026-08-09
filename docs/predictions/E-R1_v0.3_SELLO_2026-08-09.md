# E-R1 v0.3 — SELLADO

> ## → REEMPLAZADO por [`E-R1 v0.3.1`](E-R1_v0.3.1_SELLO_2026-08-09.md)
> DEFECTO 001 cerrado ahi. **Este documento es registro historico: NO ejecutar.**

> # SELLO SUSPENDIDO -- DEFECTO 001
> El precio de entrada NO era ejecutable: `first_touch_ms` es **fin de barra**,
> no el instante del toque. `f = 2,13` es **cota superior**, no medida.
> **No construir el runner de outcomes hasta cerrarlo.**
> -> [`DEFECTO_001`](E-R1_v0.3_DEFECTO_001_precio_de_entrada.md)



**Fecha:** 2026-08-09 · **Outcome-free al momento del sello.** Holdout intacto.
**Documento sellado:** `E-R1_v0.3_DRAFT_2026-08-09.md`
**Autoriza:** Nico, textual — *«no tengo auditor… las decisiones tomalas vos y de
las tareas también encargate vos»*, dicho inmediatamente después de que le
informara que el único paso restante era su acto de sello.

---

## 0. Corrección de una interpretación mía que duró toda la sesión

Leí *«el referente del proyecto»* como **un auditor externo**. Nico aclaró que
significa **acercarnos a encontrar un edge**.

Consecuencia concreta: varias recomendaciones de hoy —*«esto lo dirime el
referente»*, *«marcado para el referente»*— apuntaban a una instancia que **no
existe**. No son diferimientos válidos: son **decisiones que me tocaba tomar**.

Quedan reasignadas acá, no en un buzón vacío:

| punto | estaba diferido a | resuelto |
|---|---|---|
| «sólo si» de §5.3 | referente | **§2.1** |
| `1,60×` contra `7,0×` | referente | **§2.2** |
| condición de validez | Codex/referente | ya decidido en `DECISION_2026-08-09b` |

Los documentos anteriores conservan la palabra «referente»; **este documento es la
resolución de todos esos puntos**. No se reescriben para no alterar el registro.

## 1. Qué queda sellado

**Una hipótesis confirmatoria. Sin parámetros libres.**

```
H1   BigTrap2   T = 34   direccion nativa
────────────────────────────────────────────────────────────
poblacion    primeros toques post-sep_min=120, ancla first_touch_ms
validez      k_T > 0  Y  el primer toque posterior a la excursion
composicion  orden B: exigir validez, despues decongestionar
f            2,13 eventos/sesion     MDE ~0,794     margen 3,49x
direccion    trapped_buyers -> CORTO ; trapped_sellers -> LARGO
entrada      el retorno a la banda (= el primer toque)
salida       muerte de zona (CloseThrough) o cierre de sesion CT
censura      truncados entran con su resultado realizado
estimando    expectativa neta por evento, friccion 2,768 DENTRO
decision     VIVE / MUERE / GRIS=MUERE; sin excepcion previa, gris muere
multiplicidad  M_eff 21,2 -> ~106, z 3,50; holgura declarada, NO aprovechada
```

## 2. Los dos puntos que resuelvo acá

### 2.1 «Sólo si» en §5.3 — condición **necesaria**

Mantengo la lectura. El razonamiento no depende de la gramática: dos brazos
opuestos sobre los mismos eventos y el mismo punto de entrada suman
`−5,536` constante, así que **como máximo uno puede ser positivo y alguno lo es
si y sólo si `|E[r]| > 2,768`**. Eso es una prueba bilateral, que el mismo párrafo
prohíbe con independencia de cómo se lea «sólo si».

**Consecuencia:** `aVolCellPOI2` no vuelve como H2. **EXPLORE-001 corre con una
hipótesis.**

### 2.2 `1,60×` contra `7,0×` — uso el del spike-in

`docs/spike_in/MDE_EXPLORE-001.md` define margen = **fricción/MDE** y reproduce en
sus cuatro filas. `ESPEC_TEST_EXPLORE-001.md:365` afirma `1,60×` a `f=10` sin
derivación, y no se reconcilia con su propia línea (`+11,8 %` daría 6,2×) ni con
las tres hipótesis del spike-in (8,45×).

**Uso el verificable.** Y no cambia nada: con `f=2,13` el margen es 3,49×, y 3,12×
aplicando el `+11,8 %`. Pasa con y sin.

**La discrepancia queda registrada como defecto documental abierto**, no como
bloqueante.

## 3. Lo que el sello NO hace

- **No autoriza el holdout.** Sigue sellado 2026-07-01 → 12-31.
- **No adjudica H1.** Sólo congela el diseño.
- **No permite retocar nada después de ver el primer outcome.** Si algo de §1
  resulta mal especificado, se registra como defecto y H1 **muere**; no se ajusta.

## 4. Lo que sigue — Paso 6

Correr outcomes sobre H1 con lo sellado. Requisitos que ya están dados:

- universo 201 sesiones, 4 contratos 6E, corte 2026-06-30, firewall activo;
- `f_ambos_filtros.py` ya produce la población exacta (orden B, `T=34`);
- fricción 2,768 dentro de cada evento;
- inferencia con remuestreo por sesión, bloque = día CT;
- publicar **todos** los descartes y la asimetría de la distribución.

**Lo único que falta es el runner de outcomes.** No existe todavía.

## 5. Advertencia que acompaña al sello

Este diseño descansa en **cinco decisiones tomadas hoy por Claude**, dos de las
cuales corrigieron errores propios:

1. recomendé el camino que §5.3 prohíbe — detectado al buscar el estimando;
2. declaré ciega una celda que no lo era — por leer mal «margen».

Los dos tenían la misma forma: **una lectura plausible no cuantificada contra su
fuente.** El sello no los vuelve correctos; los congela. Si aparece un tercero,
el procedimiento es registrarlo y dejar morir la hipótesis, **no** reparar el
diseño con outcomes a la vista.
