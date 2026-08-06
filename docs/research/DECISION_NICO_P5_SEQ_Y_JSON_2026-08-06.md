# Decisión de Nico — P5 `seq_corrido` y alineación del preregistro

**Fecha:** 2026-08-06
**Decide:** Nico Buttaro
**Voto del auditor aceptado:** sí
**Tip de entrada:** `729107c`
**Rama:** `foundation/f0b-compatibility-probe`

---

## 1. Decisión A — `seq_corrido=true` con economía idéntica

**Opción elegida: B — ABSTAIN de política.**

```text
Si la subsecuencia económica ordenada es idéntica Y seq_corrido=true:
  estado de P5 = ABSTAIN
  (no PASS, no FAIL del predicado económico)

Si hay diferencia económica (tipo / orden / ts / payload):
  estado = FAIL
  (el FAIL manda sobre el corrimiento)

Si economía idéntica Y seq_corrido=false:
  estado = PASS
```

### Qué significa

- El instrumento **no aprueba solo** cuando el contador compartido corrió.
- El corrimiento **sigue publicándose** (`delta_seq_*`, `seq_corrido`,
  `footprint_mismatch_por_lado`, `n_no_economicos`, etc.).
- Un humano puede **aceptar** el ABSTAIN con acta explícita que cite esos
  campos y declare "corrimiento explicado / aceptado" **antes** de promover
  captura, pin o cierre de PRED-004.
- **No** es FAIL de regresión económica: no deshace N1; lo cierra con un gate
  de proceso enforceable por el exit code (`2` = ABSTAIN).

### Por qué no A ni C

- **A (PASS + ritual):** frágil en este proyecto; el corrimiento quedaba
  invisible si el wrapper solo miraba PASS/FAIL.
- **C (FAIL de política):** deshace N1 y hace P5 imposible entre v2.1 y v2.4
  por construcción del contador.

---

## 2. Decisión B — D1 preregistro vs contrato

**Opción elegida: enmendar el JSON PRED-004** (no dejar dos verdades).

- `docs/predictions/PRED-004_tickbar_attribution_v23.json` deja de decir
  "bit-idéntico / cualquier diferencia = FAIL" para P5.
- El predicado queda alineado al **contrato v6** del analizador (v5 + esta
  política de `seq_corrido`).
- La enmienda es **explícita y datada** dentro del propio JSON.

---

## 3. Artefactos que implementan la decisión

| Artefacto | Qué cambia |
|---|---|
| `tools/pred004_analyze.py` | `seq_corrido` + sin dif económicas ⇒ `ABSTAIN`; `p5_seq_corrido_politica` en contrato |
| `tests/bridge/test_pred004_analyze.py` | caso N1 de seq corrido espera ABSTAIN; FAIL económico sigue mandando |
| `docs/CONTRATO_ANALIZADOR_PRED-004.md` | **v6** |
| `docs/predictions/PRED-004_tickbar_attribution_v23.json` | P5 enmendado |
| Este archivo | acta de decisión |

`contrato_sha` **v6** = `4ac53dba7fee2022a3873543abbeb3eb204e260f28b6e04dfb750da67949278d`

---

## 4. Checklist operativo post-decisión (captura)

1. `git pull` tip con esta decisión.
2. T3a: copiar `oracles/BigTrap2_time1_6E_0926_v2.csv` y verificar sha
   `7d0f464fd4e1c90301799e2f854d7b5fb5a17d84f4f6600f082f2d4c0e17de27`.
3. **No** usar `run_nt8_bridge` para P5 (preflight §8 obsoleto hasta G4).
4. Correr `pred004_analyze.py p5-time ...` y leer `estado`:
   - `PASS` → economía idéntica y seq alineado.
   - `ABSTAIN` + `seq_corrido=true` → **no promover**; acta humana o investigar.
   - `FAIL` → regresión económica o diferencia real.
5. Exit codes: `0` PASS · `1` FAIL · `2` ABSTAIN.

---

## 5. Acta humana mínima si se acepta un ABSTAIN por seq

```text
Fecha / operador:
resultado_sha256 del JSON de P5:
delta_seq_min / max / n_delta_seq_distintos:
footprint_mismatch_por_lado:
n_no_economicos:
¿El corrimiento se explica por el cambio de predicado FM v2.1→v2.4? (sí/no + nota)
Decisión: ACEPTO para promoción de captura / NO ACEPTO
Firma:
```

Sin ese acta, un ABSTAIN por `seq_corrido` **no** desbloquea pin ni cierre de
PRED-004.

---

## 6. Lo que esta decisión no cierra

- T3a (bytes del oráculo en el clon)
- G4 (preflight que aún manda a `run_nt8_bridge`)
- K3 (`check_holdout` desde `p5-time`)
- Adjudicación independiente de G1
- D3 (ventana de paridad dentro de INC-005)
