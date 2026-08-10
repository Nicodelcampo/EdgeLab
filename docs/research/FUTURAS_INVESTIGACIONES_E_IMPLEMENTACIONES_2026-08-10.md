# Investigaciones e implementaciones futuras — 2026-08-10

Nada de este documento afirma un edge ni autoriza outcomes.

## P0 — integridad

1. Resolver incidente de procedencia Git/worktree.
2. Reemitir artefactos ambiguos desde commit limpio.
3. Adjudicar reruns corregidos y barrido de parámetros.
4. Resolver drift v2.5.1↔v2.2.
5. Publicar commits locales y verificar hashes.
6. Integrar `/data/` sin mezclar la tarea separada.

## Mejoras de procedencia

- `git_head()` con `git -C <repo_root>` explícito;
- `head_start`, `head_end`, `dirty_start/end`;
- hash del diff tracked y manifiesto hash de untracked;
- hashes de fuentes realmente importadas;
- repo root, git dir y worktree;
- ejecutable/venv/dependencias;
- run ID, PID, timestamps y comando;
- una worktree por sesión y un writer por directorio.

## Familia LUX-IMB (OG/VI) — línea independiente

El indicador `Imbalance Detector [LuxAlgo]`, restringido a **Opening Gap** y **Volume Imbalance** y **sin** Fair Value Gap, constituye una familia distinta de BigTrap2. No hereda resultados, poblaciones, costos, oráculos ni presupuesto de multiplicidad.

**Protocolo completo:** [`docs/research/H-COND-1_LUX-IMB_PROTOCOLO.md`](H-COND-1_LUX-IMB_PROTOCOLO.md)

- **Origen:** el operador reporta reacción visual del precio en estas zonas sobre ES en 1 minuto. La pregunta admitida no es si la intuición es correcta, sino si es distinguible de un sesgo de observación.
- **Amenaza dominante:** las zonas mitigadas desaparecen automáticamente del gráfico, por lo que el conjunto visible está compuesto casi por construcción de zonas no atravesadas. Ningún análisis puede usar el estado dibujado: se exige ledger as-of con zonas muertas y auditoría antirepintado.
- **Separación de subfamilias:** OG es un intervalo sin negociación, concentrado en horarios delgados y cortes de sesión, por lo que es casi colineal con la fase de sesión. VI implica negociación sin consenso y es mucho más denso. Se estiman por separado.
- **H-COND-1:** ¿existe una función de efecto condicional no trivial, aprendida fuera de muestra, que prediga dónde las zonas hacen algo?
- **H-PERCEPT-1:** test ciego de dos brazos que mide directamente cuánto de la intuición proviene del sesgo de supervivencia.
- **Gate:** bloqueado hasta cerrar P0, porque ES está en cuarentena y ES es el contrato observado.

## Reglas transversales nuevas

- **MDE obligatorio:** todo resultado nulo publica su efecto mínimo detectable. Un nulo sin MDE no distingue "no hay efecto" de "no podíamos verlo".
- **Canal no direccional siempre presente:** además del efecto con signo se mide magnitud absoluta, volatilidad realizada y distribución completa, porque un efecto bidireccional real puede promediar exactamente cero.
- **Ledger as-of por familia de zonas:** censo que incluya las zonas muertas y distinga fin por mitigación de fin por vencimiento de dibujo.
- **Registro de familia previo al estudio:** indicador, subfamilias habilitadas, parámetros congelados y presupuesto de multiplicidad propio.

## H-ATTR-1 — atracción/revisita

Nulos emparejados por sesión, hora, cercanía, altura y liquidez. Adjudicar solo después de reemisión verificable.

## H-LIFE-1 / H-DEP-1 / H-STATE-1

Lifecycle, competing risks, toques ordinales y estado continuo. Descripción antes de monetización.

## H-BARSPEC-1

Separar `ticks_per_row` de `bar_spec`. La réplica `tick:25` fue reportada pero queda en cuarentena hasta resolver procedencia.

## Parámetros restantes

El barrido local de 11 celdas reportó invariancia y un cruce interno valioso (`max_touches=1`: 29,9% vs F1.3: 30,3%). Debe revisarse/reemitirse antes de elevarlo. Renombrar la fase para no confundirla con F4 constitucional.

## Generalización ES/NQ/YM

- ES/NQ specs fueron reportados como agregados localmente.
- ES cubrió 201 sesiones y el proceso terminó, pero no se aportaron resultados y el artefacto está en cuarentena.
- YM mantiene 23,2M ticks ingeridos y spec local.
- Generalizar target-free primero; nunca transportar costos de 6E.

## F4 constitucional

Solo tras P0 y manifiesto aprobado. Curvas de retorno por estado/evento, controles y errores por sesión, sin argmax ni estrategia.

## Monetización posible — solo si F4 pasa

Creación, invalidación, aproximación, expiración, toque n-ésimo, confluencia o meta-label de hazard. Evaluar una sola por vez con costos específicos.

## Condiciones de cierre

- procedencia irreconstruible → reemitir o retractar;
- atracción no sobrevive nulos → cerrar antes de F4;
- F4 nulo → cierre predictivo;
- información sin economía → `informativo pero sub-fee`;
- efecto aislado → fragilidad.
