# Historia causal A→E / E→A — implementación nueva, no corrida lanzada

**IMPLEMENTED_SYNTHETIC_TESTED_NOT_FROZEN_NOT_LAUNCHED.** Continúa `NEXT_MECHANISM_AFTER_GC_NEGATIVE.md`; no modifica ningún plan previo, negativo GC, detector, dataset o criterio de confirmación.

## Qué quedó implementado

- `phenomena_history.py`: prefijo causal acotado con componentes continuos actuales y retardos20/40/60/120s. Cada retardo usa exclusivamente la última observación anterior o igual al reloj objetivo; tolerancia5s, sin interpolación/futuro. Disponibilidad y edad son features explícitas. UNKNOWN conserva su posición; no se sustituye por el último estado conocido. Máximo128 observaciones retenidas y presupuesto total de anchors; overflow falla sin truncar.
- `phenomena_transitions.py`: duración observada/cap120s y transiciones ya ocurridas. UNKNOWN, gap>10s, sesión y **cambio de dirección de referencia** interrumpen el episodio. La orientación importa: A/E están definidos respecto del impulso previo; A en dirección+ y E en dirección− no son un mismo mecanismo A→E. El argumento nuevo es opcional para compatibilidad del prototipo; el nuevo preparador lo pasa explícitamente.
- `phenomena_history_session.py`: medición/clasificación originales, luego avance de la historia, luego respuesta futura. Los anchors que posteriormente resultan censurados siguen formando parte de la historia. Sensibilidad60s selecciona el primer anchor observado antes de conocer su label, sin reemplazar seleccionados censurados.
- `phenomena_history_models.py`: catorce representaciones fijas (PRIOR/HISTORY y seis pares PROXY/CAPACITY:estado,duración,A→E,E→A,ambas transiciones,todo). Los pares tienen idéntica cantidad de features añadidas y la misma historia continua. Ridge0,01, peso igual por sesión de entrenamiento, sin ajuste en evaluación, selección automática ni export de parámetros. Umbrales A/E no se trasladan desde MNQ a GC por este módulo: el futuro caller deberá proveer calibración GC cronológica y verificable.
- Purga y embargo: helper de reloj fijo60s/60s; no usa duración realizada del outcome. **Falta conectarlo en el runner de la nueva corrida**, no afirmar que ya gobierna un kernel.

## Contrastes previstos

A→E y E→A se puntúan por separado en los mismos anchors con transición reciente ya observada; cada modelo se compara con HISTORY y su control de capacidad. También se conserva el universo común completo y sensibilidad60s. Estado/duración/transiciones combinadas son ablaciones, no oportunidades para rescatar un contraste primario negativo. Grupos sin soporte devuelven `null`, nunca pérdida cero. Anclas solapadas no se declaran episodios independientes.

Los controles suaves de capacidad están fijados en código y usan los mismos componentes presentes/pasados; igualdad dimensional no prueba equivalencia de regularización efectiva ni mecanismo físico. Una eventual diferencia será utilidad de representación en desarrollo, no evidencia de reposición pasiva, iceberg o agotamiento físico.

## Pruebas

36 pruebas focales/de compatibilidad PASS (2,551s): truncación/prefijo, aliases de arrays, as-of frente a observación futura más cercana, masks/UNKNOWN, gaps, dirección, sesión, same-ns con secuencia estricta, un único evento de transición en timestamps compartidos, expiración, presupuesto/poisoning, holdout, sensibilidad antes de labels, purga/embargo, capacidad igual, sin refit y grupos vacíos explícitos. Integración con mediciones/respuestas reales sobre tape **sintético**; prueba adicional cambia censura futura y verifica que features de los anchors comunes permanecen exactos.

No se descargaron ni leyeron ticks de mercado en el sandbox. Las pruebas no certifican calibración, soporte, potencia, velocidad real o edge.

## Falta antes de lanzar

1. Runner de nueva campaña con calendario/calibración GC vinculados explícitamente, purga/embargo y reconciliación de fechas vacías sin reemplazos; fit completo antes de leer evaluación.
2. Congelar plan propio: dos contrastes, fechas exactas, límites, soporte por sesión/transición y margen práctico/MDE declarado (no tratar miles de anchors como tamaño muestral independiente). Sept17–30 sigue candidato, no protocolo autorizado por estos módulos.
3. Empaquetado con dependencias exactas, hash/source/Docker privados, export estrictamente agregado; auditor de recibo nuevo y autoridad/journal nuevos. Nunca reusar/resetear journals terminales para obtener presupuesto.
4. Medir soporte dentro de la corrida científica única, sin nueva cadena de validaciones de datasets. Si falta soporte, registrar inconcluso, no cambiar thresholds/calendario a posteriori.

No se lanzó Kaggle, no se modificaron kernels activos/congelados, no canonical Brain write, deploymentDebian/24x7, holdout, P&L, certificaciónNT8 ni merge.

## Calibración existente y borrador listo para continuar

`GC_AE_HISTORY_DESIGN_DRAFT.json` reutiliza la calibración GC del31 de julio, SHA `539b4ba21975510eafeac107c48b415618ba502802283d8860218631b058573d`, verificada desde el recibo agregado anterior: sin outcomes y sin nueva recalibración. Training original3–10 de agosto; diez fechas candidatas17–30 de septiembre, vacíos/feriados sin reemplazos. Conserva14 representaciones; no ejecuta detectores de zonas porque primero mide si la trayectoria aporta algo más que sus componentes continuos. Por eso el speedupBT2A anterior NO se atribuye a este experimento. Margen0,001Brier y soporte2000anclas/6sesiones son candidatos explícitos, aún no congelados; no hay potencia/MDE empírica demostrada. Reutilización de la calibración es custodia técnica, no certificación del mecanismo.

Regresión del snapshot actual:948ResearchOps PASS318,750s;18navegación PASS0,145s;catálogo PASS_NAVIGATION_ONLY (no autoridad científica). Código nuevo sin ningún envíoKaggle.
