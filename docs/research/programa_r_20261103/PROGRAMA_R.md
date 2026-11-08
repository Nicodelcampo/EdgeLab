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

## Iteración 1 (2026-11-03): lo medido
1. **Mejorar el R con salidas o filtros comunes: no.** Ninguna de las 28 políticas ni de los 5 filtros confirma en réplica.
   - Cortar ganancias resta R en los dos tramos.
   - Ampliar el objetivo a 2R con stop corto da un poco a favor en los dos, sin significancia: queda como pista para familias nuevas.
   - Ver `PREREGISTRO_SALIDAS_Y_FILTROS.md`.
2. **La maldición del ganador, medida:** las canastas de pistas de 44 familias rinden −0,042R en su réplica no usada (z −4,9).
   - **No depende del tamaño de la grilla:** Spearman con log(celdas) +0,14, p 0,36; grillas de menos de 1.000 celdas dan −0,05R.
   - **El problema no es cuánto se busca, sino que estas lógicas no tienen ventaja neta fuera de muestra.** Elegir la mejor celda de una
     familia sin ventaja da cero menos costos.
3. **Consecuencia para crear lógicas (punto 1):** más grillas sobre las mismas ideas no ayuda.
   - Hacen falta **mecanismos nuevos con justificación económica**, medidos con pocas perillas, en R, y diseñados contra la correlación
     con la cartera.
   - Ganar potencia agrupando funciona para **medir**, no para **crear** ventaja.
4. **Lo que sigue en pie:**
   - la v5 (8 reglas con R > 0 en DESC y réplica), en papel con e-proceso desde sesiones nuevas;
   - la salida natural de las reglas, que no conviene recortar.

## Iteración 2 (2026-11-04): Atlas de Contexto Causal Común y Vetos Estructurales en R
- **Reporte completo y manual de referencia:** `docs/research/programa_r_20261103/RESULTADO_CONTEXTO_Y_VETOS_R_20261104.md` (pre-registro en `PREREGISTRO_CONTEXTO_Y_VETOS_R_20261104.md`, datos crudos en `contexto_marginales/RESULTADO.json`).
- **Infraestructura permanente incorporada:**
  - `edgelab/research/contexto_comun.py`: `atr_sesion` y `vwap_sesion` reiniciados en cada borde de sesión CME, hora NY con DST (`regimen_sesion.minuto_ny`), cuantiles móviles causales (`P33/P67/P90`) de las 20 sesiones cerradas previas (`calentamiento_dias = 40` en `embudo_main.py`), 7 variables `ctx_*` y 4 vetos estructurales `veto_*` orientados por el lado `s`, integrados en `STAGE_MARGINALES` (`grilla_generica.py`).
  - `nt8_tools/jforex/EdgeLabU1Cruzado.java`: paridad JForex ↔ Python agregando `maxDuracionMin = 240` y cierre diario `cierreNY = "16:59"` ET.
- **Lo confirmado en el Atlas (`135` campañas en R, `69` clusters independientes `(familia_base, activo)`):**
  1. **Ejecución colapsando `Futuro + CFD` (`K = 13` clusters):** `ejecución.stop=S3` confirma con `+0,1235R` en `DESC` ($p < 10^{-6}$) y `+0,1057R` en `REP` ($p = 4,4 \times 10^{-5}$), **13/13 (100 %) clusters positivos**; `ejecución.objetivo=T3` suma en **13/13** y `T1` resta en **13/13**.
  2. **Compresión intradía resta en todos los mecanismos:** `ctx_atr_rel=bajo` (`< P33` de 20 sesiones) resta **`-0,0793R` en `DESC`** ($p = 1,8 \times 10^{-5}$) y **`-0,0722R` en `REP`** ($p_{\text{uni}} = 0,0005$); `ctx_vol_rel=bajo` resta **`-0,0698R` en `DESC`** y **`-0,0631R` en `REP`** ($p_{\text{uni}} = 0,0024$). En cambio, `ctx_atr_rel=alto` (`+0,0380R` / `+0,0278R`) y `ctx_vol_rel=alto` (`+0,0289R` / `+0,0240R`) suman.
  3. **Ventana horaria de reversión:** `ctx_hora_ny=ny_manana_0930_12` suma **`+0,0765R` en `DESC`** y **`+0,0585R` en `REP`** ($p_{\text{uni}} = 0,0078$) en `REVERSION`.
  4. **De «Muro» a «Imán Estructural» en reversión (`veto_muro=vetado`):** tener `VWAP`, `OR30` o `ONH/ONL/PDH/PDL` entre la entrada y el 75 % del recorrido hacia `T3` suma **`+0,0883R` en `DESC`** ($z = +4,93$, $p = 10^{-6}$, 87,1 % clusters $+$) y **`+0,0732R` en `REP`** ($z = +3,21$, $p_{\text{uni}} = 0,0007$, 77,4 % clusters $+$) en `REVERSION`. En reversión, los niveles de sesión no actúan como muros sino como **imanes de equilibrio**.
- **Evaluación en las 11 reglas (`DESC + REP`, $N = 1.161$ ops) y defensa contra sobreajuste:**
  - El Atlas evitó adoptar `veto_vol_diaria_baja`, que en las 11 reglas aparentaba `+0,0311R` (`LOMO 14/14`) pero en los 69 clusters del Atlas tuvo efecto nulo (`-0,0071R`, $p = 0,71$).
  - `atlas_veto_sin_iman_estructural` (exigir imán estructural hacia `T3`) es el único filtro que pasa el Atlas, supera el $\text{MDE}_{80\%}$ (`+0,0699R > +0,0677R`, llevando la cartera de `+0,1235R` a `+0,1934R`, `+0,0847R` en `DESC` y `+0,0574R` en `REP`) y pasa las 3 compuertas (`8/11` reglas, `LOMO 14/14`, $p_{\text{nulo}} = 0,0195$). Por tener signo opuesto a la dirección pre-registrada de `veto_muro`, queda congelado para validación prospectiva desde **noviembre 2026 (`202611+`)**.
