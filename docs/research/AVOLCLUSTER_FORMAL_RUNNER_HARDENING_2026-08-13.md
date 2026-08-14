# Hardening del runner formal aVol (2026-08-13)

Estado: `RUNNER_V2_1_TESTED_SYNTHETIC`
Archivo: `diag/tasa_senales/avolcluster_formal.py` (reemplaza al v1, mismo path).
Tests: `tests/research/test_avolcluster_formal.py` (sintéticos, sin datos reales).

## Por qué se endureció antes de correr

El v1 del runner repetía errores que la saga F2.7/F2.8 ya pagó. Auditar el
runner **antes** de que lleguen los datos es la lección de F2.8 (donde los
defectos se descubrieron después de publicar el informe).

| Defecto v1 | Consecuencia | Fix v2 |
|---|---|---|
| Proporción global cruda, sin sesiones ni IC | No podía adjudicar nada | Media por sesión + HAC Bartlett (lag = ceil(sqrt(n))), IC95 |
| Sin control de barra | Un Δ > 0 sería ambiguo (lección F2.8: la barra explica casi todo) | Control en barra no-creadora, misma sesión, mismo `(d, w, lado)`, contraste **pareado** |
| `round()` de Python (banker's) en price→tick | Familia de bug documentada en F2.7 (límites .5) | `floor(p/tick + 0.5)` |
| Match `bar_close_time` ↔ M1 asumido | Si NT8 exporta bar-start, toda la carrera corre una barra corrida | Gate fail-closed: offsets {0, −1m}, match ≥ 95% y adyacencia ≥ 80%, si no `ABSTAIN_ALIGNMENT` |
| Ceros fuera del denominador | Infla p | `r_i = 0` (empate, doble censura) entra a la media por sesión; categorías separadas |
| Formato de export rígido (asumía header) | El export nativo de NT8 no trae header | Acepta `yyyyMMdd HHmmss;O;H;L;C;V` y CSV con header |
| Sesiones por timezone asumida | Depende del reloj del chart | Split por gaps > 30 min (pausa diaria CME), agnóstico de timezone |

## v2.1 — defecto encontrado auditando el primer output real

La primera corrida real (6E 09-26, 133 zonas, 48 sesiones) salió con el gate
de ties en FAIL y con el control en **−0,40, IC que excluye cero**. Un control
sano bajo el nulo debe ser ~0; esa asimetría era la alarma.

Causa raíz (defecto de construcción de `pick_control_bar` v2, no del mercado):
`search_pad=3` admitía controles **dentro del bloque formador de 10 barras**.
La creadora es el cierre del bloque; una barra a 4–10 de distancia está dentro
del mismo bloque, antes del desplazamiento que define el lado. El espejo del
control caía sobre el precio actual → `mirror_first` sistemático. El contraste
+0,55 medía "zona vs benchmark roto", no "zona vs azar".

Fix v2.1:
- `CONTROL_PAD_BARS = 12` (bloque de 10 + margen).
- Nueva familia `control_random` (misma sesión, elegida uniforme con semilla
  determinística) como diagnóstico: si ambos controles quedan ~0, el defecto
  está cerrado; si `nearest` y `random` difieren mucho, queda selección.
- Split descriptivo `by_side` (above/below) del brazo zona.
- `control_diagnostics`: distancia en barras del control a la creadora.

No es tuning de outcome: el brazo zona, los gates y las etiquetas no cambian.

## Etiquetas

```text
AVOL_ZONE_EDGE      carrera CI>0 y contraste vs control CI>0 (la zona suma sobre la barra)
AVOL_BAR_CONTEXT    carrera CI>0 pero contraste compatible con cero (es la barra, como BigTrap2)
AVOL_NO_EDGE        carrera compatible con cero
AVOL_FADE_POCKET    carrera CI<0 (corte declarado, no pesca)
AVOL_UNDERPOWERED   gates no cumplidos (resolución, sesiones, ties, match de controles)
ABSTAIN_ALIGNMENT   el log NT8 y el M1 no se alinean de forma inequívoca
```

Gates: ≥30 sesiones con zonas, resolución ≥ 0.30, ties ≤ 0.10 (M1 sin desempate
por ticks), match de controles ≥ 0.40. Holdout, P&L y outcomes fuera.

## Qué verifican los tests sintéticos

1. Parseo de ambos formatos M1 y del CSV de zonas.
2. Alineación exacta y geometría espejo disjunta (`m = 2·anchor − zona`).
3. Split de sesiones por gap.
4. Mundo nulo → `AVOL_NO_EDGE` con IC que cruza cero.
5. Señal plantada (la zona siempre toca primero) → `AVOL_ZONE_EDGE`.
6. Log corrido 7 horas → `ABSTAIN_ALIGNMENT`.
7. (v2.1) Pad del control fuera del bloque formador; control aleatorio determinístico.

## Qué NO hace v2.1 (declarado)

- No reusa `hac_bartlett_ic` de F2.7 por import: el runner es stdlib-only para
  correr también en sandboxes sin el repo. La fórmula Bartlett es la misma y
  está cubierta por los tests.
- No resuelve empates intra-barra (M1 puro; queda como `tie_same_bar` y está
  gateado). Si `frac_tie` se acerca al límite, el siguiente paso es tick data,
  no relajar el gate.
- No usa `FIRST_TOUCH`/`ZONE_INVALIDATED` del CSV: la carrera es primer pasaje
  puro en ambos brazos, simétrica por construcción.
