# Cartera Lucid intradía (8 estrategias, NQ + ES en micros): resultado y armado en NT8

> **Superado en parte (2026-11-25, tarde)**: el armado de 8 instancias quedó reemplazado por una sola estrategia (`EdgeLabCartera`, preset Intradía) y las probabilidades se recalcularon con el mínimo intradía (150K: 0,25 contraída). Ver `docs/research/cartera_nt8_20261125/RESULTADO.md`.

Estado: RESULTADO (descriptivo de cuenta, plan `PLAN.md` con enmienda 1; no suma pruebas). Configuración PROPUESTA: operar con
dinero real lo decide Nico.  
Fecha: 2026-11-25  
Herramienta: `tools/cartera_lucid.py` (`simular` → `PLANES.json`; `contratos` → contratos del trimestre). Corrida 1 (sólo 25K) en
`PLANES_corrida1_25K.json`.

## Qué dio
- **La cartera no entra en una 25K ni conviene en una 50K.** Con 1 micro por estrategia el P&L diario tiene sd ≈ $690 y peor día
  −$2.150; la pérdida máxima de la 25K es $1.000. Ahí el plan "ganador" es apostar más grande (2 micros cada una): p_ganar 0,17
  con la media contraída y 0,12 si no hubiera ventaja: es lotería, no cartera.
- **En la 150K, 1 micro por estrategia** (`INV_VOL|B200`: con stops de $150–300 por micro todas quedan en 1) es la configuración
  donde la ventaja pesa:
  | media supuesta | P(cobrar más que la evaluación) | valor esperado por intento | retiros medios |
  |---|---|---|---|
  | la de 2020–2026 | 0,47 | +$1.457 | — |
  | contraída a la mitad (criterio) | 0,27 | +$561 | 0,51 |
  | cero (sin ventaja) | 0,12 | +$48 | — |
  Pasa la evaluación ≈ 37 % de las veces, ≈ 84 sesiones por ciclo. Desde 2024 (contraída): 0,25. Ganancia media por mes con 1 micro
  cada una: 2020 $294, 2021 $1.438, 2022 $2.582, 2023 $1.252, 2024 $1.482, 2025 $2.130, 2026 $605.
- **Asegurar retiros no es posible con esta ventaja**: lo que sube la probabilidad es bajar el riesgo frente al drawdown (cuenta
  grande, tamaño mínimo), no subir el tamaño. Los pesos inverso-volatilidad recién se aplican con cuentas donde el riesgo base
  permite 2+ micros en las estrategias de stop chico; hoy, en micros, el mínimo de 1 ya iguala a las 8.
- Auditoría: la primera selección no filtraba planes por encima del tope de micros de Lucid (25K: 32 simultáneos > 20); corregido
  antes de elegir. Los pnl_pts de NT8 ya traen 1 tick de deslizamiento y además se descuenta la fricción canónica del micro
  (conservador).

## Armado en NT8 (cuenta LucidFlex 150K, plan 40 % + DLL)
Ocho instancias en la misma cuenta, todas con veto de noticias (±2 min; FOMC ±5), contratos fijos = 1 y plano a las 16:40 ET
(nuevo: también 20 min antes del fin de sesión en los cierres tempranos de feriado, que antes dejaban posiciones abiertas):
| Gráfico | Estrategia NT8 | Parámetros |
|---|---|---|
| MNQ 1 min | EdgeLabCandidataFS | Módulo T_stop100_BE15R_calFalse, Activo MNQ, Contratos fijos 1 |
| MNQ 1 min | EdgeLabCandidataFS | Módulo R_osc30_end660_ATR50, Activo MNQ, Contratos fijos 1 |
| MNQ 1 min | EdgeLabCandidataFS | Módulo Z_b15_e20_eff40_ATR50, Activo MNQ, Contratos fijos 1 |
| MNQ 1 min | EdgeLabCandidataFS | Módulo V_nm25_noCap_mae30, Activo MNQ, Contratos fijos 1 |
| MNQ 1 min | EdgeLabRQ5 | Activo MNQ, Cantidad fija 1, Riesgo USD 0 (resto por defecto) |
| MNQ 1 min | EdgeLabCandidataFranklin | Activo MNQ, Veto PREAPERTURA no, Contratos fijos 1 |
| MES 1 min | EdgeLabRQ5 | Activo MES, Cantidad fija 1, Riesgo USD 0 |
| MES 1 min | EdgeLabCandidataES5N | Activo MES, Contratos fijos 1 |
Cada trimestre: `python tools/cartera_lucid.py contratos --B 200 --hasta <fin del trimestre>` (con las corridas NT8 al día) dice
si alguna estrategia pasa a 2 micros.

## Fuera de esta cartera
- C2_VZ (NQ, ES) y SOM sin_finde mantienen de noche: no van en Lucid. Son la base de una segunda cartera sólo si se abre una cuenta
  que permita tenencia nocturna (en `cuentas_activas.json`, la FTMO Swing planificada).
- La 25K en rescate sigue con su configuración (no admite esta cartera).
