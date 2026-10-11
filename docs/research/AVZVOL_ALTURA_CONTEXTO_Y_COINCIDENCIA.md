# AVZVOL: altura del racimo, contexto y coincidencia entre configuraciones

## Resultado para decidir
No hay ventaja universal de la altura20 frente a30/45 en alcance fijo. La gran diferencia al pedir una altura de banda es, en buena parte, geometría del objetivo. Una asociación favorable tras la vuelta aparece en un recorte de contextos compartidos, pero depende mucho de ese recorte y de la ponderación. La coincidencia simultánea de racimos estrechos/amplios es una pista adicional observable al ancla en el export, no una estrategia validada.

## Altura pequeña no equivale a mayor recorrido
Mínimo4, ventana1000; selección fijada por frecuencia antes de consultar estos resultados. Ancla dentro, salida registrada, O2 conocido. Media igual de3bloques, dentro de cada bloque primero medias por sesión y luego contrato.

| Altura máxima | Alcanza20ticks real | Alcanza1h real | 20ticks pseudo | Salida coincide con tendencia500 real/pseudo |
|---|---:|---:|---:|---:|
| 20 | 24.40% | 29.43% | 24.98% | 51.90% / 50.16% |
| 30 | 24.92% | 21.21% | 24.77% | 55.24% / 51.95% |
| 45 | 23.95% | 14.76% | 24.98% | 62.31% / 55.02% |

h=H−L+1ticks reales, no altura máxima configurada. Cambiar h cambia la distancia del target1h. Los20ticks permanecen fijos. Mayor coincidencia con la tendencia500 no es señal direccional nueva del racimo; el benchmark utiliza signo anterior al ancla y excluye tendencia0. No hay modelo predictivo calibrado ni memoria espacial del corredor.

## Contraste dentro de contextos recientes similares
Se exige soporte real y pseudo para las3alturas en exactamente(contract,session,clock,trend,sign(mom100_h)). Se promedia por estrato, por sesión, por contrato y luego por bloque. Esto NO es una regla ejecutable: el soporte utiliza observaciones de toda la sesión y condiciones de desenlace conocidas posteriormente. Controles legacy no certificados como zone-free.

| Bloque | 20ticks altura20 real/pseudo | Altura30 real/pseudo | Altura45 real/pseudo | Filas reales altura20 conservadas/eligibles |
|---|---:|---:|---:|---|
| 1 | 20.07% / 21.50% | 13.11% / 21.36% | 17.49% / 33.07% | 107/447 |
| 2 | 44.86% / 33.95% | 37.27% / 21.08% | 35.13% / 19.20% | 179/642 |
| 3 | 21.48% / 17.17% | 22.53% / 18.94% | 23.53% / 22.85% | 491/1074 |

La altura20 supera30/45 en los primeros2bloques de ese recorte, pero queda por debajo de ambas en el tercero. No elegir retrospectivamente una altura ganadora por régimen. El contraste no controla velocidad real de vuelta, intensidad, trayectoria espacial ni todos los confusores.

## Pista de retorno y prueba de fragilidad
O3b: después del primer toque, lado de salida primero frente al opuesto, barreras±h; sólo0/1resueltos. No es win-rate desde fill ni P&L.

| Altura máxima | Sin recorte real/pseudo | Contextos conjuntos real/pseudo |
|---|---:|---:|
| 20 | 50.26% / 49.40% | 62.43% / 48.08% |
| 30 | 49.22% / 50.11% | 54.21% / 50.07% |
| 45 | 51.00% / 50.14% | 54.41% / 50.01% |

La altura20 da62,43% en el recorte conjunto, con757retouches reales resueltos, frente a50,26% sin recorte. Antes de interpretarlo como filtro se añadieron18variantes de ponderación/soporte/contexto por altura tras observar esa asociación: exploración post-exposición, no confirmación ciega.

| Altura20: tratamiento del recorte | Real | Pseudo |
|---|---:|---:|
| Contexto completo,6poblaciones,igual contrato | 62.43% | 48.08% |
| Mismo recorte,igual sesión | 56.66% | 48.60% |
| Contexto completo,sólo par altura20,igual sesión | 50.00% | 48.47% |
| Sólo horario,6poblaciones,igual sesión | 50.67% | 48.77% |

El62,43% no permanece como un efecto amplio y estable. Igualar contratos sobrerrepresenta tramos con4/5sesiones; exigir soporte simultáneo también cambia la población. Las cotas de identificación con O3bambiguo/no resuelto se conservan en CSV: no son intervalos de confianza.

## Idea nueva: coincidencia simultánea de alturas
Para cada formación20, buscar en el MISMO(contract,session,t0) una formación30y45cuyas cotas de creación contengan susL/H. Ninguna formación posterior ni geometría final mutada. No confundirlo con coexistencia de zonas ya antiguas, densidad de volumen o pertenencia de miembros. Fuente/asof todavía no certificados.
Se observan430formaciones estrechas coincidentes con ambas de3111formaciones20en estos3bloques (13,82%). Hay283retouches resueltos de ese grupo. Esta idea se decidió tras la primera prueba de contexto; no está preregistrada.

| Bloque | Ninguna contiene: retorno lado salida | Ambas contienen: retorno lado salida | Retouches resueltos ambas | Sesiones ambas |
|---|---:|---:|---:|---:|
| 1 | 50.98% | 58.81% | 67 | 35 |
| 2 | 44.81% | 52.86% | 79 | 32 |
| 3 | 49.33% | 53.79% | 137 | 46 |

La asociación es favorable en los3bloques al igualar sesión, pero cambia de signo en2de3al igualar contratos. Pooled de filas: diferenciasambas−ninguna +7,62/+0,46/+1,51pp; no usar el grupo conjunto como otro gran salto de62%. El alcance20ticks tampoco mejora consistentemente: igualdad de sesión daambas−ninguna−4,99/+0,03/+2,80pp por bloque. Todas las tasas/status0,1,2se conservan; no descartar el grupo1por conveniencia.

## Prioridad siguiente
1. Conservar altura20como candidato de soporte razonable, no como ganador universal de recorrido. Mantener30/45como comparadores.
2. Investigar coincidencia multiescala como feature al nacimiento, con contexto espacial del recorrido; separar si ayuda a la vuelta pero no a la excursión previa.
3. Antes de validar ese flag, usar mismo target fijo en ticks entre grupos: aquí O3b±hdeja targets distintos y no se reconstruyen nuevos desenlaces. Se necesitan trayectoria/confirmaciones causales para medir retorno con barreras fijas, adversa y precio ejecutable.
4. La campaña percentil/window_bars sigue pendiente; no se ejecutó replay ni se afirma optimización de motor. Plan previo propone reutilizar bloques/historial y cintas de zonas; benchmark/paridad sintética antes de sustituir el agrupador.
5. No promover reglas dependientes del soporte futuro de un estrato. Sin costos/fills no se puede separar rentabilidad de azar.

## Evidencia y alcance
Seis exports ya expuestos con SHA256exacto. Sólo3configuraciones seleccionadas por frecuencia,3bloques publicados anteriormente, sin precios nuevos, holdout ni P&L. No se cambian gates. Real y pseudo no son muestras causales independientes.
Se verifican columnas cargadas sin nulls, ticks enteros y O2=alcance1h; se reutilizan perfiles previos, no se rehace auditoría genérica. Numerador20ticks conjunto comprobado mediante acumulación de filas independiente;20ticks sin recorte y coincidencia verificados directamente con diccionarios sobre raw.8CSVreproducidos byteidénticos.
Resultados por contrato conservados en CSV; no afirmar que los períodos o contratos son independientes. Las figuras no se adjuntaron porque el helper de archivos está indisponible; comparación numérica visible aquí.

```bash
python docs/research/avzvol_height_context/analyze.py --repo . --raw <export-root> --out <derived-output>
```
Requiere pandas/numpy/pyarrow. plan.json fija el estudio inicial;extension-plan.jsonexplicita la extensión después de ver los primeros resultados. Datos crudos no se suben.
