import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict

from config import (
    OUTPUT_DIR,
    YEAR,
    GP_NAME,
    ROOKIE_FULL_NAMES,
    FUEL_EFFECT_PER_KG,
    FUEL_CONSUMPTION_KG_PER_LAP,
    ESTIMATED_START_FUEL_KG,
)


def format_deficit(val):
    if val >= 0:
        return f"+{val:.3f}s"
    return f"{val:.3f}s"


def format_deficit_pct(val):
    if val >= 0:
        return f"+{val:.2f}%"
    return f"{val:.2f}%"


def generate_advanced_report(
    compound_pace_df: pd.DataFrame,
    aggregate_pace_df: pd.DataFrame,
    stint_trend_df: pd.DataFrame,
    tyre_scores_df: pd.DataFrame,
    long_run_comparison_df: pd.DataFrame,
    sector_analysis_df: pd.DataFrame,
    evolution_df: pd.DataFrame,
    summary: Dict,
) -> str:
    report = []
    report.append(f"# {YEAR} {GP_NAME} GP - FP1 Rookie Performance Analysis")
    report.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    
    report.append("---\n")
    report.append("## Executive Summary\n")
    
    if summary.get("rookies_with_data"):
        report.append(f"Rookies analyzed: **{summary['rookies_with_data']}**\n")
        
        report.append("\n| Metric | Value |")
        report.append("|--------|-------|")
        
        if summary.get("avg_raw_deficit"):
            val = summary['avg_raw_deficit']
            sign = "+" if val >= 0 else ""
            report.append(f"| Average Raw Deficit | {sign}{val:.3f}s |")
        if summary.get("avg_corrected_deficit"):
            val = summary['avg_corrected_deficit']
            sign = "+" if val >= 0 else ""
            report.append(f"| Average Corrected Deficit | {sign}{val:.3f}s |")
        if summary.get("avg_raw_deficit") and summary.get("avg_corrected_deficit"):
            correction = abs(summary["avg_raw_deficit"] - summary["avg_corrected_deficit"])
            report.append(f"| Correction Impact | {correction:.3f}s |")
        if summary.get("best_rookie"):
            val = summary['best_corrected_deficit']
            sign = "+" if val >= 0 else ""
            report.append(f"| Closest to Teammate | {summary['best_rookie']} ({sign}{val:.3f}s) |")
        if summary.get("best_tyre_manager_rookie"):
            report.append(f"| Best Tyre Management | {summary['best_tyre_manager_rookie']} |")
        if summary.get("compounds_analyzed"):
            report.append(f"| Compounds Analyzed | {', '.join(summary['compounds_analyzed'])} |")
    
    report.append("\n---\n")
    report.append("## Track Evolution\n")
    
    if not evolution_df.empty and "EvolutionRate" in evolution_df.columns:
        rate = evolution_df["EvolutionRate"].iloc[0]
        direction = "improving" if rate < 0 else "degrading"
        report.append(f"Track conditions were **{direction}** at **{abs(rate):.4f} s/min**.\n")
    
    report.append("\n---\n")
    report.append("## Compound-Matched Pace\n")
    
    if not compound_pace_df.empty:
        for compound in compound_pace_df["Compound"].unique():
            compound_data = compound_pace_df[compound_pace_df["Compound"] == compound].sort_values("CorrectedDeficit")
            
            report.append(f"\n### {compound}\n")
            report.append("| Rookie | Team | Raw Deficit | Corrected Deficit | Laps |")
            report.append("|--------|------|-------------|-------------------|------|")
            
            for _, row in compound_data.iterrows():
                report.append(
                    f"| {row['RookieName']} | {row['Team']} | "
                    f"{format_deficit(row['RawDeficit'])} | {format_deficit(row['CorrectedDeficit'])} | "
                    f"{row['RookieLapCount']} |"
                )
    
    report.append("\n---\n")
    report.append("## Aggregate Pace\n")
    
    if not aggregate_pace_df.empty:
        report.append("| Rank | Rookie | Team | Corrected Deficit | % Deficit |")
        report.append("|------|--------|------|-------------------|-----------|")
        
        for rank, (_, row) in enumerate(aggregate_pace_df.sort_values("AvgCorrectedDeficit").iterrows(), 1):
            report.append(
                f"| {rank} | {row['RookieName']} | {row['Team']} | "
                f"{format_deficit(row['AvgCorrectedDeficit'])} | {format_deficit_pct(row['DeficitPercent'])} |"
            )
    
    report.append("\n---\n")
    report.append("## Stint Lap Time Trends\n")
    report.append("This shows the observed lap time change per lap over each stint, after correcting for fuel burn-off.\n")
    report.append("- **Positive values**: lap times getting slower (tyre degradation exceeds track evolution)\n")
    report.append("- **Negative values**: lap times getting faster (track evolution exceeds tyre degradation)\n")
    report.append("\nAbu Dhabi is a low-degradation circuit. The smooth surface and relatively low-energy corners mean tyre wear is minimal, so track evolution and fuel effects often dominate.\n")
    
    if not stint_trend_df.empty:
        rookie_trends = stint_trend_df[stint_trend_df["IsRookie"] == True]
        regular_trends = stint_trend_df[stint_trend_df["IsRookie"] == False]
        
        if not rookie_trends.empty:
            report.append("\n### Rookies (FP1)\n")
            for compound in rookie_trends["Compound"].unique():
                compound_data = rookie_trends[rookie_trends["Compound"] == compound].sort_values("FuelCorrectedTrend")
                
                report.append(f"\n**{compound}**\n")
                report.append("| Rookie | Team | Trend (s/lap) | Laps | R² |")
                report.append("|--------|------|---------------|------|-----|")
                
                for _, row in compound_data.iterrows():
                    trend = row['FuelCorrectedTrend']
                    sign = "+" if trend >= 0 else ""
                    report.append(
                        f"| {row['DriverName']} | {row['Team']} | "
                        f"{sign}{trend:.3f} | {row['LapCount']} | "
                        f"{row['RSquared']:.2f} |"
                    )
        
        if not regular_trends.empty:
            report.append("\n### Regular Drivers (FP2)\n")
            for compound in regular_trends["Compound"].unique():
                compound_data = regular_trends[regular_trends["Compound"] == compound].sort_values("FuelCorrectedTrend")
                
                report.append(f"\n**{compound}**\n")
                report.append("| Driver | Team | Trend (s/lap) | Laps | R² |")
                report.append("|--------|------|---------------|------|-----|")
                
                for _, row in compound_data.iterrows():
                    trend = row['FuelCorrectedTrend']
                    sign = "+" if trend >= 0 else ""
                    report.append(
                        f"| {row['DriverName']} | {row['Team']} | "
                        f"{sign}{trend:.3f} | {row['LapCount']} | "
                        f"{row['RSquared']:.2f} |"
                    )
    
    report.append("\n---\n")
    report.append("## Tyre Management Scores\n")
    
    if not tyre_scores_df.empty:
        rookie_scores = tyre_scores_df[tyre_scores_df["IsRookie"] == True]
        
        if not rookie_scores.empty:
            avg_scores = rookie_scores.groupby(["DriverName", "Team"]).agg(
                AvgScore=("TyreManagementScore", "mean"),
                AvgTrendVsMedian=("TrendVsMedian", "mean"),
            ).reset_index().sort_values("AvgScore", ascending=False)
            
            report.append("| Rank | Rookie | Team | Score | vs Median |")
            report.append("|------|--------|------|-------|-----------|")
            
            for rank, (_, row) in enumerate(avg_scores.iterrows(), 1):
                sign = "+" if row["AvgTrendVsMedian"] > 0 else ""
                report.append(
                    f"| {rank} | {row['DriverName']} | {row['Team']} | "
                    f"{row['AvgScore']:.1f} | {sign}{row['AvgTrendVsMedian']:.3f}s/lap |"
                )
    
    report.append("\n---\n")
    report.append("## Long Run Pace\n")
    
    if not long_run_comparison_df.empty:
        report.append("| Rookie | Team | Compound | Deficit | Rookie σ | Regular σ |")
        report.append("|--------|------|----------|---------|----------|-----------|")
        
        for _, row in long_run_comparison_df.sort_values("LongRunDeficit").iterrows():
            report.append(
                f"| {row['RookieName']} | {row['Team']} | {row['Compound']} | "
                f"{format_deficit(row['LongRunDeficit'])} | {row['RookieConsistency']:.3f}s | "
                f"{row['RegularConsistency']:.3f}s |"
            )
    
    report.append("\n---\n")
    report.append("## Sector Analysis\n")
    
    if not sector_analysis_df.empty:
        for compound in sector_analysis_df["Compound"].unique():
            compound_data = sector_analysis_df[sector_analysis_df["Compound"] == compound]
            
            report.append(f"\n### {compound}\n")
            report.append("| Rookie | Team | S1 | S2 | S3 | Weakest |")
            report.append("|--------|------|----|----|----|---------|")
            
            for rookie in compound_data["Rookie"].unique():
                rookie_sectors = compound_data[compound_data["Rookie"] == rookie]
                name = rookie_sectors["RookieName"].iloc[0]
                team = rookie_sectors["Team"].iloc[0]
                
                s1 = rookie_sectors[rookie_sectors["Sector"] == 1]["BestDeficit"].iloc[0] if len(rookie_sectors[rookie_sectors["Sector"] == 1]) > 0 else 0
                s2 = rookie_sectors[rookie_sectors["Sector"] == 2]["BestDeficit"].iloc[0] if len(rookie_sectors[rookie_sectors["Sector"] == 2]) > 0 else 0
                s3 = rookie_sectors[rookie_sectors["Sector"] == 3]["BestDeficit"].iloc[0] if len(rookie_sectors[rookie_sectors["Sector"] == 3]) > 0 else 0
                
                weakest = max([(s1, "S1"), (s2, "S2"), (s3, "S3")], key=lambda x: x[0])[1]
                
                report.append(
                    f"| {name} | {team} | {format_deficit(s1)} | {format_deficit(s2)} | {format_deficit(s3)} | {weakest} |"
                )
    
    report.append("\n---\n")
    report.append("## Methodology\n")
    
    report.append(f"| Parameter | Value |")
    report.append(f"|-----------|-------|")
    report.append(f"| Fuel Effect | {FUEL_EFFECT_PER_KG} s/kg |")
    report.append(f"| Fuel Consumption | {FUEL_CONSUMPTION_KG_PER_LAP} kg/lap |")
    report.append(f"| Estimated Start Fuel | {ESTIMATED_START_FUEL_KG} kg |")
    
    report.append("\n### Limitations\n")
    report.append("- **Cross-session comparison**: Rookies ran in FP1, regulars in FP2. Track conditions, temperature, and grip levels differ between sessions. FP2 typically has more rubber/grip, which may artificially reduce rookie deficits.\n")
    report.append("- Actual fuel loads unknown\n")
    report.append("- Engine modes not visible\n")
    report.append("- Setup differences not accounted for\n")
    report.append("- Run programs vary by team\n")
    
    return "\n".join(report)


def save_report(report_content: str) -> Path:
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    filepath = Path(OUTPUT_DIR) / "rookie_analysis_report.md"
    with open(filepath, "w") as f:
        f.write(report_content)
    return filepath