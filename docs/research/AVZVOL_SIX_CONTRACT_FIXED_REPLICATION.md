# AVZVOL: réplica fija en seis contratos

## Conclusión
La regla fija cumple todos los criterios en 0 de los cinco contratos distintos del descubrimiento; no constituye una ventaja validada.

Parámetros congelados: P80, window bars5, racimo mínimo8, ventana1000, altura20 ticks; excursión mínima40ticks, regreso50%, tocar borde, primera salida que alcanza D, corredor ocupado por menos del25% de hasta256 barras cerradas y selección temporal6250registros. No se modificaron después de observar los nuevos contratos. El50% es una referencia descriptiva de barreras simétricas, no un nulo causal garantizado.

## Regla primaria
| Contrato | Racimo primero / resueltos | Tasa | IC por sesiones, 95% | No resueltos | Sesiones activas / observadas |
| --- | ---: | ---: | ---: | ---: | ---: |
| MNQ 09-25 | 383/782 | 48.98% | 45.48–52.41% | 26 | 29/29 |
| MNQ 12-25 | 956/1930 | 49.53% | 47.39–51.75% | 49 | 62/62 |
| MNQ 03-26 | 1040/2087 | 49.83% | 47.89–51.77% | 49 | 57/57 |
| MNQ 06-26 | 1047/2209 | 47.40% | 45.60–49.17% | 26 | 57/57 |
| MNQ 09-26 | 1204/2515 | 47.87% | 46.08–49.70% | 30 | 46/46 |
| MNQ 12-26 | 255/467 | 54.60% | 51.89–57.14% | 9 | 10/10 |

## Las cinco referencias completas
Porcentaje de objetivo primero; entre paréntesis, resueltos. Orígenes distintos tienen poblaciones de señales distintas; no sumar sus observaciones.

| Contrato | Racimo | Traslado +250 | Precio ancho 1 | Precio ancho 10 | Precio ancho 20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| MNQ 09-25 | 48.98% (782) | 46.86% (781) | 49.61% (127) | 50.97% (771) | 50.00% (874) |
| MNQ 12-25 | 49.53% (1930) | 48.86% (1977) | 50.90% (446) | 50.29% (2929) | 49.68% (3293) |
| MNQ 03-26 | 49.83% (2087) | 51.32% (2237) | 51.80% (500) | 49.75% (3216) | 49.83% (3568) |
| MNQ 06-26 | 47.40% (2209) | 47.74% (2323) | 49.13% (631) | 49.43% (4008) | 49.80% (4456) |
| MNQ 09-26 | 47.87% (2515) | 47.79% (2649) | 47.37% (532) | 48.41% (3588) | 49.20% (3986) |
| MNQ 12-26 | 54.60% (467) | 50.81% (492) | 47.71% (109) | 48.88% (536) | 48.95% (617) |

## Alcance y verificación
- Seis contratos y 261 fechas seleccionadas. Los dos primeros contratos de PR114 reutilizan etiquetas; esta extensión añade cuatro contratos, no recontabiliza el descubrimiento como prueba independiente.
- 270 grupos de mercado, 1080 resúmenes con sensibilidades y 864 contrastes. Son análisis superpuestos, no tamaños muestrales independientes.
- 270 estratos comparados exactamente con una implementación Python de referencia, y30celdas primarias verificadas mediante ordenación estable/groupby independiente.
- Fuente exacta fijada por SHA256/tamaño/filas. Conteos del catálogo contrastados contra sesiones crudas completas. Cualquier observación seleccionada fuera del intervalo de lectura debe ser mantenimiento declarado; fallar de forma cerrada ante cualquier otra discrepancia.
- Solo fechas seleccionadas producen eventos. Warmup declarado anterior alimenta calibración, no señales. Hora16 excluida solo de derivados. Cero fugas observadas de alcance; originales intactos.
- CSR escrito por bloques de barras completas:45casos de igualdad exacta frente al constructor original. No cambia detector ni etiquetas. Borrado únicamente de cachés binarias derivadas después de validación, nunca de fuentes.

## Riesgos que siguen abiertos
1. Exploración previa y pruebas múltiples: CIs puntuales por20.000remuestreos de sesiones completas, sin corrección FWER. No es holdout virgen ni certificación de fuente.
2. Las referencias de precio tienen anchos centrados fijos y no están emparejadas exactamente en geometría/contexto con racimos reales; traslado250 es un control descriptivo, no intervención aleatoria.
3. El adelgazamiento reduce solapamiento, pero no asegura independencia entre zonas o sesiones. Parámetros vecinos D20/80,q25/75 y bin25000 son sensibilidades; no seleccionar el mejor como validación.
4. No resueltos por fin de sesión, horizonte o huecos publicados junto a cada tasa y bandas de censura. No descartar para simular operaciones ganadoras.
5. Hasta256barras previas cerradas, excluida la barra de activación. Sensibilidad full256 separada; nunca incluir información posterior en atributos.
6. El profiler genérico falló por recursos; esto no es un error del dataset. La auditoría Parquet nativa y todas las corridas principales completaron sus controles.
7. Las reglas históricas del catálogo incluyen elementos retrospectivos; seleccionar estas fechas no acredita selección ejecutable as-of. El warmup no produce eventos pero puede influir en calibración: la sensibilidad específica al salto1419ticks no seleccionado de MNQ09-26 sigue pendiente, sin tratarlo como corrupción ni borrarlo para mejorar resultados.
8. No se simulan comisiones, spread, ejecución o P&L. No invertir automáticamente una regla por un resultado negativo.

## Nueva hipótesis: zonas de2000–3000barras
Protocolo separado en `AVZVOL_LONG_LIVED_ZONES_PROTOCOL.md`. Antigüedad, ventana de detección y revisitas son conceptos distintos. La extensión está planificada, todavía no medida; no presentar esta idea como hallazgo.

## Evidencia reproducible
Agregados, manifiesto y código en `research/avzvol-six-contract-replication/`. Fuentes y señales tick-a-tick no se publican. Código snapshot con rutas locales explícitas y dependencias de los PR112/113/114; no es un runner portable ni un motor NT8 certificado. PR apilado sobre PR114, sin merge ni promoción automática.
