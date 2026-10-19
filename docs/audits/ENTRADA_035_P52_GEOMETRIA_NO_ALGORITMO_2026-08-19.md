# Entrada 035 — Opus → Aud · P-52: de NT8 se importa la geometría, no el algoritmo

- **Fecha:** 2026-08-19 · **Dirección:** Opus 5 → Auditor
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · sin corridas nuevas

---

## 1. De dónde sale

Nico preguntó si el proyecto se complicó de más replicando indicadores de NT8 en vez
de construirlos nativos. **La respuesta es sí, en parte**, y pidió asentarla. Queda
como **P-52** en `PENDIENTE.md`.

## 2. La regla

> El indicador de NT8 es un **generador de hipótesis**, no un **instrumento de
> medición**. De él se importa **dónde está la zona** — `lower_tick`, `upper_tick`,
> `creado_ns`. El resto se define nativo, con su propia definición falsable.

**Test para aplicarla:** ¿existiría esta pieza si el indicador no tuviera que
dibujarse en tiempo real sobre una plataforma? Si no, es un accidente de plataforma y
no se replica.

## 3. La evidencia, medida

**Lo que la paridad compró:** que el objeto que Nico señala sea el que la máquina
mide. La paridad de BigTrap2 (3.628/3.638 EXACT) no encontró ningún edge, pero **hizo
que su muerte sirviera** — matar una hipótesis vale sólo si mataste la correcta.

**Lo que costó**, con dos casos medidos:

- **`sesionNoConfiable`** no reseteaba porque el bloque de frontera quedó detrás de un
  `return` (fix `f77a3be`): semanas de silencio de TRAPs por un orden de sentencias en
  otro programa.
- **El P² de `VolTicksDef`** aproxima un percentil sin guardar la muestra, **porque
  NT8 no puede re-ordenar 200.000 barras por tick**. Nosotros tenemos la serie en
  memoria. Cuantil exacto = más correcto y **sin paridad**; replicar P² = paridad y
  **copiar un error de aproximación que existe por una restricción que no tenemos**.
  Eso no es medir el mercado, es medir NinjaTrader.

## 4. El patrón ya estaba bien, sin ser política

El censo **no llama al runner del portador**: trae su propia distancia en ticks
enteros por `zone_id`, y define corredor / `d_min` / separación / episodio
nativamente. Del indicador usa exactamente los tres números. Se llegó ahí empujado por
la orden 019; esta entrada lo vuelve política.

Dato de hoy que lo respalda: mi enumeración independiente de corredores dio **142.023**
y el artefacto declara `n_A1 = 142.023`. La geometría nativa reproduce el conteo del
censo exactamente — el puente NT8 no interviene.

## 5. Consecuencia: deuda aparcada, no cerrada

Paridad se paga sólo donde el indicador **carga una hipótesis viva** y la evidencia es
**visual**. Hoy: `aVolClusterPOI`. `HFTZones2` cuando P-48 lo abra.

Quedan **aparcadas** (declaradas, no perseguidas, ninguna hipótesis depende de ellas):
**P-42** (`aVolCellPOI2` sin paridad) · **P-43** (residual GC) · **P-44** (dos
catálogos) · **P-32** (conjunto de indicadores).

**Aparcar no es cerrar.** Siguen en el board con su estado real, y reactivar cualquiera
exige una hipótesis que la necesite, escrita antes.

**Sacar ítems de la cola es decisión de Nico**, no mía: por eso dicen «aparcada» y no
«cerrada». La regla la asiento; el aparcamiento espera su OK.

## 6. El límite honesto

Es fácil decirlo hoy. Hace dos meses la paridad era la única forma de descartar
«mediste otra cosa» como explicación de un resultado negativo. El error no fue empezar
por ahí — fue **no parar cuando quedó claro que la hipótesis se define sobre geometría
de precio y no sobre el interior del indicador**.

Corolario: **la paridad tiene fecha de vencimiento por hipótesis.** Cumple su función
el día que la hipótesis queda escrita como afirmación medible sobre el precio. Desde
ahí, perseguirla es deuda técnica disfrazada de rigor.

## 7. Lo que NO hice

No cerré ningún P-NN. No relajé el contrato de paridad — sigue vigente para lo que sí
se mide. No toqué `aVolClusterPOI`. No porté `VolTicksDef` ni el LuxAlgo (Nico dijo
«mejor no» al segundo). No corrí nada.

**Aporte al referente:** deja de gastarse esfuerzo en replicar accidentes de una
plataforma y se concentra en definir nativamente los objetos que las hipótesis miden.
La distancia al edge no la acorta la paridad de un sexto indicador; la acorta tener el
estimand escrito sobre el precio.
