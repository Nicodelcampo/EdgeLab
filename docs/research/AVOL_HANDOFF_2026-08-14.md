# aVolClusterPOI — handoff 2026-08-14

Rama: `research/bigtrap2-local-displacement-null`
Programa: Notion *Programa integral: extremos de sesión + indicadores*.

## Paridad

- 6E: `ABSTAIN_P2` 50/53. Espejo 27–20.
- ES 09-26 espejo: 35–49 (111 OFF, parquet `add9bfcd…`).
- ES P2 overlap justo 17-jun→1-jul: **67 matched / 87 oracle / 69 python**. 20 NT8-only, 2 Python-only. `ABSTAIN_P2`. 174 extras 8–16 jun (warmup NT8 de mayo).
- Mayo: usar `ES_06-26` como historia. No concatenar.

## Programa

R0 prerange 73% está (H-SWEEP-1) y no es edge vs 54–76% browniano.
R1 nulo del rango → R2 aVol covariable → R3 sello BT2 aparte → R4 una resolución extra.
BT2 tick:5/10 = pregunta nueva de absorción (definir en t), no reabrir imán.
L2: export NT8 a disco local. GEX: hermana 17y, M0/M1, no cruzar aún.
Kaggle: `NO_UPLOAD` se mantiene aunque el usuario acepte el riesgo. Repo sí; ticks no.

## Nota del auditor externo (sandbox Notion, 2026-08-14)

- `aVolClusterPOI.cs` recibido: verificado **byte-idéntico** al blob sellado `d512d91a` (v0.5) tras normalizar EOL (el adjunto trae BOM + 1 CRLF de más). Para NT8: checkout CRLF del repo, como siempre.
- `BigTrap2.cs` recibido: es v2.5.2 por marcadores internos, pero **no es byte-idéntico** al blob de `fix/bigtrap2-v252-tick-export` (`dbf22613`) ni al de esta rama (`78f6909d`). Registrado como **P-08**: resolver con `git diff` local antes de exportar oráculos.
- Registro completo de la pasada: `docs/research/AUDITORIA_EXTERNA_2026-08-14.md` (re-enlace Kaggle al programa R0–R4, evidencia VWAP/SMA/EMA y ancla de momentum intradía para L3, dictamen vs referente, matemática prop-firm). Pendientes nuevos: P-08, P-09, P-10.
