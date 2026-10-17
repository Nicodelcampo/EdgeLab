# ORB-CFD H1 — Manifiesto: ¿mejoran las herramientas de EdgeLab al ORB?
Fecha: 2026-10-17. Estado: **BORRADOR — requiere STOP/OK de Nico antes de correr** (condiciona sobre retornos).
`docs/NORTH_STAR.md` sha256 (cuerpo): `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Pedido de Nico (2026-10-17): *«para eso quiero mejorarla con las herramientas»*. Cierra el pendiente `PENDIENTE_ORB_HERRAMIENTAS_EDGELAB_20261017.md`.

## 0. Qué es y qué no es
Es la fase de **información condicional** de la cadena (geometría → información → P&L bruto → neto): dado un rasgo **causal en el instante de la ruptura**, ¿cambia la extensión `E` del ORB-CFD primario (15 min, primer toque, cierre 15:45)? No es una estrategia ni usa costos. Un resultado positivo abre un manifiesto de estrategia y un STOP propios.
Base: la ABSTENCIÓN de `ORB_CFD_MEDIDO_Y_NO_MEDIDO.md` (USA500: +0,11 R, SD 2,56 R, N 1.863). Conocimiento previo declarado: esas medias, y que las ventanas 5 y 30 min dieron más; **no se usan para elegir nada acá**.

## 1. Aritmética de potencia (se declara antes de correr)
MDE de una diferencia entre dos grupos ≈ 2,8 × SD × √(1/n₁+1/n₂), SD ≈ 2,5 R. Con M completo de USA500 (1.863 días): partición binaria (~930 / 930) → **~0,32 R**; terciles (~620 / 620) → **~0,40 R**; ML fuera de muestra (~1.360 días) → **~0,38 R**. USATECH (628 días): ~0,6 R. **Consecuencia: H1 sólo puede detectar mejoras grandes (>0,3-0,4 R de diferencia).** Un rasgo que agregue +0,1-0,2 R es indetectable con este N y quedará en ABSTENCIÓN: eso es un hallazgo sobre el N, no sobre el rasgo.

## 2. Herramientas y su traducción (presupuesto: 6 hipótesis, ninguna más)
Sólo rasgos de **precio** (el CFD no tiene volumen negociado). Cada uno con dirección favorable **escrita antes** y justificación:
| # | Herramienta | Rasgo causal en la ruptura | Favorable | Justificación económica |
|---|---|---|---|---|
| H1 | «desde dónde» (origen) | alineación con el gap: `signo(ruptura) × signo(apertura 09:30 − cierre RTH previo)` | alineado | el flujo overnight ya apuntó hacia ahí; la ruptura contra el gap es reversión del gap |
| H2 | régimen de volatilidad | ancho del rango de 15 min / mediana del ancho de los 20 días previos, **mediana causal** como corte (bajo/alto) | alto | rangos angostos relativos producen rupturas de ruido (las colas de `E` salen de ahí) |
| H3 | «a dónde» (destino) | espacio libre: distancia del nivel roto al extremo del día previo en la dirección de la ruptura, en anchos del rango; corte = mediana causal | más espacio | un nivel de referencia cercano frena la continuación |
| H4 | «por dónde» (camino) | velocidad: minutos entre el cierre del rango y la ruptura; corte = mediana causal | rápida | rupturas inmediatas = desequilibrio; lentas = búsqueda de liquidez |
| H5 | tendencia previa | `signo(ruptura) × signo(cierre − apertura del día previo)` | alineada | continuidad de la tendencia diaria |
| H6 | modelo (ElasticNet) | combinación lineal regularizada de los rasgos continuos de H1-H5, **walk-forward** (expansivo, mín. 500 días, purga 20 días, refit anual); sólo predicciones fuera de muestra; corte = mediana de predicciones pasadas | predicción alta | prueba si la combinación agrega algo a cada rasgo |
Los umbrales son **cortes causales (mediana expansiva)**, sin parámetros ajustados: no hay grilla. **No entran:** el corredor de baja permanencia y cualquier uso de volumen (el CFD no tiene; K36/K37 ya midieron corredor×HFT en futuros sin efecto), LightGBM/CNN (con 1.863 días y ruido de 2,5 R no hay para qué), el estimador de ejecución pasiva (es de costos, fase posterior).

## 3. Diseño
Población y `E` idénticos al ORB-CFD primario (misma implementación y guardas, kernel `orb_cfd_0b` reutilizado, **mismo conjunto M ≤ 2025-07-17**). Inferencia primaria **sólo en USA500**; USATECH es chequeo de consistencia de signo, sin α propio. Estadístico por hipótesis: `D = media(E | favorable) − media(E | desfavorable)`, nulo por **permutación de la etiqueta** entre días (2.000), p unilateral. Corrección: **Holm sobre las 6 hipótesis, α = 0,05**.
Mejora declarada (`MEJORA_EN_M`) si, para una hipótesis: (i) p ajustado por Holm < 0,05; (ii) media(E | favorable) con IC 95 % inferior > 0; (iii) `D` del mismo signo en las dos mitades cronológicas; (iv) mismo signo de `D` en USATECH. `NO_MEJORA` si el IC 95 % de `D` cabe en [−0,25; +0,25] R. Resto: ABSTENCIÓN.
Se publica la distribución completa por grupo (cuantiles), N de cada grupo, SD por grupo (la reducción de varianza también es un resultado) y la media por año. **R (2025-07-18..2026-09-30) no se abre** salvo para una hipótesis con `MEJORA_EN_M`, una sola vez.

## 4. Cómo podría refutarse
Cada hipótesis queda refutada por un IC de `D` dentro de ±0,25 R. Todo H1 queda cerrado como «sin efecto detectable a este N» si ninguna pasa; no se reabre agregando rasgos nuevos sobre las mismas 1.863 jornadas (eso es la grilla que esta fase evita).

## 5. Número efectivo de hipótesis y riesgos
6 pruebas (Holm). Riesgo principal: **falso positivo por flexibilidad** (por eso: lista cerrada, cortes sin parámetros, direcciones escritas) y **falso negativo por potencia** (sección 1). Los rasgos de H2 y H3 comparten información con el ancho del rango (correlación por construcción); se publica la matriz de correlación de rasgos. CFD ≠ futuro: cualquier mejora debe pasar la equivalencia (manifiesto 0B-CFD, secc. 4) antes de transportarse.

## 6. Decisión que se le pide a Nico
1. **(A)** Aprobar H1 tal como está (6 hipótesis, sólo USA500 con chequeo en USATECH).
2. **(B)** Ajustar la lista: **necesito que confirmes la definición exacta de «las 3 franjas»**; acá interpreté «desde dónde / por dónde / a dónde» como origen (gap), camino (velocidad) y destino (espacio libre hasta el extremo previo). Si tu definición es otra, la corrijo antes de correr.
3. **(C)** Otra cosa (p. ej. salida con stop como variable de diseño, que reduce la SD pero cambia el estimando).
**Recomendación: (B) primero** (una frase tuya sobre las franjas) y luego (A). Coste: una corrida de Kaggle de pocos minutos.

## 7. Enmienda A1 (2026-10-17, opción B de Nico): definición real de las 3 franjas
Nico indicó que la definición está en el disco G y en las corridas de Gemini. Fuente leída: `EdgeLab_Bridge/resultados_claude_local/INVESTIGACION_USO_CONJUNTO_HERRAMIENTAS_Y_SISTEMA_TRES_FRANJAS_20261016.md` (secc. 2.2-2.3), e `INFORME_IMPLEMENTACION_Y_CALIBRACION_TRES_FRANJAS_HERRAMIENTAS_K33_20261016.md` (corrida k33). **La interpretación del borrador (gap / velocidad / espacio libre) era mía y no es la definición.** La definición de Gemini es de **perfil de volumen**:
- **DESDE DÓNDE** (origen): nodo de ignición/defensa; absorción pasiva, barrido de stops, giro de delta, borde de área de valor.
- **POR DÓNDE** (tránsito): franja de **baja densidad de volumen** (LVN / vacío) cuya **conductividad** (cruce rápido, sin muros internos) permite viajar de origen a destino.
- **A DÓNDE** (destino): imán; nodo de alto volumen (HVN/POC) o liquidez pendiente no mitigada.
- Ley de acoplamiento: las tres se evalúan **juntas**; la probabilidad de éxito se factoriza en ignición × transmisión × captura.
Lo que k33 midió: tensores 6×24×32 de ES (178 sesiones, 30.101 muestras) y un modelo de toque de barrera con AUC 0,56-0,59 (en validación/evaluación temporales de ese diseño), **no** una prueba de ORB; y la cadena k34-k37 que se apoyó en esas herramientas no halló efecto neto (`K36_K37_LO_RESCATABLE_20261017.md`). No se importa ninguna conclusión de k33 a esta familia.
**Consecuencia estructural:** la definición exige **volumen negociado**. El CFD de Dukascopy no lo tiene (sólo cotizaciones). Por eso H1 se parte en dos niveles, independientes y sin transportar resultados entre sí:
- **Nivel P (precio, CFD, USA500/USATECH, N = 1.863/628):** las 6 hipótesis de la secc. 2 quedan **tal cual**, pero se reetiquetan como **proxies de precio** de las franjas, no como las franjas: H1 gap (origen, sólo proxy de dirección del flujo previo), H3 espacio libre hasta el extremo del día previo (proxy de destino), H4 velocidad (proxy de tránsito). Sin pretensión de medir densidad de volumen.
- **Nivel V (volumen, futuros ES/NQ, N = 173/161 en descubrimiento):** dos rasgos de volumen **causales**, descriptivos, **sin compuerta ni α** (la potencia no alcanza: MDE de una diferencia ~0,9-1,0 R):
  - **V1 volumen relativo del rango** (herramienta de «stocks in play», Zarattini-Aziz): volumen del rango de 15 min / mediana de los 20 rangos previos; favorable > 1.
  - **V2 conductividad del «por dónde»:** densidad de volumen por tick del **perfil de la sesión RTH previa** en el corredor de un ancho de rango por delante del nivel roto, dividida por la densidad media del perfil previo; favorable < 1 (vacío). Es la lectura causal más fiel posible de «por dónde» con estos datos.
  - «Desde dónde» (absorción/delta) y «a dónde» (HVN/liquidez pendiente) con volumen **no entran**: requieren agresor/L2 y definir imanes (POC, pools), que son más grados de libertad sobre 173 días. Quedan NO MEDIDOS.
**Qué cambia en las decisiones:** el nivel P decide con la regla de la secc. 3. El nivel V sólo publica tamaños de efecto, N y MDE con la etiqueta «factibilidad»: no promueve ni descarta nada y no abre R.
**Autorización:** «opción B, y después A» (Nico, 2026-10-17): se corrige la lista (esta enmienda) y se ejecuta. Dos kernels congelados por commit antes de correr.
