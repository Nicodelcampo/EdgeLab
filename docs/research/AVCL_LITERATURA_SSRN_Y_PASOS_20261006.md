# AVCL — qué dice el corpus SSRN y qué análisis complementan el hallazgo — 2026-10-06

Corpus `E:\$ACerebroSSRN`: 401 papers. Búsqueda **por palabras clave** sobre 24.340 pasajes, porque la búsqueda
semántica requiere `sentence_transformers` y no se instala, por la regla de no sumar dependencias pesadas.
Autoridad: todo lo de abajo es `LITERATURE_CLAIM_UNVERIFIED`; orienta qué medir, no prueba nada.

Hallazgo de partida: la creación de una zona aVolClusterPOI anticipa unas 10 barras de rango más amplio (MNQ AT
+0,081, unos 3 ticks; replica MYM) y después compresión. Ver `AVCL_VOL1_RESULTADOS_MNQ_20261006.md`.

## Qué dice la literatura
1. **El volumen anticipa volatilidad, y el efecto es transitorio.**
   - Darrat et al. (2003), citado en [206] *Lead-Lag Relationships in Market Microstructure*: el volumen lidera la
     volatilidad.
   - [96] Muravyev y Picard, *Does Trade Clustering Reduce Trading Costs?*: los picos de volumen traen más volatilidad
     **sin que cambie el spread ni la lambda de Kyle**.
   - Para nosotros: la expansión es esperable, y el costo de ejecución no tendría por qué empeorar justo ahí. Esto
     último es verificable.
2. **Autoexcitación (Hawkes): ráfaga y luego decaimiento.**
   - [209] Sharma, [85] Bilodeau, [207/208] Jain et al., [237] Bergenstein: los eventos de flujo se agrupan y se
     autoexcitan, con intensidad que decae exponencialmente.
   - Encaja **exactamente** con nuestra forma: expansión a H10 y compresión a H50/H200. La hipótesis rival fuerte es
     que la zona **no agrega nada** al Hawkes del propio volumen. Es el control "volumen alto sin zona" que ya estaba
     pendiente, pero con una forma concreta.
3. **Las ráfagas tienen dirección.** [343] *The "Neutrinos" of the Order Book*: el sentido neto de las ráfagas de
   órdenes en los 100 ms previos anticipa el movimiento. Nuestro footprint tiene el delta comprador/vendedor de la
   zona, que **todavía no se usó**.
4. **Toxicidad del flujo.** [187], [216], [234] sobre VPIN (Easley et al. 2012): el desbalance sincronizado por volumen
   anticipa episodios extremos. Las barras de 50t ya son un reloj de volumen, así que un VPIN por zona es barato.
5. **Ruptura por pico de volumen.** [296] *Breakout Detection via Volume Spike* y [22]/[400] *Regime-Filtered Intraday
   Gold (VWAP breakout)* van en la línea de uso operable, pero son de baja calidad: autores independientes, sin
   costos ni OOS. Sirven de inspiración, no de evidencia.
6. **Asimetría soporte/resistencia:** el corpus casi no la trata. Sólo aparecen [174] y [352], sobre números redondos,
   y [AAPL LOB], donde el volumen en el mejor nivel actúa "ambivalentemente como soporte o atractor". Nuestra
   asimetría (resistencias > soportes) no tiene respaldo bibliográfico directo, y eso es un motivo más para
   pre-registrarla.

## Análisis complementarios propuestos (en orden de la cadena: información → P&L)
| # | Análisis | Pregunta | Costo |
|---|---|---|---|
| A | **Control Hawkes / volumen alto sin zona** | ¿La zona agrega información sobre el pico de volumen? Emparejar por el volumen de las k barras previas y su intensidad, no sólo por el decil. | bajo (mismo runner) |
| B | **Curva de respuesta completa** | Efecto por barra h=1…200 en lugar de 3 horizontes, para estimar la vida media del decaimiento. Define cuánto debería durar una operación. | bajo |
| C | **Dirección por delta de la zona** | ¿El signo del delta (compras − ventas) del cluster anticipa hacia dónde va la expansión? Es el primer puente hacia algo direccional. | medio |
| D | **VPIN o desbalance por zona** como contexto | ¿Las zonas tóxicas expanden más? Es un contexto candidato para AVCL-VOL-2. | medio |
| E | **Costo en la ventana** | Spread y slippage en las 10 barras posteriores frente al control: verifica en nuestros datos el punto 1 de Muravyev. | bajo (hay bid/ask) |
| F | **Uso operable (requiere STOP y manifiesto)** | Breakout condicionado a zona y stop ensanchado durante la ventana, netos de costos. | después de A–C |

A, B y E son target-free con respecto a la dirección. C mide dirección, así que es información y no P&L, y aun así va
con manifiesto. Recomendación: **A + B primero**, en un solo kernel. Si la zona no sobrevive al control Hawkes, el
hallazgo es del volumen y no del indicador. Eso es igual de útil, pero cambia qué construir.
