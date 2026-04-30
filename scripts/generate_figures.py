"""
generate_figures.py -- Step 22: all paper figures (300 dpi PNG).

Figure 1: F1 bar chart (all pipelines, with error bars)
Figure 2: Precision vs Recall grouped bar chart
Figure 3: ROC curves overlaid (all pipelines)
Figure 4: Confusion matrix heatmaps (2x2 grid, best 4 pipelines)
Figure 5: Static feature importance bar chart

Requires per_contract_predictions.csv to exist (run error_analysis.py first).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    roc_curve,
    auc as sklearn_auc,
)

from src.utils import RESULTS_DIR, get_logger

log = get_logger("generate_figures")

FIGURES_DIR = Path(__file__).resolve().parents[1] / "outputs" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

MASTER_CSV = RESULTS_DIR / "master_comparison_table.csv"
PRED_CSV   = RESULTS_DIR / "per_contract_predictions.csv"
FEAT_IMP   = RESULTS_DIR / "static_feature_importance.csv"

# Colour palette (consistent across all figures)
PALETTE = {
    "Static (LR)":      "#2196F3",   # blue
    "Static (RF)":      "#64B5F6",   # light blue
    "Ensemble (LR)":    "#4CAF50",   # green
    "Ensemble (RF)":    "#81C784",   # light green
    "LLM-B":            "#FF9800",   # orange
    "LLM-A":            "#FFCC80",   # light orange
}

DPI = 300

# ── Label mapping from master CSV pipeline names to short labels ─────────────

SHORT = {
    "Static (LogisticRegression)":   "Static (LR)",
    "Static (RandomForest)":         "Static (RF)",
    "Ensemble (LogisticRegression)": "Ensemble (LR)",
    "Ensemble (RandomForest)":       "Ensemble (RF)",
    "LLM (Method B — boolean)":      "LLM-B",
    "LLM (Method A — threshold)":    "LLM-A",
}


def _load_master():
    df = pd.read_csv(MASTER_CSV)
    df["label"] = df["pipeline"].map(SHORT)
    return df


def _load_preds():
    return pd.read_csv(PRED_CSV)


# ── Figure 1: F1 bar chart ───────────────────────────────────────────────────

def fig1_f1_barchart(master):
    fig, ax = plt.subplots(figsize=(9, 5))

    labels  = master["label"].tolist()
    f1_mean = master["f1_mean"].tolist()
    f1_std  = master["f1_std"].tolist()
    colors  = [PALETTE[l] for l in labels]
    x       = np.arange(len(labels))

    bars = ax.bar(x, f1_mean, yerr=f1_std, capsize=5,
                  color=colors, edgecolor="black", linewidth=0.7,
                  error_kw={"elinewidth": 1.2, "ecolor": "#333333"})

    for bar, val, err in zip(bars, f1_mean, f1_std):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + err + 0.008,
                f"{val:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=10)
    ax.set_ylabel("F1 Score (mean ± std, LOTO)", fontsize=11)
    ax.set_title("Detection Performance: F1 Score by Pipeline", fontsize=13, fontweight="bold")
    ax.set_ylim(0, 1.12)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.spines[["top", "right"]].set_visible(False)

    path = FIGURES_DIR / "fig1_f1_comparison.png"
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    log.info("Saved %s", path)


# ── Figure 2: Precision / Recall grouped bar chart ───────────────────────────

def fig2_precision_recall(master):
    labels    = master["label"].tolist()
    precision = master["precision_mean"].tolist()
    recall    = master["recall_mean"].tolist()
    x         = np.arange(len(labels))
    w         = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))

    bars_p = ax.bar(x - w/2, precision, w, label="Precision",
                    color=[PALETTE[l] for l in labels],
                    edgecolor="black", linewidth=0.7, alpha=0.9)
    bars_r = ax.bar(x + w/2, recall, w, label="Recall",
                    color=[PALETTE[l] for l in labels],
                    edgecolor="black", linewidth=0.7, alpha=0.5,
                    hatch="//")

    for bar, val in zip(bars_p, precision):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                f"{val:.2f}", ha="center", va="bottom", fontsize=8)
    for bar, val in zip(bars_r, recall):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                f"{val:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=10)
    ax.set_ylabel("Score (mean, LOTO)", fontsize=11)
    ax.set_title("Precision vs. Recall by Pipeline", fontsize=13, fontweight="bold")
    ax.set_ylim(0, 1.15)
    ax.legend(fontsize=10, framealpha=0.8)
    ax.spines[["top", "right"]].set_visible(False)

    path = FIGURES_DIR / "fig2_precision_recall.png"
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    log.info("Saved %s", path)


# ── Figure 3: ROC curves ─────────────────────────────────────────────────────

def fig3_roc_curves(preds):
    preds = preds.dropna(subset=["static_lr_pred"])

    pipelines = [
        ("Static (LR)",   "static_lr_prob",   preds["true_label"] == "honeypot"),
        ("Ensemble (LR)", "ensemble_lr_prob",  preds["true_label"] == "honeypot"),
        ("LLM-B",         "llm_b_prob",        preds["true_label"] == "honeypot"),
    ]

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, label="Random (AUC=0.50)")

    for label, prob_col, _ in pipelines:
        mask = preds[prob_col].notna()
        y_true = (preds.loc[mask, "true_label"] == "honeypot").astype(int).values
        y_prob = preds.loc[mask, prob_col].values
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        roc_auc = sklearn_auc(fpr, tpr)
        ax.plot(fpr, tpr, color=PALETTE[label], linewidth=2,
                label=f"{label} (AUC = {roc_auc:.3f})")

    ax.set_xlabel("False Positive Rate", fontsize=11)
    ax.set_ylabel("True Positive Rate", fontsize=11)
    ax.set_title("ROC Curves — All Pipelines", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10, loc="lower right", framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)

    path = FIGURES_DIR / "fig3_roc_curves.png"
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    log.info("Saved %s", path)


# ── Figure 4: Confusion matrices ─────────────────────────────────────────────

def fig4_confusion_matrices(preds):
    combos = [
        ("Static-LR",   "static_lr_pred"),
        ("Ensemble-LR", "ensemble_lr_pred"),
        ("LLM-B",       "llm_b_pred"),
    ]
    # use 3 panels in a row
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))

    for ax, (label, col) in zip(axes, combos):
        mask = preds[col].notna()
        y_true = (preds.loc[mask, "true_label"] == "honeypot").astype(int).values
        y_pred = preds.loc[mask, col].astype(int).values
        cm = confusion_matrix(y_true, y_pred)

        im = ax.imshow(cm, cmap="Blues", aspect="auto")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred: Legit", "Pred: HP"], fontsize=9)
        ax.set_yticklabels(["True: Legit", "True: HP"], fontsize=9)
        ax.set_title(label, fontsize=11, fontweight="bold")

        for i in range(2):
            for j in range(2):
                color = "white" if cm[i, j] > cm.max() / 2 else "black"
                ax.text(j, i, str(cm[i, j]),
                        ha="center", va="center", fontsize=14,
                        fontweight="bold", color=color)

    fig.suptitle("Confusion Matrices (pooled LOTO predictions)", fontsize=13, fontweight="bold")
    path = FIGURES_DIR / "fig4_confusion_matrices.png"
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    log.info("Saved %s", path)


# ── Figure 5: Feature importance ─────────────────────────────────────────────

def fig5_feature_importance():
    fi = pd.read_csv(FEAT_IMP).sort_values("importance", ascending=True)

    # Shorten feature names for display
    short_names = {
        "uses_tx_origin":                      "tx.origin usage",
        "has_fallback":                        "Has fallback fn",
        "fallback_reverts_non_owner":          "Fallback reverts (non-owner)",
        "require_count":                       "Require count",
        "has_selfdestruct":                    "Has selfdestruct",
        "has_withdrawal_function":             "Has withdrawal fn",
        "withdrawal_owner_only":               "Withdrawal owner-only",
        "uses_inline_assembly":                "Inline assembly",
        "state_changes_before_external_calls": "State changes (pre-call)",
        "payable_to_withdraw_ratio":           "Payable/withdraw ratio",
    }
    fi["display"] = fi["feature"].map(short_names).fillna(fi["feature"])

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#2196F3" if v >= 0.1 else "#90CAF9" for v in fi["importance"]]
    bars = ax.barh(fi["display"], fi["importance"], color=colors,
                   edgecolor="black", linewidth=0.6)

    for bar, val in zip(bars, fi["importance"]):
        ax.text(bar.get_width() + 0.003, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9)

    ax.set_xlabel("Mean Decrease in Impurity (Gini)", fontsize=11)
    ax.set_title("Random Forest Feature Importance (Static Pipeline)", fontsize=13, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, fi["importance"].max() * 1.2)

    path = FIGURES_DIR / "fig5_feature_importance.png"
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    log.info("Saved %s", path)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    master = _load_master()
    preds  = _load_preds()

    fig1_f1_barchart(master)
    fig2_precision_recall(master)
    fig3_roc_curves(preds)
    fig4_confusion_matrices(preds)
    fig5_feature_importance()

    print(f"\nAll figures saved to: {FIGURES_DIR}")
    print("  fig1_f1_comparison.png")
    print("  fig2_precision_recall.png")
    print("  fig3_roc_curves.png")
    print("  fig4_confusion_matrices.png")
    print("  fig5_feature_importance.png")
