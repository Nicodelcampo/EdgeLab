# Kit de herramientas del agente: cómo las conoce, cómo las usa y cómo sabe mejorar

Estado: PROPUESTA (implementada en código; vale como diseño hasta que Nico la apruebe)
Fecha: 2026-10-16
Familia / módulo: `autopilot` (`edgelab/autopilot/herramientas.py`, `config/autopilot/herramientas.json`)
Procedencia: pedido de Nico del 2026-10-16 ("terminá de diseñar la estructura para que el agente las aproveche y sepa mejorar en su momento"), sobre los informes RRE-AI, k32 e Iteración 2.

## 1. Qué problema resuelve

Los informes externos proponen herramientas (find_peaks, TreeSHAP, Venn-Abers, CQR, encoders) como si estuvieran disponibles. El agente necesita saber, en cada ciclo y sin que un LLM lo recuerde: qué técnicas existen, cuáles puede usar para medir, cuáles sólo para proponer, qué le falta, y cuál le rindió. Y necesita un camino para que una técnica nueva entre al sistema sin que el propio agente afloje sus reglas.

## 2. El catálogo (`config/autopilot/herramientas.json`, esquema v2)

Cada técnica declara:

| campo | qué es |
|---|---|
| `id`, `ref`, `uso` | nombre, referencia bibliográfica o documento del repo, para qué sirve |
| `exige` | condiciones no negociables para usarla (partición, conteo de pruebas, parámetros fijados antes) |
| `verificar_contra` | la referencia externa o el fixture con el que se prueba la paridad |
| `estado` | `verificada` (implementación + prueba en CI: sirve para medir) · `propuesta` (idea o script ad hoc: sirve para proponer) · `falta` (no está: se pide) |
| `implementa` | ruta del módulo del repo que la implementa, o `null` |
| `fase` | `proponer` y/o `confirmar` |

El estado lo fija el archivo, no un prompt. `herramientas.cargar()` rechaza estados fuera de la lista.

## 3. Ciclo de vida de una técnica

```
falta ──(mejora de módulo: PR + implementación + test contra verificar_contra + revisión)──> verificada
propuesta ──(mismo camino: el script ad hoc gana su prueba de paridad)──> verificada
verificada ──(usos >= 5 sin ningún hit, o un artefacto demostrado)──> revisar (humano decide: retirar o acotar)
```

Nada de esto lo hace el agente solo. `mejora.py` fija el perímetro: los módulos son ámbito "sólo se propone" (estado `PROPUESTA`, aceptación "tests verdes + revisión de PR"; nunca se aplica sola). Cuando una candidata declara una técnica que falta o no tiene paridad, `herramientas.pedir_mejoras` registra esa propuesta con la referencia contra la que hay que verificarla. Eso es "saber mejorar en su momento": el agente detecta lo que le falta en el acto de proponer, lo pide con la prueba que haría falta, y sigue con lo que sí tiene.

Agregar una dependencia (LightGBM, MAPIE, torch) es parte de esa decisión humana: hoy el repo tiene `scipy` en los requisitos y `scikit-learn` sólo en scripts ad hoc.

## 4. Cómo la ve el proponente

`contexto.armar_paquete` incluye `herramientas`: lista de técnicas con `estado`, `uso` y, si hay ledger, `rendimiento` (usos, hits, nulos, fallos). Esta sección nunca se recorta por tamaño: sólo se recortan fichas y vacíos. La regla que acompaña la lista: "proponer con cualquiera; medir sólo con `verificada`; lo que falta se pide como mejora de módulo". El rol `proponente` ya tiene en su sistema "usando sólo primitivas del registro recibido": el registro ahora trae las primitivas con su estado.

## 5. Cómo la usa la promoción

Una candidata declara en `cfg.tecnicas` con qué va a medir. `promocion.chequeos_mecanicos` llama a `herramientas.faltantes`: una técnica desconocida o sin estado `verificada` es `RECHAZADA_MECANICO`, antes de gastar un revisor. Si pasa y se promueve, cada técnica queda en `herramientas.jsonl` como `lanzada` con el `run_id`.

## 6. Cómo aprende qué le rinde

`herramientas.jsonl` es append-only: `lanzada` al promover; `hit`, `nulo` o `fallo` cuando se analiza la corrida. `herramientas.rendimiento` agrega y `para_contexto` lo pone delante del proponente. El efecto buscado es que el agente prefiera técnicas con hits y deje de insistir con las que dieron nulo, sin que nadie cambie un prompt. Una técnica con usos y sin hits no se retira sola: aparece en el paquete con sus números y lo decide un humano (perímetro de `mejora.py`).

**Pendiente de cablear:** el cierre `hit / nulo / fallo` en el análisis de corridas (`brain.py` / `analyze.py`). Hoy el ledger sólo recibe `lanzada`.

## 7. Qué no hace, a propósito

- No cambia gates, FDR, holdout ni mandato (`mejora.NUNCA`).
- No marca una técnica como verificada: eso lo hace un test en CI que alguien escribió y revisó.
- No instala dependencias.
- No convierte un informe externo en técnica verificada: entra como `falta` o `propuesta`, con su referencia.

## 8. Estado del catálogo al 2026-10-16

| técnica | estado | implementa |
|---|---|---|
| corredores_densidad_hp007 | verificada | `edgelab/research/density_field.py` |
| dsr_pbo | verificada | `edgelab/research/g2.py` |
| mcpt_spa_walkforward | verificada | `validation/` |
| triple_barrera, replay_causal_fills_pasivos | propuesta | `edgelab/engine.py` (falta la orden límite con espera y cancelación) |
| meta_labeling, calibracion_isotonica | propuesta | `tools/corridor_pass2/dev_filters_analysis.py` (ad hoc) |
| pu_learning, conformal_risk_control, aprendizaje_continuo_con_embargo | falta | — |
| segmentacion_topografica_find_peaks, wasserstein_perfil, veto_aditivo_treeshap, venn_abers, cqr_aci_cota_inferior, ranker_tripletes_lambdarank, encoder_tri_franja_film | falta (Iteración 2) | — |

Pruebas: `tests/test_autopilot_contexto_mejora.py` (catálogo, ledger, paquete, pedido de mejora) y `tests/test_autopilot_promocion.py` (rechazo mecánico por técnica sin paridad).
