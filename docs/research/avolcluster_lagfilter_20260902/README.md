# aVolClusterPOI — FASE 6: mecanismo confirmado (lag −1 + filtro Low/High)

Fecha: 2026-09-02 · commit pineado `706c4fe2` · CSV NT8 sha256 `81f32a97…f9da`
Kernel: `notebooks/kaggle/avolcluster_lagfilter/lagfilter_entry.py` (Kaggle)
Estado: `DIAGNOSTIC_NO_CODE_CHANGED`.

## Mecanismo propuesto

El perfil de NT8 se acumula **desfasado** respecto de la barra que lo cierra, y
`aVolClusterPOI.cs` (~319-330) descarta sin reasignar todo lo que queda fuera de
`[Low[0], High[0]]` de esa barra. El desfasaje **redistribuye** (explica el 21,5 %
de bloques donde NT8 tiene *más* volumen); el filtro **pierde** (explica el
déficit sistemático de FASE 5). Ninguno de los dos por separado explica ambas.

Barrido: fase de barra `p` × lag del perfil `L` × filtro on/off.

## Resultado

| variante | bloques exactos | % | vol NT8/py | ticks descartados |
|---|---:|---:|---:|---:|
| baseline `p0_L0_sinfiltro` (kernel actual) | 16 | 0,07 % | 0,99588 | 0 |
| `p0_L-1_sinfiltro` (sólo lag) | 2.118 | 9,41 % | 0,99588 | 0 |
| `p-1_L0` (sólo fase, FASE 4) | 1.958 | 9,01 % | 0,99578 | 0 |
| **`p0_L-1_filtro`** | **3.436** | **15,27 %** | **0,99640** | 15.239 |

Tres cosas a la vez:

1. **Los efectos son aditivos.** Lag solo 9,4 %, filtro solo 0 %, juntos 15,3 %.
   El filtro no hace nada sin el lag — que es exactamente lo que predice el
   mecanismo y lo que la FASE 3 midió cuando lo probó aislado.
2. **El ratio de volumen se reproduce**: 0,9964 obtenido contra 0,9959 medido de
   forma independiente en la FASE 5, con el filtro descartando 15.239 ticks.
   No estaba ajustado a ese número; salió solo.
3. **Los bloques con volumen exacto** suben de 3.148 a 4.526.

## Pero no es paridad

15,27 % deja el 85 % sin explicar. El mecanismo es correcto en su forma pero
incompleto en su parametrización: un lag **constante** de un tick es una
aproximación. La FASE 7 mide dónde vive el residuo.

## Cómo podría refutarse

Si el ratio de volumen reproducido se alejara del 0,9959 medido, o si `filtro`
mejorara también con `L=0`, el mecanismo sería una coincidencia numérica. No
ocurre: con `L=0` el filtro descarta 0 ticks y no cambia nada, en las tres fases
de barra probadas.
