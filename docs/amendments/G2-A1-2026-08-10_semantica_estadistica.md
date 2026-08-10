# G2-A1 — corrección de semántica estadística

> **Estado: IMPLEMENTADA EN RAMA; PROMOCIONES G2 SIGUEN CONGELADAS.**
>
> Fecha: 2026-08-10. Rama: `fix/g2-a1-statistical-semantics`.
>
> Nico autorizó primero una verificación independiente y luego la escritura del
> código correspondiente. La autorización permite implementar y revisar; la
> promoción sigue bloqueada porque `APPROVED_G2_CONTRACT_SHA256S` permanece
> vacío hasta que la suite pase en el entorno canónico y se apruebe el hash
> exacto del contrato resultante.

## 1. Verificación independiente

La segunda lectura no se apoyó en el veredicto previo. Releyó el contrato, el
código, sus tests, la decisión persistible, la enmienda candidata del 3 de
agosto y las primitivas ratio/bootstrap ya presentes.

### 1.1 El `mcpt()` anterior no implementaba el contrato

El contrato decía permutar **la serie de señales sobre retornos reales** por
bloques de sesión. La función recibía P&L de trades ya materializado. Esa firma
no contiene ni señales ni retornos de mercado, por lo que el nulo declarado no
es representable.

La suma total tampoco cambia al permutar sesiones. Para evitar esa invariancia,
el código usó la suma de la primera mitad temporal. Por construcción, eso mide
concentración/decaimiento, no expectativa positiva.

Consecuencia adversarial: un efecto estable devuelve `p=1`; un candidato muy
concentrado al comienzo puede devolver `p<=0.05`. G1 premia estabilidad y el
`mcpt()` anterior exigía concentración temprana. No son lógicamente
incompatibles en todos los puntos, pero la región aceptable era una banda
arbitraria y contraria al objetivo de desplegar un edge persistente.

### 1.2 No existe un MCPT universal

Permutar señales completas entre sesiones sólo es válido si los bloques son
intercambiables y tienen una alineación intradía comparable. Una estrategia
recursiva, una zona condicionada por el camino o sesiones con calendarios
heterogéneos requieren otros nulos.

Decisión: retirar el generador universal. Cada campaña debe persistir
`null_id`, hipótesis, nuisance preservado, intercambiabilidad, semilla,
generador y digest. El núcleo sólo reduce estadísticas nulas con la corrección
finita:

```text
p = (1 + count(T_null >= T_observed)) / (1 + B), B >= 1000
```

El nombre estructural `mcpt` se conserva dentro del registro por compatibilidad,
pero significa **test nulo de campaña**, no la función histórica.

### 1.3 DSR era vacuo en una ruta e imposible en la otra

`g2.py` exigía `DSR > 0`; como DSR es una probabilidad, casi cualquier cálculo
con al menos dos observaciones pasaba. `g2_decision.py` exigía `>=0.95`, pero su
allowlist vacía hacía imposible aprobar.

G2-A1 fija `DSR >= 0.95`, unidad sesión, escala no anualizada y `N_eff` completo
del manifiesto. La dependencia se trata con un método versionado:

```text
session_hac_bartlett_v1
```

El tamaño efectivo se obtiene de la varianza de largo plazo Bartlett/HAC y se
acota conservadoramente a `[2,n]`; autocorrelación negativa nunca autoriza
`n_eff > n`. El specification digest se calcula canónicamente en código y la
evidencia DSR completa queda embebida en la decisión.

### 1.4 Había dos significados de “G2 aprobado”

`evaluar()` podía aprobar con DSR casi cero; `G2ValidationDecision` nunca podía
aprobar por su allowlist vacía. Además `GateResult.passed` era un booleano
confiado: un artefacto podía declarar `passed=true` con un valor rojo.

G2-A1 hace que:

- cada gate use un umbral canónico y un `PASS` incompatible con el valor sea
  rechazado;
- el gate DSR de la decisión coincida byte por byte con `DSREvidence` embebida;
- DSR e IC primario usen las mismas sesiones;
- el método de multiplicidad sea único (`dsr_manifest_n_eff`), evitando cobrar
  la misma grilla nuevamente con SPA;
- la autoridad siga siendo `G2ValidationDecision`, no el retorno en memoria de
  `evaluar()`.

## 2. Semántica aprobable propuesta

Un candidato sólo puede obtener G2 cuando pasan conjuntamente:

1. nulo específico de campaña: `p <= 0.05`, `B >= 1000`;
2. PBO CSCV `S=8` por `sum_pnl_net / n_trades`: `PBO <= 0.50`;
3. DSR por sesión, no anualizado, con HAC y `N_eff`: `DSR >= 0.95`;
4. walk-forward seleccionado y agregado por expectativa neta por trade: `>0`;
5. mediana de expectativas de vecinos ±1 paso: `>0`;
6. IC bootstrap-t estacionario del estimando canónico, con al menos 160
   sesiones y cota inferior `>0`.

El IC es la inferencia primaria. PBO, DSR, walk-forward y sensibilidad son vetos
complementarios; ninguno reemplaza expectativa positiva.

## 3. Cambios de código

- `edgelab/research/g2.py`
  - retira `mcpt()` de decisiones;
  - conserva `temporal_concentration_test()` sólo para reproducibilidad;
  - agrega `campaign_null_pvalue()`;
  - fija `DSR_MIN=0.95`;
  - agrega DSR de sesiones con HAC Bartlett versionado;
  - enruta PBO y walk-forward a las primitivas ratio existentes;
  - exige el IC primario en la composición diagnóstica.
- `edgelab/research/g2_decision.py`
  - valida umbrales y dirección de cada gate;
  - embebe `DSREvidence`;
  - exige coincidencia entre evidencia y gate;
  - elimina la doble ruta de multiplicidad.
- tests adversariales
  - prueban que un edge estable obtenía `p=1` en el diagnóstico legado;
  - impiden reusar `mcpt()` como gate;
  - verifican el p-valor finito y los empates conservadores;
  - verifican reducción de `n_eff` bajo autocorrelación positiva;
  - impiden forjar `passed` o el umbral;
  - exigen los seis requisitos G2-A1.

## 4. Congelamiento y criterio de activación

Este commit **no** habilita promociones. Para activarlo faltan, en orden:

1. ejecutar la suite específica y completa en `.venv` del repo limpio;
2. registrar HEAD, status, entorno y resultado de tests;
3. revisar cobertura sintética del DSR-HAC y del bootstrap-t ratio;
4. incorporar la semántica final a `edge_validation_contract.md`;
5. calcular SHA-256 exacto del contrato aprobado;
6. agregar ese hash a `APPROVED_G2_CONTRACT_SHA256S` en un commit posterior;
7. aprobación explícita de Nico para esa activación.

No se toca el holdout, no se reinterpreta ninguna campaña pasada y no se
promueve retroactivamente ningún resultado.

**Aporte al referente:** sustituye gates que confundían concentración temporal
con edge por una decisión que responde a expectativa neta persistente, cobra la
multiplicidad una sola vez y falla cerrado ante evidencia incompleta.
