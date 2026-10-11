# AVZVOL: robustez descriptiva del O5 ya expuesto

## Resultado principal y decisión

El gap geométrico ponderado real frente a **pseudo legacy** es **-6.48%**
(log-gap -0.067003308611) en las **31 celdas comunes a seis contratos MNQ**.
El signo agregado permanece negativo al eliminar cualquiera de los seis contratos
y en las **261 eliminaciones de una fecha observada completa**.
No parece depender de un único contrato ni de una única etiqueta de fecha.
Esto **no demuestra ausencia de sesgo, causalidad, rentabilidad ni réplica ciega**.

Hay dos límites importantes que no deben quedar detrás del promedio:
- La celda `8_1000_30` es positiva en el panel original: **+2.86%**.
  Son 30 celdas negativas y una positiva, no compresión universal.
- Con el filtro exploratorio de extremo anotado, `4_250_20` cambia de
  **-4.60%** a **+7.94%**
  en los mismos 29 grupos contrato/sesión/celda. Además, MNQ_09-25 casi pierde el gap.
  Esa sensibilidad impide describir el resultado como estable frente a todos los problemas de ventana.

**Conviene continuar con P1/P2 y después P3; no promover un edge ni abrir P4.**
La señal descriptiva justifica investigar, no resolver los criterios pendientes por el efecto que más convenga.

## Qué se midió (y qué no)

Se reutilizan los seis exports originales fijados por SHA y sus O5 existentes:
**544.531 filas; 539.759 O5 finitos; 4.772 faltantes sin imputar**.
No se calculan nuevos endpoints de precios, raw ticks, holdout ni outcomes económicos.
Los contratos son vencimientos/periodos del mismo MNQ, no seis mercados independientes.

O5 es el log del ratio original **rango posterior / rango previo en barras de 25 ticks**.
Dentro de contrato/sesión/celda se resta media O5 pseudo a media O5 real, sólo cuando
ambas existen; se ponderan igual las sesiones con soporte, luego celdas y contratos.
`exp(log-gap)` es una razón geométrica ponderada de esos ratios real/pseudo.
**-6,48% no significa un rango futuro absoluto 6,48% menor**, volatilidad a tiempo fijo ni ganancia.
El pseudo histórico no acredita ausencia de zonas/racimos ni constituye todavía un contrafactual causal emparejado.
Se conservan duplicados de reemplazo del pool y faltantes, sin convertirlos en nuevas observaciones independientes.

## 1. Eliminación de un contrato: mismo panel de 31 celdas

| Contrato eliminado | Gap geométrico relativo |
|---|---:|
| `MNQ_09-25` | -6.59% |
| `MNQ_12-25` | -6.55% |
| `MNQ_03-26` | -6.41% |
| `MNQ_06-26` | -6.60% |
| `MNQ_09-26` | -5.92% |
| `MNQ_12-26` | -6.82% |

Rango descriptivo de las seis eliminaciones: **-6,82% a -5,92%**.
Ninguna de las 31 celdas cambia su propio signo al eliminar un contrato.
[Figura de eliminaciones](avzvol_o5_robustness_20261010/contract_deletions_notion_agent_chart.html).

## 2. Eliminación de una fecha completa: mismo panel, sin achicar soporte

Se elimina cada etiqueta de fecha observada **en todos los contratos y celdas a la vez**.
Si una celda/contrato pierde soporte, el panel fijo debe marcarse no computable,
no se reemplaza por un panel menor. En esta corrida: **261 computables, cero no computables;
261 gaps agregados negativos y cero positivos**.
El gap relativo queda entre **-6.90% y -5.93%**.
Ninguna celda cambia su propio signo bajo estas eliminaciones.

Estas 261 etiquetas son las observadas en exports, **no un calendario completo de CME
certificado ni 261 pruebas independientes**. Los rangos no son intervalos de confianza.
No se calculan p-values, significancia, potencia ni nuevas confirmaciones.
El calendario y las tablas privadas por fecha no se publican.

## 3. Sensibilidad exploratoria al extremo anotado: población seleccionada

El guard histórico compara `te+199`, aunque el rango incluye `te+200`.
El [lote anterior](AVZVOL_DETECTOR_TAPE_AND_O5_BOUNDARY_20261010.md) mostró un cruce sintético
que pasa el guard. No se ha medido la frecuencia real de ese fallo.

Aquí se retienen únicamente O5 finitos cuyo último índice `te+200` tiene una etiqueta
**exacta y unívoca observada en los anchors `t0` del mismo contrato**, coincidente con
la etiqueta de sesión propia. Sin interpolación ni reconstrucción de precios.

Sólo **19.466 / 539.759 = 3,6064%** de los O5 finitos cumplen ese criterio.
Los restantes **520.293** tienen etiqueta final desconocida: **no son automáticamente
huecos de ticks ni cruces de sesión demostrados**. Cero etiquetas ambiguas observadas.
Conservados: 3.957 / 95.792 reales (4,13%) y 15.509 / 443.967 pseudo (3,49%).
Las proporciones distintas son otra advertencia de selección, no corrección de sesgo.
El filtro no certifica la ventana completa, ventana previa, calendario, reloj o liquidez,
y usa anotaciones retrospectivas; **no es una covariable causal**.

El panel original **31 celdas × 6 contratos NO ES COMPUTABLE** con esta restricción.
Nueve celdas pierden soporte completo: `5_250_20`, `6_250_30`, `6_250_45`, `6_500_20`, `6_1000_20`, `8_500_30`, `8_500_45`, `8_1000_20`, `8_1000_30`.
Incluye `8_1000_30`: sólo cuatro contratos conservan soporte, por lo que su
sensibilidad filtrada permanece **NOT_COMPUTABLE**, nunca cero ni negativa por defecto.

### Comparación secundaria válida sólo como sensibilidad

Se mantienen **22 celdas con soporte en los seis contratos**, en **1.816 grupos**
contrato/sesión/celda. Para comparar, se restringe también la base original a los
**EXACTOS MISMOS grupos** que soportan real y pseudo tras filtrar. Pesos iguales.

- Todos los O5 finitos dentro de esos mismos grupos: **-6.93%**.
- Sólo filas con extremo conocido dentro de esos grupos: **-7.94%**.

No comparar esta población seleccionada de 22 celdas con el -6,48% del panel completo
como si la población no hubiera cambiado. Tampoco llamar -7,94% al «efecto corregido».

| Contrato; mismas 22 celdas/grupos | Base de todos los O5 finitos | Sólo extremo conocido |
|---|---:|---:|
| `MNQ_09-25` | -5.55% | -0.44% |
| `MNQ_12-25` | -4.24% | -6.17% |
| `MNQ_03-26` | -10.40% | -12.85% |
| `MNQ_06-26` | -6.67% | -12.19% |
| `MNQ_09-26` | -8.35% | -8.25% |
| `MNQ_12-26` | -6.25% | -7.21% |

**MNQ_09-25 casi pierde la magnitud**, mientras MNQ_06-26 la aumenta.
No se atribuye el cambio a contaminación real: la selección de filas por disponibilidad
anotada puede producirlo. [Figura por contrato](avzvol_o5_robustness_20261010/endpoint_contracts_notion_agent_chart.html).

En las 22 comparaciones secundarias por celda, **una cambia de signo**:
`4_250_20`, de -4,60% a +7,94%. No ocultar ese cambio detrás del agregado más negativo.
[Figura completa por celda, con faltantes explícitos](avzvol_o5_robustness_20261010/endpoint_cells_notion_agent_chart.html).
La serie de panel original de esa figura es contexto de otra población; las dos series
secundarias sí comparan los mismos grupos. Nueve pares secundarios ausentes no son cero.

## Reproducibilidad y protección

[Evidence JSON](avzvol_o5_robustness_20261010/evidence.json),
[plan](avzvol_o5_robustness_20261010/analysis-plan.json),
[31 celdas: eliminaciones](avzvol_o5_robustness_20261010/cell-sensitivity.csv),
[seis contratos](avzvol_o5_robustness_20261010/contract-sensitivity.csv),
[31 estados de sensibilidad de extremo](avzvol_o5_robustness_20261010/endpoint-cell-sensitivity.json).

```bash
python tools/review_avzvol_o5_robustness.py \
  --inventory exports-locales.json --out-dir carpeta-nueva \
  --audit-reference-sha256 1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e \
  --allow-exposed-o5-review
```

Índice local: seis rutas explícitas `[{"file":"/ruta/export.parquet"}]`.
La receta usa la referencia fija del repo y verifica los seis hashes/footers antes de
cualquier payload O5. Opt-in obligatorio; directorio nuevo; no sobreescritura.
Los 199 promedios contrato/celda reproducen el lote anterior a tolerancia 1e-12.
Base y todas las eliminaciones se recomputan independientemente con listas y `math.fsum`:
diferencia máxima **1.39e-17**. El filtro de extremo
se contrasta independientemente contra diccionarios/sets de etiquetas exactas.
Pruebas unitarias nuevas usan únicamente valores inventados; no validan verdad científica del raw.
Los gráficos canónicos tienen preflight estático y se guardan en repo; no se pudo
adjuntar HTML inline en esta sesión por falta de la capacidad de subida de archivos.

## Pendiente concreto: repo y Kaggle, sin esperar nuevos originales

- **P1:** seguir acreditando fuente histórica, reloj/calendario/continuidad/liquidez y
  regla de selección D-1. Recuperar mapa completo bar→sesión; corregir el guard en
  un bundle nuevo con tests de límite y ledger de revisión, sin reescribir outputs.
  Sin ese mapa, la incidencia/impacto real del desfase sigue sin identificar.
- **P2:** construir censo causal y negativos calibrados, conservación de UNKNOWN,
  matcher same-session/as-of y benchmark de controles contra su propio censo.
  Congelar reglas/calipers antes de mirar la magnitud nueva; los pseudo legacy no
  sustituyen a consolidaciones acreditadas sin racimo.
- **P3:** mantener O5 como métrica histórica y diseñar respuesta en tiempo físico,
  censura y cobertura bajo fuentes defendibles; esta corrida no la implementa.
- **P4:** continúa prohibida. Sin P&L, costos ni búsqueda económica.
- **Kaggle:** sin nueva versión de datos/kernel de mercado ni promoción del catálogo.
  Catalog v15 / canonical v1 / reexport v2 siguen con los bloqueos documentados.
  Preparar bundle versionado con procedencia y mapa de barras sólo cuando su evidencia
  sea suficiente; un PASS de procesamiento o cero errores estructurales no lo certifica.
- **Resultados previos:** preservados y no declarados libres de sesgo. Esta revisión
  es desarrollo post-exposición, no una nueva confirmación independiente.

## Validación del lote

665 tests +25 subtests CPU; 18 tests de navegación y catálogo sin errores.
Seis tests nuevos inventados cubren pesos por sesión, eliminación completa,
soporte fijo, duplicados/faltantes, opt-in, hash de referencia con Python -O
y no sobreescritura. Tres figuras canónicas: preflight estático exitoso.
CI remoto se verifica sobre el head exacto antes de merge; no es certificación científica.
