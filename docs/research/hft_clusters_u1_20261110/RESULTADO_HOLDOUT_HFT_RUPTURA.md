# Resultado — apertura exploratoria del holdout de HFT_RUPTURA (2026-11-11)

Estado: RESULTADO (una sola vez, análisis congelado `tools/op2_holdout.py analizar`). Pre-registro: `PREREGISTRO_HOLDOUT_HFT_RUPTURA.md`
(commit del acta registrado en el kernel). Kernel `nicolasbuttaro/hft-clusters-info-op2-holdout-20261110`, ticks sellados de NQ, ES
y YM desde 2026-10-01 (YM hasta 23-oct con operaciones; sesiones excluidas de `edgelab/holdout.py`). La familia HFT_RUPTURA ya no
tiene holdout: lo que sigue es forward.

Nota de implementación: la primera ejecución del análisis falló al importar `scipy` (no está en el entorno) ANTES de calcular nada;
se reemplazó por la forma cerrada de la cola chi² de Fisher (verificada: un p da el mismo p; dos de 0,05 dan 0,0175). La regla, los
datos y el estadístico no cambiaron.

## H-YM (pedido de Nico): OP-2 en YM, stop X, objetivo X, 900 s, R neto
| tramo | operaciones | sesiones | R neto medio | R bruto medio | total | p |
|---|---|---|---|---|---|---|
| IS (DESC) | 150 | 88 | +0,035 | +0,114 | +5,2 R | 0,29 |
| OOS (réplica) | 112 | 65 | +0,025 | +0,104 | +2,8 R | 0,38 |
| **Holdout** | **12** | 9 | **+0,055** | +0,134 | +0,7 R | 0,41 |

Fisher (0,286; 0,381; 0,408) = **0,40 → NO_CONCLUYENTE**. Positivo en los tres tramos, del orden de la fricción, sin potencia
(el holdout dio 12 operaciones, no las 18 estimadas; MDE ≈ 0,6 R). Un nulo así no la mata ni la confirma. Curva: `OP2_YM_CURVA.svg`.

## H1: «el cluster grande no defiende» (real − control de `rompe`, NQ + YM)
Holdout: **+0,269 por sesión, 5/5 sub-bloques positivos, p 0,030** (28 sesiones; NQ +0,267, YM +0,275). Fisher con desarrollo
(0,088; 0,052; 0,030) = **0,0068**, nominada por BH q 0,10 sobre las dos → **A_FAVOR_COMBINADO**. El efecto del holdout es
≈ 3 veces el de desarrollo (+0,09): con 28 sesiones el IC es ancho; se toma la dirección, no el tamaño.

## Lectura
- Lo que se sostiene es el **contraste**: donde hubo un cluster HFT grande el precio atraviesa más que en un nivel cualquiera.
  No es un P&L: la ruptura absoluta a mercado no paga en NQ/ES/RTY (`RESULTADO_OP2_DESARROLLO.md`). Su uso operable directo es
  como **veto** de estrategias de reversión (OP-3) y como condición de continuación en YM, en forward.
- Es exploratorio (modo 2026-11-08), no una confirmación del embudo: no promueve nada a REAL.

## Siguiente
1. OP-3: veto «nivel con cluster grande» sobre fades existentes, medido en bruto (K2), en datos no usados por esas familias.
2. YM OP-2 en papel con regla congelada y e-proceso (`edgelab/funnel/secuencial.py`).

Aporte al referente: la primera cuerda de los clusters HFT sobrevive a datos nunca mirados; deja de ser una pista de desarrollo y
pasa a ser un filtro con evidencia combinada para no entrar contra niveles que no van a defender.
