"""Re-vectorizacion limpia v2 de tramos sin superposicion sobre la captura del vendedor.

Corrige las dos limitaciones de la extraccion previa:
1. Calibra sobre la imagen original `1024x576` usando crominancia centrada en media
   sobre prototipos de color puros de grafico + filtro de picos locales (`|dy| <= 0.07`)
   y continuidad espacial estricta (`max_step_y = 0.14`), eliminando todo salto vertical.
2. Desambigua explicitamente los tres pares de crominancia gemela sin contaminacion:
   - `A . TEAL_UPPER` vs `A . TEAL_LOWER` (`A . S` vs `A . T`) por rama vertical;
   - `B . O` vs `B . C` (orquidea/lavanda discontinua) por envolvente de altura;
   - `B . P` vs `B . R` (cian vs azul acero discontinua) por envolvente post-2024.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None  # type: ignore[assignment]

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_IMG = ROOT / "docs/research/fundedsyncstack_20261115/paridad_vendedor/vendedor_original.jpg"
DEFAULT_OUT_DIR = ROOT / "docs/research/fundedsyncstack_20261115/paridad_vendedor"

LEGEND_BOXES: dict[str, tuple[int, int, int, int]] = {
    "A · A1":  (496, 354, 383, 0),
    "A · T":   (496, 440, 469, 0),
    "A · Z":   (496, 523, 552, 0),
    "B · F":   (496, 618, 645, 1),
    "B · Q":   (496, 699, 726, 1),
    "A · E":   (513, 354, 383, 0),
    "A · V":   (513, 440, 469, 0),
    "B · A20": (513, 524, 551, 1),
    "B · O":   (513, 618, 645, 1),
    "B · R":   (513, 698, 726, 1),
    "A · S":   (530, 354, 383, 0),
    "A · W":   (530, 440, 469, 0),
    "B · C":   (530, 523, 551, 1),
    "B · P":   (530, 618, 645, 1),
}

# Prototipos de crominancia centrada en media medidos sobre pixeles puros del grafico y leyenda
FAMILIAS_CROMATICAS: dict[str, dict[str, Any]] = {
    "LIME_A":     {"chroma": np.array([0.23, 0.56, -0.79], dtype=float),  "dashed": 0},   # A1 / Z
    "GREEN_A":    {"chroma": np.array([-0.14, 0.78, -0.61], dtype=float), "dashed": 0},   # E
    "TEAL_A":     {"chroma": np.array([-0.79, 0.56, 0.24], dtype=float),  "dashed": 0},   # S / T
    "YELLOW_A":   {"chroma": np.array([0.54, 0.26, -0.80], dtype=float),  "dashed": 0},   # V
    "ORANGE_A":   {"chroma": np.array([0.74, -0.08, -0.67], dtype=float), "dashed": 0},   # W
    "BLUE_B":     {"chroma": np.array([-0.59, -0.20, 0.78], dtype=float), "dashed": 1},   # A20
    "STEEL_R":    {"chroma": np.array([-0.73, 0.07, 0.68], dtype=float),  "dashed": 1},   # R
    "CYAN_P":     {"chroma": np.array([-0.79, 0.23, 0.57], dtype=float),  "dashed": 1},   # P
    "ORCHID_O":   {"chroma": np.array([0.24, -0.80, 0.55], dtype=float),  "dashed": 1},   # O
    "LAVENDER_C": {"chroma": np.array([-0.08, -0.66, 0.75], dtype=float), "dashed": 1},   # C
    "PINK_B":     {"chroma": np.array([0.74, -0.66, -0.08], dtype=float), "dashed": 1},   # F
    "ROSE_B":     {"chroma": np.array([0.81, -0.32, -0.49], dtype=float), "dashed": 1},   # Q
}

X_ANCHORS_DEFAULT = [(2022, 69.5), (2023, 291.5), (2024, 513.5), (2025, 735.5), (2026, 957.9)]
Y_ZERO_PX_DEFAULT = 385.0
Y_STEP_PX_DEFAULT = 82.5


def calibrar_ejes(im: np.ndarray) -> dict[str, Any]:
    """Calibra fondo, ticks anuales en X y pasos horizontales de grilla en Y."""
    plot_area = im[35:438, 20:1005].astype(np.float64)
    bg = np.median(plot_area, axis=(0, 1))

    # P10 horizontal evita contaminación por curvas planas y detecta solo las 5 líneas de grilla
    gray_p10 = np.percentile(im[35:438, 100:950].mean(axis=2), 10, axis=1)
    bg_g = float(np.median(gray_p10))
    grid_ys_raw = [35 + i for i, val in enumerate(gray_p10) if bg_g + 1.2 < val < bg_g + 16.0]
    grid_centers: list[float] = []
    if grid_ys_raw:
        grp = [grid_ys_raw[0]]
        for y in grid_ys_raw[1:]:
            if y - grp[-1] <= 3:
                grp.append(y)
            else:
                grid_centers.append(float(np.mean(grp)))
                grp = [y]
        grid_centers.append(float(np.mean(grp)))
    principales: list[float] = []
    for y in grid_centers:
        if not principales or (y - principales[-1]) >= 65.0:
            principales.append(y)
    if len(principales) >= 4:
        diffs = np.diff(principales)
        y_step = float(np.median(diffs))
        y_zero = float(principales[-1])
    else:
        y_step = Y_STEP_PX_DEFAULT
        y_zero = Y_ZERO_PX_DEFAULT

    lbl = im[440:465, :].mean(axis=2)
    xs = np.where(lbl.max(axis=0) > 70.0)[0]
    x_centers: list[float] = []
    if len(xs):
        splits = np.where(np.diff(xs) > 15)[0] + 1
        x_centers = [float(g.mean()) for g in np.split(xs, splits) if len(g) > 5]
    if len(x_centers) == 5:
        anchors = list(zip((2022, 2023, 2024, 2025, 2026), x_centers))
    else:
        anchors = list(X_ANCHORS_DEFAULT)

    xs_a = np.array([a[1] for a in anchors], dtype=float)
    days_a = np.array([(pd.Timestamp(f"{yr}-01-01") - pd.Timestamp("2022-01-01")).days for yr, _ in anchors], dtype=float)
    slope_dpx, intercept_d = np.polyfit(xs_a, days_a, 1)

    return {
        "bg": bg,
        "y_zero_px": y_zero,
        "y_step_px": y_step,
        "x_anchors": anchors,
        "slope_days_per_px": float(slope_dpx),
        "intercept_days": float(intercept_d),
    }


def muestrear_paleta_leyenda(im: np.ndarray, bg: np.ndarray) -> dict[str, dict[str, Any]]:
    """Extrae firma RGB de referencia desde los swatches de la leyenda."""
    paleta: dict[str, dict[str, Any]] = {}
    for nombre, (ry, cx0, cx1, estilo) in LEGEND_BOXES.items():
        patch = im[ry - 2 : ry + 3, cx0:cx1].astype(np.float64)
        mask = patch.max(axis=2) > 75.0
        rgb = patch[mask]
        br = rgb.sum(axis=1)
        core = rgb[br >= np.percentile(br, 60)].mean(axis=0)
        d = core - bg
        chr_v = d - d.mean()
        norm_c = float(np.linalg.norm(chr_v))
        paleta[nombre] = {
            "rgb": core,
            "delta": d,
            "chroma_unit": chr_v / max(norm_c, 1e-9),
            "dashed": int(estilo),
        }
    return paleta


def _x_a_fecha(x_px: float, cal: dict[str, Any]) -> str:
    d = cal["slope_days_per_px"] * float(x_px) + cal["intercept_days"]
    ts = pd.Timestamp("2022-01-01") + pd.Timedelta(days=float(round(d)))
    return ts.strftime("%Y-%m-%d")


def _resumir_cluster(strip: np.ndarray, delta: np.ndarray, bg: np.ndarray, grp: list[int], y_min: int) -> dict[str, Any]:
    arr = np.asarray(grp, dtype=int)
    weights = np.linalg.norm(delta[arr], axis=1)
    best_i = arr[int(np.argmax(weights))]
    yc = float(np.sum((arr + y_min) * weights) / max(float(weights.sum()), 1e-9))
    d = strip[best_i] - bg
    chr_v = d - d.mean()
    c_norm = float(np.linalg.norm(chr_v))
    d_norm = float(np.linalg.norm(d))
    return {
        "y_px": yc,
        "height": int(arr[-1] - arr[0] + 1),
        "chroma_unit": chr_v / max(c_norm, 1e-9),
        "chroma_mag": c_norm,
        "delta_mag": d_norm,
    }


def _clusteres_columna(im: np.ndarray, x: int, bg: np.ndarray, y_min: int = 38, y_max: int = 436) -> list[dict[str, Any]]:
    strip = im[y_min:y_max, x].astype(np.float64)
    delta = strip - bg
    sat = strip.max(axis=1) - strip.min(axis=1)
    bright = np.linalg.norm(delta, axis=1)
    active = np.where((sat > 15.0) & (bright > 32.0))[0]
    if not len(active):
        return []
    clusters: list[dict[str, Any]] = []
    grp = [active[0]]
    for idx in active[1:]:
        if idx - grp[-1] <= 2:
            grp.append(idx)
        else:
            clusters.append(_resumir_cluster(strip, delta, bg, grp, y_min))
            grp = [idx]
    clusters.append(_resumir_cluster(strip, delta, bg, grp, y_min))
    return clusters


def _limpiar_segmentos_y_saltos(
    df_mod: pd.DataFrame,
    *,
    max_gap_x: int = 16,
    max_step_y: float = 0.14,
    max_spike_y: float = 0.065,
    min_seg_pts: int = 6,
) -> pd.DataFrame:
    """Elimina picos puntuales de 1-2 pixeles y exige continuidad espacial estricta."""
    if len(df_mod) < min_seg_pts:
        return df_mod.iloc[0:0].copy()
    sub = df_mod.sort_values("x_px").reset_index(drop=True)

    # Paso 1: remover picos aislados respecto de la mediana de vecinos cercanos en X
    xs = sub["x_px"].to_numpy(dtype=float)
    ys = sub["y_grid_unidades"].to_numpy(dtype=float)
    keep = np.ones(len(sub), dtype=bool)
    for i in range(len(sub)):
        m_vec = (np.abs(xs - xs[i]) <= 10.0) & (np.arange(len(sub)) != i)
        if m_vec.sum() >= 2:
            med = float(np.median(ys[m_vec]))
            if abs(ys[i] - med) > max_spike_y:
                keep[i] = False
    sub = sub[keep].reset_index(drop=True)
    if len(sub) < min_seg_pts:
        return sub.iloc[0:0].copy()

    # Paso 2: segmentar por continuidad estricta (|dx| <= 16 px y |dy| <= 0.14 grilla)
    xs = sub["x_px"].to_numpy(dtype=float)
    ys = sub["y_grid_unidades"].to_numpy(dtype=float)
    seg_ids = np.zeros(len(sub), dtype=int)
    cur = 1
    seg_ids[0] = cur
    for i in range(1, len(sub)):
        if (xs[i] - xs[i - 1]) > max_gap_x or abs(ys[i] - ys[i - 1]) > max_step_y:
            cur += 1
        seg_ids[i] = cur
    sub["segmento_id"] = seg_ids

    counts = sub["segmento_id"].value_counts()
    keep_segs = counts[counts >= min_seg_pts].index
    sub = sub[sub["segmento_id"].isin(keep_segs)].reset_index(drop=True)
    return sub


def _asignar_estrategia(
    fam: str,
    cl: dict[str, Any],
    x: int,
    y_grid: float,
    fecha: str,
) -> str | None:
    if fam == "GREEN_A":
        return "A · E"
    if fam == "YELLOW_A":
        if fecha >= "2024-06-01" and 0.32 <= y_grid <= 0.48:
            return "A · Z"
        return "A · V"
    if fam == "ORANGE_A":
        return "A · W"
    if fam == "BLUE_B":
        if fecha >= "2024-09-01" and y_grid < 1.28:
            return "B · R"
        return "B · A20"
    if fam == "PINK_B":
        if fecha <= "2026-01-01" and y_grid > 0.62:
            return None
        return "B · F"
    if fam == "ROSE_B":
        return "B · Q"
    if fam == "TEAL_A":
        if y_grid >= 0.55 and fecha >= "2022-07-01":
            return "A · TEAL_UPPER"
        if y_grid <= 0.45:
            return "A · TEAL_LOWER"
        return None
    if fam == "ORCHID_O":
        if y_grid >= 0.45 or (fecha <= "2022-07-01" and y_grid >= 0.08):
            return "B · O"
        return None
    if fam == "LAVENDER_C":
        if y_grid <= 0.46:
            return "B · C"
        if y_grid >= 0.55 and fecha >= "2022-06-01":
            return "B · O"
        return None
    if fam in ("CYAN_P", "STEEL_R"):
        # En 2024-07+, P despega por encima de 1.38 grilla y R queda por debajo de 1.25 grilla
        if fecha >= "2024-07-01":
            if y_grid >= 1.38:
                return "B · P"
            if y_grid <= 1.25:
                return "B · R"
            return None
        return "B · P" if fam == "CYAN_P" else "B · R"
    if fam == "LIME_A":
        # A.Z es una banda plana (0.32..0.48) de menor croma que A.A1; en 2025-07+ A.A1 sube por encima de 0.50
        if fecha >= "2024-04-01" and 0.32 <= y_grid <= 0.48 and (cl["chroma_mag"] <= 26.0 or fecha >= "2025-07-01"):
            return "A · Z"
        return "A · A1"
    return None


def extraer_curvas_limpias_v2(
    img_path: str | Path | None = None,
    out_csv: str | Path | None = None,
    *,
    min_vert_sep_px: float = 5.0,
    min_chroma_sim: float = 0.955,
    min_chroma_margin: float = 0.012,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Extrae tramos limpios sin superposicion + `TEAL_UPPER`/`TEAL_LOWER` de la grafica del vendedor."""
    if Image is None:
        raise RuntimeError("Pillow (PIL) es requerido para extraer_curvas_limpias_v2")
    ruta_img = DEFAULT_IMG if img_path is None else Path(img_path)
    im = np.array(Image.open(ruta_img).convert("RGB"))
    cal = calibrar_ejes(im)

    fam_names = list(FAMILIAS_CROMATICAS.keys())
    F_mat = np.stack([FAMILIAS_CROMATICAS[k]["chroma"] / np.linalg.norm(FAMILIAS_CROMATICAS[k]["chroma"]) for k in fam_names], axis=0)

    col_clusters: dict[int, list[dict[str, Any]]] = {}
    for x in range(16, im.shape[1] - 6):
        col_clusters[x] = _clusteres_columna(im, x, cal["bg"])

    rows: list[dict[str, Any]] = []
    for x, clist in col_clusters.items():
        if not clist:
            continue
        ys = np.array([c["y_px"] for c in clist], dtype=float)
        fecha = _x_a_fecha(x, cal)
        for idx, cl in enumerate(clist):
            if cl["height"] > 10 or cl["chroma_mag"] < 6.5 or cl["delta_mag"] < 42.0:
                continue
            d_other = min([abs(ys[idx] - ys[j]) for j in range(len(ys)) if j != idx], default=99.0)
            if d_other < min_vert_sep_px:
                continue

            dens = sum(
                1
                for dx in (-4, -3, -2, -1, 1, 2, 3, 4)
                if any(abs(o["y_px"] - cl["y_px"]) <= 2.5 for o in col_clusters.get(x + dx, []))
            )

            sims = F_mat @ cl["chroma_unit"]
            order = np.argsort(sims)[::-1]
            best_fam = fam_names[int(order[0])]
            best_sim = float(sims[int(order[0])])
            if best_sim < min_chroma_sim:
                continue

            expected_dashed = FAMILIAS_CROMATICAS[best_fam]["dashed"]
            if expected_dashed == 0 and dens < 4:
                continue

            alt_fam = fam_names[int(order[1])]
            alt_sim = float(sims[int(order[1])])
            margin = best_sim - alt_sim
            if margin < min_chroma_margin:
                alt_dashed = FAMILIAS_CROMATICAS[alt_fam]["dashed"]
                terc_sim = float(sims[int(order[2])]) if len(order) > 2 else 0.0
                pares_hermanos = ({best_fam, alt_fam} == {"CYAN_P", "STEEL_R"} and fecha >= "2024-07-01") or ({best_fam, alt_fam} in ({"LIME_A", "YELLOW_A"}, {"ORCHID_O", "LAVENDER_C"}) and fecha >= "2024-06-01")
                if expected_dashed == 0 and alt_dashed == 1 and dens >= 6 and (best_sim - terc_sim) >= min_chroma_margin:
                    margin = best_sim - terc_sim
                elif expected_dashed == 1 and alt_dashed == 0 and dens <= 5 and (best_sim - terc_sim) >= min_chroma_margin:
                    margin = best_sim - terc_sim
                elif pares_hermanos and (best_sim - terc_sim) >= min_chroma_margin:
                    margin = best_sim - terc_sim
                else:
                    continue

            y_grid = (cal["y_zero_px"] - cl["y_px"]) / cal["y_step_px"]
            est = _asignar_estrategia(best_fam, cl, x, y_grid, fecha)
            if est is None:
                continue

            rows.append({
                "estrategia": est,
                "fecha": fecha,
                "x_px": int(x),
                "y_px": round(float(cl["y_px"]), 2),
                "y_grid_unidades": round(float(y_grid), 4),
                "margen_color": round(float(margin), 5),
            })

    raw_df = pd.DataFrame(rows)
    partes = []
    if not raw_df.empty:
        for _, grp in raw_df.groupby("estrategia", sort=True):
            limpio = _limpiar_segmentos_y_saltos(grp)
            if not limpio.empty:
                partes.append(limpio)
    out_df = pd.concat(partes, ignore_index=True) if partes else raw_df
    if not out_df.empty:
        out_df = out_df.sort_values(["estrategia", "x_px"]).drop_duplicates(["estrategia", "fecha"]).reset_index(drop=True)

    if out_csv is not None:
        p = Path(out_csv)
        p.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(p, index=False)

    return out_df, cal


def graficar_verificacion_vectorizacion(
    df_v2: pd.DataFrame,
    img_path: str | Path | None = None,
    out_png: str | Path | None = None,
) -> Path:
    """Genera visualizacion comparativa de 2 paneles (overlay sobre original + curvas limpias calibradas)."""
    if Image is None or plt is None:
        raise RuntimeError("Pillow y matplotlib son requeridos para graficar_verificacion_vectorizacion")
    ruta_img = DEFAULT_IMG if img_path is None else Path(img_path)
    ruta_png = (DEFAULT_OUT_DIR / "verificacion_vectorizacion_v2_20261121.png") if out_png is None else Path(out_png)
    im = np.array(Image.open(ruta_img).convert("RGB"))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), facecolor="#0d1316")
    for ax in (ax1, ax2):
        ax.set_facecolor("#11191c")
        ax.tick_params(colors="#a7b4ba")
        for sp in ax.spines.values():
            sp.set_color("#29363c")

    ax1.imshow(im, alpha=0.42)
    cmap = plt.get_cmap("tab20")
    estrats = sorted(df_v2["estrategia"].unique())
    for idx, est in enumerate(estrats):
        col = cmap(idx % 20)
        sub = df_v2[df_v2["estrategia"] == est]
        ls = "--" if est.startswith("B") else "-"
        for _, seg in sub.groupby("segmento_id"):
            ax1.plot(seg["x_px"], seg["y_px"], color=col, linestyle=ls, linewidth=1.6, alpha=0.95)
            ax2.plot(pd.to_datetime(seg["fecha"]), seg["y_grid_unidades"], color=col, linestyle=ls, linewidth=1.6, alpha=0.95)
        ax2.plot([], [], color=col, linestyle=ls, linewidth=1.8, label=f"{est} ({len(sub)})")

    ax1.set_title("Verificacion v2 — Tramos limpios superpuestos sobre imagen original del vendedor", color="#e1e9ec", fontsize=11)
    ax1.set_xlim(0, im.shape[1])
    ax1.set_ylim(im.shape[0] - 40, 20)

    ax2.axhline(0.0, color="#3a4a52", linewidth=0.9)
    for y in (1.0, 2.0, 3.0, 4.0):
        ax2.axhline(y, color="#222d32", linewidth=0.7)
    ax2.set_title("Curvas v2 calibradas en unidades de grilla (cero picos y pares gemelos desambiguados)", color="#e1e9ec", fontsize=11)
    ax2.set_ylabel("Unidades de grilla", color="#a7b4ba")
    ax2.legend(loc="upper left", ncol=4, fontsize=8, frameon=True, facecolor="#11191c", edgecolor="#29363c", labelcolor="#d7e0e4")

    fig.tight_layout()
    out_p = ruta_png
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_p, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Re-vectoriza los tramos claros de la captura del vendedor.")
    ap.add_argument("--img", default=str(DEFAULT_IMG))
    ap.add_argument("--out-csv", default=str(DEFAULT_OUT_DIR / "curvas_extraidas_v2_limpias.csv"))
    ap.add_argument("--out-png", default=str(DEFAULT_OUT_DIR / "verificacion_vectorizacion_v2_20261121.png"))
    args = ap.parse_args(argv)

    df_v2, _ = extraer_curvas_limpias_v2(args.img, args.out_csv)
    png = graficar_verificacion_vectorizacion(df_v2, args.img, args.out_png)
    print(f"[OK] Extraidos {len(df_v2)} puntos limpios en {df_v2['estrategia'].nunique()} tracks -> {args.out_csv}")
    print(df_v2.groupby("estrategia").agg(n=("fecha", "count"), segs=("segmento_id", "nunique"), min_d=("fecha", "min"), max_d=("fecha", "max"), y_min=("y_grid_unidades", "min"), y_max=("y_grid_unidades", "max")).to_string())
    print(f"[OK] Grafico verificacion -> {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
