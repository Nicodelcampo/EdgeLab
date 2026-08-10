# F1.2 + F1.3 — supervivencia con riesgos competitivos y depleción por toque · RESULTADO

**Fecha** 2026-08-10 · **Artefacto** `F1_superv_depletion__b107bf368c08.json`
**Módulo** `diag/tasa_senales/F1_supervivencia_y_depletion.py`
**Outcomes** `false` · **Multiplicidad gastada** cero · **Holdout** intacto
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`

**Desviación declarada del plan:** el plan v2 pedía un Cox. `lifelines` no está
en el lock y `CLAUDE.md` prohíbe dependencias pesadas nuevas, así que se
estratificó por cuantil de covariable. Publica la curva completa de cada estrato
en vez de un coeficiente, lo cual acá resultó ser más informativo.

---

## 1. F1.2 — la zona rompe. Siempre.

Incidencia acumulada por causa (Aalen-Johansen, riesgos competitivos, 15.947
zonas, 34 censuradas):

```
close_through        0,9081
close_through_gap    0,0547     ->  RUPTURA TOTAL  0,9628
max_age              0,0372
```

Supervivencia de la zona:

```
   1 barra    0,8463          20 barras   0,3259
   2 barras   0,7368          60 barras   0,1977
   5 barras   0,5591         120 barras   0,1445
  10 barras   0,4303
```

**Mediana de vida: ~6 barras.** La mitad de las zonas está muerta en seis
minutos. Y el **96,3 %** termina rota, no expirada.

---

## 2. Corrección de algo que yo afirmé en el acta de muerte

En `ACTA_MUERTE_H1_2026-08-09.md` §4 escribí:

> *«"Primer toque post-`sep_min`" no selecciona rechazos de zona. **Selecciona
> rupturas.**»*

**Está mal, y la corrección importa.**

```
H1: 394 de 424 salieron por close_through      92,9 %
TODAS las zonas: rompen eventualmente          96,3 %
```

La población de H1 **no era más propensa a romper: estaba por debajo de la tasa
base.** El primer toque no selecciona nada especial — **todas las zonas rompen**.
La ruptura no es un desenlace de una subpoblación desafortunada: es el estado
terminal del objeto, y lo era antes de que ningún filtro entrara en juego.

**Lo que NO cambia**, y de hecho se refuerza: la regla de salida «sostener hasta
que la zona se invalide» paga contra una tasa base de terminación adversa del
96,3 %. Antes parecía una propiedad de la población elegida. **Es una propiedad
de toda zona de BigTrap2**, así que el defecto es más general de lo que decía el
acta, no menos.

---

## 3. F1.3 — la depleción existe, pero es débil donde están los datos

Fracción de toques que rompen el nivel **en esa misma barra**, por ordinal:

| ordinal | toques | rompió | tasa |
|---|---|---|---|
| 1 | 15.608 | 4.726 | **30,3 %** |
| 2 | 10.549 | 3.367 | **31,9 %** |
| 3 | 6.942 | 2.151 | 31,0 % |
| 4 | 4.615 | 1.428 | 30,9 % |
| 5 | 3.066 | 875 | 28,5 % |
| 6 | 2.096 | 583 | 27,8 % |
| 7 | 1.449 | 379 | 26,2 % |
| 8 | 1.038 | 281 | 27,1 % |
| 9 | 733 | 183 | 25,0 % |
| 10 | 539 | 127 | 23,6 % |
| >10 | 2.133 | 357 | **16,7 %** |
| **TOTAL** | **48.768** | **14.457** | **29,6 %** |

**Qué se confirma:** la tasa de ruptura **baja** con los toques previos, 30,3 % →
16,7 % (**1,81×**). La dirección que predice la literatura es correcta.

**Qué NO se confirma, y hay que decirlo:**

1. **El toque nº 1 no es el más propenso a romper.** El nº 2 lo es (31,9 % contra
   30,3 %). La tesis del «nivel virgen» —que H1 midió en exclusiva— **no se
   sostiene acá**.
2. **El efecto es plano donde está la masa.** Los ordinales 1–4 son **37.714 de
   48.768 toques (77 %)** y ahí la tasa no se mueve: 30–32 %. El descenso recién
   se vuelve material en la cola fina, donde hay 2.133 observaciones.

Una regla que quiera explotar la depleción tiene que operar en la cola, donde hay
**el 4,4 % de los eventos** — con el problema de potencia que eso implica.

---

## 4. La covariable de la literatura no aparece: el volumen no da estabilidad

La literatura de soportes/resistencias sostiene que *zonas formadas con alto
volumen transaccional muestran mayor estabilidad y menor probabilidad de ruptura*.

Estratificado por terciles de volumen atrapado, 15.947 zonas:

```
q1  vol <= 43      rota 0,9649
q2  43 < vol <= 71 rota 0,9607
q3  vol > 71       rota 0,9578
```

**0,7 puntos porcentuales de efecto total a lo largo de todo el rango.** En estos
datos, con este indicador, **el volumen atrapado no predice estabilidad.**

Por altura (que casi no tiene rango, como midió F0.2):

```
altura <= 1 tick   n=14.017   rota 0,964   vida mediana  7 barras
altura >  1 tick   n= 1.930   rota 0,941   vida mediana 12 barras
```

Coherente con F2: **la altura compra tiempo (1,7×), no supervivencia.**

Por toques —y acá hay que leer con cuidado—:

```
<= 1 toque    n=5.398   rota 0,926   vida  2 barras
1-3 toques    n=5.934   rota 0,979   vida  6 barras
>  3 toques   n=4.615   rota 0,979   vida 28 barras
```

Las zonas más tocadas rompen **más**, no menos. **No es contradicción con F1.3**:
es condicionamiento por supervivencia. Una zona llega a tener muchos toques
porque vivió mucho, y vivir mucho termina en ruptura (96,3 %). El estrato de ≤1
toque rompe menos sólo porque contiene a las 339 que expiran sin ser tocadas.
**Es una trampa de selección, no un hallazgo** — se deja registrada para que
nadie la lea al revés más adelante.

---

## 5. Balance de las tres hipótesis pre-declaradas

| hipótesis | origen | veredicto |
|---|---|---|
| «la altura domina el hazard de ruptura» | mía, `PLAN_ANALISIS_v2` §F1.2 | **REFUTADA** (F2: 4× altura, misma tasa) |
| «alto volumen ⇒ más estabilidad» | literatura S/R | **NO SE CONFIRMA** (0,7 pp) |
| «el rebote sube con toques previos» | literatura S/R | **CONFIRMADA en dirección**, débil donde está la masa |

Tres hipótesis declaradas antes de medir; una refutada, una no confirmada, una
parcialmente confirmada. Ninguna se reformuló después de ver el resultado.

---

## 6. Qué queda de todo esto

**El objeto está caracterizado, y es un objeto de vida corta y final único.** Una
zona de BigTrap2 vive una mediana de 6 barras y termina rota el 96,3 % de las
veces, sin que la altura, el volumen ni la selectividad muevan esa cifra.

Eso descarta —a costo cero de multiplicidad y sin tocar un outcome— toda la
familia de hipótesis del tipo *«encontrar la configuración o el subconjunto donde
el nivel resiste»*. No existe en lo barrido.

**Y deja el peso donde no se miró:**

1. **`bar_spec`** — la única dimensión que cambia toda la agregación del
   footprint, congelada en `time:1` en siete módulos, nunca variada.
2. **E4, la ruptura como evento propio** — si el 96,3 % de las zonas termina
   rota, la ruptura no es el fracaso del objeto: **es el objeto**.
3. **F1.1, el nulo contra zonas aleatorias** — con un paisaje tan plano y
   covariables que no discriminan, la pregunta de si esto se distingue del azar
   pasa a ser la más urgente del programa.

---

## Aporte al referente

Se caracterizó el objeto por primera vez —vida mediana 6 barras, 96,3 % de
terminación por ruptura, invariante a las covariables candidatas— y se corrigió
una afirmación propia del acta de muerte que atribuía a la población de H1 una
propiedad que es de **todas** las zonas. La distancia al edge se reduce por
descarte barato y por reasignación: tres ejes de búsqueda quedan cerrados con
evidencia, y el presupuesto se redirige a `bar_spec`, a la ruptura como evento y
al test nulo, que es el que puede terminar con la familia entera por menos de lo
que cuesta una hipótesis.
