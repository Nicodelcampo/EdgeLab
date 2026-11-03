# Programa: ventaja operable con potencia, medida en R (2026-11-03)

Estado: VIGENTE. Pedido de Nico: «el efecto requiere demasiada potencia para confirmarse». Hay que:
1. crear lógicas buscando diversificación y no correlación;
2. adoptar las mejores prácticas de medición;
3. investigar a fondo cómo mejorar el R promedio por operación;
4. crear variantes con lo mejor de cada estrategia sin perder potencia;
5. sumar lo que surja de leer el repo.

Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Diagnóstico (lo medido hasta hoy)
- **Medido en R, ninguna familia confirma sola.** 68 relanzadas: las 6 nominadas cayeron en integridad o en topes. Las mejores reglas
  rinden entre +0,05 y +0,2R por operación con unas 5 a 15 operaciones por mes. Para confirmar +0,1R con desvío ≈ 1R hacen falta ≈ 270
  operaciones por regla: años.
- **Las reglas son casi independientes** (Li-Ji 13/13, mediana |r| 0,06). **La potencia está en agruparlas, no en mirarlas de a una.**
- **Medir en puntos sobreestimaba:** CVGAP-NQ, CVGAP-CFD-NQ y U1-CRUZADO tenían la ventaja concentrada en los stops lejanos.

## 1. Crear lógicas para diversificar (prácticas)
- **Se diseña contra la cartera existente, no en el vacío.** Antes de lanzar una familia nueva se mide la correlación esperada de su P&L de
  desarrollo con la canasta v5 (`tools/correlacion_nominadas.py`, que se extiende a candidatas). Se priorizan familias con |r| < 0,1.
- **Fuentes de independencia, en orden de rendimiento observado:**
  - otro mecanismo: zonas de volumen, expansión de área, gap o corredor;
  - otro instrumento con su propia microestructura: ES y NQ contra GC, YM y FX;
  - otra franja horaria: Asia, Europa, EE.UU.;
  - otro sensor: CFD contra futuro, que en U1 mostró aportar.
- **Dirección y horizonte opuestos a lo que ya hay** (reversión contra continuación, intradía contra de un día para otro): bajan la
  correlación más que cambiar parámetros.
- **Las ideas transferibles** (`atlas_ideas_r_20261102/`) dicen qué componentes de ejecución funcionan en varias familias. Son los valores
  por defecto de una familia nueva.

## 2. Medir (prácticas, obligatorias desde hoy)
- **R por defecto** (`"estadistico": "R"`). Se informan además puntos y MAE. Declarar un piso de riesgo cuando la regla admite stops de 1–2
  ticks.
- **Código causal certificado:** candado en el lanzamiento y auditoría vela a vela de las reglas que van a la canasta.
- **Sesiones válidas únicamente** (`holdout.SESIONES_EXCLUIDAS_HOLDOUT`).
- **Potencia antes de decidir:** N fijo calculado en R. Si el N es inalcanzable en meses, la regla va a una canasta y no a una prueba
  individual.
- **Agrupar para tener potencia:**
  - canasta con prueba por sesión;
  - políticas comunes que se eligen en el conjunto (punto 3);
  - estimación con contracción hacia la media de la familia (empírico-bayesiana) para ponderar, nunca el máximo de una celda.
- **Forward con e-proceso,** que se puede mirar todos los días. Para pasar a REAL: e-proceso más R > 0.

## 3. Mejorar el R por operación (en curso)
- **Salidas y filtros comunes a las 8 reglas de la v5:**
  - `PREREGISTRO_SALIDAS_Y_FILTROS.md`;
  - 28 políticas: tiempo, objetivo fijo en R, break-even, trailing, stop corto y combinaciones;
  - 5 filtros: franja horaria y lado;
  - se elige en DESC agrupado y se prueba una vez en réplica agrupada;
  - insumo: la etapa `TRAYECTORIAS`.
- **Después, si la réplica confirma algo:**
  - dimensionar por calidad de la señal: R esperado según las variables de la celda, aprendido en DESC y probado en réplica;
  - salida por tiempo de parada (`simular_cierre_linea`, ya existente) en las familias de tendencia.

## 4. Variantes sin perder potencia
- **Una variante es la regla con la política o el filtro comunes confirmados.** No se elige una política distinta por regla, porque eso
  divide la muestra.
- **Celda congelada → vecindario:** promediar la celda con sus vecinas de meseta (en la grilla ya está `meseta`) da más operaciones y menos
  sobreajuste que la celda sola.
- **Ponderación de la canasta:** contracción del R de cada regla hacia la media de la canasta, ponderada por varianza.

## 5. Otros puntos (del repo)
- **Datos:**
  - exportar noviembre (Nico);
  - el 7 de octubre queda como sesión faltante: si aparece otra fuente de ticks CME, se re-sella.
- **Infraestructura:** los conductores y lanzadores se cortan a las 2 h. Se agregan chequeos programados que los retoman, y se evalúa un
  único conductor reanudable.
- **Pendiente de causa raíz:** el preflight de ruido de U1-6E-CONFIRMA-GBP-C-R, con 2 nominadas por el FDR sobre ruido.
- **Atlas de ideas:** completar las 136 corridas y analizar.

## Orden
1. Trayectorias (corriendo).
2. Salidas y filtros: DESC → réplica.
3. Atlas.
4. Ponderación de la v5 con contracción.
5. Variantes de la v5 a papel desde sesiones nuevas.
6. Familias nuevas guiadas por correlación y por el atlas.
