# Prop firms: scraper, analizador de reglas y esperanza matemática (2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Rama:** `feat/propfirm-ev-20260926`. **Código:** `edgelab/propfirm/` (`rules.py`, `ev.py`, `requirements.py`,
`scraper.py`), `tools/propfirm_ev_report.py`, tests `tests/propfirm/`. **Datos:** `config/propfirms/`.
**Estado:** herramienta de análisis, no una estrategia. No mira el holdout ni corre búsquedas sobre retornos nuevos:
usa ventajas ya medidas en EdgeLab.

## 1. Los tres papers, en simple

### Villahermosa (2026), «Prop-Firm Challenges: A Barrier Model of Pass Rates and Expected Value» — SSRN 7445798
- **Idea:** una evaluación es una carrera entre dos barreras: llegar al objetivo T antes de tocar el límite de pérdida L.
- **Resultado clave:** si no tenés ventaja, la probabilidad de pasar es **L / (T + L)**, sin importar cuánto arriesgues
  por trade. Con T = 1,25 L da 44,4 %. Es un **techo**, no una promesa.
- **Por qué el pase real es menor:**
  - el piso de pérdida sube con el máximo de la cuenta (trailing);
  - las posiciones se cierran cada día;
  - cada trade paga comisión.
  Con 6 años de datos de 1 minuto, el pase baja de 44,4 % a 40,4 % y después a **34,7 %**.
- **Plata:** el EV por intento es +0,052 L con la cuota con descuento que se paga en la práctica y **−0,018 L a precio de
  lista**. La regla de consistencia no cuesta nada si repetís exactamente el mismo bracket dos días, pero está al filo.
- **Para EdgeLab:** la cuenta no crea ventaja. Sin ventaja estás en el techo menos las fricciones, y a precio de lista
  perdés.

### Hall (2026), «Gate Design and Stage-Dependent Incentives…» — SSRN 7453580
- **Idea:** hay dos compuertas con incentivos **opuestos**.
  - La **evaluación premia** operar rápido, a los saltos y con tamaño grande: sin ninguna habilidad, sólo con el tamaño,
    se pasa ~40 % de las veces, contra un 16,8 % real observado.
  - La **cuenta fondeada castiga** esa misma conducta: con los mismos parámetros, la compuerta conjunta cae 9 veces.
- **Consecuencia:** pasar la evaluación **no prueba habilidad**. Lo que filtra es la compuerta de pago, y las firmas
  publican tasas de pase mucho más que tasas de pago.
- **Piso de costos en futuros:**
  - micro ≈ 1,12 puntos por ida y vuelta;
  - contrato completo 13,8 USD (28,8 USD en el percentil 90);
  - la mejor ventaja bruta que encontró fue +0,32 puntos: el costo se la come.
- **Regla metodológica:** todo resultado de una cuenta tiene que compararse con el **mismo pipeline sin ventaja**. Si
  no, se confunde el valor de opción de la cuenta (el riesgo está acotado a la cuota) con lo que aporta la estrategia.

### Arias (2026), «Audit-Grade Pre-Validation of Trading Strategies» — SSRN 7308022
- **Idea:** el 86 % falla la evaluación y sólo el 7 % cobra algo. La causa es el **sobreajuste**: estrategias que se ven
  bien en el backtest y no tienen ventaja.
- **Propone validar antes de pagar**, con cinco agregados al método de López de Prado:
  1. reportar el DSR con **dos** conteos de pruebas (declaradas y efectivas);
  2. un Calmar sobre el **capital operativo**, sin el inflado por apalancamiento;
  3. subperíodos que detectan una ventaja **decreciente**;
  4. un test de **aislamiento de componentes** en estrategias compuestas;
  5. regímenes de volatilidad alta y baja como compuerta **obligatoria**.
- Todo se resume en un puntaje de 0 a 100 con compuertas duras.
- **Para EdgeLab:** EdgeLab ya hace pre-registro, FDR, nulos y holdout sellado. De Arias conviene sumar los puntos 1, 3 y
  5 a la compuerta de promoción.

## 2. Qué construí

| Pieza | Qué hace |
|---|---|
| `scraper.py` | baja páginas públicas de reglas, guarda texto y sha256 y extrae **candidatos** (número + contexto) por campo. No los convierte en reglas: eso lo hace una persona. Apex y Lucid bloquean las descargas automáticas (403) y quedan marcadas `BLOQUEADO`. |
| `rules.py` | las reglas como datos: objetivo, límite de pérdida (estático, trailing al cierre o intradía, con bloqueo), límite diario, consistencia, días mínimos, cuotas, activación y retiros (días, mínimo, fracción, split, tope y cantidad). Techo `L/(T+L)`. |
| `ev.py` | Monte Carlo del **ciclo completo**: evaluación → fondeada → retiros, con el control de ventaja cero siempre al lado y el `aporte` = EV − EV sin ventaja. |
| `requirements.py` | el inverso: acierto y **ventaja neta mínima por trade (ticks)** para EV > 0, por instrumento, bracket, tamaño y cadencia; barrido de tamaño × cadencia; **`gate()`**, que evalúa la cuenta con la ventaja en el **límite inferior del IC**. |
| `tools/propfirm_ev_report.py` | reporte para el catálogo y **cruce con las ventajas medidas en EdgeLab**. |

**Validación** (`tests/propfirm/`, 8 tests):
- sin ventaja y con piso fijo, el pase simulado da L/(T+L) ± 0,03;
- el trailing al cierre y el intradía nunca pasan más que el piso fijo;
- los costos y la regla de consistencia no suben el pase;
- el control de ventaja cero tiene EV < 0;
- la compuerta rechaza una ventaja que sólo paga en el valor puntual.

**Catálogo inicial** (`config/propfirms/catalogo_inicial.json`):
- dos cuentas de referencia que reproducen los papers: Villahermosa, techo 44,4 %; Hall, techo 40 %;
- Topstep 50K Combine. Del límite de 2.000 USD tomé de la página oficial scrapeada el monto, el trailing al cierre y el
  bloqueo en el saldo inicial. El objetivo, la cuota, la consistencia y los retiros **no están verificados**.

## 3. Resultados del cruce (3.000 caminos; cuentas de referencia y Topstep sin verificar)

| Estrategia medida (ES) | Villahermosa: EV / aporte | Hall: EV / aporte | Topstep 50K: EV / aporte |
|---|---|---|---|
| TBZX-R3 sigue r=0, SL=TP=3 (−1,49 t) | −70 / 0 (pase 0 %) | −150 / 0 | −49 / 0 |
| IVC corto plazo, SL=TP=4 (−0,8 t) | −70 / 0 (pase 0 %) | −150 / 0 | −49 / 0 |
| TBZX-R3 mejor macro, SL=TP=20 (+0,19 t, **no validada**) | +51 / +98 | −5 / +137 | +102 / +144 |
| IVC-L gap → cierre, SL=TP=40, 1/día (+0,8 t, **margen IC inf. < 0**) | +48 / +53 | +46 / +122 | +150 / +124 |

**Lectura:**
1. Las ventajas de ticks chicos que EdgeLab midió **no pasan ninguna evaluación**: con 3–4 ticks por trade no se llega al
   objetivo en 60 días, y encima pierden por trade.
2. La cuenta **amplifica** una ventaja de objetivos grandes: +0,2 a +0,8 ticks por trade ya dan EV de +50 a +150 USD por
   intento. Pero **ninguna de esas ventajas está validada**. Con la `gate()`, que evalúa en el IC inferior, las dos
   quedan afuera.
3. Hay configuraciones «lotería» (bracket grande, pocos trades) con EV > 0 aun con ventaja nula o negativa. Es el valor
   de opción de la cuenta que describe Hall, y el modelo de retiros de este simulador es permisivo. **No es un edge** y
   por eso el reporte siempre muestra el control sin ventaja.

## 4. Cómo cambia el diseño de los análisis de EdgeLab

La esperanza de la cuenta pide cosas concretas a la investigación:

1. **Horizonte y bracket compatibles con la cuenta.** Con L = 1.000–2.000 USD y un objetivo de 1,25–1,5 L, los brackets
   útiles en ES van de 16 a 40 ticks, con 1–3 trades por día. Los análisis de horizonte de 1 a 15 minutos no sirven para
   esta cuenta aunque encontraran ventaja. Esto coincide con el mapa IVC.
2. **Requisito cuantitativo en el pre-registro.** Cada manifiesto de estrategia declara la cuenta objetivo y el
   requisito de `requirement()`: ventaja neta mínima por trade en ticks, con su bracket y cadencia. Una celda
   «prometedora» tiene que superar ese número con el **IC inferior**, no con el punto.
3. **Compuerta de promoción = `gate()`**: EV > 0 y aporte sobre el control sin ventaja > 0 en el IC inferior, y sólo
   con reglas `verified = True`.
4. **Tamaño y cadencia se eligen para la etapa fondeada, no para la evaluación** (Hall: la evaluación premia lo que la
   fondeada castiga). `sizing_sweep()` muestra los dos lados.
5. **Sumar de Arias** a la compuerta estadística ya existente: DSR con doble conteo de pruebas, detección de decaimiento
   por subperíodos y regímenes de volatilidad como condición obligatoria.
6. **Costos por instrumento medidos, no transportados.** `INSTRUMENTS` usa el costo agresivo de IVC para ES (2,4 t) y
   valores de Hall para los micros. Hay que ajustarlos con fills reales (EXEC-QI) antes de decidir.

## 5. Limitaciones y pendientes

- **Actualización (mismo día):** las reglas de retiro escondidas ya se simulan y hay un catálogo detallado de 50K; ver `PROPFIRM_REGLAS_DETALLADAS_20260926.md`.
- El modelo de retiros es **simplificado y permisivo**: fracción fija del beneficio del ciclo y días mínimos, sin «días
  ganadores» ni saldo buffer. Sesga el EV hacia arriba, así que hay que completarlo por firma con las reglas verificadas.
- El piso intradía aproxima el camino de cada trade: el perdedor baja directo al SL y el ganador retrocede como mucho
  `mae_win`·SL.
- El scraper sólo trae candidatos. **Verificar cada regla a mano** y marcar `verified = True` antes de usar un resultado.
  Apex y Lucid necesitan bajarse con navegador.
- Scraping: respetar los términos de cada sitio. Una bajada por página, sin reintentos agresivos.
