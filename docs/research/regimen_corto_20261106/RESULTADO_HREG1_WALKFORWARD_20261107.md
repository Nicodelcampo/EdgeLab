# Resultado — H-REG-1 walk-forward de la regla del trío

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `CANASTA_REGIMEN` / `regimen_corto_20261106`
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`
Procedencia: pre-registro `PREREGISTRO_HREG1_WALKFORWARD_20261107.md`. Corrida `python tools/hreg1_walkforward.py`. Crudo: `resultado_hreg1_walkforward.json`. Semilla 20261107, 200 canastas aleatorias. Holdout no usado.

## Decisión

**No pasa.** En el horizonte primario (3 meses → el mes siguiente, 11 ventanas, nov-2025 a sep-2026) la regla no le gana a los dos controles con t ≥ 2.

| Horizonte | Δ contra azar | t | Δ contra calidad estática | t | Pasa |
|---|---:|---:|---:|---:|---|
| W3H1 (decide) | +0,035 R/op | 0,51 | −0,235 R/op | −2,94 | no |
| W2H1 (no rescata) | +0,112 R/op | 1,34 | −0,148 R/op | −2,22 | no |

La racha reciente queda por encima del sorteo, sin llegar al umbral, y por debajo de elegir las mejores del histórico previo. La canasta estática que se repite desde 2026-04 es `PREAPERTURA-ES`, `PREAPERTURA-NQ`, `DRC-YM-4`.

El trío del tablero (`ABSORCION-NQ-3R`, `PREAPERTURA-ES`, `COMPRESION-NR-GC`) aparece como selección de la ventana de 2 meses que entra a sep-2026. En esa ventana el Δ contra la estática es −0,40 R/op. No es una continuación: es la foto que eligió el trimestre.

## Alcance

Esto refuta, en estas 26 series y estos dos horizontes, «rotar al top 3 por R reciente, una celda por familia e instrumento, sube el R/op del mes siguiente por encima del azar y de la calidad estática». El test de amplitud quedó corrido después, con su propio pre-registro: `RESULTADO_HREG2_AMPLITUD_20261107.md`. No pasa.
