# LUX-IMB — verificación de fuente antes del port Pine→NT8

**Fecha:** 2026-08-11  
**Estado:** fuente pública identificada; código Pine exacto y artefacto NT8 todavía no capturados.  
**Alcance del operador:** OG + VI activos, FVG apagado.

## 1. Fuente correcta

El indicador observado corresponde a:

- **TradingView:** `Imbalance Detector [LuxAlgo]`
- **ID público:** `C0cC294Q`
- **URL:** https://www.tradingview.com/script/C0cC294Q-Imbalance-Detector-LuxAlgo/
- **Publicación:** 2022-12-20
- **Última actualización declarada:** 2023-03-10
- **Estado:** open-source script

Fuente complementaria oficial:

- https://www.luxalgo.com/library/indicator/imbalance-detector/

No debe confundirse con **Price Action Concepts® / Imbalance Concepts**. El input `Mitigation Method` y la desaparición automática al mitigar pertenecen a ese producto distinto. No son propiedades demostradas del script `C0cC294Q` y contradicen la observación del operador para su chart.

## 2. Parámetros confirmados públicamente

Cada familia FVG/OG/VI expone el mismo layout:

1. `Imbalance`: enable/disable;
2. `Min Width`: filtro opcional;
3. método de ancho: puntos, porcentaje o múltiplos de ATR;
4. `Extend`: cantidad de barras de proyección;
5. color/estilo;
6. dashboard separado.

Configuración de esta investigación:

- OG: activo;
- VI: activo;
- FVG: apagado;
- `Min Width`: pendiente de exportar;
- modo de ancho: pendiente de exportar;
- `Extend`: pendiente de exportar;
- timeframe, símbolo, contrato y plantilla de sesión: pendientes de congelar.

## 3. Geometría confirmada por descripción oficial

### Opening Gap

- OG alcista: `low_t > high_{t-1}`;
- intervalo: `[high_{t-1}, low_t]`;
- OG bajista: `high_t < low_{t-1}`;
- intervalo: `[high_t, low_{t-1}]`.

La fuente declara que OG tiene prioridad visual sobre FVG cuando ambos aparecen. Con FVG apagado esto no cambia la población primaria, pero debe preservarse en cualquier implementación general.

### Volume Imbalance

La descripción oficial fija la estructura conceptual:

- discontinuidad entre `open_t` y `close_{t-1}`;
- cuerpos de velas no solapados;
- wicks todavía solapados;
- filtro adicional para evitar VIs excesivas en mercados con gaps frecuentes.

La prosa pública no alcanza para fijar sin ambigüedad todas las desigualdades, bordes inclusivos, filtro de ancho ni cálculo ATR/porcentaje. Además repite por error la palabra “bullish” al describir la condición extra bajista. Por eso **no se autoriza un port basado sólo en esta descripción**.

## 4. Estado visual y lifecycle

La página pública habla de porcentaje de llenado y alertas, pero no afirma que el script `C0cC294Q` borre automáticamente las zonas mitigadas. El operador observó que no desaparecen.

Contrato provisional:

- creación y geometría se reconstruyen as-of;
- `Extend` se trata como proyección visual hasta leer el Pine;
- contactos, penetraciones y cruces se guardan como eventos;
- no se inventa un estado terminal por mitigación;
- cualquier diferencia entre pantalla y ledger se resuelve por paridad, no por interpretación retrospectiva.

## 5. Posible atajo NinjaTrader

La página oficial de LuxAlgo anuncia acceso gratuito del mismo indicador para NinjaTrader. Esto puede evitar un port manual o servir como oráculo de paridad.

Todavía no se verificaron:

- URL directa del artefacto;
- versión compatible con NT8;
- código fuente o licencia;
- igualdad semántica con `C0cC294Q` de 2023;
- digest del archivo;
- parámetros y defaults.

Hasta capturar esos elementos, “NinjaTrader disponible” es una pista, no evidencia de equivalencia.

## 6. Gate de implementación

Antes de escribir el detector productivo deben existir:

- [ ] export o snapshot autorizado del Pine exacto mostrado por TradingView;
- [ ] SHA-256 del source normalizado, sin republicarlo si la licencia no lo permite;
- [ ] tabla de parámetros/defaults del chart de Nico;
- [ ] definición exacta de `Min Width` en los tres modos;
- [ ] definición exacta de VI, incluyendo desigualdades y bordes;
- [ ] semántica real de `Extend`;
- [ ] muestra Pine con al menos 50 zonas OG/VI y casos de borde;
- [ ] artefacto NT8 oficial, si existe, con versión y SHA-256;
- [ ] comparación geométrica y temporal Pine↔NT8.

Gate de paridad:

```text
Jaccard >= 0.95 por familia y dirección
error de bordes <= 1 tick
error de available_at <= 1 barra
cero diferencias no explicadas en casos de borde preregistrados
```

## 7. Decisión actual

La investigación de fuente sí cerró tres preguntas:

1. se verificó cuál es el script correcto;
2. se confirmó que OG/VI/FVG comparten `Imbalance`, `Min Width` y `Extend`;
3. se demostró que la documentación de Price Action Concepts® no puede transportarse al script abierto.

No cerró la semántica ejecutable completa. Por lo tanto, este PR permanece documental y no se escribe un detector aproximado que después pueda fabricar una “reacción” por diferencias de geometría.
