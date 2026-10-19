# Handoff local mínimo — exact4 GC listo; MNQ V2 primera sesión recibida

**30/09/2026:** MNQ20260629 V2 ya terminó y fue auditado en nube. No repetir esa ejecución ni rediseñar exact4: el núcleo ya está publicado. Nico/local proporcionó controlGC; números efectivos/resolver están preparados. Lo local pendiente es confirmar su bundle/hash/grano e integrar/correr QA target-free en datos correctos.

## 1. Tests del código nuevo (sin deps de research pesado)

```powershell
$env:PYTHONPATH="tools"
.venv\Scripts\python.exe -m unittest discover -s tests/research -p "test_gc_exact4.py" -v
```

26tests nuevos; si falla por entorno, reportar, no relajar lock/tolerancias. Un escritor/worktree y un proceso pesado.

## 2. Capturar metadata real de lo que Nico ve

`gc_exact4_prepare.py capture` necesita `--det-json` del archivo seleccionado, `--chart-bundle`, `--bar-series` EXPLÍCITA, `--bar-type` y `--bar-size` verificados, `--out` nuevo. El control declarado es GC_04-26_202602_25T_HFT__nq__n4__precio (25T_HFT). No asumir el nombre de la clave bar_series ni que los gráficos traen todos los raw timestamps. Capturador guarda hashes/parámetros/meta, NO velas/precios en repo.

```powershell
.venv\Scripts\python.exe tools/gc_exact4_prepare.py capture --det-json "<bundle peaks_det seleccionado>" --chart-bundle "<bundle de velas>" --bar-series "<clave seleccionada exacta>" --bar-type "<tipo verificado>" --bar-size 25 --out E:\gc_exact4_baseline_local.json
```

Los placeholders NO son rutas inventadas para ejecutar. Si conf no se puede resolver inequívoca desde metadata, aborta sin defaults. La captura prueba identidad de metadata declarada; paridad geométrica/raw queda separada.

## 3. Censo C1–C4 sin outcomes

Una vez que haya barras cerradas del MISMO grano/ventana/custodia, JSONL con high_tick,low_tick,close_tick,time (o close_ts_us),session_id. Para checks de publicación: snapshot_asof_row/snapshot_ts_us/bar_close_row/available_row/available_ts_us/publication_mode del exporter auditado. Ausentes => no disponible, no fill. No usar exporterMNQ para GC ni mezclar Feb con nuestros ejemplosMayo/Jun.

```powershell
.venv\Scripts\python.exe tools/gc_exact4_prepare.py census --baseline E:\gc_exact4_baseline_local.json --bars-jsonl "<GC barras causales compatibles>" --out E:\gc_exact4_targetfree --ack-targetfree
```

C0 devuelve abstención: correrlo con su detector actual conservado, no reemplazar por Exact4. El censo NO es adapterraw/visor, ni reporteL2 completo; si falta archivo compatible, pasar bundle privado a nube para preparar puente, no rehacer diseño ni inventar schema. Configs efectivos/evidence se devuelven a nube; eventos_private/precios privados. Ver perfiles ya resueltos en artifacts/gc_exact4_preparation_20260930/gc_resolved_profiles.json.

## 4. Visor y estado de MNQ

La integración/capa exact4 aún NO está hecha. Reusar visor canónico y adaptador existente, namespaces y opt-in, C0 intacto, pintar sólo4miembros. Si no quedan créditos, pasar bundles+manifest propios a nube y dejar esa integración local pendiente; núcleo/censo ya no requieren desarrollo deClaude.

MNQ V2:31señales iguales aV1;26 niveles observables antes del extremo (6true de regla compatible),17 al publicarse su grupo (1true),4 al confirmar (1true). Sólo propuesta de feature histórica disponible AL DETECTAR; no entrada anticipada ni ganancias. Antes de ampliar población, congelar diagnósticos y plan muestra; no52automático ni climasSTOP.

## Aporte al referente

El diseño/código/QA están en nube; la PC sólo aporta identidad/datos e integración específica, sin resultados financieros nuevos.
