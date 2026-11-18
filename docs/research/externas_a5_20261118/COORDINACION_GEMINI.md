# EXTERNAS: coordinación entre Claude (EXTERNAS_A5) y Gemini Argon (EXTERNAS-ESTRUCTURALES-A5) (2026-11-18)

Estado: VIGENTE — nota operativa para los dos agentes; se supera cuando los dos resultados estén mergeados.

## Lo que hizo Claude en esta rama (`claude/vibrant-clarke-s9z6e2`) — leer antes de mergear
- **OPTION-ALPHA (OA1–OA8) ya corrió y está CERRADA:** 0/13 en BH en DESC 2006–2025 y R neto negativo en las 8
  (`docs/research/option_alpha_20261118/RESULTADO.md`, factor `F-OPTION-ALPHA-FUTUROS`, NO_REPETIR). No volver a correrla ni usar
  `OA1`–`OA8` como «señal bruta viva» (el plan de Gemini del 18-nov la listaba así): ninguna pasó.
- **EXTERNAS_A5 (familia nueva, 114 pruebas contadas en `TRIAL_REGISTRY_GLOBAL.jsonl` antes de correr):** las 114 variantes del
  catálogo `c8d0e912` tal cual, en NQ/ES/YM/GC 2006–2025 con A5, módulo `edgelab/research/externas_a5.py` (`X000`–`X113`, mapa en
  `MAPA.json`). Fase 0 sin retornos (fricción en R ≤ 0,08 y ≥ 30 sesiones DESC) corriendo; en una prueba en NQ 2010 sólo pasaban
  `X036`–`X039` (Dual Thrust). Sólo las que pasen la fase 0 van a DESC.

## Superposición con EXTERNAS-ESTRUCTURALES-A5 (Gemini)
- **`X036`–`X039` (Dual Thrust de fábrica) pertenecen a la familia `EXTERNAS_A5` y ya están contadas.** Si Gemini corre su
  «auditoría» de esas cuatro con desenlaces, son las mismas pruebas mirando los mismos datos: no se cuentan de nuevo en otra familia ni
  se nomina con ellas dos veces. Una de las dos corridas se declara la oficial (propuesta: la de `EXTERNAS_A5`, que se registró
  primero) y la otra queda como verificación cruzada del motor, sin decisión propia.
- **`ES1`–`ES8`** (versiones re-diseñadas: otro marco temporal, stops amplios, D1/H1, Kalman como spread) son una familia distinta y
  legítima, con linaje `padres: ["EXTERNAS_A5"]` en `LINAJES.jsonl`: heredan la multiplicidad de haber mirado las originales.
- Si una corrida usó código que después se corrigió (la nota de Gemini menciona el trailing de PMax H1 y las llaves del mapa de Dual
  Thrust), esa corrida se documenta como descartada y no se mira (regla de CLAUDE.md, grilla masiva).
- **Un solo escritor por árbol:** Gemini trabaja en la copia local de Nico; Claude en esta rama remota. Antes de mergear, `git fetch`
  y merge (nunca rebase ni force-push sobre la rama del otro).

## Pendiente que deja Claude
- **P-97 — T como edge de régimen 2021+** (`docs/research/t_regimen_20261118/PROPUESTA.md`): pausado por Nico unas horas.
