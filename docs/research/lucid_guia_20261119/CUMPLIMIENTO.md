# LucidFlex: ¿incumplen alguna regla las canastas y la forma de operar? (2026-11-19)

Estado: VIGENTE — revisión de reglas contra las estrategias (descriptivo; no mide edges, no cuenta pruebas). Pedido de Nico: «investigá también
si incumpliríamos alguna regla con estas estrategias y esta manera de operar». North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Cálculos: `RESULTADO.md` y `LUCID_GUIA.json` de esta carpeta.

Fuentes (leídas el 2026-11-19):
- Lucid, centro de ayuda: [Prohibited: Hedging](https://support.lucidtrading.com/en/articles/11404734-prohibited-hedging), LucidFlex
  Payouts / Evaluation / Funded / Drawdown, Maximum Accounts, LucidLive, Other Trading Activities, Allowed trading times y Terms of Use.
- Lucid, [página de planes](https://lucidtrading.com/).
- Terceros: [trader-review.io](https://trader-review.io/reviews/lucid-trading) (precios y reglas al 2026-10-07; recopila denuncias de cierres de
  cuentas desde agosto de 2026) y el hilo de r/LucidProp «Banned by Lucid for "cross-user coordinated trading" while using automation their own
  rules allow» (sólo se pudo leer el título y el extracto: el lector no soporta Reddit).

## Tabla: regla → qué hacen nuestras estrategias → dato
| Regla de Lucid | Qué hacen T, R, Z-banda, SOM y Franklin | Dato medido | Estado |
|---|---|---|---|
| Plano a las 16:45 ET; sin posiciones de un día al otro ni de fin de semana (evaluación y fondeada) | T sale a más tardar a las 16:00 ET (`CashClose1600ET`). R y Z (motor FundedSync) cierran con su salida propia o con el cierre diario del motor, a las **15:44 CT = 16:44 ET** (`DailyFuturesFlattenTimeCentral`). Franklin sale en el minuto 599 de su reloj (intradía). **SOM `sin_finde` (la que usaban las canastas de Lucid hasta hoy) mantiene posiciones de noche**; SOM `eod` cierra a las 15:55 ET | SOM `sin_finde`, NQ: 7,6 % de las operaciones duran más de 24 h. SOM `eod` en 2018–2025.07: +0,038 R/op contra +0,036 de `sin_finde` | **SOM `sin_finde` incumple** (las tablas viejas de Lucid con SOM la usaban). Con `eod` no. El cierre de 16:44 del motor deja un minuto de margen |
| Cobertura prohibida: posiciones opuestas en el mismo contrato o en contratos correlacionados, en la misma cuenta o en cuentas distintas, propias, de otros usuarios o de otras firmas. Primera vez: la cuenta vuelve al saldo del día anterior y no se puede pedir retiro. Si se repite: cuenta quemada y posible expulsión | Todas operan NQ/MNQ. Si **todas las cuentas operan la misma canasta**, todas tienen la misma posición y no hay cobertura entre cuentas. Si distintas cuentas operan reglas distintas, hay días con direcciones opuestas | 2020-01 → 2025-07, mismo día y dirección opuesta: T vs Z-banda 56 de 155 días comunes; T vs R 16 de 178; R vs Z-banda 10 de 13. Las 9 configuraciones de Z-banda nunca se contradicen (0 de 165) | **Repartir reglas entre cuentas incumpliría** en esos días (no se sabe si se solapan en el tiempo: las operaciones guardadas no tienen la hora de salida). Dentro de una sola cuenta, dos estrategias opuestas en NQ se netean, pero la página dice también «no long/short del mismo contrato en la misma cuenta», y el P&L real ya no es el simulado |
| Trading automatizado y copiadores entre cuentas propias: permitidos (el trader responde por los errores) | Todo es automático (NT8 / FundedSync DLL) | — | Cumple |
| HFT prohibido; microscalping: se revisa si más del 50 % de la ganancia viene de operaciones de ≤ 5 s | Entradas en M1; salidas por objetivo, stop móvil u hora | No se puede medir debajo de 1 minuto con M1. Las ganancias vienen de objetivos lejanos (T: 473 de 3.470 operaciones por objetivo) y salidas por hora (15:30 / 16:00); un stop que salta en ≤ 5 s sólo puede dar pérdidas | Cumple (con la salvedad de la resolución) |
| Operar en conjunto con otros usuarios («alone or in concert with others … pool or hedge risk») y operar por cuenta de terceros: prohibido. Lucid decide sola qué cuenta como coordinación | **T es la ruptura de apertura del producto comercial FundedSync**: la misma señal la ejecutan todos los que compraron el producto | Hay denuncias de cierres por «cross-user coordinated trading» desde agosto de 2026, una de ellas con automatización, que Lucid permite (r/LucidProp; trader-review.io: «since August 2026 dozens of traders report bans at payout on this ground … no trade evidence shown»). No hay datos de cuántos usuarios de FundedSync operan en Lucid ni de si los cerraron | **Riesgo no medible**: la regla se puede incumplir sin querer si muchos compradores ejecutan la misma señal a la misma hora. R y Z-banda también salen del mismo producto. Franklin y SOM no |
| Máximo de cuentas: 10 evaluaciones, 5 fondeadas, 10 en total por hogar; 5 LucidLive | La simulación de cartera respeta los tres límites | — | Cumple |
| Paso a live tras 5 retiros: todas las fondeadas elegibles pasan a live, **se cierran todas las cuentas de simulación** y nadie del hogar puede operar en simulación mientras haya una cuenta live | Afecta a cualquier manera de operar muchas cuentas | En la simulación de cartera, el primer 5.º retiro termina la etapa de simulación (ver `RESULTADO.md`) | No es un incumplimiento, pero pone techo a lo que se cobra en simulación |
| Tamaño máximo: 25K 2 minis / 20 micros; 50K 4 / 40; 100K 6 / 60; 150K 10 / 100 | MNQ con tamaño por riesgo; tope por regla = máximo del tamaño / 3 | Con 100 USD de riesgo en la 25K el promedio es ≈ 1 micro por operación | Cumple. trader-review.io dice que en la fondeada Flex el máximo arranca más bajo y crece con la ganancia; la página oficial leída dice «mismo tamaño máximo»: **no verificado** |
| DLL (opcional): incumplimiento blando, frena el día | La simulación corta la pérdida del día en el DLL | — | Cumple (aproximación: en la realidad el día se corta cuando se toca, no al cierre) |
| Inactividad: si la cuenta tiene menos de $1 de P&L neto en 30 días, se borra | T opera el 88 % de los días | — | Cumple |
| Noticias: permitidas en Flex | — | — | Cumple |
| KYC en el primer retiro; contracargos → expulsión de por vida; una cuenta por persona; se pide no compartir red ni dispositivo con otro trader | Operativo, no de estrategia | — | A cuidar al abrir cuentas |

## Resumen en datos
1. **Incumple hoy:** la SOM de las canastas viejas de Lucid (`sin_finde`), por posiciones de noche. Desde hoy las canastas de Lucid usan `SOMEOD`.
2. **Incumpliría con otra forma de operar:** poner reglas distintas en cuentas distintas. Hay días con direcciones opuestas en NQ: T vs Z-banda
   56 de 155, T vs R 16 de 178, R vs Z-banda 10 de 13. Con la misma canasta en todas las cuentas, no.
3. **Riesgo sin medir:** coordinación entre usuarios. T, R y Z vienen de un producto que se vende a muchos usuarios. Las denuncias de
   expulsiones al momento de cobrar existen desde agosto de 2026; la regla la interpreta Lucid.
4. **Margen chico:** el cierre diario del motor FundedSync a las 16:44 ET queda a un minuto del límite de las 16:45.
5. **Sin verificar:** el máximo de contratos de la fondeada Flex (la fuente oficial y la de terceros no coinciden).

Aporte al referente: separa qué de la operativa propuesta viola las reglas de Lucid (SOM nocturna, reglas distintas por cuenta) de lo que es
riesgo de interpretación (coordinación entre usuarios con un producto comercial), antes de arriesgar dinero en cuentas.
