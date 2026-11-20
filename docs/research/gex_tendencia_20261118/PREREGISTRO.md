# GEX a fondo: variantes de gamma, desenlaces continuos y momentum intradía condicionado a gamma (Baltussen et al. 2021) — exploración en DESC y una apertura del holdout A5 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — fase 1 (exploración en DESC), commiteada y contada antes de correr. La fase 2 (holdout) se fija con un apéndice
commiteado después de la exploración y antes de abrir.
- **Pedido de Nico:** «indagá más en maneras de predecir tendencia, y probablemente si profundizás más en GEX vas a encontrar mejores
  maneras».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF2 en DESC y EF5 en el holdout A5. **Familia:** `DIA_TENDENCIA_A5` (la misma: su REP ya se usó y su holdout A5 sigue
  sellado).
- **Herramienta:** `tools/gex_tendencia.py`.

Antecedentes: `docs/research/dia_tendencia_20261118/RESULTADO.md` (GEX bajo → más días de tendencia, AUC 0,55, sin potencia) y
GEX1/GEX1b (menos gamma, más amplitud).
- **Literatura:** Baltussen, Da, Lammers y Martens (2021, JFE), «Hedging demand and market intraday momentum». La cobertura de gamma
  de los dealers con gamma negativa empuja el precio en la dirección del día; el momentum de la última media hora es más fuerte con
  gamma negativa.
- **Lo que ya se descartó:** el momentum intradía en forma simple (F-LIT-MACRO-CFD, CFD H1). Acá se condiciona a la gamma, que es su
  mecanismo, y se mide en futuros M1.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6.
- §2: A5, sólo meses DESC. REP ya está consumido por la familia; HOLDOUT y EMBARGO, ni siquiera en la tabla.
- §3: desenlaces en ATR20 (K35: el riesgo de un movimiento de día es el ATR); bruto y neto con mini y micro para las reglas operables.
- §4: potencia **en días, no en filas** (lección del 18-nov).
- §6: K48, GEX del cierre previo (los retornos intradía de entrada se conocen al momento de entrar).

Potencia previa:
- **Exploración:** DESC tiene ≈ 1.966 días con GEX (≈ 7.000 filas). No decide.
- **Apertura del holdout:** ≈ 880 días con GEX. Se calcula con `plan_potencia` al nivel LORD (K42), en días, con la mitad del efecto
  de DESC del candidato. Si no llega a 0,8, NO se abre.

## 1. Justificación económica
- **Gamma negativa:** los dealers cubren comprando cuando sube y vendiendo cuando baja, lo que amplifica la tendencia, y su cobertura
  se concentra al cierre (última media hora).
- **Gamma positiva:** hacen lo contrario y anclan el precio.
- **Por qué variantes:** la variable útil puede ser el signo (negativo o no), el nivel relativo o el cambio. Y la etiqueta binaria
  pierde potencia frente a la magnitud continua.

## 2. Fase 1: exploración en DESC (contada, no confirmatoria)
**Predictores de gamma** (todos del cierre de d−1):
- `g_rank250` (percentil contra 250), `g_rank60`, `g_neg` (GEX < 0), `g_z20` (z contra 20 días), `g_chg` (cambio del percentil en 1
  día), `g_esc` (GEX / precio²) y `dix_rank250`;
- más interacciones: `g_rank250` dentro de terciles de vol20 y de gap.

**Desenlaces:**
- **Y1** = |cierre − apertura RTH| / ATR20; **Y2** = rango RTH / ATR20; **E1** y **E3** (los de `dia_tendencia`);
- **Y4** (momentum del cierre, Baltussen) = signo(retorno 09:30→15:30) × retorno 15:30→16:00 / ATR20;
- **Y5** (continuación desde las 10:00) = signo(retorno 09:30→10:00) × retorno 10:00→16:00 / ATR20.

**Medidas:**
- Spearman de cada predictor con Y1/Y2;
- AUC con E1/E3;
- media de Y4/Y5 por tercil de gamma y bajo − alto, con bootstrap por fecha.

**Contador:** 7 predictores × 6 desenlaces + 12 interacciones = 54 pruebas exploratorias (EF2, nota «no confirmatoria»).

## 3. Fase 2: congelar y abrir el holdout A5 una vez
- **Hasta 3 candidatos**, elegidos por una regla fija: mayor efecto en DESC en la dirección económica, estable en ≥ 3 de 4 índices y
  en ≥ 60 % de los años, y con potencia del holdout ≥ 0,8 al nivel LORD (en días).
- **Preferencia:** uno operable (Y4 o Y5 condicionado a gamma baja, medido como regla con costos) y uno de etiqueta (Y1 o E1/E3).
- **Antes de abrir:** se commitean el apéndice, el plan de potencia y la reserva LORD.

## 4. Cómo podría refutarse
- **Ninguna variante de gamma mejora el AUC/Spearman de `g_rank250`, y el momentum condicionado no existe en DESC:** GEX no da más
  de lo medido.
- **El candidato congelado no confirma en el holdout con potencia:** lo de DESC era selección.

## 5. Contador
- **Fase 1:** `tools/registro_global.py preregistrado GEX-TENDENCIA-DESC DIA_TENDENCIA_A5 54 docs/research/gex_tendencia_20261118/PREREGISTRO.md`.
- **Fase 2:** se cuenta aparte al congelar.

## Apéndice 1 (fase 2, 2026-11-18, antes de mirar): confirmación del filtro de gamma en las reglas de tendencia, REP + HOLDOUT A5
**Decisión de Nico:** «REP+HOLDOUT, una vez». La exploración (fase 1, `RESULTADO_EXPLORACION.md`) eligió UNA hipótesis.
- **Hipótesis:** «con gamma alta (cierre previo) las reglas de tendencia rinden menos que con gamma baja».
- **Declaración obligatoria:** en los meses REP y HOLDOUT ya se había mirado el R AGREGADO de T, Franklin y SOM (mediciones de M1
  largo). El cruce con la gamma nunca se calculó fuera de DESC.

**Datos:**
- R neto por operación de T (NQ/ES/YM), Franklin (NQ/ES) y SOM `sin_finde` (NQ/ES/YM), de `docs/research/m1_largo_20261117/`;
- sólo días de meses REP y HOLDOUT de A5 (sin EMBARGO), 2011-11 → 2025-07;
- GEX de SqueezeMetrics (dato de d−1).

**Variable:** `g_rank250` del cierre previo, con los cortes CONGELADOS de DESC (por día): bajo < 0,3655 ≤ medio < 0,7390 ≤ alto
(`CORTES_DESC.json`).

**Estadístico:** canasta = suma del R neto de las tres reglas por día. Contraste = media en gamma baja − media en gamma alta, con
bootstrap por día y p unilateral.

**Decisión:**
- **CONFIRMADA:** p ≤ nivel LORD++ reservado (`DIA_TENDENCIA_A5::GEX_FILTRO_CONF_20261118`), contraste > 0 y ≥ 60 % de los años con el
  contraste positivo.
- **REFUTADA:** contraste ≤ 0, o cota superior unilateral al 95 % < 0,25 R/día (un cuarto del efecto de DESC).
- **NO_CONFIRMADA:** cualquier otro caso.

**Económico (no decide la confirmación, sí el uso):**
- canasta «sin gamma alta» con R/día > 0 (p ≤ 0,05);
- por regla y por instrumento; ORB O1 bruto (`orb_a5_20261118/OPS_DESC_REP.csv.gz`, sólo REP) como descriptivo.

**Potencia:**
- `plan_potencia("fijo", efecto DESC completo 0,874, sd·√2, n = días por tercil, alfa = nivel reservado)`; la apertura se registra
  con ese plan (K27/K42);
- con 0,75 del efecto la potencia es 0,56; está declarado.

**Contador:** 1 prueba (`GEX-FILTRO-CONF`). Una sola lectura: no se vuelve a abrir.

## Apéndice 2 (2026-11-18, antes de mirar): tres pruebas nuevas del mecanismo de la gamma
**Pedido de Nico:** «profundizá una vez más». Lo que replicó en la confirmación es el extremo: con gamma ALTA las reglas de tendencia
pierden. Se prueba la forma operable (exclusión) en datos cuyo cruce con la gamma nunca se calculó, más una predicción opuesta del
mismo mecanismo.

**Variable:** `alto` = `g_rank250` del cierre previo ≥ 0,7390 (corte congelado de DESC, `CORTES_DESC.json`); `resto` = los demás días
con GEX (desde 2011-11). Contraste = media en `alto` − media en `resto`, con bootstrap por día.
- **P1, exclusión en otros índices:** canasta T + Franklin + SOM (R neto por día) en EMD y RTY, todos los meses hasta 2025-07.
  **H1: contraste < 0.**
- **P2, predicción opuesta (reversión):** fade de impulsos LUX-IMB en NQ (`luximb_ejecucion`, z0, stop 0,5·D, R bruto por operación),
  meses DESC y REP. **H1: contraste > 0** (con gamma alta el precio se ancla y revierte más).
- **P3, ORB O1** (R bruto por operación) en sus operaciones de confirmación (holdout A5 de NQ/ES/YM, más EMD y RTY). **H1: contraste
  < 0.**

**Declaración:** en estos datos ya se miró el R AGREGADO de cada regla; el cruce con la gamma nunca.

**Decisión:**
- `LibroLord().probar("DIA_TENDENCIA_A5", "GEX_MECANISMO_20261118", [P1, P2, P3])`, con p unilaterales en la dirección de cada H1.
- **Confirmada cada una** si la rechaza LORD y ≥ 60 % de sus años tienen el signo de H1.
- **El mecanismo queda confirmado** si P1 o P3 y P2 confirman (efecto en las dos direcciones).

**Potencia previa:**
- P1: en NQ/ES/YM el efecto alto − resto fue ≈ −0,6 R/día. En EMD/RTY las reglas son más chicas en R y la potencia es menor (≈ 0,5
  con la mitad del efecto). Declarado.
- P2 y P3: N grande (≈ 60.000 fades desde 2011; ≈ 6.000 ORB), con potencia alta para 0,02 R.

**Contador:** 3 pruebas (`GEX-MECANISMO`).
