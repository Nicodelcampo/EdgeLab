# CRIPTO-PIT: las 3 reglas cripto de la auditoría con universo punto en el tiempo y costos con deslizamiento (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO — se fija antes de medir (el universo ya está armado: sólo usa volumen y fechas de cotización, nunca retornos).

- **Origen:** pista `F-CRIPTO-TENDENCIA-DECORRELACIONADA`; frente 2 de `docs/research/auditoria_cartera_20261126/REVISION_CLAUDE.md` §3.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (réplica ampliada de un hallazgo exploratorio). **Familia:** `CRIPTO_BINANCE` (lleva 7 pruebas contadas después de mirar).
  **Pruebas:** 4.
- **Herramienta:** `python tools/cripto_pit.py medir` (llama a `exigir_contada`).

Cambio respecto a falla previa:
- **Universo:** la auditoría eligió hoy 8 monedas que sobrevivieron. Acá el universo es punto en el tiempo e incluye las dadas de baja.
- **Costos:** la auditoría cobró sólo la comisión. Acá se cobra comisión más deslizamiento.
- **Reglas:** no se tocan. Se miden tal como las escribió la auditoría (sin re-optimizar nada).

Antecedentes:
- `auditoria_cartera_20261126/RESULTADO.md` §4 y `REVISION_CLAUDE.md` §2.5: 3 de 5 reglas positivas en DESC y REP con 8 monedas, t 1,2–1,8
  cada una, 1/N t 2,31 en 51 meses, correlación con CME +0,02.
- No hay otra campaña cripto en EdgeLab (`tools/antecedentes.py "cripto"`: sólo esa familia).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36: la unidad es USD sobre $10.000 de base; K49: costos declarados antes; K27:
potencia antes de abrir un holdout).

Potencia previa: cripto_1n_dias.csv (1/N de la auditoría, 8 monedas, R = USD/100): 22.2 ops/mes, R/op +0.086, sd 1.29, n para decidir 1410,
63.5 meses → NO: tarda 63.5 meses en decidir (> 60). Lectura de N 540 (≈ los días HOLDOUT A5 2021–2026) con la mitad del efecto: potencia
0,191 (NO se abre). Por eso este paso es sólo la réplica ampliada en DESC y REP. El HOLDOUT A5 se abre sólo si la potencia recalculada con
el universo ampliado pasa la compuerta K27, con un pre-registro aparte.

Diagnóstico de mecanismo: sin grilla (3 reglas fijas y su 1/N). Qué mueve cada regla:
- Donchian 20/10 diario: sigue tendencias de semanas.
- EMA 24/96 en 4 h con stop de 2,5 ATR: tendencias de días, con mucha rotación (≈ 500 operaciones por mes en 8 monedas). Es la más
  sensible al costo.
- Momentum transversal 14 días neutral: gana si las monedas fuertes siguen siéndolo frente a las débiles, sin exposición al mercado.

Se publican los meses positivos por regla (episodios) y los tres escenarios de costo.

## Justificación económica
En cripto la tendencia de serie de tiempo y el momentum transversal están documentados (inversores minoristas que persiguen precio,
apalancamiento que se desarma en cascada, financiamiento que ajusta lento). Es un motor que no depende de la sesión de EE. UU.: su
correlación con la cartera de futuros fue +0,02. Sumarlo es diversificación real, si sobrevive al universo completo y al costo.

## Diseño (fijo)
- **Universo:** perpetuos lineales USDT-M de Binance, vivos y dados de baja (listado completo de data.binance.vision). Cada mes entran
  las 25 con más volumen en USDT de los 30 días previos al 1.º del mes, si cotizaron ≥ 60 días antes (`UNIVERSO_PIT.csv`).
- **Reglas:** las 3 de la auditoría, congeladas (`tools/cartera_cripto_binance.py::build_strategies`), con tres cambios que impone el
  universo variable:
  1. posición 0 en monedas fuera del universo ese mes (se cierra al salir, con costo);
  2. tamaño por moneda × 8 / n_elegibles, para mantener el presupuesto de riesgo de 8 monedas;
  3. el momentum transversal rankea y neutraliza sólo entre elegibles.
- **Costos:** base 20 pb ida y vuelta (comisión taker 5 pb por lado + deslizamiento 5 pb por lado) más el funding real cada 8 h.
  También se informan, sin decidir con ellos, 10 pb (lo de la auditoría) y 30 pb.
- **Datos:** 2020-09 → 2026-09-30 (calentamiento hasta 2020-12). Se leen sólo los días DESC y REP de A5. HOLDOUT y EMBARGO quedan
  sellados (NaN en las series guardadas). Nada desde 2026-10-01.
- **Pruebas (4):** 1/N de las 3 reglas (principal) y cada regla sola. BH q 0,10 sobre las 4, en DESC+REP con el costo base.

## Cómo se lee (decidido antes)
- **Pasa al plan del HOLDOUT A5** (pre-registro aparte) si se cumplen las tres:
  - el 1/N con costo base tiene t ≥ 2 en DESC+REP;
  - la media del 1/N es > 0 en REP;
  - la potencia recalculada (`tools/potencia_previa.py`) pasa la compuerta K27.
- **Viva sin potencia:** si el 1/N es positivo pero no pasa K27, va a papel/forward con vigilancia secuencial y no se abre el holdout.
- **Refutada en su forma actual:** si el 1/N con costo base tiene media ≤ 0 en DESC+REP. Lo de la auditoría era supervivencia o costo.

## Cómo podría refutarse
- Media del 1/N ≤ 0 en DESC+REP con 20 pb: la ventaja de la auditoría venía de las 8 monedas elegidas hoy o de no cobrar deslizamiento.
- Alguna regla sola con media > 0 sólo a 10 pb y ≤ 0 a 20 pb: esa regla vive de la comisión mínima y no es operable con deslizamiento real.
