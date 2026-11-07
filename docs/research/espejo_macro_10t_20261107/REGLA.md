# Candidatos a espejo en velas de 10 ticks

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `ESPEJO` / `edgelab.research.espejo_macro_10t`
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`

## Qué es y qué no es

Es un detector de forma para que una persona diga, candidato por candidato, si lo que se ve es un espejo. No es una orden, no tiene P&L y no abre el holdout. El juicio humano es la medida; los umbrales de abajo quedan congelados antes de leer ese juicio.

## Regla congelada

Se observa el cierre de velas de 10 ticks, armadas dentro de una sesión CME (el resto que no completa la vela se tira; la pausa 16:00–17:00 CT no entra).

Un candidato exige las dos cosas a la vez:

1. Un impulso ancho. En NQ el piso sale de la fricción canónica, escenario severo (spread medido + comisión máxima de las firmas que admiten algoritmos + 3 ticks de slippage por lado): unos 10,2 ticks por viaje. El gráfico corta al 50 %, así que sólo la mitad del ancho sigue disponible hasta A. Esa mitad tiene que valer 40 viajes severos. El ancho mínimo queda en el doble, del orden de 200 puntos, y la ida tiene que durar las velas que hagan falta para no ser un latigazo (cerca de 10 ticks de avance por vela). Sin un retroceso marcado: un cierre que devuelve más del 20 % de lo que el tramo ya había recorrido, y después el precio hace un extremo nuevo.
2. Una vuelta, en la dirección contraria, igual de limpia y con el mismo ritmo, cuyo primer cierre deshace el 50 % del ancho del impulso.

Ahí se corta. No se mira si el precio llega a A. Las velas que se muestran terminan en ese cierre.

El retroceso se mide en el cierre, no en la mecha: la mecha de una vela de 10 ticks es el propio recorrido de esos ticks y marcaría un serrucho donde el cierre va derecho.

## De dónde salen los gráficos

El dataset de Kaggle `nicolasbuttaro/edgelab-ticks-nq-preholdout` no tiene archivos posteriores a junio de 2026 (no existe `NQ_12-26`; `NQ_09-26` termina el 30 de junio). Esos parquets ya estaban en el cache local, así que no se volvió a bajar nada y no se tocó el holdout sellado.

La ventana es el último trimestre anterior a esa frontera: sesiones CME del 2026-04-01 al 2026-06-30. Si un día cae en dos contratos, se usa el de más trades. El conteo queda en `recibo.json`, al lado de este archivo. El paquete con precios vive sólo en `viewer/nt8_bridge/bundles/` y no se versiona.

## Cómo podría refutarse esta definición

Si quien clasifica marca como espejo, de forma sistemática, caminos que esta regla tira (un serrucho) o rechaza los que deja pasar (una montaña de un solo trazo), la regla de forma está mal y hay que reescribirla antes de cualquier barrido. Ese desacuerdo no se usa para mover el 20 %, el 50 % o los 80 ticks mirando el mismo gráfico.

## Justificación económica

Todavía no hay una. Un espejo macro, si la vuelta completa el tramo, recorre decenas de puntos de NQ contra una fricción de unos pocos ticks. Eso sólo se mide después de que la forma quede aceptada y con una orden pre-registrada. Esta página no es esa medida.
