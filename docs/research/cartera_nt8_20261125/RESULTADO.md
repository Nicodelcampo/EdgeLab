# Carteras NT8: estrategia única, multiactivo y gestión del riesgo en cuentas fondeadas

Estado: RESULTADO (pre-registro `PREREGISTRO_MULTIACTIVO_Y_GESTION.md`; Parte A 13 pruebas contadas en
`CARTERA_MULTIACTIVO_20261125`; Parte B descriptiva). Configuraciones PROPUESTAS: operar con dinero real lo decide Nico.  
Fecha: 2026-11-25  
Diagnóstico de grilla: Parte B = 672 políticas × 3 medias × 3 muestras con criterio declarado y validación fuera de tiempo
(correlación de rangos H1–H2 0,91–0,98 en cuentas; 0,56 en rescate); sin búsqueda de ventaja.

## 1. Una sola estrategia NT8: `EdgeLabCartera`
- **Qué es**: una estrategia NT8 que corre varias estrategias en uno o más instrumentos (`EdgeLabCartera.cs`, motor común
  `EdgeLabFundedSyncCore.cs`, motores nuevos `EdgeLabCarteraEngines.cs` para RQ5, Franklin, ES5N y C2_VZ/C2_EVRP, ejecutor
  `EdgeLabCarteraBook.cs`). Presets: **Intradía** (MNQ: T, R, Z, V, RQ5, Franklin; MES: RQ5, ES5N), **Interdía** (MNQ: SOM
  sin_finde, C2_VZ; MES: C2_VZ), **Rescate25K** (MNQ: T). Composición editable (`MNQ:T=1,R=1;MES:RQ5=1`).
- **Cambio de ejecución (problema del adaptador anterior, encontrado al revisarlo)**: el adaptador histórico de los módulos
  FundedSync ajustaba la posición neta al cierre de cada vela: **la entrada salía una vela después** de la que registraba y
  **los stops eran virtuales** (se ejecutaban al cierre de la vela siguiente, sin orden en el broker). El CSV mostraba los precios
  virtuales, no los fills. `EdgeLabCartera` le da a cada estrategia sus órdenes reales (entrada al cierre de la vela de la señal,
  stop y objetivo OCO en el broker, salida a mercado sólo después de confirmar que no queda protección viva) y la cuenta queda con
  la suma. En una corrida en vivo el histórico se simula sin órdenes y arranca plano; en el Strategy Analyzer opera con órdenes
  reales desde la primera vela. Guardas de cuenta (pérdida diaria, pérdida total, objetivo diario), plano 16:40 ET y 20 min antes
  del fin de sesión (también en cierres tempranos de feriado), veto de noticias, CSV de operaciones por libro y registro de
  ejecución en tiempo real (latencia y deslizamiento en ticks y USD por orden).
- **Paridad fuera de NT8** (`tools/nt8_cartera_paridad.py`: compila los mismos .cs con un broker simulado de reglas del backtest
  de NT8 y compara con las corridas individuales, 2019-07 → 2026-09):

| Estrategia | Emparejadas | Misma entrada | Nota |
|---|---|---|---|
| T, R, Z, V (NQ) | 98,8–100 % | 100 % | salidas: 77–97 % iguales en modo broker (stop redondeado a tick y real, no virtual); ΔP&L ≤ 0,1 pts/op |
| RQ5 NQ / ES | 99,7 % | 100 % | salida igual 98,3–98,8 % |
| Franklin NQ, ES5N ES, C2_VZ NQ/ES | 98,3–99,6 % | 2–10 % | la diferencia es exactamente 1 tick: esas corridas NT8 tenían `Slippage = 1` |
| SOM sin_finde NQ | 99,9 % | 100 % | salida igual 99,2 % (virtual) |

## 2. Técnicas investigadas (fuentes) y qué dijo la medición
| Técnica | Qué dice la literatura | Qué dio acá |
|---|---|---|
| Apostar chico o grande para llegar a un objetivo antes de un piso (Dubins y Savage; Sudderth, *How to control a process to a goal*) | Juego favorable: apostar chico ("timid") maximiza la probabilidad; desfavorable o neutro: apostar grande ("bold") | En la 25K y la 50K "gana" apostar grande sólo cuando se mira el cierre (señal de ventaja insuficiente frente al drawdown); con el mínimo intradía, más tamaño siempre baja la probabilidad en la 150K (k1 0,169 → k4 0,018) |
| Tamaño contra el colchón del drawdown, no contra el saldo (guías de cuentas fondeadas: satotrades, propfirmshub, NinjaTrader prop) | Riesgo por operación ≈ colchón / 8–10 | Confirmado: la cartera de 8 a 1 micro (sd diaria ≈ $670) sólo es razonable donde el colchón es ≥ ~7 sd diarias (150K: $4.500) |
| Control de drawdown (Grossman y Zhou 1993; CPPI; Bayes-GZ, SSRN 6942459) | Exposición proporcional a la distancia al piso | Escalar según el colchón (dyn1) y el escalón con colchón alto (dyn3) **empeoran** (0,112 → 0,042 / 0,039 de media); el escalón al fijarse el piso (dyn2) ≈ fijo |
| Gestión por volatilidad (Moreira y Muir 2017) | Sube el Sharpe dentro de muestra | Fuera de muestra suele fallar (Cederburg et al. 2020, 103 estrategias); acá, con micros enteros, el peso mínimo de 1 iguala a todas |
| 1/N vs inverso-volatilidad vs HRP (DeMiguel et al. 2009; López de Prado 2016; estudio Monte Carlo HRP/ERC, SSRN 7036740) | 1/N difícil de batir; HRP baja la varianza fuera de muestra | A 1 micro las tres son iguales; con más contratos HRP > inverso-vol > 1/N en promedio, pero ningún esquema con más contratos supera a 1/N con 1 micro |
| Freno diario de pérdida | Práctica común | **Sesgo encontrado y corregido**: simulado con el cierre del día parece excelente (rescate 66 %); con el mínimo intradía, corta los días que se recuperan y no ayuda (rescate 4 %), como F-FRENO-DIARIO-NO |

## 3. Multiactivo: pros y contras (Parte A, 13 series nuevas, micros con costos canónicos; M2K con spread estimado)
- **Contras medidos**: (1) YM y RTY se mueven con la canasta (correlación diaria 0,24–0,39): no diversifican; (2) en micros, las
  reglas de índices no tienen ventaja propia fuera de NQ/ES (R/op entre −0,11 y +0,03; RQ5 YM −0,036, RTY −0,005); (3) el oro no se
  correlaciona (−0,04 a 0,09) pero tampoco gana (FR −0,068, ES5N −0,063, RQ5 −0,007). **Sumar cualquiera de las 13 a la cartera de
  la 150K baja la probabilidad de cobro** (0,30 → 0,26–0,29).
- **Pro**: un activo de otra clase sí baja la volatilidad conjunta (oro, correlación ≈ 0) — sirve **cuando tiene ventaja propia**.
  Hoy no hay ninguna regla con evidencia en oro, petróleo, bonos o divisas (CL, ZN, 6E sin historia M1 de NT8: sólo ticks desde 2025).
- **El único estabilizador real es C2_VZ** (otra fuente: volatilidad implícita, no la apertura): correlación ≈ 0 con la canasta,
  gana en sus meses malos, y sumado a la intradía baja el peor semestre de −$5.992 a −$1.571 y sube el Sharpe de 1,48 a 1,70 (2026:
  $1.366/mes vs $613). **Mantiene de noche**: no entra en Lucid.
- Costos usados (Internet, 2026-11-25): Lucid cobra 0,50 USD por lado en MES, MNQ, M2K, MYM y MCL; 0,80 en MGC; 2,40 en 6E
  (support.lucidtrading.com, «Approved Products and Commissions»). Spread de M2K estimado = el medido de RTY (1,5 ticks).

## 4. Gestión en Lucid (Parte B, Kaggle `edgelab-cartera-gestion-20261125`, 20.000 trayectorias por configuración)
Iteración 1 (sólo cierres) publicada en `RESULTADOS_GESTION_iter1_solo_cierre.json`: **sesgada** (frenos gratis, piso sólo al
cierre). Iteración 2 (la que cuenta): mínimo intradía por estrategia (vela a vela en el arnés) y piso/frenos dentro del día; la suma
de mínimos es conservadora, la de cierres optimista: la verdad está entre las dos.

| Cuenta (cartera intradía, 1 micro c/u, 1/N, sin dinámico ni freno) | P(cobrar más que el precio): contraída · desarrollo · cero | Valor esperado por intento (contraída) | Pasa la evaluación | Días |
|---|---|---|---|---|
| 150K | **0,25** (sólo cierres 0,30) · 0,50 · 0,09 | +$279 | 35 % | 94 |
| 50K | 0,055 (0,14) · 0,13 · 0,02 | +$7 | 17 % | 23 |
| 25K | 0,009 (0,11) · 0,03 · 0,003 | −$33 | 7 % | 10 |
- En la 150K, la mejor política es prácticamente la simple (tope diario en evaluación: 0,255, dentro del ruido). Ranking estable
  entre 2019–2023 y 2024–2026 (Spearman 0,98). Con la cartera interdía (sumando C2_VZ) 0,257: mejora chica en estas reglas.
- **Rescate de la 25K** (saldo 24.270, piso 24.000 sin verificar, objetivo 26.250): lo más robusto es **T sola en 1 MNQ**: pasa
  13,6 % (contraída; 27 % con la media de desarrollo, 5,7 % sin ventaja), igual en las dos mitades (13,8 % / 13,6 %), ≈ 22 días.
  Su pérdida diaria máxima es ≈ $204 (stop tope 100 pts) < colchón. La cartera completa: 1 %. Elegir mirando sólo 2019–2023
  (V con freno 120) se desploma a 3 % en 2024–2026: ejemplo concreto de sobreajuste de la gestión.

## 5. Qué cargar en NT8
| Cuenta | Gráfico | Estrategia | Preset | Notas |
|---|---|---|---|---|
| LucidFlex 150K (propuesta) | MNQ 1 min | EdgeLabCartera | Intradía | agrega MES solo (mismo vencimiento). Sin freno diario. |
| 25K en rescate | MNQ 1 min | EdgeLabCartera | Rescate25K | 1 MNQ en T; registro de ejecución activo: sirve también para auditar fills, latencia y deslizamiento |
| Cuenta que permita noches (si se abre) | MNQ 1 min | EdgeLabCartera | Interdía | requiere `Documents\NinjaTrader 8\EdgeLab\datos\cboe_vol_diario.csv` al día (`tools/exportar_vix_nt8.py`) |
Antes del dinero real: correr cada preset en el Strategy Analyzer (cuenta Backtest, 2019-07 → 2026-09) y en Sim101 un par de días;
comparar el CSV `Documents\NinjaTrader 8\EdgeLab\cartera\<preset>_<raiz>.csv` con el arnés.

## 6. Límites
- El mínimo intradía de la cartera es la suma de mínimos por estrategia (conservador); las operaciones de varios días se imputan
  al cierre. El arnés no prueba la parte NT8 del host (acciones de orden unmanaged, fin de sesión con SessionIterator, guardas):
  eso se verifica en el Strategy Analyzer y en Sim.
- Ninguna estrategia de la cartera está confirmada (0 edges promovidos); las probabilidades usan la media contraída a la mitad.

## 7. Estado en NT8 (2026-11-26) — leer antes de usar `EdgeLabCartera`
- **No usar en cuenta real todavía.** Primera corrida de Nico en el Strategy Analyzer (Intradía, 2025-01 → 2026-11): Franklin, R y ES5N
  operan como en el arnés, pero **RQ5 0 operaciones (arnés 282), T 3 (379), Z 7 (46), V 221 (390)**. Patrón: fallan las que tienen stop
  y objetivo OCO o salen por señal propia → una salida queda esperando la confirmación de cancelación de su stop/objetivo y la estrategia
  queda "abierta" para siempre. El arnés (que no reproduce la semántica OCO/eventos de NT8) no lo muestra.
- Corregido antes (commit 45bc8c9c): bucle infinito de órdenes (OCO reusado + reenvío dentro del evento de rechazo) que llevaba a NT8 a
  13 GB; referencias viejas por rechazo/fill sincrónico; arnés con modo `nt8` (rechazos sincrónicos) y control posición broker = libro.
- Agregado (2026-11-26): **vigilante** en `CarteraBook.Vigilar` (salida o entrada a mercado sin resolver en 2 velas → se destraba y se
  imprime `DESTRABE …`) y control `DESCUADRE` (posición real de NT8 ≠ suma del libro) en el host; la línea mensual `EdgeLabCartera DIAG`
  ahora incluye destrabes y descuadres.
- **Siguiente paso**: Nico corre Intradía 2025-07 → 2026-09 con el Output abierto; las líneas `DESTRABE` dicen qué orden no confirma
  (stop/objetivo) y en qué estrategia; con eso se corrige la causa (probablemente la cancelación automática del OCO en NT8 o el orden de
  sus eventos) y se compara el CSV `Documents\NinjaTrader 8\EdgeLab\cartera\Intradia_*.csv` con el arnés (`tools/nt8_cartera_paridad.py`).
- La investigación (secciones 1–6) no depende de esto: usa el motor en el arnés, verificado contra las corridas NT8 individuales.

## 8. Causa raíz de «RQ5, T y Z no operan en NT8» (2026-11-26) — corregida
- **Causa:** al pedir una salida (fin del día, señal propia, fin de sesión), el libro cancelaba el stop y el objetivo del grupo OCO y esperaba
  el aviso de cancelación de **los dos** antes de mandar la salida a mercado. En NT8, cancelar una pata de un OCO cancela también la otra,
  y ese aviso de la hermana puede no llegarle al libro. El objetivo quedaba «vivo» en el libro y la estrategia, abierta para siempre:
  no volvía a operar. Por eso fallaban justo las que tienen objetivo (RQ5, T, Z) y no Franklin, R ni ES5N (sólo stop).
- **Reproducción:** el arnés ahora emula la cascada OCO de NT8 (`HARNESS_OCO=2`, cascada sin aviso para la hermana). Sin vigilante y con el
  libro viejo, 2024-09 → 2025-06: NQ RQ5 0, ES RQ5 0, T 2, Z 0; Franklin 23, R 6 y ES5N 3 intactas. Es la misma firma de la corrida de Nico
  (RQ5 0, T 3, Z 7).
- **Corrección** (`EdgeLabCarteraBook.cs`, `EdgeLabCartera.cs`):
  - el gateway expone `Status(tag)`, el estado real de la orden en NT8 (`Order.OrderState`);
  - al salir (y al rearmar un OCO muerto), el libro suelta las órdenes que el broker ya canceló o rechazó, sin esperar su aviso;
  - una orden llenada no se suelta: su aviso de fill cierra la posición, así no hay sobrellenado.
- **Verificación en el arnés:**
  - con cascada OCO 0, 1 y 2, con y sin vigilante, las operaciones son iguales a la simulación virtual (NQ RQ5 128, ES RQ5 131, T 76,
    Z 17, Franklin 23, R 6, ES5N 3);
  - 0 destrabes y 0 descuadres;
  - el precio de salida difiere ≤ 0,16 pts (redondeo a tick).
- **Segunda causa, sólo para V (no es un error de órdenes):** `VaultBreakEngine` necesita 252 sesiones RTH para su ATR diario. En una
  corrida del Strategy Analyzer que empieza en 2025-01 sin historia previa, V no opera su primer año (221 contra 390). Para comparar,
  cargar datos desde 2024-01 o antes.
- **Sigue pendiente:** volver a correr en el Strategy Analyzer de NT8 (Intradía, con datos desde 2024) y comparar contra el arnés. El arnés no
  prueba la semántica exacta de NT8; la corrección se basa en el estado real de la orden y debería cubrir tanto el aviso que no llega como
  el que llega tarde.
