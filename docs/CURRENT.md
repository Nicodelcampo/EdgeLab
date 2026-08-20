# CURRENT — empezar acá

> Punto de entrada único. Una sesión nueva (Claude, auditor o Nico) lee esto
> antes de cualquier otra página. Si este archivo y Notion divergen, **manda
> el repo**.

**Rama viva:** `foundation/f0b-compatibility-probe`
**Fecha:** 2026-08-20
**Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Qué está vivo hoy

**Frente principal: `HFTZonesESPureV2` sobre ES.** Primero entender el indicador
original en su activo; la adaptación multi-activo queda para después.

1. **Oráculo controlado** — `runs/oraculo_espurev2_ES_snapshot.sqlite`
   (`sha256 bece887455c0347b…`). DbPath nuevo, **un solo escritor**: resuelve el
   bloqueante del log compartido, donde 3 indicadores escribían la misma tabla sin
   columna de autor. **23.863 zonas · 120 sesiones** pre-firewall. 0 duplicados,
   0 retrocesos, 0 post-firewall. Acta: `ORACULO_ESPUREV2_ES_2026-08-19.md`.
2. **Censo descriptivo corrido** — `CENSO_ZONAS_ES_2026-08-19.md`. Hallazgo:
   **92 % de zonas bajistas por el `isDown`-first** (`.cs` l.215-216 y 233-234: con
   precio plano las dos condiciones son true e `isDown` gana). Idéntico en 3 buckets
   y 3 contratos. **Ninguna lectura direccional de esa población es válida.**
   Segundo hallazgo: la **ocupación está saturada** (p05 0,80 · p50 0,95), así que el
   ABSORB propuesto en la spec de HFTZonesRange clasificaría casi todo.
3. **Parche listo, sin tocar el original** — `docs/research/parches/HFTZonesESPureV2Flat.cs`
   (`sha256 4e80c24d…`), ya copiado a la carpeta de NT8. **Falta compilar y correr.**
   Comparador preparado: `diag/tasa_senales/comparar_v2_vs_flat.py`.
4. **Retorno a zona** — `diag/tasa_senales/retorno_a_zona_es.py`, target-free, con
   dos controles construidos en la misma sesión (espejo emparejado por distancia,
   placebo aleatorio con semilla fija).

**Línea H-Z2A:** v4, manifiesto v1 SUSPENDIDO, censo v2 verificado, P-47 = A.
**Línea HFTZonesRange / multi-activo: APARCADA** salvo el diagnóstico v2.3, que cerró
limpio.
**H-ASIA-1** en 6J: refutada en su forma literal.

**Board:** hasta **P-55** (el contexto no es un control: un nulo puede ser dos efectos
opuestos cancelándose). `PENDIENTE.md`.
**Canal:** `docs/audits/CANAL_AUDITOR.md`, hasta la entrada 043.

## Qué no tocar

Holdout · P&L · F4 sin STOP · MAE/MFE · `features.py` · `fix/g2-a1-*` ·
`COVERAGE_NEUTRAL` · matriz de kernels · Optuna/CatBoost · cambiar el 403 ·
boolean de sesiones · semáforo de «vive» en el visor.
Firewall: outcomes `false`, holdout 2026-07-01 → 2026-12-31
(`1782856800000000000` ns).

**Aporte al referente:** A evita convertir la potencia en una etiqueta. El visor
acorta el tiempo entre «esto huele mal» y el corredor, sin mirar el resultado.
