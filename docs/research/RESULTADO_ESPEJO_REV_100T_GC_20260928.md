# ESPEJO-REV-100T — GC (Lucid) — resultado (2026-09-28)

Kaggle `edgelab-espejo-rev100t-gc-20260928`. Configuración de Nico: W ≥ 100 t, 30 velas de 100t. **Febrero 2026 excluido**
(el mes que Nico miró). 150 sesiones elegibles, 115 con eventos; 2.240 cruces, 2.103 trades de reversión (el tope no se
alcanzó: muestra completa). W mediano 137 t. t crítico 3,35. **1 celda sobrevive.**

## A) Cruce hacia B — sin efecto
Todas las celdas en el azar: exceso −0,026 a +0,006 (todos) y −0,033 a +0,030 («no lista» + ineficiente), IC que cruzan 0.
Las 12 capturas de febrero eran una racha: fuera de febrero, el cruce no se aparta del paseo sin memoria.

## B) TP/SL de reversión — primer R bruto positivo que sobrevive
| Filtro | TP / SL | n | R bruto | Exceso sobre nulo (IC 90 %) | t |
|---|---|---|---|---|---|
| **todos** | **2 W / 1 W** | 2.103 | **+0,026 W** (≈ +3,6 t) | **+0,106 [+0,068; +0,146]** | **4,36 (sobrevive)** |
| todos | 1,5 W / 1 W | 2.103 | +0,011 | +0,053 [+0,017; +0,086] | 2,54 |
| no lista + ineficiente | 2 W / 1 W | 391 | +0,048 | +0,162 [+0,068; +0,262] | 2,82 |
| no lista + ineficiente | 1,5 W / 1 W | 391 | +0,052 | +0,102 | 1,86 |
- Entrada: límite en A a favor de B, sólo si la vela de completación pasó A ≥ 1 tick (sin eso no hay llenado).
- Las celdas con TP amplio (1,5–2 W) y SL 1 W son las positivas; con TP chicos el R es negativo.
- **Economía, a verificar:** +3,6 t brutos por trade en GC (tick 0,1 = US$10) contra una fricción GC propia que hay que
  estimar (no se transporta la de ES). Plausiblemente cubre spread + comisión, no el deslizamiento de un límite que se
  llena sólo cuando el precio atraviesa (selección adversa ya parcialmente modelada con el requisito de 1 tick).

## Qué habilita
**Candidato para la confirmación única abr–jun 2026 (Lucid GC):** reversión TP 2 W / SL 1 W, W ≥ 100 t / 30 velas; como
variante, con «no lista» + ineficiente. Antes: estimar la fricción GC y el control empírico del nulo (misma entrada en
momentos al azar), pendiente también para NQ/YM.
