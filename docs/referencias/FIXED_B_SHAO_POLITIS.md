[# Referencia: inferencia fixed-b calibrada por p-valor (Shao-Politis 2013)

Este documento baja al repositorio las ecuaciones que necesita la
implementación de fixed-b, para que no haya que inventarlas ni consultar
una fuente externa. Incluye también la cota de cobertura de Huang-Shao
(2016), que es una restricción DURA sobre cuándo el método es aplicable.

## Fuentes

[SP2013] Shao, X. y Politis, D. N. (2013). "Fixed-b Subsampling and the
         Block Bootstrap: Improved Confidence Sets Based on p-Value
         Calibration". Journal of the Royal Statistical Society Series B
         75(1):161-184.
         Preprint: arXiv:1204.1035

[HS2016] Huang, Y. y Shao, X. (2016). "Coverage Bound for Fixed-b
         Subsampling and Generalized Subsampling for Time Series".
         Statistica Sinica 26:1499-1524.
         doi:10.5705/ss.2014.185t

[KV2005] Kiefer, N. M. y Vogelsang, T. J. (2005). "A New Asymptotic
         Theory for Heteroskedasticity-Autocorrelation Robust Tests".
         Econometric Theory 21:1130-1164.

[Lahiri2001] Lahiri, S. N. (2001). "Effects of block lengths on the
             validity of block resampling methods". Probab. Theory
             Related Fields 121:73-97.

[Shao2010] Shao, X. (2010). "A self-normalized approach to confidence
           interval construction in time series". JRSS-B 72(3):343-366.

Consultadas el 2026-07-28 en:
  https://arxiv.org/abs/1204.1035
  https://www3.stat.sinica.edu.tw/sstest/oldpdf/A26n48.pdf

## 1. El problema que resuelve

En subsampling y block bootstrap hay un parámetro de ancho de banda l_n
(largo de bloque, ancho de ventana). En la asintótica tradicional
"small-b" se exige

    l_n -> inf   y   b = l_n / n -> 0

y bajo esa condición el método es consistente, pero el efecto de b NO
aparece en la distribución límite de primer orden. En la práctica, dos
valores de b distintos dan resultados distintos, y la teoría no lo captura.

La asintótica "fixed-b" de Kiefer-Vogelsang mantiene b en (0,1] FIJO
cuando n -> inf. Distintos b dan distintas distribuciones límite, así
que el efecto del ancho de banda queda capturado a primer orden.

OBSERVACIÓN CENTRAL DE SP2013. Bajo fixed-b, Lahiri (2001) mostró que la
aproximación de subsampling y del moving block bootstrap ya NO es
consistente para la media muestral. La salida de SP2013 no es corregir
la distribución, sino estudiar la distribución límite nula del P-VALOR:

    small-b:  el p-valor tiende a U(0,1)
    fixed-b:  el p-valor tiende a una distribución que depende de b
              y que NO es U(0,1)

Como esa distribución es pivotal para un parámetro escalar, se puede
usar para CALIBRAR el nivel: donde el procedimiento small-b usa alpha,
el procedimiento fixed-b usa el cuantil alpha de la distribución límite.

## 2. Notación

    {X_t}_{t=1}^{n}   serie estacionaria observada
    theta = T(F)      parámetro de interés, en R^k
    theta_hat_n       estimador basado en las n observaciones
    l = b n           ancho de ventana de subsampling
    N = n - l + 1     cantidad de subventanas
    theta_hat_{j,j+l-1}   estimador sobre la subventana que arranca en j
    W(t)              movimiento browniano estándar en [0,1]
    W_k(t)            vector de k brownianos independientes

## 3. Caso media, alternativa de una cola

Subventanas:

    Xbar_{j,j+l-1} = l^{-1} suma_{i=j}^{j+l-1} X_i,   j = 1, ..., N

Distribución de subsampling:

    L_{n,l}(x) = N^{-1} suma_{j=1}^{N}
                 1{ sqrt(l) (Xbar_{j,j+l-1} - Xbar_n) <= x }

Valores críticos:

    c_{n,l}(1-alpha) = inf{ x : L_{n,l}(x) >= 1-alpha }

P-valor para H1: mu > mu_0

    pval^SUB_{n,l} = N^{-1} suma_{j=1}^{N}
        1{ sqrt(n)(Xbar_n - mu_0) <= sqrt(l)(Xbar_{j,j+l-1} - Xbar_n) }

DISTRIBUCIÓN LÍMITE NULA BAJO FIXED-B. El p-valor converge en
distribución a G(b), donde

    G(b) = (1-b)^{-1} integral_{0}^{1-b}
           1[ W(1) <= { W(b+t) - W(t) - b W(1) } / sqrt(b) ] dt

El parámetro de escala sigma se CANCELA en G(b). Por eso G(b) es
pivotal para un b dado.

Sea G_alpha(b) el cuantil 100*alpha% de G(b). Entonces se rechaza H0 a
nivel alpha si el p-valor realizado es menor que G_alpha(b).

Intervalo de una cola por inversión del test:

    { mu : pval >= G_alpha(b) }
      = [ Xbar_n - n^{-1/2} c_{n,l}(1 - G_alpha(b)) , +inf )

La otra cola:

    ( -inf , Xbar_n - n^{-1/2} c_{n,l}(G_alpha(b)) ]

Intervalo bilateral de colas iguales:

    [ Xbar_n - n^{-1/2} c_{n,l}(1 - G_{alpha/2}(b)) ,
      Xbar_n - n^{-1/2} c_{n,l}(    G_{alpha/2}(b)) ]

LA ÚNICA DIFERENCIA con el procedimiento small-b es que alpha se
reemplaza por G_alpha(b). Nótese que alpha es exactamente el cuantil
100*alpha% de U(0,1), que es la distribución límite del p-valor bajo
small-b. La calibración es literalmente esa sustitución.

## 4. Caso media, versión simétrica

Distribución de subsampling del valor absoluto:

    L_tilde_{n,l}(x) = N^{-1} suma_{j=1}^{N}
                       1( sqrt(l) |Xbar_{j,j+l-1} - Xbar_n| <= x )

    c_tilde_{n,l}(1-alpha) = inf{ x : L_tilde_{n,l}(x) >= 1-alpha }

P-valor:

    pval_tilde^SUB_{n,l} = N^{-1} suma_{j=1}^{N}
        1{ sqrt(n)|Xbar_n - mu_0| <= sqrt(l)|Xbar_{j,j+l-1} - Xbar_n| }

Distribución límite nula bajo fixed-b: G_tilde(b), donde

    G_tilde(b) = (1-b)^{-1} integral_{0}^{1-b}
        1{ |W(1)| <= |W(b+t) - W(t) - b W(1)| / sqrt(b) } dt

Intervalo simétrico de nivel 100(1-alpha)%:

    [ theta_hat_n - n^{-1/2} c_tilde_{n,l}(1 - G_tilde_alpha(b)) ,
      theta_hat_n + n^{-1/2} c_tilde_{n,l}(1 - G_tilde_alpha(b)) ]

## 5. Parámetro finito-dimensional general (Teorema 1 de SP2013)

Este es el caso que aplica a EdgeLab, porque el estimando NO es una
media simple sino un funcional del tipo theta = T(F).

Expansión por función de influencia:

    T(rho_{1,n}) = T(F) + n^{-1} suma_{t=1}^{n} IF(X_t; F) + R_{1,n}

    IF(x; F) = lim_{eps -> 0+}
               [ T((1-eps)F + eps*delta_x) - T(F) ] / eps

SUPUESTOS.

  (A.1)  E{IF(X_j; F)} = 0  y
         n^{-1/2} suma_{j=1}^{floor(nr)} IF(X_j; F)
             => Sigma(P)^{1/2} W_k(r)
         con Sigma(P) definida positiva.
         Es un teorema central del límite FUNCIONAL para el proceso de
         sumas parciales de la función de influencia.

  (A.2)  sqrt(n) ||R_{1,n}|| = o_p(1)   y
         sqrt(l) sup_{j=1..N} ||R_{j,j+l-1}|| = o_p(1)
         Es decir, los restos son despreciables, también sobre las
         subventanas, que son más cortas.

P-valor general (norma ||.|| en R^k):

    pval_tilde^SUB_{n,l} = N^{-1} suma_{j=1}^{N}
        1( ||sqrt(n)(theta_hat_n - theta)||
           <= ||sqrt(l)(theta_hat_{j,j+l-1} - theta_hat_n)|| )

TEOREMA 1. Bajo (A.1) y (A.2), con b en (0,1] fijo, la distribución
límite nula del p-valor es la de G_tilde(b;k):

    G_tilde(b;k) = (1-b)^{-1} integral_{0}^{1-b}
        1[ ||Sigma^{1/2} W_k(1)||
           <= ||Sigma^{1/2} { W_k(b+t) - W_k(t) - b W_k(1) }|| / sqrt(b)
         ] dt

    con Sigma = Sigma(P) = suma_{j=-inf}^{inf} cov(IF(X_0;P), IF(X_j;P))

CASO k = 1. G_tilde(b;1) = G_tilde(b). Sigma es un escalar y se cancela.
LA DISTRIBUCIÓN ES PIVOTAL. Se usa directamente el cuantil simulado.

CASO k >= 2. G_tilde(b;k) depende de la matriz de varianza de largo
plazo Sigma, que es desconocida. NO ES PIVOTAL. Hay que usar el
procedimiento de doble subsampling de la Sección 3.1 de SP2013.

Intervalo simétrico para k = 1:

    [ theta_hat_n - n^{-1/2} c_tilde_{n,l}(1 - G_tilde_alpha(b)) ,
      theta_hat_n + n^{-1/2} c_tilde_{n,l}(1 - G_tilde_alpha(b)) ]

## 6. Versión moving block bootstrap

Se incluye por completitud; NO es el método elegido.

Con R_b = n/l = 1/b entero, el p-valor de una cola converge a H(b):

    H(b) = (1-b)^{-R_b}
           integral_0^{1-b} ... integral_0^{1-b}
           1[ suma_{h=1}^{R_b} { W(t_h + b) - W(t_h) } >= 2 W(1) ]
           dt_1 ... dt_{R_b}

Versión simétrica:

    H_tilde(b) = (1-b)^{-R_b}
        integral_0^{1-b} ... integral_0^{1-b}
        1( | suma_{h=1}^{R_b} { W(t_h+b) - W(t_h) } - W(1) | >= |W(1)| )
        dt_1 ... dt_{R_b}

Si 1/b no es entero se usa una fracción del último bloque remuestreado
para igualar el tamaño; SP2013 da la fórmula pero recomienda trabajar
con 1/b entero.

Nótese que H y H_tilde son integrales R_b-dimensionales. Con b = 0.08,
R_b = 12.5, no entero. Esta es una razón práctica adicional para
preferir SUBSAMPLING sobre MBB en nuestro caso.

## 7. Protocolo de simulación de los autores

De la Sección 3.1 de SP2013, para reproducibilidad:

  - Valores de alpha simulados: 0.05 y 0.10
  - Grilla de b: 0.01, 0.02, ..., 0.20
  - El browniano se aproxima con la suma parcial normalizada de
    5000 variables iid N(0,1)
  - 50000 réplicas Monte Carlo en todos los casos
  - Para H y H_tilde, la esperanza E* se aproxima con 50000 bootstraps
  - Se ajusta por mínimos cuadrados la cuadrática
        cv(b) = a_0 + a_1 b + a_2 b^2
    con el intercepto FORZADO a a_0 = alpha, de modo que cv(0) = alpha
  - R^2 de los ajustes entre 0.9584 y 0.9997

ADVERTENCIA DE LOS AUTORES. Para alpha chico (por ejemplo 0.01) y b
relativamente grande (0.15 a 0.20), los valores críticos simulados son
mayormente CERO, y no se puede dar una cuadrática ajustada. La Tabla 1
de SP2013 es útil para b en (0, 0.20].

Comportamiento esperado: cv(b) DECRECE con b desde cv(0) = alpha. Por
lo tanto el umbral calibrado es más exigente que alpha, y el intervalo
fixed-b resulta LEVEMENTE MÁS ANCHO que el small-b. Los autores lo
reportan explícitamente y es consistente con Kiefer-Vogelsang.

## 8. COTA DE COBERTURA (Huang-Shao 2016)

Esta sección es una restricción dura. Un intervalo fixed-b puede ser
INCAPAZ de alcanzar su nivel nominal, sin importar cómo se lo calibre.

Definir

    beta_n(b) = P( max_{j=1..N} |sqrt(l)(Xbar_{j,j+l-1} - Xbar_n)|
                   < sqrt(n)|Xbar_n - mu_0| )

con mu_0 el valor verdadero. Su límite:

    beta(b) = P( sup_{t in [0, 1-b]}
                 |W(b+t) - W(t) - b W(1)| / sqrt(b)  <  |W(1)| )

Entonces, para el intervalo small-b y también para el calibrado fixed-b:

    P(mu_0 en IC) <= 1 - beta_n(b)  ->  1 - beta(b)

Se llama a 1 - beta_n(b) la cota de cobertura en muestra finita y a
1 - beta(b) la cota límite.

RAZÓN. El intervalo nunca puede ser más ancho que el máximo de las
desviaciones de las subventanas. Si el estadístico real supera a TODAS
ellas, el valor verdadero queda afuera, pase lo que pase.

Además, beta(b) = P(G_tilde(b) = 0). De ahí:

    Si beta(b) > alpha:
        G_tilde_alpha(b) = 0, la desigualdad se vuelve IGUALDAD, y es
        IMPOSIBLE construir un intervalo con cobertura asintótica
        correcta a ese b. No hay calibración que lo arregle.

    Si beta(b) <= alpha:
        Se puede construir un intervalo asintóticamente válido, pero la
        cota en muestra finita para un n dado sigue sin conocerse y hay
        que medirla por simulación.

Bajo small-b el problema desaparece porque beta_n(b) ~= beta(0) = 0.
Bajo fixed-b, o con n chico, la cota es estrictamente menor que 1.

La subcobertura se agrava cuando:
  - la dimensión k del parámetro es grande
  - la dependencia de la serie es POSITIVA y FUERTE
  - b es grande

Caso vectorial:

    beta(b; d; Sigma) = P( sup_{r in [0,1-b]}
        ||Sigma^{1/2}(W_d(b+r) - W_d(r) - b W_d(1))|| / sqrt(b)
        < ||Sigma^{1/2} W_d(1)|| )

Para d = 1 no depende de Sigma.

REMEDIO PROPUESTO. Huang-Shao proponen el subsampling generalizado
(GS), que usa bloques de tamaños distintos e introduce un parámetro de
escala, combinando prepivoteo de SP2013 con los estimadores recursivos
de la self-normalization de Shao (2010). Los autores muestran que la
cota puede acercarse mucho a 1 si el parámetro de escala está en cierto
rango.

## 9. Consecuencias para EdgeLab

  1. El estimando es theta = suma u_d / suma v_d, un funcional T(F) con
     k = 1. Por el Teorema 1, la distribución límite del p-valor es
     PIVOTAL. No hace falta doble subsampling.

  2. Hay que verificar (A.1) y (A.2) para el estimador de razón, no
     darlos por sentados. La función de influencia de una razón de
     medias es
         IF(x) = ( u(x) - theta * v(x) ) / E[v]
     y hay que declararla.

  3. theta_hat sobre una subventana debe recomputarse desde las sumas
     de ESA subventana. Coincide con el invariante ya vigente en
     edgelab/stats/estimando_diario.py.

  4. DEGENERACIÓN. Una subventana de largo l puede no contener ningún
     día activo, y entonces theta_hat_{j,j+l-1} no está definido:
     suma v_d = 0. El módulo actual lanza SinDiasActivosError. Hay que
     declarar ANTES de correr qué se hace con esas subventanas, y la
     decisión debe estar en el preregistro. Descartarlas cambia N y por
     lo tanto cambia b efectivo.

  5. b = 0.08 con n = 188 da l = 15 y N = 174. Cae dentro de la grilla
     (0, 0.20] para la que SP2013 provee valores críticos.

  6. COMPUERTA OBLIGATORIA. Antes de implementar la inferencia hay que
     calcular beta(0.08) por simulación browniana y compararlo con
     alpha = 0.05. Si beta(0.08) > 0.05, fixed-b calibrado queda
     descartado a ese b. Usa el mismo generador browniano que el
     método, así que es barato.

  7. Preferir SUBSAMPLING sobre MBB: con b = 0.08, R_b = 12.5 no es
     entero, y H(b) es una integral de dimensión 12 o 13.

  8. DEFINICIONES. Con D(t) = W(b+t) - W(t) - b*W(1), t en [0, 1-b]:

        G_tilde(b) = (1-b)^-1 ∫ 1{ |W(1)| <= |D(t)|/sqrt(b) } dt   simétrico
        G(b)       = (1-b)^-1 ∫ 1{  W(1) <=  D(t)/sqrt(b) } dt     una cola superior

        La tercera opción, bilateral con colas iguales, requiere G_{alpha/2}(b).

  9. DECLARACIÓN. EXPLORE-001 usa G(b), una cola superior. La constante de
     calibración es cuantil_G(b, alpha). NO cuantil_G_sim.

        Fundamento: la pregunta científica es "¿theta > theta_BE?", unilateral
        por construcción, y el arnés inferencial ya declara p-valor de una cola.
        La opción de colas iguales se rechaza además porque exige una constante
        nunca computada ni validada contra la compuerta.

  10. DESAJUSTE REGISTRADO. La compuerta de Huang-Shao se ejecutó en c009009
      sobre beta = P(G_sim = 0), es decir sobre el funcional simétrico, que no
      es el que usará la inferencia. Recomputado sobre el funcional correcto
      (50.000 réplicas, semilla 20260801):

        b=0.0800 (grilla 5000)  beta_sim=0.01664  beta_1cola=0.01492  ic_inf=0.013687
        b=0.0761 (grilla 4925)  beta_sim=0.01546  beta_1cola=0.01352  ic_inf=0.012347
        b=0.0812 (grilla 4925)  beta_sim=0.01720  beta_1cola=0.01440  ic_inf=0.013189

      El funcional de una cola degenera MENOS. El APTO se mantiene contra
      alpha=0.05 y la prohibición del intervalo al 99% se mantiene porque
      ic_inf > 0.01 en los tres casos, por Clopper-Pearson exacto con delta=0.01.

  11. ADVERTENCIA OBLIGATORIA. El margen relativo sobre 0.01 cae de 53% (valor
      citado sobre el simétrico) a entre 23,5% y 36,9%. Queda PROHIBIDO seguir
      citando el 53%. La prohibición del 99% es dependiente de b: una vez sellado
      n, hay que recomputar ic_inf al b definitivo antes de preregistrar el nivel
      de confianza.

  12. PROCEDENCIA. Estos valores provienen de una verificación externa
      independiente, NO del módulo edgelab/stats/fixed_b.py, que hoy sólo
      computa el funcional simétrico. Marcalos explícitamente como "pendientes
      de reproducción en módulo". La reproducción va en el commit de migración
      de GRILLA.

  13. DEUDA ABIERTA que debe quedar escrita: el commit 5 debe incluir un test
      que falle si el intervalo se construye con cuantil_G_sim. Ambas funciones
      seguirán existiendo -- G_sim es necesaria para la compuerta -- así que el
      riesgo de tomar la equivocada es permanente.

