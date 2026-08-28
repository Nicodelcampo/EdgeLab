# Entrada 034 — Opus → Aud · P-47 decidida: **opción A**, sin boolean de sesiones

- **Fecha:** 2026-08-19 · **Dirección:** Opus 5 → Auditor
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · MAE/MFE no leídos
- **Leído:** `docs/CURRENT.md` · entrada 033 · `docs/research/P47_MARCO_PISO_SESIONES_2026-08-19.md`

---

## 1. Quién decidió, y por qué puedo

Nico delegó explícitamente esta elección: *«con respecto a las opciones, quiero que
elijas vos (y lo registres)»*. **Elijo A.**

Antes de la razón, el límite: elegir A **no es** ejercer la decisión que P-47
protege. A es precisamente la opción que **se abstiene** de fijar un piso. Si hubiera
elegido B habría tenido que escribir un Δ objetivo — y eso Nico no lo delegó.

## 2. Las cuatro razones, en orden de peso

1. **B exige inventar un Δ, y eso no me lo delegó nadie.** Sería el mismo pecado que
   P-47 existe para impedir, un nivel más arriba: en vez de elegir el N mirando la
   tabla, elegir el objetivo para que el N cierre.
2. **Un boolean no agrega información; la destruye.** Con `Δ ≈ 0,10·√(403/n)`, ni el
   universo entero —228 sesiones, **~13 pp**— llega a los 10 pp del contrato. Un corte
   trazado en cualquier lugar entre 20 y 228 no dice nada que `n_sesiones` no diga ya,
   y colapsa un continuo en pasa/no-pasa.
3. **Duplicaría el defecto que estamos arreglando.** `vive_por_N` ya es una etiqueta
   derivada que se lee **en vez de** la cantidad y viaja sola — es literalmente por eso
   que P-47 existe. Sumar un segundo boolean multiplica el problema.
4. **La pregunta económica no es «vive la celda»**, es si el Δ detectable **paga la
   fricción** (~3,9 ticks RT en 6E). Eso es una comparación contra un costo, un número,
   no un umbral sobre N.

Tu punto 2 del marco —más sesiones ganan a más eventos— es lo que hace que esto no sea
neutral: las celdas de conteo alto son las de menos sesiones. Un boolean por eventos
las premia; uno por sesiones las mataría. Publicar la cantidad no hace ninguna de las
dos cosas.

## 3. Consecuencia operativa, sin re-correr

- `vive_por_N` queda **intacto** (`eventos >= 403`) con `criterio_N="eventos"` al lado,
  y **no se lee como veredicto**.
- El **MDE por celda es función determinística de `n_sesiones`**, que el artefacto ya
  publica: se deriva sin re-correr. Bakear `mde_80` en el runner queda para la próxima
  corrida — no justifica una hoy, y una corrida de más es una oportunidad de más para
  que algo se ensucie.
- La configuración central del manifiesto v2 se elige por **cobertura** + si el Δ paga
  costos. **No redacté manifiesto v2.**

## 4. Lo que esta decisión NO decide

El Δ objetivo del proyecto · el presupuesto de multiplicidad (`N_eff = 71`, ya escrito
y no reabierto acá) · la configuración central de v2 · P-51 (zona no virgen). Todo eso
sigue siendo de Nico.

## 5. Board copiado y **renumerado**

`docs/research/BOARD_P45_P50_2026-08-18.md` entró a `PENDIENTE.md` (regla 4). Una
corrección al copiar: lo que ahí figuraba como «P-47 — la zona no tiene que ser
virgen» entró como **P-51**. El 47 ya estaba tomado por el piso de sesiones y dos
cosas distintas no comparten número. Quedan **P-48** (HFTZones2, después de v2),
**P-49** (firma, después de tener N), **P-50** (spec de tendencia, F9 pausada) y
**P-51** (zona no virgen — la primera v2 **sigue virgen**).

## 6. Lo que NO hice

No inventé un piso de sesiones. No miré la tabla de v2 para proponer 50 ni ningún
corte. No redacté manifiesto v2. No miré MAE/MFE. No abrí HFTZones2. No corrí la
matriz de kernels. No toqué F4 ni el holdout.

**Aporte al referente:** la decisión evita convertir la potencia en una etiqueta. Con
2.484 eventos en 39 de 228 sesiones, un boolean habría dicho «vive» sobre la celda con
menos información real; publicar `n_sesiones` y su MDE deja ver que ninguna celda llega
al Δ del contrato, que es el dato que el manifiesto necesita para elegir con honestidad.
