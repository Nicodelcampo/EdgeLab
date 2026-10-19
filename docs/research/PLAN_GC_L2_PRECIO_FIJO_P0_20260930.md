# GC L2 R02 / I-3 — piloto mecánico target-free

Registrado antes de contar ciclos de reposición. No es estrategia nueva: continúa I-3
de ABS-CTX y R02 del backlog; reconstrucción/calidad ya investigadas en EdgeLab.

Fuente privada: `nicolasbuttaro/edgelab-l2-gc-bookmap-audit-20260921`, versión 2.
Se usan únicamente L1/L2 y manifiestos de 20260531 y 20260615, elegidos por disponibilidad
del ejemplo, no por resultados. No cargar bundles del visor ni artefactos de retornos.
Raw local-only. Fuente NT8 MBP, no MBO. Código base consultado:
`cf7c4a3266709fc6674e5e11ec0dae0995e891d2`.

## Pregunta

¿Se pueden medir sin confundir niveles móviles con precios fijos los ciclos de caída
de tamaño visible → recuperación, separando coincidencia con trades de desaparición
del nivel? ¿La implementación mantiene causalidad y evita reutilizar un trade?

## Método fijo

1. Verificar hashes de los cuatro parquet contra manifiesto, grilla GC 0,1, source_row
   único/intercalado y monotonicidad del reloj. Los timestamps antiguos dicen reloj
   de referencia sin resolver: sólo diferencias de microsegundos; no clasificar
   horarios CME ni comparar contra otro feed. No reparar tiempos.
2. Reconstruir con `edgelab.research.l2_phase0.apply_event`, sin cambiar reglas.
   Registrar resync/borde, inválidos y cruces; excluir transiciones con libro cruzado.
3. Clave (lado, precio absoluto), no número de nivel. Sólo comparar tamaño antes/después
   en UPDATE que conserva precio. ADD no es un descenso; DELETE/cambio de precio
   cierra el episodio pendiente. Desaparición no implica cancelación ni ejecución.
4. Descenso compatible con trades: impresiones LAST al mismo precio en los 2 s previos,
   ordenadas por source_row, nunca futuras. Cada impresión se consume como evidencia
   una sola vez. No inferir agresor, prioridad o ID de orden.
5. Recuperación: UPDATE posterior del mismo precio, con aumento de tamaño, hasta 5 s
   después del descenso y >=70 % del tamaño previo. Umbrales heredados del tracker
   de referencia, no ajustados con la muestra. No usar percentiles de sesión completa.
6. Pruebas sintéticas: sin trades, trade futuro, trade expirado, DELETE+ADD, cambio
   de precio, timeout, no reutilización, y equivalencia de eventos por prefijos.
7. Medir viabilidad/QA y conteos por sesión. No comparar rendimiento ni extrapolar
   frecuencias de una sesión corta a una completa.

## Límites

Coincidencia temporal precio/trade y recuperación es heurística, no volumen ejecutado
identificado ni iceberg demostrado. MBP agrega participantes. La atribución causal
de consumo necesitaría mensajes de órdenes/trade summary no disponibles.
Dos ejemplos no validan estabilidad, efecto sobre señales, fills ni economía.

STOP: hashes no reconciliados, inversiones de reloj, precios fuera de grilla o
source_row duplicado/colisionado. Para nuevas pruebas sobre retornos/costos/riesgo:
manifiesto separado y OK explícito. Holdout forward oct+ no se toca.