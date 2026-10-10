# AVZVOL: revisión exploratoria de O5 con los exports disponibles

**Se usaron los datos actuales, sin esperar nuevas subidas.** Identidad distinta:
`AVZVOL-EXPOSED-DESC-1`. Descriptivo, desarrollo ya expuesto, no confirmación ciega,
certificación de raw, prueba incremental limpia ni evidencia de rentabilidad.
Autorización del usuario: usar lo existente considerando faltantes y acreditar
lo verificable. No se habilita el release research ni se rellenan reviewed_input_pins.

## Resultado principal y excepción

La diferencia descriptiva O5 real − pseudo es negativa, en promedio, en los seis
contratos al dar igual peso a las **31 celdas computables en todos ellos**.
En el paisaje de las 36 definiciones: 35 permiten
un cálculo descriptivo en algún contrato, 34 medias de celda
son negativas y 1 positiva; `8_250_20` no es computable.
**No son 35 tests ni 35 réplicas independientes.** Se conservan todas las celdas,
incluidas las escasas; no se les atribuye la elegibilidad inferencial original.

La excepción es `8_1000_30` (mínimo 8 zonas, ventana nominal 1000 barras, altura
máxima 30 ticks): media entre contratos **+0.0282**,
positiva en 4 de 6 contratos.
Es una excepción observada después de inspeccionar el paisaje, NO una celda
prerregistrada ni ganadora a promover. Tampoco invalida por sí sola el resultado
original: el estimando y la población de esta revisión son distintos.

| Contrato | Gap medio, 31 celdas comunes (log) | O5 finitos / filas reales | O5 finitos / filas pseudo |
|---|---:|---:|---:|
| `MNQ_09-25` | -0.0611 | 9,660/9,816 | 46,192/46,822 |
| `MNQ_12-25` | -0.0635 | 18,912/19,143 | 87,152/87,955 |
| `MNQ_03-26` | -0.0710 | 16,847/17,039 | 76,354/77,127 |
| `MNQ_06-26` | -0.0606 | 18,364/18,524 | 84,493/85,061 |
| `MNQ_09-26` | -0.0970 | 25,953/26,139 | 121,376/122,290 |
| `MNQ_12-26` | -0.0488 | 6,056/6,094 | 28,400/28,521 |

Una diferencia negativa significa menor **ratio de rango posterior/anterior**
para los reales en esta comparación de exports; no prueba menor rango absoluto,
volatilidad a tiempo fijo, reversión, menores colas ni efecto causal de zonas.

## Cómo se calculó y qué se conservó

1. Verificar schema/rows y estadísticas de sesión de TODOS los seis footers:
   etiquetas estrictamente anteriores al holdout `20261001`. Comprobar TODOS
   los hashes contra la auditoría fijada antes de leer payload de eventos.
2. Leer sólo contract/cell/kind/session/t0/te/o5. No ticks, futuros precios,
   P&L, nuevo endpoint ni recálculo de O5 desde mercado.
3. Dentro de contrato × sesión × celda, media del O5 finito de reales menos media
   del O5 finito de pseudo. No emparejamiento por evento ni reconstrucción de pares.
4. Igual peso a cada sesión con ambos grupos finitos dentro de contrato/celda.
   Para la tabla/figura de contratos, igual peso a las 31 celdas comunes;
   para el paisaje completo, igual peso a los contratos computables por celda.
5. Mantener duplicados pseudo: su muestreo fue con reemplazo. No deduplicar,
   ampliar calipers, imputar O5 ni elegir filas según su signo.
6. Conservar las cuatro celdas sin soporte común en todos los contratos y la celda
   totalmente no computable en los CSV/tablas, no imputarlas al gráfico común.

O5 conserva la receta histórica en barras de **25 trades**: log del rango de 200
barras después de la primera salida sobre el rango de 200 barras anteriores a la
primera zona del racimo; el numerador original tiene floor de 1 tick. No se cambia
el denominador por uno previo a t0. La definición/ventanas/clock/calendario de los
exports no quedan validadas por esta agregación. Se reutilizan también los antiguos
exports de confirmación como datos EXpuestos, nunca como nueva confirmación.
La receta de reproducción se fija para este lote; **no fue prerregistrada a ciegas**.

## Faltantes y cobertura: no se ocultaron

- 544,531 filas evento×celda: 96,755 reales y 447,776 pseudo;
  no equivalen a eventos independientes ni a todos los eventos del mercado.
- 539,759 O5 finitos y **4,772 faltantes**.
- 287 faltantes tienen `te < 0` (sin salida registrada);
  **4,485** tienen otra causa no distinguible por estos exports.
  No atribuirlos automáticamente a huecos de ticks, ni a censura/horizonte incompleto.
- 6,057 grupos sesión×celda con ambos tipos finitos;
  1,926 sin soporte: 60 sólo real,
  1,834 sólo pseudo y 32 sin ninguno finito.
  Todos permanecen en el accounting; sólo los soportados entran al contraste.

## Qué se acreditó y qué no

Acreditado **ahora para los exports**: identidad de bytes, rows/schema, etiquetas de
partición preholdout y aritmética. Se recomputaron los 199
gaps contrato/celda por NumPy + math.fsum, sin usar las medias pandas; error máximo
3.47e-17. Totales y finitud recomprobados con Arrow.
El profiler genérico falló al interpretar Parquet como texto; se sustituyó por
perfil técnico Arrow, no se calificaron los archivos como corruptos ni se cambiaron.

NO acreditado: captura/export/timezone, calendario/continuidad completa, liquidez
causal y warmup del raw, montaje histórico, ni ausencia de racimos en controles.
Los pseudo son controles legacy de actividad/ocupación; no un censo sin zonas
revisado. Un resultado de estos exports NO permite certificar las fuentes ni
medir el sesgo que producirían los faltantes upstream.
No p-values, intervalos, potencia ni inferencia; no independencia entre celdas,
contratos sucesivos, pares reutilizados o eventos solapados. No nuevo kernel,
release, promoción ni cambios de resultados/ledgers históricos. P4 sigue prohibida.

## Paisaje completo: 36 celdas, sin elegir por signo

| Celda | Contratos computables | Gap descriptivo medio (log) | Contratos negativos / positivos |
|---|---:|---:|---:|
| `4_250_20` | 6 | -0.0949 | 6 / 0 |
| `4_250_30` | 6 | -0.0687 | 5 / 1 |
| `4_250_45` | 6 | -0.0857 | 6 / 0 |
| `4_500_20` | 6 | -0.0561 | 6 / 0 |
| `4_500_30` | 6 | -0.0705 | 6 / 0 |
| `4_500_45` | 6 | -0.0718 | 6 / 0 |
| `4_1000_20` | 6 | -0.0358 | 6 / 0 |
| `4_1000_30` | 6 | -0.0540 | 6 / 0 |
| `4_1000_45` | 6 | -0.0641 | 6 / 0 |
| `5_250_20` | 6 | -0.1503 | 6 / 0 |
| `5_250_30` | 6 | -0.0999 | 6 / 0 |
| `5_250_45` | 6 | -0.0896 | 6 / 0 |
| `5_500_20` | 6 | -0.0824 | 6 / 0 |
| `5_500_30` | 6 | -0.0615 | 6 / 0 |
| `5_500_45` | 6 | -0.0723 | 6 / 0 |
| `5_1000_20` | 6 | -0.0685 | 6 / 0 |
| `5_1000_30` | 6 | -0.0447 | 6 / 0 |
| `5_1000_45` | 6 | -0.0675 | 6 / 0 |
| `6_250_20` | 5 | -0.1600 | 4 / 1 |
| `6_250_30` | 6 | -0.1118 | 5 / 1 |
| `6_250_45` | 6 | -0.1039 | 5 / 1 |
| `6_500_20` | 6 | -0.0624 | 6 / 0 |
| `6_500_30` | 6 | -0.0508 | 5 / 1 |
| `6_500_45` | 6 | -0.0788 | 6 / 0 |
| `6_1000_20` | 6 | -0.0613 | 5 / 1 |
| `6_1000_30` | 6 | -0.0485 | 5 / 1 |
| `6_1000_45` | 6 | -0.0540 | 6 / 0 |
| `8_250_20` | 0 | — | 0 / 0 |
| `8_250_30` | 1 | -0.1592 | 1 / 0 |
| `8_250_45` | 5 | -0.0298 | 3 / 2 |
| `8_500_20` | 2 | -0.1532 | 2 / 0 |
| `8_500_30` | 6 | -0.0733 | 4 / 2 |
| `8_500_45` | 6 | -0.0226 | 5 / 1 |
| `8_1000_20` | 6 | -0.0742 | 4 / 2 |
| `8_1000_30` | 6 | +0.0282 | 2 / 4 |
| `8_1000_45` | 6 | -0.0251 | 5 / 1 |

## Reproducción y siguiente paso

[JSON de evidencia](avzvol_exposed_o5_review_20261010/evidence.json),
[36 celdas](avzvol_exposed_o5_review_20261010/all-cells.csv),
[contrato × celda](avzvol_exposed_o5_review_20261010/contract-cells.csv) y
[receta](avzvol_exposed_o5_review_20261010/analysis-plan.json).
La tabla privada por sesión no se publica. El índice contiene seis rutas explícitas
`[{"file":"/ruta/export.parquet"}]`; los pins provienen de la auditoría fijada.

```bash
python tools/review_avzvol_exposed_o5.py \
  --audit-reference docs/infra/AVZVOL_AUDIT_20261010.json \
  --audit-reference-sha256 1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e \
  --inventory exports-locales.json --out-dir carpeta-nueva \
  --allow-exposed-o5-review
```

Este comando es opt-in para revisión descriptiva de evidencia expuesta, no bypass
para ticks/holdout/research certificado. No sobrescribe carpetas de resultados.

El patrón de compresión relativa merece seguimiento, pero **no es universal ni
suficiente para promover un edge**. La prueba incremental P2 exige construir un
censo causal con las fuentes actuales que puedan justificarse, conservar UNKNOWN
y excluir ventanas por reglas de calidad/cobertura previas al outcome, no por el
mejor efecto. Sigue pendiente el benchmark de controles contra su propio censo.
P3 (tiempo físico) no se sustituye por O5. P4 continúa bloqueada.

## Validación de software del lote

587 tests +25 subtests en CPU; navegación 18 tests. Los siete tests nuevos usan
sólo exports inventados: faltantes, pesos, permiso explícito, hash/holdout,
protección incluso con Python -O y no sobrescritura. No prueban verdad del raw.
La figura canónica generada con preflight está conservada en
`avzvol_exposed_o5_review_20261010/avzvol_o5_notion_agent_chart.html`.
