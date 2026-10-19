# RTY sin L2: seis pruebas precio/volumen 5/15min — resultado exploratorio

## Veredicto y alcance

**0/6 celdas pasan la compuerta conjunta; no abre validación interna ni holdout.** No es prueba de ausencia de todos los efectos RTY. Momentum tiene media condicional positiva y límite neto inferior ajustado bajo cero; reversión VWAP media negativa; ORFAIL muestra insuficiente. No invertir señales ni aflojar umbrales a partir de este resultado.

Autorización de Nico: elegir activo/temporalidad y ejecutar varios análisis sin L2 en Kaggle mientras avanza Codex. Campaña separada de IPC × L2; no modificación/merge del trabajo de Codex. Rama propia `research/rty-no-l2-six-tests-20260930`, base391314907dec889599493c4a38282171d94a2f25.

## Medición

RTY NT8 canónico privado, contrato elegido por catálogo previo, 56 fechas CME incluidas20251007–20251231. Horario RTH09:30–16:00ET. Seis variantes: momentum60min, reversión distancia2ATR respectoVWAP RTH y reentrada después de primera ruptura del rango09:30–10:00 dentro30min; cada una5/15min. ATR20 estrictamente anterior. Decisión cierre completado10:00–13:45ET; entrada primer print después250ms dentro1s, salida fija2h con print dentro1s. Una posición no solapada por variante; ORFAIL primer intento.

PNL por cotizaciones agresivas observadas, más1tick de slippage/lado y comisión **asumida**0,9tick (USD4,50 si RTYtickUSD5). No son fills ni cotizaciones con edad certificada. No libro L2. Benchmark dirección aleatoria en idénticos momentos; alpha equivale al cambio de mid orientado por señal. No modeloM0/M1 ni control geométrico de zonas.

12 endpoints primarios: neto y alpha ×6;20.000 bootstrap por sesión, mínimo30eventos/20fechas activas; límites inferiores unilateralesBonferroni. MDE80 aproximado, no power certificado. Enero–marzo sólo supervivientes; como hubo0, no se decodificaron sus outcomes. Abril–junio tampoco; holdoutjulio cerrado. Dataset conserva contenedores posteriores, pero sólo filtros anteriores a enero se decodificaron; hashear contenedores no es abrir desenlaces.

| Variante | Evaluados / emitidos | Neto ticks/evento | Límite inferior ajustado | Estado |
|---|---:|---:|---:|---|
| Momentum 5 min | 82 / 111 | +41.62 | -0.89 | No pasa |
| Momentum 15 min | 77 / 99 | +42.66 | -3.97 | No pasa |
| Reversión VWAP 5 min | 82 / 99 | -39.46 | -82.63 | No pasa |
| Reversión VWAP 15 min | 57 / 63 | -52.99 | -96.36 | No pasa |
| Fallo rango 5 min | 29 / 34 | -55.97 | — | Muestra insuficiente |
| Fallo rango 15 min | 17 / 19 | -15.49 | — | Muestra insuficiente |

## Cobertura y limitaciones que cambian la interpretación

425 eventos-celda emitidos;344 evaluados;81 censurados por falta de print dentro1s (entrada32; salida49). Son eventos-celda, **no425 operaciones únicas**: variantes pueden compartir momentos y desarrollo. Todas las56fechas pasan los gates completosRTH por variante.

La censura de disponibilidad de salida puede seleccionar soporte dependiente del futuro; las medias son condicionales a tener extremos observados, no estimaciones de rentabilidad de toda señal operable. Cobertura por variante difiere. No recodificar censura como cero/pérdida ni cambiar1s para rescatar. La comisión no fue contrastada contra tarifa del usuario. PNL neto bajo supuestos, no ventaja ejecutable.

Momentum5/15: MDE80 neto aproximado58,57/59,22ticks, superior a las medias41,62/42,66ticks. Información direccional tiene límites inferiores3,22/0,049ticks, pero no alcanza la compuerta económica; además rige el problema de censura. ORFAIL29/17evaluados no cumplemínimo30. No interpretar NO_SUPPORT como equivalencia a cero, ni INCONCLUSIVE como fracaso confirmado.

## Procedencia y errores de infraestructura

Manifest publicado en Notion antes de correr. Código ejecutadoSHA256 `4a3743ed166c45efcc0c1d8d0b8333ac303aa0c366426550354793c44eae810d`; manifest `32e98b0ea4891a51fafcab04aceecc690c66631e8757eef6969448e5df030dd3`. ReceiptKaggle y manifest descargados coinciden con los congelados; selftests sintéticosPASS local y Kaggle. Datos y catálogo hasheados antes de medición; catálogoKagglebytescc3f1c4d…dc73 semánticamente igual al repo, distinto formato. AUDIT_MANIFESTZSTD19 hasheado; SHA originales anteriores a recompresión registrados separadamente. No se dispensaron hashes discordantes.

Kaggle privado: https://www.kaggle.com/code/nicolasbuttaro/edgelab-rty-sin-l2-seis-pruebas-20260930, versión3, COMPLETE. Versiones1/2 fallaron DATASET_ROOT antes de leer datos, sin outcomes. V3 sólo cambia transporte: descarga autorizada privada de seis archivos y metadatos exactos, verifica hashes y ejecuta código congelado sin modificaciones. Wrapper con enlaces temporales se excluye del repo. Duración de cómputo/export inicial ~59s según log, sin cola ni publicaciónHTML.

Auditoría independiente: identidades sin duplicados por celda/fecha/señal, reconciliación emitidos=evaluados+censurados, cotizacionesPNL y timestamps, promedios/fechas activas/denominadores. No certificación exhaustiva de fills ni reloj absoluto del proveedor. PerfilArrow de RTY12:8.512.225filas archivo,8.098.752del fragmento desarrollo, timestamps no decrecientes;4.226.795timestamps repetidos son prints distintos, no filas duplicadas eliminables;0null en cinco columnas;28quotes inválidas en fragmento. El perfil genérico no admite esteparquet y falló comoCSV: se reemplazó explícitamente porPyArrow, sin adjudicar corrupción.

Cerebro consultado: `artifacts/hippocampus/research_history_ledger.jsonl` e `ipc_20260926.jsonl`; reglas contra rescates de grillas, controles geométricos sesgados y p-valores degenerados de muestras chicas. ZB/6J se descartaron **antes** de outcomes por manifiestos de régimen con0sesiones elegibles. RTY es transporte exploratorio de reglas de precio, no desarrollo virgen ni reapertura automática de familias históricas cerradas.

## MEDIDO / NO MEDIDO y siguiente decisión

MEDIDO: este screen de seis celdas, soporte común, benchmark direccional, costes supuestos e incertidumbre. NO MEDIDO: enero–marzo, abril en adelante, holdout, ejecución/fills, tarifas propias, cobertura operable completa, independencia de censura, utilidad L2. No mezclar con campañafiltrosIPC × L2.

Antes de una nueva pregunta sobre momentum: auditar cobertura temporal/as-of y tarifas, diseñar una salida operable que no condicione inclusión a datos futuros, preregistro nuevo y presupuesto específico; no retocar esta tanda. No hay candidato autorizado a confirmación del presente screen.

Aporte al referente: precio-onlyRTY muestra dos medias momentum positivas pero0/6pases completos; reversiónVWAP no respalda esa entrada y ORFAIL carece de muestra. Se conserva incertidumbre y la censura, sin convertir medias en ventaja.
