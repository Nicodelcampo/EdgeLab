# G2-A1 — corrección de semántica estadística

> **Estado: IMPLEMENTADA Y VALIDADA EN PR; PROMOCIONES G2 SIGUEN CONGELADAS.**
>
> Fecha: 2026-08-10. Rama: `fix/g2-a1-statistical-semantics`. PR #5.
>
> Nico autorizó la verificación independiente y la escritura del código. Esa
> autorización no habilita promociones: los hashes exactos del contrato y de la
> implementación permanecen fuera de sus allowlists hasta aprobación final.

## 1. Verificación independiente

La segunda lectura no se apoyó en el veredicto previo. Releyó el contrato, el
código, sus tests, la decisión persistible, la enmienda candidata del 3 de
agosto y las primitivas ratio/bootstrap ya presentes.

### 1.1 El `mcpt()` anterior no implementaba el contrato

El contrato decía permutar **la serie de señales sobre retornos reales** por
bloques de sesión. La función recibía P&L de trades ya materializado. Esa firma
no contiene ni señales ni retornos de mercado, por lo que el nulo declarado no
era representable.

La suma total tampoco cambia al permutar sesiones. Para evitar esa invariancia,
el código usó la suma de la primera mitad temporal. Por construcción, medía
concentración/decaimiento, no expectativa positiva. Un efecto estable devolvía
`p=1`; un candidato concentrado al comienzo podía devolver `p<=0.05`.

### 1.2 No existe un MCPT universal

Permutar señales completas entre sesiones sólo es válido si los bloques son
intercambiables y tienen una alineación intradía comparable. Una estrategia
recursiva, una zona dependiente del camino o calendarios heterogéneos requieren
otros nulos.

Decisión: retirar el generador universal. Cada campaña persiste `null_id`,
hipótesis, nuisance preservado, intercambiabilidad, semilla, generador y digest.
El núcleo sólo reduce estadísticas nulas con:

```text
p = (1 + count(T_null >= T_observed)) / (1 + B), B >= 1000
```

El nombre estructural `mcpt` se conserva en el registro por compatibilidad, pero
significa **test nulo de campaña**, no la función histórica.

### 1.3 DSR era vacuo en una ruta e imposible en la otra

`g2.py` exigía `DSR > 0`; como DSR es una probabilidad, casi cualquier cálculo
pasaba. `g2_decision.py` exigía `>=0.95`, pero su allowlist vacía impedía aprobar.

G2-A1 fija `DSR >= 0.95`, unidad sesión, escala no anualizada y `N_eff` del
manifiesto. La implementación final pasa a:

```text
session_hac_bartlett_v2
```

V2 exige al menos 160 sesiones, calendario elegible completo, ceros explícitos
para sesiones sin trades, digest del calendario y lag Bartlett por defecto
`ceil(sqrt(n))`. Persiste Sharpe, momentos, lag, varianzas, factor de dependencia
y dos identidades separadas: digest de especificación y digest AST de la
implementación ejecutada.

### 1.4 Había dos significados de “G2 aprobado”

`evaluar()` podía aprobar con DSR casi cero; `G2ValidationDecision` no podía
aprobar. Además, `GateResult.passed` era un booleano confiado.

Ahora:

- cada gate usa umbral y dirección canónicos;
- un `PASS` incompatible con el valor es rechazado;
- el gate DSR coincide byte por byte con `DSREvidence` embebida;
- DSR e IC primario usan las mismas sesiones y el mismo calendario;
- la multiplicidad es única (`dsr_manifest_n_eff`), sin doble cobro SPA/DSR;
- la autoridad es `G2ValidationDecision`, no `evaluar()` en memoria.

## 2. Semántica final incorporada al contrato rector

Un candidato sólo puede obtener G2 cuando pasan conjuntamente:

1. nulo específico de campaña: `p <= 0.05`, `B >= 1000`;
2. PBO CSCV `S=8` por `sum_pnl_net / n_trades`: `PBO <= 0.50`;
3. DSR por sesión, no anualizado, con calendario completo, HAC y `N_eff`:
   `DSR >= 0.95`;
4. walk-forward seleccionado y agregado por expectativa neta por trade: `>0`;
5. mediana de expectativas de vecinos ±1 paso: `>0`;
6. IC bootstrap-t estacionario del estimando canónico, con al menos 160
   sesiones y cota inferior `>0`.

El IC es la inferencia primaria. Los otros componentes son vetos
complementarios; ninguno reemplaza expectativa positiva.

## 3. Calibración sintética formal

`tests/research/test_g2_dsr_calibration.py` fija los sobres antes de observar CI
y ejecuta 400 paneles de 160 sesiones por escenario:

- gaussiano IID bajo nulo;
- AR(1) con `rho=0.50` bajo nulo;
- Student-t(5) bajo nulo;
- 40% de sesiones sin trades bajo nulo;
- el mismo panel IID con `N_eff=48`;
- efectos plantados IID (`mu=0.20`) y AR(1) (`mu=0.30`).

Criterios pre-fijados:

- tasa IID nula entre 1% y 9%;
- cada nulo adversarial ≤11%;
- multiplicidad nunca aumenta aprobaciones sobre el mismo panel;
- poder IID ≥70% y poder AR(1) ≥60%;
- `n_effective` medio AR(1) menor que el IID.

El workflow publica el JSON exacto, el digest de especificación, el fingerprint
AST y el SHA-256 del contrato en el comentario del PR. Esta calibración detecta
fallos gruesos; no prueba validez universal y no sustituye el IC primario.

## 4. Identidad de implementación y congelamiento

El digest de especificación no basta: un cambio de código puede alterar el
resultado sin cambiar el texto. Por eso `deflated_sharpe_sessions` calcula un
fingerprint SHA-256 de su AST canónico y lo embebe en la evidencia.

Promotion Registry exige dos allowlists independientes:

```text
APPROVED_G2_CONTRACT_SHA256S
APPROVED_G2_IMPLEMENTATION_SHA256S
```

Ambas permanecen vacías. Cambiar la implementación cambia el fingerprint y
vuelve a congelar promociones aunque la especificación sea idéntica.

## 5. Validación CI

- Suite dirigida G2-A1: PASS.
- Suite completa diferencial contra
  `foundation/f0b-compatibility-probe`: PASS, cero fallos nuevos.
- PR y base conservan únicamente las mismas dos identidades fallidas históricas
  de paridad BigTrap2.
- No se tocaron datos ni holdout.

## 6. Criterio de activación restante

1. registrar el JSON exacto de calibración y ambos hashes en PR #5;
2. completar revisión automatizada y/o humana;
3. aprobación explícita de Nico sobre los hashes exactos;
4. poblar ambas allowlists en un commit posterior;
5. repetir suite dirigida y diferencial;
6. recién entonces considerar mergear y activar.

No se reinterpreta ninguna campaña pasada ni se promueve retroactivamente ningún
resultado.

**Aporte al referente:** sustituye gates que confundían concentración temporal
con edge por una decisión alineada con expectativa neta persistente y ligada
criptográficamente a la especificación, al calendario y al código ejecutado.
