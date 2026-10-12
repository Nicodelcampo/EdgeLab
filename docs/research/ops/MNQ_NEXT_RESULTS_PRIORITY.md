# MNQ: cerrar el trabajo guardado y priorizar resultados científicos nuevos

## Cambio de prioridad solicitado

El usuario pidió guardar todo el trabajo y priorizar resultados nuevos sobre
volver a auditar lo ya hecho. A partir de este checkpoint quedan en pausa las
nuevas expansiones de auditoría histórica, paridad, profiling y telemetría del
supervisor, salvo un defecto concreto que afecte una nueva corrida científica.
Mantener sólo los controles necesarios de fuente/fechas/causalidad/protocolo.
No repetir las matrices/focales ni convertir este cambio en permiso de holdout,
P&L, promoción o modificación retrospectiva del protocolo congelado.

## Qué ya está terminado y publicado

- Rama sistema PR117:711bd94a59c618d0a86031a6231c9b05d3a1b30d, verificada contra
  remoto antes de este checkpoint. Incluye código/evidencia, paridad11340filas,
  diagnóstico cgroup y500pruebas Research Ops. No supervisor24x7 ni claves reales.
- Rama científica `research/avzvol-longevity-full-grid`:
  eca53ec2277536b89f3b68cc39770c19dcba2483. Cinco matrices y cinco focales cerrados;
  interpretación conjunta y replicación del banco congelado publicadas.
- Protocolo científico9125197dc6098100459f36a3d90a5c7b7aa4f9c0 intacto.
- No edge validado. Las corridas previstas de la campaña ya terminaron: no hace
  falta repetirlas para cerrar su cómputo/recuperación.
- Dos scripts que estaban sólo en /data/analysis se hicieron portables y se
  incluyen en `tools/research_ops/reports/`. Reproducen EXACTAMENTE ambos informes
  técnicos publicados, desde sus agregados guardados, sin eventos privados/red.
  Gráficos/specs/tablas se regeneran; no hay que subir archivos de sesión secretos.

Los requests efímeros con URLs firmadas, credenciales, privados derivados/ticks y
archivos de servicios no se pushean. Todo el trabajo de código, planes, evidencia
y reproducción disponible de este hilo sí. No se afirma recuperar código perdido
que nunca se publicó en otro hilo.

## Qué queda pendiente científicamente (no confundir con infraestructura)

Fuente: `analysis-evidence.json` de las cinco réplicas dice explícitamente que
volumefraction/imbalance/efficiency están persistidas y que modelos incrementales,
carry entre sesiones y outcomes de familias no primarias aún no están analizados
inferencialmente. Existen diagnósticos combinados train/test, no una ausencia
absoluta de modelado: `INCREMENTAL_DIAGNOSTIC_NOT_VIRGIN_HOLDOUT`. En particular,
MNQ06-26 incluye baseline de contexto vs contexto+revisitas/volumen/velocidad/flujo,
ridge fijo10, sin tuning, imputación/scaling sólo entrenamiento. No aisla el
aporte estable de cada bloque ni es validación virgen/globalmente corregida.

### Prioridad1: aporte incremental y ablaciones sobre eventos existentes

Pregunta nueva: ¿revisitas, fracción de volumen interior, flujo/proxy y eficiencia
aportan información predictiva estable POR SEPARADO y en conjunto, más allá de
edad/distancia/volatilidad/hora, o el resultado depende de contrato/época/soporte?

Plan siguiente a fijar antes de ejecutar: mismos casos para cada comparación,
train/test temporales de DESARROLLO identificados explícitamente, imputación y
scaling sólo train, baseline fijo, pocos bloques/ablaciones sin tuning abierto,
población/dedup/endpoint/controles congelados y registro de toda la familia de
comparaciones. No presentar splits ya inspeccionados como holdout virgen.

Entregables nuevos: matriz contrato x bloque con cambio de Brier/log-loss y sus
bandas por sesión, soporte/censuras y estabilidad temporal; efectos que se
repiten vs los que se revierten; negativos y decisión de continuar/descartar.
Calidad predictiva NO es rentabilidad ni efecto causal. EXPLORAR, no CONFIRMAR.
Reutilizar eventos/atributos preparados en Kaggle donde cubran la pregunta,
sin regenerar detectores ni reauditar la campaña. El sampler entero de conteos
no se aplica automáticamente a pérdidas flotantes: método nuevo bien definido.

### Prioridad2: controles que discriminen mecanismo de geometría/contexto

Precisar antes de correr comparaciones de lado/ancho/contexto y soporte común,
sin suavizar gates de la campaña. Si las columnas/control-populations existentes
alcanzan, esto es análisis nuevo de outputs; si falta un control nuevo, requiere
un experimento nuevo separado y acotado. No cambiar recetas congeladas después
de conocer sus réplicas. Evitar que una pequeña diferencia relativa se venda
como interés de mercado absoluto o edge económico.

### Prioridad3: ampliar la generalización, no una búsqueda abierta de ganadores

- Otras familias: el focal YA explora18familias; lo pendiente es extender las
  preguntas incrementales/detalladas más allá de la geometría primaria, con una
  familia limitada y procedimiento de multiplicidad definido. No decir que
  esas18familias nunca fueron analizadas ni elegir sólo celdas positivas.
- Carry entre sesiones: pregunta no cubierta por el análisis inferencial actual.
  Puede exigir nueva generación de eventos/historia de formación y protocolo;
  NO es una condición para cerrar la campaña congelada ni un ajuste gratuito.

## Qué NO bloquea estas próximas corridas manuales

No hace falta terminar el writer canónico, firmas de producción, delegación
cgroup o deploy autónomo para producir análisis científicos MANUALES y acotados
en Kaggle. Esos faltantes bloquean autonomía/ingest autenticado, no el estudio de
outputs existentes. Son cosas separadas: no etiquetar un manual como autónomo.
Mantener mercado/privados en Kaggle, holdout desde2026-10-01 cerrado, no P&L,
no promoción/merge automático. Un manifiesto nuevo de análisis se guarda aparte;
verificación mínima de input/build/alcance no implica repetir auditorías viejas.

## Próxima acción sugerida

Prioridad1 primero, luego control discriminante según el resultado. Guardar una
especificación corta y todos los resultados/negativos agregados. Este documento
fija la prioridad y los pendientes: NO afirma haber lanzado análisis nuevos ni
completado un preregistro/admisión. No pedir un VPS/credenciales de producción
sólo para poder analizar los outputs en Kaggle.

## Reproducción de trabajo técnico ya realizado

```bash
python tools/research_ops/reports/reproduce_resampling_report.py \
  --output-dir /tmp/edgelab-resampling-report
python tools/research_ops/reports/reproduce_primary_grid_report.py \
  --output-dir /tmp/edgelab-primary-grid-report
```

Los outputs deben estar fuera del repo para no sobrescribir evidencia histórica.
Ambas interpretaciones regeneradas se compararon por igualdad JSON exacta con
las publicadas; no se ejecutó ninguna investigación de mercado en esta verificación.
