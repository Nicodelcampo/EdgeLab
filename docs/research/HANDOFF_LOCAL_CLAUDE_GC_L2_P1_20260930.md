# Traspaso GC L2 R02/I-3 — sesión local de Claude

Pedido de Nico: hacer desde el sandbox lo posible y dejar la continuación local
documentada. **No se invocó ni se programó otra sesión de Claude**; este es su
paquete de arranque, no una tarea remota ya asignada.

## Arranque e integridad

Leer `AGENTS.md`, `PROJECT_INDEX.md`, `AUDITOR_START_HERE.md`, `docs/CURRENT.md`
y el acta/plan P0/P1 de este paquete. Resolver HEAD remoto actual, no usar un hash
recordado como estado vivo. Rama de integración: `foundation/f0b-compatibility-probe`.
Usar una worktree propia, un escritor por directorio. Inventariar cambios no
commiteados antes de tocar el visor. No `reset --hard`, `clean`, force-push ni
pull sobre trabajo ajeno. Remoto real podría llamarse `github`, no `origin`.

Hay resúmenes viejos contradictorios sobre holdout: manda HOLDOUT-A3 y el
protocolo de la familia. **Forward desde sesión CME 1-oct-2026 sellado.**
Abr–sep no autoriza reaperturas de outcomes; para contextos L2 es desarrollo.
Estas pruebas sólo son mecánicas y no autorizan retornos.

El proceso de la PC **no fue inspeccionado ni modificado desde el sandbox**.
Durante este trabajo otra sesión publicó `RESULTADO_CONTEXTOS_L2_MES_MNQ_20260930.md`:
MES y MNQ dieron STOP de cuatro estados por semillas; global 0,557 y 0,714.
En MNQ calm 0,98 no habilita por sí solo un filtro; toxic binario no fue evaluado.
Resolver el estado local actual antes de lanzar procesos. En la PC de 16 GB,
mantener como máximo un proceso pesado; no detener ni duplicar trabajo ajeno.

## Lo terminado desde la nube

- P0: reconstrucción canónica sin modificarla; episodios a precio fijo; cuatro
  parquet privados GC verificados; 12 tests unitarios y conteos agregados.
- P1: un matching histórico 1:1 sin reemplazo y sin selección por desenlace.
  Misma muestra ya conocida: **no confirmación independiente**. Controles sin
  prints previos al mismo precio, con profundidad/tamaño/caída/actividad similares.
- Reproducción exacta P0, 12 tests adicionales y replay de prefijos reales.
- Repetición en precio fijo usando sólo recuperaciones ya publicadas.
- Raw y episodios con precios no versionados. No se tocaron el visor, los
  detectores de IPC/escalonadas, parámetros de climas ni archivos de retorno.

Leer la conclusión y los límites en
`docs/research/RESULTADO_GC_L2_CONTROLES_P1_20260930.md`.
No llamar estos episodios icebergs/absorción certificada ni filtros válidos.

## Archivos y reproducción

Repo:
- `tools/gc_l2_fixed_price_probe.py`
- `tools/gc_l2_historical_controls.py`
- `tests/research/test_gc_l2_fixed_price_probe.py`
- `tests/research/test_gc_l2_historical_controls.py`
- `docs/research/PLAN_GC_L2_PRECIO_FIJO_P0_20260930.md`
- `docs/research/PLAN_GC_L2_CONTROLES_P1_20260930.md`
- `artifacts/gc_l2_fixed_price_p0_20260930/evidence.json`
- `artifacts/gc_l2_controls_p1_20260930/evidence.json`

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests/research -p "test_gc_l2*.py" -v
```

Entorno de la corrida sandbox: NumPy 2.5.3, pandas 3.0.6, PyArrow 25.0.0;
no se certificó el lock/CI completo. Local: seguir lock del repo y reportar
cualquier diferencia, no relajar pins para forzar verde.

Fuente exacta: dataset **privado** Kaggle
`nicolasbuttaro/edgelab-l2-gc-bookmap-audit-20260921`, versión 2.
Estructura: `docs/manifest.json`, `l1_quotes/<fecha>.parquet`,
`l2_depth/<fecha>.parquet`, `manifests/<fecha>.manifest.json`.
El ZIP de entrega no trae datos privados ni URLs firmadas.

P1 compara sus conteos contra evidencia P0 y, si están disponibles, sus JSONL:

```powershell
.venv\Scripts\python.exe tools/gc_l2_historical_controls.py `
  --raw <ruta-privada-dataset-v2> `
  --out <ruta-privada-nueva-P1> `
  --book-module edgelab/research/l2_phase0.py `
  --p0-evidence artifacts/gc_l2_fixed_price_p0_20260930/evidence.json `
  --plan docs/research/PLAN_GC_L2_CONTROLES_P1_20260930.md
```

Las salidas `*_private.*` son LOCAL-ONLY. No subirlas al repo ni públicos.
El CLI de P1 reproduce sus métricas, QA y prefijos; el plan/acta describe qué
metadatos de análisis agregados se añadieron después. No sobrescribir evidencia
publicada con una corrida nueva sin comparar hashes y resultados.

## Pendiente local 1 — visor causal, antes que nuevas hipótesis

**Un solo visor:** `viewer/nt8_bridge/index.html`; usar builder existente
`tools/build_l2_viewer_bundle.py`, no fabricar otro visor o copiar el de esta captura.

1. Alinear al mismo feed NT8 del GC las velas/trades/libro. Los manifiestos del
   dataset piloto conservan reloj de referencia sin certificar. Para coordenadas
   absolutas del visor, seguir resolución/documentación de GC y demostrar la
   transformación en un nuevo manifest; no editar los parquet originales.
   No unir por cercanía a `.Last.txt` de otro conversor.
2. Capa provisional independiente del detector viejo. Mostrar el nivel de la
   caída con disponibilidad en su snapshot y la recuperación **en `available_ts_us`
   / `available_row`**, no en `drop_ts`. A futuro oculto, ninguna recuperación
   puede aparecer antes de observarse. El final de un grupo de timestamp es la
   disponibilidad conservadora del snapshot, no un fill intragrupo.
3. Tooltip: lado/precio, tamaño anterior/tras caída/recuperado, ventana de prints,
   demora, método y leyenda «recuperación compatible · MBP · no iceberg certificado».
   Distinguir desaparición/salida top-10 de retiro real; ausencia visible no es
   cancelación probada.
4. Vectores dorados y prefijos Python↔visor, corte temporal, zoom/pan sin cambiar
   episodios. Juicio humano sin ver el futuro, sólo paridad de capa; no seleccionar
   ejemplos por éxito del trade.
5. No mostrar un desenlace futuro del control como atributo disponible en una
   señal. Matching P1 es diagnóstico mecánico, no regla live de entrada.

**Criterio de entrega:** mismos IDs/conteos/timestamps al cortar el futuro y
leyenda provisional visible. Si no coincide, STOP, no ampliar tolerancias.

## Pendiente local 2 — adaptación a ES/MNQ

El probe actual es **específico de estos dos GC legacy**: fechas y tick 0,1
fijados; lector espera `price` redundante. **No correrlo sin cambios sobre ES/MNQ.**
Las conversiones actuales pueden omitir `price` tras validarla.

Antes de medir:
- inventariar L1/L2, contratos, schemas, manifests, hashes, cobertura y clock;
- adaptar lector desde contrato/schema explícito (tick del instrumento, sin
  redondeo silencioso), preservar filas y orden, tratar rolls/resets;
- demostrar paridad y prefijos en una ventana pequeña, target-free;
- fijar por escrito ventanas/umbrales y presupuesto para ES/MNQ. Los 2 s / 5 s /
  70 % de GC son heurística heredada, **no parámetros transportables certificados**;
- resolver unión causal con señales **congeladas** de IPC/escalonadas/espejo;
  no suponer equivalencia de reloj entre climas de un minuto y velas 25t.

Primero describir defensa local en los niveles y su evolución antes de la señal;
un episodio confirmado después de la entrada no puede justificar esa entrada.
El STOP de cuatro climas en ES/MES/MNQ no impide estudiar features locales,
pero tampoco certifica un binario calm/toxic. Son preguntas distintas y con
protocolos separados; no usar esta capa para cambiar etiquetas o rescatar el modelo.

## Pendiente local 3 — utilidad, sólo con manifiesto y OK

No correr grillas de retornos ni rescatar ventanas después de leer P1.
Antes de TP/SL/MFE/MAE/P&L/costos: evento/instante disponible, control por distancia
al toque y actividad, hipótesis efectivas, datos faltantes, MDE/estadística por sesión,
costos propios del instrumento, particiones y aprobación explícita de Nico.
No interpretar los miles de episodios dependientes como miles de sesiones independientes.

No hace falta ampliar el research público para integrar la capa. El cuello de
botella local es datos/alineación/visor, y después probar utilidad bajo el firewall.

## Aporte al referente

La sesión local recibe código reproducible, controles descriptivos y una lista
cerrada de integración causal; no una estrategia aprobada ni un permiso para
abrir retornos.