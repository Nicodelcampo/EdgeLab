# PRESET-DIVERSIFICADA: Intradía + N + SOMEOD en NT8 y tamaño por cuenta LucidFlex (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO — se fija antes de correr la simulación de cuentas.

- **Decisión que lo origina:** Nico, `docs/DECISIONES_20261126.md` (sumar estrategias decorrelacionadas, no cortar por rendimiento
  reciente) y orden de frentes de `docs/research/auditoria_cartera_20261126/REVISION_CLAUDE.md` §3 (frentes 1 y 6).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2** (descriptivo de cuenta; no elige reglas). **Familia:** `CANASTA_CORRELACION`. **Pruebas:** 1.
- **Herramientas:**
  - `tools/cartera_lucid.py simular --universo DIVERSIFICADA10` (simulador calibrado K28,
    `tests/research/test_cartera_lucid_calibracion.py`);
  - `tools/nt8_cartera_paridad.py` (arnés de NT8).

Cambio respecto a falla previa: no elige estrategias por resultado (la inclusión de N y SOMEOD la fija la decisión de Nico y su
operabilidad en NT8, no su P&L). Tampoco usa variantes elegidas mirando el HOLDOUT A5 (stops ATR nuevos, V re-preciada): usa los motores
NT8 tal como están instalados. F, C y O quedan fuera porque no tienen motor NT8.

Antecedentes:
- `cartera_lucid_20261125/RESULTADO.md`: 8 estrategias a 1 micro sólo en la 150K (P(cobrar > evaluación) 0,27 contraída).
- `candidatas_nt8_20261125/SOMEOD/`: corrida NT8 de SOMEOD (1.871 operaciones 2019–2026).
- `fs_nfco_a5_20261126/RESULTADO.md`: N NO_CONCLUYENTE en A5.
- `estabilidad_cartera_20261126/RESULTADO.md`: N suma estabilidad.
- `auditoria_cartera_20261126/REVISION_CLAUDE.md`: a igual riesgo, la caída baja por tamaño, no por selección.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 USD con 1 micro y fricción canónica del micro; K52 tamaño; K28 simulador
calibrado).

Potencia previa: no aplica (descriptivo de cuenta, sin contraste). La diferencia entre 8 y 10 estrategias se informa con su error de
Monte Carlo (10.000 caminos, semilla fija); una diferencia de P(cobrar) < 0,02 se lee como empate.

Diagnóstico de mecanismo: no aplica (sin grilla). Los planes son los mismos del plan de `cartera_lucid` (UNOx1–4, RIESGO_IGUAL e
INV_VOL con B 100–800), sin planes nuevos.

## Justificación económica
N (máximos de 5 días, largo) y SOMEOD (momentum de la apertura, cierre en el día) son motores distintos de las rupturas de la mañana
(T, R, Z, V) y de las reversiones (RQ5, Franklin, ES5N). Si cada una tiene ventaja chica y la correlación es baja, sumarlas a 1 micro
baja la dependencia de que una sola siga funcionando. En una cuenta con pérdida máxima fija, lo que decide el cobro es el riesgo
frente a esa pérdida, no la cantidad de estrategias.

## Qué se corre (fijo)
1. **Arnés NT8** de la composición `NQ:T,R,Z,V,N,SOMEOD,RQ5,FR;ES:RQ5,ES5N` (1 micro c/u), modos virtual y broker, 2018-12 → 2026-09.
   Se informa:
   - la paridad contra las corridas NT8 individuales;
   - 0 descuadres broker/libro.

   Las operaciones de N del modo virtual van a `ARNES_N_NQ.csv.gz` (N no tiene corrida NT8 propia).
2. **Simulador de cuentas** con el criterio ya fijado en `cartera_lucid`:
   - por cuenta (25K, 50K, 150K), máxima P(cobrar más que la evaluación) con media contraída a la mitad;
   - empate a 0,02 → mayor valor esperado;
   - se descartan los planes por encima del tope de micros de Lucid.

   Se corre para `INTRA8` (las 8 de hoy) y para `DIVERSIFICADA10`.

## Cómo se lee (decidido antes)
- La inclusión de N y SOMEOD no depende de este resultado (decisión de Nico).
- Este resultado decide el **tamaño por cuenta**: el plan elegido de `DIVERSIFICADA10` es la configuración propuesta del preset nuevo.
  Si en una cuenta ningún plan supera la P(cobrar) de «sin ventaja» (media cero) por 0,05, esa cuenta no lleva la cartera.

## Cómo podría refutarse
- La paridad del arnés contra NT8 baja del 95 % de operaciones emparejadas en alguna estrategia con corrida NT8: entonces el preset no
  se propone hasta corregirlo.
- Con 10 estrategias, la P(cobrar) contraída de la cuenta elegida queda más de 0,02 debajo de la de 8 con el mismo plan: entonces sumar
  N y SOMEOD no ayuda en esa cuenta, y se informa así (la decisión de incluirlas la retoma Nico).
