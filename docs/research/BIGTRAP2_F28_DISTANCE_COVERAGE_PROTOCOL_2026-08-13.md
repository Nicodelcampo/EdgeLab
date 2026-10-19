# F2.8 — Atlas de distancia, ancla, cobertura y residuales (2026-08-13)

Estado: `PREREGISTERED_NOT_RUN`
Spec: `specs/bigtrap2_f28_distance_coverage_v0.json`
Hereda: F2.7 v2, mismas 201 sesiones, mismo `r_i`, mismo firewall, mismo kernel.

## 0. Para qué existe

F2.8 **no** es un tribunal para refutar BigTrap2. F2.7 ya adjudicó una asimetría geométrica:

```text
Δ_reflection = +0.04815
IC95 = [0.03068, 0.06563]
201 sesiones / 15.947 zonas
8.280 real primero / 7.661 espejo primero
```

Eso demuestra que, con lifecycle reflejado y misma distancia al close, las ubicaciones no son intercambiables. No demuestra:

- que la zona atraiga;
- que el efecto viva lejos del ancla;
- que BigTrap2 sea el objeto, y no la barra creadora;
- que exista un canal zona vs no-zona;
- que haya o no otra familia explotable.

F2.8 existe para **localizar el mecanismo y mapear residuales**. Un cierre, una reapertura o un giro de producto son los tres resultados útiles.

## 1. Correcciones que quedan congeladas

1. La zona real **no está más cerca del close que el espejo**. Por construcción `d` es idéntica. La historia ingenua de mean-reversion-por-cercanía no explica F2.7.
2. El overlap espejo-con-otra-zona **no** es la fracción del rango intradía cubierta. Puede haber overlap geométrico sin ocupación simultánea.
3. Replicar en ES/NQ es valioso, pero **después** de saber qué objeto se está replicando. En 6E ya hay 201 sesiones formales.

## 2. Anclas externas, usadas con mesura

- **Osler (2000), FRBNY.** Los S/R publicados se contrastan contra miles de niveles arbitrarios. El hecho útil no fue “el precio toca el nivel”, sino que **interrumpe la tendencia** más que los controles. F2.8 copia esa lógica: controles emparejados + interrupción geométrica, sin P&L.
- **Principio de reflexión / primer pasaje.** El nulo de F2.7 ya es esa simetría. F2.8 pregunta si el residuo depende de `d`, de la selección de barra o de la densidad.
- **Mean-reversion local de microestructura.** En activos large-tick, el hueco entre el último/mid y un ancla puede revertir aunque el objeto “zona” sea inerte. Eso motiva los controles de barra creadora, no un modelo OU operativo.

## 3. Familias. No hay producto cartesiano

### A — Landscape de distancia

Publicar la curva completa de `Δ(d)`, no un único corte ganador.

Cortes descriptivos, declarados ahora y no después de ver F2.8:

```text
d ≤ 2        masa principal (71%)
3 ≤ d ≤ 5    hombro
d ≥ 6        cola (≈5%)
```

También se publican `d>3`, `d>5` y un resumen continuo. Estos cortes nacen de la distribución ya vista en F2.7; son enmienda explícita, no hipótesis original disfrazada.

Para cada corte: `n`, sesiones con soporte, resolución, `Δ`, SE HAC, IC95, MDE observado, real/espejo/doble censura.

Un IC que incluye cero en `d≥6` **no** cierra la cola si el estrato no tiene poder. Un IC positivo en la cola **abre** una familia chica y pura, no un atlas de 17 frames.

### B — Controles de barra creadora

Pregunta: ¿la carrera es de la zona o de la barra?

Dos controles, sin leer retornos:

1. **Geometría emparejada en barra no-trampa.** Misma sesión, mismo lado del close, mismo `d`, mismo ancho, barra sin zona BigTrap2.
2. **Placebo en la misma barra.** Conservar `d` y ancho, desplazar el intervalo a otra ubicación disjunta del mismo lado si existe.

Contraste: `Δ_BT2 − Δ_control` por sesión. Si BigTrap2 no gana al control, el objeto útil puede ser **clasificador de barras**, no imán de precio. Eso sigue siendo información nueva.

### C — Ocupación activa precio × tiempo

Unidad: cada tick del rango `[low, high]` de cada barra posterior a la creación.

Una zona está activa en `b` si nació antes y todavía no fue invalidada ni expirada.

Métricas:

- fracción del rango de la barra cubierta por la unión de zonas vivas;
- fracción de precios visitados cubiertos;
- zonas activas;
- distancia a la zona viva más cercana;
- tasa de zonas aisladas (sin overlap simultáneo);
- lo mismo contra 200 colocaciones aleatorias por sesión, semilla `20260813`.

Si la ocupación visitada mediana supera 80% y casi no hay zonas aisladas, el canal “zona vs no-zona” es estrecho. Eso no mata F2.7; cambia el producto a **features de densidad**.

### D — Atlas de residuales / oportunidades

Cada clase se declara ahora. No se inventan después.

| Clase | Si ocurre | Oportunidad |
|---|---|---|
| `FAR_ISOLATED` | `d≥6`, aislada, ocupación local baja | familia chica de alta pureza |
| `NEAR_BAR_TIMER` | el efecto vive en `d≤2` y el control de barra lo explica | BigTrap2 como selector de barras |
| `UNCOVERED_HOLE` | huecos persistentes que reciben primer pasaje más que huecos aleatorios | anti-zona / agujero de liquidez |
| `MIRROR_FIRST_POCKET` | algún corte declarado tiene IC95 enteramente negativo | fade / primer pasaje al lado opuesto |
| `INTERRUPTION_NOT_RACE` | interrumpe o rebota más que controles aunque `r_i≈0` | la zona es freno, no imán |
| `CROWDED_WALLPAPER` | ocupación alta y aislamiento bajo | dejar de tratar zonas como i.i.d. |

### E — Interrupción geométrica estilo Osler

Después del primer contacto, en las siguientes 5 barras, y **sin P&L**:

- ¿atraviesa el lado lejano?
- ¿revierte al menos un ancho hacia el close creador?
- ¿se queda, sin través ni rebote?

Esto puede revelar un producto distinto al de la carrera: no “quién llega primero”, sino “el nivel frena”.

## 4. Etiquetas. Pueden convivir varias

```text
OPEN_FAR_ZONE_FAMILY
OPEN_BAR_CLASSIFIER
OPEN_HOLE_FAMILY
OPEN_FADE_MIRROR
OPEN_INTERRUPTION_FAMILY
OPEN_DENSITY_FEATURES
CLOSE_ZONE_ATTRACTION
CONTINUE_AMBIGUOUS
```

Reglas exactas en la spec. No hay voto informal.

Interpretación práctica:

- `OPEN_FAR_ZONE_FAMILY` → una campaña chica sobre la cola, no Z2.
- `OPEN_BAR_CLASSIFIER` → el objeto pasa a ser la barra creadora; BigTrap2 queda como detector de contexto.
- `OPEN_HOLE_FAMILY` → el residual descubierto son los huecos, no las zonas.
- `OPEN_FADE_MIRROR` → hay un bolsillo donde el espejo gana; eso es una oportunidad, no un fracaso.
- `OPEN_INTERRUPTION_FAMILY` → endpoint sucesor = interrupción/rebote, no carrera binaria.
- `CLOSE_ZONE_ATTRACTION` → F2.7 sigue siendo un hecho geométrico; se deja de vender “la zona atrae”.

## 5. Qué queda cerrado

Kernel, F1.1, holdout, tick:25, P&L, dirección, stops/targets, barrido de parámetros, Z2, upload de ticks a Kaggle, y recortes post-resultado presentados como primarios.

PIT, Kaplan–Meier y Cox **esperan**. Si se reabren, tendrán que nacer condicionales a `d`, densidad y clase residual. Un hazard bruto mediría la masa `d≤2`, no la zona.

## 6. Orden de ejecución

1. Reconstruir el universo F2.7 y verificar que se reproducen los totales globales.
2. A — curva de distancia.
3. C — ocupación, porque informa todos los contrastes.
4. B — controles de barra.
5. E — interrupción/rebote.
6. D — etiquetar residuales.
7. Emitir etiquetas. No abrir Z2 desde este documento.

## 7. Instrucción mínima para el implementador

> Implementá F2.8 de forma aditiva sobre la rama `research/bigtrap2-local-displacement-null`. No toques el kernel. Reusá `r_i` y el lifecycle reflejado de F2.7. Publicá todas las familias, incluidos nulos y abstenciones. No elijas el corte más lindo. No leas holdout ni P&L. Si una etiqueta `OPEN_*` se enciende, escribí una spec de una sola familia; no un atlas.
