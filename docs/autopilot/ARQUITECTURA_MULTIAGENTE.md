# Arquitectura multiagente del autopilot (consolidada y aplicable) — 2026-10-19

Estado: VIGENTE — referencia de la arquitectura multiagente; roles LLM apagados por defecto (encendido por etapas, §6).

Documento de referencia de qué agentes hay, qué modelo usa cada uno, qué ve, qué decide y cómo se enciende.
Reemplaza la propuesta suelta del chat. Código: `edgelab/autopilot/` · despliegue: `deploy/debian/`.

## 1. Principio
**El código orquesta; los modelos responden.** Ningún LLM lanza corridas, toca el alfa, cambia guardas, escribe código ni
abre datos. Cada rol es una llamada `claude -p` sin herramientas ni MCP, con salida JSON validada contra un esquema,
tope diario, caché por hash de entrada, gobernador de rate limit y registro en `llm_calls.sqlite` (rol, modelo exacto,
hash de entrada y salida, tokens). Ninguna salida de un rol es evidencia.

## 1b. Criterios del dueño que todo rol pondera (2026-10-19)
- **Macro antes que micro:** horizontes y movimientos grandes; la fricción se come los efectos chicos (ver `friccion.py`, ratio ≥ 3).
- **Régimen:** una estrategia puede no ser rentable siempre pero sí ahora; vale si el régimen se detecta en tiempo real con regla pre-registrada y estabilidad medida fuera de muestra.
- **Cartera:** muchas estrategias rentables y poco correlacionadas diversifican más que una sola; la baja correlación con lo vivo pesa tanto como el rendimiento.
Están en `contexto.PRIORIDADES` (las ve el proponente en cada ciclo) y en la consigna del revisor.

## 2. Capas
```
            ┌────────────────────── CAPA DETERMINISTA (sin LLM) ───────────────────────┐
 timer 10'  │ daemon.tick: PAUSE/PAUSE_SALA → protegidos → cerrar corridas → Holm      │
            │ al nivel apostado → alfa → Brain → lanzar (guardas + registro global)    │
 timer diario│ conocimiento.indexar (biblioteca trazable) · generate (candidatas)      │
 timer 30'  │ watchdog (latido, unidades, envíos inciertos) → alertas                  │
            └───────────────┬───────────────────────────────────────▲──────────────────┘
                            │ paquetes armados por código            │ salidas JSON validadas
            ┌───────────────▼────────────── CAPA DE ROLES (LLM) ────┴──────────────────┐
            │ proponente → [mecánico] → revisor → revisor2 → pre-registro publicado    │
            │ auditor (post-corrida) → abogado del diablo (sólo hallazgos)             │
            │ lector · bibliotecario · cronista (resúmenes)                            │
            └──────────────────────────────────────────────────────────────────────────┘
```

## 3. Roles, modelos y límites
| Rol | Modelo (fijado) | Tope/día | Recibe | Devuelve | Efecto |
|---|---|---|---|---|---|
| proponente | `claude-opus-5-5` | 6 | prioridades, lente rotativa, tablero (retiradas, edges, corridas, auditorías), fichas citables de la biblioteca (research propio y papers por separado), vacíos | 1 familia falsable, ≤3 parámetros, refs | borrador en `propuestas.jsonl` (con fuentes exactas y huella de la biblioteca) |
| revisor | `claude-opus-5-5` | 10 | pre-registro, métricas públicas, antecedentes | PROMOTE / KILL / DERIVE | primer filtro |
| revisor2 | `claude-sonnet-5-5` | 10 | **la misma entrada**, sin la razón del primero, consigna escéptica | PROMOTE / KILL / DERIVE + riesgo | sólo se llama si el primero dijo PROMOTE; hacen falta **los dos** |
| auditor | `claude-sonnet-5-5` | 20 | pre-registro, especificación lanzada, decisión numérica, chequeos mecánicos | CONFORME / DESVIO / SOSPECHA_FUGA | estado de la corrida en `auditorias.jsonl` |
| abogado | `claude-opus-5-5` | 6 | hallazgo (hit), pre-registro, antecedentes | explicación no-edge, tipo, prueba refutadora, gravedad | gravedad alta → EN_DUDA |
| lector | `claude-haiku-5-5` | 200 | resultados | resumen por familia | informes |
| bibliotecario | `claude-haiku-5-5` | 100 | pasajes de papers | fichas (afirma, a favor/en contra) | enriquece la biblioteca |
| cronista | `claude-haiku-5-5` | 100 | hechos del ciclo (números aparte) | texto para la sala | `sala_outbox.jsonl` |

Los modelos se cambian sin tocar código con `"modelos": {...}` en `/etc/edgelab/autopilot.json`.
Por qué así: Opus donde la calidad del razonamiento decide (crear y adjudicar, refutar), Sonnet como segunda mirada de
otra familia de modelo y para auditoría estructurada, Haiku para tareas mecánicas de alto volumen.

## 4. Flujo de una idea, de punta a punta (con dónde queda cada rastro)
1. **Biblioteca** (`index`, diario): Brain, papers SSRN, research, registros, resultados → `biblioteca.json` + `biblioteca_manifiesto.json` (sha256 y commit por fuente).
2. **Propuesta** (`propose`, si `proponente: true`): paquete armado por código → proponente → filtro de novedad → `propuestas.jsonl`.
3. **Candidatas** (`draft`): evidencia + literatura + resultados vivos → borradores de pre-registro.
4. **Promoción** (`auto-promote`, si `auto_promocion: true` y la enmienda AUTONOMIA-A1 está firmada): mecánico → revisor → revisor2 → pre-registro committeado y **publicado** en `autopilot/prereg/<run_id>` → guardas → `candidates.json` → `promociones.jsonl`.
5. **Lanzamiento y cierre** (`tick`, cada 10 min): registro global de pruebas antes de lanzar, alfa apostado, Holm propio, Brain.
6. **Auditoría** (`audit`, diario): mecánica siempre; auditor y abogado si `auditor: true` → `auditorias.jsonl`. Un hallazgo EN_DUDA o BLOQUEADO lo ve el proponente en el tablero y queda para revisión humana.
7. **Pedidos a humano** (`pedidos.py`): lo que sólo una persona puede dar (datos, exportación NT8, credencial, decisión) se pide con id en `pedidos_humano.jsonl` y en la sala; se cierra con `resuelto <id>`; el vigilante avisa si pasan 72 h. Los bloqueos del ciclo por datos faltantes se convierten solos en pedidos.
8. **Sala y alertas**: cronista o plantilla → `sala_outbox.jsonl`; watchdog → `alertas.jsonl`.
Todo lo anterior se sube a la rama `autopilot/state` (`sync_state.sh`); `runs.sqlite` se respalda a diario.

## 5. Qué NO puede hacer ningún agente
Cambiar guardas, FDR, holdout, mandato o protegidos (STOP si cambian) · lanzar sin pre-registro committeado y publicado ·
leer el holdout · subir el alfa · promover a edge (todo hallazgo es exploratorio hasta réplica pre-registrada) ·
levantar una pausa de consola · escribir código del motor (eso es una sesión aparte con PR, tests y revisión humana).

## 6. Encendido por etapas (configuración)
| Etapa | `/etc/edgelab/autopilot.json` | Llamadas LLM/día (techo) | Pasar a la siguiente si |
|---|---|---|---|
| 0 | `mode: propose`, sin `roles_ledger` | 0 | 1–2 semanas sin incidentes; watchdog verde |
| 1 | `mode: execute`, `max_per_day: 1`, candidatas promovidas a mano | 0 | prueba punta a punta en SV1 OK |
| 2 | + `roles_ledger`, `sala.cronista: true`, `auditor: true` | ~30 (Haiku/Sonnet) | auditorías coherentes con revisión humana de 5 corridas |
| 3 | + `proponente: true` | +6 Opus | propuestas no repetidas y con fuentes citadas |
| 4 | + `auto_promocion: true` (enmienda firmada), `max_por_ciclo: 1` | +≤20 (revisores) | tasa de PROMOTE doble < 30 %; ninguna BLOQUEADA en 2 semanas |

## 7. Métricas para ajustar la estructura
- hallazgos replicados por 100 llamadas de Opus, por lente (`propuestas.jsonl` × `auditorias.jsonl` × ledger);
- tasa de PROMOTE del revisor y del revisor2 y su acuerdo (si coinciden > 95 %, el segundo no aporta: cambiar consigna o modelo);
- fracción de corridas EN_DUDA/BLOQUEADA (si sube, revisar el generador de candidatas, no aflojar el auditor);
- costo y tokens por rol (`RoleRunner.usage`).
