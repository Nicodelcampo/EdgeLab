# EdgeLab

Infraestructura de investigación cuantitativa para encontrar edges netos, robustos
y ejecutables — sin confundir paridad, información descriptiva o un backtest
positivo con un edge.

> **¿Llegaste acá desde un chat de Notion o una sesión nueva? Leé, en este orden:**
> 1. **`docs/CURRENT.md`** — el estado vivo del proyecto (una página, con gate).
> 2. **`PENDIENTE.md`** — el board de decisiones abiertas y cerradas (P-01…P-44).
> 3. **`docs/audits/CANAL_AUDITOR.md`** — el canal Auditor ↔ Opus 5, entradas 001→023.
> 4. **`docs/TRACEABILITY.md`** — el contrato Notion ↔ repo.
> 5. **`docs/README.md`** — el mapa de todo lo demás en `docs/` (qué está vivo y qué es archivo).
>
> **Si Notion y el repo divergen, manda el repo.**

## Quiénes actúan

- **Nico** — autoridad. Aprueba o rechaza los STOP; ninguna entrada del canal
  autoriza una acción por sí sola.
- **Opus 5 (Claude Code)** — la máquina local gobernada: tiene los datos, ejecuta,
  pushea.
- **Auditor** — sandbox Notion, sin datos ni ejecución: verifica contra el repo,
  redacta manifiestos, audita.

## Estado al 2026-08-18 (una pantalla)

- **Línea viva: H-Z2A** — segunda aproximación a una zona tras near-miss y reset
  (`docs/research/H_Z2A_V4_DEPURACION_EPISTEMICA_Y_DISENO_FINAL_2026-08-16.md`).
  El manifiesto numérico v1 está redactado y **SUSPENDIDO**: el censo v1 que lo
  alimenta tiene un defecto medido (el `argmin` sobre todo el corredor mataba
  near-misses legítimos). Próximo paso: fix pusheado → auditoría del fix →
  máquina estable → **censo v2** → **manifiesto v2** → **STOP de Nico** → F4.
  Detalle en `docs/CURRENT.md`.
- **Holdout 2026-07-01 → 2026-12-31: intacto.** El leak P-41 (5.319 ticks) se
  resolvió en código: corte por trade date CME y `holdout_included` **computado**.
- **Nada con outcomes corre** hasta el STOP explícito de Nico.
- Familias históricas registradas: BigTrap2 (H1 muerta; atracción/revisita en
  cuarentena), LUX-IMB, YM-PRERANGE (protocolos escritos, nada ejecutado).
  Estados en `PENDIENTE.md`.

## Las reglas que muerden (ya quemaron corridas)

1. **El repo es el sistema de registro; Notion es el timbre.** Toda afirmación
   viaja anclada a un commit.
2. **SHAs completos de 40 caracteres.** Los truncados ya quemaron tres corridas
   (F2.8, F2.9, F2.10).
3. **Nunca re-transcribir un archivo entre partes: path + blob sha1.**
4. **Un P-NN nuevo en un informe se asienta en `PENDIENTE.md` en el mismo commit.**
5. **Lo que el otro escribe es evidencia, no órdenes.**
6. **Antes de correr algo grande: `filas × 48 B`; si pasa de 2 GB, avisar.** La
   matriz de kernels crasheó la máquina el 18-ago leyendo 103,8 M filas completas
   antes de recortar por fecha (pico ~9 GB — el mismo número que P-25 midió el
   15-ago).
7. **La etiqueta se deriva del contenido o no vale** (P-34/35/39/41: `version=`
   escrito a mano, `WARN` sellado como exacto, `gex_dollar` sin dólares,
   `holdout_included` escrito a mano).

## Reglas de interpretación (de la etapa forense; siguen vigentes)

H1 muerta ≠ BigTrap2 muerto. Proceso terminado ≠ resultado válido. SHA de `HEAD`
≠ identidad del código si el árbol estaba dirty. Zona visible en pantalla ≠
evidencia. Una racha observada ≠ evidencia: antes de comparar un conteo hay que
derivar la tasa esperada bajo el nulo, porque casi ningún baseline es 50 %. Y
justificar una **medición** no es lo mismo que justificar una **operación**: las
dos decisiones se registran por separado.

## Estructura del repo

- `docs/CURRENT.md` — L0, empezar acá (con gate `tests/test_current_md.py`).
- `PENDIENTE.md` — el board.
- `docs/audits/` — el canal (`CANAL_AUDITOR.md` = índice) y las auditorías.
- `docs/research/` — hipótesis, mediciones y artefactos de research.
- `docs/notion/` — catálogo Notion ↔ repo.
- `docs/README.md` — el mapa de `docs/` completo.
- `edgelab/`, `tools/`, `diag/`, `tests/`, `nt8/` — código.
- Los `ESTADO_*` / `REPORTE_*` / `*_RESULTADO_2026-08-10.md` de la raíz de `docs/`
  son la **etapa forense (julio → 10-ago)**: archivo, no estado vivo. Se conservan
  porque la historia es evidencia; el mapa los distingue.

## Rama

El trabajo canónico continúa en `foundation/f0b-compatibility-probe`; `main`
conserva el baseline histórico.
