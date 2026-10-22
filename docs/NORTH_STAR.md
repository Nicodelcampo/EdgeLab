# NORTH STAR — Referente rector de EdgeLab

> Documento canónico versionado. Gobierna toda decisión, tarea y trade-off del
> proyecto. Su hash se registra al pie y se cita en cada manifiesto de campaña.

## Objetivo final

**EL OBJETIVO FINAL DEL PROYECTO ES ENCONTRAR EDGES VÁLIDOS Y APLICABLES EN EL
MERCADO A TRAVÉS DE ALGORITMOS QUE, A TRAVÉS DE LA RENTABILIDAD, PERMITAN
OBTENER GANANCIAS EN LAS CUENTAS DE TRADING DONDE SE APLICAN.**

## Jerarquía de objetivos (para priorizar cualquier tarea o trade-off)

1. **Expectativa económica NETA** (después de comisiones, spread y slippage).
2. **Validez fuera de muestra** (holdout sellado, sin data snooping).
3. **Robustez estadística** (MCPT, PBO, DSR/SPA, walk-forward, sensibilidad).
4. **Ejecutabilidad real** (feed en vivo, fills realistas, latencia, reglas
   completas de entrada/salida/sizing/kill switch).
5. **Control de riesgo** (drawdown tolerable, despliegue con riesgo mínimo).
6. **Paridad, determinismo, trazabilidad y visor COMO MEDIOS para 1–5.**

## Recordatorios

- Un indicador con paridad exacta **no es un edge**. Una zona bien almacenada
  **no es un edge**. Un backtest positivo **no es un edge** si no sobrevive
  selección, costos, OOS y ejecución.
- **Target-free** aplica a la construcción técnica de indicadores; el research
  de estrategias SÍ usa retornos y P&L, pero bajo pre-registro, presupuesto de
  investigación, corrección por múltiples pruebas y holdout sellado.
- El progreso NO se mide por infraestructura terminada sino por **cuánto reduce
  la distancia hacia un edge neto, robusto y operable**.
- **No prometer rentabilidad futura**: el objetivo metodológico es maximizar la
  probabilidad de detectar edges reales y rechazar falsos antes de arriesgar
  capital.

## Definición operativa: "edge válido y aplicable"

Un edge se considera válido y aplicable solo cuando satisface las **cuatro
clases de validez**, en orden y sin saltos:

1. **Validez técnica** — lineage completo, features as-of sin look-ahead,
   identidad (config_id + bar_spec), disponibilidad en tiempo real, paridad
   declarada, determinismo. (Es condición necesaria, NO suficiente.)
2. **Validez estadística** — expectativa positiva que sobrevive corrección por
   múltiples pruebas (MCPT/PBO/DSR/SPA según corresponda), walk-forward y
   sensibilidad paramétrica, contando TODAS las variantes cobradas al budget.
3. **Validez económica** — expectativa NETA positiva con costos desglosados
   (comisión, exchange/NFA, spread, slippage) en escenario base y sin colapso
   inmediato en escenario adverso; capacidad y turnover razonables.
4. **Aplicabilidad** — ejecutable en vivo con reglas completas
   (entrada/salida/sizing/límites/kill switch), paridad research↔live, y
   despliegue con riesgo mínimo tras paper/shadow.

## Cadena de estados de promoción

```
idea
  → technically_valid        (G0: integridad técnica, paridad/determinismo)
  → exploratory_candidate    (G1: evidencia exploratoria, sin tocar holdout)
  → statistically_supported  (G2: robustez estadística, múltiples pruebas)
  → economically_viable      (G3: expectativa NETA positiva con costos)
  → holdout_confirmed        (G4: OOS sellado, una sola apertura)
  → paper_validated          (G5: paper/shadow, paridad research↔live)
  → live_candidate           (apto para despliegue con riesgo mínimo)
  ┊
  → retired / failed         (resultado negativo: se registra, no se relajan gates)
```

Reglas de promoción (gates duros y blandos definidos ANTES de ver resultados;
detalle en `edge_validation_contract.md`):
- `EDGES_DISCOVERED.md` exige **≥ statistically_supported** y **parity_exact**
  propio de la config ganadora.
- `LIVE_CANDIDATES` exige **≥ paper_validated**.
- Un resultado negativo se **registra**, no relaja gates ni abre el holdout.

## Firewall del holdout

Holdout sellado: **desde la sesión CME del 2026-10-01** (apertura 2026-09-30 17:00 CT =
22:00 UTC), a futuro, **para todos los instrumentos y todo tipo de dato** (ticks, barras,
L2). Una sola apertura por candidato, conforme a protocolo pre-declarado. Fuente única en
código: `edgelab/holdout.py` (enmienda **HOLDOUT-A4**, firmada por Nico el 2026-10-22,
`docs/incidents/AMENDMENT_HOLDOUT-A4_2026-10-22.md`); reemplaza las fronteras parciales
de las enmiendas anteriores (A1–A3 y la de L2), que quedan como historia.

- Todo lo anterior a esa apertura es **desarrollo**. Para ES y NQ rige además la partición
  de A3: descubrimiento hasta 2026-03-31 y réplica abr–sep una vez por familia. Para el resto,
  una familia que quiera réplica la pre-registra antes de mirar.
- **Prohibido** usar el holdout para elegir dirección, entradas/salidas, thresholds,
  bar_spec, costos o candidatos.
- **Permitido** solo para validaciones target-free (paridad, determinismo,
  geometría, integridad, visor).

> **La frontera es un sello, no un cursor (regla 95).** El 2026-08-01 un commit
> etiquetado `chore` movió la frontera declarando que un mes "fue absorbido a la muestra
> pre-holdout": es des-sellar material protegido, y además venció solo cuando el reloj
> cruzó la fecha. Revertido en INC-006. La frontera efectiva se calcula como
> `min(sello, declarada)`, así que atrasarla es imposible por construcción. El único
> movimiento del sello es una enmienda firmada por Nico (HOLDOUT-A4), nunca un cambio de código.

## Rituales permanentes

- Todo checkpoint de turno termina con **"Aporte al referente: …"** (1–2 líneas:
  qué distancia se redujo hacia un edge neto y operable).
- Todo manifiesto de campaña cita el **hash de este documento**.
- Toda plantilla generadora (scaffold, spec LLM, reportes) incluye los campos
  obligatorios **"justificación económica"** y **"cómo podría refutarse"**.

## Decisión de prioridad vigente (sellada por Nico)

**F9 (nuevos indicadores) PAUSADA** hasta ejecutar al menos una campaña formal
de descubrimiento sobre los 5 indicadores existentes. Agregar indicadores hoy
amplía el espacio de búsqueda y el data snooping sin evidencia de que haga falta.

---

Ver también: `edge_validation_contract.md` (gates G0–G5), `kernel_contract.md`
(construcción técnica target-free), `nt8_indicator_parity_contract.md` (paridad).

<!-- SHA256-BODY-ABOVE -->

**sha256 (cuerpo hasta el marcador):** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
