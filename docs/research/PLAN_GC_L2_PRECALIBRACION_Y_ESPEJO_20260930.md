# Plan target-free — GC antes de calibración y L2 durante el espejo

Estado: preparación y QA de observables, NO evaluación predictiva/financiera.
HEAD inicial: `767e30bcc5b54d35b6f19013d09f192520cafafc`.
Este plan se escribe ANTES de contar resultados nuevos. No modifica C0–C4,
el detector de MNQ, climas STOP, raw ni visores.

## Trabajo que no depende de la calibración humana de GC

Un extractor as-of, en ticks y contratos, independiente del detector:

- Spread y profundidad visible, desequilibrio de colas a 1/3/10 niveles.
- Desvío del mid ponderado por las colas respecto del mid. Es proxy, NO microprice
  calibrado, probabilidad ni precio justo.
- OFI de endpoints consecutivos publicados, suma retrospectiva en 10 s y
  normalización por profundidad actual. NO flujo completo de eventos intragrupo.
- Visibilidad del precio fijo solicitado en el lado declarado. Fuera del top-10
  devuelve UNKNOWN/null, no tamaño cero ni cancelación.
- Gate de integridad, edad, filas de snapshot/publicación/decisión y soporte de
  ventana completa. Sin heurística de agresor, IDs de órdenes ni etiqueta iceberg.
  OFI de ventana incompleta devuelve null; la suma del prefijo observado se guarda
  aparte sólo para diagnóstico, no como si fueran 10 s completos.

Primero ejercitar el extractor en los DOS ejemplos GC privados ya expuestos en
P0/P1, sin zonas ni señales nuevas, sin retornos. Reloj absoluto no certificado:
usar orden raw y tiempo relativo; NO asignar horas CME o afirmar sesiones completas.
No mezclar mayo/junio con GC febrero de 25t ni MNQ. No son una confirmación nueva.

Publicar el grupo del timestamp anterior sólo cuando aparece la SIGUIENTE FILA
REAL con timestamp mayor. Snapshot as-of excluye esa fila nueva. EOF no publica
un estado operable. Reiniciar historia al invalidar el libro; desconocidos no
se convierten en false/cero. Fórmulas fijas, sin seleccionar umbrales con precio futuro.

Pruebas: espejo de precios/lados, fórmulas a mano, prefijo exacto, misma marca de
tiempo, snapshot futuro prohibido, EOF, reset y cross-instrument. Muestreo privado
fijo cada 500 publicaciones válidas sólo para QA; los agregados recorren TODAS.
No tratar snapshots como operaciones ni muestras independientes.

## Espejo: definir una pregunta falsable, sin abrir destinos

Interpretación propuesta: segundo impulso = regreso desde B hacia A, donde A/B
YA estaban confirmados causalmente. No continuación después de A ni rebote en A.
Landmark primario propuesto 50 %; NO aprobado como regla operativa. Otros
porcentajes sólo vía manifest ratificado, no una búsqueda automática.

`mirror_l2_attempts.py` exige registro con filas conocidas y geometría congelada.
Todos los intentos quedan en receipts: pendientes, invalidados antes del landmark,
landmark tardío y A ya alcanzado. Primer precio observado ya más allá del landmark
no se retrotrae: se abstiene de evento prospectivo por cruce no observado.
Al landmark se une sólo información L2 ya publicada; presión se orienta hacia A.
No es un detector causal de A/B: requiere ledger upstream verificable.

## Evidencia externa que motiva, no demuestra la hipótesis

- Cont, Kukanov y Stoikov, The Price Impact of Order Book Events:
  https://arxiv.org/html/1011.6402v3 — relación de OFI con cambios CONTEMPORÁNEOS,
  no prueba de predicción de llegada a A. Fuente en acciones NYSE, no GC/MNQ.
- Gould y Bonart, Queue Imbalance as a One-Tick-Ahead Price Predictor:
  https://arxiv.org/html/1512.03492v1 — evidencia de siguiente cambio de mid,
  heterogénea por tamaño relativo del tick. No implica predecir un impulso entero,
  P&L neto ni portar sus particiones aleatorias a nuestro dato intrasesión.

## STOP antes de probar predictibilidad

Antes de cualquier etiqueta de precio futuro o modelo supervisado:
ledger A/B causal y población de TODOS los intentos; instrumento/periodo;
landmark, invalidación, timeout y unidad económica; selección de features;
split temporal por sesiones, purga/embargo de episodios solapados;
baseline de precio/anchura/progreso/velocidad/volatilidad/spread frente al
mismo baseline + L2; log-loss/Brier y calibración OOS, no sólo acierto;
soporte de missing/fallback, dependencia intrasesión, mínima mejora útil/MDE,
presupuesto de hipótesis y OK explícito de Nico.

GC exact4 también necesita aprobación geométrica y publicación raw antes de
unir eventos operables. Reposición previa P1 NO probó absorción. No seleccionar
C1–C4 por retornos. Costs/fills sólo con motor gobernado y permiso separado.
Holdout forward octubre+ intacto. Privados/velas/precios/packets NO al repo.

## Aporte al referente

Adelanta la medición reutilizable y separa presión contemporánea de predicción
incremental futura, sin contaminar calibración ni abrir un backtest no autorizado.