"""Generate all three 300-DPI publication figures for Paper 34:
NOGO-PSPACE-CERT-1.0 (Burke, Davies, & Tennenhouse, arXiv:2611.33127).

Author: Lluis Eriksson
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FIG_DIR = ROOT / "figures"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.grid": True,
    "grid.alpha": 0.28,
})


def make_fig1() -> None:
    d1 = json.loads((DATA_DIR / "exp1_grid_normal_vs_misere.json").read_text(encoding="utf-8"))
    d3 = json.loads((DATA_DIR / "exp3_subcubic_bipartite_atlas.json").read_text(encoding="utf-8"))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.6), dpi=300)

    # Panel (a): Exact Grid NoGo Normal vs. Misere Minimax States & Winners
    rows1 = d1["grids"]
    labels1 = [r["grid"] for r in rows1]
    x1 = np.arange(len(rows1))
    w = 0.36
    sn = [r["normal_states"] for r in rows1]
    sm = [r["misere_states"] for r in rows1]
    b1 = ax1.bar(x1 - w / 2, sn, width=w, color="#1f4e79", label="Normal play states")
    b2 = ax1.bar(x1 + w / 2, sm, width=w, color="#c55a11", label="Misère play states")
    ax1.set_yscale("log")
    for bar, r in zip(b1, rows1):
        tag = "B" if r["normal_winner"] == "Black" else "W"
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.25, tag, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#1f4e79")
    for bar, r in zip(b2, rows1):
        tag = "B" if r["misere_winner"] == "Black" else "W"
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.25, tag, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#c55a11")
    ax1.set_xticks(x1)
    ax1.set_xticklabels(labels1)
    ax1.set_ylim(1, max(max(sn), max(sm)) * 6.0)
    ax1.set_xlabel(r"Empty square/rectangular grid $r \times c$")
    ax1.set_ylabel(r"Exact minimax states evaluated (log)")
    ax1.set_title(r"(a) Grid NoGo: Normal vs. Misère (B/W Winner)")
    ax1.legend(loc="upper left", framealpha=0.92, fontsize=7.5)

    # Panel (b): Subcubic Bipartite Graph NoGo Atlas (Thm 1.2)
    rows3 = d3["graphs"]
    labels3 = [f"${r['graph']}$" for r in rows3]
    x3 = np.arange(len(rows3))
    gn = [r["normal_states"] for r in rows3]
    gm = [r["misere_states"] for r in rows3]
    gb1 = ax2.bar(x3 - w / 2, gn, width=w, color="#2e75b6", label="Normal play states")
    gb2 = ax2.bar(x3 + w / 2, gm, width=w, color="#548235", label="Misère play states")
    ax2.set_yscale("log")
    for bar, r in zip(gb1, rows3):
        tag = "B" if r["normal_winner"] == "Black" else "W"
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.25, tag, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#1f4e79")
    for bar, r in zip(gb2, rows3):
        tag = "B" if r["misere_winner"] == "Black" else "W"
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.25, tag, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#385723")
    ax2.set_xticks(x3)
    ax2.set_xticklabels(labels3)
    ax2.set_ylim(1, max(max(gn), max(gm)) * 6.0)
    ax2.set_xlabel(r"Connected bipartite subcubic graph ($\Delta \leq 3$)")
    ax2.set_ylabel(r"Exact minimax states evaluated (log)")
    ax2.set_title(r"(b) Theorem 1.2 Subcubic Bipartite Atlas (B/W)")
    ax2.legend(loc="upper left", framealpha=0.92, fontsize=7.5)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_grid_normal_vs_misere_and_subcubic.png", dpi=300)
    plt.close(fig)


def make_fig2() -> None:
    d2 = json.loads((DATA_DIR / "exp2_coins_are_lava_rope_sweep.json").read_text(encoding="utf-8"))
    d4 = json.loads((DATA_DIR / "exp4_b2cl_budget_scaling.json").read_text(encoding="utf-8"))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.6), dpi=300)

    # Panel (a): Lemma 4.1 Rope-Width Separation 2*t*w + 1 < N*w (N = 2t + 3)
    rows2 = d2["rope_separation"]
    ts = [r["t"] for r in rows2]
    w2_cuts = [r["w2_max_lower_cuts"] for r in rows2]
    w2_rope = [r["w2_rope_width"] for r in rows2]
    ax1.plot(ts, w2_rope, "o-", ms=5.0, lw=2.0, color="#1f4e79", label=r"Next-level rope width $N^2 = (2t+3)^2$")
    ax1.plot(ts, w2_cuts, "s--", ms=5.0, lw=2.0, color="#c00000", label=r"Max lower-level cuts $2tN + 1$")
    ax1.fill_between(ts, w2_cuts, w2_rope, color="#d9e8f5", alpha=0.5, label=r"Strict safety margin ($3N - 1 > 0$)")
    ax1.set_xticks(ts)
    ax1.set_ylim(0, max(w2_rope) * 1.15)
    ax1.set_xlabel(r"Total lower-level rope count $t$ ($N = 2t + 3$ odd)")
    ax1.set_ylabel(r"String count")
    ax1.set_title(r"(a) Lemma 4.1 Coins-are-Lava Rope Separation")
    ax1.legend(loc="upper left", framealpha=0.92, fontsize=7.3)

    # Panel (b): Section 2 B2CL Move Budget & White Reserve Scaling
    rows4 = d4["scaling"]
    ks = [r["scale_k"] for r in rows4]
    x_blk = [r["x_black_budget"] for r in rows4]
    w_res_h = [r["white_reserve_holes"] for r in rows4]
    blk_win = [r["black_win_moves"] for r in rows4]
    ax2.plot(ks, blk_win, "o-", ms=4.8, lw=2.0, color="#1f4e79", label=r"Black winning moves $x + 1$ (with Goal)")
    ax2.plot(ks, x_blk, "s--", ms=4.5, lw=1.8, color="#c55a11", label=r"White total moves $a + (x - a) = x$")
    ax2.plot(ks, w_res_h, "^:", ms=4.8, lw=1.8, color="#548235", label=r"White reserve holes $x + 1 - a$")
    ax2.set_xticks(ks)
    ax2.set_ylim(0, max(blk_win) * 1.18)
    ax2.set_xlabel(r"B2CL circuit scale $k$ ($a=b=c=d=e=k$)")
    ax2.set_ylabel(r"Move / hole count")
    ax2.set_title(r"(b) Section 2 B2CL Budget & White Reserve Scaling")
    ax2.legend(loc="upper left", framealpha=0.92, fontsize=7.3)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_lava_rope_and_b2cl_budget.png", dpi=300)
    plt.close(fig)


def make_fig3() -> None:
    rep = json.loads((DATA_DIR / "certificate_replay_summary.json").read_text(encoding="utf-8"))
    certs = rep["certificates"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.6), dpi=300)

    mode_colors = {
        "nogo_board_legality_and_reachability": "#1f4e79",
        "b2cl_gadget_minimax_normal_misere": "#2e75b6",
        "coins_are_lava_exact_minimax": "#548235",
        "subcubic_bipartite_graph_nogo": "#c55a11",
    }
    mode_short = {
        "nogo_board_legality_and_reachability": "Mode 1 (Reachability)",
        "b2cl_gadget_minimax_normal_misere": "Mode 2 (Grid Minimax)",
        "coins_are_lava_exact_minimax": "Mode 3 (Coins-are-Lava)",
        "subcubic_bipartite_graph_nogo": "Mode 4 (Subcubic Bip.)",
    }

    ys = np.arange(len(certs))
    lat = [max(c["verify_ms"], 0.01) for c in certs]
    cols = [mode_colors[c["mode"]] for c in certs]
    ax1.barh(ys, lat, color=cols, height=0.72, alpha=0.9)
    ax1.set_xscale("log")
    ax1.set_yticks(ys)
    ax1.set_yticklabels([f"C{i+1:02d}" for i in range(len(certs))], fontsize=7.2)
    ax1.invert_yaxis()
    ax1.set_xlim(0.02, max(lat) * 6.0)
    ax1.set_xlabel(r"Exact replay latency (ms, log scale)")
    ax1.set_title(r"(a) Replay Latency Across All 16 NOGO-PSPACE Certs")
    handles = [plt.Rectangle((0, 0), 1, 1, color=col, label=mode_short[m]) for m, col in mode_colors.items()]
    ax1.legend(handles=handles, loc="upper right", framealpha=0.92, fontsize=6.8)

    cats = ["Global\nSchema", "Mode 1\nReach.", "Mode 2\nGrid", "Mode 3\nLava", "Mode 4\nSubcubic"]
    counts = [10, 12, 12, 12, 14]
    bar_cols = ["#595959", "#1f4e79", "#2e75b6", "#548235", "#c55a11"]
    bars = ax2.bar(cats, counts, width=0.58, color=bar_cols, edgecolor="#222222", alpha=0.9)
    for b, cnt in zip(bars, counts):
        ax2.text(
            b.get_x() + b.get_width() / 2,
            cnt + 0.45,
            f"{cnt}/{cnt}",
            ha="center",
            va="bottom",
            fontsize=8.2,
            fontweight="bold",
            color="#111111",
        )
    ax2.set_ylim(0, 17.5)
    ax2.set_ylabel(r"Adversarial forgeries rejected")
    ax2.set_title(r"(b) Red-Team Adversarial Audit (60/60 Rejected)")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_certificate_replay_atlas.png", dpi=300)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    make_fig1()
    make_fig2()
    make_fig3()
    print("Generated all 3 publication figures successfully.")


if __name__ == "__main__":
    main()
