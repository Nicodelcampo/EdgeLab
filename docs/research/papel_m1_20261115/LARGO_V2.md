# Papel M1 — el largo con régimen, v2 con el motor corregido (K40) (2026-11-18)

Estado: RESULTADO — reemplaza a `LARGO.md` (v1, DESCARTADA por K40).
- **Pre-registro:** `PREREGISTRO.md` con la enmienda 1: el largo NO da de baja; mapa y encendido por régimen.
- **Datos:** `LARGO_v2.json` y `resultados/OTR930-NQ-CANASTA_*.json`.
- **Código:** el mismo cálculo que la v1 (`edgelab/research/papel_regimen.py`, `cartera.papel.canasta_por_sesion`; variables causales
  del día previo: vol20, tend60, noche y dst).
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

**OTR930-NQ.** Comando: `python tools/papel_m1.py largo OTR930-NQ-CANASTA` → `LARGO_OTR930-NQ-CANASTA.json`, con la canasta de la ficha
(K47), el ranking de la noche sin huecos y la guarda de causalidad K48 (para OTR930, que entra después de las 09:30, las cuatro
variables son causales). ASIA-NQ se mide aparte (`docs/research/asia_noche_20261118/`): su variable `noche` no era causal.

## OTR930-NQ (canasta por sesión, puntos netos, M1 USATECH)
| Tramo | Sesiones | Media (ee) |
|---|---|---|
| 2012–2019 | 1.433 | −0,82 (0,11) |
| 2020–2023 | 833 | −1,00 (0,53) |
| 2024 → 2025-07 | 324 | −3,01 (1,11) |
| 2025-08 → 2026-09 (validación) | 243 | +3,86 (2,05) |

- **Trimestres positivos:** 12 de 54.
- **Mapa de régimen:** negativo en todos los estados de las cuatro variables. Ninguna ordena el resultado; la noche alta es la peor
  (−1,43).
- **Encendido walk-forward** (50 trimestres) contra estados al azar: vol20 p 0,93; tend60 p 0,94; noche p 0,40; dst p 0,96. **Sin
  régimen detectable.**
- **Lectura:** igual que la v1. La regla pierde en 12 años y vive sólo en el último. No hay un estado observable antes de operar que la
  separe. Por el principio de edges actuales no se da de baja, pero no tiene respaldo histórico ni filtro: la decide el forward.
- **M1 es optimista frente a ticks en esta regla** (validación: +10,4 contra +6,3 por sesión en el tramo común). Lo histórico negativo
  no es un artefacto pesimista.

## ASIA-NQ: la «noche movida» (corrección del 2026-11-18)
- **Primera lectura de hoy:** decía que ASIA no pasaba la validación de la fuente. Era un error de agregación (K47); con la canasta de
  la ficha calibra (`VALIDACION.md`).
- **Fuga de la variable:** la `noche` de ASIA no es causal (K48). Es el rango de la misma noche en la que ASIA entra.
- **Prueba causal:** se hizo con la noche anterior, en datos no mirados y con futuros M1 (`docs/research/asia_noche_20261118/`).
