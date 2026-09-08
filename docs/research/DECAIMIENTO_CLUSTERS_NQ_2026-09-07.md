# Decaimiento empírico de clusters HFT sobre NQ — primer resultado

> **Target-free.** Tres canales no direccionales. Sin P&L, sin dirección esperada.
> Reproducción: `tools/decaimiento_clusters_nq.py --sesiones 3`.
> Estimador: `edgelab/research/cluster_decay.py` (14 tests).
> Datos: `data/nt8_oracles/decaimiento_clusters_nq.json`.
> **Alcance: 3 sesiones de `NQ 06-26`, mayo 2026, pre-holdout.** Holdout intacto.

---

## Veredicto

**SIN EFECTO DETECTADO, NO CERRADO.** No hay curva de decaimiento que ajustar: el
contraste contra el placebo no decae con el consumo. Y el nivel del contraste tampoco es
positivo — si algo, el precio reentra al cluster **menos** que a una banda cualquiera a
la misma distancia.

Pero el MDE es **0,206** y los contrastes observados están en torno a **0,05**. La
medición no tiene potencia para descartar un efecto de ese tamaño. No se cierra nada.

## Qué se midió

Para cada cluster vivo, cada 5 barras, con el precio **afuera** y a 2–40 ticks: fracción
de capacidad consumida `c`, y qué hace el precio en las 20 barras siguientes. Cada
muestra apareada con un **placebo** del mismo ancho, a la misma distancia, del lado
opuesto, descartando los que colisionan con un cluster real.

| | |
| :-- | --: |
| sesiones | 3 |
| zonas | 24.143 |
| clusters | 122 |
| **muestras** | **690** |
| descartes por distancia fuera de \[2, 40\] | 471.212 |
| descartes por control inelegible | 19.783 |
| **MDE** (5 bins, Bonferroni, deff = 5) | **0,206** |

## Resultados

### Reentrada (¿el precio vuelve a entrar al rango?)

| consumo | n | real | placebo | contraste |
| :-- | --: | --: | --: | --: |
| 0,0–0,2 | 187 | 0,695 | 0,717 | −0,021 |
| 0,2–0,4 | 95 | 0,558 | 0,611 | −0,053 |
| 0,4–0,6 | 37 | 0,378 | 0,730 | −0,351 |
| 0,6–0,8 | 53 | 0,491 | 0,547 | −0,057 |
| 0,8–1,0 | 318 | 0,399 | 0,456 | −0,057 |

### Cruce (¿lo atraviesa de lado a lado?)

| consumo | n | real | placebo | contraste |
| :-- | --: | --: | --: | --: |
| 0,0–0,2 | 187 | 0,449 | 0,460 | −0,011 |
| 0,2–0,4 | 95 | 0,263 | 0,221 | +0,042 |
| 0,4–0,6 | 37 | 0,054 | 0,054 | 0,000 |
| 0,6–0,8 | 53 | 0,151 | 0,170 | −0,019 |
| 0,8–1,0 | 318 | 0,041 | 0,016 | +0,025 |

### Permanencia (barras dentro del rango, de 20)

| consumo | n | real | placebo | contraste |
| :-- | --: | --: | --: | --: |
| 0,0–0,2 | 187 | 4,29 | 5,42 | −1,12 |
| 0,2–0,4 | 95 | 3,94 | 5,14 | −1,20 |
| 0,4–0,6 | 37 | 3,32 | 7,54 | −4,22 |
| 0,6–0,8 | 53 | 5,02 | 4,25 | +0,77 |
| 0,8–1,0 | 318 | 3,14 | 3,92 | −0,78 |

## Lectura

**1. No hay decaimiento.** El contraste no cae monótonamente con `c`. Sube y baja sin
patrón, y el único bin que supera el MDE —el de 0,4–0,6 en reentrada, −0,351— es el
**más chico de todos** (n = 37). Es el aspecto que tiene el ruido.

Consecuencia directa sobre la pregunta que originó el módulo: **no hay una curva
empírica de decaimiento para copiar.** Bajo esta medición, consumir un cluster no cambia
el comportamiento del precio respecto de una banda cualquiera. Si eso se sostiene con
más potencia, el decaimiento óptimo sería *ninguno* — porque no habría nada que decaiga.

**2. El nivel del contraste tampoco favorece a la hipótesis.** La reentrada es negativa
en **los cinco bins**, y la permanencia en cuatro de cinco. El precio entra y se queda
en el cluster **menos** que en el placebo. Cinco de cinco con el mismo signo no es
casualidad obvia, pero tampoco es evidencia: los bins comparten clusters —el mismo
cluster aparece en varios a medida que se consume— así que no son independientes, y
todos los valores están dentro del MDE.

**Lo que no se puede decir:** que los clusters repelen al precio. **Lo que sí:** en esta
muestra no aparece atracción, y la dirección del residuo, si algo, va al revés.

**3. La potencia es el límite, y se sabe de dónde viene.** 471.212 pares
cluster-barra descartados por caer fuera de \[2, 40\] ticks: el 96 %. Los clusters pasan
la mayor parte del tiempo lejos del precio. Con 690 muestras el MDE es 0,206; para
detectar un contraste de 0,05 harían falta del orden de **10.000 muestras**, o sea unas
40 sesiones.

## Un defecto del motor que esta medición destapó

Para observar el consumo hay que **desactivar la invalidación dura**: con ella activa, el
99,4 % de los clusters muere perforado antes de consumirse y no existe población con `c`
alto.

Pero apenas se desactiva aparece la **canibalización**: el filtro de fusión excluye
`DEPLETED` e `INVALIDATED` y **no** `EXPIRED`, así que un cluster que no muere absorbe
todo lo que solapa y crece sin techo. Quedaban 40 clusters por sesión en vez de cientos.

Está corregido con `merge_excluye_expirados`, apagado por defecto —el default reproduce
el `.cs` certificado— y encendido en la configuración de campaña. El mecanismo lo
identificó el agente de Antigravity mirando el chart; acá estaba documentado como rareza
de paridad, con test propio, **sin haber sido conectado con su consecuencia**.

## Qué haría falta para cerrar

1. **Más sesiones.** 40 para llegar a MDE ≈ 0,05. Va a Kaggle, no a la máquina local.
2. **Declarar antes** si se ensancha la banda de distancia. Ensancharla después de ver
   estos números sería mover el arco.
3. El canal **direccional** (H2: rechazo en los extremos) todavía no se midió. Este
   módulo cubre los tres canales no direccionales.

---

**Aporte al referente:** contesta con datos la pregunta de cuál es el decaimiento
óptimo —no hay curva que ajustar en esta muestra— y publica el MDE que impide cerrarlo,
evitando que se calibre un mecanismo de decaimiento sobre ruido.
