# Leer antes de cada corrida — índice obligatorio (v2, 2026-11-18)

Estado: VIGENTE — pedido de Nico: «un documento que sea obligatorio leer para cada corrida, que sea un índice de todos los otros
documentos que se deberían leer». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

**Cómo se cumple:**
- Todo pre-registro nuevo lleva una línea «Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v2 — …» que diga qué secciones aplican.
- `edgelab/research/preflight.py::validar_preregistro` la exige; sin ella, `tools/registro_global.py preregistrado` no cuenta la corrida y
  el CI la rechaza.
- Este índice se versiona: si cambia, sube la versión y los pre-registros nuevos citan la nueva.

## 0. Dónde estamos (siempre)
- `CLAUDE.md` (estado vigente y rituales) y `docs/research/VEREDICTO_M1_20261117.md` (qué regla está viva, refutada o sin medir).
- `docs/research/FACTORES_CON_VENTAJA.md`: lo que hay que indagar primero y la lista NO_REPETIR.
- `docs/research/FAMILIAS.md` y `docs/research/LINAJES.jsonl`: de qué familia deriva la idea y qué ya usó.
- `python tools/antecedentes.py "<idea>"`: su línea va al pre-registro.

## 1. Antes de diseñar
- **Reutilizar:** `python tools/existente.py buscar "<qué>"`, `docs/MODULES.md`, `docs/HERRAMIENTAS.md`.
- **Según el tipo de corrida:**
  - grilla grande: `docs/research/GUIA_GRILLA_MASIVA.md` (K4: más de 500 celdas con retornos exige un E0 antes);
  - muchas ideas sobre los mismos eventos: `docs/research/BANCO_DE_EVENTOS.md`;
  - régimen: `docs/research/GUIA_REGIMEN_PARA_AGENTE_20261107.md`;
  - estrategia de afuera: medir la regla exacta primero (ritual del visor, CLAUDE.md).
- **Población y espacio de eventos declarados** (CLAUDE.md, reglas permanentes).

## 2. Datos, holdout y ventanas
- **Holdout:**
  - frontera única y partición A5: `edgelab/holdout.py`, `docs/incidents/AMENDMENT_HOLDOUT-A4_2026-10-22.md` y
    `docs/incidents/AMENDMENT_HOLDOUT-A5_2026-11-17.md`;
  - ventanas ya consumidas por la familia o su linaje: `docs/research/HOLDOUT_VENTANAS.jsonl` (incluye `consumida_atras`).
- **M1 de futuros de NT8** (`M1NT8:`, 2006/2008 → frontera):
  - antes de usarlo, calibrar la regla contra ticks (`docs/research/papel_m1_20261115/VALIDACION.md`,
    `docs/research/atras_m1_20261117/CALIBRACION.json`);
  - no se usa para reglas de footprint, de velas de ticks o con señal en un CFD.
  - **K40:** con stops chicos frente al rango de la vela, el simulador cobra el stop en el extremo de la vela. Usar el nivel del stop salvo
    un hueco en la apertura (`luximb_hvn._e0_nb`, `ctx["m1_sintetico"]`), y calibrar.
- **Datasets privados de Kaggle:** lanzar con la cuenta dueña (`docs/research/atras_m1_20261117/FALLIDAS.jsonl`).

## 3. Medición (dónde más nos equivocamos)
- **Medir en R** (`docs/research/MEDIR_EN_R_20261102.md`), con el riesgo INICIAL de la propia regla. Verificar en el código que la
  columna de riesgo sea el stop inicial y no el activo al salir (T guardaba el activo).
- **K35, la unidad de riesgo:** comparar estrategias o épocas en la unidad de riesgo de cada regla. El ATR diario diluye 3–10 veces a las
  reglas que arriesgan mucho menos que un ATR (`docs/research/m1_largo_20261117/AUDITORIA_Y_VIEJAS.md`).
- **K36, parámetros en puntos fijos** (topes de stop, objetivos, filtros): antes de comparar épocas, listar los parámetros en puntos y
  verificar si cambian la regla entre épocas. T y E cambian por completo entre 2008 y 2025.
- **K37, puntos por operación entre años:** no se comparan entre años con precios distintos (EdgeReplica). Usar R o ATR.
- **Bruto y neto siempre juntos, con la fricción en R por época** (`docs/research/m1_largo_20261117/RESULTADO.md` §3): el «antes no, ahora
  sí» suele ser fricción relativa.
- **Costos** sólo de `edgelab/costos.py`. Los estimados, únicamente dentro de `costos.estimados_permitidos(<pre-registro>)` (K33).

## 4. Inferencia y decisión
- `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` (A, E2, E3, E5 y E6), y `docs/research_funnel_playbook.md` (ATJ).
- `python tools/potencia_previa.py <ops>`: su línea va al pre-registro (K27). Las pruebas con n < 30 quedan fuera de BH (K29). Todo nulo
  publica su MDE.
- `docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md`: el OOS mata sólo con potencia; FDR; LORD++.
- **K38, ajuste de quien diseñó la regla:** probar fuera de lo que el diseñador pudo haber usado (otros instrumentos u otros años). Los
  módulos de FundedSync sólo «funcionan» en NQ 2020+; T es la excepción porque también pasa ES/YM.
- Lo elegido entre muchas variantes con poca historia arranca con media ≈ 0 (paso 2 de `urgencia_vs_evidencia_20261117`, `atras_m1_20261117`).

## 5. Proceso (K32) y cierre
`antecedentes.py` → `potencia_previa.py` → pre-registro con «Antecedentes:», «Potencia previa:» y «Lectura previa:» → commit →
`python tools/registro_global.py preregistrado …` → correr → resultado con su entrada en FACTORES en el mismo commit →
`python tools/cierre.py` sin tubos → `git show --stat` → push.
