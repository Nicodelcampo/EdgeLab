# Benchmark de representación v1 — fallo de arranque, sin resultados

## Estado cerrado

Kernel138420049/v1 `edgelab-mnq-phenomena-model-benchmark`, fuentee6eff31a84eb0ed78b46cfe21c39f67f16bc240a: terminalERROR observado tras dos consultas reservadas. Intento manual único ACK→ERROR, ningún retry. Source exacto/privadoCPU/Docker verificados antes. Boot agregado vinculado a source/bundle/plan correctos, integridad del archivo aprobadoPASS. No nueva QA ni salida privada.

Boot: descarga76.728s, host78.484s, hijo exit1, sin stop por límites; RSS hijo muestreado47,255,552bytes (no cgroup ni peak exacto). `outcomes_computed=false`, sin resultado/model receipt. HTTP404 para runner-failure receipt, no reintentado. No comparación científica nueva, ni fallo de hipótesis A/E.

## Diagnóstico y corrección

El runner nuevo importa `source_footer.validate_pin`, pero el paquete heredado no incluía `source_footer.py`. Reproducción del paquete EXACTO aislado, sin acceso a datos ni URL: `ModuleNotFoundError: tools.research_ops.confluence.source_footer`. Esto identifica un defecto determinista de empaquetado y concuerda con fallo temprano del hijo remoto. No se dispone del traceback privado remoto: no afirmar que se lo leyó.

Se añadió esa dependencia al bundle. La prueba nueva desempaqueta el código en directorio aislado, elimina PYTHONPATH del repo y ejecuta `--help`: caso positivo correcto y caso negativo quitando la dependencia reproducen/resuelven el fallo. Compile del notebook y suite desde repo NO detectaban ese faltante; aprender a probar límites reales de aislamiento además de funciones.

NO cambiaron fechas, features, A/E thresholds, modelos, lambda, métrica, gates de calidad/censura ni presupuestos. Calibración anterior sigue congelada. El intento fallido NO se reemplaza retroactivamente por versión corregida, ni se resetea journal. Nuevo intento requiere autorización explícita y presupuesto nuevo vinculado al cierre.

## Siguiente paso

Nueva ejecución controlada del paquete corregido bajo el MISMO protocolo científico; adquirir boot/model agregados y revisar con `review_phenomena_models.py`. Aún no hay evidencia incremental para decidir interacciones de zonas ni resultado que escribir en Brain científico. Sistema autónomo/servidorDebian no desplegados ni integrados por este benchmark.
