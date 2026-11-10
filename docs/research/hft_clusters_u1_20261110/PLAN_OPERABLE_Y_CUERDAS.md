# Plan — de «las zonas HFT no son soporte» a situaciones operables, y cómo agregarle efecto

Estado: PLAN (2026-11-10, pedido de Nico; escrito ANTES de ver los resultados de `REBOTE_NIVEL_SESION` y de la confirmación
`CONFIRMACION_NO_DEFIENDE.md`). No lanza nada: las corridas que siguen se pre-registran cuando esos dos resultados estén.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 0. Dónde estamos (números, no impresiones)
- **La cuerda:** en el primer regreso a un nivel de la sesión, un nivel cualquiera revierte (control: NQ +0,078, RTY +0,100, YM
  +0,073 de rebote en la carrera ±X), y donde hubo actividad HFT ese rebote desaparece o se invierte (real − control +0,10 en
  ruptura, estable 4/5 en activos independientes, p 0,088; re-medición de rebotes D0/D1/D6 y de clusters chicos con el mismo signo).
- **Tamaño:** el rebote del nivel limpio es del orden del umbral económico (0,08 R de fricción con stop X): en bruto paga apenas la
  fricción; lo operable exige concentrarlo o cambiar la geometría.
- **Pendiente:** el banco de `REBOTE_NIVEL_SESION` (abr–sep, la distancia a zonas como parámetro espacial × temporal) y la
  confirmación congelada de «no defiende» (LORD++ 0,0109).
- **Presupuesto de datos:** DESC ya está mirado para estos objetos en NQ/ES/RTY/YM/6E/6B (y GC para clusters chicos). Abr–sep se
  consume en las dos corridas pendientes. Lo que queda sin mirar: el **holdout** (desde la sesión del 1-oct-2026, una apertura por
  familia, por protocolo), el **forward/papel**, y DESC de activos/eventos que nunca se usaron (p. ej. niveles de pivote en GC).

## 1. Principio (directiva 17)
Un efecto chico no se vuelve operable agrandando la grilla. Se vuelve operable por cuatro caminos, en este orden:
1. **Concentrarlo** (la cuerda): encontrar la condición donde el rebote es varias veces el promedio y explicar por qué.
2. **Geometría:** elegir dónde entrar y salir para que el mismo efecto pague más que la fricción (entrada pasiva en el nivel,
   objetivo y stop asimétricos), medido con fills realistas.
3. **Veto en la cartera:** usar «nivel con zonas HFT» como filtro de estrategias de reversión ya existentes: no agrega señales, saca
   las malas (efecto sin costo de entrada propio).
4. **Canasta:** varios activos y horarios poco correlacionados (regla 08/11), en vez de la mejor celda aislada.

## 2. Traducción operable — tres candidatos (se pre-registran después de los resultados pendientes)
Comunes: R = (resultado − costos de `edgelab/costos.py`) / riesgo inicial; motor tick a tick (`edgelab/research/sim.py`); un
evento por activo a la vez (los niveles se solapan); sin entradas en los últimos 15 min de la sesión; tope de pérdida diaria y
kill switch de la cartera (`edgelab/cartera/`).

| Id | Situación | Entrada | Salida | Qué lo mata |
|---|---|---|---|---|
| **OP-1 Fade del nivel limpio** | primer regreso a un nivel de la sesión SIN zonas HFT cerca (distancia y ventana: las que nomine el banco) | orden **límite en el borde del nivel**, colocada al fijarse el nivel (el nivel se conoce antes del toque: la orden puede estar en el libro) | stop X más allá del nivel; objetivo X (y variantes de geometría §3-I6); tiempo máximo = vida del nivel | rebote neto ≤ 0 con **fills pasivos realistas** (selección adversa: la límite se llena sobre todo cuando el precio sigue) |
| **OP-2 Continuación en zona HFT** | primer regreso a un nivel CON cluster/zonas HFT | stop de entrada a favor de la llegada al penetrar X/8 en la banda | stop al otro lado de la banda + X/2; objetivo X | sólo vale si el banco/estabilidad muestra ruptura > 0,08 en alguna condición; hoy +0,01–0,03: candidato débil |
| **OP-3 Veto HFT para reversión** | estrategias de reversión ya medidas (fade de extremos, ORB fallido, etc.) | las mismas | las mismas | el veto («no entrar si hay zona HFT a < 0,5 X en 30 min») no mejora el R **en bruto** (K2) o sólo saca operaciones al azar |

OP-1 es el más directo; OP-3 es el más barato (no necesita fills nuevos ni señal nueva) y respeta «filtrar antes que agregar».

## 3. Indagar para agregarle efecto (de más barato a más caro)
| Id | Pregunta (cuerda) | Cómo | Datos |
|---|---|---|---|
| I1 | ¿El rebote crece monótonamente con la distancia a zonas y con el tiempo sin zonas? (firma de mecanismo) | curva dosis-respuesta continua (distancia × ventana) sobre la tabla de niveles; monotonía como predicción | tabla de abr–sep (después del banco: exploratoria) |
| I2 | ¿Qué TIPO de nivel defiende más? | generadores nuevos (regla b): pivotes de 1 min, extremos de la sesión, apertura, VWAP; mismo evento D0 | DESC de activos/eventos no usados; holdout para confirmar |
| I3 | ¿Es liquidez pasiva visible? | profundidad del libro en el nivel al regreso (L2) contra el rebote | L2 local de GC/ES (`docs/research/ENTREGA_LOCAL_L2_GC_ES_20260930.md`): verificar cobertura antes |
| I4 | ¿El agresor decide? | desequilibrio por tick rule y pico de volumen en los 30 s previos (ya son rasgos: `deseq30`, `vol30_rel`); cruce con distancia a zonas | tabla de niveles |
| I5 | ¿Régimen? | día de rango vs. tendencia (rango de la sesión / ATR, detectable en tiempo real), volatilidad de 30 min, hora | tabla de niveles; régimen declarado antes (motor de régimen offline) |
| I6 | ¿Geometría? | la tabla ya trae ±X/2 y ±2X: elegir **ex ante** 3 geometrías (X/X, X/2·X, 2X·X) y medirlas juntas, no buscar la mejor | tabla de niveles |
| I7 | ¿Confluencia entre activos? | NQ y ES (o NQ y RTY) en un nivel limpio a la vez | tabla de niveles |

Cada indagación es una especificación del banco o una hipótesis previa (no un módulo nuevo), con estabilidad por sub-bloques.

## 4. Estructura que falta construir (directiva 18)
1. **Motor de fills pasivos tick a tick con máquina de estados causal** (orden en el libro desde que se fija el nivel; llena sólo si
   el precio opera A TRAVÉS del nivel por ≥ 1 tick, o al tocar con cola desconocida en el escenario adverso; cancela al vencer). Hoy
   no existe en el repo (k32 lo midió afuera: +0,64 ticks/op de optimismo del modelo simple). Sin esto OP-1 no se puede medir.
2. **Banco con varios desenlaces** por especificación (geometrías de I6) contados como una familia.
3. **Generadores de nivel** de I2 con su test de prefijo, registrados en `GENERADORES`.
4. **Puente L2** (I3) si la cobertura alcanza.

## 5. Árbol de decisión (según los dos resultados pendientes)
- **Confirmación H1 confirmada y el banco de niveles nomina «sin zonas → rebote»:** construir el motor de fills (§4.1), pre-registrar
  OP-1 y OP-3 con la distancia/ventana nominadas, medirlos en DESC de activos no usados (I2) y confirmar la canasta OP-1 + OP-3 en el
  **holdout** (una apertura, probabilidad de azar de desarrollo declarada, regla 08/11).
- **H1 confirmada pero el banco no nomina nada:** el mecanismo existe pero el nivel limpio no paga: priorizar OP-3 (veto) y las
  indagaciones I3–I5 para concentrar.
- **H1 no confirmada:** la cuerda se debilita: no construir OP-1; dejar F-HFT-ZONAS-NO-SON-SOPORTE en seguimiento y medir sólo OP-3
  como veto barato en estrategias existentes.
- **Siempre:** asentar en FACTORES, actualizar REMEDICIONES si cambia la medición, y no reabrir el rebote EN zonas HFT.

## 6. Riesgos
- **Selección adversa** en la entrada pasiva (puede comerse todo el efecto: por eso el motor de fills va antes que cualquier P&L).
- **Datos escasos sin mirar:** después de abr–sep sólo queda el holdout y el forward; cada familia tiene UNA apertura.
- **Efecto del orden del umbral:** sin concentración, OP-1 da ≈ 0 neto; el plan no lo fuerza.
- **Correlación entre niveles** de la misma sesión: el riesgo real es por sesión, no por evento.

## 7. Iteración 1 (2026-11-10, antes de ver resultados) — lo que cambió al llevarlo a cabo
- **Motor de fills pasivos construido** (`edgelab/research/fill_pasivo.py`, tests): máquina de estados ESPERA → EN_LIBRO → LLENA →
  CERRADA/VENCIDA; modelos «toca» (optimista) y «atraviesa» (decide); stop gana en empate; salida por tiempo.
- **La orden de OP-1 se activa recién a ≥ X/2 del nivel** (si estuviera desde que el nivel se fija, se llenaría en el acto):
  coincide con el evento D0 y es causal.
- **Nulo de selección adversa medido:** en una caminata al azar sintética, la orden límite con fill «atraviesa» da R bruto ≈ −0,07
  (objetivo X), −0,04 (X/2), −0,085 (2X). Consecuencia: el rebote +0,08 de la carrera desde el borde no alcanza; OP-1 necesita un
  filtro que lleve el rebote bruto a ≳ +0,15. Esto vuelve más importantes las indagaciones de concentración (I1, I4, I5) y OP-3.
- **Geometrías fijadas antes:** objetivo X/2, X (primaria) y 2X, siempre con stop X (fricción en R = 0,08; un stop menor la sube).
- **Tipos de nivel (I2) implementados:** «reloj» y «pivote» (máximo/mínimo de 1 min confirmado) en el mismo generador.
- **Tabla operable lanzada** (`niveles_op_replica`: abr–sep, NQ/ES/RTY/YM/GC, los dos tipos, fills y geometrías; sólo tabla).
  Pre-registro y análisis congelado: `PREREGISTRO_OP1.md`, `tools/op1_niveles.py` (24 pruebas, familia REBOTE_NIVEL_SESION).
- **OP-3 (veto):** requiere las operaciones de estrategias de reversión ya medidas con su instante de entrada; queda como tarea del
  agente (lente `cuerdas`/`remedir`): listar candidatas en `FAMILIAS.md` con trayectorias disponibles y medir el veto en bruto.
