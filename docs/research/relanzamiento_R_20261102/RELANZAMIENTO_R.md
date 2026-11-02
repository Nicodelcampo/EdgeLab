# Relanzamiento de todas las campañas con el P&L medido en R (2026-11-02)

Estado: VIGENTE. Decisión de Nico: «sí, relanza todo». Motivo y alcance: `docs/research/MEDIR_EN_R_20261102.md`. Referente:
`docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Qué se relanza
- **68 campañas, con cid `<original>-R`** (`CAMPANAS.json`). Son todas las del embudo con estado; si existe la versión causal `-C`, se
  relanza ésa.
- **Igual que el original:** módulo, grilla, períodos, justificación, refutación y familia, con código causal.
- **Distinto:** `"estadistico": "R"`. Todas las etapas (DESC, pistas, réplica, OOS, topes, acta y holdout) miden el P&L neto en R.

## Multiplicidad y holdout
- Cada DESC vuelve a registrar sus celdas en el contador global. Los pasos de LORD++ salen del libro de cada familia: es lo conservador.
- Las familias que ya abrieron el holdout (las 12 nominadas y las 3 forzadas) tienen su apertura vigente desde 20261001. Si una versión
  `-R` llega a ACTA, el embudo aplica sus reglas de reuso de ventana. No hay apertura nueva sin acta registrada antes.
- Los resultados en puntos no se borran: quedan como lo medido con el estimando anterior.

## Conducción
4 conductores locales (`tools/embudo_correr.py`) desde esta sesión, con estado en `embudo/`. El chequeo diario los retoma si el contenedor
se reinicia.
