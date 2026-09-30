# Borrador — información L2 incremental dentro del segundo impulso

**NO APROBADO / NO EJECUTAR LABELS, MODELOS NI OUTCOMES.**
No autoriza una búsqueda sobre retornos. Software y soporte target-free ya
pueden probarse; la hipótesis predictiva real necesita ratificación de Nico.

## Pregunta primaria propuesta

Entre los intentos de regreso B→A observables después de confirmar A/B,
¿la información L2 disponible al cruzar el 50 % mejora la probabilidad de llegar
a A antes de una invalidación y plazo definidos, respecto de lo que ya sabemos
por el precio?

No equivale a predecir el próximo tick, a continuar después de A ni a rebotar en A.
Si el landmark/A ya se alcanzó antes del registro/primera observación, conservar
el intento pero abstenerse de considerarlo un cruce prospectivo. No usar el conjunto
de espejos completados como denominador.

## Campos que faltan ratificar

| Campo | Propuesta / estado |
|---|---|
| Instrumento y contrato | MNQ o GC; por fijar, campañas separadas, sin pooling |
| Detector A/B | Configuración congelada de IMP_CONFIRMED; no terminal records |
| Marco de barras | Por instrumento; no trasladar 150t MNQ a 25t GC |
| Publicación raw | Ledger verificado a cierre/grupo/primera fila real posterior |
| Landmark | 50 % primario propuesto; alternativas no se barren automáticamente |
| Invalidación del target futuro | Por ratificar; el rechazo geométrico del helper no define un SL |
| Plazo/censuras | Por ratificar en tiempo/barras/eventos; tratamiento de fin de sesión |
| Ventana features | 10 s de diagnóstico, propuesta no validada económicamente |
| Edad máxima del snapshot | Por ratificar; age no se rellena con cero |
| Grupo de features primario | QI touch + OFI endpoint normalizado; propuesta |
| Tamaño mínimo económicamente útil | Por fijar en ticks/R netos; sin N iid universal |
| Datos y splits | Desarrollo temporal y confirmación reservada por sesión/episodio |

## Baselines y contraste

Baseline B0: anchura del primer impulso, dirección, progreso actual, tiempo desde
confirmación B, velocidad/volatilidad histórica y spread disponibles en el evento.
B1: exactamente el mismo B0 más el pequeño bloque L2 preespecificado.
Todos los intentos registrados deben figurar en el ledger; los que no alcanzan
landmark/son tardíos se cuentan separadamente. No aprender una regla con la ausencia
silenciosa de fallidos o con registros que conocen `estado_final`.

`weighted_mid_minus_mid_ticks = spread_ticks * QI_touch / 2`: no tratar el mid
ponderado y QI como dos evidencias independientes. QI3/QI10 y reposición son
alternativas registradas, no una búsqueda libre de combinaciones por beneficio.
OFI de endpoints tampoco es flujo intragrupo ni demuestra identidad de órdenes.

Evaluación primaria propuesta: diferencia OOS de log-loss/Brier, calibración de
probabilidades y estabilidad entre sesiones. AUC/acierto sólo secundarios.
Prohibido asumir un nulo universal 50 % para llegada a A: geometría y barreras
pueden explicarlo. Predicción incremental no implica rentabilidad.

## Validación y potencia

- División temporal por sesiones, sin random split entre filas próximas.
- Purga/embargo declarados para intentos, landmarks y ventanas solapados.
- Normalización/calibración entrenadas sólo con pasado del bloque de entrenamiento.
- Misma población para B0/B1; reportar soporte observable y fallback B0 cuando falta L2.
- Dependencia por sesión/episodio; no miles de snapshots = miles de trades independientes.
- Número pequeño de hipótesis, corrección declarada, mínimo de mejora y MDE antes de abrir.
- Más datos si no hay potencia; no aflojar umbrales para obtener significación.

Los dos ejemplos GC ya expuestos sirven para QA, NO confirmación independiente.
Holdout forward octubre+ sellado. Disponibilidad/clock/cobertura se comprueban
antes de labels. Comisiones, spread y slippage propios del instrumento y fills
gobernados constituyen una fase posterior, con manifiesto y autorización.

## Autorización

GO sólo después de que Nico apruebe el manifest completo con los campos pendientes.
El pedido de preparar investigación no sustituye el OK separado para abrir destinos.
No se genera aquí y_true, accuracy, P&L ni un estimador de probabilidad.

## Aporte al referente

La pregunta puede refutarse: exige valor adicional al precio, separación temporal
y economía posterior, no sólo reconocer un espejo cuando ya terminó.