# AVZVOL / MNQ — QA física de seis fuentes candidatas

**PASS_RAW_STRUCTURE_ONLY; revisión de calidad de fuente ABIERTA.** No es certificado
causal, de liquidez, de ausencia de sesgo ni attestation del consumo histórico.
[Registro completo con pins, métricas y bloqueos](../../config/research/avzvol_mnq_raw_quality_review_20261010.json).
No se calcularon outcomes económicos, P&L, señales, nuevos contrastes ni hipótesis.
Se leyeron precios/quotes sólo para QA estructural; el diagnóstico de cobertura
adicional leyó únicamente timestamps. No ocultar esa distinción.

## Qué se comprobó ahora

Descarga vía Kaggle MCP de versiones exactas. SHA256, bytes y filas concuerdan con
los pins previamente declarados para los seis archivos. Barrera global: todos los
hashes y footers verificados antes de deserializar el primer payload. Todas las
row groups terminan antes de 2026-09-30T22:00:00Z (inicio de trade date holdout
2026-10-01 en Chicago). No se abrió payload holdout ni se reescribieron originales.

Canonical v1: MNQ 09-25, 12-25 y 03-26. Reexport 20261005 v2: MNQ 06-26, 09-26 y
12-26. Son candidatos recuperados de AVZVOL; **no reemplazan el contrato portable
ES/NQ ni demuestran los mounts de las corridas originales**.

| Contrato | Versión | Filas completas | Filas 16–17 CT | Filas cierre semanal de referencia |
|---|---|---:|---:|---:|
| MNQ_03-26 | 1 | 103,921,542 | 8 | 15 |
| MNQ_06-26 | 2 | 116,002,246 | 2 | 3 |
| MNQ_09-25 | 1 | 34,508,845 | 22 | 26 |
| MNQ_09-26 | 2 | 110,632,331 | 0 | 0 |
| MNQ_12-25 | 1 | 99,091,418 | 14 | 25 |
| MNQ_12-26 | 2 | 21,440,578 | 1 | 0 |

Total: **485.596.960 filas; cero errores en los controles estructurales aplicados**:
nulos obligatorios, retrocesos temporales, precisión, precios/quotes/volumen no
positivos, book cruzado, identidad incorrecta, agresor inválido y duplicación de
identidad local de origen. No es prueba de exactitud contra el feed original.

Advertencias conservadas: 298.243.543 timestamps repetidos (no deduplicar por tiempo),
562 books locked y 659 agresores no clasificados. No hay discontinuidades en la
secuencia local, pero ésta no prueba continuidad del exchange.
`ts_local_ns == ts_utc_ns` en todas las filas; un campo copiado no acredita timezone.

## Cobertura y definición de gaps

Los conjuntos de fechas, counts y extremos first/last concuerdan con los JSON del
productor. No hay discrepancias entre counts raw de sesiones candidatas aprobadas
y resolver v15. Reconciliar documentos de la misma fuente **no prueba completitud**.

Había 12 diferencias entre el máximo gap **sin filtrar** y `max_gap_s` declarado.
Se revisaron 16 casos (unión de fechas distintas y fechas con prints 16–17 CT):
todos concuerdan bajo la definición encontrada en el builder candidato fijado en
[f397a318 / build_es_ext_2026q3.py](https://github.com/Nicodelcampo/EdgeLab/blob/f397a318be8b0acf68789070fe8064d83e172f7d/tools/build_es_ext_2026q3.py).
No está probado que ése sea el productor histórico exacto de MNQ.

Definición: calcular diferencias de timestamps adyacentes **originales** y excluir
la diferencia si su extremo derecho cae entre 16:00 y 17:00 Chicago. NO equivale a
eliminar filas de esa banda y luego recalcular gaps. Se comparó con tolerancia de
1 microsegundo sólo por redondeo numérico, no como umbral de calidad.

Ejemplo MNQ 03-26, trade date 2026-02-05: 597,2263972 segundos entre 15:59:59 y
16:09:56 CT; cruza la pausa de referencia. No presentarlo como un hueco de diez
minutos durante mercado abierto. El resumen declara 8,236 s bajo su filtro.
Tampoco basta el filtro para afirmar que no existen huecos: falta calendario
histórico revisado y referencia upstream independiente.

Hay 47 filas en la banda 16–17 CT, en 21 minutos×contrato observados. La referencia
semanal simple (sábado; domingo antes de 17; viernes desde 16) marca 69 filas,
4 en sesiones candidatas aprobadas. **Referencia, no calendario histórico
certificado ni cuarentena automática**: cierre, reloj y procedencia deben revisarse.
No se borró ningún print ni se promovieron silenciosamente sesiones/contratos.

## Cómo reproducir y qué falta

Usar los pins del registro JSON, nunca `latest`; preservar privacidad/licencia.
El auditor existente es `tools/audit_kaggle_raw_ticks.py`:

```bash
python tools/audit_kaggle_raw_ticks.py \
  --path "$RAW_FILE" --expected-sha256 "$PIN_SHA256" \
  --expected-bytes "$PIN_BYTES" --expected-rows "$PIN_ROWS" \
  --instrument MNQ --contract "$CONTRACT_WITH_SPACE" \
  --include-clock-diagnostics --out-dir "$NEW_EVIDENCE_DIR"
```

Fijar dependencias CPU; verificar primero TODOS los seis hashes/footers contra el
holdout, no sólo el archivo individual del CLI. El registro describe el método
adicional de timestamps y preserva los casos del diagnóstico; no confundirlo con
una nueva certificación de calendario. Exit 0 significa sólo estructura.

Pendientes: evidencia upstream de timezone/quotes/agresor/continuidad; calendario
con aperturas/cierres históricos; liquidez del contrato líder versus challengers,
roll causal y warmup de 45 días; consumo histórico físico; pares/pesos/solapamientos
AVZVOL y protocolo científico aprobado. Los `reviewed_input_pins` siguen vacíos.
R7/K8 permanecen abiertos. P1 tiene QA técnica avanzada, no revisión cerrada.

[Cuatro propuestas y bloqueos](../../config/research/avzvol_followup_proposals_v1.json):
P1 método/procedencia; P2 controles apareados y su censo; P3 O5 y tiempo de reloj;
P4 documentada pero **prohibida por instrucción vigente del usuario**. No inferir
permiso económico desde un PASS técnico ni desde una autorización anterior amplia.
