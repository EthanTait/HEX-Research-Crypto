# shared figure style: one fixed colour per symbol (never cycled), one axis per chart, thin marks
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from .config import paths

COLORS = {"BTCUSDT": "#2a78d6", "ETHUSDT": "#eb6834", "SOLUSDT": "#1baf7a", "XRPUSDT": "#eda100",
          "DOGEUSDT": "#e87ba4", "index": "#52514e"}
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
# diverging: blue, neutral grey, orange. for correlations in [-1, 1]
DIVERGING = LinearSegmentedColormap.from_list("div", ["#1c5cab", "#e6e5e1", "#d95926"])
SEQUENTIAL = LinearSegmentedColormap.from_list("seq", ["#cde2fb", "#0d366b"])


def style():
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 150, "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
        "grid.linewidth": 0.5, "lines.linewidth": 1.4, "legend.frameon": False, "legend.fontsize": 8,
        "axes.prop_cycle": matplotlib.cycler(color=SERIES),
    })


def save(fig, name):
    out = paths()["output"] / "figures"
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{name}.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def heatmap(ax, m, vmin=-1, vmax=1, cmap=DIVERGING, fmt="{:.2f}", title=None):
    im = ax.imshow(m.values, vmin=vmin, vmax=vmax, cmap=cmap)
    ax.set_xticks(range(m.shape[1]), [str(c).replace("USDT", "") for c in m.columns], rotation=45, ha="right")
    ax.set_yticks(range(m.shape[0]), [str(c).replace("USDT", "") for c in m.index])
    ax.grid(False)
    if fmt and m.shape[0] <= 12:
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                ax.text(j, i, fmt.format(m.values[i, j]), ha="center", va="center", fontsize=7, color="#0b0b0b")
    if title:
        ax.set_title(title)
    return im
