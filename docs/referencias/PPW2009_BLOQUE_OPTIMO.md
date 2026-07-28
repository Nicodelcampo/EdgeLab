[# Referencia: selección automática del largo de bloque (PPW 2009

Este documento existe para cerrar un hueco de PROCEDENCIA, no de fórmula.
El repositorio afirmaba tener implementada la corrección de 2009 y haberla
"verificado línea por línea", pero la fuente no estaba en el repositorio.
Sin esto, la implementación es indistinguible de una fórmula inventada.

## Fuentes

[PW2004] Politis, D. N. y White, H. (2004). "Automatic Block-Length
         Selection for the Dependent Bootstrap". Econometric Reviews
         23(1):53-70. DOI: 10.1081/ETC-120028836

[PPW2009] Patton, A., Politis, D. N. y White, H. (2009). "Correction to
          'Automatic Block-Length Selection for the Dependent Bootstrap'
          by D. Politis and H. White". Econometric Reviews 28(4):372-375.
          DOI: 10.1080/07474930802459016

[PR1994] Politis, D. N. y Romano, J. P. (1994). "The Stationary Bootstrap".
         JASA 89:1303-1313.

[PR1995] Politis, D. N. y Romano, J. P. (1995). "Bias-corrected
         nonparametric spectral estimation". J. Time Series Anal. 16:67-103.

[Lahiri1999] Lahiri, S. N. (1999). "Theoretical comparisons of block
             bootstrap methods". Ann. Statist. 27:386-404.

[Nordman2008] Nordman, D. J. (2008). "A note on the stationary bootstrap's
              variance". Ann. Statist.

Consultadas el 2026-07-28 en:
  https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf
  https://public.econ.duke.edu/~ap172/Politis_White_2004.pdf

## 1. Marco

Serie estrictamente estacionaria X_1, ..., X_N con media mu y
autocovarianza R(s) = E[(X_t - mu)(X_{t+s} - mu)].

Densidad espectral:

    g(w) = suma_{s=-inf}^{inf} R(s) cos(w s)

Varianza asintótica de la media muestral:

    sigma^2 = suma_{s=-inf}^{inf} R(s) = g(0)

## 2. Teorema 3.1 de PW2004 (debido a Lahiri 1999)

CONDICIONES. E|X_t|^{6+d} < inf y suma_k k^2 alpha_X(k)^{d/(6+d)} < inf
para algún d > 0. Además b -> inf cuando N -> inf, PERO b = o(N^{1/2}).

Para el bootstrap estacionario (SB):

    Bias(sigma^2_{b,SB}) = -(1/b) G + o(1/b)          [PW2004 eq. 4]
    Var(sigma^2_{b,SB})  = (b/N) D_SB + o(b/N)        [PW2004 eq. 5]

con

    G = suma_{k=-inf}^{inf} |k| R(k)

Para el bootstrap circular (CB):

    D_CB = (4/3) g^2(0)

VALOR DE D_SB EN PW2004 (INCORRECTO, NO USAR):

    D_SB = 4 g^2(0) + (2/pi) integral_{-pi}^{pi} (1 + cos w) g^2(w) dw

Nordman (2008) halló un error en el cálculo de la varianza del bootstrap
estacionario hecho por Lahiri (1999). Como los resultados de PW2004 se
apoyaban en ese cálculo, D_SB quedó mal.

## 3. La corrección de 2009

PPW2009 enumera cinco correcciones. Textualmente:

1. El valor correcto de la constante de varianza D_SB definida en el
   Teorema 3.1 de PW2004 es

       D_SB = 2 g^2(0)

2. El Lema 2.1 (cota sobre la eficiencia relativa asintótica) se
   reemplaza por el valor exacto

       ARE_{CB/SB} = (2/3)^{2/3} = 0.7631428

   Esto sustituye la cota 0.331 <= ARE <= 0.481 del Lema 3.1 de PW2004.

3. Las ecuaciones (6) y (7) de PW2004 SIGUEN VALIENDO, siempre que se
   use la expresión correcta de D_SB.

4. La ecuación (8) de PW2004 se corrige a

       D_SB_hat = 2 g_hat^2(0)

5. Con la expresión corregida, la ecuación (9) de PW2004 da el estimador
   del largo esperado de bloque óptimo, y el Teorema 3.2 sigue siendo
   válido tal como está enunciado.

## 4. Fórmulas vigentes (2004 con la corrección de 2009)

MSE asintótico del estimador de varianza bajo SB:

    MSE(sigma^2_{b,SB}) = G^2 / b^2 + D_SB * b / N + o(b^{-2}) + o(b/N)

Minimizando en b:

    b_opt,SB = (2 G^2 / D_SB)^{1/3} * N^{1/3}          [PW2004 eq. 6]

MSE óptimo alcanzado:

    MSE_opt,SB ~= (3 / 2^{2/3}) * G^{2/3} * D_SB^{2/3} / N^{2/3}
                                                        [PW2004 eq. 7]

## 5. Estimación: ventana flat-top

G y g(0) son desconocidos. PW2004 propone estimarlos con la ventana
flat-top de Politis-Romano (1995), que aprovecha el decaimiento rápido
de R(k) y alcanza la mejor tasa de convergencia posible.

Ventana trapezoidal, simétrica en cero:

    lambda(t) = 1              si |t| en [0, 1/2]
    lambda(t) = 2 (1 - |t|)    si |t| en (1/2, 1]
    lambda(t) = 0              en otro caso

Autocovarianza muestral:

    R_hat(k) = N^{-1} * suma_{i=1}^{N-k} (X_i - Xbar_N)(X_{i+k} - Xbar_N)

    OJO: el divisor es N, no N-k.

Estimadores enchufados:

    G_hat = suma_{k=-M}^{M} lambda(|k|/M) * |k| * R_hat(k)   [PW2004 eq. 8]

    g_hat(w) = suma_{k=-M}^{M} lambda(|k|/M) * R_hat(k) * cos(w k)

    D_SB_hat = 2 * g_hat^2(0)          [corregido por PPW2009 punto 4]

    D_CB_hat = (4/3) * g_hat^2(0)      [PW2004 eq. 13]

Estimador final del largo esperado de bloque:

    b_opt_hat,SB = (2 G_hat^2 / D_SB_hat)^{1/3} * N^{1/3}   [PW2004 eq. 9]

## 6. Forma simplificada

Sustituyendo D_SB_hat = 2 g_hat^2(0) en la ecuación (9):

    b_opt_hat,SB = (2 G_hat^2 / (2 g_hat^2(0)))^{1/3} * N^{1/3}
                 = (G_hat^2 / g_hat^2(0))^{1/3} * N^{1/3}
                 = |G_hat / g_hat(0)|^{2/3} * N^{1/3}

El argumento 2 G_hat^2 / D_SB_hat es siempre no negativo, así que el
valor absoluto queda implícito y no hay riesgo de raíz de un negativo.

INVARIANCIA A LA NORMALIZACIÓN. Si en lugar de autocovarianzas R_hat(k)
se usan autocorrelaciones rho_hat(k) = R_hat(k)/R_hat(0), entonces tanto
G_hat como g_hat(0) quedan divididos por R_hat(0). El cociente
G_hat/g_hat(0) no cambia, y por lo tanto b_opt_hat tampoco. Ambas
implementaciones son equivalentes.

## 7. Elección del ancho de banda M

PW2004 recomienda M = 2m, donde m es el menor lag a partir del cual el
correlograma es despreciable.

Formalización (PW2004, nota al pie c, atribuida a Politis 2001):

    m = menor entero positivo tal que

        |rho_hat(m + k)| < c * sqrt(log10(N) / N)

    para todo k = 1, ..., K_N.

    Valores prácticos recomendados:  c = 2
                                     K_N = max(5, sqrt(log10 N))

    Luego:  M = 2m

El logaritmo es en base 10.

Justificación de M = 2m: es una forma empírica de obtener la constante
óptima A en M ~ A log N (Teorema 3.2 ii), y se adapta automáticamente a
distintas estructuras de correlación. Si R(k) decae polinomialmente, m
crece a tasa polinómica. Si R(k) = 0 para k > q (modelo MA(q)), entonces
m converge en probabilidad a q. La receta M = 2m sólo es aplicable con
ventanas flat-top; no funciona con ventanas tradicionales.

## 8. Teorema 3.2: tasas de convergencia

Bajo las condiciones del Teorema 3.1:

  (i)   Si suma_s |s|^{r+1} |R(s)| < inf para un entero positivo r,
        tomando M proporcional a N^{1/(2r+1)}:

            b_opt_hat = b_opt (1 + O_P(N^{-r/(2r+1)}))

  (ii)  Si R(k) decae exponencialmente, tomando M ~ A log N:

            b_opt_hat = b_opt (1 + O_P(log N / sqrt(N)))

  (iii) Si R(k) = 0 para k > q, tomando M = 2q:

            b_opt_hat = b_opt (1 + O_P(1 / sqrt(N)))

## 9. Desempeño reportado en PPW2009

Simulaciones re-corridas con el D_SB corregido, 1000 series AR(1)
X_t = phi X_{t-1} + Z_t con Z_t iid N(0,1).

Largos de bloque teóricos óptimos (Tabla 1):

    phi =  0.7,  N = 200  ->  b_opt,SB = 11.47
    phi =  0.7,  N = 800  ->  b_opt,SB = 18.20
    phi =  0.1,  N = 200  ->  b_opt,SB =  2.01
    phi =  0.1,  N = 800  ->  b_opt,SB =  3.20
    phi = -0.4,  N = 200  ->  b_opt,SB =  5.66
    phi = -0.4,  N = 800  ->  b_opt,SB =  8.99

Media de b_opt_hat / b_opt (Tabla 2):

    phi =  0.7,  N = 200  ->  0.859   (sd 0.342)
    phi =  0.7,  N = 800  ->  0.927   (sd 0.244)
    phi =  0.1,  N = 200  ->  0.959   (sd 0.943)
    phi =  0.1,  N = 800  ->  0.881   (sd 0.323)
    phi = -0.4,  N = 200  ->  1.062   (sd 0.644)
    phi = -0.4,  N = 800  ->  1.081   (sd 0.368)

Conclusión de los autores: los bloques estimados quedan en promedio
entre el 90 % y el 110 % del óptimo verdadero, y el RMSE se reduce
aproximadamente a la mitad al cuadruplicar el tamaño muestral.

## 10. Alcance: qué NO demuestra esta referencia

Esto es central para EdgeLab y hay que leerlo antes de citar PPW.

- El criterio optimizado es el MSE del ESTIMADOR DE VARIANZA
  sigma^2_{b,SB}. No es la cobertura de un intervalo de confianza.

- Ni PW2004 ni PPW2009 demuestran que un intervalo percentil construido
  con b_opt_hat alcance su nivel nominal en muestra finita.

- Usar b_opt_hat NO autoriza a suponer cobertura nominal. La cobertura
  hay que medirla por separado.

- El Teorema 3.1 exige b = o(N^{1/2}). Con N = 188 se tiene
  N^{1/2} ~= 13.7, mientras que el bloque estimado para la serie diaria
  ronda 14-15. La aplicación está en el borde del régimen asintótico
  para el que fueron derivadas las expansiones, o fuera de él.
  Esto debe declararse en el preregistro.

## 11. Correspondencia con la implementación

Archivo: edgelab/stats/bootstrap_estacionario.py

    _flat_top()                lambda(t) de la sección 5
    largo_de_bloque_optimo()   ecuación (9) con la corrección de 2009

Verificación algebraica (línea 103 y línea 106):

    D = 2.0 * s * s            con s = suma w(k) rho_hat(k) = g_hat(0)
    b = (2 G^2 / D)^{1/3} * n^{1/3}
      = |G / g_hat(0)|^{2/3} * n^{1/3}

Coincide con la sección 6. La implementación usa autocorrelaciones; por
la sección 6 eso es equivalente.

Comportamiento verificado en ejecución el 2026-07-28:

    AR(0.8), n = 200  ->  b_opt = 14
    ruido blanco      ->  b_opt = 6

El primero es consistente con la Tabla 1 de PPW2009 (11.47 para phi=0.7,
n=200; 0.8 tiene más dependencia, así que 14 es razonable).

## 12. Decisiones de implementación NO presentes en las fuentes

Estas líneas no provienen de PW2004 ni de PPW2009. Son decisiones del
repositorio y deben tratarse como tales: no se pueden citar como
"según Politis-White".

  linea 81-82   Si n < 8, devolver 1.
                Los papers no especifican un mínimo.

  linea 84      max_lag = min(n-2, ceil(sqrt(n)) + K_N + 20).
                El límite superior de lags no está en los papers.

  linea 88-92   m = k - 1 donde k es el primer lag tal que los K_N lags
                siguientes están bajo el umbral.
                Esto SÍ coincide con la nota al pie c de PW2004.
                Pero permite m = 0, mientras que el paper dice
                "menor entero POSITIVO".

  linea 93-94   Si ningún lag cumple el criterio, m = max_lag // 2.
                Este fallback NO está en los papers.

  linea 95-96   M = max(2m, 2) y M = min(M, max_lag).
                El piso de 2 y el techo no están en los papers.

  linea 104-105 Si D <= 0 o G no es finito, devolver 1.
                No está en los papers.

  linea 109     b acotado a [1, n // 3].
                No está en los papers. Nótese que n/3 es mucho más
                laxo que la condición b = o(N^{1/2}) del Teorema 3.1.

PENDIENTE DE VERIFICAR: que autocorrelaciones() use divisor N y no N-k
en R_hat(k), conforme a la sección 5.

## 13. Consecuencia para la batería de cobertura

tools/bateria_cobertura_bootstrap.py etiqueta una columna como "pw2004"
y declara "ppw2009 NO DISPONIBLE - falta la errata de 2009 en el repo".

Ambas cosas quedan obsoletas con este documento:

- La columna "pw2004" ya calcula la fórmula corregida de 2009.
  Debe renombrarse a "ppw2009".

- El mensaje de no disponibilidad debe eliminarse: la errata está ahora
  en el repositorio, en este archivo.

- No existe una comparación "PW2004 vs PPW2009" que hacer, porque el
  repositorio nunca implementó la versión de 2004. La comparación real
  es bloque fijo vs PPW 2009.

