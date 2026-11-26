# REGLA-CARTERA: regla fija de construcción por suma de estrategias decorrelacionadas (pre-registro, 2026-11-26)

Estado: PRE-REGISTRO — la regla se fija acá, antes de aplicarla.
- **Decisión de Nico** (`docs/DECISIONES_20261126.md`): sumar estrategias decorrelacionadas con curvas estables, sin apagar por rendimiento
  reciente.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2** (construcción descriptiva más una validación fuera de tiempo). **Familia:** `CANASTA_CORRELACION`. **Pruebas:** 1.
- **Herramienta:** `tools/regla_cartera.py` (llama a `exigir_contada`).

Cambio respecto a falla previa: no elige por R máximo ni por el tramo reciente. Aplica una regla fija y la valida en un tramo posterior al
de selección.

Antecedentes:
- `estabilidad_cartera_20261126/RESULTADO.md`: series y tamiz.
- `carril2_extension_20261126/RESULTADO.md`: sólo C2_VZ de Carril 2.
- `fs_nfco_a5_20261126/RESULTADO.md`: O confirma en REP, pero sin operar desde 2025-10.
- `adaptar_presente_20261126/RESULTADO.md`: no se adoptan las escalas.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 USD con 1 micro, K52 tamaño, K56 episodios).

Potencia previa: no aplica a una prueba. La validación fuera de tiempo tiene 39 meses (2023-07 → 2026-09). Una diferencia de Sharpe < 0,5
contra la cartera actual no se distingue del ruido, y se publica así.

Diagnóstico de mecanismo: no aplica (una regla con 4 umbrales fijos, sin barrido). No se prueban otros umbrales.

## Justificación económica
Si cada estrategia tiene ventaja positiva aunque sea chica y la correlación entre ellas es baja, la suma a riesgo parejo hace que la
cartera dependa menos de que una sola siga funcionando (ver `DECISIONES_20261126.md`).

## Regla (fija)
**Pozo:** las series con cobertura completa 2019-07 → 2026-09 de `estabilidad_cartera_20261126/SERIES_DIARIAS.csv.gz`, en USD con 1 micro.
Las definiciones de Carril 2 distintas de C2_VZ y C2_EVRP quedan fuera: sólo tienen DESC/REP.

1. **Elegible:** t mensual ≥ 1,5 y ≥ 60 % de años positivos en la ventana de selección.
2. **Orden:** por t mensual, de mayor a menor. Se agrega una estrategia si:
   - su correlación mensual con la suma de la cartera actual es ≤ 0,4;
   - y su correlación con cada miembro es ≤ 0,6.
3. **Pesos:**
   - riesgo parejo: cada una pesa 1 / sd mensual, normalizado a peso medio 1;
   - se informa también la versión entera en micros (redondeo, mínimo 1);
   - y la de 1 micro cada una.
4. **Dos universos:**
   - **Intradía:** sin estrategias que mantengan de noche (fuera SOM, C2_VZ, C2_EVRP y O), para cuentas plano diario como Lucid.
   - **Mixto:** todas, para cuentas que permiten la noche.

**Validación (la decisiva):**
- se aplica la regla con selección en 2019-07 → 2023-06 y se evalúa en 2023-07 → 2026-09, sin volver a elegir;
- se compara contra la cartera actual (INTRADIA8 o INTRADIA8 + INTERDIA3) en el mismo tramo;
- se informa también la regla aplicada a toda la ventana (descriptiva, elegida sobre datos vistos).

## Cómo podría refutarse
- En el tramo de validación, la cartera de la regla tiene un Sharpe o un % de meses positivos menor que la cartera actual: sumar por la
  regla no ayuda.
