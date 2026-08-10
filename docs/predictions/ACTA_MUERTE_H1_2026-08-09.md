# ACTA DE MUERTE — H1 (BigTrap2, T=34, dirección nativa)

**Fecha** 2026-08-09 · **Sello ejecutado** `E-R1_v0.3.1_SELLO_2026-08-09.md`
**Artefactos** `runner_H1_outcomes__92e16c4fe51d.json` · `inferencia_H1__e8fd2b74ba47.json`
**Commits** `880c96c` (reparación) · `889c048` (primer cruce legítimo) · `5f1b65d` (veredicto)
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`

---

## 1. Veredicto

```
trade-weighted   -2,4685 ticks/evento
IC 99,9535 %     [-5,2370 , +4,9780]   contiene 0 -> GRIS
equal-weight     -2,9417 (sensibilidad; mismo signo, sin diferencia material)
```

**GRIS. Y el sello declara, antes de ver un número, que gris MUERE por defecto.**
H1 está muerta. No se reabre, no se reparametriza para salvarla, no se
reinterpreta.

Base: 201 sesiones (178 con eventos, 23 sin), 424 eventos, 848 precios leídos,
bloque PPW 2 sesiones, 20.000 réplicas, semilla 20260809.

---

## 2. El embudo — qué población se midió realmente

```
15.577  primeros toques post sep_min=120   (4 contratos 6E, 201 sesiones)
   755  con excursión k_T > 0 a T = 34 ticks          <- el filtro T tira el 95,15 %
   424  tras descongestionar sep_min=120  (f = 424/201 = 2,11 eventos/sesión)
```

**El filtro de excursión T=34 es el que define la población, no BigTrap2.** De
cada 100 zonas tocadas, 5 sobreviven al umbral. Ese es el hecho dominante del
diseño y no es un parámetro del indicador: es un parámetro de la hipótesis.

---

## 3. Diagnóstico económico — declarado DESPUÉS del veredicto

```
bruto      +0,2995 ticks/evento     (total +127 ticks)
fricción   -2,768  ticks/evento     (total -1.174 ticks)
neto       -2,4685 ticks/evento     (total -1.047 ticks)
```

**La fricción se come el bruto 9,2 veces.** No murió por ausencia de señal:
murió porque la señal es un orden de magnitud menor que su costo de ejecución.

---

## 4. El hallazgo estructural — esto es lo que sobrevive a H1

Desagregado por motivo de salida:

| salida | n | % | bruto medio | mediana | gana bruto | duración mediana |
|---|---|---|---|---|---|---|
| `close_through` | 394 | 92,9 % | −3,454 | −2,0 | **0 de 394 (0 %)** | **2 barras** |
| `fin_de_sesion` | 30 | 7,1 % | +49,600 | +39,0 | 29 de 30 (97 %) | 405 barras |

Ciclo de vida de la zona: `close_through` 385 · `close_through_gap` 22 ·
`max_age` 16 · sin dato 1. **El 96 % de las zonas muere por close-through.**

### Lo que esto significa

**Para el 92,9 % de la población, el primer toque y la muerte de la zona son
prácticamente el mismo evento** — mediana 2 barras entre uno y otro. Y el
close-through es, por construcción, el cierre del precio del lado adverso a la
operación nativa: de ahí que **ninguno de los 394 gane, ni uno**. No es un
resultado estadístico, es una identidad del diseño.

> «Primer toque post-`sep_min`» no selecciona rechazos de zona. **Selecciona
> rupturas.** Los 30 rechazos genuinos son el 7,1 % residual, y son los que
> aportan todo el bruto.

H1 pagó 424 peajes de 2,768 ticks para cobrar 30 boletos. Con ese reparto, el
bruto tendría que haber sido 9,2× mayor sólo para empatar.

---

## 5. Potencia del diseño — lo que H1 nunca pudo haber detectado

```
SE (HAC, lag 1)   1,0903 ticks      sd por evento 19,63 · design effect 1,14
```

El *design effect* de 1,14 dice que la dependencia serial casi no aporta: el
error es **varianza pura del pago**, producida por la estructura de lotería del
punto 4 (mediana −2, máximo +209).

| M_eff | z | MDE neto | bruto que habría hecho falta |
|---|---|---|---|
| ~106 (H1) | 3,50 | 3,82 | **6,58** |
| ~1.000 | 4,06 | 4,43 | 7,19 |
| ~10.000 | 4,57 | 4,98 | 7,75 |
| ~100.000 | 5,03 | 5,48 | 8,25 |

**El diseño sólo podía declarar VIVE con un bruto ≥ 6,58 ticks/evento. El
observado fue +0,30 — veintidós veces por debajo de su propio piso.**

Corolario incómodo y necesario: existe una **banda ciega** de brutos entre 2,768
(donde el neto ya es positivo) y 6,58 (donde recién se detecta). Un edge real de
4 ticks brutos habría muerto igual, indistinguible de cero.

---

## 6. Qué queda refutado y qué NO

**Refutado.** Esta celda concreta —BigTrap2 por defecto, `bar_spec` time:1,
T=34, orden B, `sep_min`=120, entrada al cierre de la barra de primer toque,
salida al close-through o fin de sesión, dirección nativa, 2,768 ticks de
fricción adentro— no produce expectativa neta positiva, y el punto estimado es
negativo.

**NO refutado, y es importante no confundirlo:**

1. **Que BigTrap2 no tenga información.** El diseño no podía distinguir un edge
   moderado de cero (punto 5). Ausencia de detección ≠ detección de ausencia.
2. **Que el espacio de parámetros sea estéril.** Se visitó **una** celda.
3. **Que las zonas no sirvan.** Los 30 rechazos genuinos promediaron +49,6 ticks
   brutos. Existe un techo de oráculo grande; lo que no hay es evidencia de que
   algo observable al momento de la entrada separe esos 30 de los otros 394.

**Lo que la muerte de H1 sí compra**, y no es poco: la regla de salida heredada
—«sostener hasta que la zona se invalide»— está estructuralmente sesgada a
perder, porque la invalidación *sólo ocurre en contra*. Cualquier hipótesis
futura que la reutilice arranca con el mismo defecto.

---

## 7. Higiene

- **Holdout intacto.** Ninguna lectura tocó 2026-07-01 → 12-31. `firewall_corte_iso`
  registrado en los tres artefactos.
- **Artefacto falso en cuarentena, no borrado**:
  `incidentes/INCIDENTE_artefacto_declaro_outcomes_sin_leer_precios__f078322ed851.json`.
- **Multiplicidad gastada**: 1 hipótesis del presupuesto declarado de 3. La
  holgura queda declarada y **no se aprovecha** para reinterpretar este
  resultado.

---

## Aporte al referente

Se cerró el primer ciclo completo de falsación con dinero simulado real: una
hipótesis preregistrada llegó a outcomes, murió por regla, y dejó dos cantidades
que antes no existían — **el piso de detección del diseño (6,58 ticks brutos) y
el peaje que hay que superar (2,768)**. La distancia hacia un edge neto no se
redujo por haber encontrado uno, sino porque ahora se sabe cuánta señal hace
falta, dónde se está perdiendo (la salida, no el indicador) y que la
multiplicidad es logarítmica y por lo tanto barata. Eso convierte la próxima
campaña en un problema de potencia y varianza, que es medible, en vez de un
problema de fe.
