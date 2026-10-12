# Generación de candidatas (autopilot)

Objetivo: que cada ronda proponga corridas con más chance de aportar información que la anterior, sin reducir el rigor ni gastar alfa de más.

## Flujo
`evidencia propia (evidence_seed.json + resultados vivos) + literatura (literature_leads.json)` → **reglas** (`generate.rules`) → candidatas con procedencia a favor Y en contra → **puntuación** → borradores de pre-registro + RunSpec → revisión humana y commit → `promote` → `candidates.json` → ciclo del autopilot → resultado → **evidencia viva** (`evidence.record_outcome`) → la siguiente ronda ya sabe qué se confirmó, qué falló y qué muestra se consumió.

## Reglas actuales (cada una es una conexión entre piezas de información)
| Regla | Conecta | Ejemplo generado |
|---|---|---|
| R1 réplica de pista débil en muestra no usada | pista débil + muestra independiente sin consumir | SLOT-1: la reversión 04:30 CT de GC en otros activos |
| R2 puente información → mecanismo publicado | hallazgo de información (gamma→amplitud) + literatura (momentum intradía por cobertura de gamma) | IDM-1: «resto del día → última media hora» y su modulación por gamma, ventana de 30 min (la de GEX-1 era de 90) |
| R3 chequeo de artefacto | resultado sospechoso de microestructura + literatura de rebote bid-ask | OU-2: ZB con precio medio |
| R4 ampliar potencia | efecto grande en una muestra y sin potencia en otra | GEX-2: NQ/YM spot |
| R5 información → dirección | efecto en amplitud sin dirección probada | AVCL-2 (dueño: sesión local) |

## Puntuación (valor esperado de información)
`score = p0 · potencia / √(costo/600 s)`, con `p0 = (1 + aciertos_familia + w·pro) / (5 + n_familia + w·(pro+contra))` (w = 0,5). Los aciertos son los del libro de corridas ya analizadas; la literatura pesa la mitad que un resultado propio y las afirmaciones **en contra** suben el denominador (bajan p0). La potencia es un supuesto declarado por regla, no una medición.

## Qué impide que esto se convierta en pesca de resultados
- Toda candidata paga multiplicidad: se cuenta en el registro global antes de lanzar y apuesta alfa (alpha-investing). Priorizar no regala significancia.
- Una candidata declara la **muestra independiente que consume**; si ya se consumió (resultado vivo), no se vuelve a proponer.
- La configuración que llega al kernel (`STUDY_CFG`) debe figurar **textualmente** en el pre-registro committeado; el guard lo verifica.
- Los borradores no se auto-aprueban: los committea y promueve un humano (`tools/autopilot_generate.py promote`).
- La literatura es `LITERATURE_CLAIM_UNVERIFIED` y `claims_are_evidence=false`.

## Integración con Research Ops (#117/#118)
`research_directives.json` ya sale en el formato que espera `research_cycle.plan_research` (`gap_kind` del vocabulario `GAP_KINDS`, `missing_evidence`, pregunta pública neutral + pregunta contraria, `public_query_reviewed=False`). Cuando ambas ramas converjan: (1) el planificador de Research Ops consume esas directivas con su presupuesto durable (`DispatchLedger`); (2) sus recibos reemplazan a `literature_leads.json` escrito a mano; (3) la cola/presupuesto de Research Ops reemplaza a `RunLedger` para recuperación tras reinicio. Hoy no se fusionan porque viven en bases distintas.

## Qué falta
Scripts para GEX-2, OU-2 (precio medio) y AVCL-2; más reglas (barrido horario en índices con spot 2018+, cruce con condiciones de volatilidad); estimación de potencia medida (no supuesta) a partir del nulo de cada estudio; actualización automática de `literature_leads.json` desde Research Ops.
