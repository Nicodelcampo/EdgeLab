# Auditoría de Claude a la Espiral de Antigravity, fases 1 y 2 (2026-11-28)

Estado: AUDITORÍA — revisión de los commits `4fca10ae`, `8ad50c8f`, `117c7eaf`, `cbc440ba`, `dea0f909` y `456307bb`.
- Se revisaron los pre-registros, los resultados, el código, el orden de los commits y el registro de aperturas del holdout.
- Se recalculó lo que se pudo con los datos de este entorno (`tools/auditoria_espiral_20261128.py`, `CARRIL2_VOL_LOCAL_SIN_HOLDOUT.json`).
- No se agregan pruebas al contador: son las mismas pruebas pre-registradas, medidas con la máscara corregida.

## Resumen
| Campaña | Veredicto de Antigravity | Auditoría |
|---|---|---|
| MACRO_CTA_VRP_20Y | Canasta Sh 0,77 (t 3,04), PISTA_VIVA | **Se acepta con salvedad grande:** la pata principal no es un mecanismo, es exposición pasiva (§3) |
| M1_RELVAL_EVENTOS_20Y | Pre-FOMC Sh 0,69 (t 2,56) | **Se acepta y se refuerza:** se sostiene después de su publicación. Dos defectos chicos de calendario (§4) |
| CRIPTO_FUNDING_CARRY_PIT | NO_REPETIR | Se acepta |
| FX_MACRO_FIX_20Y | Canasta en contra en REP | Se acepta. Buen uso de la guarda K58. **No se acepta** sacar FXF3 de la canasta para los pools (§5) |
| CARRIL2_EMD | NO_CONCLUYENTE | **El veredicto se mantiene, pero la prueba leyó meses HOLDOUT sin apertura registrada** (§1) |
| CARRIL2_VOL_LOCAL | PISTA_VIVA (VBB local, diferencia t 2,32) | **Sin los meses sellados y en EE. UU., no se sostiene:** VBB local da t −0,88 contra su control (§1–§2) |
| CRIPTO_XSMOM_SPOT_PRE | NO_CONCLUYENTE (t 0,61) | Se acepta; K60 bien aplicada. La pata corta no era operable en spot 2017–2019 (§6) |
| Síntesis de las dos fases | Pools Sh 0,96–1,25, potencia K27 hasta 0,89 | **Descriptivo, no evidencia:** los pools se armaron con los sobrevivientes ya vistos (§5) |

## 1. Lectura del holdout sin apertura (grave)
- **CARRIL2_EMD:** las pruebas primarias «todo 2006–2026» y «desde 2009» incluyen los meses HOLDOUT de A5, y se publica además una fila
  HOLDOUT (63 meses).
- **CARRIL2_VOL_LOCAL:** en Dow, Russell 2000 y GC, `tools/carril2_vol_local_20261127.py` lee todos los meses anteriores a 2026-10-01, sin
  máscara A5.
  - Dow ≈ YM, Russell ≈ RTY, y GC son instrumentos del universo de Carril 2.
- `HOLDOUT_VENTANAS.jsonl` no tiene ninguna apertura para estas familias. La familia de Carril 2 (`CARRIL2_A5`) ya usó la suya.
- Con reglas congeladas no hay selección dentro de la prueba, pero:
  - el protocolo exige la apertura registrada antes de lanzar;
  - cualquier decisión posterior apoyada en estos números queda contaminada.
- **Corrección:**
  - EMD: el veredicto se lee en DESC y REP. Núcleo 5 contra su control: DESC t 2,06, REP t 0,46. Sigue NO_CONCLUYENTE.
  - VOL_LOCAL: re-medida en §2.

## 2. Volatilidad local: lo que queda sin meses sellados
Re-medición (mismas funciones y pares de Antigravity; entrada y salida en meses DESC o REP; Dow, Russell 2000 y GC; 186 meses):

| Regla (diferencia contra control N) | Local | VIX de EE. UU. |
|---|---|---|
| C2_VBB | **Sh −0,22 (t −0,88)** | Sh −0,15 (t −0,60) |
| C2_VZ_1F | Sh 0,27 (t 1,06) | Sh 0,18 (t 0,71) |
| C2_EVRP_1F | Sh 0,37 (t 1,45) | Sh 0,37 (t 1,44) |

- En EE. UU., la volatilidad local (VXD, RVX) da lo mismo que el VIX. Era esperable: están muy correlacionadas.
- El «rescate» de VBB (diferencia t 2,32) venía de mezclar ASX200 con meses sellados. En meses limpios de EE. UU., VBB no le gana a su
  control.
- **Lo valioso del trabajo de Antigravity se mantiene:**
  - El ASX cierra 14 horas antes que el VIX de la misma fecha, así que usar el VIX del mismo día en Asia mira el futuro. Así salía el
    t 12 de VZ en ASX.
  - Eso afecta también a VBB en ASX, Nikkei y Hang Seng en H1 de CONFIANZA-SIN-FORWARD: el número de VBB afuera no vale en ningún sentido.
  - El resultado de H1 sin VBB (t 3,84) no usa el VIX y queda en pie.
- ASX200 no se re-midió: no es del universo de Carril 2 y los datos (`^AXVI`) no están en este entorno.

## 3. MACRO_CTA_VRP: la pata «vol-managed» es exposición pasiva
- MVC4 son pesos sólo comprados en TLT, IEF, GLD, DBC y HYG, escalados por 1/varianza.
- Su propio control estático 1/vol da más: Sh 0,838 contra 0,766. Ajustar por volatilidad (Moreira-Muir) **no agrega nada**.
- Lo que rinde es la prima de bonos, oro y crédito (correlación 0,475 con RP4).
- La canasta MVC (Sh 0,77) es MVC1 (tendencia, Sh 0,43, t 1,68) más esa exposición. **No es una fuente nueva de ventaja.** Al sumarla a
  una cartera hay que tratarla como beta de activos no-equity, no como alfa.

## 4. Pre-FOMC: se sostiene después de publicarse (y dos defectos chicos)
- Por período, con la serie publicada (meses DESC+REP):

  | Período | Sharpe | t |
  |---|---|---|
  | 2008 → 2011-06 | 0,88 | 1,42 |
  | 2011-07 → 2015-02 (borrador y publicación de Lucca-Moench) | 0,60 | 0,99 |
  | Desde 2015-03 | **0,79** | **2,32** |
  | Desde 2022 | 1,33 | 2,49 |

  **No decae después de publicarse**, a diferencia de Carril 2 afuera. Es la mejor noticia de las dos fases.
- **Defecto 1: el calendario incluye reuniones no programadas** (2008-03-11, 2008-10-08, 2020-03-03, 2020-03-19, 2020-03-23). Entrar a
  las 14:00 del día anterior a una reunión que nadie conocía mira el futuro. Sin esas reuniones: Sh 0,67, t 2,51. No cambia el veredicto.
- **Defecto 2: en 2011–2012, los días de conferencia de prensa el comunicado salía a las 12:30.** La salida fija a las 13:55 incluía la
  reacción al anuncio. Son 6 eventos y 4 % de la ganancia.
- **Concentración:** los 5 mejores eventos suman 75 % de la ganancia (2008-10-29 solo, 28 %). La t no depende de ellos: sin el mayor,
  2,62.
- **Corrección pedida:** usar sólo el calendario programado y salir 5 minutos antes del horario real de cada comunicado.

## 5. Pools armados después de mirar
- Las síntesis combinan los sobrevivientes: «Arquitectura 5F» Sh 1,25, t 4,66, potencia K27 0,89.
- FXF3 se sacó de una canasta que falló en REP (la regla pre-registrada de la canasta la incluía junto a FXF4).
- Los pesos 40/40/20 se fijaron después.
- Elegir qué entra después de ver DESC y REP es selección (K60): **el Sharpe y la potencia de esos pools no sirven para decidir abrir
  un holdout**. Lo admisible es lo pre-registrado: cada canasta con su regla, y el pool sólo si sus componentes y pesos se declaran antes.

## 6. Otros
- **XSMOM spot 2017–2019:** la pata compradora da Sh −0,06 y la vendedora 0,34. En Binance spot no había margen para vender en corto
  hasta julio de 2019, así que lo medido no era operable. Para una versión sólo comprada no hay evidencia.
- **Orden del proceso:**
  - Fase 1: el conteo en el registro global entró en el mismo commit que los resultados (`8ad50c8f`), no antes de correr (guía §5).
  - Fase 2: lo hizo bien (`cbc440ba` antes de `dea0f909`).
- **Linajes:** las 7 familias nuevas no estaban en `LINAJES.jsonl`. Quedan declaradas en este commit, con sus padres (CARRIL2_EMD y
  CARRIL2_VOL_LOCAL ← CARRIL2_A5; CRIPTO_XSMOM_SPOT_PRE y CRIPTO_FUNDING_CARRY_PIT ← CRIPTO_BINANCE; MACRO_CTA_VRP_20Y y
  FX_MACRO_FIX_20Y ← MACRO_RISK_PREMIA), y heredan su multiplicidad.
- **MRV4 fuera de la canasta:** la condición extra (exceso sobre comprar y mantener > 0) no estaba en la regla de la canasta, pero sí en
  el criterio de refutación del pre-registro. Se acepta.

## Qué cambia para el plan
- **Pre-FOMC** es la mejor candidata nueva: mecanismo publicado, sigue después de publicarse y no se correlaciona con Carril 2. Siguiente
  paso: corregir el calendario y pre-registrar su lectura del HOLDOUT A5 con plan de potencia, como familia nueva que todavía no usó su
  apertura.
- **Carril 2:** ni EMD ni la volatilidad local suman evidencia limpia. Su confianza queda donde la dejó CONFIANZA-SIN-FORWARD.
- **Macro CTA:** sólo MVC1 (tendencia) es candidata a alfa, y débil (t 1,68).

Aporte al referente: separa lo que sí acerca a una ventaja (la deriva previa a la Fed, robusta después de publicarse) de lo que eran
lecturas del holdout, beta pasiva o selección después de mirar, antes de que entren a una cartera.
