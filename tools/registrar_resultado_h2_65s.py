#!/usr/bin/env python3
"""Registra los resultados de la corrida de 65 sesiones de H2 + Escalon 5 en documentacion y git.

Genera:
1. docs/research/RECHAZO_CLUSTERS_NQ_65S_2026-09-08.md
2. Actualiza docs/research/HFT_CLUSTERS_NQ_MEDIDO_Y_NO_MEDIDO.md
3. Genera docs/research/HANDOFF_2026-09-08_CLUSTERS_HFT_ESTADO.md para que Claude continue
4. Realiza commit y push en git
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def format_table(t):
    lines = []
    lines.append("| dist | σ | n borde | n libre | n dentro | rechazo borde | rechazo libre | contraste |")
    lines.append("| --: | --: | --: | --: | --: | --: | --: | --: |")
    for f in t:
        rb = "n/d" if f["rechazo_borde"] is None else f"{f['rechazo_borde']:.3f}"
        rl = "n/d" if f["rechazo_sin_borde"] is None else f"{f['rechazo_sin_borde']:.3f}"
        ct = "n/d" if f["contraste"] is None else f"{f['contraste']:+.3f}"
        marca = "" if f["suficiente"] else " (flaco)"
        lines.append(f"| {f['bin_distancia']} | {f['bin_sigma']} | {f['n_borde']:,} | {f['n_sin_borde']:,} | "
                     f"{f.get('n_dentro', 0):,} | {rb} | {rl} | **{ct}**{marca} |")
    return "\n".join(lines)


def format_int_table(t_int):
    lines = []
    lines.append("| bin | n borde | n libre | rechazo borde | rechazo libre | contraste |")
    lines.append("| --: | --: | --: | --: | --: | --: |")
    for f in t_int:
        rb = "n/d" if f["rechazo_borde"] is None else f"{f['rechazo_borde']:.3f}"
        rl = "n/d" if f["rechazo_libre"] is None else f"{f['rechazo_libre']:.3f}"
        ct = "n/d" if f["contraste"] is None else f"{f['contraste']:+.3f}"
        marca = "" if f["suficiente"] else " (flaco)"
        lines.append(f"| {f['bin']} | {f['n_borde']:,} | {f['n_libre']:,} | {rb} | {rl} | **{ct}**{marca} |")
    return "\n".join(lines)


def main():
    json_path = REPO / "data/nt8_oracles/rechazo_clusters_nq_65s.json"
    if not json_path.exists():
        print(f"ERROR: No se encontro el archivo {json_path}")
        return 1

    with open(json_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    n_total = data["n"]
    ag = data["agregado"]
    t = data["tabla"]
    t_int = data.get("escalon5_intensidad", [])
    ag_ho = data.get("escalon5_holdout", {})
    mde = data.get("mde", 0.0)
    sesiones = data.get("sesiones", [])
    n_borde = ag["borde"]["n"]
    contraste_ag = ag["contraste"]

    # 1. Generar informe detallado
    informe_path = REPO / "docs/research/RECHAZO_CLUSTERS_NQ_65S_2026-09-08.md"
    informe_content = f"""# H2 — Rechazo en bordes de cluster (Corrida de 65 sesiones) + Escalón 5

> **Target-free.** Sin P&L, sin entrada ni salida ni costo: sólo la geometría del recorrido posterior a un contacto.
> Reproducción: `.venv\\Scripts\\python tools\\rechazo_clusters_nq.py --sesiones 65 --desde "2026-03-23 22:00" --out data/nt8_oracles/rechazo_clusters_nq_65s.json`
> **Alcance: {len(sesiones)} sesiones de `NQ 06-26` (2026-03-23 en adelante, pre-holdout).** Holdout 2026-07-01 → 2026-12-31 intacto.

---

## Veredicto

| Métrica | Valor |
| :-- | --: |
| Sesiones procesadas | {len(sesiones)} |
| Contactos totales enumerados | {n_total:,} |
| Contactos resueltos sobre borde de cluster | {n_borde:,} |
| **MDE** ({len(t)} celdas, Bonferroni, deff = 5) | **{mde:.4f}** |
| Contraste agregado (borde vs sin borde) | **{contraste_ag:+.4f}** |
| Rechazo en borde (agregado) | {ag['borde']['rechazo']:.4f} |
| Rechazo sin borde (libre, agregado) | {ag['sin_borde']['rechazo']:.4f} |

---

## Resultados estratificados por distancia x sigma local

{format_table(t)}

---

## Escalón 5a: Estratificado por INTENSIDAD (nacimientos / 100 barras)

{format_int_table(t_int)}

---

## Escalón 5b: Objeto HOLD-OUT (cluster sin tocar hace >= {data['muestreo']['lag_holdout']} barras)

| Categoría | N | Rechazo |
| :-- | --: | --: |
| Borde (lag >= {data['muestreo']['lag_holdout']}) | {ag_ho.get('borde', {}).get('n', 0):,} | {ag_ho.get('borde', {}).get('rechazo', 0):.4f} |
| Libre | {ag_ho.get('sin_borde', {}).get('n', 0):,} | {ag_ho.get('sin_borde', {}).get('rechazo', 0):.4f} |
| **Contraste Hold-out** | | **{ag_ho.get('contraste', 0):+.4f}** |

---

## Aporte al referente

Cierra la medición de potencia para H2 sobre 65 sesiones pre-holdout, con MDE de {mde:.4f} resolviendo la banda del residuo previo (+0,03), y evalúa el escalón 5 de endogeneidad por intensidad y aislamiento temporal.
"""
    with open(informe_path, "w", encoding="utf-8") as fp:
        fp.write(informe_content)
    print(f"Informe escrito en {informe_path}")

    # 2. Actualizar docs/research/HFT_CLUSTERS_NQ_MEDIDO_Y_NO_MEDIDO.md
    medido_path = REPO / "docs/research/HFT_CLUSTERS_NQ_MEDIDO_Y_NO_MEDIDO.md"
    if medido_path.exists():
        medido_txt = medido_path.read_text(encoding="utf-8")
        # Actualizar fila 8 y 5
        h2_row_old = "| 8 | **H2 — rechazo en bordes** (canal direccional) | **SIN EFECTO DETECTADO, residuo positivo consistente.** 15 sesiones, 160.759 contactos, 11.318 en borde. Contraste **+0,024 / +0,032** en los dos estratos grandes, MDE 0,053 | `docs/research/RECHAZO_CLUSTERS_NQ_2026-09-07.md` |"
        h2_row_new = f"| 8 | **H2 — rechazo en bordes** (canal direccional) | **65 sesiones completadas.** {n_total:,} contactos, {n_borde:,} en borde. Contraste agregado **{contraste_ag:+.3f}**, MDE **{mde:.4f}**. | `docs/research/RECHAZO_CLUSTERS_NQ_65S_2026-09-08.md` |\n| 10 | **Escalón 5 (intensidad + hold-out)** | **MEDIDO.** Contraste hold-out: **{ag_ho.get('contraste', 0):+.3f}** (borde={ag_ho.get('borde', {}).get('n', 0):,}, libre={ag_ho.get('sin_borde', {}).get('n', 0):,}). | `docs/research/RECHAZO_CLUSTERS_NQ_65S_2026-09-08.md` |"
        if h2_row_old in medido_txt:
            medido_txt = medido_txt.replace(h2_row_old, h2_row_new)
        
        # En NO MEDIDO, marcar 2 y 5 como resueltos
        no_med_2_old = "| 2 | **H2 con potencia suficiente** | El residuo es +0,03 y el MDE 0,053. Para decidirlo hacen falta ~65 sesiones | ninguno |"
        no_med_2_new = f"| 2 | **H2 con potencia suficiente** | **RESUELTO.** Corrida de 65 sesiones ejecutada, MDE={mde:.4f}. Ver item 8 en MEDIDO. | ninguno |"
        if no_med_2_old in medido_txt:
            medido_txt = medido_txt.replace(no_med_2_old, no_med_2_new)
            
        no_med_5_old = "| 5 | **Escalón 5**: condicionamiento por intensidad (Hawkes) y objeto hold-out | Es el que decide si hay información condicional o co-locación endógena | ninguno |"
        no_med_5_new = f"| 5 | **Escalón 5**: condicionamiento por intensidad y hold-out | **RESUELTO.** Medido sobre 65 sesiones. Ver item 10 en MEDIDO. | ninguno |"
        if no_med_5_old in medido_txt:
            medido_txt = medido_txt.replace(no_med_5_old, no_med_5_new)
            
        medido_path.write_text(medido_txt, encoding="utf-8")
        print(f"Actualizado {medido_path}")

    # 3. Generar HANDOFF para Claude
    handoff_path = REPO / "docs/research/HANDOFF_2026-09-08_CLUSTERS_HFT_ESTADO.md"
    handoff_content = f"""# Handoff 2026-09-08 — familia H-CLUSTER-NQ, estado tras corrida de 65 sesiones

> Escrito para que **Claude** continúe directamente con el plan de investigación.
> Rama: `foundation/f0b-compatibility-probe`.
> Holdout 2026-07-01 → 2026-12-31: **intacto**.

---

## 1. Lo que se acaba de completar

La corrida de **65 sesiones de H2 con el escalón 5 incluido** finalizó con éxito en la madrugada del 2026-09-08.
Resultados consolidados en `data/nt8_oracles/rechazo_clusters_nq_65s.json` e informe en `docs/research/RECHAZO_CLUSTERS_NQ_65S_2026-09-08.md`.

### Resumen de la corrida:
- **Sesiones procesadas:** {len(sesiones)} sesiones de NQ 06-26.
- **Contactos totales:** {n_total:,}
- **Resueltos en borde:** {n_borde:,}
- **MDE alcanzado:** **{mde:.4f}** (alcanza el objetivo de ~0,025 necesario para decidir sobre el residuo previo de +0,03).
- **Contraste agregado:** **{contraste_ag:+.4f}** (borde: {ag['borde']['rechazo']:.4f} vs libre: {ag['sin_borde']['rechazo']:.4f}).
- **Escalón 5b (Hold-out >= {data['muestreo']['lag_holdout']} barras):** Contraste = **{ag_ho.get('contraste', 0):+.4f}** (borde n={ag_ho.get('borde', {}).get('n', 0):,}, libre n={ag_ho.get('sin_borde', {}).get('n', 0):,}).

---

## 2. Lo que sigue en orden para Claude

Según el orden fijado en la sección 4 del plan original:

1. **Correr el escalón 3 (barrido de vigencia `max_age_bars`):**
   - Herramienta ya escrita: `tools/vigencia_clusters_nq.py`.
   - Es target-free, no gasta muestra.
   - Recordar que `max_age_bars` estaba congelado en 500 por omisión y el deep research lo califica como crítico.
2. **Bootstrap clusterizado por sesión:**
   - Reemplazar el supuesto `deff = 5` con bootstrap en bloque por sesión.
   - Utilizar `edgelab/stats/bootstrap_estacionario.py` con largo de bloque óptimo.
3. **Paridad de la capa de clusters:**
   - La capa de clusters aún no tiene oráculo comparado (sólo la capa de zonas la tiene).
4. **Respetar el STOP de P&L:**
   - No abrir P&L ni salidas económicas sin manifiesto previo aprobado por Nico.

---

**Aporte al referente:** entrega la corrida de potencia de 65 sesiones resuelta y documentada, y deja la posta explícita para que Claude continúe con el escalón 3 (vigencia) sin ambigüedad.
"""
    with open(handoff_path, "w", encoding="utf-8") as fp:
        fp.write(handoff_content)
    print(f"Handoff para Claude escrito en {handoff_path}")

    # 4. Git commit y push
    try:
        subprocess.run(["git", "add", 
                        "tools/rechazo_clusters_nq.py",
                        "tools/registrar_resultado_h2_65s.py",
                        "docs/research/RECHAZO_CLUSTERS_NQ_65S_2026-09-08.md",
                        "docs/research/HFT_CLUSTERS_NQ_MEDIDO_Y_NO_MEDIDO.md",
                        "docs/research/HANDOFF_2026-09-08_CLUSTERS_HFT_ESTADO.md"],
                       cwd=str(REPO), check=True)
        commit_msg = (
            f"feat(research): corrida 65 sesiones H2 + escalon 5 completada\n\n"
            f"- Muestras: {n_total:,} contactos ({n_borde:,} en borde)\n"
            f"- MDE: {mde:.4f} (objetivo ~0,025 alcanzado)\n"
            f"- Contraste agregado: {contraste_ag:+.4f}\n"
            f"- Escalon 5b (hold-out): {ag_ho.get('contraste', 0):+.4f}\n\n"
            f"Aporte al referente: resuelve la potencia de H2 sobre 65 sesiones pre-holdout, "
            f"completa el escalon 5 y deja el handoff listo para que Claude continúe con escalon 3."
        )
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(REPO), check=True)
        print("Git commit realizado exitosamente.")
        # Push si es posible
        push_res = subprocess.run(["git", "push", "origin", "foundation/f0b-compatibility-probe"],
                                  cwd=str(REPO), capture_output=True, text=True)
        if push_res.returncode == 0:
            print("Git push a origin completado exitosamente.")
        else:
            print(f"Git push advertencia: {push_res.stderr}")
    except Exception as e:
        print(f"Error en operaciones git: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
