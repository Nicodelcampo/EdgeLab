# AVCL-CIERRE — resultados MNQ — 2026-10-06

- Manifiesto: `AVCL_CIERRE_MANIFIESTO_20261006.md`.
- Kernels `edgelab-avcl-grid-mnq-k1..k4` (13 celdas + delta) + `edgelab-avcl-cierre-20261006`.
- JSON: `avcl_vol1_20261005/AVCL_CIERRE_RESULTADOS.json`. 8 pruebas, familia `AVCL_CIERRE`.

## Formal (8, Holm, bilaterales)
| prueba | resultado | Holm |
|---|---|---|
| Delta, media de s_d H10, AT | −0,006 (MDE 0,019) | 1 |
| Delta, media de s_d H10, OFF | +0,008 (MDE 0,016) | 0,71 |
| Delta, cola s_d ≥ 1R, AT | +1,87 pp | <1e-4 |
| Delta, cola s_d ≥ 1R, OFF | +1,81 pp | <1e-4 |
| Asimetría regreso − alejamiento, Q5 de anomalía, OFF H10 | **+1,74 pp** (MDE 1,84) | **0,041** |
| 200t, AT `y_rg` H10 A2 | **+0,065** (MDE 0,048) | 0,0009 |
| 200t, OFF cola de alejamiento H10 | +0,23 pp | 1 |
| 200t, OFF cola de regreso H10 | +0,38 pp | 1 |

### Corrección de diseño (delta): **el delta NO orienta la expansión**
Las pruebas de "cola s_d ≥ 1R" quedaron **mal planteadas en el manifiesto**: miden una sola cola, y DIST ya había
mostrado que la expansión engorda **las dos** colas (+1,1 pp cada una en OFF, unos +1,9 pp por lado en AT). Una cola
que sube +1,8 pp es la expansión bidireccional, no dirección. La prueba que responde la pregunta es la **media** de
s_d, y da ≈ 0 en AT y en OFF, con MDE chicos. Los quintiles de |dnorm| tampoco muestran gradiente. El delta coincide con
el lado de la zona en el 53 % de los casos (casi azar).
**Conclusión: el delta de la zona no da dirección.** La significancia de las colas se registra, pero no se interpreta
como dirección. La prueba correcta, para cualquier repetición, es cola(dirección) − cola(opuesta).

### Asimetría de regreso: confirmada, chica
En las zonas OFF de más anomalía (Q5), la probabilidad de volver más de 1R hacia la zona supera a la de alejarse en
+1,7 pp (Holm 0,041, justo en el MDE). Es el primer **indicio direccional** de toda la familia: en alta anomalía, el
precio tiende a volver. Es débil y necesita réplica (200t, otros instrumentos).

### 200t
La expansión de rango se replica (AT A2 +0,065). Las colas de OFF en 200t son ≈ 0 (MDE 1,0–1,3 pp), con muestra 4 veces
menor: replica el rango, no la forma de las colas.

## Grilla de sensibilidad (13 celdas, descriptiva, sin elegir)
β `y_rg` H10, RTH. A1 = controles comunes; A2 = contra volumen alto sin zona.

| celda | AT A1 | AT A2 | OFF A1 | OFF A2 | colas OFF (alej / reg) |
|---|---|---|---|---|---|
| base p95 W10 k2 | 0,081 | 0,054 | 0,055 | 0,072 | 1,1 / 1,1 pp |
| p90 | 0,066 | 0,040 | 0,034 | 0,047 | 0,7 / 0,7 |
| **p98** | 0,094 | 0,067 | 0,079 | 0,090 | 1,6 / 1,6 |
| W5 | 0,030 | 0,039 | 0,049 | 0,071 | 1,2 / 1,0 |
| **W20** | **0,250** | 0,269 | **−0,046** | −0,034 | −0,7 / −0,7 |
| **k1,5** | **0,115** | 0,097 | **0,088** | 0,101 | 2,0 / 1,8 |
| **k3,0** | 0,012 | 0,001 | −0,010 | 0,003 | ≈0 |
| m4 | 0,078 | 0,043 | 0,052 | 0,063 | 1,0 / 1,0 |
| 200t | 0,076 | 0,065 | 0,041 | 0,034 | 0,2 / 0,4 |
| p90W5 | 0,021 | 0,031 | 0,031 | 0,056 | 0,6 / 0,6 |
| p90W20 | 0,245 | 0,254 | −0,049 | −0,045 | −0,7 / −0,5 |
| p98W5 | 0,037 | 0,045 | 0,067 | 0,080 | 1,7 / 1,0 |
| p98W20 | 0,265 | 0,275 | −0,039 | −0,027 | −1,1 / −0,6 |

Lectura:
- **El efecto NO es universal en la grilla.** Positivo y estable en las celdas de W5/W10, más fuerte con percentil
  más exigente (p98) y con multiplicador más bajo (k1,5). **Desaparece con k3,0.**
- **W20 es sospechoso de artefacto de medición:** AT salta a +0,25 y OFF se vuelve negativo. Con un bloque de 20 barras
  y una ventana previa de 10, la ventana "previa" de `y_rg` queda **dentro** del bloque creador. La condición AT (cierre
  dentro del cluster) selecciona finales de bloque comprimidos y agranda el cociente mecánicamente. **No se interpreta
  W20** hasta medir con una ventana previa anterior al bloque.
- Ese mismo riesgo existe, más chico, en la base (W10 = H10: la ventana previa es exactamente el bloque, igual en
  eventos y controles). Queda como **verificación pendiente**: repetir VOL-1/2 con la ventana previa desplazada antes
  del bloque.

## Estado de la familia aVolClusterPOI (cierre)
- **Establecido:**
  - expansión de rango corta (≈10 barras), bidireccional, propia de la zona (supera al volumen alto);
  - dosis monótona; la zona angosta expande más; luego compresión;
  - estable entre contratos y franjas; ETH; replica en 200t (rango).
- **Sin dirección:** ni por lado, ni por delta, ni por la media de colas. Única excepción: el regreso leve en alta
  anomalía (+1,7 pp, por replicar).
- **Frágil a parámetros:** depende de k y W. k1,5 y p98 lo refuerzan; k3,0 lo anula; W20 queda pendiente de una
  medición limpia.
- **Pendiente antes de construir encima:**
  - (1) ventana previa fuera del bloque (descarta el artefacto de medición);
  - (2) réplica en otros instrumentos;
  - (3) contexto por estado de mercado;
  - (4) traducción a algo operable (volatilidad / stops), con STOP y manifiesto.
