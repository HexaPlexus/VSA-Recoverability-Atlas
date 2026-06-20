from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"
FIG_DIR = PAPER_DIR / "figures"

plt.rcParams.update(
    {
        "figure.dpi": 160,
        "savefig.dpi": 300,
        "font.family": "DejaVu Serif",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "mathtext.fontset": "stix",
    }
)

COLORS = {
    "blue": "#356BB3",
    "orange": "#C26B2D",
    "green": "#2E8B57",
    "teal": "#2B8C99",
    "red": "#B24745",
    "purple": "#6E5AA8",
    "gray": "#6B7280",
    "light": "#EEF2F7",
    "dark": "#1F2937",
}

PDF_METADATA = {
    "Creator": "scripts/build_manuscript_figures.py",
    "Producer": "Matplotlib",
    "CreationDate": datetime(2026, 6, 20, tzinfo=timezone.utc),
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_figure(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIG_DIR / f"{stem}.pdf", bbox_inches="tight", metadata=PDF_METADATA)
    fig.savefig(FIG_DIR / f"{stem}.png", bbox_inches="tight")
    plt.close(fig)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def figure1_budget_map() -> None:
    fig, ax = plt.subplots(figsize=(10.2, 4.9))
    ax.set_axis_off()

    ax.text(0.0, 1.02, "Recoverability workflow", transform=ax.transAxes, fontsize=12, fontweight="bold")
    ax.text(
        0.0,
        0.97,
        "Conceptual figure. Acceptance never bypasses the verifier.",
        transform=ax.transAxes,
        color=COLORS["gray"],
    )

    boxes = [
        (0.02, 0.38, 0.16, 0.22, "Task and\nrisk contract", "#DCE7F5"),
        (0.22, 0.38, 0.16, 0.22, "Recoverability\nbudget", "#DBF0EE"),
        (0.42, 0.38, 0.18, 0.22, "Representation and\nnative decoder", "#E7F3E8"),
        (0.64, 0.38, 0.15, 0.22, "Candidate\nresult", "#F8ECD7"),
        (0.82, 0.38, 0.14, 0.22, "Independent\nverifier", "#EEE8F8"),
        (0.82, 0.72, 0.14, 0.14, "Accept", "#E6F2E8"),
        (0.82, 0.18, 0.14, 0.14, "Abstain", "#ECEFF4"),
        (0.62, 0.72, 0.14, 0.14, "Fallback", "#F7E4E3"),
    ]
    for x, y, w, h, label, color in boxes:
        ax.add_patch(
            patches.FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.012,rounding_size=0.02",
                linewidth=1.0,
                edgecolor=COLORS["dark"],
                facecolor=color,
                transform=ax.transAxes,
            )
        )
        ax.text(x + w / 2, y + h / 2, label, transform=ax.transAxes, ha="center", va="center", fontsize=10)

    arrows = [
        ((0.18, 0.49), (0.22, 0.49), COLORS["blue"]),
        ((0.38, 0.49), (0.42, 0.49), COLORS["blue"]),
        ((0.60, 0.49), (0.64, 0.49), COLORS["blue"]),
        ((0.79, 0.49), (0.82, 0.49), COLORS["blue"]),
        ((0.89, 0.60), (0.89, 0.72), COLORS["green"]),
        ((0.82, 0.72), (0.76, 0.72), COLORS["red"]),
        ((0.89, 0.38), (0.89, 0.32), COLORS["gray"]),
        ((0.82, 0.25), (0.75, 0.25), COLORS["gray"]),
    ]
    for (x1, y1), (x2, y2), color in arrows:
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            xycoords=ax.transAxes,
            textcoords=ax.transAxes,
            arrowprops=dict(arrowstyle="-|>", lw=1.8, color=color, shrinkA=2, shrinkB=2),
        )

    ax.text(0.895, 0.66, "verified", transform=ax.transAxes, fontsize=9, color=COLORS["green"], ha="left")
    ax.text(0.79, 0.75, "not verified", transform=ax.transAxes, fontsize=9, color=COLORS["red"], ha="right")
    ax.text(0.89, 0.33, "no safe decision", transform=ax.transAxes, fontsize=9, color=COLORS["gray"], ha="left")
    ax.text(
        0.02,
        0.08,
        "Acceptance never bypasses the independent verifier. Fallback is explicit rather than implicit.",
        transform=ax.transAxes,
        color=COLORS["dark"],
    )

    save_figure(fig, "figure1_budget_map")


def figure2_evidence_atlas() -> None:
    payload = load_json(PAPER_DIR / "evidence_registry.yaml")
    entries = payload["entries"]
    status_order = [
        "ADOPTED_ENGINEERING_BASELINE",
        "REPRODUCED_IN_REPO",
        "PARTIALLY_REPRODUCED",
        "PAPER_REPRODUCTION",
        "IMPLEMENTATION_AUDITED",
        "DEFERRED_HYPOTHESIS",
        "BLOCKED_WITH_EVIDENCE",
    ]
    disposition_order = [
        "ADOPTED_ENGINEERING_BASELINE",
        "REPRODUCED_IN_REPO",
        "PARTIALLY_REPRODUCED",
        "IMPLEMENTATION_AUDITED",
        "DEFERRED_HYPOTHESIS",
        "BLOCKED_WITH_EVIDENCE",
    ]
    labels = {
        "ADOPTED_ENGINEERING_BASELINE": "Baseline",
        "REPRODUCED_IN_REPO": "Reproduced",
        "PARTIALLY_REPRODUCED": "Partial",
        "PAPER_REPRODUCTION": "Paper-only",
        "IMPLEMENTATION_AUDITED": "Audit",
        "DEFERRED_HYPOTHESIS": "Development",
        "BLOCKED_WITH_EVIDENCE": "Unsupported",
    }
    palette = {
        "ADOPTED_ENGINEERING_BASELINE": COLORS["blue"],
        "REPRODUCED_IN_REPO": COLORS["green"],
        "PARTIALLY_REPRODUCED": COLORS["teal"],
        "PAPER_REPRODUCTION": COLORS["orange"],
        "IMPLEMENTATION_AUDITED": COLORS["purple"],
        "DEFERRED_HYPOTHESIS": "#C9A227",
        "BLOCKED_WITH_EVIDENCE": COLORS["red"],
    }

    status_counts = {key: 0 for key in status_order}
    disposition_counts = {key: 0 for key in disposition_order}
    for entry in entries:
        status_counts[entry["evidence_status"]] += 1
        disposition_counts[entry["architectural_disposition"]] += 1

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5), sharey=True)
    fig.suptitle("Repository evidence status summary", x=0.06, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.06, 0.92, "Source: canonical evidence registry. N = 24 normalized lines.", color=COLORS["gray"])
    fig.subplots_adjust(top=0.82, bottom=0.23, wspace=0.20)

    for ax, title, order, counts in (
        (axes[0], "(a) Evidence maturity", status_order, status_counts),
        (axes[1], "(b) Architectural disposition", disposition_order, disposition_counts),
    ):
        values = [counts[key] for key in order]
        x = range(len(order))
        ax.bar(x, values, color=[palette[key] for key in order], edgecolor=COLORS["dark"], linewidth=0.8)
        ax.set_title(title, loc="left")
        ax.set_ylabel("Number of normalized lines")
        ax.set_ylim(0, max(values) + 2)
        ax.set_xticks(list(x))
        ax.set_xticklabels([labels[key] for key in order], rotation=18, ha="right")
        ax.tick_params(axis="x", labelsize=7)
        ax.grid(axis="y", color="#D7DEE8", linewidth=0.8)
        ax.set_axisbelow(True)
        for idx, value in enumerate(values):
            ax.text(idx, value + 0.08, str(value), ha="center", va="bottom", fontsize=9, fontweight="bold")

    save_figure(fig, "figure2_evidence_atlas")


def figure3_capacity_frontier() -> None:
    rows = load_csv(ROOT / "results" / "level3_2" / "recovery_summary.csv")
    wanted = {
        (10, "MAP", "map_d512"),
        (10, "MAP", "map_d1024"),
        (10, "BCF", "bcf_d512_f3_b4"),
        (22, "MAP", "map_d512"),
        (22, "MAP", "map_d1024"),
        (22, "BCF", "bcf_d512_f3_b4"),
        (31, "MAP", "map_d512"),
        (31, "MAP", "map_d1024"),
        (31, "BCF", "bcf_d512_f3_b4"),
        (68, "MAP", "map_d512"),
        (68, "MAP", "map_d1024"),
        (68, "BCF", "bcf_d512_f3_b4"),
    }
    series = {"MAP D512": [], "MAP D1024": [], "BCF": []}
    for row in rows:
        key = (int(row["domain_size"]), row["substrate"], row["config_id"])
        if key not in wanted:
            continue
        label = "BCF" if row["substrate"] == "BCF" else ("MAP D512" if row["config_id"] == "map_d512" else "MAP D1024")
        series[label].append(
            (
                int(row["domain_size"]),
                float(row["exact_recovery_rate"]),
                float(row["exact_recovery_ci_low"]),
                float(row["exact_recovery_ci_high"]),
                int(row["trials"]),
            )
        )
    for points in series.values():
        points.sort()

    styles = {
        "MAP D512": dict(color=COLORS["orange"], marker="o", linestyle="--"),
        "MAP D1024": dict(color=COLORS["blue"], marker="s", linestyle="-"),
        "BCF": dict(color=COLORS["green"], marker="^", linestyle="-."),
    }

    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    fig.suptitle("Clean $F = 3$ capacity frontier", x=0.06, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.06, 0.92, "Scope: clean, single-product, common-envelope comparison.", color=COLORS["gray"])

    for label, points in series.items():
        x = [item[0] for item in points]
        y = [item[1] for item in points]
        lower = [item[1] - item[2] for item in points]
        upper = [item[3] - item[1] for item in points]
        style = styles[label]
        ax.errorbar(
            x,
            y,
            yerr=[lower, upper],
            capsize=3,
            linewidth=1.8,
            markersize=6,
            label=label,
            **style,
        )
        for x_val, y_val, _, _, trials in points:
            ax.annotate(f"n={trials}", (x_val, y_val), textcoords="offset points", xytext=(6, 6), fontsize=8, color=COLORS["gray"])

    ax.set_xlabel(r"Domain size $M$")
    ax.set_ylabel("Exact recovery rate")
    ax.set_xlim(8, 70)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xticks([10, 22, 31, 68])
    ax.grid(color="#D7DEE8", linewidth=0.8)
    ax.legend(frameon=False, loc="lower left")

    save_figure(fig, "figure3_clean_f3_frontier")


def figure4_repair_costs() -> None:
    rows = load_csv(ROOT / "results" / "codebook_residue_v0_1" / "arm_summary.csv")
    wanted = {
        ("A_MAP_B_HARD", "sign_only"): ("Hard-sign MAP", "o", COLORS["gray"]),
        ("C_SCALAR_RESIDUE_EQUAL_RATE", "scalar_zlib_4level"): ("Scalar residue", "s", COLORS["orange"]),
        ("E_BLOCK_CODEBOOK_C16", "C16"): ("Block residue C16", "^", COLORS["teal"]),
        ("H_EQUAL_TOTAL_BIT_MAP_B", "equal_bits_for_C16"): ("Equal-bit extra dimensions", "D", COLORS["blue"]),
        ("G_MAP_I_EXACT_ACCUMULATOR", "exact_accumulator_k31"): ("MAP-I accumulator", "P", COLORS["green"]),
    }
    chosen: list[tuple[str, float, float, str, str]] = []
    for row in rows:
        key = (row["arm_id"], row["variant_id"])
        if row["split_name"] == "FINAL_DEVELOPMENT_EVALUATION" and row["bundle_width"] == "31" and key in wanted:
            label, marker, color = wanted[key]
            chosen.append(
                (
                    label,
                    float(row["mean_physical_bits_total"]),
                    float(row["mean_full_member_enumeration_recall"]),
                    marker,
                    color,
                )
            )
    chosen.sort(key=lambda item: item[1])

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    fig.suptitle("Repair cost versus recall", x=0.06, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.06, 0.92, "Final $K = 31$ development evaluation cell from the residue-control study.", color=COLORS["gray"])

    for label, bits, recall, marker, color in chosen:
        ax.scatter(bits, recall, s=85, marker=marker, color=color, edgecolor=COLORS["dark"], linewidth=0.7, zorder=3)
        ax.annotate(
            f"{label}\n{bits:.0f} bits, {recall:.3f}",
            (bits, recall),
            textcoords="offset points",
            xytext=(8, 8),
            fontsize=8.5,
        )

    ax.set_xlabel("Physical bits per bundle")
    ax.set_ylabel("Full-member enumeration recall")
    ax.set_ylim(0.4, 1.02)
    ax.grid(color="#D7DEE8", linewidth=0.8)

    handles = [
        Line2D([0], [0], marker=marker, linestyle="none", markerfacecolor=color, markeredgecolor=COLORS["dark"], label=label)
        for label, _, _, marker, color in chosen
    ]
    ax.legend(handles=handles, frameon=False, loc="lower right")

    save_figure(fig, "figure4_repair_costs")


def figure5_escalation() -> None:
    rows = load_csv(ROOT / "results" / "oracle_portfolio_v0_1" / "method_summary.csv")
    final_non_easy = {row["method_id"]: row for row in rows if row["subset"] == "FINAL_NON_EASY"}
    map_fast = float(final_non_easy["MAP_D1024_FAST"]["median_latency_sec"])
    bcf = float(final_non_easy["BCF_NATIVE"]["median_latency_sec"])
    exit_rate = float(final_non_easy["MAP_D1024_FAST"]["accepted_exact_coverage"])
    break_even = map_fast / bcf
    cascade = map_fast + (1.0 - exit_rate) * bcf

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.4))
    fig.suptitle("Sequential escalation economics", x=0.06, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.06, 0.92, "Fast-path probe cost is measured on the same runtime and hardware as the fallback arm.", color=COLORS["gray"])

    panels = [
        (
            axes[0],
            "(a) Verified exit probability",
            [("Observed exit", exit_rate, COLORS["blue"]), ("Break-even exit", break_even, COLORS["orange"])],
            "Probability",
            1.0,
        ),
        (
            axes[1],
            "(b) Expected latency",
            [("Expected cascade", cascade, COLORS["purple"]), ("Always BCF", bcf, COLORS["green"])],
            "Seconds",
            max(cascade, bcf) * 1.35,
        ),
    ]

    for ax, title, values, ylabel, ymax in panels:
        ax.set_title(title, loc="left")
        y_positions = list(range(len(values)))[::-1]
        for pos, (label, value, color) in zip(y_positions, values):
            ax.hlines(pos, 0, value, color=color, linewidth=3)
            ax.plot(value, pos, "o", color=color, markersize=8)
            ax.text(value + ymax * 0.03, pos, f"{value:.3f}" if ylabel == "Probability" else f"{value:.4f}", va="center", fontsize=9)
        ax.set_yticks(y_positions)
        ax.set_yticklabels([label for label, _, _ in values])
        ax.set_xlim(0, ymax)
        ax.set_xlabel(ylabel)
        ax.grid(axis="x", color="#D7DEE8", linewidth=0.8)

    save_figure(fig, "figure5_escalation")


def figure6_architecture_flow() -> None:
    fig, ax = plt.subplots(figsize=(10.0, 5.0))
    ax.set_axis_off()
    ax.text(0.0, 1.02, "Resource-aware architecture guide", transform=ax.transAxes, fontsize=12, fontweight="bold")
    ax.text(
        0.0,
        0.97,
        "Supplementary decision flow retained for the source bundle rather than the main paper.",
        transform=ax.transAxes,
        color=COLORS["gray"],
    )

    boxes = [
        (0.03, 0.62, 0.18, 0.16, "Define task\nand risk"),
        (0.28, 0.62, 0.20, 0.16, "Exact structure\navailable?"),
        (0.55, 0.77, 0.20, 0.14, "Preserve exact\nside information"),
        (0.55, 0.50, 0.20, 0.14, "Use bounded\napproximate view"),
        (0.80, 0.77, 0.16, 0.14, "Verify"),
        (0.80, 0.50, 0.16, 0.14, "Decode or\nabstain"),
        (0.55, 0.23, 0.20, 0.14, "Promote only\nnondominated cost"),
        (0.80, 0.23, 0.16, 0.14, "Stop or\nfallback"),
    ]
    for x, y, w, h, label in boxes:
        ax.add_patch(
            patches.FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.012,rounding_size=0.02",
                linewidth=1.0,
                edgecolor=COLORS["dark"],
                facecolor=COLORS["light"],
                transform=ax.transAxes,
            )
        )
        ax.text(x + w / 2, y + h / 2, label, transform=ax.transAxes, ha="center", va="center")

    arrows = [
        ((0.21, 0.70), (0.28, 0.70)),
        ((0.48, 0.72), (0.55, 0.84)),
        ((0.48, 0.66), (0.55, 0.57)),
        ((0.75, 0.84), (0.80, 0.84)),
        ((0.75, 0.57), (0.80, 0.57)),
        ((0.65, 0.50), (0.65, 0.37)),
        ((0.75, 0.30), (0.80, 0.30)),
    ]
    for (x1, y1), (x2, y2) in arrows:
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            xycoords=ax.transAxes,
            textcoords=ax.transAxes,
            arrowprops=dict(arrowstyle="-|>", lw=1.6, color=COLORS["blue"]),
        )

    save_figure(fig, "figure6_architecture_flow")


def main() -> None:
    ensure_dir(FIG_DIR)
    figure1_budget_map()
    figure2_evidence_atlas()
    figure3_capacity_frontier()
    figure4_repair_costs()
    figure5_escalation()
    figure6_architecture_flow()
    print(f"Generated vector manuscript figures in {FIG_DIR}")


if __name__ == "__main__":
    main()
