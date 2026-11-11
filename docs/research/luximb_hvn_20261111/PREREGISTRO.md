# LUXIMB-HVN — la regla de expansiones con OG/VI en su 25 % inicial, medida a fondo (NQ y USATECH)

Estado: PRE-REGISTRO (2026-11-11, pedido de Nico). Escrito antes de generar ninguna tabla. Etapa **EF2 exploratoria** sobre datos de
desarrollo ya mirados por el linaje; la confirmación es en datos que nadie miró (§5).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `LUXIMB_HVN`; linaje: `LUXIMB_FADE_VISOR`, `LUXIMB_GRILLA`, `EXPANSION_ZONAS` (hereda su multiplicidad y sus ventanas
consumidas del holdout: 1–22 oct). Código: `edgelab/research/luximb_hvn.py` (tests `tests/research/test_luximb_hvn.py`),
kernel `tools/kaggle_grilla/luximb_hvn_main.py` (`python tools/luximb_hvn.py lanzar|traer`), análisis `tools/luximb_hvn_analisis.py`.

## 1. Pedido
Medir la regla del visor (expansión con zonas LUX-IMB OG/VI en su 25 % inicial; fade hacia el origen A) en NQ y en USATECH, cada
uno con sus zonas. Preguntas: (a) cuando el precio primero se extiende más allá del extremo B y después vuelve, ¿había más allá un
nodo de volumen alto (HVN) del pasado? (b) entrar esperando la interacción con esa franja y la vuelta, con distintas distancias de
retorno, stop y objetivo; (c) lo mismo sin mirar el volumen: esperar que se aleje x y vuelva x; (d) en la entrada al confirmar,
tomas parciales y/o break even; (e) definición del impulso parametrizable.

## 2. Espacio de eventos (enumerado antes de congelar la población)
Alrededor de una expansión: su creación, la marca en tiempo real (vela M1 en que el tramo cumple amplitud, rapidez y zonas), la
extensión más allá de B, la interacción con un nodo de volumen más allá, la vuelta, el toque de la mitad y de A, la invalidación
(extensión excesiva) y el vencimiento; también el estado continuo (distancia a A/B en cada vela). **Se miden dos:** la marca (E0) y
la vuelta después de una extensión (EXT). Por qué: son las dos entradas que pide Nico. **Control:** la misma marca sin condición de
zonas (definición `z0` de cada detector): si el control da lo mismo, el efecto es de «expansión grande», no de las zonas.
Cómo podría refutarse la población: real − control ≈ 0 en el mecanismo y en el P&L.

## 3. Definiciones
- **Impulso** (`luximb_grilla.marcas_segmento`, el objeto congelado del visor, ahora parametrizable): detector ESPEJO-IND en M1 con
  `DETECTORES` = D3_20 (3·ATR(14), ≤ 20 velas: el del visor), D2_20, D4_20, D3_40; amplitud ≥ max(percentil causal 60 u 80, 60
  puntos); zonas: z0 sin condición (control), z1 ≥ 1, **z2 ≥ 3 (visor)**, z3 ≥ 5 zonas en el 25 % inicial, z4 ≥ 3 en el 50 % inicial
  (y ≥ 50 % del total ahí). 4 × 2 × 5 = 40 definiciones; la del visor es `D3_20_a0_z2`.
- **HVN** (rasgo, no ejecución): volumen de la franja más allá de B con alto = la mitad del impulso, en las L = 240 o 1.440 velas M1
  ANTERIORES al inicio del impulso (sin el volumen del propio impulso), dividido por el mayor de las dos franjas vecinas del mismo
  alto (la de adentro del impulso y la siguiente más allá). `hvn_cen`: dónde está el volumen dentro de la franja.
  En USATECH el volumen es el de Dukascopy (cotizaciones, no contratos): es un proxy y se informa por separado.
- **Mecanismo** (sin P&L): máxima extensión más allá de B antes de tocar A (en rangos), si tocó la mitad y si tocó A (240 velas).

## 4. Ejecuciones (fijadas acá; R = resultado / riesgo inicial, neto = − fricción de `edgelab/costos.py` / riesgo)
- **E0** (entrada a mercado en el primer tick de la vela siguiente a la marca, hacia A): stop 0,2 / 0,35 / 0,5 · D, objetivo 0,5 / 1,0 · D
  (D = entrada − A), gestión: ninguna; parcial del 50 % a 0,25 o 0,5 · D; BE a 0,25 o 0,5 · D; parcial + BE a la misma distancia
  (sólo si queda antes del objetivo). 42 ejecuciones.
- **EXT** (esperar la extensión y la vuelta): se arma cuando el precio se extendió e = 0,1 / 0,25 / 0,5 · rango más allá de B; se
  cancela si pasa de c = e + 0,25 o e + 0,5 · rango, si toca A antes o a las 240 velas; entra a mercado cuando vuelve r = 0,05 / 0,1 / 0,2 ·
  rango desde el extremo; stop b = 0,05 / 0,1 · rango más allá del extremo; objetivo A o la mitad del impulso. 72 ejecuciones. El HVN
  entra como filtro en el análisis (hvn ≥ 1,5 / 2 / 3, y «sin HVN» = hvn < 1, en las dos ventanas): misma ejecución con y sin volumen.
- Convenciones: el stop es a mercado y sale al tick que lo cruza (con el salto); objetivo y parcial son límites, en su nivel; tope de
  240 velas desde la entrada, fin de sesión o hueco > 30 min; sin entradas que crucen de sesión.

## 5. Datos y uso (qué se puede mirar y qué no)
- **Desarrollo (ya mirado por el linaje; exploración libre e iteraciones):** NQ 2025-08-05 → 2026-03-31 y 2026-04-01 → 2026-09-25;
  USATECH 2025-08-05 → 2026-03-31 y 2026-04-01 → 2026-09-30. DESC y REP se informan por separado (que algo aparezca en los dos es
  el primer filtro).
- **Confirmación (NUNCA mirado por este linaje): USATECH 2023-01-03 → 2025-07-31.** Se genera recién después de congelar, por
  escrito, ≤ k hipótesis (definición + ejecución + filtro + signo) y se prueba UNA vez: BH q 0,10 sobre las k, estabilidad en 5
  sub-bloques, R neto > 0. Para NQ: forward en papel y, si una hipótesis confirma en USATECH, una apertura del holdout desde la
  sesión del 2026-10-23 (lo anterior está consumido para el linaje), por protocolo.
- Nada del holdout se lee para elegir (los lectores lo rechazan).

## 6. Hipótesis previas (escritas antes de ver ninguna tabla; se informan en desarrollo y se re-prueban en confirmación)
- **H-HVN-1 (mecanismo de Nico):** en la definición del visor, entre los eventos que se extienden ≥ 0,1 · rango más allá de B,
  P(toca A después) es mayor con `hvn_1440` ≥ 2 que con `hvn_1440` < 1.
- **H-HVN-2:** la ejecución EXT con e = 0,1, r = 0,1, b = 0,1, objetivo A, c = 0,6 rinde más R neto con `hvn_1440` ≥ 2 que con < 1.
- **H-ZONAS:** en E0 con stop 0,5·D y objetivo 1,0·D (fricción en R ≈ 0,03), el visor (z2) rinde más R bruto que su control (z0).

## 7. Guardas
- Una celda con fricción mediana > 0,08 R no es elegible para congelar (el stop chico del visor, 0,2·D, suele violarla: se informa).
- Toda tabla de exploración muestra el **nulo de la búsqueda completa** (mejor t por azar con todas las celdas evaluables, inversión
  de signo por sesión): una celda por debajo de su percentil 95 no es una pista.
- No repetir: la regla del visor tal cual dio 0/14 en su mirada del holdout y EXPANSION_ZONAS no confirmó en réplica
  (`FACTORES_CON_VENTAJA.md`); lo nuevo acá es la entrada en la vuelta, el volumen más allá, la gestión y la medición en R.

## 8. Justificación económica y cómo podría refutarse
- **Justificación:** una expansión que nace de desequilibrios deja órdenes sin completar en su origen; si el precio se pasa de B
  hasta una zona donde antes hubo mucho intercambio, ahí hay liquidez para absorber el impulso y darlo vuelta. Esperar esa
  interacción mejora la entrada (stop corto detrás del extremo) frente a entrar al confirmar.
- **Refutación:** P(toca A | extendió) no depende del HVN; la EXT con y sin volumen rinde lo mismo; el visor no supera a su control;
  o nada de lo congelado da R neto > 0 en USATECH 2023–2025.

## 9. Conteo
Exploración: 40 definiciones × (42 E0 + 72 EXT × 9 filtros de volumen) = 27.600 celdas por fuente y período, registradas como
`luximb_hvn/desarrollo` (EF2). La confirmación se registra aparte, con su k, antes de generar la tabla de 2023–2025.
