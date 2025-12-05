import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

from config import TEAM_COLORS, OUTPUT_DIR, DRIVER_ROOKIE_MAPPING


COMPOUND_COLORS = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFF200",
    "HARD": "#EBEBEB",
    "INTERMEDIATE": "#39B54A",
    "WET": "#00AEEF",
}


def setup_style():
    plt.style.use("seaborn-v0_8-darkgrid")
    plt.rcParams["figure.figsize"] = (12, 8)
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.titlesize"] = 14
    plt.rcParams["axes.labelsize"] = 12
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["savefig.dpi"] = 150
    plt.rcParams["savefig.bbox"] = "tight"
    plt.rcParams["axes.facecolor"] = "#1a1a2e"
    plt.rcParams["figure.facecolor"] = "#1a1a2e"
    plt.rcParams["text.color"] = "white"
    plt.rcParams["axes.labelcolor"] = "white"
    plt.rcParams["xtick.color"] = "white"
    plt.rcParams["ytick.color"] = "white"
    plt.rcParams["axes.edgecolor"] = "white"
    plt.rcParams["grid.color"] = "#333366"


def ensure_output_dir():
    Path(OUTPUT_DIR).mkdir(exist_ok=True)


def plot_compound_matched_pace(compound_pace_df: pd.DataFrame, session_name: str) -> plt.Figure:
    setup_style()
    
    compounds = compound_pace_df["Compound"].unique()
    n_compounds = len(compounds)
    
    fig, axes = plt.subplots(1, n_compounds, figsize=(6 * n_compounds, 8), squeeze=False)
    axes = axes.flatten()
    
    for idx, compound in enumerate(compounds):
        ax = axes[idx]
        compound_data = compound_pace_df[compound_pace_df["Compound"] == compound].sort_values("CorrectedDeficit")
        
        colors = [TEAM_COLORS.get(team, "#888888") for team in compound_data["Team"]]
        
        y_pos = np.arange(len(compound_data))
        ax.barh(y_pos, compound_data["CorrectedDeficit"], color=colors, edgecolor="white", linewidth=0.5)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(compound_data["RookieName"])
        ax.set_xlabel("Corrected Deficit (seconds)")
        ax.set_title(f"{compound}", color=COMPOUND_COLORS.get(compound, "white"), fontweight="bold")
        ax.axvline(x=0, color="white", linestyle="-", linewidth=0.5)
        
        for i, (deficit, raw) in enumerate(zip(compound_data["CorrectedDeficit"], compound_data["RawDeficit"])):
            label = f"+{deficit:.3f}s (raw: +{raw:.3f}s)"
            ax.text(deficit + 0.02, i, label, va="center", fontsize=8, color="white")
    
    fig.suptitle(f"Compound-Matched Pace Deficit (Fuel/Track/Tyre Corrected) - {session_name}", fontsize=14, y=1.02)
    plt.tight_layout()
    return fig


def plot_aggregate_pace_comparison(aggregate_df: pd.DataFrame, session_name: str) -> plt.Figure:
    setup_style()
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))
    
    aggregate_df = aggregate_df.sort_values("AvgCorrectedDeficit")
    colors = [TEAM_COLORS.get(team, "#888888") for team in aggregate_df["Team"]]
    
    ax1 = axes[0]
    y_pos = np.arange(len(aggregate_df))
    ax1.barh(y_pos, aggregate_df["AvgRawDeficit"], color=colors, alpha=0.5, label="Raw", edgecolor="white")
    ax1.barh(y_pos, aggregate_df["AvgCorrectedDeficit"], color=colors, alpha=0.9, label="Corrected", edgecolor="white", linewidth=0.5)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(aggregate_df["RookieName"])
    ax1.set_xlabel("Average Deficit (seconds)")
    ax1.set_title("Raw vs Corrected Deficit")
    ax1.legend()
    
    for i, (raw, corr) in enumerate(zip(aggregate_df["AvgRawDeficit"], aggregate_df["AvgCorrectedDeficit"])):
        ax1.text(max(raw, corr) + 0.02, i, f"Δ{abs(raw-corr):.3f}s", va="center", fontsize=8, color="white")
    
    ax2 = axes[1]
    ax2.barh(y_pos, aggregate_df["DeficitPercent"], color=colors, edgecolor="white", linewidth=0.5)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(aggregate_df["RookieName"])
    ax2.set_xlabel("Deficit (%)")
    ax2.set_title("Percentage Deficit to Teammate")
    
    for i, pct in enumerate(aggregate_df["DeficitPercent"]):
        ax2.text(pct + 0.02, i, f"+{pct:.2f}%", va="center", fontsize=9, color="white")
    
    fig.suptitle(f"Aggregate Pace Analysis - {session_name}", fontsize=14, y=1.02)
    plt.tight_layout()
    return fig


def plot_stint_degradation(stint_trend_df: pd.DataFrame, session_name: str) -> plt.Figure:
    setup_style()
    
    compounds = stint_trend_df["Compound"].unique()
    fig, axes = plt.subplots(1, len(compounds), figsize=(7 * len(compounds), 8), squeeze=False)
    axes = axes.flatten()
    
    for idx, compound in enumerate(compounds):
        ax = axes[idx]
        compound_data = stint_trend_df[stint_trend_df["Compound"] == compound].copy()
        
        if compound_data.empty:
            continue
        
        compound_data = compound_data.sort_values("FuelCorrectedTrend")
        
        colors = ["#E74C3C" if r else "#3498DB" for r in compound_data["IsRookie"]]
        
        y_pos = np.arange(len(compound_data))
        ax.barh(y_pos, compound_data["FuelCorrectedTrend"], color=colors, edgecolor="white", linewidth=0.5)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(compound_data["DriverName"])
        ax.set_xlabel("Lap Time Trend (sec/lap)")
        ax.set_title(f"{compound}", color=COMPOUND_COLORS.get(compound, "white"), fontweight="bold")
        ax.axvline(x=0, color="white", linestyle="--", linewidth=0.5)
        
        for i, (trend, r2) in enumerate(zip(compound_data["FuelCorrectedTrend"], compound_data["RSquared"])):
            ax.text(trend + 0.002, i, f"{trend:.3f} (R²={r2:.2f})", va="center", fontsize=8, color="white")
    
    rookie_patch = mpatches.Patch(color="#E74C3C", label="Rookie")
    regular_patch = mpatches.Patch(color="#3498DB", label="Regular Driver")
    fig.legend(handles=[rookie_patch, regular_patch], loc="upper right")
    
    fig.suptitle(f"Stint Lap Time Trend (Fuel-Corrected) - {session_name}", fontsize=14, y=1.02)
    plt.tight_layout()
    return fig


def plot_stint_pace_evolution(laps_df: pd.DataFrame, driver: str, session_name: str) -> plt.Figure:
    setup_style()
    
    driver_laps = laps_df[laps_df["Driver"] == driver].copy()
    
    if driver_laps.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", color="white")
        return fig
    
    stints = driver_laps["StintNumber"].unique()
    n_stints = len(stints)
    
    fig, axes = plt.subplots(1, n_stints, figsize=(5 * n_stints, 6), squeeze=False)
    axes = axes.flatten()
    
    for idx, stint in enumerate(stints):
        ax = axes[idx]
        stint_laps = driver_laps[driver_laps["StintNumber"] == stint].sort_values("TyreLap")
        
        compound = stint_laps["Compound"].iloc[0]
        color = COMPOUND_COLORS.get(compound, "#888888")
        
        ax.plot(stint_laps["TyreLap"], stint_laps["LapTimeSeconds"], "o-", color=color, label="Raw", alpha=0.6)
        ax.plot(stint_laps["TyreLap"], stint_laps["FuelCorrectedTime"], "s-", color=color, label="Fuel Corrected")
        
        ax.set_xlabel("Tyre Lap")
        ax.set_ylabel("Lap Time (s)")
        ax.set_title(f"Stint {stint} - {compound}")
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    fig.suptitle(f"Stint Pace Evolution - {driver} - {session_name}", fontsize=14, y=1.02)
    plt.tight_layout()
    return fig


def plot_long_run_comparison(long_run_df: pd.DataFrame, session_name: str) -> plt.Figure:
    setup_style()
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))
    
    long_run_df = long_run_df.sort_values("LongRunDeficit")
    colors = [TEAM_COLORS.get(team, "#888888") for team in long_run_df["Team"]]
    
    ax1 = axes[0]
    y_pos = np.arange(len(long_run_df))
    ax1.barh(y_pos, long_run_df["LongRunDeficit"], color=colors, edgecolor="white", linewidth=0.5)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels([f"{row['RookieName']} ({row['Compound']})" for _, row in long_run_df.iterrows()])
    ax1.set_xlabel("Long Run Pace Deficit (seconds)")
    ax1.set_title("Long Run Pace Deficit to Teammate")
    ax1.axvline(x=0, color="white", linestyle="-", linewidth=0.5)
    
    ax2 = axes[1]
    x = np.arange(len(long_run_df))
    width = 0.35
    ax2.bar(x - width/2, long_run_df["RookieConsistency"], width, label="Rookie", color="#E74C3C")
    ax2.bar(x + width/2, long_run_df["RegularConsistency"], width, label="Regular", color="#3498DB")
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{row['RookieName'][:8]}" for _, row in long_run_df.iterrows()], rotation=45, ha="right")
    ax2.set_ylabel("Lap Time Std Dev (seconds)")
    ax2.set_title("Long Run Consistency Comparison")
    ax2.legend()
    
    fig.suptitle(f"Long Run Analysis - {session_name}", fontsize=14, y=1.02)
    plt.tight_layout()
    return fig


def plot_sector_heatmap(sector_df: pd.DataFrame, session_name: str) -> plt.Figure:
    setup_style()
    
    compounds = sector_df["Compound"].unique()
    n_compounds = len(compounds)
    
    fig, axes = plt.subplots(1, n_compounds, figsize=(8 * n_compounds, 6), squeeze=False)
    axes = axes.flatten()
    
    for idx, compound in enumerate(compounds):
        ax = axes[idx]
        compound_data = sector_df[sector_df["Compound"] == compound]
        
        pivot = compound_data.pivot_table(
            index="RookieName",
            columns="Sector",
            values="BestDeficit",
            aggfunc="mean"
        )
        
        sns.heatmap(
            pivot,
            annot=True,
            fmt=".3f",
            cmap="RdYlGn_r",
            center=0,
            ax=ax,
            cbar_kws={"label": "Deficit (s)"},
            annot_kws={"color": "black"}
        )
        ax.set_title(f"{compound}", color=COMPOUND_COLORS.get(compound, "white"), fontweight="bold")
        ax.set_xlabel("Sector")
        ax.set_ylabel("Rookie")
    
    fig.suptitle(f"Sector Deficit Heatmap by Compound - {session_name}", fontsize=14, y=1.02)
    plt.tight_layout()
    return fig


def plot_track_evolution(evolution_df: pd.DataFrame, session_name: str) -> plt.Figure:
    setup_style()
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.scatter(evolution_df["WindowMid"], evolution_df["BestTime"], color="#3498DB", s=100, zorder=3, label="Best Lap per Window")
    
    if "FittedTime" in evolution_df.columns:
        ax.plot(evolution_df["WindowMid"], evolution_df["FittedTime"], "--", color="#E74C3C", linewidth=2, label="Trend Line")
    
    ax.set_xlabel("Session Time (minutes)")
    ax.set_ylabel("Best Lap Time (seconds)")
    ax.set_title(f"Track Evolution - {session_name}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    if "EvolutionRate" in evolution_df.columns and len(evolution_df) > 0:
        rate = evolution_df["EvolutionRate"].iloc[0]
        ax.text(
            0.02, 0.98,
            f"Evolution Rate: {rate:.4f} s/min",
            transform=ax.transAxes,
            fontsize=10,
            va="top",
            color="white",
            bbox=dict(boxstyle="round", facecolor="#333366", alpha=0.8)
        )
    
    plt.tight_layout()
    return fig


def plot_tyre_management_scores(tyre_scores_df: pd.DataFrame, session_name: str) -> plt.Figure:
    setup_style()
    
    rookie_scores = tyre_scores_df[tyre_scores_df["IsRookie"] == True]
    
    if rookie_scores.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No rookie tyre management data available", ha="center", va="center", color="white")
        return fig
    
    avg_scores = rookie_scores.groupby(["Driver", "DriverName", "Team"]).agg(
        AvgScore=("TyreManagementScore", "mean"),
        AvgTrendVsMedian=("TrendVsMedian", "mean"),
    ).reset_index().sort_values("AvgScore", ascending=False)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    colors = [TEAM_COLORS.get(team, "#888888") for team in avg_scores["Team"]]
    y_pos = np.arange(len(avg_scores))
    
    ax.barh(y_pos, avg_scores["AvgScore"], color=colors, edgecolor="white", linewidth=0.5)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(avg_scores["DriverName"])
    ax.set_xlabel("Tyre Management Score (higher = better)")
    ax.set_title(f"Rookie Tyre Management Scores - {session_name}")
    ax.axvline(x=50, color="white", linestyle="--", linewidth=0.5, label="Median")
    
    for i, (score, trend) in enumerate(zip(avg_scores["AvgScore"], avg_scores["AvgTrendVsMedian"])):
        sign = "+" if trend > 0 else ""
        ax.text(score + 1, i, f"{score:.1f} ({sign}{trend:.3f}s/lap)", va="center", fontsize=9, color="white")
    
    plt.tight_layout()
    return fig


def plot_corrections_breakdown(laps_df: pd.DataFrame, rookie: str, session_name: str) -> plt.Figure:
    setup_style()
    
    rookie_laps = laps_df[laps_df["Driver"] == rookie].sort_values("LapNumber")
    
    if rookie_laps.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", color="white")
        return fig
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    ax1 = axes[0, 0]
    ax1.plot(rookie_laps["LapNumber"], rookie_laps["LapTimeSeconds"], "o-", label="Raw", alpha=0.7)
    ax1.plot(rookie_laps["LapNumber"], rookie_laps["FullyCorrectedTime"], "s-", label="Fully Corrected")
    ax1.set_xlabel("Lap Number")
    ax1.set_ylabel("Lap Time (s)")
    ax1.set_title("Raw vs Fully Corrected Lap Times")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2 = axes[0, 1]
    ax2.bar(rookie_laps["LapNumber"], rookie_laps["FuelCorrection"], alpha=0.7, label="Fuel", color="#3498DB")
    ax2.set_xlabel("Lap Number")
    ax2.set_ylabel("Correction (s)")
    ax2.set_title("Fuel Load Correction")
    ax2.grid(True, alpha=0.3)
    
    ax3 = axes[1, 0]
    ax3.bar(rookie_laps["LapNumber"], rookie_laps["TrackEvolutionCorrection"], alpha=0.7, label="Track Evolution", color="#E74C3C")
    ax3.set_xlabel("Lap Number")
    ax3.set_ylabel("Correction (s)")
    ax3.set_title("Track Evolution Correction")
    ax3.grid(True, alpha=0.3)
    
    ax4 = axes[1, 1]
    ax4.bar(rookie_laps["LapNumber"], rookie_laps["TyreAgeCorrection"], alpha=0.7, label="Tyre Age", color="#2ECC71")
    ax4.set_xlabel("Lap Number")
    ax4.set_ylabel("Correction (s)")
    ax4.set_title("Tyre Age Correction")
    ax4.grid(True, alpha=0.3)
    
    fig.suptitle(f"Lap Time Corrections Breakdown - {rookie} - {session_name}", fontsize=14, y=1.02)
    plt.tight_layout()
    return fig


def save_all_figures(figures: dict):
    ensure_output_dir()
    for name, fig in figures.items():
        filepath = Path(OUTPUT_DIR) / f"{name}.png"
        fig.savefig(filepath, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)