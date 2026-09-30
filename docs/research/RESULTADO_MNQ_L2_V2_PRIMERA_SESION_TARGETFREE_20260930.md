# MNQ V2 — primera sesión: procedencia, disponibilidad e historia del pico

**Sesión20260629, MNQ_09-26 · Target-free, sin retornos/costos.** ZIP recibido sha256 `bbb11655a67aec1de7566f2f0e869246c85ca13c5b75e017904f26d78326b1bc`, 4.585.302bytes. Raw MNQ sigue en la PC; aquí se verifican adjunto/exports/código, no se rehashean sus parquets originales. Los hashes/raw receipts son iguales a V1.

## Procedencia y geometría

Los cuatro hashes recibidos coinciden EXACTAMENTE con bytes CRLF de los blobs publicados. Exporter V2 recibido `ee5f6dd48d068b9b4e7be54d56596038906954d4b56fa5216eb7b620798886fc`; blob LF equivalente sha256 `cfe868e993684f2780107d6660d113559810518a6c9a74ebef7e8a249080f4ce`. No cambios de método/parametrización fuera del diagnóstico V2 previamente optado.

19.569 velas150-LAST = 2.935.350 prints +90 parciales =2.935.440 elegibles. TODAS las velas OHLC/índices/filas de cierre coinciden con V1 y TODAS las31 señales coinciden en geometría y replay del detector congelado. Unicidad, grilla implícita, orden, publicación posterior al snapshot y UTC=ART+3h pasan el contrato declarado. Ninguna de las31 señales es sólo diagnóstico EOF/fin de sesión.

Este adjunto no contiene las filas raw de frontera: la publicación observada se verifica contra metadata + código y tests, no contra un nuevo replay independiente de100M eventos raw en nube. No es certificación de fills live.

## Tres momentos, las mismas31 señales

| Momento de observación | Nivel observable | Regla mecánica true | Visible false | Desconocido |
|---|---:|---:|---:|---:|
| Snapshot ya publicado antes/al LAST del extremo |26|6|20|5|
| Grupo que contiene el extremo, publicado después |17|1|16|14|
| Confirmación de la zona |4|1|3|27|

Conteos recalculados por Counter y pandas, denominador31 en todas las filas. Observable exige libro válido y precio presente top10. Regla mecánica=true significa >=2 reposiciones COMPATIBLES al mismo lado/precio en10s y tamaño visible positivo; NO iceberg, absorción, defensa efectiva ni ventaja probados.

Snapshot previo: edad mediana4ms, p95 24ms, máximo104ms (31registros). Es historia ya conocida antes/al extremo. Pero saber que ese extremo será el último pico de ESA zona se conoce después, al detectar: no habilita retrotraer la entrada al instante previo. Es candidato a feature histórica usada AL CONFIRMAR.

La señal aparece tras la publicación del grupo del extremo con demora mediana3,016s, máxima30,544s. Explica la necesidad de distinguir historia de pico de libro actual, no prueba que esa historia tenga información incremental.

## Cobertura y causa del faltante V1

4.299.562 grupos =4.199.913 PASS +99.159 bootstrap60s +312 profundidad incompleta +160 cruzados/missingtouch +18 desordenados. Los490 estructuralmente inválidos no son99.159 bootstrap. Grupo no es minuto ni vela.

18.870/19.569 velas con libro válido. Las699 no disponibles se explican por685 BOOTSTRAP_60S y14 INCOMPLETE_DEPTH. Causa por gate ya resuelta; no declarar corrupción de raw por ello. V2 permite distinguir esos casos y conserva la máscara en decisión exactamente como V1: sólo1true.

Profiler: constantes sesión/n_last/modo esperadas; campos de nivel vacíos en barras sin target y87%máscaras nulas en señales de decisión son faltantes intencionales. No rellenar0/false ni excluir señales para inflar tasa.

## Decisión

**PASS QA y soporte diagnóstico de primera sesión; no resultado financiero ni GO automático de52.** La historia pre-extremo ofrece26casos observables y6true compatibles, contra4/1 en decisión. Vale preparar una hipótesis nueva de historia de pico disponible al detectar; no sustituir silenciosamente el filtro original ni usar retornos para escoger ventana.

Antes de expansión: congelar mediciones/gates/población, contar frecuencia/observabilidad/clusters por sesión y acordar muestra suficiente. Antes de utilidad: manifiesto +OK de Nico, estimando/MDE/costos por instrumento y pocas pruebas. Una sesión no da potencia/edge. ClimasSTOP no rescatados; forward oct+ intacto.

## Aporte al referente

V2 conserva las31 señales y resuelve disponibilidad/cobertura. La observabilidad mejora usando historia previa del pico, pero utilidad y potencia económica siguen pendientes.
