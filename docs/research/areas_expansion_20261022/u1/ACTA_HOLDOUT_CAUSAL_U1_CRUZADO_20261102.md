# Acta: U1-CRUZADO CAUSAL sobre el holdout sellado (2026-11-02), registrada antes de correr

Estado: VIGENTE. Decisión de Nico (2026-11-02): «se vuelve a correr el holdout con el código causal». Referente: `docs/NORTH_STAR.md`,
cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5.

## Por qué se repite
La corrida del acta `ACTA_HOLDOUT_COMPLETO_U1_CRUZADO_20261102.md` usó `areas_expansion.disparos` con mirada al futuro
(`HALLAZGO_LOOKAHEAD_DISPAROS_U1_20261102.md`). Su resultado (+25,8, 18 operaciones) no estima lo que se puede operar. Esta corrida
lo **reemplaza como estimación operable**. No es una regla nueva ni un ajuste: misma regla, mismo período, mismo dato y misma
ejecución, con el único cambio de la causalidad, decidido antes de ver este resultado y por un motivo ajeno a él.

## Regla y código
- Misma regla congelada: U1 sobre USATECH, N ≥ 3, 40 pts, A/H ≥ 8, x = 0,25; NQ E1A/T3/S3, tope 3×, fricción 1,5455.
- `edgelab/research/u1_cruzado_papel.py` (OPERAR). Llama a `u1_cruzado.operar`, que desde el 2026-11-02 es causal por defecto,
  con el certificado de causalidad vigente.
- Es la misma regla que corre la ficha en papel y que porta la estrategia JForex (paridad del núcleo 15/15).

## Datos
Dataset `nicolasbuttaro/edgelab-holdout-sellado`, sesiones 2026-10-01 → 2026-10-30. Sin calentamiento de desarrollo: las zonas se
arman sólo con ticks del holdout, igual que en la corrida anterior, para que la única diferencia sea la causalidad.

## Pruebas, declaradas antes de mirar
1. **Principal, e-proceso de edge** (`MonitorCandidato`), igual que en el acta anterior: cotas −655/+735, `mu_util` 10,63.
   - **Nivel LORD++ reservado**: α = 0,003608 (`LIBRO_LORD.json`, reserva `U1-CRUZADO/holdout_causal_20261102`, t = 2). Es un paso
     nuevo de la familia: repetir cuesta α.
   - **CONFIRMADA** si e_edge ≥ 1/α = 277. **REFUTADA** si e_futilidad ≥ 10. Si no, **NO_CONCLUYENTE**.
2. Informativo: n, media y aciertos totales; sólo las sesiones 10-23 → 10-30; diferencias operación por operación con la corrida
   anterior.

**Expectativa honesta.** Con 10–20 operaciones, lo más probable es NO_CONCLUYENTE. El resultado no se usa para ajustar nada.

## Registro
- La apertura de la familia (`HOLDOUT_VENTANAS.jsonl`, cid `U1-CRUZADO`, desde 20261001) ya existe; esta corrida usa la misma
  ventana.
- Conteo: 1 prueba en `TRIAL_REGISTRY_GLOBAL.jsonl` (`holdout/U1-CRUZADO-CAUSAL/20261001-20261030`).

## Cómo podría refutarse
e_futilidad ≥ 10, o media neta ≤ 0 en el holdout con el código operable.
