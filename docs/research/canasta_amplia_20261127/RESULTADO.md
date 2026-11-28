# CANASTA-AMPLIA: la ventaja medida a nivel canasta (resultado, 2026-11-27)

Estado: RESULTADO — EF2 exploratorio (`REGISTRO_POSTERIOR.md`, 9 pruebas contadas después). La apertura del HOLDOUT A5 de la canasta
Carril 2 sellada está pre-registrada y **bloqueada por K27** (`PREREGISTRO_HOLDOUT_CARRIL2.md`).

Herramienta: `python tools/canasta_amplia.py explorar` (`EXPLORACION.json`).

Pedido de Nico: «el n diluye las exigencias tanto en nuestra como en cantidad de estrategias».

## 1. Encogimiento medido con todo el pozo, no con las sobrevivientes
Pozo: 100 series CME, de las cuales 40 tienen los tres bloques A5 con datos.

| Elegidas por DESC | n | REP + | HOLDOUT + | Canasta 1/sd: REP | Canasta 1/sd: HOLDOUT |
|---|---|---|---|---|---|
| todas, sin elegir | 40 | 53 % | 65 % | SR 0,75 (t 0,87) | SR 1,28 (t 1,73) |
| **DESC > 0** | **27** | 59 % | **74 %** | SR 1,11 (t 1,28) | **SR 1,81 (t 2,45)** |
| DESC t > 1 | 13 | 69 % | 85 % | SR 1,12 (t 1,29) | SR 2,09 (t 2,83) |
| DESC t > 2 | 5 | 60 % | 100 % | SR 0,45 (t 0,52) | SR 1,83 (t 2,47) |
| DESC ≤ 0 | 13 | 38 % | 46 % | SR −0,33 | SR 0,18 |

- La pendiente del Sharpe es DESC → REP 0,43 y DESC → HOLDOUT 0,70.
  - Con reglas curadas y con mecanismo se conserva entre la mitad y dos tercios.
  - No es el colapso de las grillas grandes (`F-SELECCION-EN-GRILLAS-GRANDES`, b ≈ −0,26).
- Exigirle más a cada estrategia no mejora la canasta: con 27 rinde como con 13.
- Salvedad: el HOLDOUT A5 de estas 40 ya estaba mirado, y la lista viene de campañas anteriores.

## 2. Pozos con HOLDOUT A5 sellado
Misma regla: DESC > 0, pesos 1/sd.

| Pozo | n | DESC | REP | Meses HOLDOUT sellados | Potencia de una lectura única (efecto × 0,5 / 0,7 / 1) |
|---|---|---|---|---|---|
| **Carril 2** (swing en índices) | 20 | SR 0,86, t 2,98 (143 meses) | **SR 1,66, t 3,11** (42) | 63 | 0,25 / 0,40 / 0,63 |
| Barrido multiactivo (Kaggle) | 24 | SR 0,91, t 1,83 | SR −0,09 | 22 | 0,13 / 0,22 / — |
| Cripto (PIT) | 3 | SR 1,09, t 1,97 | SR −0,66 | 18 | 0,14 / 0,24 / — |

**Carril 2 replica como canasta, aunque ninguna regla sola lo hacía.**
- Sin cada regla, la REP sigue con t 2,48–3,96.
- Aporte en REP: VZ 27 %, EVRP 21 %, TT 18 %, D7 15 %, IBS 12 %, ROT 9 %, TOM 5 %, VBB −7 %; por instrumento, ES 44 % y NQ 40 %.
- 79 % de meses y 95 % de años positivos en REP.

Sin C2_VZ ni C2_EVRP (sus meses HOLDOUT ya los recorrieron las corridas NT8), la canasta sellada (16) da DESC t 2,77 y REP t 2,01.

## 3. El N diluye sólo con mecanismos distintos
| Canasta intradía | REP | HOLDOUT A5 (mirado) | Caída máx. (USD, 1 micro) | Calmar |
|---|---|---|---|---|
| Intradía 8 (actual) | SR 0,81 | SR 2,19 | −13.964 | 1,17 |
| Amplia operable en NT8 (16, mismos motores en más índices) | SR 0,10 | SR 1,90 | −28.531 | 0,69 |
| Todas DESC > 0 (23) | SR 0,55 | SR 1,84 | −28.506 | 0,92 |

- Ampliar la intradía con más de lo mismo no ayuda.
  - Lo que se agrega son rupturas y reversiones de la mañana en índices que se mueven juntos (correlación 0,25).
  - Duplica la caída sin subir el Sharpe.
- Carril 2 contra la intradía: correlación mensual 0,14.

| Combinación (riesgo parejo) | DESC | REP | 2019–2026 |
|---|---|---|---|
| Intradía 8 | SR 1,72 | SR 0,81 (t 0,94) | SR 1,67 |
| + Carril 2 completa | SR 1,51 | SR 2,17 (t 2,50) | SR 1,68 |
| + Carril 2 sellada | SR 1,30 | SR 1,70 (t 1,96) | SR 1,44 |

- Carril 2 se concentra en 2006–2018 y en REP. Desde 2019 su DESC es débil (SR 0,19–0,40), así que a riesgo parejo no sube el Sharpe
  2019–2026.
- No se ajusta el peso sobre estos datos.

Diagnóstico de grilla: sin grilla. La única perilla es la regla de inclusión y se publica completa (§1).
Episodios: Carril 2 en REP, 79 % de meses y 95 % de años positivos; intradía 8, 63 % de meses positivos 2019–2026.

## 4. Qué queda
1. **Confirmación limpia de la canasta Carril 2 sellada:** apertura única de su HOLDOUT A5 (63 meses), pre-registrada.
   - Hoy está bloqueada por K27: potencia 0,25 con la mitad del efecto y 0,63 con el efecto completo.
   - Levantar K27 para esta apertura es decisión de Nico.
   - Si no se levanta: forward, que es swing y necesita una cuenta que mantenga de noche.
2. **Criterio de cartera:** sumar estrategias **descorrelacionadas y de mecanismo distinto**, no más de la misma familia.
   - Para Lucid (sólo intradía) se mantiene la Intradía 8.
   - Para una cuenta que admita mantener de noche, Intradía 8 + Carril 2.

Aporte al referente: con evidencia, la canasta replica donde las reglas sueltas no (Carril 2, REP t 3,11) y diversificar suma sólo con
mecanismos distintos. Deja lista para una decisión de Nico una confirmación limpia de 63 meses de la canasta sellada.
