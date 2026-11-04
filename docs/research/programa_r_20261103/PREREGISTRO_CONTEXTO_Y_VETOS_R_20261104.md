# Pre-registro: Contexto Causal Común y Vetos Estructurales en R (2026-11-04)

Estado: **VIGENTE**, registrado antes de correr el meta-análisis y antes de evaluar los vetos sobre las estrategias seguidas.
Programa: [`PROGRAMA_R.md`](file:///e:/EdgeLab-port/docs/research/programa_r_20261103/PROGRAMA_R.md) · Antecedentes directos: [`PREREGISTRO_ATLAS_IDEAS_R.md`](file:///e:/EdgeLab-port/docs/research/atlas_ideas_r_20261102/PREREGISTRO_ATLAS_IDEAS_R.md) y [`PREREGISTRO_SALIDAS_Y_FILTROS.md`](file:///e:/EdgeLab-port/docs/research/programa_r_20261103/PREREGISTRO_SALIDAS_Y_FILTROS.md).
Referente: [`docs/NORTH_STAR.md`](file:///e:/EdgeLab-port/docs/NORTH_STAR.md), cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF3** (exploratorio entre familias sobre desarrollo + aplicación únicamente de lo confirmado a reglas congeladas con validación forward desde noviembre 2026).

---

## 1. Problema y lecciones incorporadas de la revisión crítica

1. **Riesgo de sobreajuste por sesgo de selección (defensa principal):**
   Las 11 estrategias seguidas en [`Estabilidad_mensual_en_R.html`](file:///C:/Users/Usuario/.gemini/antigravity/brain/3a8b386b-d489-4d86-8383-261a23f9f553/.user_uploaded/media_1793803704881_2b212293.html) (8 de la canasta v5 más `CONF-CVR-ES`, `CONF-CVR-CFD-NQ` y `TORI-NQ`) fueron seleccionadas mirando su desempeño en desarrollo y réplica. Estimar o elegir filtros directamente sobre esas 11 reglas contaminaría la inferencia. Por diseño:
   - **Los filtros de contexto y los 4 vetos se estiman y seleccionan sobre TODAS las campañas en R del repositorio** (decenas de miles de operaciones a través de todas las familias de reversión y continuación), mediante la etapa liviana `MARGINALES` ([`edgelab/research/contexto_comun.py`](file:///e:/EdgeLab-port/edgelab/research/contexto_comun.py)).
   - **A las 11 reglas sólo llega lo que pase el meta-análisis global** (DESC + confirmación en réplica).
2. **Frontera limpia de validación prospectiva:**
   El mes de octubre de 2026 (`202610`) ya fue abierto e inspeccionado en la tabla mensual de las 11 reglas. Por lo tanto, **octubre de 2026 NO es confirmación ciega** (se informa únicamente de forma descriptiva). Toda validación limpia de las variantes filtradas corre estrictamente **hacia adelante desde noviembre de 2026 (`202611+`)**.
3. **Orientación por el lado `s` de la operación y separación por mecanismo:**
   Un filtro direccional evaluado sólo por la vela $k$ suma en compras y resta en ventas, cancelándose. En [`contexto_comun.py`](file:///e:/EdgeLab-port/edgelab/research/contexto_comun.py), toda variable direccional se orienta con el lado $s \in \{+1, -1\}$ de cada operación. Además, el meta-análisis se estratifica en **`REVERSION`** vs **`CONTINUACION`** (ruptura/tendencia), ya que un régimen de tendencia fuerte favorece a la continuación y perjudica a la reversión.
4. **Colapso de pares `Futuro + CFD` del mismo activo subyacente:**
   Campañas de la misma familia sobre el futuro y el CFD del mismo subyacente (p. ej. `CVGAP-NQ-R` + `CVGAP-CFD-NQ-R`, o `U1-6E-FUT` + `U1-6E`) comparten el mismo proceso de precios subyacente y **no son independientes**. Antes de correr DerSimonian–Laird, se promedian dentro de un único cluster independiente `(FamiliaBase, ActivoSubyacente)`.
5. **Cuantiles móviles causales de 20 sesiones (cero umbrales elegidos a ojo) con calentamiento:**
   Se eliminan todos los cortes continuos arbitrarios (`ER60 > 0,60`, `75 %`, `1,5R`). Cada variable continua se discretiza usando los terciles móviles causales (`P33`, `P67`) y el decil superior (`P90`) calculados **exclusivamente sobre las hasta 20 sesiones cerradas anteriores del propio instrumento** (`ctx["calentamiento"]` precarga los 40 días calendario previos a la ventana para que la sesión 1 de evaluación ya tenga las 20 sesiones cerradas pobladas).
6. **No recortar ganancias ni acercar objetivos:**
   El Programa R ([`PREREGISTRO_SALIDAS_Y_FILTROS.md`](file:///e:/EdgeLab-port/docs/research/programa_r_20261103/PREREGISTRO_SALIDAS_Y_FILTROS.md)) y el Atlas en R ([`RESULTADO_ATLAS_IDEAS_R_20261103.md`](file:///e:/EdgeLab-port/docs/research/atlas_ideas_r_20261102/RESULTADO_ATLAS_IDEAS_R_20261103.md)) demostraron que acercar objetivos (`T1` resta $-0,070\text{R}$ en DESC y $-0,051\text{R}$ en réplica) o salir por tiempo resta $R$, mientras que el stop estructural y objetivo lejano (`S3 + T3`) suman $+0,134\text{R}$ y $+0,065\text{R}$. Por ello, `veto_muro` se evalúa **únicamente como veto binario** (nunca recorta el objetivo), no se invierte la señal en `veto_huida` y no se altera el tamaño de posición por racha.

---

## 2. Potencia y Efecto Mínimo Detectable (MDE) publicados antes de mirar

Con $\alpha = 0,05$ unilateral ($z_\alpha = 1,645$) y potencia $1 - \beta = 0,80$ ($z_\beta = 0,842$, $z_\alpha + z_\beta = 2,487$), desviación típica por operación $\sigma_R \approx 1,20\text{R}$ y un filtro/veto que descarta una fracción $f \approx 0,30$ de las operaciones:

| Nivel de análisis | Muestra efectiva | Error estándar ($\text{SE}$) | Umbral de significancia ($p < 0,05$) | **MDE al 80 % de potencia** |
|---|---|---|---|---|
| **11 reglas seguidas (`DESC + REP`, $N \approx 1.100$ ops, $\sim 280$ sesiones)** | $N = 1.100$, $f = 0,30$ | $\text{SE}(\bar{R}_{\text{pasa}} - \bar{R}_{\text{vetado}}) \approx 0,079\text{R}$ (por operación) / $\approx 0,062\text{R}$ en $\Delta \bar{R}_{\text{cartera}}$ con dependencia intradía | $+0,10\text{R}$ a $+0,13\text{R}$ | **$+0,15\text{R}$ a $+0,20\text{R}$** |
| **11 reglas sólo en `REP` ($N \approx 470$ ops, $\sim 125$ sesiones)** | $N = 470$, $f = 0,30$ | $\text{SE}(\Delta \bar{R}) \approx 0,095\text{R}$ a $0,121\text{R}$ | $+0,16\text{R}$ a $+0,20\text{R}$ | **$+0,24\text{R}$ a $+0,30\text{R}$** |
| **Meta-análisis global en R ($K = 20$ clusters independientes `Familia × Activo`, $> 50.000$ ops por tramo)** | $K = 20$, $s_c \approx 0,12\text{R}$, $\tau \approx 0,04\text{R}$ | $\text{SE}_{\text{DL}} = \sqrt{1 / \sum (s_c^2 + \tau^2)^{-1}} \approx 0,028\text{R}$ | **$+0,046\text{R}$** | **$+0,070\text{R}$** |
| **Meta-análisis por mecanismo (`REVERSION` o `CONTINUACION`, $K = 10$ clusters)** | $K = 10$, $s_c \approx 0,12\text{R}$, $\tau \approx 0,04\text{R}$ | $\text{SE}_{\text{DL}} \approx 0,040\text{R}$ | **$+0,066\text{R}$** | **$+0,100\text{R}$** |

> **Regla de interpretación fijada ex ante:** Sobre las 11 reglas por sí solas, cualquier mejora menor a $+0,15\text{R}$ no tiene potencia para distinguirse del ruido. La única vía con potencia para detectar efectos reales de $+0,05\text{R}$ a $+0,10\text{R}$ es el meta-análisis entre clusters independientes de todas las campañas en $R$.

---

## 3. Definición causal de las 7 variables de contexto y los 4 vetos (`edgelab/research/contexto_comun.py`)

Todas las primitivas se evalúan en la vela de decisión $k$ usando únicamente velas $\le k$ de la sesión actual y estadísticas de las hasta $20$ sesiones cerradas previas (`N_SES_HIST = 20`, `MIN_SES_HIST = 3`). Cero look-ahead verificado por truncado en [`tests/research/test_contexto_comun.py`](file:///e:/EdgeLab-port/tests/research/test_contexto_comun.py).

### 3.1. Siete variables de contexto común
1. `ctx_vol_diaria` (`baja`, `media`, `alta`): tercil móvil causal (sobre las 20 sesiones cerradas previas) de `rango_sesion_previa / mediana_20_previas`.
2. `ctx_atr_rel` (`bajo`, `medio`, `alto`): tercil móvil causal de `atr_sesion(14)[k] / rango_medio_vela_sesion_previa`, donde `atr_sesion` reinicia estrictamente en cada sesión CME (sin salto overnight).
3. `ctx_tendencia_favor` (`contra_fuerte`, `neutra`, `favor_fuerte`): tercil móvil causal (simetrizado) de $s \cdot (C_k - \text{Open}_{\text{sesión}}) / \text{Rango}_{\text{sesión previa}}$.
4. `ctx_vwap_favor` (`contra_vwap`, `favor_vwap`): signo de $s \cdot (C_k - \text{VWAP}_{\text{sesión}, k})$.
5. `ctx_eficiencia_contra` (`favor_o_baja`, `contra_media`, `contra_alta`): si el desplazamiento intra-sesión de 60 velas va en contra del lado $s$ ($s \cdot (C_k - C_{k-60}) < 0$), clasifica `er_sesion(60)[k]` según los terciles móviles causales `P33` y `P67` de las 20 sesiones previas; si va a favor o `er_sesion(60) <= P33`, vale `0` (`favor_o_baja`).
6. `ctx_hora_ny` (`overnight_18_03`, `londres_03_0930`, `ny_manana_0930_12`, `ny_tarde_12_16`, `cierre_16_17`): bloque horario en Nueva York ajustado por horario de verano (`regimen_sesion.minuto_ny`).
7. `ctx_vol_rel` (`bajo`, `medio`, `alto`): tercil móvil causal de `media_volumen_sesion(30)[k] / volumen_medio_vela_sesion_previa`.

### 3.2. Cuatro vetos estructurales binarios (`0 = pasa`, `1 = vetado`) con respaldo verificado en el corpus SSRN
1. **`veto_horizonte` (Horizonte insuficiente antes del cierre CME):**
   - **Definición:** Veta entradas desde las `16:00 ET` hasta el cierre de sesión (`16:00 <= hora_ny < 17:00 ET`, menos de 60 minutos de horizonte antes del cierre forzoso).
   - **Fundamento en el corpus:** [`corpus/ssrn/cerebro/hallazgos_por_mercado.md#L728`](file:///e:/EdgeLab-port/corpus/ssrn/cerebro/hallazgos_por_mercado.md#L728) (doc `146`) y [`#L736`](file:///e:/EdgeLab-port/corpus/ssrn/cerebro/hallazgos_por_mercado.md#L736) (doc `214`): los cierres forzados por fin de horizonte antes de converger concentran las pérdidas de cartera.
2. **`veto_muro` (Muro estructural interpuesto entre la entrada y el objetivo):**
   - **Definición:** Veta la operación (`1`) si entre el precio de entrada $e$ y el objetivo $tp$ ($\text{ mín}(e, tp) + \text{tick} \le \text{nivel} \le \text{máx}(e, tp) - \text{tick}$) se interpone alguno de los niveles estructurales mayores ya cerrados y conocidos: `PDH`, `PDL`, `ONH`/`ONL` (expuestos únicamente tras las `09:30 ET` cuando el rango overnight ya cerró) o `VWAP` de la sesión. **No recorta el objetivo.**
3. **`veto_huida` (Impulso direccional en contra en el decil superior `> P90` del propio activo):**
   - **Definición:** Veta la operación (`1`) cuando el cambio de 60 velas dentro de la sesión va en contra del lado $s$ ($s \cdot (C_k - C_{k-60}) < 0$) y la eficiencia de Kaufman intra-sesión `er_sesion(60)[k]` supera el **percentil 90 móvil causal (`P90`)** de las 20 sesiones cerradas previas del propio instrumento.
   - **Fundamento en el corpus:** [`corpus/ssrn/cerebro/hallazgos_por_mercado.md#L337`](file:///e:/EdgeLab-port/corpus/ssrn/cerebro/hallazgos_por_mercado.md#L337) (doc `101`), [`#L367`](file:///e:/EdgeLab-port/corpus/ssrn/cerebro/hallazgos_por_mercado.md#L367) (doc `118`) y [`LEDGER_EXPERIMENTOS.md#L12-L15`](file:///e:/EdgeLab-port/corpus/ssrn/cerebro/LEDGER_EXPERIMENTOS.md#L12-L15) (`EXP-002`): la probabilidad de reversión colapsa cuando la envolvente direccional supera el decil extremo de persistencia.
4. **`veto_liquidez_macro` (Valle de liquidez nocturno `18:00–02:00 ET` o shock macro Tier-1 `±5 min`):**
   - **Definición:** Veta entradas durante la ventana ilíquida de Globex (`18:00–02:00 ET`) o dentro de `±5 min` de un anuncio macroeconómico programado Tier-1 (`eventos.TIPOS_TIER1`).
   - **Fundamento en el corpus:** [`corpus/ssrn/cerebro/hallazgos_por_mercado.md#L101`](file:///e:/EdgeLab-port/corpus/ssrn/cerebro/hallazgos_por_mercado.md#L101) (doc `114`) y [`#L483`](file:///e:/EdgeLab-port/corpus/ssrn/cerebro/hallazgos_por_mercado.md#L483) (doc `169`): retiro de liquidez en el libro de órdenes 5 minutos antes del anuncio y selección adversa en horarios de libro delgado.

---

## 4. Estadístico primario único y compuertas secundarias declaradas

### 4.1. Estadístico primario único (meta-análisis entre clusters independientes)
Para cada etiqueta $(v, \ell)$ dentro de un estrato ($S \in \{\text{GLOBAL}, \text{REVERSION}, \text{CONTINUACION}\}$):
1. En cada campaña $i$ con al menos $30$ operaciones y $10$ sesiones en el nivel $\ell$, se calcula el diferencial respecto a la media de su propia campaña:
   $$d_{i,\ell} = \bar{R}_{i,\ell} - \bar{R}_i, \qquad v_{i,\ell} = \frac{\hat{\sigma}_{i,\ell}^2}{\text{sesiones}_{i,\ell}}.$$
2. **Colapso `Futuro + CFD`:** Las campañas que comparten `(FamiliaBase, ActivoSubyacente)` se promedian en un único cluster independiente $c$:
   $$y_{c,\ell} = \frac{1}{|I_c|} \sum_{i \in I_c} d_{i,\ell}, \qquad V_{c,\ell} = \frac{1}{|I_c|} \sum_{i \in I_c} v_{i,\ell}.$$
3. **Estadístico primario ($\hat{\mu}_{\text{DL}}$):** Estimador de efectos aleatorios de DerSimonian–Laird / contracción empírico-bayesiana ([`hallazgos_por_mercado.md#L781`](file:///e:/EdgeLab-port/corpus/ssrn/cerebro/hallazgos_por_mercado.md#L781), doc `301`) sobre los $K \ge 4$ clusters independientes:
   $$\hat{\mu}_{\text{DL}} = \frac{\sum_{c=1}^K w_c^* y_{c,\ell}}{\sum_{c=1}^K w_c^*}, \qquad w_c^* = \frac{1}{V_{c,\ell} + \hat{\tau}^2}, \qquad z_{\text{DL}} = \frac{\hat{\mu}_{\text{DL}}}{\text{SE}_{\text{DL}}}.$$
4. **Criterio de descubrimiento y confirmación:**
   - **DESC:** Benjamini–Hochberg $q \le 0,10$ sobre las etiquetas evaluadas.
   - **REP (sólo para las descubiertas en DESC):** Mismo signo que en DESC y $p_{\text{unilateral}} < 0,05$ en la ventana de réplica.

### 4.2. Compuertas secundarias obligatorias para aplicar un veto confirmado a las 11 reglas
Un veto o filtro confirmado en el meta-análisis global sólo se adopta sobre las 11 reglas seguidas si además supera las tres compuertas secundarias en el conjunto de desarrollo (`DESC + REP`, Ago 2025 – Sep 2026):
1. **Consistencia transversal:** Al menos **8 de las 11 reglas** (o $\ge 70\%$ de las reglas afectadas por el veto) muestran $\Delta \bar{R} \ge 0$.
2. **Estabilidad Leave-One-Month-Out (LOMO):** Al retirar cualquiera de los 14 meses de desarrollo (`202508`–`202609`), el cambio medio $\Delta \bar{R}$ de la cartera filtrada se mantiene $> 0$ en los **14/14** subperíodos.
3. **Control nulo mensual (`EXP-004b`, $B = 2.000$):** El $\Delta \bar{R}$ observado supera al percentil 95 ($p_{\text{nulo}} < 0,05$) de descartar al azar exactamente la misma cantidad de operaciones dentro de cada `(regla, mes)`.

---

## 5. Registro de multiplicidad y linaje
- **Linaje:** `ATLAS_CONTEXTO_VETOS_R` en [`docs/research/LINAJES.jsonl`](file:///e:/EdgeLab-port/docs/research/LINAJES.jsonl), con padres `["ATLAS_IDEAS_R", "PROGRAMA_R_SALIDAS"]` y herencia `"bruto"`.
- **Contador global:** `programa_r/contexto_vetos_r/20261104` en [`docs/research/TRIAL_REGISTRY_GLOBAL.jsonl`](file:///e:/EdgeLab-port/docs/research/TRIAL_REGISTRY_GLOBAL.jsonl) con cota de `220` pruebas (`96` etiquetas por ventana $\times 2$ ventanas + evaluaciones agrupadas).

