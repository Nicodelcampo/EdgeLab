# Estado del edge real (2026-11-27): dónde está, qué lo confirma y qué lo puede mejorar

Estado: VIGENTE — diagnóstico descriptivo sobre datos de desarrollo ya mirados (2021-02 → 2026-09) y el registro de FACTORES. No suma
pruebas: no elige reglas ni mira el holdout. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Pedido de Nico: «enfocate por ahora en mejorar el edge real, no en cuentas».

## 1. Dónde está la evidencia: información por mes de cada estrategia
Información por mes = (media / sd del R diario)² × 21: lo que cada estrategia aporta para distinguir ventaja de ruido. La fuente son las
corridas NT8 de la cartera, 1 R por operación, 2021-01 → 2026-09.

| Estrategia | Información/mes | Meses para t 2,5 sola |
|---|---|---|
| T (NQ) | 0,33 | 19 |
| R (NQ, AtrPhase con stop 0,5 × ATR) | 0,21 | 30 |
| V (NQ) | 0,17 | 38 |
| RQ5 NQ | 0,11 | 57 |
| Z (NQ) | 0,11 | 59 |
| N, SOMEOD | 0,05–0,06 | 109–139 |
| RQ5 ES, Franklin, ES5N | 0,006–0,02 | 270–1.000 |
| T+R+Z+V (1 R c/u) | 0,50 | 12 |
| Las 10 de la cartera | 0,25 | 25 |

- La ventaja medible de la cartera está en **T, R, V y Z** (los cuatro de NQ). Las cinco más débiles agregan ruido correlacionado: RQ5 ES
  con RQ5 NQ 0,65; Franklin con RQ5 NQ 0,50. Como prueba de ventaja, sumar estrategias **alarga** la confirmación (25 meses las 10 contra
  12 las cuatro).
- Z es la única descorrelacionada de todas (≈ 0). Con riesgo parejo, **T+R+Z** da 0,55/mes.
  - Ninguna intradía la sube (V, SOM, N y F la dejan igual o la bajan).
  - Las swing de Carril 2 la suben un poco: C2_VZ NQ llega a 0,63. Pero mantienen de noche (no van en Lucid), y sus meses HOLDOUT
    estaban en cero en esa serie.

## 2. Qué la confirma y cuánto tarda (forward, el único dato que nadie miró)
- El vendedor de FundedSync pudo ver hasta el 2026-10-29: para T, R y Z no hay historia limpia; la confirmación es el forward desde el
  2026-11-14 (`regimen_forward_20261119/`, canasta T+R con e-proceso).
- Tiempo hasta la decisión, por simulación del e-proceso real (bootstrap en bloques de 5 días de desarrollo):

  | Serie | Efecto de desarrollo | Mitad del efecto | Sin efecto |
  |---|---|---|---|
  | T+R (vigente, cotas [−6, +16]) | EDGE 99,8 %, ≈ 14,5 meses | EDGE 74 %, ≈ 33 meses | corte por caída 97 % |
  | T+R+Z con riesgo parejo (cotas [−8, +23]) | EDGE 99 %, ≈ 13,1 meses | EDGE 68 %, ≈ 27 meses | corte por caída 99 % |

- **No se pre-registra el núcleo T+R+Z.** Gana 1–6 meses, pero una segunda serie de decisión obliga a repartir el α (e ≥ 40 en vez de 20),
  y eso se come la ganancia. El e-proceso actual apuesta cerca de lo óptimo (fracción máxima 0,083 por R contra Kelly ≈ 0,10): ajustar
  cotas o apuestas ahorraría, a lo sumo, 20–30 %.
- **Conclusión:** el tiempo de confirmación (≈ 13–15 meses con el efecto de desarrollo, ≈ 27–33 con la mitad) es una propiedad de los datos
  (señal/ruido de T+R), no del diseño.

## 2b. Corrección (Nico, 2026-11-27): el vendedor vende desde el 2026-09-01
La muestra del vendedor llega, como mínimo, hasta agosto de 2026; el DLL analizado se compiló el 2026-10-29. Fuera de su muestra queda:
- **septiembre de 2026:** un mes, ya leído por EdgeLab;
- **el holdout terminal desde 2026-10-01:** ya abierto para T y A20;
- **el forward desde 2026-11-14.**

La adenda «desde el 1-sep» de `verif_vendedor_20261120/RESULTADO.md` supuso 2025: esos 13 meses (R t 3,57, T 1,90) **están dentro** de
la muestra del vendedor y no son evidencia fuera de muestra. Se mantiene la conclusión de §2: la confirmación es el forward.

## 3. Qué ya no sirve para mejorar el edge con historia (registro de FACTORES)
| Vía | Factor | Resultado |
|---|---|---|
| Transferir R a ES/YM/EMD/RTY | `VEREDICTO_M1_20261117` | Decae después de 2011; NO_CONCLUYENTE con potencia 0,93 |
| Transferir Z a RTY | `F-Z-TRANSFER-RTY` | 97 operaciones, sin potencia |
| Franklin en días volátiles en otros índices | `F-FRANKLIN-DIAS-VOLATILES` | Potencia 0,18–0,23 |
| Bajar fricción con órdenes límite | `F-SELECCION-ADVERSA-PASIVA`, `F-ENTRADA-RETROCESO-SELECCION-ADVERSA` | Selección adversa: se llenan las perdedoras |
| Ensanchar el stop | `F-VENTAJA-EN-PUNTOS-NO-ESCALA` | La ventaja es un monto fijo en puntos |
| Confluencia de señales de la primera media hora | `F-CONFLUENCIA-MISMA-INFORMACION` | Misma información |
| Predecir el día de tendencia | `F-DIA-TENDENCIA-NO-ANTICIPABLE`, `F-GEX-DIA-TENDENCIA` | AUC 0,45–0,55 |
| Variantes de T, R, Z sobre la historia | `F-FUNDEDSYNC-SIN-HOLDOUT-A5-PARA-VARIANTES-B` | El HOLDOUT A5 de FUNDEDSYNC ya está leído: sólo terminal y forward |

## 4. Qué sí puede mejorar el edge real
1. **Flujo de datos nuevos (lo que más acerca):** cada mes de forward aporta 0,6–0,7 unidades de información a T+R(+Z). Hoy el dataset
   sellado de Kaggle termina el 2026-11-17 y el último forward leído es del 2026-11-23. Una subida semanal del M1 de NT8 (o del USATECH
   sellado) hace avanzar la confirmación sola.
2. **Ejecución fiel en NT8 (ejecutabilidad, punto 4 del North Star):** que lo operado capture lo medido.
   - Paridad de la cartera ≥ 98,8 % en el arnés.
   - Faltan la paridad de N en el Strategy Analyzer y el precio de entrada de Franklin y ES5N.
   - R necesita su stop (ya está en el motor NT8 con 0,5 × ATR).
3. **Fuentes de información nuevas, no reglas nuevas sobre las mismas velas:** una ventaja nueva con potencia necesita información
   distinta. Por ejemplo:
   - flujo de órdenes de los ticks de `liquid_tick_v1`, hoy CANDIDATE_NOT_RESEARCH_APPROVED;
   - posicionamiento de opciones intradía;
   - otros horarios u otros activos con fricción baja.

   Abrir una de esas fuentes es decisión de Nico.

Aporte al referente: ubica la ventaja medible en T, R, V y Z de NQ, muestra que sumar estrategias débiles alarga su confirmación y que
el tiempo de confirmación (≈ 13–15 meses) lo fija la señal/ruido, no el diseño. Deja las tres palancas reales: datos forward, ejecución
fiel e información nueva.

## 5. Evidencia conjunta (Nico: «el n diluye las exigencias»), 2026-11-27
12 estrategias candidatas (`estabilidad_cartera_20261126/SERIES_DIARIAS.csv.gz`, 1 micro), t mensual por bloque de A5. Descriptivo:
estos meses ya se habían mirado.

| Bloque | Positivas | Stouffer z (independencia) | Stouffer con ρ ≈ 0,25 | Cartera con riesgo parejo |
|---|---|---|---|---|
| DESC (49 meses) | 12/12 | 7,00 | ≈ 3,6 | t 4,01 |
| REP (16 meses) | 9/12 (signo p 0,07) | 3,35 | ≈ 1,7 | t 2,05 |
| HOLDOUT A5 (22 meses) | 11/12 (signo p 0,003) | 4,54 | ≈ 2,3 | t 2,71 |

Lectura:
- Individualmente casi nada pasa los controles. En conjunto, la cartera es positiva en los tres bloques, con t 2,0–2,7 fuera de DESC.
  La t de la cartera es la cifra honesta, porque ya incluye la correlación.
- Salvedades:
  - el vendedor vio todo el período para los módulos FundedSync;
  - la lista de 12 salió de un pozo mayor (selección de sobrevivientes);
  - el HOLDOUT A5 ya estaba mirado.
- Es evidencia direccional fuerte de que la canasta tiene ventaja neta, no una confirmación limpia. Esa la da el forward.

## 6. Canasta amplia (2026-11-27, continuación)
Ver `canasta_amplia_20261127/RESULTADO.md`:
- el encogimiento fuera de muestra con reglas curadas conserva el 43–70 % del Sharpe;
- Carril 2 replica como canasta (REP t 3,11) aunque ninguna regla sola lo hacía;
- ampliar la intradía con más de lo mismo empeora.

La apertura del HOLDOUT A5 de la canasta Carril 2 sellada está lista y bloqueada por K27 hasta que Nico decida.
