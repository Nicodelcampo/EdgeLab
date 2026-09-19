# START HERE — traspaso de EdgeLab a otra cuenta de Notion

**Fecha de corte:** 2026-09-19  
**Responsable:** Nicolas Buttaro  
**Repositorio:** https://github.com/Nicodelcampo/EdgeLab  
**Estado:** `HANDOFF_READY_WITH_OPEN_ITEMS`

Este documento es el punto de entrada para continuar el trabajo desde otra cuenta de Notion sin depender del historial de conversación de la cuenta anterior.

## 1. Qué es canónico y dónde está

### Auditoría Edge Factory, migración Kaggle y bundles

- Rama: `audit/edge-discovery-factory-foundation-20260919`
- Commit de fundación auditada: `49eadf059a004fd91c6759f65d03307962263e01`
- Commit de migración/compresión: `79592c1ebfb675edb2c9aea332c0f843eed6ad8c`
- Documento de compresión: `docs/research/BUNDLE_COMPRESSION_AUDIT.md`
- Evidencia estructurada: `artifacts/migration/BUNDLE_COMPRESSION_AUDIT.json`
- Aclaración autoritativa de cobertura: `docs/research/25T_BUNDLE_SCOPE_AND_KAGGLE_CUSTODY_20260919.md`

### Cerebro recursivo / memoria metodológica

- Rama: `feat/edge-discovery-brain-foundation-20260919`
- Pull request draft: https://github.com/Nicodelcampo/EdgeLab/pull/43
- Commits principales: `0ef307b772d7f407fe7f93591f6d185b947d223a`, `a3b64735866a2d14d7c218e6e23995997c3f9983`
- Correcciones CI/dependencias: `f0dfbaff37f6a65734dc3ae72a3ec8cca20c4ff9`, `529228dec5ddbe284b6983b414f67c02bfaa0602`, `debe979dfc86553b2bc48316d914355acf6217e6`

La rama del cerebro contiene:

- contratos de medición;
- memoria de errores metodológicos;
- claims y dependencias;
- provenance de ejecuciones de modelos;
- ledger JSONL append-only con cadena SHA-256;
- propagación determinista de invalidación;
- tests y documento de arquitectura.

**No fusionar PR #43 todavía:** los checks de GitHub Actions siguen rojos. La primera causa probable (`jsonschema` no declarado) fue corregida, pero las dos ejecuciones posteriores continuaron fallando y el error exacto no quedó accesible desde la integración. Debe reproducirse con Python 3.12 o abrirse el log de Actions antes de mergear.

La base de PR #43 avanzó posteriormente con `79592c1`. El intento automático de actualizar la rama del PR falló. La nueva cuenta debe actualizar/rebasear la rama antes de continuar y conservar ambos historiales.

## 2. Estado de Kaggle

Datasets privados conocidos:

```text
nicolasbuttaro/edgelab-edge-factory-audit-evidence-20260919
nicolasbuttaro/edgelab-edge-factory-target-free-audited
nicolasbuttaro/edgelab-ticks-6b-preholdout
nicolasbuttaro/edgelab-ticks-6j-preholdout
nicolasbuttaro/edgelab-ticks-mnq-preholdout
```

MNQ fue reportado como verificado bit a bit post-descarga:

```text
5 contratos
334,506,728 ticks
~5.64 GB
0 holdout violations
```

### Bundles 25t

```text
Estado: PAUSED_NOT_UPLOADED
Bundles subidos: 0
Archivos locales eliminados/modificados: 0
```

No autorizar una subida hasta aplicar la aclaración de alcance. Los 147 bundles son **muestras por instrumento/contrato/mes**, no activos continuos completos ni todos los contratos disponibles.

Nombre Kaggle recomendado:

```text
nicolasbuttaro/edgelab-25t-hft-contract-month-slices-zstd-preholdout
```

Formato recomendado: `.json.zst` individual ZSTD-19 + manifiesto por bundle + manifiesto raíz. No subir `.js` redundante.

## 3. Holdout y reglas que no se deben relajar

```text
holdout_boundary_ns = 1782856800000000000
holdout_boundary_utc = 2026-06-30T22:00:00Z
```

- No leer, resumir ni perfilar outcomes del holdout.
- No promover hipótesis usando el mismo modelo que la generó.
- No tratar resultados LLM como evidencia computada.
- No llamar “continuo” a un conjunto de contract-month slices.
- No interpretar archivos/meses faltantes como cero eventos.
- No unir contratos sin metodología de roll preregistrada y auditada.
- No reabrir HP-008 histórico como validado. Estado canónico:

```text
UNVALIDATED_HISTORICAL_RESULT
CONTRADICTED_BY_CAUSAL_MULTICONTRACT_REPLICATION
REQUIRES_REAUDIT_AFTER_AVAILABLE_TS_AND_BAR_KEY_FIXES
HP008_NOT_REPRODUCED_CAUSAL_MULTICONTRACT_PREHOLDOUT
H20 = -8.7849
H50 = -14.9551
```

## 4. Cómo reconectar una nueva cuenta de Notion

1. Conectar GitHub y abrir este repositorio.
2. Leer primero este archivo y `docs/research/25T_BUNDLE_SCOPE_AND_KAGGLE_CUSTODY_20260919.md`.
3. Abrir PR #43 y descargar los logs de los checks fallidos.
4. Conectar o recrear el Worker de Kaggle con acceso **read-only** inicialmente.
5. Solicitar `KAGGLE_API_TOKEN` mediante el flujo seguro de secretos; nunca pegarlo en chat, Notion, GitHub ni documentación.
6. Validar que la cuenta pueda listar y descargar los datasets privados.
7. Comparar hashes y manifiestos remotos antes de ejecutar análisis.
8. Mantener la cola de bundles pausada hasta una autorización explícita.

Worker usado en la cuenta anterior:

```text
name: edgelab-kaggle-access
access: read-only
secret variable: KAGGLE_API_TOKEN
```

No se guardó ningún valor secreto en GitHub.

## 5. Próximas tareas en orden

1. **Git/CI:** incorporar `79592c1` en la rama de PR #43, reproducir CI con Python 3.12 y dejar todos los checks verdes.
2. **Lock canónico:** integrar el lock suplementario de `jsonschema` dentro de `requirements/core-bridge-dev.lock` usando Python 3.12; eliminar el lock temporal sólo después de verificar CI.
3. **Cerebro fase 2:** agregar schemas `source`, `artifact`, `hypothesis`, `preregistration`, `experiment`, `result` y `decision`, compatibles con Edge Factory.
4. **Proyección determinista:** ledger JSONL → Parquet ZSTD con schema Arrow explícito, hashes e idempotencia.
5. **Vistas DuckDB:** implementar controles de claims sin contrato, gaps semánticos, dependencias stale, tests faltantes, artefactos superseded y outputs no revisados.
6. **SSRN/JLP piloto:** importar sólo una muestra adjudicada; no importar todo el corpus hasta probar duplicados, contaminación e invalidación.
7. **Kaggle:** validar manifiesto global, hashes y schemas de audit evidence, target-free, 6B, 6J y MNQ.
8. **Bundles:** si Nicolas autoriza, comprimir/subir con la semántica parcial obligatoria del documento de alcance.
9. **Auditoría pendiente:** provenance de `available_ns`, cobertura real de NQ 09-26, membresía 25 ticks por barra y corredores canónicos.

## 6. CerebroSSRN y CerebroJLP

Revisión realizada fuera de GitHub sobre archivos privados adjuntos:

```text
876 archivos extraídos
401 papers
24,340 pasajes
2,491 nodos
3,662 aristas
```

Conclusión de arquitectura:

```text
CerebroJLP -> arquitectura, rebuild, contaminación y provenance
CerebroSSRN -> literatura, hallazgos, ledger y falsificación
EdgeLab -> mediciones, evidencia, dependencias e invalidación
```

Los corpus privados no se subieron al repositorio. Hashes de los adjuntos analizados:

```text
ACerebroSSRN.rar
970d55ea05798b2013cb1876a34aae573a96ec5418d010e2a595ca2768816475

CerebroJLP_Fusionado_Diagramas.zip
54f8e61e1200d8ff50e7bd2b1021c2cafac73b4b2da046acadc7cde5ee51fb4f
```

## 7. Model routing previsto

- Python/SQL/DuckDB/Polars/PyArrow/pytest: evidencia determinista.
- Modelos externos/locales: generación masiva, extracción y crítica, siempre con provenance.
- Notion: planificación, integración, revisión y decisiones.
- Ningún modelo promueve su propia hipótesis.
- No depender de archivos locales cuando un artefacto canónico verificado pueda publicarse en Kaggle.

## 8. Definición de “traspaso correcto”

La nueva cuenta no necesita el historial de chat si puede:

- encontrar este documento;
- acceder a las dos ramas y PR #43;
- distinguir evidencia auditada de scaffolds o claims históricos;
- reconectar Kaggle sin exponer secretos;
- mantener holdout y uploads pausados;
- reproducir CI y continuar la fase 2 del cerebro.

Ante cualquier contradicción, prevalecen en este orden:

1. evidencia estructurada y hashes;
2. aclaraciones autoritativas posteriores;
3. documentación de auditoría;
4. reportes conversacionales.
