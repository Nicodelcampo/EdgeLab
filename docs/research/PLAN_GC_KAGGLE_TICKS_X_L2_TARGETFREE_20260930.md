# GC Kaggle ticks ↔ L2: prueba de identidad target-free

Fuentes fijadas: ticks GC08-26 Kaggle v2, SHA7976fbe9…; L2 GC08-26 v2
archivos20260531/20260615 con hashes previamente verificados. No GCfebrero,
ningún holdout, ni outcomes/modelos/P&L. Corte1782856800000000000.

El repo resuelve reloj L2 como pared ART, pero prohíbe join cercano con Last.txt:
correspondencia entre conversores NO resuelta. Evaluar sólo dos referencias
preespecificadas: ts_us*1000 literal y +3h según acta de timezone. No búsqueda
por correlación de retornos ni nearest-neighbor ni interpolación.

Comparar identidad exacta(timestamp,precio_ticks,volumen) y multiplicidad
entre trades L1 side2 y ticks.Last, agrupando duplicados sin inventar parejas.
Reportar no encontrados/ambigüedad, orden y cobertura. Coincidencia parcial
no autoriza acoplar el libro. Sólo población íntegra con secuencia/orden raw
verificada habilitaría propuesta de join; cualquier fallo conserva ABSTAIN.

Si no pasa, usar cinta side2 del MISMO feed para barras/ledger causal, sin
confundirla con las barras febrero ni afirmar equivalencia de feeds. No cambiar
umbrales del detector, no activar escenarios económicos ni calibrar perfiles.

## Refinamiento de identidad después del primer diagnóstico, antes del replay

La multiset May31 es íntegra pero contiene ejecuciones repetidas. Se comprueba
la cinta COMPLETA en orden raw contra la cinta completa Last, no sólo claves
únicas; no se elige un subset. Si todos los triples en orden son iguales,
puede probarse libro con publicación ESTRICTAMENTE ANTERIOR al timestamp del
trade. Prohibido usar cualquier libro publicado en el mismo timestamp aunque
el source_row del otro conversor parezca ubicarlo antes. Así los prints
idénticos dentro de un timestamp no requieren inventar orden entre feeds.
No certifica fills/latencia ni otras fechas. Junio15 falla cinco timestamps:
no se corrigen, nearest-neighbor sigue prohibido y el gate permanece ABSTAIN.
Barras25 operaciones de la cinta Kaggle íntegra May31; OHLC sólo descriptivo,
no detección IPC ni etiquetas/retornos. Prefijo2000 trades vs replaycompleto.
