"""
analyze.py - Lee el registro de ensayos (.jsonl) y genera las figuras y las tablas LaTeX de la evaluación.

Uso:
    python analyze.py --input piloto.jsonl --outdir resultados

Genera en --outdir:
    fig_recuperacion.png/.pdf   mapa de calor de la tasa de recuperación R por calidad Q y alpha
    fig_ber.png/.pdf            BER antes de RS en función de Q, una línea por alpha
    fig_calidad.png/.pdf        PSNR y SSIM por alpha (solo ensayos normales)
    tabla_recuperacion.tex      tabla R por Q y alpha
    tabla_controles.tex         resumen de los controles (clave incorrecta, imagen limpia)
Dependencias: numpy y matplotlib.

Decisiones de lectura (para citarlas en la memoria):
  - R es la fracción de ensayos "normales" con estado "correcta" (los fallos y las falsas correcciones cuentan como fallo).
  - Las figuras no usan color como único canal: cada alpha lleva además un marcador distinto.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Paleta categórica en orden fijo (azul, naranja, aguamarina, amarillo) y secuencial de un solo tono (azul).
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
MARKERS = ["o", "s", "^", "D"]
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e3e2de"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": INK_SECONDARY, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK_SECONDARY, "ytick.color": INK_SECONDARY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.dpi": 150, "savefig.bbox": "tight",
})


def load_records(path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fmt(x: float, digits: int = 2) -> str:
    """Número con punto decimal protegido para LaTeX: 0.45 -> 0{.}45."""
    return f"{x:.{digits}f}".replace(".", "{.}")


def group(records, key):
    groups = {}
    for r in records:
        groups.setdefault(key(r), []).append(r)
    return groups


def recovery_matrix(normal, qualities, alphas):
    R = np.zeros((len(qualities), len(alphas)))
    N = np.zeros((len(qualities), len(alphas)), dtype=int)
    for i, q in enumerate(qualities):
        for j, a in enumerate(alphas):
            cell = [r for r in normal if r["quality"] == q and r["alpha"] == a]
            N[i, j] = len(cell)
            R[i, j] = np.mean([r["status"] == "correcta" for r in cell]) if cell else np.nan
    return R, N


def save(fig, outdir, name):
    fig.savefig(outdir / f"{name}.png")
    fig.savefig(outdir / f"{name}.pdf")
    plt.close(fig)


def fig_recovery(R, qualities, alphas, outdir):
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    cmap = matplotlib.colormaps["Blues"]
    im = ax.imshow(R, vmin=0, vmax=1, cmap=cmap, aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(len(alphas)), [str(a) for a in alphas])
    ax.set_yticks(range(len(qualities)), [str(q) for q in qualities])
    ax.set_xlabel(r"$\alpha$ (paso $\Delta = \alpha \cdot q^{(50)}$)")
    ax.set_ylabel("Calidad JPEG $Q$")
    for i in range(R.shape[0]):
        for j in range(R.shape[1]):
            v = R[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9,
                    color="white" if v > 0.55 else INK)
    for s in ax.spines.values():
        s.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cbar.set_label("Tasa de recuperación $R$")
    cbar.outline.set_visible(False)
    ax.set_title("Recuperación de la trama tras la recompresión JPEG", fontsize=10, color=INK)
    save(fig, outdir, "fig_recuperacion")


def fig_ber(normal, qualities, alphas, outdir):
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    sizes = [6, 6, 11, 5]          # tamaños distintos: las curvas con BER 0 se solapan y así se ven todas
    for k, a in enumerate(alphas):
        ys = [np.mean([r["ber_raw"] for r in normal if r["quality"] == q and r["alpha"] == a]) for q in qualities]
        ax.plot(qualities, ys, color=SERIES_COLORS[k % 4], marker=MARKERS[k % 4], markersize=sizes[k % 4],
                linewidth=2, markeredgecolor="white", markeredgewidth=1, zorder=3 + k,
                label=f"α = {a}")
    ax.set_xlabel("Calidad JPEG $Q$")
    ax.set_ylabel("BER antes de Reed-Solomon (media)")
    ax.set_xticks(qualities)
    ax.set_ylim(bottom=-0.01)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("Error de bit en el canal según la calidad y el paso", fontsize=10, color=INK)
    save(fig, outdir, "fig_ber")


def fig_quality(normal, alphas, outdir):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.6, 3.6))
    for ax, key, label in ((ax1, "psnr", "PSNR (dB)"), (ax2, "ssim", "SSIM")):
        data = [[r[key] for r in normal if r["alpha"] == a and r[key] is not None] for a in alphas]
        bp = ax.boxplot(data, positions=range(len(alphas)), widths=0.55, patch_artist=True, showfliers=False,
                        medianprops=dict(color=INK, linewidth=1.5), whiskerprops=dict(color=INK_SECONDARY),
                        capprops=dict(color=INK_SECONDARY), boxprops=dict(edgecolor=INK_SECONDARY))
        for k, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(SERIES_COLORS[k % 4])
            patch.set_alpha(0.85)
        ax.set_xticks(range(len(alphas)), [str(a) for a in alphas])
        ax.set_xlabel(r"$\alpha$")
        ax.set_ylabel(label)
    ax1.axhline(38, color=INK_SECONDARY, linestyle="--", linewidth=1)
    ax1.text(len(alphas) - 0.5, 38.8, "umbral 38 dB", ha="right", fontsize=8, color=INK_SECONDARY)
    ax1.set_ylim(35, None)
    ssim_min = min(r["ssim"] for r in normal)
    ax2.set_ylim(ssim_min - 0.0003, 1.0002)       # el umbral 0,95 queda muy por debajo: se indica en el título
    ax2.set_title("umbral 0,95 fuera de escala", fontsize=8, color=INK_SECONDARY)
    fig.suptitle("Calidad visual entre la imagen original y la estego-imagen", fontsize=10, color=INK)
    fig.tight_layout()
    save(fig, outdir, "fig_calidad")


def _header(cells):
    """Fila de cabecera con el estilo de las tablas de la memoria."""
    return [r"\rowcolor{uocnavy}"] + [rf"\color{{white}}\textbf{{{c}}} &" for c in cells[:-1]] + \
           [rf"\color{{white}}\textbf{{{cells[-1]}}} \\"]


def table_recovery(R, N, qualities, alphas, outdir):
    cols = "c" * len(alphas)
    n_min, n_max = N.min(), N.max()
    per_cell = f"{n_min}" if n_max == n_min else f"{n_min}-{n_max}"
    alpha_txt = [fmt(a, 0) if float(a).is_integer() else fmt(a, 1) for a in alphas]
    lines = [r"\begin{table}[H]", r"\centering", r"\scriptsize",
             rf"\caption{{Tasa de recuperación $R$ por calidad $Q$ y factor $\alpha$ ({per_cell} imágenes por celda).}}",
             r"\label{tab:recuperacion}",
             rf"\begin{{tabular}}{{|c|{'|'.join(cols)}|}}", r"\hline"]
    lines += _header(["$Q$"] + [rf"$\alpha={t}$" for t in alpha_txt])
    lines.append(r"\hline")
    for i, q in enumerate(qualities):
        lines.append(f"{q} & " + " & ".join(fmt(R[i, j]) for j in range(len(alphas))) + r" \\")
        lines.append(r"\hline")
    lines += [r"\end{tabular}", r"\end{table}"]
    (outdir / "tabla_recuperacion.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def table_controls(records, outdir):
    names = {"wrong_key": "Clave incorrecta", "clean_image": "Imagen limpia"}
    lines = [r"\begin{table}[H]", r"\centering", r"\scriptsize",
             r"\caption{Controles de acceso al mapa y de falsos positivos.}", r"\label{tab:controles}",
             r"\begin{tabular}{|l|c|c|c|c|c|}", r"\hline"]
    lines += _header(["Control", "Ensayos", "BER media", "Fallos", "Falsas correcciones", "Aceptadas"])
    lines.append(r"\hline")
    for ctrl in ("wrong_key", "clean_image"):
        cr = [r for r in records if r["control"] == ctrl]
        if not cr:
            continue
        c = Counter(r["status"] for r in cr)
        lines.append(f"{names[ctrl]} & {len(cr)} & {fmt(np.mean([r['ber_raw'] for r in cr]), 3)} & "
                     f"{c['fallo']} & {c['falsa_correccion']} & {sum(r['accepted'] for r in cr)} \\\\")
        lines.append(r"\hline")
    lines += [r"\end{tabular}", r"\end{table}"]
    (outdir / "tabla_controles.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Figuras y tablas a partir del registro de ensayos.")
    parser.add_argument("--input", required=True, help="fichero .jsonl del experimento")
    parser.add_argument("--outdir", default="resultados", help="carpeta de salida")
    args = parser.parse_args(argv)

    records = load_records(args.input)
    if not records:
        raise SystemExit("El registro está vacío.")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    normal = [r for r in records if r["control"] == "normal"]
    qualities = sorted({r["quality"] for r in normal})
    alphas = sorted({r["alpha"] for r in normal})
    R, N = recovery_matrix(normal, qualities, alphas)

    fig_recovery(R, qualities, alphas, outdir)
    fig_ber(normal, qualities, alphas, outdir)
    fig_quality(normal, alphas, outdir)
    table_recovery(R, N, qualities, alphas, outdir)
    table_controls(records, outdir)

    images = len({r["image_id"] for r in records})
    print(f"{len(records)} ensayos, {images} imágenes. Salida en {outdir}/")
    print("Estados (normales):", dict(Counter(r["status"] for r in normal)))


if __name__ == "__main__":
    main()