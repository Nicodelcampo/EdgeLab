# RESEARCH — Opciones de ejecución liviana para los procesos del proyecto (2026-08-30)

**Autor:** Notion AI (auditor) · **Motivo:** pedido de Nico ("en el futuro habrá procesos más pesados").
**Método:** búsqueda web 2026-08-30 (fuentes citadas al final). **No cambia ninguna política** — las opciones que implican mover datos CME o cambiar la plataforma de ejecución atestada son decisiones de Nico (política `KAGGLE_ONLY_EXECUTION_POLICY_V1` + decisión de licencia `DATA_LICENSE_DECISION.md`).

## 0. El marco que manda: dos familias de trabajo

La respuesta correcta depende de si el proceso **toca los ticks CME** o no:

- **A. Data-bound** (toca el paquete privado NQ / tapes GC): la licencia CME y la política de ejecución atestada los anclan a Kaggle. Cualquier alternativa que requiera subir los ticks a otro servicio queda **descalificada por licencia**, no por precio.
- **B. Data-free** (suites sintéticas de verdad conocida, tests de contratos, metodología RW/MCS, validaciones): no tocan datos — pueden correr en cualquier lado, y hay una opción gratis e ilimitada ya disponible (§2).

## 1. Dentro de Kaggle (familia A): el hallazgo grande — la TPU-VM como máquina CPU

Specs actuales documentadas de Kaggle Notebooks: CPU = 4 cores / ~30 GB RAM / sesiones de 12 h; GPU = P100 o 2×T4 / 4 cores / 29 GB / 12 h; cuotas ~30 h GPU/semana y ~20 h TPU/semana. Y el dato clave:

> **TPU 1VM: 96 CPU cores y 330 GB de RAM** (sesiones de 9 h, cuota ~20 h/semana).

Para trabajo tabular CPU-bound (lo nuestro: bootstrap clusterizado, Romano-Wolf sobre 372 celdas, builds de stores), la TPU-VM **usada como máquina CPU gigante** es 24× los cores y 11× la RAM del tier CPU, dentro de la misma plataforma, la misma política y el mismo protocolo de atestación ya escrito (`KAGGLE_FROZEN_EXECUTION_PROTOCOL_V1`). Costo: consume la cuota TPU semanal y la sesión baja a 9 h — que con checkpointing byte-idéntico (contrato de paralelismo ya escrito) no importa. Es la palanca más grande disponible **sin tocar una sola cláusula**.

Segunda palanca dentro de Kaggle: reducir el footprint para que 30 GB rindan como 60-100 GB efectivos (§3).

## 2. Fuera de Kaggle, solo familia B: GitHub Actions — gratis e ILIMITADO en repo público

El repo es público: los runners estándar de GitHub son **gratis e ilimitados para repos públicos** (recientemente duplicados a 4 vCPU / 16 GB para open source). Los workflows se disparan por push — no hace falta API de dispatch: con pushear alcanza (y eso sí puedo hacerlo yo vía el MCP actual).

Uso recomendado (todo data-free):
- La suite de verdad conocida de Romano-Wolf + MCS (blocker de freeze de la campaña SL/TP): datos sintéticos, cero ticks → corre perfecto en CI.
- Las suites de contratos/tests del repo (ya existe el patrón: `contract_kaggle_frozen_execution.yml` corre en ubuntu-latest).
- Cualquier verificación de metodología futura (nunca datos reales).

Descalificado para familia A por licencia CME + egress, no por capacidad.

## 3. Palanca de software (ambas familias): menos memoria = entornos más grandes de facto

- **Polars** (columnar Arrow, lazy + streaming): típicamente 5-10× más rápido que pandas con 2-4× el tamaño del dataset en RAM (vs 5-10× de pandas); el modo streaming procesa más-que-RAM. Aplica a las capas de carga/joins/asignación de estratos (los kernels de medición ya son numpy puro y no se tocan).
- **DuckDB** (out-of-core con límite de memoria estricto, spill a disco): para agregaciones sobre parquet grandes con pico de memoria acotado — útil en censo/build de stores.
- Regla del proyecto que les aplica: cualquier cambio de capa de datos pasa el **test de determinismo byte-idéntico** (1 vs N workers; serial vs streaming) antes de confiar — igual que el contrato de paralelismo.

## 4. Descalificadas con razón registrada

- **Google Colab free**: límites dinámicos no garantizados, GPU no elegible, sesiones más cortas en la práctica; y exigiría mover los ticks (licencia). Inferior a Kaggle en todo lo que nos importa.
- **Lightning AI free**: 1 Studio CPU a la vez + créditos one-time (~30). Peor que Kaggle para batch recurrente.
- **Paperspace Gradient free**: sesiones de 6 h máximo, GPUs débiles. No aplica.
- **Modal / serverless**: buen diseño, pero es pago-dependiente y también mueve datos. Si alguna vez hiciera falta burst masivo data-free (ej. barrido sintético enorme), Modal free tier ($30/mes de créditos) es la primera a mirar.
- **GitHub Actions para datos CME**: ver §2 — licencia + egress, no capacidad.

## 5. Opción cero, la que ya existe: la máquina de Nico

Los datos se originaron localmente (export NT8) — la jurisdicción de la licencia empieza ahí. Corridas locales overnight para trabajo exploratorio pesado son compatibles con la licencia tal como está escrita (verificar contra `DATA_LICENSE_DECISION.md` antes de la primera) y con el patrón de atestación (el mismo script con `--output-dir` local + manifiesto). No reemplaza Kaggle para lo confirmatorio (la política manda Kaggle), pero es capacidad gratis ya pagada.

## 6. Recomendación (sin cambio de política)

1. **Familia A pesada** (campaña SL/TP: 372 celdas × 22.202 eventos × bootstrap 10.000 + RW): Kaggle **TPU-VM** (96 cores / 330 GB), paralelismo por contrato-sesión con el contrato ya escrito, checkpoints byte-idénticos contra la sesión de 9 h.
2. **Familia B toda**: GitHub Actions por push — empezando por la suite RW/MCS, que es el blocker de freeze más cercano y no necesita un solo tick.
3. **Footprint**: polars/duckdb en capas de carga y estratos, con test de determinismo como puerta.
4. La política `KAGGLE_ONLY` queda intacta para lo confirmatorio; si algún día se evalúa burst externo, es enmienda de Nico + revisión de licencia primero.

## Fuentes

- Kaggle Notebooks docs (specs y límites de sesión; TPU 1VM 96 cores/330 GB): https://www.kaggle.com/docs/notebooks · cuotas semanales (~30 h GPU, ~20 h TPU): kaggle.com/general/108481 y d2l.smola.org (snapshot 2026)
- GitHub Actions: gratis e ilimitado en repos públicos, runners 4-vCPU para open source: docs.github.com/en/actions/reference/runners/github-hosted-runners · github.blog/news-insights/product-news/github-hosted-runners-double-the-power-for-open-source
- Lightning AI pricing (free tier): https://lightning.ai/pricing/ · Colab FAQ (límites dinámicos): research.google.com/colaboratory/faq.html · Gradient free 6 h: blog.paperspace.com
- Polars vs pandas (memoria 2-4× vs 5-10×, streaming): blog.jetbrains.com/pycharm/2024/07/polars-vs-pandas · pythonspeed.com/articles/polars-memory-pandas · DuckDB larger-than-memory y límites estrictos: duckdb.org/docs/lts/guides/performance/how_to_tune_workloads.html · codecentric.de DuckDB vs Polars memoria en Parquet
