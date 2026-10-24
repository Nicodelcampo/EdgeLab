# Balance de las corridas del 23 y 24 de octubre: resultados, próximos pasos y mejoras

Estado: VIGENTE. Las mejoras que tocan reglas de validación están en estado PROPUESTA: decide Nico.
Fecha: 2026-10-24
Familia / módulo: EXPANSION_ZONAS (EXPZ-NQ, EXPZ-CFD), AREAS_EXP_1_CRUZADO (U1), LUXIMB_FADE_VISOR, embudo y agente del Debian
North Star: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Procedencia: foundation en `c7ff0835` (incluye #129–#131, #133 y #134). Fuentes: `AUDITORIA_CORRIDAS_KAGGLE_Y_EMBUDO_20261024.md`,
`MEDIDO.md` de cada campaña EXPZ, `AREAS_EXP_1_MEDIDO_Y_NO_MEDIDO.md`, `RESULTADOS_RECALCULO_CANONICO_RELEASE_20261024.md`,
`DECISIONES_VALIDACION_20261024.md`, `HOLDOUT_VENTANAS.jsonl`, y el estado de los kernels en Kaggle a las 18:50 UTC.

## 1. Resultados por campaña
| campaña | qué corrió | resultado | estado con las reglas del #133 |
|---|---|---|---|
| EXPZ-NQ | DESC 2025-08-05 → 2026-03-31, 466.560 pruebas (233.280 celdas × 2 canales) | 9.960 celdas evaluables, **0 nominadas por FDR y 0 por Romano-Wolf** (umbral t 4,11). Igual pasaron 3 candidatas con la regla vieja | `SIN_CANDIDATAS` por D1. Pausada. El kernel de INDAGA terminó y **no se leyó** |
| EXPZ-CFD | ídem, con la señal en el CFD | 8.400 evaluables, **0 por FDR y 0 por Romano-Wolf**, 3 candidatas con la regla vieja | igual que EXPZ-NQ |
| U1-CRUZADO, fix 27 | topes en desarrollo re-medidos y OOS USATECH 2023-01 → 2025-07 | OOS: T1 −0,16 pts/op [−9,2, +8,1], T3 −4,84 [−16,0, +5,9]. MDE 13–17 pts/op, **sin rechazo**. El fix cambió 42 de 313 operaciones, todas a peor. Densidad del feed: **mercado** | El OOS no tiene potencia (`NO_CONCLUYENTE`): no la mata y no suma. No se lee como «otro régimen» porque el régimen no se declaró antes de re-correr (D2). Con la herencia del linaje (19,4 M pruebas, D4) ninguna celda de desarrollo se puede nominar. **Viva, sólo se confirma en el holdout desde el 23-10** |
| U1-CRUZADO, holdout exploratorio | sesiones 01-10 → 22-10 (acta `61d3b9dd`) | 11 señales en el CFD, **8 operadas en NQ** en 4 sesiones. T3: +29,4 pts/op, 7 de 8 ganadoras, IC90 [−1,2, +72,0], p 0,15 | `NO_CONCLUYENTE` (n = 8, el acta pedía 95). **Ventana consumida** (ver §2) |
| LUX-IMB, recálculo canónico (24-10) | regla del visor congelada, release de Kaggle, NQ ago-2025 → sep-2026 | +4,05 pts/op neto canónico, IC90 [+0,36, +7,56]; +0,198 R, IC [+0,013, +0,375]; DSR 0,33; efecto esperado tras selección ≈ 0 | `SIN_POTENCIA`: viva en reserva. Hacen falta ~944 operaciones (~400 sesiones). Confirmación sólo en el holdout desde el 22-10 |

En ningún caso se usó el holdout para elegir ni ajustar. Los costos salen de `edgelab/costos.py`. Hay una excepción, el literal
1,545 de los kernels AREAS (P8, diferencia 0,0005 pts).

## 2. La corrida del holdout con 8 de 11 operaciones (U1-CRUZADO)
- **Qué fue:** la mirada exploratoria del holdout de U1-CRUZADO. Acta `61d3b9dd` registrada antes de correr; resultado
  `c63ba501`, re-corrido con el fix 27. En el registro: fila `consumida` de `AREAS_EXP_1_CRUZADO` en `HOLDOUT_VENTANAS.jsonl`,
  desde 20261001 hasta 20261022.
- **No queda abierta esperando más sesiones.** El acta lo dejó escrito antes de mirar: la apertura limpia de las sesiones
  01-10 → 22-10 queda consumida. Esas 8 operaciones no se suman a las que vengan: ya se vieron, y sumarlas sería decidir con
  datos mirados.
- **La hipótesis sí sigue viva.** `NO_CONCLUYENTE` no mata. La confirmación se hace con sesiones posteriores al 22-10, con la
  misma regla intacta (T3, tope 3×), a N fijo y con una sola apertura por familia.
- **Con las reglas del #133:** el acta de esa confirmación reserva su paso de LORD++ al escribirse (D3). Es la única vía, porque
  con la herencia del linaje no se puede nominar nada en desarrollo (D4). La confirmación es en el régimen actual por
  construcción (D2). Mientras tanto se puede seguir semana a semana con `edgelab/funnel/secuencial.py`, que es válido mirando
  cada semana; mirar a mano y decidir no lo es.
- **Falta:** el acta de la confirmación todavía no existe. Hay que escribirla y registrarla antes de mirar la primera sesión
  posterior al 22-10. Además, operar U1 sigue exigiendo la paridad de zonas contra un feed en vivo distinto de Dukascopy.
- **Plazo:** en el exploratorio hubo unas 0,5 operaciones por sesión con NQ (8 en unas 15). A ese ritmo, las 95 del acta tardan
  muchos meses. Conviene que el acta fije un N alcanzable o que use el seguimiento secuencial, y eso se decide antes de mirar.

## 3. Próximos pasos
1. **Nico:** decidir cómo se suben las seis versiones recortadas de Dukascopy (`RECORTE_SPOT_HOLDOUT_20261024.md`).
2. **Mergear el #132.** Trae los 9 arreglos del embudo, el registro retroactivo, las EXPZ pausadas, el recorte y lo de abajo.
3. **EXPZ:** cerrarlas como `SIN_CANDIDATAS` y no leer los resultados de INDAGA, que con la regla nueva no deciden nada. La
   familia EXPANSION_ZONAS queda sin consumir su réplica ni su holdout.
4. **U1-CRUZADO:** escribir y registrar el acta de la confirmación forward (desde el 23-10, N fijo o secuencial) antes de mirar
   cualquier sesión, y plantear la paridad de zonas con feed en vivo.
5. **LUX-IMB:** lo mismo, desde el 22-10, con su propia y única apertura.
6. **Decisiones abiertas de Nico:** P2 (réplica consumida por linaje), P3 (contar INDAGA e INTEGRIDAD), P6 (MES y MNQ en A3),
   P8 (costo de AREAS desde `costos.py`), y las tres que dejó abiertas el #133 (FDR de dos canales ≈ 2q, campañas hermanas,
   ancestros sin declarar).

## 4. Mejoras que salen de los errores observados
### Ya aplicadas (no cambian reglas)
| error observado | arreglo |
|---|---|
| Pasaban candidatas con 0 nominadas | compuerta FDR dura en DESC (#133, decisión de Nico) |
| 53 pruebas fuera del contador; una familia nueva arrancaba en cero | registro retroactivo (#132) y herencia de linaje (#133) |
| Resultados de EXPZ no persistidos; estado en CORRIENDO después del kernel | el embudo guarda el RESULTADO y el resultado ilegible cuenta como falla (#130/#132) |
| Dos conductores podían relanzar la misma campaña | un solo `conductor` por campaña (#132) |
| Dos libros de LORD++ | libro único con lock (#133). **Nuevo hoy:** `update.sh` y `sync_state.sh` lo conservan y lo publican en el Debian. Antes, cambiar de versión lo pisaba con la copia del release o se negaba a hacer checkout |
| Libro de ventanas del holdout en el clon de código | se sincroniza al estado (#132) |
| Datasets SPOT con 2 horas del holdout | `tools/recortar_spot_holdout.py`. **Nuevo hoy:** `tools/kaggle_dataset.py` se niega a subir un parquet con filas desde la frontera, salvo `--permitir-holdout` (que exige el OK de Nico) |
| 26 manifiestos de lanzamiento sin commitear | recuperados y copiados al estado en cada ciclo (#132) |

### Propuestas (no aplicadas)
- **Potencia antes de lanzar (eficiencia).** EXPZ gastó 466.560 pruebas por campaña para llegar a un umbral de t 4,11 con
  menos de 10.000 celdas evaluables. El PREFLIGHT podría calcular el MDE del FDR a q 0,10 con el m y el N de la grilla, y
  avisar o frenar si ese MDE supera un efecto económicamente plausible. Avisar es una mejora del agente. Frenar sería una regla
  nueva y la decide Nico.
- **Todo nulo publica su MDE.** «FDR 0» en el `MEDIDO.md` de EXPZ no dice si faltó efecto o faltó poder. La regla ya existe en
  `CLAUDE.md`; falta que DESC la cumpla sola.
- **El registro antes del lanzamiento, verificable sin depender de git.** En EXPZ DESC la fila del contador se commiteó 2
  minutos después del lanzamiento. La propuesta es que el manifiesto de lanzamiento cite la cabeza de la cadena del registro.
  Así el orden se prueba con el hash, no con la hora del commit.
- **Régimen declarado antes de re-correr.** U1 perdió la lectura «otro régimen» de su OOS por no declararlo antes del fix 27.
  El PREFLIGHT podría avisar cuando falta `regimen`.
- **Literales de costo en kernels.** Un chequeo estático que busque fricciones numéricas fuera de `costos.py` (P8).

### Para el agente del Debian
- Antes de diseñar, mirar cuánta multiplicidad hereda la familia. Un hijo del linaje AREAS arranca con 19,4 M pruebas y no
  puede nominar nada en desarrollo. Conviene abrir familias realmente independientes, declaradas como tales, o diseñar desde el
  inicio para confirmar forward.
- Preferir grillas cuya potencia alcance con el N disponible (primera propuesta de arriba) a grillas más grandes. Más
  variantes sin potencia suben el umbral y no encuentran más.
- Escribir el acta forward en el mismo commit que congela la regla, con N alcanzable o secuencial.

Aporte al referente: el balance deja una sola vía abierta para U1 y LUX-IMB, la confirmación forward con su apertura única, y
saca a las dos EXPZ del camino del holdout. Las mejoras apuntan a que el Debian gaste sus pruebas en grillas con potencia y no
pueda subir el holdout por error.
