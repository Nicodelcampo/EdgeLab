# Manifiesto M8 (PROPUESTO, sin OK) — franjas arriba/abajo del impulso: desbalance de zonas OG/VI (+ ML acotado)

Estado: PROPUESTO. **No se corre sin OK de Nico.** Fecha 2026-10-20.
Referente: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Origen: pedido de Nico (ML por franjas sobre la disposicion de OG/VI arriba y abajo de la expansion; logica base: cantidad
arriba vs abajo con varias vidas y su desbalance). Antecedente: el sistema de 3 franjas de Gemini (K32/K37, corredor EMA y
corredor x HFT) **no replico** (neto -2,0 a -2,5 ticks/trade en abr-sep); de ahi se toma la estructura de franjas, no el
modelo. Leccion de M7b: todo efecto de zonas se mide **contra una base de contexto** (volatilidad previa, hora, tamano).

## Poblacion (amplia, sin exigir zonas en el 25 % inicial)
Todos los impulsos ESPEJO-IND en M1 (detector sin cambios), marcados en tiempo real en la primera vela en curso con
amplitud >= max(p50 causal, 1,3 x mediana causal) — `luximb_impulsos.py --modo inicio --p-rango 50 --min-ini 0
--share-ini 0 --rango-min-rel 1.3`. Sin requisito de zonas: la disposicion de zonas pasa a ser **variable**, no filtro.
Event-space declarado: activacion / cumplimiento en curso (elegido) / extremo final (no causal) / confirmacion por retroceso.
- **NQ descubrimiento** (09-25..06-26/31-mar) = muestra de desarrollo (conteo target-free en el anexo).
- **ES descubrimiento** (mismos tramos, K-bars no aplican: impulsos M1) = **prueba externa** congelada; replicaciones
  (abr-sep) de NQ y ES no se tocan. Holdout no se toca.

## Franjas (causales, en la vela de marca; A origen, X extremo, R = |X - A|)
- **Superior**: (X, X + R] si sube / la franja equivalente del otro lado si baja — se definen como **"adelante"** (en la
  direccion del impulso, mas alla de X) y **"atras"** (mas alla de A, en contra). Tambien la franja **interior** [A, X].
- Zonas OG/VI vivas en la vela de marca con **4 vidas**: 100, 200, 500 y 1000 velas M1 (cada vida es un juego de conteos).
- Por franja y vida: n OG, n VI, n total, n alcistas, n bajistas, distancia al borde de la zona mas cercana (en R).
- **Desbalance** por vida: D_v = (n_adelante - n_atras) / (n_adelante + n_atras + 1).

## Desenlaces (los ya usados en la familia; no se agregan nuevos)
- Y1: carrera desde la marca: vuelta del 50 % del impulso antes de extender +25 % (binaria).
- Y2: recorrido 60 min / vol_pre (no direccional, relativo — evita la confusion de M7b).

## Hipotesis
**Parte A — logica simple de Nico (principal, 4 pruebas, Holm):**
- A1 (por vida 100/200/500/1000): P(Y1) en el quintil de D_v mas "adelante" menos P(Y1) en el quintil mas "atras",
  **ajustado por la base de contexto** (estratos de vol_pre x franja horaria x terciles de R). Bilateral (no hay direccion
  previa fundada: zonas adelante podrian frenar la extension o atraerla). Bootstrap por dia, 10.000.
**Parte B — ML acotado (secundaria, 1 prueba):**
- Modelo de gradient boosting chico (profundidad <= 3, <= 200 arboles, sin redes, sin seleccion de hiperparametros por
  desenlace: valores fijos aca) con ~30 variables de franjas + base de contexto, vs el mismo modelo **solo con contexto**
  (vol_pre, ATR, hora, R, velas 25t, direccion).
- Validacion: CV por bloques de dias con purga (5 bloques) en NQ; metrica = mejora de log-loss del modelo con franjas sobre
  el de contexto, IC por bootstrap de dias.
- B1: la mejora es > 0 en NQ (CV) **y** el modelo congelado mejora sobre contexto en ES (prueba externa).
**Parte C — economica (solo si A o B pasan):** P&L neto del decil extremo (fade o seguir, segun el signo hallado) con
costos propios de cada instrumento; descriptivo, no inferencial, hasta replicacion.

Numero efectivo de hipotesis inferenciales: 5 (A1 x 4 vidas + B1). Las vidas estan correlacionadas (Holm es conservador).

## Justificacion economica
Si las zonas sin negociar actuan como liquidez pendiente, un impulso con muchas zonas por delante y pocas por detras deberia
comportarse distinto (frenar/atraer) que uno con el desbalance opuesto, a igual contexto de volatilidad.

## Como podria refutarse
A1 sin diferencia en ninguna vida (IC incluye 0) con MDE publicado, y B1 sin mejora sobre contexto en NQ o en ES.
Si solo pasa en NQ y no en ES: no replicado, no se promueve.

## Riesgos
1. Sobreajuste del ML: se fija todo de antemano; la prueba que cuenta es ES externo.
2. Confusion con volatilidad: cubierta por la base de contexto y por Y2 relativo.
3. Paridad LUX-IMB/barras en ES no medida contra NT8.
4. Impulsos consecutivos solapados y clustering por dia (bootstrap por dia).
5. La familia ya acumulo 7 mediciones nulas: la probabilidad previa de exito es baja; el costo es bajo y el diseno es estricto.

## Datos faltantes
Ninguno. ES necesita construir impulsos M1 y zonas por contrato (numpy, como M7).

## Anexo — conteo target-free de la poblacion (NQ descubrimiento)
Impulsos que cumplen la amplitud (sin mirar desenlaces), piso 1,3 x mediana: NQ 09-25 = 774, 12-25 = 2.238, 03-26 = 2.214,
06-26 (2 semanas) ~ 300 -> **~5.500 en NQ** (vs 150-330 de las definiciones con zonas agrupadas). Con piso 1,0: ~7.700.
Quintiles de D_v -> ~1.100 eventos por quintil: MDE de A1 del orden de 5-6 pp. ES externo: escala similar (a contar).

## OK y enmienda pre-desenlace (2026-10-20)
- OK de Nico ("si, medi M8"). PRE-REGISTRADO.
- Empates (visto solo en D, target-free, NQ): con vida 100 el 55 % de los impulsos tiene D = 0 (p80 = 0). Los grupos extremos
  de A1 se definen: **adelante** = D >= max(p80, >0); **atras** = D <= min(p20, <0); cortes p20/p80 de NQ aplicados tambien a ES.
- Franjas por punto medio de la zona: adelante (X, X+R], interior [A, X], atras [A-R, A). Vida = velas M1 desde la creacion.
- Y1 = "Tg" (vuelta del 50 % antes de +25 %); "tiempo" cuenta como no-Tg.
- ES externo: impulsos con la misma regla (umbrales causales propios de ES).
