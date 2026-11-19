# CONFLUENCIA: ¿las señales intradía con bruto real rinden neto cuando otra señal independiente ya confirmó la dirección del día? (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Pedido de Nico:** «adelante con la confluencia: RQ5, FM1/FM2, Dual Thrust, SOM y Franklin tienen bruto real y neto negativo … sólo cuando
  dos o tres coinciden en día y dirección». Intradía: operable en LucidFlex.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC de A5; EF4 en REP sólo si se nomina y con potencia K49. **Familia:** `CONFLUENCIA_A5` (nueva; padres `ROBOQUANT_A5`,
  `FLUJOS_MACRO_A5`, `SOM`, `FRANKLIN`).
- **Herramienta:** `tools/confluencia.py desc|rep` sobre operaciones ya calculadas: SOM y Franklin (`mejora_sf_20261119/TABLA.csv.gz`, R neto),
  RQ5/RQ6 (`friccion_rq_20261119/OPS.csv.gz`, celda esc1, neto = R − fricR), FM1/FM2 (`flujos_macro_20261119/OPS_DESC_REP.csv.gz`, neto =
  r_P_obj_stop_fin − fricción canónica / rg). `holdout.a5_bloque`, bootstrap por sesión, `a5.bh`, `a5.plan_lectura`, `libro_lord`.
  `registro_global.exigir_contada` al inicio. **Dual Thrust queda fuera:** no hay operaciones guardadas (sólo el resumen de la auditoría).

Antecedentes: FRICCION-RQ (RQ5+RQ6 en una sola posición cuando coinciden empeora: −0,071 contra −0,021), MEJORA-SF M1 (Franklin concordante con
SOM +0,064 R, p 0,19), FLUJOS-MACRO (FM1/FM2 bruto real, neto negativo), F-SENALES-ESTABLES-SOM-FRANKLIN, MIRADA_HUMANA_20261119.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36, K40, K48 causalidad, K49, K51, K52, K55/K56).

Diagnóstico de mecanismo: no hay grilla; las reglas base están congeladas en sus versiones medidas. La única perilla es el orden causal fijo
de abajo. Se publican operaciones por clase (confirmada / no confirmada) y por estrategia, y la descomposición por meses (Episodios) del
resultado con tools/diagnostico_grilla.py.

Potencia previa: DESC NQ+ES 2006–2025: SOM ≈ 5.400, Franklin ≈ 1.500, RQ5 ≈ 2.300, RQ6 ≈ 2.700, FM1 ≈ 2.000, FM2 ≈ 1.000 operaciones; se espera
que entre un tercio y la mitad tenga confirmación previa: miles por clase, ee del contraste ≈ 0,02–0,03 R. REP sólo con potencia ≥ 0,8 (K49).

## Justificación económica
- Cada señal capta el mismo fenómeno de fondo (el flujo direccional del día: cobertura de opciones, rebalanceo, momentum de apertura) con
  ruido propio. Cuando dos señales independientes coinciden, el día tiene más probabilidad de ser direccional: más ventaja por operación con
  la misma fricción por operación.

## Regla (fija)
- **Orden causal de las señales** (hora de entrada): SOM 09:35; Franklin 10:00; FM1 10:00; FM2 su hora; RQ5 10:00–11:30; RQ6 10:30–12:30.
- Una operación base B (de cualquiera de las 6 reglas) está **confirmada** si, el mismo día y en el mismo instrumento, al menos otra regla
  distinta ya disparó en la **misma dirección** a una hora ≤ la de B: SOM confirma a todas las demás; Franklin y FM1 confirman a las de hora
  ≥ 10:00 (entre ellas, mutuamente: misma hora); FM2 confirma a las de hora ≥ su hora (para RQ5/RQ6 sólo si FM2 ≤ 10:00); RQ5/RQ6 no
  confirman a nadie (su hora exacta no está en los archivos). Instrumentos: NQ y ES.
- **Pruebas en DESC (2, BH q 0,10):** P1 contraste R neto (confirmadas − no confirmadas), todas las bases juntas; P2 R neto de las confirmadas
  > 0 (la regla operable). Bootstrap por sesión, p unilateral. Descriptivo: por estrategia y con ≥ 2 confirmaciones.
- REP: una lectura con LORD++ de `CONFLUENCIA_A5`, sólo si se nomina y la potencia en días es ≥ 0,8.
- **Cómo podría refutarse:** contraste ≤ 0, o confirmadas con neto ≤ 0 aunque el contraste sea positivo (mejora sin neto).
- **Contador:** 2 pruebas en `CONFLUENCIA_A5`.
