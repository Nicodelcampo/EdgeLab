# MNQ escalonadas × L2 — preparación target-free (30/09/2026)

Pedido de Nico: preparar el trabajo desde nube, minimizar trabajo/créditos de Claude local.
**No autoriza todavía retornos/costos ni nueva apertura del holdout.**

## Objeto único

MNQ escalonadas PLANAS, escala 150 ticks, confirmación por precio, transferencia
existente ES ×12,42. Geometría heredada, no elegir la mejor de las 648 celdas.
Parámetros: w=2, max_gap=15, max_step=25, min_pull=62, nmin=3,
dmax=35, total_min=0, step_min=0, X=25 ticks. Se usa el redondeo del CLI existente.
Corrección de transcripción antes de probar datos: el CLI escala también CONF_TICKS;
2×12,42 redondea a 25, no a 2. No se modifica el detector original.

El evento de esta preparación se conoce **al cierre de la vela de confirmación**,
con disponibilidad conservadora al terminar su grupo de timestamp. No se reutiliza
un supuesto fill intrabar del estudio anterior. Es una variante de disponibilidad
que debe figurar explícita en un manifiesto nuevo, no una réplica de ese P&L.

## Trabajo ejecutable ahora

1. Detector incremental de geometría y confirmaciones, sin copiar información del
   final de una serie. Test contra detector existente en cada prefijo.
2. Exporter local de L1/L2 del mismo feed MNQ: velas 150-LAST (número de prints,
   no volumen), eventos causales y features del libro previas/disponibles al emitir.
   Ledger por archivo/sesión y hashes; clock ART→UTC sólo bajo contrato explícito.
3. Recoveries compatibles a precio fijo (no icebergs): mismas ventanas P0 2 s/5 s/70 %,
   por continuidad del observable, NO validación de umbrales en MNQ.
4. Features para inspección, no entradas: spread, profundidad 3 niveles, imbalance
   agregado, distancia al nivel, recoveries en el nivel en los 10 s previos.
   No cuantiles por sesión completa ni climas STOP.
5. Muestra GC disponible sólo smoke de ejecución/schema, no evidencia MNQ ni selección
   de features/thresholds. Nada de retornos, destinos de precio, MFE/MAE.

## Fuentes / bloqueo

Raw MNQ está en la PC (E:\l2_parquet), no encontrado como L2 en Kaggle My.
Sólo se encontraron ticks MNQ y GC L2/NQ-contextos. No sustituir L2 real por labels
de climas ni por L1. Se requieren sesiones del catálogo y manifests/hash reales.
Datos propios NT8, no Lucid. Un proceso pesado, outputs local-only y una worktree propia.

## Filtro y protocolo financiero — BORRADOR, no correr

Una hipótesis de defensa repetida, no grilla: >=2 recoveries compatibles del
mismo lado/precio en 10 s, todos publicados antes de la decisión. Es una propuesta
numérica previa a MNQ, no un filtro validado ni una etiqueta de absorción.
Si casi no hay eventos/support, STOP por potencia, no ampliar radio/ventana.
Spread/imbalance son diagnóstico y control, NO filtros alternativos testeados por P&L.
Comparar estrategia sin filtro vs misma estrategia filtrada, por sesión, con costos
MNQ propios. La comisión no se reduce por filtrar; debe mejorar la selección neta.
SL=28 ticks, TP=2R, BE=ninguno propuestos por convención fija (2×SL base 150t);
no elegidos como la mejor celda. Requieren aprobación expresa antes de retornos.
Señales desde L1 propio, sin unión no certificada con .Last.txt.
52 sesiones catálogo: primeros 17 desarrollo mecánico; siguientes 35 para validación
sólo tras congelar versión y OK. Son desarrollo pre-holdout, no confirmación oct+.
No bootstrap iid por episodio. MDE por sesión, reentrada y control geométrico a fijar
en el manifiesto final tras inventario target-free, antes de abrir destinos de precio.

## Espejo — línea aparte, todavía semántica pendiente

Hipótesis sugerida: desde B hacia A (segundo impulso), en el primer cruce de 50 %
de |B−A|, L2 aporta sobre geometría/velocidad/spread para anticipar llegada a A.
25 % sólo candidato de diseño, NO otra búsqueda abierta. Registrar todos los
intentos desde un B confirmado causalmente, incluidos los que nunca forman espejo.
Helper de landmarks implementado y probado sin calcular destinos reales.
No usar A/B finales retrospectivos, ni la muestra de 80 espejos completos para
certificar predicción de formación. Qué es A/B causal requiere congelación local.
Sin autorización de outcomes esta línea no se ejecuta sobre precios futuros.