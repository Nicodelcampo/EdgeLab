# DATA_LICENSE_DECISION — licencia de los datos de mercado (M0 / P-07)

**Estado**: `PENDING` — **bloqueante**. Ninguna herramienta de EdgeLab puede
publicar, redistribuir ni cambiar a público un dataset derivado de estos datos
mientras este documento no diga `status: APPROVED`.

Este documento no es prosa decorativa: el bloque `EDGELAB-LICENSE-GATE` de abajo
lo **lee `tools/build_kaggle_bundle.py`** en cada corrida. Con `status: PENDING`
el builder emite veredicto `ABSTAIN_LICENSE`, no escribe `dataset-metadata.json`
y no stagea un solo byte (exit code 2). Es el gate de código que faltaba: hasta
el 2026-08-14 el builder declaraba `CC0-1.0` sobre estos datos.

---

## Bloque de decisión (legible por máquina)

No reformatear: el parser espera `clave: valor`, una por línea, dentro del
comentario. Un valor entre `<>` cuenta como no completado.

<!-- EDGELAB-LICENSE-GATE
schema: 1
status: PENDING
provider: <por completar: entidad que licencia los datos a Nico>
redistribution_allowed: false
kaggle_visibility: private_only
kaggle_license_name: copyright-authors
approved_by: <por completar: nombre de quien aprueba>
approved_at_utc: <por completar: ISO-8601>
terms_source_sha256: <por completar: sha256 del PDF/HTML de los términos>
-->

---

## 1. Qué hay que decidir

| # | Pregunta | Por qué bloquea |
| --- | --- | --- |
| 1 | ¿Qué entidad licencia los datos y bajo qué acuerdo? | Sin el acuerdo concreto no se sabe qué derechos hay. NinjaTrader/Continuum redistribuye datos de CME bajo su propio acuerdo; el usuario final es sublicenciatario, no titular. |
| 2 | ¿El acuerdo permite redistribuir *ticks crudos* a un tercero (Kaggle)? | Es la pregunta central. Subir ticks a un servicio de terceros es distribución, aunque el dataset esté privado (hay una copia en infraestructura ajena). |
| 3 | ¿Qué se considera *dato derivado* y qué tarifas/permisos aplican? | CME tiene un régimen específico de Derived Data con tarifas y política de waiver académico. Un agregado no reversible puede caer ahí; los ticks no. |
| 4 | ¿Quién firma la responsabilidad? | El gate exige `approved_by`. Ninguna herramienta asume esta decisión. |

## 2. Términos que ya se identificaron (insumos, no decisión)

- CME Information License Agreement, Schedule 7:
  `https://www.cmegroup.com/market-data/files/information-license-agreement-schedule-7-2021.pdf`
- CME MDLA Schedule 7 (copia de Thomson Reuters):
  `https://www.thomsonreuters.com/content/dam/ewp-m/documents/thomsonreuters/en/pdf/third-party-restrictions/cme-mdla-schedule-7.pdf`
- CME Derived Data License Fees (2024):
  `https://www.cmegroup.com/market-data/files/2024-derived-data-fees.pdf`

Lectura literal de esos textos: el licenciatario no puede *"license, sublicense,
transfer, sell, resell, publish, reproduce, or otherwise distribute or
redistribute"* la información, ni crear obras derivadas diseminadas
externamente. Mientras ese sea el marco aplicable, `redistribution_allowed`
queda en `false` y la visibilidad en `private_only`.

**Esto es lectura de auditoría, no asesoramiento legal.** La fuente autoritativa
es el acuerdo que efectivamente firmó Nico con su proveedor, y su sha256 va en
`terms_source_sha256`.

## 3. Nombres de licencia prohibidos por código

`tools/build_kaggle_bundle.py` **aborta** (no abstiene: aborta) si este documento
declara un `kaggle_license_name` que afirme derechos que EdgeLab no tiene:
`CC0-1.0`, `PDDL`, `ODbL-1.0`, `DbCL-1.0`, `CC-BY-*`, `MIT`, `Apache-2.0`,
`Unlicense`, entre otros. Permitidos: `copyright-authors`, `other`, `unknown`.

Motivo: el builder v1 (`56184a3`, blob `df383c06`) declaraba
`licenses: [{"name": "CC0-1.0"}]`, es decir dedicación al dominio público de
datos de mercado de terceros. Eso no era un error de tipeo: era una afirmación
de derechos.

## 4. Estado del dataset ya subido

- Dataset: `nicolasbuttaro/edgelab-cme-futures-universe`, v1, 17,97 GB, 57
  archivos, **privado** (confirmado por Nico el 2026-08-14).
- V1 contiene ticks crudos y **contiene el holdout** (ver P-17/P-18): el archivo
  ancla `6E_09-26` trae 871 filas del trade date `2026-07-01`. Por eso v1 es
  `raw_custody` bajo la Cláusula 2 del contrato y no es un dataset de
  investigación.
- Acción mínima mientras `status: PENDING`: **no cambiar la visibilidad**, no
  compartir por link, no crear datasets públicos derivados.

## 5. Criterio de cierre de P-07

1. Nico aporta el acuerdo aplicable y su sha256.
2. Se completan los cinco campos `<por completar>` y se pone `status: APPROVED`.
3. `python tools/build_kaggle_bundle.py --selftest` sigue en 0 fallas.
4. Una corrida del builder sobre los datos reales devuelve `PASS` (o el
   `ABSTAIN_*` que corresponda por otro gate, que se registra tal cual).

Mientras 1–2 no ocurran, el gate hace su trabajo solo: el proyecto no puede
publicar por accidente.
