# AVZVOL — selección causal y evidencia de competidores D-1

**Datos/research siguen BLOQUEADOS. Sin outcomes económicos.**
[Registro para agentes](../../config/research/avzvol_selection_readiness_review_v1.json).
Base del refuerzo: `f35246944d3d8e9847e71002ae982d149936aeaa`.

## Límite encontrado y reproducido

El gate anterior comprobaba el calendario declarado, volumen/spread del contrato
seleccionado y hash del régimen. No exigía en ese punto evidencia de todos los
competidores ni sus timestamps de disponibilidad. Un fixture inventado con
selección incoherente, conservando volumen del elegido y reseal de metadatos,
pasaba. Es un límite de consistencia, **no un bypass de autenticación ni una prueba
de sesgo en AVZVOL**: un hash recalculado nunca fue aprobación externa.

Ahora `require_research_eligibility` exige `certificate.selection_review` antes de
abrir cualquier fuente. El lector de sesión y el consumidor opt-in de agregados
heredan el rechazo. No se reescribieron loaders legacy; siguen prohibidos como bypass.

## Nuevo requisito de evidencia (NO generador de certificados)

`selection_review.schema = "edgelab_reviewed_prior_challengers_v1"`, con:

- `root`; referencias SHA externas `calendar_evidence_sha256` y
  `universe_evidence_sha256`; `universe_review`, `calendar_review`, `asof_review`
  iguales a PASS como **afirmaciones de revisión externa**, no veredictos del código.
- `contract_metadata_sha256`: digest `seal` de TODOS los registros de contratos del
  root, ordenados por `contract`; no sólo el elegido o el old/new del roll.
- `decisions["ROOT|YYYYMMDD"]`: `trade_date`, `signal_trade_date` D-1,
  `evidence_sha256`, `cutoff_review=PASS`, `previous_session_close_utc`,
  `target_session_open_utc`, `decision_cutoff_utc`,
  `contract_metadata_available_at_utc` y lista exacta `candidate_contracts`.
- Cada `certificate.sessions["ROOT|CONTRACT|D-1"]`: status PASS,
  `complete_session=true`, `trade_quantity`, `available_at_utc`,
  `evidence_sha256`. Los timestamps deben tener zona explícita.

El universo de candidatos debe concordar exactamente con la cobertura contractual
declarada para D-1. Se exige incluso evidencia del competidor backward aunque la
política monotónica impida volver a él. **Cobertura observada no es vida/listado ni
conocimiento histórico de disponibilidad**: esos límites deben ser revisados y
conocidos as-of, no derivados del último tick de una muestra futura.

Una fila faltante, incompleta, sin evidencia o conocida después del cutoff produce
STOP. El cero sólo se acepta como medida explícita revisada para un competidor;
el contrato elegido sigue necesitando volumen positivo y los límites congelados
externos. No se inventan mínimos, calendarios, medianas móviles ni permisos.

Orden temporal requerido: cierre previo <= disponibilidad del volumen <= cutoff
<= apertura destino. El universo también debe estar disponible al cutoff. El
código sólo compara declaraciones fijadas; **no valida la verdad del calendario,
el clock o que todos los contratos reales estén censados**. Esa revisión sigue
siendo externa y necesaria. Un timestamp agregado a mano no subsana la ausencia.

Se recomprueba la política ya definida: inicialización con líder D-1, tie que
conserva current (si no existe, vencimiento más cercano), crossover estricto y
avance sin roll backward. Se comparan contrato/leader/decisión y ambos volúmenes;
no se calcula ningún precio, outcome, P&L o sesgo científico.

## Compatibilidad y situación real

Los certificados futuros sin `selection_review` ahora fallan: endurecimiento
intencional, sin defaults ni adaptador que fabrique revisiones. No convertir la
matriz del catálogo ni los fixtures de tests en certificados reales. Los pins
siguen viniendo de autoridad externa; no hay autenticación nueva del aprobador.

Se volvió a descargar catalog/RESOLVER v15 vía Kaggle MCP con versión explícita:
SHA idénticos a los fijados. Siguen las 261 sesiones candidatas aprobadas y los
cinco rolls declarados MNQ. v15 no presenta la política causal requerida por el
consumidor. Esa concordancia no acredita D-1 completo, todos los challengers ni
as-of; no se cambió v15 ni se emitió un resolver nuevo.

El profiler dataframe no puede representar esos JSON heterogéneos. Se validaron
shapes/fechas/conteos por JSON nativo y pins, sin inferir corrupción de ese error.
El escaneo físico previo sigue siendo [estructura solamente](AVZVOL_MNQ_RAW_QUALITY_20261010.md).

## Qué falta y cómo seguir sin economía

1. Conseguir revisión independiente de calendario, reloj y continuidad de cada
   fuente, incluida semántica de quotes/agresor y logs/exportador.
2. Medir/reconciliar una matriz D-1 completa de TODOS los contratos competidores,
   por fuente/versión, contra evidencia upstream; distinguir sesión incompleta,
   cierre programado, actividad cero demostrada y ausencia UNKNOWN.
3. Revisar disponibilidad histórica del universo, selección/elegibilidad as-of y
   warmup de 45 días. Mantener la exposición fuera de la máscara como pendiente.
4. Revisar método, pares/pesos/reutilización/solapamiento y censos/matching de P1/P2;
   congelar endpoints/reloj/censura/potencia de P3. No seleccionar reglas por outcomes.
5. Obtener aprobación/pins separados para una revisión científica nueva; conservar
   originales y exposición. P4 **prohibida hasta nueva autorización explícita**.

R7/K8 permanecen abiertos; reviewed_input_pins/source_quality_review_refs quedan
null. Las cuatro propuestas y el gate D de réplica no se sustituyen por esta QA.
