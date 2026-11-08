# Directivas de Nico para el agente del Debian (vigentes; las lee cada rol en cada ciclo)

Detalle y contexto: docs/research/MENSAJES_AL_AGENTE_DEBIAN.md (lo más nuevo, arriba).

1. Arreglate solo: monitoreá el proyecto y a vos mismo en cada ciclo (campañas BLOQUEADA o con fallas, unidades en failed, estado sin
   publicar, CI rojo); causa raíz, arreglo con test, desbloqueo de la misma etapa, y registro en ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md.
2. Pensá fuera del molde: proponé y mejorá por iniciativa propia los análisis, tus herramientas y tu proceso, sin romper la estructura.
3. Trabajá en espiral: medir → aprender (docs/research/APRENDIZAJES_ESPIRAL.md) → investigar afuera (Internet: inspiración, nunca
   evidencia) → proponer → correr → mejorarte → contar en la sala.
4. Usá las dos cuentas de Kaggle (nicolasbuttaro y nicobuttaro) para las corridas: repartí los lanzamientos ("cuenta_kaggle": "auto")
   y, si una está llena o falla, usá la otra; medí y reportá cuánto se usa cada una.
5. Estructura que no se rompe: nada se elige mirando el holdout; todo se pre-registra y se cuenta antes de correr (contador global,
   LORD++); nunca se relaja un criterio después de ver resultados; lo refinado con datos ya mirados se confirma con datos nuevos;
   cambiar gates/FDR/mandato/archivos protegidos sigue CLAUDE.md; no se opera con dinero real.
6. Holdout global desde el 30-sep (apertura `2026-09-30 22:00 UTC` = sesión CME `20261001`) y canasta de régimen: aplica a todos los
   agentes, todos los activos y todo el proyecto. Ninguna campaña cuyo desarrollo/OOS cerró el 2026-09-30 debe usar `holdout.desde: 20261023`.
   Dado que los edges operables son de régimen, no se espera años a acumular un `n_fijo` individual gigante: el riesgo se diversifica en una
   canasta de estrategias de régimen y cada candidata se confirma para la canasta si su rendimiento en la ventana reducida de holdout
   disponible está dentro de la desviación esperada según su distribución en desarrollo/OOS.
7. Auditoría prioritaria de las 16 corridas cosechadas de la sesión en la nube (Olas 1–9, 2026-10-29): ejecutá en el ciclo inmediato
   `python3 tools/auditar_corridas_nube_20261029.py`, procesá la cola `docs/research/auditoria_corridas_20261029/COLA_AUDITORIA_DEBIAN_20261029.json`
   (evaluación de las 6 nuevas `ACTA_HOLDOUT.json` en `edgelab-holdout-sellado` con `CONTEO` y `tools/holdout_canasta.py`, y evaluación
   de las 9 campañas con `PISTAS_VIVAS.json` con `tools/analizar_embudo.py` y `tools/holdout_canasta.py`) y publicá el dictamen firmado en
   `docs/research/auditoria_corridas_20261029/DICTAMEN_AUDITORIA_DEBIAN_20261029.md`.
8. **Cartera viva (centro de EdgeLab, decisión de Nico 2026-10-31, docs/CARTERA_VIVA.md).** Sos el dueño de las canastas: todos los
   días, después del cierre de CME, corrés `tools/cartera_diaria.py ciclo` (timer `edgelab-cartera`), retirás lo que dejó de
   funcionar, ajustás la cartera al régimen de mañana y repartís el riesgo por cuenta. Con urgencia: la cola de investigación del
   plan (`PLAN_ACTUAL.json`) manda sobre el resto de tu trabajo; lo P0 se resuelve en el día (reemplazar retiros, cubrir huecos de
   régimen con familias chicas pre-registradas), lo P1 en 24 h (dar de alta en PAPEL lo que tiene réplica a favor, destrabar). Todo lo
   que entra a la cartera entra pre-registrado; habilitar cuentas reales y cambiar `alfa_real`/`dd_max_r` es humano.

9. **Lo aprendido el 2026-11-08 (Nico).** Trabajá siempre sobre el estado actual del repo (`foundation`). La búsqueda de régimen
   offline no superó al azar y la mejor celda estática le ganó a la de los últimos meses (`docs/research/regimen_busqueda_20261108/`);
   lo elegido en grillas grandes cae a ≈ 0 en la réplica por selección, no por costos (`docs/research/bruto_neto_pistas_20261108/`).
   Regla global: estabilidad en 5 sub-bloques, canastas poco correlacionadas de varios activos y nulo que repite la selección completa
   (`docs/DECISIONES_20261108.md`, `edgelab/research/canasta_global.py`). Generá el cubo de cada campaña nueva para que entre al universo.
10. **Creatividad e investigación (Nico 2026-11-08).** Hacen falta más estrategias y mejores, y vos sos el que más puede aportar. En cada
   ciclo de propuesta:
   - **Conectá lo que está separado.** El repo tiene mecanismos que nunca se combinaron: leé `docs/research/APRENDIZAJES_ESPIRAL.md`,
     `docs/research/atlas_ideas_r_20261102/`, `docs/research/LINAJES.jsonl`, los RESULTADO de cada carpeta y el meta-análisis
     (`tools/metaanalisis_embudo.py`). Proponé cruces concretos: una señal de una familia como filtro de otra, un sensor en un activo y
     la ejecución en otro (como U1-CRUZADO), una salida que funcionó en una familia aplicada a otra, lo que fue SIN_POTENCIA en un activo
     probado en canasta con otros.
   - **Aportá ideas propias**, que no salgan de lo ya medido: al menos una por ciclo, con mecanismo económico y forma de refutarla.
   - **Investigá afuera**: papers, microestructura y práctica (web), y traé la evidencia citada en la propuesta. La inspiración externa
     se mide con nuestras reglas antes de creerla.
   - **Pocas reglas, buen motivo.** Preferí familias chicas con justificación económica a barridos de cientos de miles de celdas, y
     pensalas desde el principio como piezas de una canasta diversificada (otros activos, otros horarios, baja correlación).
   - Todo lo creativo pasa por la misma estructura: pre-registro, contador, linaje, embudo y holdout.
11. **Frecuencia (Nico 2026-11-08).** Buscá estrategias que operen mucho más seguido: una canasta con 30 operaciones por mes no se puede
   confirmar nunca. Apuntá a ≥ 0,5 operaciones por sesión por regla y ≥ 3 por sesión por canasta. La forma preferida de ganar frecuencia
   es correr la misma regla con motivo económico en los 14 activos de la release (no suma selección); después, familias en velas de pocos
   ticks y varios horarios. Condición de diseño: el recorrido típico por operación tiene que ser varias veces la fricción canónica del
   instrumento (con objetivos chicos la fricción se come la ganancia: `docs/research/orb_nq_20261108/RESULTADO_VARIANTES.md`).
12. **Memoria de ideas (Nico 2026-11-08).** En cada ciclo recibís `memoria_ideas`: el índice de ideas externas
   (`docs/research/ideas_externas/INDICE.md`, reels que junta Nico), un reel completo que rota y hallazgos robustos del CerebroSSRN
   (`corpus/ssrn/cerebro/`). Usalos para combinar ideas (p. ej. tamaño del gap de Kemet × momentum de cierre de Gao/Baltussen ×
   régimen de gamma) y proponer familias nuevas con motivo económico. Lo que dice un reel o un paper no es evidencia: se mide con
   pre-registro, costos canónicos y R. Mirá el estado en el índice antes de repetir algo ya medido; si medís una idea, actualizá su línea.
