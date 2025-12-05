import pandas as pd
from pathlib import Path

from config import OUTPUT_DIR, ROOKIE_DRIVERS
from data_collector import load_all_sessions, get_lap_data
from advanced_analysis import (
    calculate_track_evolution_model,
    add_fully_corrected_times,
    calculate_compound_matched_pace,
    calculate_aggregate_pace_deficit,
    calculate_stint_analysis,
    calculate_stint_pace_trend,
    calculate_tyre_management_score,
    calculate_long_run_pace,
    compare_long_run_pace,
    calculate_advanced_sector_analysis,
    generate_advanced_summary,
    calculate_empirical_degradation,
    add_stint_info,
    add_fuel_corrected_times,
)
from advanced_visualizations import (
    plot_compound_matched_pace,
    plot_aggregate_pace_comparison,
    plot_stint_degradation,
    plot_stint_pace_evolution,
    plot_long_run_comparison,
    plot_sector_heatmap,
    plot_track_evolution,
    plot_tyre_management_scores,
    plot_corrections_breakdown,
    save_all_figures,
)
from advanced_report import generate_advanced_report, save_report


def ensure_output_dir():
    Path(OUTPUT_DIR).mkdir(exist_ok=True)


def export_dataframes(dataframes: dict):
    ensure_output_dir()
    for name, df in dataframes.items():
        if isinstance(df, pd.DataFrame) and not df.empty:
            filepath = Path(OUTPUT_DIR) / f"{name}.csv"
            df.to_csv(filepath, index=False)


def main():
    print("Loading session data...")
    sessions = load_all_sessions()
    fp1 = sessions["FP1"]
    fp2 = sessions["FP2"]
    
    print("Building track evolution model...")
    fp1_evolution = calculate_track_evolution_model(fp1)
    fp2_evolution = calculate_track_evolution_model(fp2)
    
    print("Calculating empirical tyre degradation...")
    fp1_laps_raw = get_lap_data(fp1)
    fp1_laps_with_stints = add_stint_info(fp1_laps_raw)
    fp1_laps_fuel_corrected = add_fuel_corrected_times(fp1_laps_with_stints)
    empirical_deg = calculate_empirical_degradation(fp1_laps_fuel_corrected)
    
    for compound, stats in empirical_deg.items():
        print(f"  {compound}: {stats['median']:.4f} s/lap ({stats['n_stints']} stints)")
    
    print("Preparing corrected lap data...")
    fp1_laps = get_lap_data(fp1)
    fp1_laps_corrected = add_fully_corrected_times(fp1_laps, fp1_evolution, empirical_deg)
    
    print("Calculating compound-matched pace (FP1 rookies vs FP2 regulars)...")
    compound_pace = calculate_compound_matched_pace(fp1, fp2, fp1_evolution, fp2_evolution)
    
    print("Calculating aggregate pace...")
    aggregate_pace = calculate_aggregate_pace_deficit(compound_pace)
    
    print("Analyzing stints...")
    stint_analysis = calculate_stint_analysis(fp1, fp1_evolution)
    
    print("Calculating stint pace trends...")
    stint_trends = calculate_stint_pace_trend(fp1, fp2, fp1_evolution, fp2_evolution)
    
    print("Calculating tyre management scores...")
    tyre_scores = calculate_tyre_management_score(stint_trends)
    
    print("Analyzing long runs...")
    long_runs = calculate_long_run_pace(fp1, fp2, fp1_evolution, fp2_evolution)
    long_run_comparison = compare_long_run_pace(long_runs)
    
    print("Analyzing sectors (FP1 rookies vs FP2 regulars)...")
    sector_analysis = calculate_advanced_sector_analysis(fp1, fp2, fp1_evolution, fp2_evolution)
    
    print("Generating summary...")
    summary = generate_advanced_summary(
        compound_pace,
        aggregate_pace,
        stint_trends,
        long_run_comparison,
    )
    
    print("Creating visualizations...")
    figures = {}
    
    figures["track_evolution_fp1"] = plot_track_evolution(fp1_evolution, "FP1")
    figures["track_evolution_fp2"] = plot_track_evolution(fp2_evolution, "FP2")
    
    if not compound_pace.empty:
        figures["compound_matched_pace"] = plot_compound_matched_pace(compound_pace, "FP1")
    
    if not aggregate_pace.empty:
        figures["aggregate_pace_comparison"] = plot_aggregate_pace_comparison(aggregate_pace, "FP1")
    
    if not stint_trends.empty:
        figures["stint_pace_trends"] = plot_stint_degradation(stint_trends, "FP1+FP2")
    
    if not long_run_comparison.empty:
        figures["long_run_comparison"] = plot_long_run_comparison(long_run_comparison, "FP1")
    
    if not sector_analysis.empty:
        figures["sector_heatmap"] = plot_sector_heatmap(sector_analysis, "FP1")
    
    if not tyre_scores.empty:
        figures["tyre_management_scores"] = plot_tyre_management_scores(tyre_scores, "FP1")
    
    for rookie in ROOKIE_DRIVERS:
        if rookie in fp1_laps_corrected["Driver"].values:
            figures[f"stint_evolution_{rookie}"] = plot_stint_pace_evolution(
                fp1_laps_corrected, rookie, "FP1"
            )
            figures[f"corrections_breakdown_{rookie}"] = plot_corrections_breakdown(
                fp1_laps_corrected, rookie, "FP1"
            )
    
    print("Saving visualizations...")
    save_all_figures(figures)
    
    print("Exporting data...")
    
    empirical_deg_df = pd.DataFrame([
        {"Compound": comp, **stats}
        for comp, stats in empirical_deg.items()
    ])
    
    dataframes = {
        "track_evolution_fp1": fp1_evolution,
        "track_evolution_fp2": fp2_evolution,
        "empirical_degradation": empirical_deg_df,
        "compound_matched_pace": compound_pace,
        "aggregate_pace_deficit": aggregate_pace,
        "stint_analysis": stint_analysis,
        "stint_pace_trends": stint_trends,
        "tyre_management_scores": tyre_scores,
        "long_run_pace": long_runs,
        "long_run_comparison": long_run_comparison,
        "sector_analysis": sector_analysis,
        "corrected_laps_fp1": fp1_laps_corrected,
    }
    export_dataframes(dataframes)
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(Path(OUTPUT_DIR) / "summary.csv", index=False)
    
    print("Generating report...")
    report_content = generate_advanced_report(
        compound_pace,
        aggregate_pace,
        stint_trends,
        tyre_scores,
        long_run_comparison,
        sector_analysis,
        fp1_evolution,
        summary,
    )
    report_path = save_report(report_content)
    
    print(f"\nComplete. Output: {OUTPUT_DIR}/")
    print(f"Rookies: {summary['rookies_with_data']}/{summary['total_rookies']}")
    if summary["avg_corrected_deficit"]:
        print(f"Avg deficit: +{summary['avg_corrected_deficit']:.3f}s")
    if summary["best_rookie"]:
        print(f"Best: {summary['best_rookie']} (+{summary['best_corrected_deficit']:.3f}s)")


if __name__ == "__main__":
    main()