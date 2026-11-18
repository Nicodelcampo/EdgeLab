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
