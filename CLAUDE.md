# EdgeLab — instrucciones permanentes de sesión

> Este archivo se carga en cada sesión de Claude Code. El documento canónico
> versionado es **`docs/NORTH_STAR.md`** (sha256 `21bb3b01a33e2b37…`); si hay
> conflicto, manda ese doc.

## NORTH STAR — referente rector (gobierna todo)

**EL OBJETIVO FINAL DEL PROYECTO ES ENCONTRAR EDGES VÁLIDOS Y APLICABLES EN EL
MERCADO A TRAVÉS DE ALGORITMOS QUE, A TRAVÉS DE LA RENTABILIDAD, PERMITAN
OBTENER GANANCIAS EN LAS CUENTAS DE TRADING DONDE SE APLICAN.**

Jerarquía de objetivos (para priorizar cualquier tarea o trade-off):
1. Expectativa económica NETA (después de comisiones, spread y slippage).
2. Validez fuera de muestra (holdout sellado, sin data snooping).
3. Robustez estadística (MCPT, PBO, DSR/SPA, walk-forward, sensibilidad).
4. Ejecutabilidad real (feed en vivo, fills realistas, latencia, reglas
   completas de entrada/salida/sizing/kill switch).
5. Control de riesgo (drawdown tolerable, despliegue con riesgo mínimo).
6. Paridad, determinismo, trazabilidad y visor COMO MEDIOS para 1–5.

Recordatorios:
- Un indicador con paridad exacta no es un edge. Una zona bien almacenada no
  es un edge. Un backtest positivo no es un edge si no sobrevive selección,
  costos, OOS y ejecución.
- Target-free aplica a la construcción técnica de indicadores; el research de
  estrategias SÍ usa retornos y P&L, pero bajo pre-registro, presupuesto de
  investigación, corrección por múltiples pruebas y holdout sellado.
- El progreso NO se mide por infraestructura terminada sino por cuánto reduce
  la distancia hacia un edge neto, robusto y operable.
- No prometer rentabilidad futura: el objetivo metodológico es maximizar la
  probabilidad de detectar edges reales y rechazar falsos antes de arriesgar
  capital.

## Decisión de prioridad vigente (sellada por Nico)

**F9 (nuevos indicadores) PAUSADA** hasta ejecutar al menos una campaña formal
de descubrimiento sobre los 5 indicadores existentes. Agregar indicadores hoy
amplía el espacio de búsqueda y el data snooping sin evidencia de que haga falta.

## Rituales permanentes

- Todo **checkpoint de turno termina con "Aporte al referente: …"** (1–2 líneas:
  qué distancia se redujo hacia un edge neto y operable). Obligatorio.
- Todo **manifiesto de campaña cita el hash de `docs/NORTH_STAR.md`**.
- Toda **plantilla generadora** (scaffold, spec LLM, reportes) incluye los
  campos obligatorios **"justificación económica"** y **"cómo podría refutarse"**.

## Firewall del holdout (2026-07-01 → 2026-12-31)

- **Prohibido** usar el holdout para elegir dirección, entradas/salidas,
  thresholds, bar_spec, costos o candidatos.
- **Permitido** solo para validaciones target-free (paridad, determinismo,
  geometría, integridad, visor). Una sola apertura por candidato, por protocolo.

## Reglas permanentes

- **Referente rector primero**: toda tarea se justifica por su aporte al edge
  neto, robusto y operable.
- No tocar F0–F2 ni el schema canónico; no modificar parquets reales; no editar
  particiones publicadas (son inmutables).
- **Causa raíz obligatoria** para todo WARN/FAIL; prohibido ampliar tolerancias
  o relajar gates después de ver resultados; cambios de semántica de validación
  se **consultan con Nico**.
- **Ninguna población se congela sin enumerar antes, por escrito, el espacio de
  eventos y estados del que se la extrae**, con su justificación y su condición
  de refutación. Una población elegida sin alternativas escritas no es una
  elección: es una herencia. Extiende el campo obligatorio «cómo podría
  refutarse» de la hipótesis **a la población sobre la que se define**.
  El 2026-08-10 se descubrió que TODO el corpus sobre BigTrap2 medía una sola
  familia de entradas —el toque— porque una premisa dentro de un condicional de
  la enmienda del 2026-08-04 pasó a axioma, y el marco alternativo (zona como
  estado, `features.py`) llevaba trece días construido sin que research lo
  usara. Ningún gate podía cazarlo: **lo único que nadie auditó es lo que nadie
  escribió como decisión.** Ver
  `docs/SESGO_DE_DISENO_2026-08-10_EL_TOQUE_COMO_UNICA_ENTRADA.md`.
- No mirar el holdout para diseñar o elegir. No seleccionar por P&L máximo
  aislado. No ocultar resultados negativos. No ejecutar fills imposibles.
- Tests con fixtures chicos y deterministas; sin dependencias pesadas nuevas
  (duckdb/polars/pyarrow ya están); sin CUDA.
- Commits chicos por fase, push al cierre. Si git pide credenciales: frenar y
  pedir a Nico. Al pushear, usar el token que Nico provea sin persistirlo en
  `.git/config` y redactarlo de los logs.

## Interrupción por oráculos (prioridad máxima permanente)

Si aparecen CSVs en `oracles\`: interrumpir en punto seguro → validar
versión/hash del `.cs` y ventana/params → correr gates → **causa raíz de todo
WARN/FAIL** → promover particiones → regenerar visor → registrar cobertura →
retomar la tarea anterior.

## STOP antes de correr búsqueda sobre retornos

Antes de ejecutar CUALQUIER búsqueda sobre P&L/retornos: presentar a Nico el
**manifiesto de campaña + número efectivo de hipótesis + riesgos + datos
faltantes**, y esperar aprobación. No correr la búsqueda sin ese OK.

## Punteros

- `docs/NORTH_STAR.md` — referente canónico (fuente de verdad).
- `docs/edge_validation_contract.md` — gates G0–G5 de "edge válido y aplicable".
- `docs/kernel_contract.md` — construcción técnica target-free de kernels.
- `docs/nt8_indicator_parity_contract.md` — protocolo de paridad NT8↔Python.
- `docs/nt8_bridge.md` — store, gate P3, campañas, visor, API de features.

## Entorno

`.venv` (Python 3.12) desde `requirements/core-bridge-dev.lock`. Suite:
`.venv\Scripts\python -m pytest tests -m "not vectorbt" -q`. Branch de trabajo:
`foundation/f0b-compatibility-probe` (main = baseline original, no mergear).

## PRIMER COMANDO DE CADA SESIÓN

```
.venv\Scripts\python tools\estado.py
```

Dice en qué rama estás, si coincide con la declarada arriba, si estás
sincronizado con el remoto, **y si otra rama tiene trabajo que la tuya no
tiene**. Sale 1 si algo requiere atención. Correlo ANTES de medir cualquier cosa.

**Regla de una sola rama.** Todo el trabajo va a `foundation/f0b-compatibility-probe`.
Si hace falta una rama auxiliar, se mergea de vuelta **el mismo día**. El
2026-08-05 dos máquinas midieron cosas distintas creyendo mirar lo mismo: 70
commits vivían en una rama que este archivo no mencionaba, y cada lado leyó la
suya. Las dos lecturas eran internamente coherentes. Ver `docs/AVISO_DIVERGENCIA_DE_RAMAS_2026-08-06.md`.

Excepciones que divergen a propósito y `estado.py` no marca: `main`, `backup/*`,
`preserve/*`.

**Dos clones en esta máquina** — `E:\EdgeLab` y `E:\ProyectosQuant\EdgeLab-sync-desktop`.
Los dos apuntan al mismo remoto. Correr `estado.py` en el que vayas a usar.
