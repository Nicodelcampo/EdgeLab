# AVZVOL: de la geometría histórica a una confirmación observable

## Resultado y decisión

**La siguiente pregunta útil no es qué filtro hace positivo el resultado antiguo: es si una confirmación observable tras el retest distingue continuación de reentrada. Esa pregunta todavía no está medida.** El paso anterior orientó H2 frente a H3, pero no probó ninguna de las dos.

Esta revisión verificó nuevamente los seis exports fijados, con **544.531 filas representadas por sus footers**. Ninguno conserva el registro de retest y nueva confirmación necesario para evaluar directamente esa decisión. Es un faltante de observabilidad, **no 544.531 operaciones fallidas ni 544.531 eventos independientes**, ni invalidación de los endpoints históricos.

Sólo se inspeccionaron hashes, schemas y footers. **Cero payloads de columnas**, cero outcomes nuevos, cero P&L, cero holdout. Las cuentas por archivo coinciden por tres vías: footer del archivo, suma de row groups y pin original. No se han releído O3 ni seleccionado casos por sus resultados.

## Qué existe y qué no

Los schemas preservan `t0`, `L`, `H`, `h`, `te`, `dir`, O2/O3 y covariables del ancla. La presencia de esos nombres no acredita as-of de formación ni temporalidad del contexto en otra decisión. La semántica ya revisada muestra que O3a codifica si se observó un retest y O3b qué barrera posterior se tocó primero; no guardan el retest como evento con timestamp/cierre de confirmación.

| Información | Estado en los seis exports | Por qué importa |
|---|---|---|
| Identidad/versionado de banda y cuándo fue conocida | `L/H` presentes, snapshot causal no registrado | No usar el racimo final para definir una oportunidad anterior |
| Barra y disponibilidad UTC del retest | No registradas | El código de desenlace no dice cuándo podías tomar la decisión |
| Barra, política y disponibilidad UTC de confirmación | No registradas | Tocar no equivale a rechazo; volver dentro no equivale a continuar |
| Cierre observable en la nueva decisión | No exportado | No hay precio de confirmación conservado; tampoco fill |
| Contexto con identidad y tiempo de la nueva decisión | No registrado | `trend`/`mom100_h` del ancla no son indicadores recalculados en el trigger |
| Censo propio y clasificación as-of del control | No registrados | Pseudo legacy no acredita ausencia de zona ni comparación incremental limpia |

La auditoría informa ausencia de **nombres exactos del contrato propuesto**, no intenta certificar cualquier esquema alternativo. La conclusión sobre retest/confirmación también se apoya en la semántica del estudio anterior, no sólo en cómo se llaman las columnas. Un mapa de timestamps puede vincular índices existentes como `t0/te`; no puede recuperar un índice de retest/confirmación que nunca se exportó sin una reconstrucción nueva. Los ticks podrían permitir esa reconstrucción; esta revisión **no los abre ni certifica** y no habilita su replay.

## Contraste que conviene preparar

Secuencia conceptual, **no algoritmo científico congelado ni recomendación operativa**:

1. **Banda conocida:** snapshot de geometría y momento de disponibilidad, preservando actualizaciones.
2. **Salida observada:** cierre completo fuera de la banda; desde ahí se conoce su lado. H1 es referencia, no decisión al nacimiento de la zona.
3. **Retest observado:** guardar el contacto como evento, sin llamarlo automáticamente rechazo, entrada ni éxito.
4. **Nueva decisión observable:** distinguir cierre del lado de salida, cierre de vuelta dentro y estado desconocido. La definición final de rechazo/aceptación, orden dentro de la misma barra y confirmación requiere política aparte; ningún número de cierres o buffer fue elegido aquí.
5. **H2 vs H3 vs H1:** comparar desde sus propios instantes de decisión, con contexto disponible entonces y controles equivalentes de censo propio. No sustituir esa evaluación por O3b medido desde otra referencia temporal.

**Recomendación de investigación:** priorizar la discriminación H2/H3 y mantener H1 como benchmark. No sabemos aún si la confirmación aporta ventaja: sólo sabemos que el toque aislado y las barreras antiguas no bastan para acreditarla. No invertir automáticamente la ruptura porque O2 falle.

## Producto concreto dejado listo

[Contrato de captura propuesto](../../config/research/avzvol_interaction_capture_v1.json): snapshots de banda, barras completas, interacción, decisión, contexto y control. Separa hora de cierre, hora de disponibilidad y secuencia de fuente. Un empate UTC sin orden acreditado debe conservar UNKNOWN; una ausencia de observación no se vuelve negativa.

[Auditoría reproducible](../../tools/audit_avzvol_trigger_observability.py): exige los seis pins originales y particiones expuestas anteriores al holdout; cruza row groups sin abrir payload. Rechaza archivo cambiado, población distinta, sesión desconocida/reservada y cuentas incompatibles. **Es inventario de captura, no validador semántico completo, motor de estados ni certificado de research.**

Los parámetros científicos permanecen **null**: buffers, definición de touch/rechazo/reentrada/aceptación, confirmación, espera, políticas intrabar y entre sesiones, horizonte de reloj, matching, censura, familia y presupuesto. No se rellenan con defaults por conveniencia ni por resultados favorables. El contrato puede ampliarse/revisarse antes de aprobar una campaña.

## Qué falta para un resultado nuevo válido

- P1: revisión independiente de fuente, reloj/calendario/continuidad y exposición; hashes no sustituyen esa revisión.
- P2: snapshots de formación as-of y censo propio zone-free/control; preservar desconocidos y política entre sesiones.
- Captura de la secuencia y contexto en cada nueva decisión; aquí no se construyó cinta de mercado.
- P3: congelar pregunta y endpoint no económico desde confirmación, horizontes/censura/matching/soporte/inferencia antes de medir.
- Sólo luego ejecutar el contraste autorizado. P4 económico y holdout siguen cerrados; no se altera ninguna aprobación por esta auditoría.

No corresponde seguir probando filtros sobre los mismos resultados hasta conseguir un ganador. **La ausencia de este dato se resuelve registrando la decisión causal, no buscando un subconjunto con porcentaje alto.**

## Evidencia y reproducción

[Plan](avzvol_trigger_observability_20261011/analysis-plan.json), [evidencia por archivo y schema](avzvol_trigger_observability_20261011/evidence.json). El inventario privado contiene sólo rutas a los exports ya fijados; no se publica ni se incluyen enlaces firmados. Reproducción: `python tools/audit_avzvol_trigger_observability.py --inventory <inventario-local> --out-dir <directorio-nuevo> --allow-exposed-footer-audit`.

[Semántica de retest e hipótesis H1/H2/H3](AVZVOL_LOGICAS_DE_ENTRADA_20261011.md), [control comparability](AVZVOL_CONTROLES_COMPARABILIDAD_20261011.md), [gates científicos](../../specs/research/avzvol_incremental_design_v1.json). Se preservan resultados y evidencia históricos; esta revisión no añade efectos calculados ni significancia.
