# P-47 — marco para decidir el piso de sesiones (research, 2026-08-19)

- **Para:** Nico. Decidir **antes** de volver a la tabla de v2.
- **No es un umbral.** No elige 27, 50 ni 139 mirando celdas.
- **Firewall:** sin outcomes.

## Lo que dice la literatura (no el censo)

1. **La unidad es el cluster, no el evento.** Design effect
   `DEFF = 1 + (m − 1) ρ` (Donner & Klar). Un ICC chico con muchos
   eventos por sesión hincha el N. Con m = 80 y ρ = 0,05, DEFF ≈ 6:
   2.000 eventos no son 2.000 observaciones.
   [MetricGate / Donner](https://metricgate.com/blogs/sample-size-for-cluster-randomized-trials/)
2. **Más sesiones > más eventos por sesión.** Añadir eventos al mismo
   día rinde poco. Añadir sesiones sí. Preferir muchas sesiones flacas
   a pocas gordas.
3. **Pocos clusters mienten.** < 10–15 por brazo: la normal no vale.
   < 30: los IC suelen ser estrechos de más; hace falta wild cluster
   bootstrap (Cameron–Gelbach–Miller, 2008).
   [World Bank](https://blogs.worldbank.org/en/impactevaluations/beware-of-studies-with-a-small-number-of-clusters)
4. **Justificar N después de ver el número es SPARKing.** Elegir 50
   porque «9 de 22 < 50» es eso. Si no hay N a priori, se dice
   «sin justificación / recurso acotado» (Lakens), no se fabrica uno.
   [Frontiers 2023](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2023.912338/full)
5. **Mirar 60 celdas y quedarse con la gorda** es data snooping
   (White 2000, Hansen SPA 2005). El presupuesto N_eff = 71 ya está
   escrito. No se reabre acá.

## La aritmética que YA tenés (manifiesto v1, no v2)

Mismo contrato: dos proporciones, α = 0,05, potencia 80 %, p = 0,5,
N ≥ 403 ⇒ Δ = 10 pp. Entonces `Δ ≈ 0,10 × √(403 / n_sesiones)`:

| n sesiones (genérico) | MDE₈₀ |
|---|---|
| 20 | ≈ 45 pp |
| 30 | ≈ 37 pp |
| 50 | ≈ 28 pp |
| 80 | ≈ 22 pp |
| 139 (ejemplo del manifiesto v1) | ≈ 17 pp |
| 228 (todo el universo) | ≈ 13 pp |

403 sesiones para Δ = 10 pp **es imposible** (universo = 228).

## Las dos opciones, en criollo

**A — Sin boolean (recomendado).** No hay «celda viva». Cada celda
publica `n_sesiones` + MDE. La central se elige por cobertura y por
si el Δ detectable paga costos (~3,9 ticks RT en 6E), no por un corte.
Es lo que Lakens llama decir la verdad cuando no hay N a priori.

**B — Piso derivado de un Δ que vos fijás ahora.** Escribís el Δ
*antes* de volver a la tabla. El n sale de la fórmula de arriba.
Si querés ~17 pp, el contrato viejo ya implica ~139 sesiones. Si
querés 10 pp, no hay celda que viva. No uses 50.

## Qué no decidir ahora

Visor: útil para ver los dos roles de δ. No desbloquea F4.
Manifiesto v2: después de A o B.

**Aporte al referente:** un piso sacado de la tabla no es un piso.
La potencia la ponen las sesiones. La literatura y la 014 dicen lo mismo.
