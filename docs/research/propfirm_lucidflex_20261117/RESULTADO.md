# LucidFlex 25K «rinse» sin edge: verificación propia (2026-11-17)

Estado: VIGENTE — cálculo descriptivo, pedido de Nico («quiero que hagas tu propia investigación y cálculos» sobre el reel de @la.tradez
y el documento de verificación que lo acompaña). No es búsqueda de edge: dirección al azar por construcción, sin selección; no cuenta
pruebas. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Código: `tools/lucidflex_rinse.py`;
datos: `RESULTADO.json`.

## Reglas verificadas en la fuente (support.lucidtrading.com, leídas el 2026-11-17)
| Regla | Valor oficial | Página |
|---|---|---|
| Evaluación 25K | objetivo $1.250; pérdida máxima $1.000; **consistencia 40 % (50 % con el adicional pago)**; 2 minis o 20 micros | LucidFlex Evaluation Account; Consistency Percentage |
| Consistencia | mayor día / beneficio de la cuenta ≤ 40 % (o 50 %) **al llegar al objetivo**; si no, se sigue operando | Consistency Percentage |
| Drawdown | EOD: sube con el mejor cierre hasta el piso **$25.100**; se bloquea al superar $26.100 o **al pedir el primer payout** | LucidFlex Drawdown |
| Payout | 5 días con ≥ $100 en el ciclo + neto del ciclo > 0; **50 % del beneficio hasta $1.000**; mínimo $500; 90/10; **máximo 5 payouts** y pasa a live; los días se reinician en cada payout | LucidFlex Payouts |
| Fondeada | sin consistencia, sin buffer | LucidFlex Funded Account |
| Precio | **no figura** en las páginas de Lucid que se pudieron leer; se usa $65 de lista (terceros) y se informa el precio de equilibrio | — |
«50 % del beneficio» admite dos lecturas: **A** beneficio total de la cuenta (la página dice también «50 % of their account balance») y **B**
beneficio del ciclo (la lectura del documento, que exige +$2.000 nuevos por cada $1.000). Se miden las dos.

## Modelo
Recorridos reales del Nasdaq (USATECH M1, RTH 09:30–15:59, 1.700 días de 2020-01 a 2026-09; nada del holdout), dirección al azar cada día,
bracket en USD neto (la fricción canónica MNQ con comisión de Lucid, $3,06 por micro ida y vuelta, se suma al objetivo y se resta del stop),
micros para que el bracket sea ≈ 25 puntos (tope 20 micros), stop antes que objetivo en el mismo minuto, salida 15:59 sin toque.
Evaluación: 3 días de $417 (40 %) o 2 de $625 (50 %), stop = colchón hasta el piso. Fondeada (política de Ari): ir al saldo que da el payout
máximo arriesgando el colchón, después días de +$100 arriesgando $100 hasta juntar 5, pedir el payout. 20.000 cuentas por escenario.

## Resultado (por cuenta comprada)
| Escenario | Pasa la evaluación | Llega a un payout | Cobrado medio (ee) | Si cobra | EV a $65 | EV por día operado |
|---|---|---|---|---|---|---|
| Ari (moneda, sin costos ni topes, teórico) | 38 % | 12,6 % | $227 | $1.800 | **+$157** | — |
| **40 %, lectura A, payout de $1.000** | 25,5 % | 6,7 % | $103 (3) | $1.548 | **+$38** | +$8,6 |
| 40 %, lectura B (la del documento) | 25,6 % | 6,7 % | $93 (3) | $1.388 | +$28 | +$6,5 |
| 50 % (con el adicional; su precio no restado) | 32,1 % | 8,7 % | $134 (4) | $1.539 | +$69 | +$15,8 |
| 40 %, A, payout mínimo de $500 | 25,3 % | 7,9 % | $62 (2) | $790 | −$3 | −$0,6 |
| 40 %, A, sin costos de operación | 30,4 % | 8,9 % | $153 (4) | $1.720 | +$88 | +$17,5 |
Cuentas compradas por cada una que llega a fondeada: 4,05 (40 %) / 3,16 (50 %); cobrado medio por fondeada ≈ $410–420; la fondeada dura ≈ 6–7
días operados. Ganar plata con una cuenta: 6,7–8,7 % de las veces; la cuenta típica pierde el precio.

## Lectura
1. **La aritmética de Ari es correcta en su modelo, y el signo también**: con las reglas reales y costos reales el EV sin edge sigue
   positivo, pero ≈ 4 veces menor (+$28 a +$69 por cuenta, no +$157). Viene de la asimetría de la cuenta (pérdida acotada al precio,
   payouts sin tope de pérdida para el trader), no de los precios.
2. **El documento de verificación se equivoca en el signo**: cobra $200–$350 de costos a TODAS las cuentas, como si cada una llegara a 14
   operaciones; en el modelo la cuenta media dura 4,5 días y los costos le restan ≈ $50, no $200–350. También da por segura la lectura B
   del tope de payout, que la propia página contradice («50 % of their account balance»); con B el EV baja $10, no cambia de signo.
   Acierta en la consistencia (40 % sin adicional), el bloqueo del piso, los 5 payouts y el límite de cuentas.
3. **$10.000 por mes no**: el límite es de 5 fondeadas activas, que duran ≈ 6,5 días y dejan ≈ $415 cada una. Con los 5 lugares siempre
   llenos son ≈ 16 fondeadas por mes: ≈ $6.700 brutos menos ≈ 65 evaluaciones compradas (≈ $4.200) → **del orden de $2.500 por mes de
   esperanza**, con una varianza enorme.
4. **Riesgos que el número no incluye**:
   - Para tener 65 evaluaciones por mes hay que operar muchas a la vez, y Lucid prohíbe la cobertura entre cuentas: todas van en la
     misma dirección, así que pierden juntas (no hay ley de los grandes números dentro del mes).
   - Las condiciones de Lucid permiten quitar ganancias por operar «evitando los objetivos» o de mala fe; operar a moneda con brackets
     calibrados a las reglas es exactamente eso. Es un riesgo de perderlo todo que no se puede modelar.
   - El paso a live después de 5 payouts no se valoró (podría sumar).
5. **Para EdgeLab**: confirma que en una prop la geometría de las reglas pesa tanto como la ventaja. Una regla con edge real (la cartera v2
   o la B) se apalanca en esa misma asimetría; el siguiente paso útil es correr la cartera con estas reglas de Lucid en el simulador de
   prop (`cartera_20261116/PROP.json` usa otra firma) en vez de operar a moneda.

## Justificación económica / cómo podría refutarse
La cuenta limita la pérdida al precio y paga hasta 5 retiros: una opción con valor positivo aun sin edge si las reglas lo permiten. Se
refuta con reglas distintas a las leídas (precio, tope de payout), con costos de ejecución mayores a los canónicos, o si Lucid aplica la
cláusula de mala fe.

## Las 4 configuraciones de LucidFlex 25K (Nico mandó capturas de la página; reglas en «LucidFlex Customization», 2026-11-17)
El límite diario de $600 (DLL) es un corte **blando** (bloquea hasta la sesión siguiente, no pierde la cuenta) y vale en evaluación y
fondeada; trae los payouts a demanda (retiro intradía de la ganancia de la sesión, pausa hasta el día siguiente). Sin DLL, payouts al
cierre. Precio con cupón: DLL+40 % $45,50; DLL+50 % $55,30; sin DLL+40 % $60,20; sin DLL+50 % $70,00 (lista $65 base; reset = precio).
Modelo: con DLL, el stop del día es el menor entre el colchón y $600. Lectura A del tope de payout; 20.000 cuentas cada una (ee ≈ $3,3).

| Configuración | Precio | Pasa | Cobra | EV por cuenta | EV por día operado | Neto por fondeada | ≈ USD/mes con 5 fondeadas (orden de magnitud) | Evaluaciones/mes |
|---|---|---|---|---|---|---|---|---|
| DLL $600 + 40 % | $45,50 | 26 % | 6,8 % | +$60 | +$8,6 | $228 | ≈ 3.300 | ≈ 56 |
| **DLL $600 + 50 %** | $55,30 | 32 % | 8,4 % | **+$74** | +$11,9 | $232 | **≈ 3.800** | ≈ 51 |
| sin DLL + 40 % | $60,20 | 26 % | 6,7 % | +$43 | +$9,6 | $169 | ≈ 2.700 | ≈ 64 |
| sin DLL + 50 % | $70,00 | 32 % | 8,7 % | +$64 | **+$14,7** | $199 | ≈ 3.500 | ≈ 55 |
Lectura B (tope sobre el beneficio del ciclo): −$10 a −$15 por cuenta, mismo orden. Las diferencias entre configuraciones son de 1–4
errores estándar: **el 50 % vale lo que cuesta** (sube el pase de 26 a 32 % por $9,80) y el **DLL no estorba** a esta política (su stop ya
era el colchón) y abarata la cuenta. Lo mensual es una cota gruesa (días de fondeada aproximados), siempre con cuentas que pierden juntas y el
riesgo de la cláusula de mala fe.

## Las canastas en LucidFlex 25K (`tools/lucid_canastas.py`, `CANASTAS_LUCID.json`; pedido de Nico, 2026-11-17)
Series diarias en USD de desarrollo (v2/v3: DESC+REP 2025-08 → 2026-09 con micros enteros a 100/200/300 USD por operación; B: T+Z+R a 1–2
MNQ, 2020 → 2026-09, sin el stop de catástrofe de Z/R), bootstrap por bloques de 5 sesiones recentrado a la media de desarrollo, a la
**contraída** (× factor de selección de la batería; 0,5 en B) o a cero. Las 4 configuraciones × retirar $1.000 o el mínimo; 20.000 cuentas.

| Canasta (DLL $600 + 50 %, $55,30) | USD/sesión (t) | Pasa | Cobra | EV desarrollo | **EV contraída** | EV sin edge | Días por cuenta | EV contraída por mes de cuenta |
|---|---|---|---|---|---|---|---|---|
| v2 a 100 USD | +49 (4,1) | 73 % | 52 % | +3.299 | **+1.912** | +55 | 114 | +352 |
| v2 a 200 USD | +98 (4,3) | 56 % | 33 % | +2.305 | **+1.127** | +36 | 51 | +464 |
| v2 a 300 USD | +150 (4,3) | 48 % | 24 % | +1.774 | **+832** | +34 | 34 | +507 |
| v3 a 200 USD | +110 (3,9) | 46 % | 22 % | +1.466 | **+679** | +70 | 30 | +476 |
| v3 a 300 USD | +167 (3,9) | 43 % | 20 % | +1.280 | **+676** | +100 | 25 | +579 |
| B a 1 MNQ | +47 (8,2) | 52 % | 25 % | +2.104 | **+654** | +69 | 58 | +239 |
| B a 2 MNQ | +94 (8,2) | 41 % | 17 % | +1.276 | **+442** | +72 | 25 | +368 |
| v2 200 + B 1 MNQ | +175 (5,7) | 46 % | 22 % | +2.401 | **+708** | +53 | 29 | +519 |
(Pasa/cobra con la media contraída.) Lectura:
1. **Con la media contraída, cualquier canasta tiene un EV por cuenta 10 a 35 veces el de operar a moneda** (+$440 a +$1.900 contra +$35 a
   +$100): la ventaja se monta sobre la misma asimetría de la cuenta.
2. **Tamaño: chico rinde más por cuenta, grande más por mes.** A 100 USD por operación se cobra en el 52 % de las cuentas pero tarda ≈ 5
   meses; a 300 USD, en un mes y medio con la mitad de probabilidad. Con 5 fondeadas como límite, conviene el tamaño medio-alto
   (200–300 USD) y varias cuentas en paralelo con la misma canasta (sin cobertura entre cuentas).
3. **Configuración**: DLL $600 + 50 % es la mejor o empata en todas (más barata, el corte blando casi no cuesta); retirar el máximo
   ($1.000) gana a retirar el mínimo.
4. **La B sola rinde menos por mes** que la v2/v3 aunque su t es el más alto (pocas operaciones por día, desvío alto sin el stop de
   catástrofe); **sumada a la v2** no mejora a la v2 sola a 300 USD en EV por mes (correlación positiva en el tramo común).
5. **Límites del cálculo**: el DLL se aproxima cortando la pérdida del día en −$600 (no ve el recorrido intradía); el escalado de contratos
   de la fondeada 25K y la política de algoritmos de Lucid («condicional» en el catálogo, no verificado) pueden limitar el tamaño; las medias
   de desarrollo vienen de reglas elegidas (por eso manda la contraída) y el forward todavía no confirmó ninguna canasta.

> **Corrección del 2026-11-17 (paso 2 de urgencia_vs_evidencia):** la «media contraída» (James-Stein, ≈ mitad) resultó optimista: lo
> elegido por el embudo no conservó nada en su réplica. Hasta que el forward acumule evidencia, la expectativa por cuenta está entre la
> columna «sin edge» y la «contraída»; el paso 3 la recalcula con la evidencia forward.

### La cartera B (T+Z+R) por componentes (Nico: «¿probaste T+Z+R?»; DLL $600 + 50 %, 1 MNQ por regla, 2020 → 2026-09)
| Combinación | USD/sesión (t) | EV desarrollo | **EV contraída** | Cobra (contraída) | Días por cuenta | EV contraída por mes de cuenta |
|---|---|---|---|---|---|---|
| **T+Z+R** | +47 (8,2) | +2.104 | **+654** | 25 % | 58 | **+239** |
| T+Z+R desde 2025-08 (mismo tramo que la v2) | +77 (4,6) | +2.537 | **+746** | 26 % | 43 | **+363** |
| T sola | +27 (6,3) | +1.642 | +516 | 22 % | 74 | +147 |
| T+R | +41 (7,2) | +1.825 | +566 | 22 % | 58 | +204 |
| T+Z | +34 (7,4) | +2.067 | +638 | 25 % | 74 | +182 |
| Z+R | +20 (6,4) | +2.195 | +680 | 34 % | 189 | +76 |
| R sola | +13 (5,0) | +1.225 | +365 | 27 % | 219 | +35 |
| Z sola | +6 (4,0) | +210 | +5 | 6 % | 279 | +0 |
T sostiene la canasta; Z sola opera tan poco (≈ 2 por mes) que en la cuenta no llega a cobrar; las tres juntas son la mejor combinación
por mes. Z y R sin su stop de catástrofe en estas series.
