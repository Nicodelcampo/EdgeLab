# GC L2 P1 — controles mecánicos históricos y repetición

Fijado antes de contar P1. Es continuación target-free de P0 (commit 899c1c4),
no confirmación independiente ni evaluación de una estrategia. Datos ya vistos en P0:
GC NT8, Kaggle privado v2, archivos 20260531/20260615. Nada de holdout, retornos,
MAE/MFE, fills ni costos. Mantener apply_event y parámetros P0 intactos.

## Una comparación, sin búsqueda de variantes

Para cada descenso elegible, seguir recuperación >=70 % del tamaño anterior en
<=5 s, con la misma censura por nuevo descenso/desaparición/reset/invalidación.
Positivos: descenso con prints previos acreditados por P0, consumidos una sola vez.
Controles: descenso sin NINGÚN print al mismo precio en los 2 s previos disponible
hasta su UPDATE. Un descenso con prints pero sin crédito restante no es control.

Emparejar 1:1 sin reemplazo, sólo controles que comenzaron antes del positivo,
misma sesión/archivo, lado y estrato. Usar el más reciente de los 10 min pasados;
no mirar desenlace ni exigir que el control haya terminado al emparejarlo.

Estrato fijo con información disponible en el descenso:
- profundidad previa del precio: 1 / 2–3 / 4–6 / 7–10;
- tamaño visible previo y magnitud absoluta de caída: floor(log2(max(1,tamaño)));
- número de LAST (cualquier precio) en 2 s previos: 0 / 1–3 / 4–15 / 16–63 / >=64.
No usar hora CME (reloj absoluto no certificado) ni parámetros adaptados a sesión.

Publicar soporte común y pares por archivo; recuperación observada por todos los
pares (no sólo casos completos), censuras por separado. Sin p-values/IC iid:
episodios dependientes, 2 ejemplos no representativos, matching grueso y retrospectivo.
Esto no identifica causalidad ni efectividad del nivel; compara una heurística mecánica.
Si soporte común <10 % de positivos, declarar comparación insuficiente, no aflojar
los estratos. Cualquier otra variante necesitará otro plan, no se prueba aquí.

## Repetición observable

Sobre los episodios P0 ya completados, contar cuántos tienen una recuperación previa
al mismo (lado, precio) en los 60 s anteriores. Sólo historial disponible al emitir;
no llamar iceberg/absorción y no convertirlo en señal de entrada.

## QA adicional

Reproducción exacta de conteos/eventos P0 por archivo; balance de episodios P1 y
parejas sin reutilización; igualdad de estratos y control temporal previo. Pruebas
unitarias de matching (no futuros/no selección por desenlace/no reemplazo/bins),
censura y clasificación. Chequeo de prefijo con replay real hasta timestamp completo:
añadir futuro no debe cambiar eventos ya publicados ni parejas ya fijadas.

STOP por hashes/QA o diferencias inexplicadas contra P0. Raw, pares y episodios
con precios quedan privados. Repo sólo código, agregado, pruebas y handoff.

## Traspaso local

Claude local: no correr más variantes con estas métricas sin otro plan. Integrar
capa causal al visor sin crear segundo visor; cruzar ES/MNQ sólo con sus L1/L2
propios y señales congeladas/alineadas; usar available_ts/row, nunca drop_ts
como disponibilidad. Requiere revisión de Nico antes de medir retornos/costos.
