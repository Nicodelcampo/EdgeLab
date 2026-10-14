# Protocolo de desarrollo: proxies A/E y respuesta, sin zonas

**FIXED_BEFORE_FIRST_RESPONSE_PILOT, EXPLORATORY_DEVELOPMENT.** No confirmación, preregistro externo/independiente, mecanismo físico o estrategia. Complementa `ABSORPTION_EXHAUSTION_EMPIRICAL_DESIGN.md` y registra cambios explícitos de aquella propuesta antes de leer estas respuestas. Papers/Brain referenciados y scoped en `ABSORPTION_EXHAUSTION_SOURCE_REVIEW.json`; no se afirma nueva lectura integral de toda la biblioteca.

## 1. Pregunta, población y separación temporal

¿Las firmas continuas ya medidas permiten definir proxies reproducibles de presión confinada y decaimiento tras impulso, y qué respuestas/censura descriptivas siguen a cada estado? Primero censo sin usar zonas como filtro; esto NO significa que sepamos que no había zonas. Sin detectores96configs, no es todavía comparación de geometría/llegadas ni efecto incremental de modelos M2−M1.

Mantener fuente MNQ09-26versión2 y rangos naturales ya usados. Calibración sólo June12; evaluación de desarrollo June15/16. Las features de las tres fechas se inspeccionaron en el atlas y guiaron el protocolo; NO son holdout virgen. No sustituir fechas si falta soporte, no abrir≥2026-10-01. Clasificación/primitivas W20 y contexto trailing60s, primer trade por celda5s. `(timestamp_ns,sequence)` define corte; ninguna secuencia futura entra en features. Calibración antes de procesar evaluación, sin etiquetas/respuestas de train para escoger umbrales.

## 2. Cobertura y calibración fija

Se preservan gates P0 (cotización válida/volumen80%, gapmáximo2s, historia) y se añade **para clasificación**, no retroactivamente al atlas, cobertura de signo≥80% en current y prior. UNKNOWN no es NEITHER. Sesión canónica y reloj se validan juntos; no alcanza cambiar date label para aparentar train pasado.

Calibrar por dirección previa(+/−) y dos fases ex ante: America/Chicago08:30≤hora<15:00(RTH), resto OTHER. No ranking de fases/direcciones por outcomes. Mínimo100anclas medibles/celda para cuantiles lineales; insuficiente/alto-pressure quantile no positivo→UNKNOWN_CALIBRATION, no fallback global. Es soporte de ingeniería del estimador, no100observaciones independientes ni potencia estadística.

En current de train: presión dirigida q20/q80; abs progreso q20; rango q25; path q25. En prior de train: presión dirigida q80. Todos congelados con hash antes de clasificar eval; no recalibrar usando June15 para mejorar June16 en este intento.

## 3. Estados únicos, ambos posibles

Dirección s = signo flujo previo P0. Presión es volumen estimado a favor de s, no OFI/MLOFI ni profundidad. Interior/quotesinválidas siguen sin BUY por defecto.

- **A_PROXY:** presión current≥q80current y prior≥q80prior; abs avance neto current≤min(2ticks,q20abs); rango current≤q25range Y recorrido(path)current≤q25path. Se requiere presión alta sostenida y confinamiento: poco avance neto tras gran excursión/retorno NO A por esta definición.
- **E_PROXY:** presión prior≥q80prior Y avance dirigido prior≥4ticks; ratio presión current/prior≤0,5 Y ratio número de trades≤0,5. No imponer reversión ya ocurrida ni leer futuro para decidir impulso. Decaimiento de presión sin frecuencia o sin impulso previo se cuenta aparte, no E.
- Etiqueta disjunta A_ONLY/E_ONLY/BOTH/NEITHER/UNKNOWN. A yE pueden coexistir con presión previa muy alta y actual aún alta pero menor. Cero BOTH/soporte no autoriza aflojar umbrales.

Cambios frente a propuesta original: se usa abs progreso acotado para no llamar “stall” a gran reversión; se agregan rango/path; caída presión Y frecuencia explícitas, y gate de signo. Decisiones ex ante de este desarrollo, no optimización por respuestas. No sensibilidades70/90/otros horizontes en este piloto. Sin LOB/MBO, ninguno identifica reposición pasiva, iceberg o final de metaorden.

## 4. Controles descriptivos sin zonas

Tags ex ante: HIGH_PRESSURE_PROGRESS, HIGH_PRESSURE_EXCURSION_RETURN, LOW_PRESSURE_SMALL_NET, PRIOR_IMPULSE_NO_JOINT_DECAY, DECAY_WITHOUT_PRIOR_IMPULSE. Usan sólo features propias del anchor. Pueden solaparse con estados y entre sí: NO sumar conteos como poblaciones independientes. Dirección previa cero queda UNKNOWN, no se fuerza una comparación direccional.

Son contrastes descriptivos/no-zone-census, **no matching causal**. No se afirma que eliminaron selección, actividad o regresión hacia la media al orientar por prior. Informar celdas fase×dirección y baseline continuo. Una diferencia de tasas sin M1/controles comparables no demuestra valor incremental de A/E. Entradas para M1 ya definidas; modelos no se ajustan en este piloto.

## 5. Respuesta primaria y observabilidad

En el mismo anchor de features, midpoint2=bid+ask entero (medios ticks). Distancia whole ticks fijada entonces: `max(4,ceil(0.5*rango_midpoint_trailing60s))`. Contexto trailing60s CURRENT, no ventana previa desplazada y no rango futuro. Contexto/origen/dirección no observables→ORIGIN_*_UNKNOWN; conservar denominador.

Buscar en orden `(ns,seq)` estrictamente después del anchor, hasta t+60s inclusivo: continuación primero/reversión primero respecto de s. Otros ticks del mismo ns posteriores al anchor pueden cruzar; todos los ticks del ns exacto de deadline entran. No interpolación ni fills. Primer cruce antes de censura es utilizable aunque luego termine tape o haya gap; no se exige horizonte completo tras evento ya resuelto.

Sin cruce: NO_OBSERVED_PASSAGE sólo si el horizonte fue observado sin gaps>2s/quoteinválida hasta su punto de confirmación. Si no hay punto exacto de deadline, exigir primer trade posterior válido y separación≤2s para confirmar cobertura, pero **no contar su precio como cruce antes del deadline**. Gap o quoteinválida en esa confirmación→censurado. Con muestra exacta de deadline y sus secuencias completas, no hace falta mirar después. EOF sin cobertura→EOF_CENSORED. Es primera pasada de cotizaciones registradas en trades, NO camino continuo completo.

Censura se aplica antes de aparente cruce tras gap/quoteinválida; unknown/EOF nunca se etiqueta “ninguna”. Tasas entre respuestas utilizables condicionadas a observabilidad de estado/contexto/futuro, no todo el mercado. Comparar censura por estado y fase, conservar counts del censo entero. No inferir ausencia de efecto de muestras censuradas o de estado sin soporte.

## 6. Optimización y límites

Una lectura de cada sesión, prefijos P0 compartidos, arrays de next-gap/next-badquote y búsqueda por deadline. Cruces vectorizados dentro de la ventana de cada anchor, no bucle Python por cada tick×config. Roster único20s/60s; en reloj5s hay a lo sumo13anclas cuyas ventanas60s contienen un tick. Índices y datos por sesión, sin JSONL/private rows persistentes ni producto cartesiano. Cota explícita100Mscan elements/sesión,120Mtotal; fail/no truncation, no assertion de speedup de mercado antes de medir.

Tres sesiones,5Mticks/sesión,8Mtotal,250kanclas/sesión;900sCPU/runner,4GiBRSS sampled,6GiBAS,600stransporte,1500sparent/1800snotebook. Un envío manual privadoCPU, sin auto-retry. Holdout/P&L/inferencia/modelos/zonas/writer Brain desactivados.

Allowlist final boot/science receipt o runner-failure (sólo type, sin mensajes ni paths);1MiB/archivo/4MiBtotal en adquisición. Falla/capacidad no es cierre científico completo. Recibos agregados de calibración y counts permitidos; no raw clock/sequence/feature/label export.

## 7. Criterio de avance, no inferencia adelantada

Este piloto describe soporte/estados/censura/respuestas, no Brier/CI/valor incremental ni regla de trading. Dos sesiones de evaluación no bastan para equivalencia/transportabilidad. Ningún p-value: no FDR falso aplicado a counts. Respetar mínimos de sesiones/bloques y margen práctico ex ante para etapa inferencial posterior; no multiplicar definiciones sobre los mismos episodios para aparentar potencia.

Siguiente: si soporte/observabilidad lo permite, registrar evaluación por bloques de sesiones y pérdidas emparejadas M0/M1/M2, con calibración/splits/purge≥60s, intervalos por sesiones y multiplicidad completos. Comparar A/E contra componentes continuos, separar regresión a la media y presión vs tamaño/frecuencia. Después episodios/llegadas y geometría de AVZP2/racimos/BT2/BT2A, con densidad/ocupación y dependencia AVZ-racimo. No convertir counts o resultado de un desarrollo en edge validado/autopromoción.

## 8. Operación y recuperación

Los diarios locales anteriores reaparecieron más antiguos que los snapshots publicados; no reescribirlos, rearmar eventos inventados ni resetear su lifetime budget. Este intento tendrá journal nuevo de batch1y watch4consultas, anclado explícitamente al último snapshot publicado con historial anterior terminal. No se declara presupuesto global/lock contra otro controlador. Antes de instalar Debian: reconciliar release/estado desde fuentes durables aprobadas, no restaurar automáticamente sandbox viejo. Un único controlador, sin auto-pull y writer canónico todavía no autorizado.
