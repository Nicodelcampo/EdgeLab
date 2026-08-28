# Entrada 029 — Aud → canal · intake Nico: P-45 es (c); máquina libre; v2 no mira outcomes

- **Fecha:** 2026-08-18
- **Dirección:** Auditor → canal (copia a Opus y a Nico)
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · censo v2 **NO corrido**
- **Esto es evidencia y adjudicación de alcance, no una orden de F4.**

**Commits leídos:** `2fd0d93e510f2793fa0e9e26914d78fbd020b2b2` (HEAD) · `784edaec656043d522597c9d28daaa6d78dc9895` (028)

**Canónico de la prosa de Nico:** `docs/research/INTAKE_NICO_HZ2A_EXPLORATORIO_2026-08-18.md`
**Asiento de board (P-45 c + P-47…P-50):** `docs/research/BOARD_P45_P50_2026-08-18.md`

---

## 1. Máquina libre — asentado

Nico: «La máquina está libre.» 2026-08-18. Condición 3 de la 025, cumplida.

## 2. P-45 = (c) episodio — no es (a) ni (b)

No eligió golosa ni ciclos independientes. Eligió:

- umbral/rango de near-miss, como parámetro;
- al inicio no distinguir más cerca / más lejos, sí poder ver cuál δ funciona mejor;
- cumplido el near-miss, el 2º acercamiento es **retorno (A2)** si entra en el umbral;
- otro near-miss **sólo** si después se vuelven a cumplir las condiciones.

Eso es **consumir el retorno**: la observación de la 025 deja de ser nota y pasa a ser el estimand. Opus implementa (c) en `censar_zona` + test que fije A2 ≠ NM del ciclo 2. **No corre v2** hasta que ese test exista.

## 3. v2 mide capa 1. El resto no entra en esta corrida

Nico aceptó «solo capa» si se hace bien respecto de la idea. La idea completa es una **cadena** (v4: H-NM → H-REVISIT → H-A2ACCESS → H-PEN → H-ECON). v2 es el censo de población de la geometría, con (c). No es la cadena entera.

| Pedido | Adjudicación |
|---|---|
| 3 · poco cómputo, buena relación | un portador (aVol 6E formal), sin matriz de kernels, sin HFTZones2 en la misma corrida |
| 4 · abrir HFTZones2 | **P-48** decidida, **después** de v2 aVol |
| 5 · mirar MAE/MFE, expansión, fuerza al llegar | **no en v2**. Es H-PEN / H-A2ACCESS. Exige manifiesto + STOP. El censo que mira outcomes deja de ser censo |
| 6 · tendencia saludable ahora | **P-50**: spec ahora; F9 sigue pausada para *correr* |
| zona no virgen | **P-47**: se revisa; v2 primera corrida **sigue virgen** |
| «firma» | **P-49**: después de tener N |

## 4. Lo que NO hago

No autorizo F4. No autorizo MAE/MFE en el runner del censo. No des-pauso F9. No abro HFTZones2 en la misma corrida. No implemento (c) yo (máquina).

## 5. Qué sigue

| Quién | Qué |
|---|---|
| **Opus** | Implementar (c) + test. Copiar `BOARD_P45_P50` al final de `PENDIENTE.md`. **No v2** hasta el test. No MAE/MFE. No matriz. Spec de P-50 si no atrasa (c). |
| **Nico** | Nada más para destrabar v2. El STOP viene después del artefacto. |
| **Auditor** | Con (c) en origin y v2 corrido: verificar artefacto y manifiesto v2. |

**Aporte al referente:** la hipótesis quedó partida en capas medibles. v2 puede contar población sin mirar si «funciona». Mezclar MAE/MFE ahora habría convertido el censo en selección sobre el resultado.
