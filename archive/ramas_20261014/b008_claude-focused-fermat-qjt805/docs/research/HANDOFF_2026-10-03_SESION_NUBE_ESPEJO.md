# Traspaso de la sesión en la nube del 26/09 al 03/10/2026 — espejo, indicador y acceso a Kaggle

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Rama:** `claude/focused-fermat-qjt805` (PR #62, draft; base `feat/unified-nt8-viewer-20260920`).
**Para qué es:** recoger lo que **sólo se dijo en el chat** y no quedó en otro documento. Lo medido y lo no medido
sigue en `ESPEJO_MEDIDO_Y_NO_MEDIDO.md`; este archivo no lo reemplaza.

## 1. Leer primero
1. `docs/research/ESPEJO_MEDIDO_Y_NO_MEDIDO.md`: qué se midió y qué no, y la regla de cierre de la familia.
2. `docs/research/MANIFIESTO_ESPEJO_SIM_COMPLEMENTOS_MNQ_20260928.md`: el pre-registro pendiente (§3).
3. `docs/research/REGISTRO_FAMILIA_ESPEJO_IND_20260926.md`, secciones 6 y 7: el indicador y la semejanza v2.
4. `docs/research/HANDOFF_2026-09-26_HFT_REV_Y_ESPEJO.md`: la base de la sesión.

## 2. Lo que cambió el panorama y no está escrito en otro lado

### 2.1 El nulo f de ESPEJO-MACRO está en duda
- La sesión local verificó en paseos sintéticos que el nulo f no es exacto (auditoría 056 §4). Sobre los eventos
  resueltos queda sesgado entre +1 y +5 pp, y hasta +25 pp cuando hay censura.
- **No lo verifiqué yo:** lo tomo de su documento.
- **Consecuencia:** el exceso de +9,4 pp al 75 % (replicado en ES, NQ e YM) puede ser en parte o del todo un artefacto.
  Mis estudios macro excluían los censurados.
- **Con el nulo simulado N1, ES a 100 ticks al 75 % da exceso 0,000.**
- **Pendiente:** re-medir ESPEJO-MACRO con N1 (`edgelab/research/espejo_nulo.py`, rama `foundation`).
- **Mientras tanto,** el veredicto «SÍ, seguir» del tamiz está sobreestimado.
- **Lo que no depende del nulo:**
  - la ganancia neta E2 (+1,5 a +12 t por operación en ES, con IC que toca el cero);
  - los contrastes entre vueltas parecidas y poco parecidas.

### 2.2 PIVOTES-BARRIDO-MES quedó refutado
- 272 mil pivotes se barren como el azar. El +5 pp del control venía de selección.
- Yo había recomendado priorizarlo: **esa recomendación ya no vale.**

### 2.3 Resultados de los días siguientes (de títulos de commits y READMEs; no los re-corrí)
- **IPC:**
  - ESCALONADAS: 0 de 180 en ES y 0 de 648 en MNQ.
  - IPC 25t etapa A: 0 de 23 celdas sostienen. El positivo venía de controles contaminados con zonas futuras.
- **Espejo:**
  - ESPEJO-NICO-100T: 0 de 8.
  - VOLLIMP: 0 de 24.
  - Espejo × picos en ES: peor con picos en 4 de 4 celdas.
- **Campaña de medias móviles y momentum, multiactivo (29/09 al 2/10):** cada prueba termina en «sin ventaja validada».
  - EMA3: 0 de 24. Momentum cruzado: 0 de 24.
  - Pullback a EMA20: sin avance económico.
  - MGC: TP400 pasa MCPT p = 0,024, pero DSR 0/42, BH 0/42 y SPA p = 0,34.
- **Qué falta mirar:** las ramas `research/*` de Nicodelcampo, `docs/research/mgc_ema_20261002/` y el embudo gobernado
  `edgelab/funnel/` (`docs/research_funnel_playbook.md`).

### 2.4 `origin/main` ya no es el baseline
- Tiene 9 commits de Nicodelcampo, y el histórico de `foundation` no está dentro de él.
- `CLAUDE.md` todavía dice «main = baseline, no mergear». Hay que reconciliarlo.

## 3. Lo que hice en esta sesión (todo está pusheado)
- Estudios y registros:
  - HFT-REV, ESPEJO-SIM, ESPEJO-MACRO y su parte económica (E2);
  - diagnóstico de curva en `artifacts/research/espejo_macro/CURVA/`;
  - Fase 0 de ESPEJO-MÁS-ALLÁ (sin heterogeneidad visible más allá de A).
- Indicador ESPEJO-IND (kernel Python, port JS con paridad, capa del visor, 18 tests):
  - atributos de zona no lista y aceptación en B;
  - semejanza v2 por nivel de precio.
- Diálogo único de Indicadores en el visor.
- Pre-registro de ESPEJO-SIM-COMP (10 cruces; **sin correr**).

## 4. Pendientes y decisiones abiertas
1. **Re-medir ESPEJO-MACRO con el nulo N1** (§2.1).
2. **ESPEJO-SIM-COMP:** se corre sólo con el OK de Nico.
   - Faltan datos: confirmar NQ o MES a 25 ticks para la tercera muestra y traer `espejo_nulo.py`.
   - El orden «después de PIVOTES-BARRIDO» ya se cumplió: PIVOTES resultó refutado.
3. **Imanes** de ESPEJO-MÁS-ALLÁ: Nico tiene que definir qué cuenta como imán. Requisitos en §4.3 del borrador.
4. **Juicios ✓/✗ de Nico** sobre las zonas no listas y las vueltas «parecidas». Si el acierto es < 70 %, la definición
   no captura lo que Nico ve.
5. **Mapa de MAE/MFE** de los eventos macro: no se arrancó, y primero conviene el punto 1.
6. **Indicador en 25 ticks:** probarlo con un bundle de 25t. Sólo se probó en 5 minutos, donde las franjas no listas
   salen angostas.
7. **`viewer/gc_audit/index.html`:** preguntar si se archiva.
8. Reconciliar `origin/main` con `foundation` (§2.4).
9. Holdout y abr–jun: sin abrir.

## 5. Arquitectura propuesta para el servidor Debian con la API de Claude (sólo conversada)
Una idea de Nico, que no quedó escrita en el repo. La estructura que se comentó:
registro de la hipótesis → compuerta económica y de potencia → validación target-free → contraste contra nulo en
descubrimiento → replicación en otra partición → retornos (con OK) → confirmación única y holdout.

**Riesgos y cómo se controlan:**
- Multiplicidad: contador global de FDR en línea (LORD, SAFFRON o alpha-investing).
- Datos limitados: particiones selladas por código, no por disciplina.
- Error en el instrumento de medición: calibración sintética obligatoria; sobre un paseo sin memoria todo nulo y todo
  control debe dar exceso 0. Eso habría cazado el sesgo del nulo f el primer día.
- Sesgo del generador: roles separados de generador y auditor adversarial.

El embudo `edgelab/funnel/` de la rama `main` ya tiene parte del esqueleto: particiones D0/D1/D2, ledger encadenado,
hipótesis del LLM sin auto-promoción.
Faltan el contador global de FDR, el banco sintético de calibración y la compuerta económica automática.

## 6. Acceso a Kaggle (estado al 03/10)
- Se creó una credencial de entorno «Kaggle»: encabezado `Authorization: Bearer`, host `www.kaggle.com`.
- **Una sesión que ya estaba abierta no la ve.** Una sesión nueva sí.
- **La credencial no es una variable de entorno:** se agrega sola al encabezado en las llamadas hacia el host
  permitido.
  - Hay que usar la API web con `curl`; el cliente `kaggle` de línea de comandos busca el token en una variable de
    entorno y no la encuentra.
  - Si las descargas redirigen a `storage.googleapis.com`, ese host también tiene que estar permitido.
- Verificar con una llamada de lectura, por ejemplo listar los datasets propios del usuario.
- **El token que se pegó en el chat el 26/09 debe revocarse** (Kaggle → Settings → API).
- Nunca guardar tokens en archivos del repo, ni pedir que se peguen en el chat.

## 7. Cuidados de procedencia
- La sesión local escribe en esta misma rama: antes de pushear, `git fetch` y merge, como pasó el 28/09 con tres
  commits del visor.
- Los bundles de prueba del visor (`bundles/`) están gitignorados. El de ES a 5 minutos que usé era local.
- En este entorno, los tests de módulos que importan `jsonschema` no cargan por una dependencia ausente. No es un fallo
  de código.

Aporte al referente: deja visible lo que sólo estaba en el chat: el nulo f en duda, las ideas refutadas, la arquitectura
del servidor y el estado del acceso a Kaggle.
