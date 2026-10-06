# EdgeReplica — prueba fuera de muestra posterior a la publicación (protocolo) — 2026-10-06

**Estado: BORRADOR, pendiente de OK de Nico. Nada se descargó ni se abrió.**

## Pregunta
¿Las 60 reglas publicadas el **2026-09-10 12:00 CT** siguen teniendo expectativa neta positiva en MNQ con datos que
ni el proveedor ni nosotros usamos para elegir nada?

## Lo que ya está visto (no cuenta como prueba)
Diagnóstico `ghost_edgeexperiment_re_20261003/DIAGNOSTICO_MNQ_VS_NQ_Y_ULTIMAS_3_SEMANAS.md` §3.1, en puntos netos por
operación:
- Antes (1-jul → 10-sep): +3,77 [−3,11; +11,26].
- Después (11-sep → 30-sep): −5,44 [−15,94; +5,44], 130 operaciones, 13 sesiones.

Estos números se reportan junto al resultado como contexto, pero **no entran en la decisión**. Ya los miramos.

## Muestra de la prueba (única apertura de HOLDOUT-A1 para esta familia)
- MNQ 12-26, sesiones CME desde la del **2026-10-01** (abre 2026-09-30 17:00 CT) hasta la del **2026-10-30**,
  ambas inclusive. Son unas 22 sesiones y unas 220 operaciones.
- La fecha de corte se fija ahora y no se adelanta ni se extiende después de ver datos.
- Datos: ticks NT8 (`EdgeLabTickHistory`), con el bloqueo del holdout levantado sólo para MNQ 12-26 y esta ventana.
  La descarga se hace **después** del 30-oct, en una sola vez. Tras procesarla, los datos quedan en cuarentena.

## Estrategia (congelada)
- `EdgeReplica` tal como está en el repo: 60 reglas, 1 contrato, mismas órdenes (EXPERIMENT-n).
- El simulador es el mismo del diagnóstico (ejecución con libro), con una guarda nueva: se descarta la operación si
  el tick de salida llega más de 300 s tarde. Esta guarda se agrega y se testea **antes** de abrir.
- Costos: comisión USD 1,90 por ida y vuelta + 1 tick de slippage por lado (= 0,95 + 0,5 puntos).

## Métrica y decisión
Métrica primaria: puntos netos por operación. IC95 por bootstrap de sesiones (bloque = sesión, 20.000 réplicas,
semilla 20261006).
- **SOBREVIVE**: límite inferior del IC > 0.
- **DECAYÓ**: límite superior del IC < 0.
- **INCONCLUSO**: en cualquier otro caso. Además se reporta si el IC excluye +3,77, la media previa a la publicación.

Se publica el MDE (≈ 2,8 × el error estándar observado). Si el MDE es mayor que 3,77, se dice explícitamente que la
muestra no podía distinguir la expectativa previa de cero.

Descriptivos: largos/cortos, por regla, por día, curva de equidad, peor día, y el resultado sin los 2 peores días.

## Justificación económica
Celdas horarias exógenas: apertura de Europa, datos a las 07:30, cash a las 08:30, cierre. Si existe un flujo
recurrente a esas horas, la ventana corta lo captura. Si eran puro ajuste, la expectativa posterior a la publicación es ≤ 0.

## Cómo podría refutarse
Con un IC posterior a la publicación enteramente negativo (DECAYÓ). Con un INCONCLUSO, la familia **no** se promueve.

## Registro
1 prueba en `TRIAL_REGISTRY_GLOBAL` (familia EdgeReplica / MNQ), sumada a las variantes ya probadas (NQ, oro).
Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
