# Retroceso EMA20 multi-activo — preparación causal y censo target-free

## Estado

Censo real enviado a Kaggle v2. Estado observado RUNNING; aún NO hay un censo completo certificado ni resultados económicos. No convertir esta preparación en evidencia de edge.

Nueva hipótesis, no rescate de RTY60 ni réplica de cruces/barridos anteriores: aprovechar un retroceso a EMA20 dentro de una tendencia ya establecida. ES no está en el dataset canónico verificado; se difiere. MNQ, RTY y YM tienen respectivamente 154, 175 y 177 fechas elegibles propias del catálogo entre 20251007 y 20260630. La intersección común sólo sería 151: no se descartan fechas para igualar denominadores. Desarrollo expuesto, NO ciego/OOS. Activos de índices correlacionados no son tres réplicas independientes. Holdout general julio+ intacto.

## Detector y elección congelados antes del censo

EMA20/50/200 sobre barras 1/5min, 600 barras reales de warmup, hasta siete días calendario previos, reset por contrato. Tendencia previa EMA20>EMA50 y cierre previo>EMA200 para compras, inverso para ventas. Nivel EMA20 de la barra PREVIA, no EMA intrabar ni recalculada con el cierre de señal.

Armar tras una barra enteramente del lado favorable. Tocar/cruzar la EMA20 previa y recuperarla con cierre favorable; same-bar reclaim permitido. Una señal por episodio, rearmado sólo en una barra posterior intacta. Expiración diez barras; reset por gap, cambio de tendencia o fecha. Horario 10:00 ET–último cierre14:45 ET. Reserva31min sólo para contar intenciones; no simula posiciones ni fills.

Base y subconjunto separación |EMA20−EMA50|≥0,25×SMA20 true range estrictamente anterior, con veinte barras contiguas. Se fija el calendario BASE primero; filtrar no reprograma otros slots. Unidad U en ticks, no ROC porcentual ni ATR14.

Por activo, preferir5min si ≥200intenciones reservadas, mediana≥4/sesión y actividad≥80% de sesiones; si falla, elegir1min únicamente si cumple lo mismo. Si ambos fallan, STOP por frecuencia sin relajar umbrales ni buscar otro ganador. Subconjunto separado conserva sus conteos propios y no hereda potencia del BASE. Elección no accede a PnL.

## QA realizada y alcance

- Ocho tests sintéticos dirigidos PASS, no suite completa: touch/reclaim, armado, simetría short, gap, una señal por episodio, reserva, prefijos y expiración.
- QA real local separada: RTY20251007, ambos TF, fuente SHAexacto. Recursión escalar independiente reproduce todas las EMAs; cálculo directo TR20/U y condiciones de señales reproducen. Tres prefijos por TF, seis en total, PASS. Una sesión NO acredita toda la población ni frecuencia típica.
- En esa muestra únicamente: TF1 17 episodios/5intenciones; TF5 3/2. No son aciertos/trades ni censo completo.
- Runner real comprueba custodia completa de doce parquets antes de formar eventos, hashes de módulos/manifiesto, catálogo→universo_estudio y guardas holdout. Reconciliación de ticks por sesión y hasta tres prefijos por archivo/TF están planificados en el censo real, no declarados PASS antes de terminar.
- Sin retornos, modelos, L2, salida económica, fills, quote age o reloj absoluto certificados. Libro/IPC/escalonadas de otras campañas no se mezclan.

## Fallo v1 y corrección transparente

Kaggle privado nicolasbuttaro/edgelab-ema-pullback-census-20261001, kernel136606905. Fuente exacta privada de v1 y v2 comprobada.

V1 ERROR antes de leer datos: CANONICAL_ROOT0, dataset montado ausente. No produjo censo/outcomes. El intento de descargar ZIP de salida devolvió403; la API de session output sí permitió inspeccionar el traceback. No es una falla del detector.

V2 cambia sólo transporte: descarga autorizada de los mismos doce archivos, internet habilitado, custodia SHA requerida. Manifiesto y código detector idénticos. URLs firmadas/transporte/dataset privado no se publican. Whole-file hash de09-26 puede incluir bytes posteriores a julio; escaneo de precios termina estrictamente antes de julio.

Manifiesto SHA256 3409f5c3a47ac8858a7e5ea6e83efdcc423c8a5cc643f6208d2db1d67d31f94e; runner8b6ae2d3a3e326ec6b5fb3523e2ed447f25f2dc05ccf8c74b9c638a89e791d23. Base módulos nativos foundation391314907dec889599493c4a38282171d94a2f25. Registro previo en Notion; módulos exactos y parámetros en manifest.json.

## Qué sigue y qué bloquea medir ventaja

1. Recuperar custodia/preflight antes del censo; verificar fuente exacta y prefijos; reconciliar JSONL privado por identidad, conteos/fecha/contrato y selección congelada.
2. Sólo si hay soporte, cerrar manifiesto económico: salida fija, cotizaciones y costos nativos con stress, controles emparejados por precio/horario/tendencia/volatilidad, particiones/exposición e inferencia por sesión con presupuesto histórico. No escoger salida por beneficio.
3. MNQ154 no supera por sí solo el mínimo160 del componente nativo formal. RTY/YM>=160 tampoco aprueban G2 sin historiaN_eff, PBO/DSR/WF/vecinos/paridad.
4. No medir fills/PnL ni promover una estrategia con el censo. No abrir reservas para rescatar variantes.

Entregar código/manifest/QA y MEDIDO/NO MEDIDO en rama research/ema-pullback-census-20261001, sin merge. Productor privado completo, catálogo embebido/URLs/raw y ledgers de precio quedan privados; reproducción pública incompleta sin fuentes autorizadas.

Aporte al referente: se plantea una mecánica de entrada distinta y se exige frecuencia causal antes de gastar presupuesto en buscar ganancias.
