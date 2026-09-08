# Pre-registro — H-CLUSTER-NQ: comportamiento del precio frente a clusters HFT

> **Familia:** `H-CLUSTER-NQ`. Instrumento: **NQ**, CME. Registrada antes de medir.
> **NORTH STAR:** `docs/NORTH_STAR.md`, sha256 del cuerpo
> `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
> (verificado por `tests/test_north_star_hash.py`, 3 passed, 2026-09-07).
> **Estado:** escrito **antes** de mirar ninguna relación entre precio y cluster.
> **Holdout:** 2026-07-01 → 2026-12-31, intacto y fuera de alcance.

---

## 1. Las hipótesis, tal como las planteó Nico

- **H1 — atracción.** *Si el precio viene desde una distancia alejada y se acerca a un
  cluster, probablemente ingrese a él, a comerciar y rebalancear.*
- **H2 — rechazo.** *El precio rechaza los extremos de un cluster.*

No compiten: **H1 es el canal no direccional** (¿llega?) y **H2 el direccional** (¿qué
hace al llegar?). Se miden juntas por obligación del proyecto: un efecto que empuja en
las dos direcciones promedia exactamente cero si sólo se mira el canal direccional.

## 2. Justificación económica

Si un cluster concentra inventario que necesita rebalanceo, el precio que se acerca
tiene contraparte esperándolo, y eso produce dos cosas medibles: mayor probabilidad de
alcanzarlo que la de un nivel arbitrario a la misma distancia (H1), y una reacción
asimétrica en su borde (H2). Si ninguna de las dos aparece, el cluster es una marca
sobre el gráfico sin contraparte detrás.

## 3. Cómo podría refutarse

- **H1** muere si la frecuencia de toque no supera a la de un nivel-placebo emparejado
  en distancia, instante y volatilidad local. Es el control que mató a la línea del 6E.
- **H2** muere si, condicionado a tocar el borde, la probabilidad de rechazo no difiere
  de la del placebo.
- **Las dos** mueren si el efecto desaparece al condicionar por la intensidad previa
  (el cluster nace donde ya hubo actividad).

## 4. El espacio de eventos, enumerado antes de congelar la población

Regla del proyecto: *ninguna población se congela sin enumerar antes, por escrito, el
espacio del que se la extrae*. Sobre un cluster existen al menos:

| # | Evento o estado | ¿Se mide? |
| :-- | :-- | :-- |
| 1 | Nacimiento del cluster | contexto, no población |
| 2 | **Aproximación** desde `d ≥ D_min` | **SÍ — población de H1** |
| 3 | Primer toque del **borde** | **SÍ — población de H2** |
| 4 | Toque del **POC** | desenlace de H1 |
| 5 | Toque n-ésimo | no en esta campaña |
| 6 | Expansión / fusión | covariable |
| 7 | Invalidación, agotamiento, expiración | riesgos competitivos |
| 8 | Confluencia con otro cluster | no en esta campaña |
| 9 | **Estado continuo** (distancia por barra) | **SÍ — canal no direccional** |

Se declaran las dos unidades. **Evento** (aproximación → desenlace) para la inferencia
primaria: cada observación es condicionalmente independiente. **Estado** (distancia por
barra) para la dinámica: mucho más N, pero fuertemente autocorrelacionado, así que su
inferencia va con bootstrap por bloques y su N efectivo es mucho menor que el nominal.
Reportar el N nominal del panel como si fuera N independiente sería la trampa de
potencia más común.

## 5. Estimands

**H1.** `Δ_toque = P(tocar el POC en h barras | d, σ_t, cluster activo) − P_placebo(d, σ_t, h)`,
con `P_null` browniano `2·(1 − Φ(d/(σ_t·√h)))` como referencia adicional, **condicional a
la volatilidad local** — con σ global, un cluster nacido en régimen de alta σ "atrae"
sólo por eso.

**H2.** `Δ_rechazo = P(salir del rango sin alcanzar el POC en k barras | tocó el borde)
− P_placebo`.

**No direccional.** Distribución completa de `Δdistancia` por barra con cluster activo,
contra la misma distribución en el placebo. Se publica la distribución, no sólo la media.

## 6. Controles, heredados del cierre del 6E

Tres, y los tres se corren desde el primer escalón:

1. **Espejo geométrico** — el cluster reflejado respecto del precio, a `−d`.
2. **Placebo sin cluster** — mismo instante, misma `d`, mismo ancho de banda, misma
   `σ_t`, en un nivel donde no hay cluster. Se excluyen placebos que colisionen con un
   cluster real.
3. **Sello genérico** — un nivel marcado por una vela extrema cualquiera. Si sella tan
   bien como el cluster, el detector no aporta nada por encima de un marcador barato.

En el 6E, (1) daba positivo y (2) lo mataba. Ése es el orden en que se van a mirar.

## 7. Presupuesto de multiplicidad, declarado antes

El espacio de configuración del instrumento es grande: modo de peso (3) × umbral de
volumen (3) × σ (3) × densidad mínima (4) = **108 configuraciones**, y eso antes de
tocar `D_min`, `h` o `k`.

**Decisión: la configuración del instrumento se congela con un criterio target-free,
antes de mirar nada relacionado con el precio.** El criterio es el contrato del repo
(turnover < 5 % ante ±1 de volumen en dos tercios de los ticks) más no-degeneración.

> **ENMENDADO el 2026-09-07 — ver `docs/research/ENMIENDA_P72_2026-09-07.md`.**
> La banda original de no-degeneración decía «cobertura media as-of entre 15 % y 60 %».
> Se fijó sin conocer la escala del objeto y las 108 mediciones dieron como máximo
> 9,6 %, con lo que **ninguna configuración pasaba**. Texto vigente: *existe el objeto
> (≥ 20 clusters por sesión) y no lo cubre todo (cobertura < 60 %)*. El criterio de
> estabilidad no se modificó. Ese barrido **no gasta
presupuesto estadístico**, porque no mira el precio futuro.

De ahí sale **una** configuración congelada. H1 y H2 se miden sobre esa sola. Si ninguna
configuración pasa el criterio target-free, la campaña **no arranca** — y ése es un
resultado, no un fracaso.

Los parámetros de medición que quedan (`D_min`, `h`, `k`) se fijan a un valor por
argumento previo, y su sensibilidad se reporta como diagnóstico, no como selección.

## 8. MDE, calculado antes de correr

Para una proporción, con `n` eventos de aproximación, potencia 0,8 y α bilateral
corregido por Bonferroni sobre el número de celdas declaradas:

    MDE ≈ (z_{1−α/2} + z_{0,8}) · √(2·p̄·(1−p̄)/n_ef)

con `n_ef = n / deff` y `deff = 1 + (m−1)·ICC` por la agrupación en sesiones. Se publica
`MDE` junto a **todo** resultado nulo: un nulo sin MDE no distingue ausencia de efecto de
falta de potencia.

Se calcula y se escribe **antes** de ver el resultado.

## 9. Qué NO se hace en esta campaña

- **Nada de P&L.** Ni entradas, ni salidas, ni sizing, ni costos. Medir valor económico
  exige el STOP del proyecto con manifiesto aparte, y no se llega ahí hasta que la
  información condicional esté demostrada.
- **No se abre el holdout.** Las tres sesiones de trabajo son de mayo 2026 sobre
  `NQ 06-26`; el firewall arranca el 2026-07-01 y las herramientas lo rechazan por
  construcción.
- **No se transporta** nada a ES, GC, ZB ni 6E. Cada instrumento estima lo suyo.

## 10. Estado de las precondiciones

| Precondición | Estado |
| :-- | :-- |
| Paridad del motor de zonas | **EXACT**, 7.494/7.494, 20 campos (`docs/parity_coverage/HFTZonesNQ.md`) |
| Censo de zonas | hecho (`docs/research/CENSO_ZONAS_NQ_2026-09-07.md`) |
| Estabilidad del instrumento | **en curso** — es lo que congela la configuración |
| Pre-registro | este documento |
| Manifiesto de campaña con STOP | no aplica todavía (no hay P&L) |

---

**Aporte al referente:** fija estimands, población, controles, MDE y presupuesto de
multiplicidad antes de la primera medición sobre el precio, y traslada la elección de
configuración a un criterio que no consume muestra — que es la forma concreta de
maximizar la probabilidad de que un resultado positivo, si aparece, sea real.
