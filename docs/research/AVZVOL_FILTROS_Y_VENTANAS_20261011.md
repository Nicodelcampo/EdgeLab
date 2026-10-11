# AVZVOL: filtros justificables y verificación de toda la ventana O5

## Decisión antes de filtrar

**No buscar filtros hasta que el efecto «vuelva a ser fuerte».** Un contexto
predefinido puede tener una señal distinta, pero elegirlo después de mirar O5
produce selección de resultados. Mejor magnitud no equivale a mayor validez.

Se ejecutó el primer chequeo de calidad legítimo con los exports existentes:
verificar **cada una de las 200 barras posteriores**, no sólo el extremo.
Resultado: **0 / 539.759 O5 finitos tienen las 200 etiquetas exactas de sesión
observables en los exports**. Los 539.759 quedan con cobertura parcial/desconocida;
cero contradicciones internas y cero ambigüedades observadas.

**Esto no demuestra que las ventanas estén rotas ni que el efecto sea nulo.**
Los exports guardan eventos/anchors, no cada barra; faltan anotaciones, no se
ha demostrado que falten ticks. No hay con estos archivos un subconjunto cuya
ventana completa pueda declararse validada mediante este criterio.

## Corrida real de QA, sin búsqueda de efectos

Se usan los mismos seis exports fijados de la [auditoría](../infra/AVZVOL_AUDIT_20261010.md),
544.531 filas y 4.772 O5 faltantes conservados. Sólo se lee el O5 existente para
identificar finitud; su magnitud no interviene en ninguna regla ni se recalcula.
No raw ticks, precios, nuevo outcome, holdout, P&L o certificación.

Por contrato se construye el mapa exacto `t0 -> conjunto de etiquetas session`
con todas las filas ya expuestas. Para cada O5 finito se buscan **todos** los índices
incluidos `[te+1, te+200]`:
- Una contradicción unívoca observada se informa como contradicción interna.
- Una etiqueta conflictiva se conserva como ambigua, sin elegir la favorable.
- Sólo 200 índices distintos, todos unívocos y coincidentes con la sesión propia,
  dan cobertura completa de anotaciones posteriores.
- Cualquier índice sin anotación produce cobertura parcial/UNKNOWN: no interpolación,
  relleno desde vecinos, deduplicación de casos favorables ni tratamiento como cero.

| Contrato | O5 finitos | Ventanas con las 200 etiquetas | Máximo de barras anotadas por ventana |
|---|---:|---:|---:|
| `MNQ_09-25` | 55,852 | 0 | 55 / 200 |
| `MNQ_12-25` | 106,064 | 0 | 41 / 200 |
| `MNQ_03-26` | 93,201 | 0 | 49 / 200 |
| `MNQ_06-26` | 102,857 | 0 | 37 / 200 |
| `MNQ_09-26` | 147,329 | 0 | 54 / 200 |
| `MNQ_12-26` | 34,456 | 0 | 64 / 200 |

De las filas finitas, **20.776** no tienen ninguna barra posterior anotada;
**518.818** tienen entre 1 y 49; **165** tienen entre 50 y 199; **ninguna** tiene 200.
La mayor cobertura observada es 64/200. Son cuentas de filas evento×celda,
no sesiones/eventos independientes. Duplicados de reemplazo no crean barras.

La [revisión del extremo](AVZVOL_O5_ROBUSTNESS_20261010.md) retenía 19.466 filas
(3,61%) con etiqueta final coincidente. **Ese subconjunto no acredita el interior
de la ventana**: aquí se verifica toda la secuencia y ninguna tiene cobertura completa.
No se convierte -7,94% del subconjunto en efecto «corregido».
Los resultados y excepciones de la revisión anterior permanecen intactos.

Incluso una eventual ventana con 200 etiquetas coincidentes sólo probaría
consistencia interna del export. No adjudicaría reloj/calendario independiente,
continuidad de ticks, consumo histórico, prewindow ni control causal.
Este auditor **no resuelve ni corrige el desfase `te+199`/`te+200` del guard original**;
comprueba la disponibilidad de anotaciones para una revisión, sin modificar outputs.

## Qué filtros corresponden y qué debe quedar pendiente

### 1. Calidad e identidad: resolver por evidencia, no por O5

- Misma fuente/versión/hash y transformación de barras acreditados; calendario,
  reloj, continuidad, quotes y selección contractual D-1 revisados independientemente.
- Mapa completo de barras con índices/timestamps/sesión; verificar todas las barras
  pre y post, incluido el último índice; no inferir el inicio previo desde `t0`.
- Registrar cada exclusión/UNKNOWN por regla y contrato/sesión/celda/kind,
  antes/después y causa concreta. Un faltante no prueba corrupción ni efecto cero.
- Completitud posterior y salida observada son condiciones conocidas a futuro:
  **no features causales disponibles al ancla**. Exigen población condicional y
  ledger de censura; eliminarlas puede seleccionar supervivientes. No vender el
  subconjunto de horizontes completos como población original sin ajuste/protocolo.

Estos son requisitos de revisión. No conceden por sí mismos permiso ni fabricación
de un certificado PASS. Los pins/certificaciones y censura aprobados siguen pendientes.

### 2. Mecanismo y comparabilidad: candidatos previos al ancla, no filtros ganadores

El [diseño existente](../../specs/research/avzvol_incremental_design_v1.json) ya exige
comparar mismo contrato, sesión, celda, franja de reloj y signo de tendencia;
ocupación, amplitud, tendencia/momentum, volumen/actividad y duración previos.
Son covariables para construir comparabilidad y probar heterogeneidad, **no una
lista de umbrales a barrer para elegir el mayor O5**.

Los snapshots deben existir y estar disponibles al ancla. No reutilizar estados
finales mutables ni pertenencia futura de zonas/racimos. «No figura racimo» no
prueba negativo calibrado; falta de bloques o baseline conserva UNKNOWN.

Escalas, bins, calipers, cortes de intensidad/duración, soporte/balance y familia
formal siguen **no congelados**. No agregar defaults arbitrarios. Determinarlos
por justificación externa/diseño outcome-blind y versionarlos antes de medir
el nuevo contraste; el desarrollo ya visto no vuelve a ser preregistrado.

### 3. Prácticas que no se aplicarán

- Quitar `4_250_20` porque revierte o `8_1000_30` porque era positiva.
- Sacar MNQ_09-25 porque casi pierde magnitud en la sensibilidad.
- Barrer umbrales, celdas, franjas o contratos y publicar sólo el mejor subconjunto.
- Cambiar el detector o prewindow y mantener la misma identidad de experimento.
- Tratar UNKNOWN como negativo/ausencia de zonas o como control elegible.
- Llamar a una revisión expuesta réplica independiente, significancia o causalidad.

Conservar universo completo, excepciones y todos los intentos. Si se ensayan
contextos exploratorios, registrarlos como exploratorios, sin aceptación formal,
y diseñar después una prueba independiente bajo sus permisos; no abrir holdout.
El panel descriptivo previo de 31 celdas y el grid original no se estrechan aquí.

## Siguiente paso de las cuatro propuestas, sin economía

- **P1:** obtener/reconciliar mapa completo bajo fuente y transformación revisadas;
  implementación nueva de guard completo con identidad distinta y ledger de revisión.
  El chequeo actual no puede producir ese mapa a partir de anchors dispersos.
- **P2:** censo causal de consolidaciones/negativos calibrados y controles contra
  su propio censo, matching y ledger de soporte/censura fijados antes del efecto.
- **P3:** mantener O5 y separar respuesta en tiempo físico; endpoints y presupuesto
  formal aún pendientes. Más filtros en barras no reemplazan esa comparación.
- **P4:** permanece prohibida. Sin outcomes económicos, P&L o costos.

Fuentes actuales de Kaggle mantienen sus bloqueos; no nuevo dataset/kernel ni
promoción. Sin mapa y revisión independiente suficiente, **no declarar el efecto
real/causal validado ni afirmar que filtrar necesariamente lo recuperará**.
Esto es una limitación identificada, no una decisión de abandonar la hipótesis.

## Reproducir y revisar

[Evidencia agregada completa](../../config/research/avzvol_o5_postwindow_export_audit_20261011.json).
La receta conserva una carpeta nueva y exige opt-in; verifica los seis footers y
SHA antes de cualquier payload. Dos implementaciones independientes coinciden:
vectorizada con searchsorted/prefix sums y diccionarios/sets/bisect, para todas las filas.
No se publican arrays privados, fechas fila a fila, testigos ni raw.

```bash
python tools/audit_avzvol_o5_postwindow_labels.py \
  --audit-reference docs/infra/AVZVOL_AUDIT_20261010.json \
  --audit-reference-sha256 1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e \
  --inventory exports-locales.json --out-dir carpeta-nueva \
  --allow-exposed-output-audit
```

Índice local: seis rutas explícitas `[{"file":"/ruta/export.parquet"}]`.
Tests sólo inventados: último índice aislado, 200 completos, falta en cada límite/interior,
contradicción interior aunque último coincida, etiquetas ambiguas/repetidas, overflow,
holdout, preflight global del último archivo con Python -O, opt-in y no sobreescritura.
Pruebas de software no certifican el origen ni convierten UNKNOWN en una ventana válida.

## Validación del lote

684 tests +25 subtests CPU; 19 tests nuevos de anotaciones inventadas, 18 de
navegación y catálogo sin errores. Verificación numérica independiente de todas
las ventanas finitas. La integración remota requiere checks del head exacto
y árbol verificado; esos checks no acreditan verdad científica del raw.
