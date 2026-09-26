# H-LIQPOOL — qué dice la literatura sobre máximos/mínimos repetidos y atracción

Fecha: 2026-09-03 · Búsqueda bibliográfica pedida por Nico antes de construir el
detector. Familia `H-LIQPOOL-ZB` (`H-LIQPOOL-ZB_DISENO_2026-09-03.md`).

## Resumen en cuatro líneas

El mecanismo que Nico intuye **existe y está documentado**, pero la literatura lo
describe como **barrera** (el precio rebota) más que como **imán** (el precio es
atraído). La versión «imán» es vocabulario de trader, no de paper. Y hay un
hallazgo académico que respalda directamente su idea de *picos repetidos*: **más
toques previos ⇒ más probabilidad de rebote**. Además, la literatura implica un
detalle de diseño que cambia dónde hay que dibujar la zona.

---

## 1. El mecanismo tiene base empírica sólida

**Osler (2003, *Journal of Finance*)** analizó el libro de órdenes completo del
Royal Bank of Scotland: 9.655 órdenes, más de USD 55.000 millones, tres pares.
Encontró que las órdenes **stop-loss y take-profit se agrupan en números
redondos**, y que los dos tipos producen efectos **opuestos**:

- **take-profit agrupados ⇒ el precio revierte** en el nivel (barrera);
- **stop-loss agrupados ⇒ el precio acelera** al atravesarlo (cascada).

**Osler (2005, *J. International Money and Finance*)** documenta las cascadas:
los stop-loss generan retroalimentación positiva y las tendencias son
inusualmente rápidas justo en los niveles donde esas órdenes se agrupan. Los
stop-loss eran el **43 % del volumen** de órdenes.

**Osler (2000, FRBNY)** evaluó niveles de soporte/resistencia publicados por seis
firmas: predicen interrupciones de tendencia intradiarias con **más de 60 % de
rebote**, y **más del 70 % de los niveles terminaban en números redondos**.

**Cellier & Bourghelle (Euronext)** y la literatura de *price clustering*
confirman la parte de libro de órdenes: las órdenes límite se agrupan en precios
salientes, y eso genera acumulación de profundidad que actúa como barrera.

**Brunnermeier & Pedersen (2005, *JF*), «Predatory Trading»**: hay incentivo
formal para empujar el precio hacia donde otros tienen que liquidar. Es el
sustento teórico de lo que los traders llaman *stop hunt*.

## 2. El hallazgo que respalda directamente lo de Nico

**«Evidence and Behaviour of Support and Resistance Levels in Financial Time
Series» (arXiv 2101.07410)**, sobre datos intradiarios, con detección algorítmica
de niveles y nulo **AR(1)**:

> los niveles descubiertos revierten tendencias de forma estadísticamente
> significativa, y **el precio que entra en un nivel con mayor número de rebotes
> previos tiene más probabilidad de volver a rebotar**. Además la probabilidad de
> rebote **decae con el tiempo**.

Eso es, casi textualmente, la intuición de *«highs o lows consecutivos»*: más
picos en el mismo nivel ⇒ nivel más fuerte. Y agrega algo que Nico no mencionó y
que hay que parametrizar: **el efecto decae**, así que la zona necesita
expiración.

## 3. La distinción que la hipótesis tiene que resolver

Nico dijo **«atraen al precio»**. La literatura académica mide **rebote**, que es
lo contrario en términos de dirección esperada:

| versión | predicción | respaldo |
|---|---|---|
| **barrera** | el precio llega y **revierte** | académico, fuerte (Osler, arXiv 2101.07410) |
| **imán** | el precio **deriva hacia** el nivel | practicante (ICT), sin test académico directo |
| **imán + barrido + reversión** | el precio va al nivel, lo barre, y **después** revierte | practicante; combina las dos y es lo que describen los *liquidity sweeps* |

La tercera es la que más se parece a lo que se ve en las capturas, y es
**testeable**, pero son **tres hipótesis distintas** y hay que declarar cuál se
mide. Medir «atracción» y encontrar «rebote» —o al revés— y llamarlo confirmación
es el error clásico.

**Y hay antecedente propio**: en este proyecto la versión imán ya murió
(`BIGTRAP2_MAGNET_LINE_CLOSED`, F2.8) porque un control sin zona con la misma
geometría dio lo mismo. La versión barrera **nunca se probó acá**.

## 4. El detalle de diseño que cambia dónde va la zona

Si el mecanismo son **órdenes en reposo**, entonces:

- los **stop-loss de quien está corto** se apoyan **por encima** de los máximos
  iguales, no exactamente en ellos;
- los **stop de quien está largo** van **por debajo** de los mínimos iguales;
- los **take-profit** sí tienden a estar **en** el nivel.

**Consecuencia para el indicador**: la zona no es sólo la línea de los picos. Son
**dos objetos distintos** y conviene marcarlos por separado:

1. el **nivel** (donde están los take-profit → barrera);
2. la **banda de liquidez**, unos ticks **más allá** del nivel (donde están los
   stops → combustible de la cascada).

Un detector que sólo marca la línea mezcla los dos mecanismos, que la literatura
dice que tienen efectos opuestos. Por eso el indicador va a exponer
`LiquidityBandTicks` como parámetro propio.

## 5. Lo que la literatura advierte, y aplica a ZB

- **Los efectos son mixtos y frágiles fuera de muestra.** Hsu, Hsu & Kuan
  (*J. Empirical Finance*) muestran que buena parte de la predictibilidad técnica
  se evapora al corregir *data snooping*, y que se debilita después de que
  aparecen ETFs.
- **En futuros de bonos el clustering de precios es BAJO.** El estudio de LIFFE
  sobre futuros de bonos de gobierno encontró que los contratos alemán y británico
  tienen **poco clustering**, con spreads pegados al tick mínimo. Si ZB se parece
  a eso, el efecto de número redondo —que es el que la literatura documenta— puede
  ser **débil justamente en el instrumento elegido**.
- **ZB tiene tick de 1/32 y sesiones de ~27 precios distintos** (medido en el paso
  1 de esta familia). Eso ya mostró que la repetición de niveles **no supera al
  azar en frecuencia**. Nada en la literatura contradice ese resultado: los papers
  documentan que las órdenes se agrupan, no que los picos repetidos sean raros.

## 6. Qué queda para el indicador

La bibliografía justifica construirlo y dice **cómo**:

| de la literatura | al parámetro |
|---|---|
| más toques ⇒ más fuerte (arXiv 2101.07410) | `MinPivots`, y registrar el conteo |
| el efecto decae con el tiempo | `MaxAgeBars`, y registrar la edad |
| stops **más allá** del nivel, TP **en** el nivel | `LiquidityBandTicks` separado del nivel |
| números redondos concentran órdenes (Osler) | marcar confluencia con nivel redondo |
| barrera vs cascada según qué órdenes dominan | registrar si el precio **rebotó** o **atravesó** |
| clustering bajo en futuros de bonos | no asumir; medir en ZB |

**El indicador no decide cuál de las tres hipótesis es cierta.** Marca el objeto y
exporta todo lo necesario para que después se puedan separar barrera, imán y
barrido — incluidas las zonas que expiraron sin ser tocadas.

## Fuentes

- [Osler, *Currency Orders and Exchange Rate Dynamics* (FRBNY SR125 / J. Finance 2003)](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf)
- [Osler, *Stop-Loss Orders and Price Cascades in Currency Markets* (FRBNY SR150 / JIMF 2005)](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf)
- [Osler, *Support for Resistance: Technical Analysis and Intraday Exchange Rates* (FRBNY Econ. Policy Review 2000)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=888805)
- [*Evidence and Behaviour of Support and Resistance Levels in Financial Time Series* (arXiv 2101.07410)](https://arxiv.org/abs/2101.07410)
- [Cellier & Bourghelle, *Limit Order Clustering and Price Barriers: Evidence from Euronext*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=966454)
- [Brunnermeier & Pedersen, *Predatory Trading* (J. Finance 2005)](https://pages.stern.nyu.edu/~lpederse/papers/predatory_trading.pdf)
- [Lo, Mamaysky & Wang, *Foundations of Technical Analysis* (J. Finance 2000)](https://www.nber.org/system/files/working_papers/w7613/w7613.pdf)
- [Hsu, Hsu & Kuan, *Testing the Predictive Ability of Technical Analysis Without Data Snooping Bias*](https://doi.org/10.2139/ssrn.1087044)
- [*Price clustering and bid-ask spreads in international bond futures*](https://www.sciencedirect.com/science/article/abs/pii/S1042443198000456)
