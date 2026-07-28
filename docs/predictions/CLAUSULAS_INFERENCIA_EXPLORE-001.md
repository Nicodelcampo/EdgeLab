# Cláusulas de inferencia para el pre-registro de EXPLORE-001

**Redactadas 2026-07-27**, después de medir que la dependencia entre días dura
**13–18 días** (Politis–White sobre la serie diaria real) y que el bloque fijo
de 1 día subestima la incertidumbre **a más del doble**.

Estas cláusulas se copian tal cual al pre-registro. Se congelan **antes** de
correr el estudio y **antes** de mirar cualquier zona real.

---

## §1 · MCPT — la permutación es POR DÍA, ESTRATIFICADA, no entre días

### El problema

El criterio primario incluye MCPT por bloques de día. Pero permutar días
individuales asume que los días son intercambiables — exactamente la
independencia que `b_opt = 13–18` acaba de refutar. Si el intervalo se corrigió
y el p-valor no, la sub-cobertura vuelve a entrar por la otra puerta.

La solución obvia sería permutar **bloques** de ~`b_opt` días. Funciona, pero
tiene un costo grande: con 188 días y bloques de 15, quedan ~12 unidades
permutables. Un test de permutación con 12 unidades tiene una resolución mínima
de p-valor de 1/12 ≈ 0,083 — no puede producir evidencia al 5 % ni aunque el
efecto sea enorme.

### El esquema adoptado: permutación ESTRATIFICADA POR DÍA

**Dentro de cada día**, se reasigna al azar cuáles de los instantes candidatos
de ese día son "toque de zona", manteniendo fijo el número de toques del día.
Los instantes candidatos son **las anclas placebo del atlas para ese mismo
día**, ya calculadas, con la misma seed y la misma regla de separación mínima.

- El estadístico se recalcula sobre cada reasignación.
- `p = fracción de permutaciones con estadístico ≥ observado`.
- Réplicas: 10.000. Seed declarada.

### Por qué esto resuelve el problema, y no lo esquiva

Cada permutación **preserva la identidad del día y su tasa base**. La estructura
de dependencia entre días es **idéntica en todas las permutaciones**, incluida
la observada: por lo tanto no puede inflar la significancia. El agrupamiento de
volatilidad de 13–18 días queda condicionado, no supuesto ausente.

Dicho de otro modo: la pregunta pasa a ser *"dentro de este día, ¿los toques de
zona le ganan a instantes al azar del mismo día?"*. Un día volátil aporta tanto
al numerador como al denominador de su propia comparación.

### Lo que este test NO puede detectar — declarado

Un efecto puramente **entre días** — por ejemplo "los días con muchas zonas son
días distintos". La permutación estratificada lo condiciona y por lo tanto lo
borra.

Se acepta a propósito: la hipótesis de EXPLORE-001 es que **el toque de una zona
marca un momento**, no que marque un día. Si algún día interesa la versión entre
días, es una hipótesis distinta, con su propio turno y su propio esquema
(ahí sí, permutación por bloques de ~`b_opt` con la pérdida de resolución
asumida y declarada).

### El bootstrap sigue, con otro trabajo

La permutación da el **p-valor** bajo la nula aguda. El **intervalo** del tamaño
de efecto lo sigue dando el bootstrap estacionario con `b_opt`. Son dos
preguntas distintas y cada método responde la suya; ninguno reemplaza al otro.

### Control obligatorio antes de creerle al p-valor

Si el número de toques por día es chico (1–3), las reasignaciones distintas
dentro de un día son pocas y el test pierde potencia. **Se reporta la
distribución de toques por día junto con el p-valor.** Si la mediana es < 3, el
p-valor se declara de baja resolución y no decide solo.

---

## §2 · Congelamiento: se congela el PROCEDIMIENTO, no el número

> **Cláusula (copiar textual al pre-registro).**
>
> El método de inferencia de este estudio queda congelado en esta
> pre-registración: **bootstrap estacionario de Politis–Romano con largo de
> bloque estimado por Politis–White**, según
> `edgelab/stats/bootstrap_estacionario.py`.
>
> Lo que se congela es el **procedimiento**, no el valor de `b`. El largo de
> bloque se estima **en tiempo de corrida**, con Politis–White, sobre la **serie
> diaria de estadísticos PLACEBO de la geometría (H, P, N) elegida** — la que el
> atlas guarda en `por_dia_tasas` de su salida.
>
> **Prohibido estimar `b` sobre resultados de zonas reales**, sobre la serie de
> estadísticos del estudio, o sobre cualquier cosa posterior a mirar el
> resultado. El `b` se calcula sobre el nulo, que es información disponible
> antes de correr el estudio y que no depende de su desenlace.
>
> **Prohibido elegir entre `metodo="estacionario"` y `metodo="fijo"` después de
> ver los intervalos.** Si el estacionario no estuviera adoptado (sintético en
> verde + no-regresión) al momento de congelar, el estudio corre con el bloque
> fijo actual y el estacionario espera al siguiente. Elegir el método viendo el
> intervalo es búsqueda de especificación con otro nombre.
>
> Se reportan **los dos** intervalos —fijo y estacionario— en el resultado, con
> el estacionario como el que decide. Reportar ambos no es opcional: hace
> visible cuánto de la conclusión depende del método.

---

## §3 · Universo — el detalle que va declarado

- **188 bloques de día**, no 191. Los tres días que están en alcance y no
  aportan anclas son **2025-12-12, 2026-03-13 y 2026-06-12**: los tres viernes
  de roll trimestral, con 6.791 / 13.216 / 9.812 ticks. Con `sep_min_minutos`
  igual al horizonte máximo, no entra en ellos ninguna ancla que no comparta
  futuro con otra. No es exclusión por defecto de dato: es la regla de
  separación mínima haciendo su trabajo, y se declara para que el N no parezca
  arbitrario.
- **Alcance por tipo de día**: `COMPLETO` + `CIERRE_SEMANAL`. Sin domingos
  (`APERTURA_SEMANAL`). **El estudio y su nulo usan exactamente los mismos
  tipos.** Si aparecen zonas en días fuera del alcance, el arnés **falla
  ruidoso** en vez de compararlas contra un nulo que no las cubre.
- **Estratos**: exactamente los del atlas — 4 franjas horarias × 3 terciles de
  volatilidad rezagada = **12**. No 6, no otros.
- **N efectivo para potencia**: `188 / b_opt`. Con `b_opt` de 13–18, eso es
  **entre 10 y 14 unidades verdaderamente independientes**. Ese es el número que
  gobierna lo que el estudio puede y no puede detectar, y va escrito en el
  pre-registro antes de correrlo.
