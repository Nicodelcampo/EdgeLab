# AVZVOL: auditoría de evidencia, baseline y comparaciones

**Estado: requiere revisión; no certificado libre de sesgo.**
Alcance exclusivo: AVZVOL k1/k2/k3 v1 y sus seis exports de eventos MNQ.
No se auditaron otras corridas en esta revisión. Se preservaron originales,
negativos y holdout. [Snapshot reproducible](AVZVOL_AUDIT_20261010.json).

## Qué quedó verificado

- Los tres `procedencia.json` descargados por API con versión numérica 1
  coinciden byte a byte con los guardados; se registran SHA y run IDs.
  Para status/listado, la API requiere etiqueta `v1`, no `1`.
  El listado MCP devuelve tamaños inconsistentes con los bytes reales:
  no usar esos tamaños como comprobación de integridad.
- Los seis exports coinciden con sus SHA guardados. TODOS sus row groups
  tienen prueba de `session < 20261001` antes de leer covariables.
- `544,531` filas evento×celda reconciliadas con Arrow.
  **No son racimos independientes:** un evento puede figurar en varias celdas.
- El protocolo original exige **25 ticks**. `SPEC=25` es correcto; la
  descripción vieja de 50t no demuestra un cambio de configuración.
- Las **23 celdas evaluables** y los conteos reales de descubrimiento coinciden
  con el publicado. Se reprodujo únicamente el baseline O5 ya publicado con
  las funciones del estimador congelado, desde exports: diferencia máxima
  absoluta de β **2.6367796834847468e-16**, menor que la tolerancia fija `1e-9`.
  También coinciden `n_real`, `n_pseudo`, `n_sesiones` en cada celda.
  No se recalcularon outcomes de confirmación ni se abrieron pruebas nuevas
  del control de actividad. Reproducir ese cálculo no certifica el upstream.

La referencia y funciones públicas provienen de
`4e1e26930f9778f974a4dd4946977ac48b1725d8`.
Ver [manifiesto y enmienda 2](https://github.com/Nicodelcampo/EdgeLab/blob/4e1e26930f9778f974a4dd4946977ac48b1725d8/docs/research/AVZP2_RACIMO_GRILLA_MANIFIESTO_20261008.md)
y [manifiesto base](https://github.com/Nicodelcampo/EdgeLab/blob/4e1e26930f9778f974a4dd4946977ac48b1725d8/docs/research/AVZP2_RACIMO_MANIFIESTO_20261008.md).

## Hallazgos que impiden declarar ausencia de sesgo

### 1. El nominal de cinco pseudo no se cumple por fila real

| Contrato | Filas reales | Pseudo-filas | Pseudo / (5 × real) |
|---|---:|---:|---:|
| `MNQ_09-25` | 9,816 | 46,822 | 95.40% |
| `MNQ_12-25` | 19,143 | 87,955 | 91.89% |
| `MNQ_03-26` | 17,039 | 77,127 | 90.53% |
| `MNQ_06-26` | 18,524 | 85,061 | 91.84% |
| `MNQ_09-26` | 26,139 | 122,290 | 93.57% |
| `MNQ_12-26` | 6,094 | 28,521 | 93.60% |

Total: `447,776` pseudo-filas frente a
`483,775` nominales (**92.56%**).
Esto **no demuestra huecos en ticks** ni sesgo económico. El código muestrea
con reemplazo y limita a 200 candidatos, con rechazo por ocupación; puede
obtener menos de cinco. No hay `pair_id`: no se puede certificar cuántos
controles recibió cada real ni si el peso de controles por real es uniforme.
No completar filas a posteriori ni deduplicar controles: se cambiaría el diseño.
Las repeticiones son compatibles con muestreo con reemplazo y no se declaran
automáticamente datos corruptos.

### 2. Los bins de FE dependen del orden en valores empatados

`qcut(rank(method="first"))` separa valores idénticos entre bins distintos.
Se verificaron **295 casos partición×celda×variable** en los exports,
con recomputación independiente NumPy frente a pandas.
El orden físico pone reales antes de pseudo dentro de las celdas/contratos;
los empates pueden introducir dependencia artificial entre FE y tratamiento.
**La ocurrencia está verificada; su impacto económico no se cuantificó.**

`assign_frozen_bins` ofrece una alternativa opt-in para ejecuciones futuras:
cutpoints externos congelados, valores iguales en el mismo bin e invariancia
al orden. No aprende umbrales de confirmación ni imputa faltantes.
Usarla cambia el método: requiere enmienda/identidad de auditoría nueva,
no una sustitución silenciosa en el resultado anterior.

### 3. La guardia legacy de reproducción tiene un bypass real

El runner histórico permite omitir el JSON publicado y compara sólo las
celdas que encuentre en `pub["O5"]`. Puede aceptar una referencia incompleta
aunque la lista `evaluables` siga completa. Un test sintético reproduce ese
falso PASS; **no se afirma que haya ocurrido en estas salidas**.

`require_baseline_reproduction` exige referencia, universo exacto, todas las
celdas, β finitos, conteos iguales y tolerancia fija. El caso real completo
pasa. La guardia es opt-in: **no modifica ni protege automáticamente el
runner legacy que sigue en la rama histórica**.

### 4. Calidad upstream y lineage raw siguen sin certificar

Los logs indican `edgelab-ticks-nt8-canonical` para los primeros tres contratos
y `edgelab-ticks-nt8-reexport-20261005` para los otros tres. No registran
versión/archivo/hash físicos consumidos ni hash del resolver/code bundle.
Una etiqueta de commit no verifica todos los imports montados.
Tampoco se certificaron calendario/feriados, continuidad, reloj NT8, cotizaciones,
liquidez causal o selección de sesiones MNQ. No trasladar a MNQ un fallo de
ES o de un archivo NQ ni asumir que el catálogo montado era v15.

## Cómo repetir la revisión técnica

Con Python 3.12 y extra Arrow, obtener primero los outputs de **v1** por MCP
y registrar sus SHA en una lista `{"file": "/ruta/export.parquet", "sha256": "…"}`
de los seis contratos. Los pins deben medirse/verificarse externamente;
un hash autoemitido no es aprobación.

```bash
python tools/audit_avzvol_outputs.py --inventory outputs-pinned.json \
  --out nueva-auditoria.json --allow-preholdout-covariate-audit
```

El CLI sólo lee identidades/covariables; no `o5`, retornos, control o ticks.
Comprueba TODAS las particiones antes de cualquier payload de eventos.
No sobrescribe archivos existentes. Devuelve exit 2 y `REQUIRES_REVIEW`,
no permiso de research. `--published-baseline` y `--reproduced-baseline`
deben suministrarse juntos si se comparan metadatos de baseline ya calculados.
Esa comparación no ejecuta estimadores ni autentica autoridad de los JSON.

El profiler genérico no pudo leer este formato Parquet. Su error no prueba
corrupción: se reemplazó el perfil técnico por schema/estadísticas Arrow,
pins y validación de covariables, sin descartar ni modificar filas.

## Pendientes concretos de AVZVOL

1. Recuperar versiones/hashes realmente montados de raw, resolver y code
   bundle; revisar calidad MNQ y decisiones de selección/cobertura.
2. Congelar evidencia de pares (`pair_id`, draw ID, candidatos aceptados y
   rechazos) y política de pesos para una revisión nueva; no inventarla en
   los exports actuales.
3. Definir y aprobar bins sin separación de empates fuera de confirmación.
   Conservar aparte la reproducción exacta de la receta legacy.
4. Integrar la guardia obligatoria al runner antes de su siguiente ejecución.
5. Sólo después de resolver autorización/especificación/calidad, avanzar con
   el control de volumen/intensidad de la enmienda 2. La confirmación ya vista
   no se presenta como réplica nueva y ningún resultado habilita P&L o promoción.

No se tocaron resultados anteriores, ledger, umbrales, fuente de ticks ni
datos reservados. El snapshot es una revisión separada, no una invalidación
automática ni una certificación científica.
