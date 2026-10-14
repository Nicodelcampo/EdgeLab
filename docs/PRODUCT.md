# EdgeLab — producto, objetivo y roadmap

Estado: VIGENTE  
Fecha: 2026-10-14

> Versión 1 — 2026-10-14. Autoridad: `docs/NORTH_STAR.md` manda sobre este documento. El mapa de módulos es `docs/MODULES.md` (generado desde `config/modules.json`); las reglas de documentación son `docs/DOCUMENTATION_PROTOCOL.md`.

## 1. Qué es EdgeLab
**Un sistema que encuentra, valida y despliega edges de trading en futuros CME, rechazando los falsos antes de arriesgar capital.** No es una colección de indicadores ni de backtests: es una cadena de custodia que va del dato crudo a una decisión operable, con cada paso trazable y refutable.

**Objetivo único (North Star):** encontrar edges válidos y aplicables en el mercado, con expectativa económica **neta** (después de comisión, spread y slippage), válida fuera de muestra, robusta ante múltiples pruebas y ejecutable en las cuentas reales.
**Qué NO es objetivo:** paridad exacta, infraestructura o visor por sí mismos. Son medios.
**Métrica de progreso:** cuánto reduce la distancia hacia un edge neto, robusto y operable. Hoy: **0 edges promovidos** (`EDGES_DISCOVERED.md`).

## 2. Para quién
- **Nico:** decide aprobaciones (licencia, política de liquidez, P&L, holdout, cuenta), pone el capital.
- **Agentes de IA** (Claude local, Gemini, Notion, otros): ejecutan, auditan y proponen. Deben poder continuar sin la conversación previa: todo lo que decide algo vive en el repo.

## 3. Cómo está armado
Ocho capas; una dependencia nunca apunta a una capa superior (lo verifica `tools/check_modules.py` en CI).

| Capa | Qué hace | Módulos principales |
|---|---|---|
| 0 Captura | Saca datos de NT8 y de las firmas | `nt8-capture` |
| 1 Base | Rutas, instrumentos, sesiones, regímenes | `config-core`, `sessions` |
| 2 Datos y custodia | Contratos, calendario, compuertas, release canónica, Kaggle | `data-custody`, `liquid-release`, `kaggle-custody` |
| 3 Indicadores | Barras, footprint, kernels con paridad contra NT8 | `bridge-kernels` |
| 4 Contexto y búsqueda | Contexto causal, estadística, campañas pre-registradas | `context`, `stats`, `research`, `external-models`, `gex` |
| 5 Ejecución y validación | Fills a nivel tick, arnés anti-lookahead, props | `execution-engine`, `validation`, `propfirm` |
| 6 Memoria y gobernanza | Registro de lo medido, fábrica de hipótesis, reglas | `edge-brain`, `edge-factory`, `governance` |
| 7 Operación | Visor y puente multi-IA | `viewer`, `agent-bridge` |
Detalle de funciones, entradas, salidas, dependencias, documentos y tests por módulo: `docs/MODULES.md`.

### La cadena de un candidato (orden obligatorio)
`idea con justificación económica y condición de refutación` → `geometría/lifecycle target-free` → `información (¿predice algo?)` → `P&L bruto` → `edge neto y replicado` → `holdout sellado (una sola apertura)` → `ejecución real`.
Cada salto necesita su propio manifiesto, N efectivo de hipótesis y OK de Nico antes de tocar retornos.

## 4. Estado a 2026-10-14
| Pieza | Estado |
|---|---|
| Datos de ticks | Release v4 publicada, verificada, auditada y **aprobada** (2026-10-14, uso privado); límites en `docs/infra/RELEASE_APPROVAL_20261014.md` |
| L2 | ≈62 GB en una PC, 34–60 sesiones por producto; sin respaldo; poco poder |
| Mediciones | HFTZones: 5 mediciones, ninguna positiva. BigTrap2 imán: cerrado. AVZP2: O5 real (no edge), O1 refutado. GC presión/progreso: décimas de tick |
| Fricción ES | ≈3,4–3,6 ticks por viaje (spread medido + comisión + slippage declarado) |
| Pruebas | Suite completa (`pytest tests -m "not vectorbt"`) en verde tras la unificación; ver `docs/DECISIONES_20261014.md` |
| Código | Una sola línea: `main` se integró en `foundation` con merge real (2026-10-14) |

## 5. Roadmap
Cada fase tiene un criterio de salida verificable. El orden sigue la jerarquía del North Star.

| Fase | Objetivo | Criterio de salida | Estado |
|---|---|---|---|
| **R0 Datos cerrados** | Release aprobada, faltantes P0 resueltos o acotados, respaldo, captura continua | Aprobación de Nico; manifiesto v-final; respaldo con hashes; captura diaria automática | release aprobada (`docs/infra/RELEASE_APPROVAL_20261014.md`); respaldo local verificado; chequeo diario y runbook de captura (`docs/infra/CAPTURA_CONTINUA_RUNBOOK.md`). **Falta (requiere NT8/Nico):** reanudar la captura L2 (cortada el 2026-09-27), exportar los P0 y una copia fuera de la PC |
| **R1 Un producto, una línea** | Unificar `main` y `foundation`, reconciliar `CLAUDE.md`, módulos registrados, documentación con protocolo e índice | `tools/check_modules.py` y `tools/docs_index.py --check` verdes en CI; una sola rama viva; entrada única | **hecho (2026-10-14)** |
| **R2 Viabilidad económica target-free** | Medir cuántos ticks de recorrido existen frente a la fricción real, por activo, hora y régimen | Tabla publicada con MDE; ideas que no pagan fricción, cerradas | **hecho (2026-10-14, provisional)**: `docs/research/R2_RECORRIDO_VS_FRICCION_RESULTADOS_20261014.md`. Siguiente: R3 (manifiesto de dirección a 15–60 min en índices, requiere OK de Nico) |
| **R3 Campañas de información** | Familias registradas con N efectivo, multiplicidad y refutación | Manifiestos aprobados; actas MEDIDO/NO MEDIDO al día | desbloqueada por R2; falta manifiesto y OK de Nico |
| **R4 Edge neto** | P&L bajo manifiesto con costos de la cuenta elegida; G0–G5 | Un candidato que supera costos, OOS, MCPT/PBO/SPA y holdout | sin candidato |
| **R5 Ejecutabilidad** | Feed vivo, slippage y fills reales, kill switch, paper/sim | Brecha research↔live medida y acotada | sin empezar |
| **R6 Portafolio y operación** | Varias apuestas descorrelacionadas, monitoreo, cerebro recursivo 24/7 | Cartera con riesgo acotado y control en operación | sin empezar |

## 6. Principios de producto
1. **Un dato, una fuente de verdad** (manifiesto + hash). Lo que no está en el repo no existe para otro agente.
2. **Cada módulo tiene una función, un dueño documental y tests**; el registro lo hace cumplir.
3. **Lo muerto se registra con alcance preciso** y no se reabre sin evidencia nueva (Edge Brain y registro MEDIDO/NO MEDIDO).
4. **Integridad antes que interpretación**: un resultado con datos o nulo defectuosos queda provisional.
5. **Los agentes proponen, el repo decide**: los parches de otros agentes se revisan; nada se aplica ni se ejecuta automáticamente.
6. **Sin P&L, holdout ni aprobaciones sin OK explícito de Nico.**

## 7. Quién decide qué
| Decisión | Quién |
|---|---|
| Aprobar release, licencia, política de liquidez, calendario | Nico |
| Abrir P&L, manifiestos de campaña, holdout, cuenta/broker | Nico |
| Unificar líneas de código, borrar datasets | Nico (los agentes preparan y verifican) |
| Implementar, medir target-free, auditar, documentar | Agentes, bajo el protocolo |
