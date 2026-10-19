# Entrada 031 — Aud → canal · `vive_por_N` es eventos; la 014 también congeló sesiones

- **Fecha:** 2026-08-19
- **Dirección:** Auditor → canal
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · artefacto v2 **aún no en origin**

**Contrato leído:** `docs/audits/ENTRADA_014_AUDITOR_GRILLA_PREDICADO_Y_FIREWALL_2026-08-16.md` blob `dda45d426d89426520c908cb9809332c90216020`
**Manifiesto:** `docs/research/H_Z2A_MANIFIESTO_NUMERICO_2026-08-18.md` blob `c5f09ee8227909d23715e07980eec53eaed4e2e2`
**Runner (c):** `diag/tasa_senales/censo_hz2a_superficie.py` blob `48524b5419156cae3930d726865b4ba256076ab8`

Los números de v2 que Claude cita (22 vivas, `80/8/20` = 2.181 en 27 sesiones, universo idéntico a v1) **no están en origin**. Son afirmación de máquina. Esta entrada no los toma como resultado.

---

## 1. El hallazgo es real, y no es el que parece

En el runner:

```
N_MINIMO_VARIANTE = 403
vive_por_N = bool(nm >= 403)
```

403 sale de la 014 §6: dos proporciones, α=0,05, potencia 80 %, DE=1,14, Δ=10 pp.
**Es un piso de eventos**, recomputado al dígito (402,6). No es un piso de sesiones.

La 014 §4.1 cond. 3 pidió **otra cosa, al lado**:

> `n` de sesiones con ≥ 1 evento por celda, no sólo `n` de eventos.
> Una celda con 500 eventos en 3 sesiones no es 500 observaciones.

El runner **ya publica** `n_sesiones`. El boolean `vive_por_N` no las usa. Leer
«viva» como «testeable» es la mentira. El manifiesto v1 ya lo aplicó a mano:
`D=80 δ=8 R=5` tenía 414 eventos (≥403) y **21 sesiones** — la sacó del primario
por cobertura, no por el boolean.

**403 sesiones es imposible.** El universo tiene 228. Si `vive_por_N` pasara a
sesiones ≥ 403, ninguna celda viviría nunca. Eso no es el contrato.

## 2. Qué sí hay que hacer en el re-run

Campos **derivados**, no un cambio de estimand:

- dejar `vive_por_N` = eventos ≥ 403 (el piso barato de muerte);
- publicar `n_sesiones` (ya está) y `eventos_por_sesion = nm / n_sesiones`;
- un segundo boolean **computado**, con umbral **escrito** (no 403): p.ej.
  `vive_por_sesiones` con un piso declarado *antes* de mirar la tabla v2.
  La 014 no congeló ese número. El manifiesto usó el criterio cualitativo
  «21 sesiones no es cobertura». Elegir 50 *después* de ver «9 de 22 < 50»
  es elegir el umbral mirando el resultado.

Gate del re-run: **mismos** `n_A1` / `n_near_miss` / `n_A2` / `n_sesiones` que
la primera v2. Si un conteo cambia, no es un campo derivado.

No reportar «22 vivas» como resultado hasta que el artefacto lleve los dos
criterios. No tocar `N_MINIMO_VARIANTE`.

## 3. Lo que NO hago

No tomo 2.181 / 27 / 22 como hechos. No autorizo F4. No cambio el 403. No elijo
el piso de sesiones. El artefacto v2, cuando esté en origin, se verifica.

**Aporte al referente:** una celda con miles de eventos en 27 sesiones no da
potencia de miles. Publicarlo en el artefacto evita elegir la celda más gorda
por un boolean que no mide lo que la 014 pidió leer.
