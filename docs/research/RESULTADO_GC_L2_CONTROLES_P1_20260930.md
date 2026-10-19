# GC L2 — controles históricos P1 y traspaso local

**MEDIDO, descriptivo mecánico; utilidad operativa NO MEDIDA.**
Continuación R02/I-3 de P0. Una comparación fijada antes de contar P1, sobre los
mismos dos ejemplos privados ya vistos en P0: no es confirmación fuera de muestra.

## Conclusión

La recuperación visible observada fue **menor** tras caídas con trades compatibles
acreditados que en controles similares sin prints al mismo precio. No basta observar
reposición para identificar absorción/icebergs o justificar una entrada. Tampoco
este resultado prueba que la defensa local carezca de utilidad: **no se midieron
señales, desplazamiento de precio ni retornos**.

## Método congelado

Plan: `PLAN_GC_L2_CONTROLES_P1_20260930.md`, SHA256 `43065d2ae09c197bafce9779eb65edd839accf4987d6ca75809bdcbf244e9d7f`.
Mismos cuatro parquet GC NT8 privados Kaggle v2, hashes reconciliados como P0.
Mismo `apply_event`, bootstrap 60 s, snapshots al final del timestamp, precio fijo,
ventana de prints 2 s, recuperación >=70 % del tamaño anterior dentro de 5 s.

- Positivo: crédito de prints según P0, sin reutilizar una impresión.
- Control: ningún print al mismo precio en los 2 s previos disponible hasta el
  UPDATE; un descenso con prints cuyo crédito ya se gastó NO entra como control.
- Una pareja por positivo, sin reemplazo. Control iniciado **antes** del positivo
  en los 10 min anteriores; no se exige desenlace finalizado y no se selecciona por
  recuperar o fallar.
- Mismo archivo, lado, banda de profundidad previa (1/2–3/4–6/7–10), log2 de tamaño
  previo y caída absoluta, banda de actividad LAST de 2 s (0/1–3/4–15/16–63/64+).
  Información conocida en la caída; sin hora CME ni percentiles de sesión completa.
- Matching grueso, no igualdad exacta de todas las covariables continuas. No
  balance certificado de confusores, aleatorización ni efecto causal identificado.

## Recuperación observada en el soporte común

| Archivo | Pares | Positivos emparejados / total positivos | Con trades compatibles | Control sin prints al precio | Diferencia |
|---|---:|---:|---:|---:|---:|
| 20260531 | 3.992 | 90,1 % | 29,5 % | 37,0 % | -7.54 pp |
| 20260615 | 31.577 | 91,3 % | 38,0 % | 45,5 % | -7.53 pp |

Numeradores/denominadores del gráfico: 1.178/3.992 frente a 1.479/3.992; y
11.991/31.577 frente a 14.369/31.577. Diferencias calculadas a precisión completa.
El mínimo de soporte del plan (10 %) se superó en ambos; no se aflojaron estratos.

**La tasa es recuperación observada / todos los pares**, con censuras incluidas.
No es una estimación de probabilidad latente, supervivencia ajustada, absorción
real ni respuesta del precio. Salir del top-10 no prueba cancelación; la recuperación
fuera de lo visible puede ser desconocida. Los dos EOF pendientes también se conservan.
Miles de episodios correlacionados en dos archivos no son miles de sesiones
independientes: no se publica un p-value ni IC iid que aparenten confirmación.

### Destinos reconciliados de los pares

| Archivo | Grupo | Recuperación | Nuevo descenso | Desaparición/reset | Timeout | Grupo inválido | EOF |
|---|---|---:|---:|---:|---:|---:|---:|
| 20260531 | Con crédito de prints | 1178 | 985 | 1737 | 92 | 0 | 0 |
| 20260531 | Control sin prints al precio | 1479 | 892 | 1501 | 120 | 0 | 0 |
| 20260615 | Con crédito de prints | 11991 | 7876 | 11445 | 263 | 0 | 2 |
| 20260615 | Control sin prints al precio | 14369 | 7025 | 9757 | 426 | 0 | 0 |

Cada fila suma al número de pares del archivo. La censura es parte de la interpretación,
no casos descartados para mejorar la tasa.

## Repetición disponible causalmente

Un episodio repetido cuenta sólo si ya hubo una recuperación publicada en el mismo
(lado, precio) en los 60 s anteriores. No cuenta futuras recuperaciones ni usa IDs de orden.

| Archivo | Recuperaciones P0 | Con recuperación previa al mismo precio en 60 s |
|---|---:|---:|
| 20260531 | 1.282 | 127 |
| 20260615 | 12.818 | 3.347 |

Esto entrega una feature observable para un visor; **no un detector validado de
icebergs ni una nueva regla operativa**. La persistencia de la defensa, reposición
neto de consumo y efecto en señales quedan pendientes.

## QA adicional y límites

- 12 pruebas nuevas de matching y tracker, además de las 12 de P0.
- Conteos, resúmenes y JSONL de recuperaciones P0 reproducidos exactamente.
- Prefijos de datos reales hasta timestamp completo: 54 eventos / 124 parejas
  y 106 eventos / 306 parejas; agregar el resto del archivo no cambia ninguno.
- Recuento independiente de los CSV privados para ambos lados de todas las parejas,
  estratos, no reutilización, temporalidad y estados finales. Repeticiones
  verificadas por un segundo recorrido de los JSONL.
- En 20260615, 15 episodios **no positivos P0** fueron censurados por perder diez
  niveles visibles. Diagnóstico: un endpoint L2 con profundidades [10,5] en fila
  4.280.696; siguiente snapshot completo [10,10] en fila 4.280.702. Se cerraron los
  pendientes y reinició bootstrap; no se reconstruyó liquidez faltante.
  El contador P0 denominado `crossed_or_incomplete_groups` mide falta de touch/cross,
  no todas las pérdidas de diez niveles: no confundir su cero con completitud perfecta.
  Esto amplía la QA de P0 sin cambiar sus conteos positivos. No se atribuye causa
  a una hora CME ni se declara corrupción del feed por este endpoint parcial.
- Reloj absoluto de los manifiestos legacy no certificado aquí: sólo orden de filas
  y tiempo relativo. MBP no trae IDs de orden ni prioridad de cola.
- Entorno ejecutado: NumPy 2.5.3, pandas 3.0.6, PyArrow 25.0.0; no certificación de CI.

## Publicado y pendiente local

Código: `tools/gc_l2_historical_controls.py` y tests; evidencia agregada en
`artifacts/gc_l2_controls_p1_20260930/evidence.json`. El código ejecutado fuera de
una worktree git se identifica por bytes, no por afirmar que un commit clean corrió.
SHA256 P1: `fccb5e987035553b35cf7975b8f5280da0e9bba27da9bdf9cb11e1c516754967`.
HEAD al comenzar: 899c1c4; HEAD remoto posterior observado: 9cc2227 (otra sesión
integró contextos MES/MNQ). Se conserva su ledger íntegro al añadir P1.
Raw y pares/episodios con precios quedan privados; no se tocaron visor ni climas.

Traspaso: `HANDOFF_LOCAL_CLAUDE_GC_L2_P1_20260930.md`.
Local debe alinear relojes/datos propios, integrar la capa al único visor y adaptar
el lector a ES/MNQ. El probe GC hardcodea tick 0,1, fechas y schema legacy: no sirve
para esos activos sin adapter validado. No reutilizar sus umbrales como parámetros
certificados de ES/MNQ ni rescatar climas STOP.

Antes de retornos/costos/MFE/MAE: manifiesto aparte y OK de Nico. Holdout forward
oct+ intacto. No se inició otra sesión de Claude desde este traspaso.

## Aporte al referente

Los controles impiden equiparar reposición con absorción; queda una capa causal
reproducible y el trabajo local delimitado, sin prometer un edge todavía no medido.
