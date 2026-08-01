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

Holdout sellado: **2026-07-01 → 2026-12-31**. Una sola apertura por candidato,
conforme a protocolo pre-declarado.

> **La frontera es un sello, no un cursor (regla 95).** El 2026-08-01 un commit
> etiquetado `chore` la movió a 2026-08-01 declarando que julio "fue absorbido
> a la muestra pre-holdout". Eso no es una repartición: es des-sellar un mes ya
> protegido, y además venció solo cuando el reloj cruzó la fecha. Revertido en
> INC-006. La frontera efectiva hoy se calcula como `min(sello, declarada)`, de
> modo que atrasarla es imposible por construcción, no por convención.
- **Prohibido** usarlo para elegir dirección, entradas/salidas, thresholds,
  bar_spec, costos o candidatos.
- **Permitido** solo para validaciones target-free (paridad, determinismo,
  geometría, integridad, visor).

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

**sha256 (cuerpo hasta el marcador):** `21bb3b01a33e2b373859a38ac4615de376a6262f0aa7ced0e8f5dec33b5256a8`
