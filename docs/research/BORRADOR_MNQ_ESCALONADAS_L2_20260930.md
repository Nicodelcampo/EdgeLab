# BORRADOR — MNQ escalonadas 150t × defensa L2

**DRAFT / NO AUTORIZADO PARA OUTCOMES.** No se ejecutó retorno, P&L, MFE/MAE ni costo.
Pedido de Nico: preparar todo desde nube por pocos créditos de Claude. Este pedido
de preparación no se toma como aprobación de parámetros/partición financiera.

## Hipótesis y objeto

Defensa repetida local, conocida antes de decidir, agrega valor sobre escalonadas
PLANAS MNQ 150t. No se usan climas STOP ni se presume un edge previo demostrado.
No replica el caso favorable escogido en febrero ni selecciona la mejor de 648.

Geometría: precio confirmado, ES ×12,42, w2, max_gap15, escalón25, retroceso62,
nmin3, dmax35, X25 ticks (el CLI escala también confirmación). Nuevo emisor
incremental; prueba de paridad geométrica por prefijo, sin geometría futura de
una serie ya terminada.

Disponibilidad: cierre de la vela de confirmación 150-LAST + fin del grupo de
timestamp. **Esta convención conservadora difiere de fills intrabar del estudio
previo**. No mezclar su resultado con el anterior.

## Única propuesta de filtro

En `det_nivel_tick`, mismo lado del libro que el pico (H=ask, L=bid):
>=2 recuperaciones compatibles ya publicadas en los 10 s anteriores y cantidad
visible actual positiva. Misma definición mecánica P0: prints al mismo precio
en 2 s, no futuros, crédito no reutilizado, recuperación >=70 % dentro de 5 s.
Es una feature provisional, NO iceberg/absorción certificados.

Libro válido/bootstrapped indispensable. Falta de libro o nivel fuera del top10
no cuenta como «sin defensa»: mask null, población desconocida por separado;
se publica por separado y no se descarta silenciosamente para subir el neto.
Imbalance, spread y distancia al nivel se exportan como diagnóstico/control, no
ejes de una grilla de P&L. No barrer ventanas, radio de precios ni umbrales después
de ver métricas financieras.

## Mecánica financiera propuesta (pendiente de OK)

- Dirección: H corto, L largo.
- Entrada a mercado en el primer LAST **posterior a `available_row`**, con bid/ask
  conocido hasta esa fila. No regresar al disparo intrabar. Estado de orden/fill
  siempre se separa del estado de señal.
- SL28 ticks, TP56 ticks (2R), BE apagado, máximo30min o fin de sesión.
  SL28 es 2×SL base150t; no la celda ganadora. Parámetros nuevos de esta propuesta.
- Una posición simultánea por sesión; todas las señales suprimidas por ocupación
  se cuentan, igual en baseline y filtrada. Se define el event-space completo antes.
- Spread incorporado por lados ejecutables; stop al lado ejecutable tras el cruce,
  con gaps/deslizamiento observados, nunca garantizar el nivel teórico.
- TP límite exige penetración1 tick. Es modelo de fill, no cola certificada por MBP.
- Escenario de comisión+fees3 ticks ida/vuelta heredado del estudio previo,
  **no afirmación de tarifa real del broker**. Nico debe ratificar/reemplazarlo
  antes del congelamiento. No se ensayan tarifas para encontrar positivo.
- Baseline idéntica sin filtro; control de selección aleatoria de igual número
  de señales en los mismos estratos sesión/dirección/franja30min/volatilidad
  previa. Cortes de volatilidad sólo del tramo de desarrollo, no sesión futura.
  Su soporte se audita target-free antes de abrir resultados.

## Población, inferencia y decisión

Catálogo MNQ09-26: 52 sesiones, primeros17 para QA/desarrollo target-free,
siguientes35 para una evaluación financiera sólo después de congelar y recibir OK.
No se calculan retornos del desarrollo para escoger parámetros. Mismo feed L1/L2;
no join por cercanía a `.Last.txt` ni extrapolar resultados ago2025–ene2026.
Todos estos datos son desarrollo pre-holdout; confirmación oct+ sigue sellada.

Dos criterios coprimarios, no 648 celdas:
1. expectativa R neta de filtrada >0;
2. diferencia R neta de filtrada frente al control de selección >0.

Bootstrap por sesión, 5.000 remuestreos con pesos comunes; corrección familiar de
los dos criterios y MDE por sesión publicados. Señales correlacionadas no cuentan
como sesiones independientes. Publicar baseline, filtered, conteos/no-fills,
exposición y costo además de media R; no ocultar que filtrar cambia la población.
Soporte mínimo propuesto: 30 operaciones y 8 sesiones evaluables en filtrada y
control; falta de soporte => INCONCLUSO, no ampliar ventana/filtro.

STOP/no promoción si costos no ratificados, causalidad/alineación falla, soporte
insuficiente o alguno de los dos criterios no supera su umbral. No abrir oct+
como rescate. Antes de ejecutar, versión ejecutable financiera, seeds/control,
regla exacta de corrección/MDE y hashes deben estar congelados y aceptados por Nico.
**Este archivo no es ese congelamiento final ni existe aún un runner financiero aprobado.**

## Pendiente inmediato mínimo

Un comando local exporta primero una sesión MNQ con datos propios. Nico sube el ZIP
derivado privado; la sesión nube analiza QA/support y prepara el congelamiento final.
Claude no necesita escribir código ni correr una nueva investigación.