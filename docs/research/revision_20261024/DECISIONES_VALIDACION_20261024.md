# Decisiones de validación del 2026-10-24

Estado: VIGENTE — aprobadas por Nico el 2026-10-24 (02:30 UTC) sobre la propuesta de la sección 4 de `REVISION_20261024.md`.
Palabras de Nico sobre el OOS: «Si pero con matices: algunas estrategias funcionan por régimen, y eso no significa que no ganen
plata ahora. Por ejemplo, la de hoy parece que si funciona en este momento, pero no en 2023 por ejemplo.»

Son cambios de semántica de validación, así que quedan escritos acá con su regla exacta. Ninguno relaja una compuerta: los
cuatro endurecen, salvo el matiz de régimen, que evita que un OOS sin potencia o de otro régimen **declarado antes** mate un edge actual.
No se tocó ningún archivo del manifiesto de protegidos (`config/autopilot/protected.json`).

## D1. Nominación FDR como compuerta dura de DESC
- **Antes:** DESC elegía candidatas por IC90, meseta y sesiones aunque el tamiz FDR no nominara nada. EXPZ-NQ y EXPZ-CFD pasaron
  3 candidatas cada una con **0 nominadas**.
- **Ahora:** una pista sólo puede ser candidata si el FDR del canal (Storey, q = 0,10, sobre TODAS las celdas del canal, las no
  evaluables con p = 1) la nomina. El q no se configura por campaña (`embudo.Q_FDR_DESC`). Romano-Wolf queda como diagnóstico
  (se publica umbral, rechazadas y p del máximo; no decide).
- **Código:** `grilla_generica.canales` marca cada pista con `q_fdr`, `nominada_fdr`, `pi0_fdr`, `m_fdr` usando los q-valores
  completos (la lista `nominadas` tiene tope y no sirve para esto). `embudo.nominada()` y `_fin_desc` aplican la compuerta.
  `escalera.evaluar` tampoco confirma una réplica de algo no nominado (scripts sueltos).
- **Consecuencia ya visible:** al aplicarse, las dos EXPZ quedan `SIN_CANDIDATAS` (test `test_expz_en_curso_queda_sin_candidatas`).
  Se aplica también a campañas que ya pasaron DESC (`Embudo._revalidar_20261024`): una pista sin la marca cuenta como no nominada.

## D2. OOS por régimen, con potencia
- **Antes:** el OOS nunca mataba («principio de edges actuales»).
- **Ahora**, por candidata (`Embudo._fin_oos`):
  | veredicto | condición | efecto |
  |---|---|---|
  | `REFUTADA_OOS` | potencia ≥ 0,8 para `fraccion_efecto` (0,5) × media de DESC, IC90 entero < 0, y el OOS toca el régimen actual | sale; si salen todas, la campaña cierra `REFUTADA_OOS` |
  | `EN_CONTRA_OTRO_REGIMEN` | lo mismo, pero el OOS cae entero antes de `regimen.actual_desde` | sigue viva |
  | `NO_CONCLUYENTE` | sin potencia (o no evaluable) | sigue viva, no suma |
  | `A_FAVOR` / `SIN_RECHAZO` | según el paso de LORD++ de la familia | sigue viva |
- **Régimen:** la campaña declara `regimen.definicion` (texto) y `regimen.actual_desde` (YYYYMMDD) en el JSON **antes del PREFLIGHT** (después la campaña no se puede editar: quedaría BLOQUEADA); quedan
  congelados en el estado. `actual_desde` tiene que ser anterior al holdout (el régimen se define con desarrollo, nunca con el
  holdout). Sin declaración, el OOS cuenta como del régimen actual: no hay excepción a posteriori.
- La confirmación de una candidata viva sigue saliendo del holdout (que es, por construcción, el régimen actual).
- **Para U1:** su OOS 2023–2025 sólo podría leerse como «otro régimen» si la definición se escribe antes de re-correrlo con el fix 27.

## D3. α reservado por acta, libro único con lock, p de Romano-Wolf corregido
- **Reserva:** el ACTA consume su paso de LORD++ en el momento de escribirse (`LibroLord.reservar`), con el nivel fijo; el HOLDOUT
  decide a ese nivel (`LibroLord.resolver`). Antes el acta anotaba `nivel()` sin descontarlo: dos actas de la misma familia, o un
  OOS entre medio, se adjudicaban el mismo α. Mientras una reserva está pendiente cuenta como no rechazo para los pasos siguientes
  (sólo les deja menos nivel; LORD++ asincrónico, Zrnic-Ramdas-Jordan 2021), así que el FDR sigue controlado.
- **Libro único:** `edgelab/funnel/libro_lord.py::RUTA_CANONICA` = `docs/research/LIBRO_LORD.json` (versionado, como
  HOLDOUT_VENTANAS). Otra ruta sólo con `permitir_otra_ruta=True` (tests). El ciclo del Debian y `tools/embudo_correr.py` usan
  este libro (`--libro` se eliminó). **Si en el Debian existe `<root>/libro_lord.json` con pasos gastados, hay que pasarlos al
  libro canónico antes de la próxima corrida** (hoy ninguna campaña del embudo llegó a OOS).
- **Lock:** cada lectura-modificación-escritura toma un lock exclusivo del sistema operativo (`fcntl` en Debian, `msvcrt` en
  Windows) y relee el disco adentro. Test con 6 procesos concurrentes.
- **Romano-Wolf:** `p_rw_del_maximo = (1 + #{max* ≥ t_max}) / (B + 1)` (nunca 0) y `B` por defecto 1000 (antes 200) en
  `grilla_masiva.romano_wolf` y `grilla_generica.B_RW`. La memoria es B × celdas evaluables × 4 bytes (≈ 40 MB con 10.000).

## D4. Herencia de multiplicidad del linaje
- **Antes:** U1-CRUZADO figuraba con ~20 pruebas (`AREAS_EXP_1_CRUZADO`) saliendo de un linaje de 19.408.976.
- **Ahora:** toda familia que entra al embudo declara su linaje en `docs/research/LINAJES.jsonl` (append-only) antes de su DESC
  (`edgelab/research/linaje.py`). Por defecto el número heredado es `"bruto"`: todas las pruebas de los padres en el registro
  global más lo que ellos heredan, sin descuento por correlación. Un número menor exige `justificacion_descuento`. Una corrección
  sólo puede subir el número o agregar padres. Los padres que `HOLDOUT_VENTANAS.jsonl` ya vincula (`relacionadas`) son obligatorios.
- **Dónde muerde:** en DESC, `q_linaje = q_BH · (m + N_heredado) / m` (las heredadas como si hubieran estado en el mismo tamiz,
  π0 = 1) tiene que quedar ≤ 0,10. En el ACTA se anotan la multiplicidad total, el recorte de Harvey-Liu sobre ella, el efecto
  esperado y la potencia del holdout a N fijo (información; la decisión es el paso de LORD++).
- **Declarados hoy:** `AREAS_EXP_1_CRUZADO` ← `AREAS_EXP_1_NQ`, `AREAS_EXP_1_USATECH` (19.408.976); `LUXIMB_IMPULSOS`,
  `LUXIMB_ESCALONADAS_AREA`, `LUXIMB_FUT_VS_CFD` ← `LUXIMB_FADE_VISOR`; `EXPANSION_ZONAS` ← `LUXIMB_FADE_VISOR`, `LUXIMB_IMPULSOS`,
  `AREAS_EXP_1_CRUZADO` (19.409.082; declarado después de su DESC, sólo endurece).
- **Para U1 y LUX-IMB:** con lo heredado, ninguna celda de desarrollo puede nominarse; siguen siendo hipótesis a confirmar sólo
  con sesiones desde el 2026-10-23 (ventanas consumidas), con una apertura por familia.

## Lo que queda abierto (propuesta, no aplicado)
- **Dos canales por campaña.** DESC corre el FDR por separado en `total` y `reciente` (cada uno a q = 0,10), así que la campaña
  entera controla ~2q. Alternativas: un solo BH sobre los dos canales, o q/2 por canal. Lo decide Nico.
- **Campañas hermanas de una familia** (EXPZ-NQ y EXPZ-CFD): el linaje sólo cobra lo heredado de los padres, no lo que prueba la
  campaña hermana. Cobrarlo sería coherente con D4; lo decide Nico.
- **Ancestros sin declaración** (`AREAS_EXP_1_NQ`, `AREAS_EXP_1_USATECH`, `LUXIMB_FADE_VISOR`): cuentan sólo sus pruebas propias.
  Si derivan de algo anterior, hay que declararlo.

## Enmienda del mismo día: falsos negativos (`FALSOS_NEGATIVOS_EMBUDO_20261024.md`)
A pedido de Nico («que el embudo no descarte candidatas reales, manteniendo el control del error»):
- **D1:** el m del FDR pasa a ser el de las celdas **evaluables** (filtrado independiente); se publican las dos cuentas. Cero
  nominadas ya no cierra la campaña: van las top-k pistas a réplica en lote, con un paso de LORD++ (etapa `PISTAS`).
- **D4:** el linaje es **información** por defecto (`linaje_como: "informacion"`); sigue como compuerta sólo con
  `"compuerta"` o en estados congelados antes de la enmienda.
- La meseta ordena y no mata; el bootstrap resuelve el umbral nivel/m (o usa el p analítico por sesión); se evalúan todas las
  nominadas por FDR; el número efectivo usa Li-Ji cuando hay matriz de P&L.

Aporte al referente: cierra las cuatro vías por las que el embudo podía promover algo sin evidencia (sin nominación, con α
compartido, con p = 0, con el contador en cero) y evita matar un edge actual por un OOS sin potencia o de otro régimen declarado.

## D5 (2026-10-24, tarde). Reuso de las sesiones del holdout miradas en exploración
Decisión de Nico: «aunque se haya usado luego el holdout fue en otra computadora y un análisis bastante simple, así que si
reutilizamos esos datos no nos arriesgamos tanto y el valor de la información que obtenemos es mayor al riesgo».
- **Alcance:** sólo U1-CRUZADO (`AREAS_EXP_1_CRUZADO`) y la regla del visor de LUX-IMB (`LUXIMB_FADE_VISOR`). Son las dos familias
  cuya regla se congeló ANTES de la mirada y no cambió después. Las familias derivadas (EXPANSION_ZONAS y otras) **no** heredan
  el reuso.
- **Condición:** el estadístico tiene que ser válido ante miradas, un e-proceso (`edgelab/funnel/secuencial.py`) que arranca en la
  frontera (2026-10-01). La mirada previa no lo invalida y se puede seguir sumando sesiones. Se reporta siempre también el
  resultado sin las sesiones miradas.
- **Riesgo declarado:**
  - U1: la mirada fue favorable (8 operaciones). Seguir mirando porque dio bien es una selección leve; el e-proceso la tolera.
  - LUX: la mirada fue desfavorable (14 de 14 en SL), así que incluirla es conservador.
- **En código:** `edgelab/research/holdout_ventanas.py` (`reuso_autorizado`; el embudo lo acepta sólo con `estadistico="e_proceso"`).
  Libro: `docs/research/HOLDOUT_VENTANAS.jsonl` (filas `reuso_autorizado`).
