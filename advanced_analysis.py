import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, List
from scipy import stats

from config import (
    DRIVER_ROOKIE_MAPPING,
    ROOKIE_DRIVERS,
    REGULAR_DRIVERS,
    TEAM_MAPPING,
    ROOKIE_FULL_NAMES,
    REGULAR_FULL_NAMES,
    ALL_DRIVER_NAMES,
    FUEL_EFFECT_PER_KG,
    FUEL_CONSUMPTION_KG_PER_LAP,
    ESTIMATED_START_FUEL_KG,
    TIRE_DEGRADATION_ESTIMATES,
    MIN_LAPS_FOR_DEGRADATION,
    TRACK_EVOLUTION_WINDOW_MINUTES,
    OUTLIER_THRESHOLD_PERCENT,
)
from data_collector import get_lap_data


def add_stint_info(laps: pd.DataFrame, gap_threshold_seconds: float = 300) -> pd.DataFrame:
    laps = laps.copy()
    result_frames = []
    
    for driver in laps["Driver"].unique():
        driver_laps = laps[laps["Driver"] == driver].sort_values("LapStartTime").copy()
        
        if driver_laps.empty:
            continue
        
        driver_laps["TimeSincePrevLap"] = driver_laps["LapStartTime"].diff().dt.total_seconds()
        driver_laps["CompoundChange"] = driver_laps["Compound"] != driver_laps["Compound"].shift(1)
        driver_laps["NewStint"] = (
            (driver_laps["TimeSincePrevLap"] > gap_threshold_seconds) |
            driver_laps["CompoundChange"] |
            driver_laps["TimeSincePrevLap"].isna()
        )
        driver_laps["StintNumber"] = driver_laps["NewStint"].cumsum()
        
        stint_lap_counts = driver_laps.groupby("StintNumber").cumcount() + 1
        driver_laps["TyreLap"] = stint_lap_counts
        
        result_frames.append(driver_laps)
    
    return pd.concat(result_frames, ignore_index=True)


def estimate_fuel_load(lap_number: int, session_total_laps: int = 30) -> float:
    laps_completed = lap_number - 1
    fuel_burned = laps_completed * FUEL_CONSUMPTION_KG_PER_LAP
    return max(ESTIMATED_START_FUEL_KG - fuel_burned, 5)


def calculate_fuel_correction(lap_number: int, reference_lap: int = 1) -> float:
    fuel_at_lap = estimate_fuel_load(lap_number)
    fuel_at_reference = estimate_fuel_load(reference_lap)
    fuel_difference = fuel_at_lap - fuel_at_reference
    return fuel_difference * FUEL_EFFECT_PER_KG


def add_fuel_corrected_times(laps: pd.DataFrame) -> pd.DataFrame:
    laps = laps.copy()
    median_lap = laps["LapNumber"].median()
    
    laps["FuelCorrection"] = laps["LapNumber"].apply(
        lambda x: calculate_fuel_correction(x, int(median_lap))
    )
    laps["FuelCorrectedTime"] = laps["LapTimeSeconds"] + laps["FuelCorrection"]
    
    return laps


def calculate_track_evolution_model(session) -> pd.DataFrame:
    laps = get_lap_data(session)
    laps = laps.copy()
    
    best_time = laps["LapTimeSeconds"].min()
    threshold = best_time * 1.05
    laps = laps[laps["LapTimeSeconds"] <= threshold]
    
    laps["SessionMinute"] = (
        laps["LapStartTime"] - session.session_start_time
    ).dt.total_seconds() / 60
    
    best_per_window = []
    max_minute = laps["SessionMinute"].max()
    
    for window_start in np.arange(0, max_minute, TRACK_EVOLUTION_WINDOW_MINUTES):
        window_end = window_start + TRACK_EVOLUTION_WINDOW_MINUTES
        window_laps = laps[
            (laps["SessionMinute"] >= window_start) &
            (laps["SessionMinute"] < window_end)
        ]
        
        if len(window_laps) >= 3:
            best_time = window_laps["LapTimeSeconds"].min()
            best_per_window.append({
                "WindowStart": window_start,
                "WindowMid": window_start + TRACK_EVOLUTION_WINDOW_MINUTES / 2,
                "BestTime": best_time,
                "LapCount": len(window_laps),
            })
    
    evolution_df = pd.DataFrame(best_per_window)
    
    if len(evolution_df) >= 3:
        x = evolution_df["WindowMid"].values
        y = evolution_df["BestTime"].values
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        if abs(slope) > 0.05:
            slope = 0.05 if slope > 0 else -0.05
        
        evolution_df["FittedTime"] = intercept + slope * evolution_df["WindowMid"]
        evolution_df["EvolutionRate"] = slope
        evolution_df["RSquared"] = r_value ** 2
    else:
        evolution_df["FittedTime"] = evolution_df["BestTime"] if not evolution_df.empty else []
        evolution_df["EvolutionRate"] = 0
        evolution_df["RSquared"] = 0
    
    return evolution_df


def add_track_evolution_correction(laps: pd.DataFrame, evolution_model: pd.DataFrame) -> pd.DataFrame:
    laps = laps.copy()
    
    if evolution_model.empty or "EvolutionRate" not in evolution_model.columns:
        laps["TrackEvolutionCorrection"] = 0
        laps["EvolutionCorrectedTime"] = laps["LapTimeSeconds"]
        return laps
    
    first_lap_time = laps["LapStartTime"].min()
    laps["SessionMinute"] = (laps["LapStartTime"] - first_lap_time).dt.total_seconds() / 60
    
    evolution_rate = evolution_model["EvolutionRate"].iloc[0]
    session_midpoint = evolution_model["WindowMid"].median()
    
    laps["TrackEvolutionCorrection"] = (
        (laps["SessionMinute"] - session_midpoint) * evolution_rate * -1
    )
    laps["EvolutionCorrectedTime"] = laps["LapTimeSeconds"] + laps["TrackEvolutionCorrection"]
    
    return laps


def calculate_empirical_degradation(laps: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    laps = laps.copy()
    
    if "TyreLap" not in laps.columns:
        laps = add_stint_info(laps)
    
    laps = add_fuel_corrected_times(laps)
    
    deg_by_compound = {}
    
    for compound in laps["Compound"].unique():
        compound_laps = laps[laps["Compound"] == compound]
        stint_slopes = []
        
        for driver in compound_laps["Driver"].unique():
            driver_compound = compound_laps[compound_laps["Driver"] == driver]
            
            for stint in driver_compound["StintNumber"].unique():
                stint_laps = driver_compound[driver_compound["StintNumber"] == stint]
                stint_laps = stint_laps.sort_values("TyreLap")
                
                if len(stint_laps) < MIN_LAPS_FOR_DEGRADATION:
                    continue
                
                x = stint_laps["TyreLap"].values
                y = stint_laps["FuelCorrectedTime"].values
                
                slope, _ = np.polyfit(x, y, 1)
                
                if 0 < slope < 0.3:
                    stint_slopes.append(slope)
        
        if stint_slopes:
            deg_by_compound[compound] = {
                "median": np.median(stint_slopes),
                "mean": np.mean(stint_slopes),
                "std": np.std(stint_slopes),
                "n_stints": len(stint_slopes),
            }
        else:
            deg_by_compound[compound] = {
                "median": TIRE_DEGRADATION_ESTIMATES.get(compound, 0.05),
                "mean": TIRE_DEGRADATION_ESTIMATES.get(compound, 0.05),
                "std": 0,
                "n_stints": 0,
            }
    
    return deg_by_compound


def add_tyre_age_correction(
    laps: pd.DataFrame,
    empirical_deg: Optional[Dict[str, Dict[str, float]]] = None,
) -> pd.DataFrame:
    laps = laps.copy()
    
    if "TyreLap" not in laps.columns:
        laps = add_stint_info(laps)
    
    if empirical_deg is None:
        empirical_deg = calculate_empirical_degradation(laps)
    
    median_tyre_lap = laps["TyreLap"].median()
    
    def calc_tyre_correction(row):
        compound = row["Compound"]
        tyre_lap = row["TyreLap"]
        
        if compound in empirical_deg:
            deg_rate = empirical_deg[compound]["median"]
        else:
            deg_rate = TIRE_DEGRADATION_ESTIMATES.get(compound, 0.05)
        
        return (tyre_lap - median_tyre_lap) * deg_rate * -1
    
    laps["TyreAgeCorrection"] = laps.apply(calc_tyre_correction, axis=1)
    laps["TyreCorrectedTime"] = laps["LapTimeSeconds"] + laps["TyreAgeCorrection"]
    
    return laps


def add_fully_corrected_times(
    laps: pd.DataFrame,
    evolution_model: pd.DataFrame,
    empirical_deg: Optional[Dict[str, Dict[str, float]]] = None,
) -> pd.DataFrame:
    laps = add_stint_info(laps)
    laps = add_fuel_corrected_times(laps)
    laps = add_track_evolution_correction(laps, evolution_model)
    
    if empirical_deg is None:
        empirical_deg = calculate_empirical_degradation(laps)
    
    laps = add_tyre_age_correction(laps, empirical_deg)
    
    laps["FullyCorrectedTime"] = (
        laps["LapTimeSeconds"] +
        laps["FuelCorrection"] +
        laps["TrackEvolutionCorrection"] +
        laps["TyreAgeCorrection"]
    )
    
    return laps


def filter_representative_laps(laps: pd.DataFrame) -> pd.DataFrame:
    laps = laps.copy()
    best_time = laps["LapTimeSeconds"].min()
    threshold = best_time * (OUTLIER_THRESHOLD_PERCENT / 100)
    return laps[laps["LapTimeSeconds"] <= threshold]


def calculate_compound_matched_pace(
    fp1_session,
    fp2_session,
    fp1_evolution: pd.DataFrame,
    fp2_evolution: pd.DataFrame,
) -> pd.DataFrame:
    fp1_laps = get_lap_data(fp1_session)
    fp1_laps = add_stint_info(fp1_laps)
    fp1_laps = add_fuel_corrected_times(fp1_laps)
    fp1_laps = filter_representative_laps(fp1_laps)
    
    fp2_laps = get_lap_data(fp2_session)
    fp2_laps = add_stint_info(fp2_laps)
    fp2_laps = add_fuel_corrected_times(fp2_laps)
    fp2_laps = filter_representative_laps(fp2_laps)
    
    results = []
    
    for regular, rookie in DRIVER_ROOKIE_MAPPING.items():
        rookie_laps = fp1_laps[fp1_laps["Driver"] == rookie]
        regular_laps = fp2_laps[fp2_laps["Driver"] == regular]
        
        if rookie_laps.empty or regular_laps.empty:
            continue
        
        common_compounds = set(rookie_laps["Compound"].unique()) & set(regular_laps["Compound"].unique())
        
        for compound in common_compounds:
            rook_compound = rookie_laps[rookie_laps["Compound"] == compound]
            reg_compound = regular_laps[regular_laps["Compound"] == compound]
            
            if rook_compound.empty or reg_compound.empty:
                continue
            
            reg_best_raw = reg_compound["LapTimeSeconds"].min()
            rook_best_raw = rook_compound["LapTimeSeconds"].min()
            raw_deficit = rook_best_raw - reg_best_raw
            
            reg_best_fuel_corrected = reg_compound["FuelCorrectedTime"].min()
            rook_best_fuel_corrected = rook_compound["FuelCorrectedTime"].min()
            corrected_deficit = rook_best_fuel_corrected - reg_best_fuel_corrected
            
            results.append({
                "Regular": regular,
                "RegularName": REGULAR_FULL_NAMES.get(regular, regular),
                "Rookie": rookie,
                "RookieName": ROOKIE_FULL_NAMES.get(rookie, rookie),
                "Team": TEAM_MAPPING.get(rookie, "Unknown"),
                "Compound": compound,
                "RegularBestRaw": reg_best_raw,
                "RookieBestRaw": rook_best_raw,
                "RawDeficit": raw_deficit,
                "RegularBestCorrected": reg_best_fuel_corrected,
                "RookieBestCorrected": rook_best_fuel_corrected,
                "CorrectedDeficit": corrected_deficit,
                "RegularLapCount": len(reg_compound),
                "RookieLapCount": len(rook_compound),
            })
    
    return pd.DataFrame(results)


def calculate_aggregate_pace_deficit(compound_pace_df: pd.DataFrame) -> pd.DataFrame:
    if compound_pace_df.empty:
        return pd.DataFrame()
    
    aggregated = compound_pace_df.groupby(["Regular", "Rookie", "Team"]).agg(
        RegularName=("RegularName", "first"),
        RookieName=("RookieName", "first"),
        AvgRawDeficit=("RawDeficit", "mean"),
        AvgCorrectedDeficit=("CorrectedDeficit", "mean"),
        BestRawDeficit=("RawDeficit", "min"),
        BestCorrectedDeficit=("CorrectedDeficit", "min"),
        CompoundsCompared=("Compound", "count"),
        TotalRegularLaps=("RegularLapCount", "sum"),
        TotalRookieLaps=("RookieLapCount", "sum"),
    ).reset_index()
    
    overall_best_regular = compound_pace_df.groupby("Regular")["RegularBestRaw"].min()
    aggregated["RegularOverallBest"] = aggregated["Regular"].map(overall_best_regular)
    aggregated["DeficitPercent"] = (
        aggregated["AvgCorrectedDeficit"] / aggregated["RegularOverallBest"]
    ) * 100
    
    return aggregated


def calculate_stint_analysis(session, evolution_model: pd.DataFrame) -> pd.DataFrame:
    laps = get_lap_data(session)
    laps = add_fully_corrected_times(laps, evolution_model)
    laps = filter_representative_laps(laps)
    
    stint_stats = laps.groupby(["Driver", "StintNumber", "Compound"]).agg(
        LapCount=("LapTime", "count"),
        TotalStintLaps=("TyreLap", "max"),
        BestLapRaw=("LapTimeSeconds", "min"),
        BestLapCorrected=("FullyCorrectedTime", "min"),
        AvgLapRaw=("LapTimeSeconds", "mean"),
        AvgLapCorrected=("FullyCorrectedTime", "mean"),
        StdLap=("LapTimeSeconds", "std"),
        FirstLapNumber=("LapNumber", "min"),
        LastLapNumber=("LapNumber", "max"),
    ).reset_index()
    
    stint_stats["IsRookie"] = stint_stats["Driver"].isin(ROOKIE_DRIVERS)
    stint_stats["DriverName"] = stint_stats["Driver"].apply(
        lambda x: ALL_DRIVER_NAMES.get(x, x)
    )
    stint_stats["Team"] = stint_stats["Driver"].map(TEAM_MAPPING)
    
    return stint_stats


def calculate_stint_pace_trend(
    fp1_session,
    fp2_session,
    fp1_evolution: pd.DataFrame,
    fp2_evolution: pd.DataFrame,
) -> pd.DataFrame:
    fp1_laps = get_lap_data(fp1_session)
    fp1_laps = add_stint_info(fp1_laps)
    fp1_laps = add_fuel_corrected_times(fp1_laps)
    fp1_laps = filter_representative_laps(fp1_laps)
    fp1_laps["Session"] = "FP1"
    
    fp2_laps = get_lap_data(fp2_session)
    fp2_laps = add_stint_info(fp2_laps)
    fp2_laps = add_fuel_corrected_times(fp2_laps)
    fp2_laps = filter_representative_laps(fp2_laps)
    fp2_laps["Session"] = "FP2"
    
    all_laps = pd.concat([fp1_laps, fp2_laps], ignore_index=True)
    
    results = []
    
    for driver in all_laps["Driver"].unique():
        driver_laps = all_laps[all_laps["Driver"] == driver]
        
        for stint in driver_laps["StintNumber"].unique():
            stint_laps = driver_laps[driver_laps["StintNumber"] == stint].sort_values("TyreLap")
            
            if len(stint_laps) < MIN_LAPS_FOR_DEGRADATION:
                continue
            
            compound = stint_laps["Compound"].iloc[0]
            session = stint_laps["Session"].iloc[0]
            
            x = stint_laps["TyreLap"].values
            y_raw = stint_laps["LapTimeSeconds"].values
            y_fuel_corrected = stint_laps["FuelCorrectedTime"].values
            
            if len(x) >= 2:
                slope_raw, intercept_raw = np.polyfit(x, y_raw, 1)
                slope_fuel_corrected, intercept_fuel_corrected = np.polyfit(x, y_fuel_corrected, 1)
                
                y_pred = intercept_raw + slope_raw * x
                ss_res = np.sum((y_raw - y_pred) ** 2)
                ss_tot = np.sum((y_raw - np.mean(y_raw)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                is_rookie = driver in ROOKIE_DRIVERS
                name = ALL_DRIVER_NAMES.get(driver, driver)
                
                results.append({
                    "Driver": driver,
                    "DriverName": name,
                    "Team": TEAM_MAPPING.get(driver, "Unknown"),
                    "IsRookie": is_rookie,
                    "Session": session,
                    "StintNumber": stint,
                    "Compound": compound,
                    "LapCount": len(stint_laps),
                    "RawTrend": slope_raw,
                    "FuelCorrectedTrend": slope_fuel_corrected,
                    "InitialPace": intercept_raw,
                    "RSquared": r_squared,
                })
    
    return pd.DataFrame(results)


def calculate_tyre_management_score(stint_trend_df: pd.DataFrame) -> pd.DataFrame:
    if stint_trend_df.empty:
        return pd.DataFrame()
    
    results = []
    
    for compound in stint_trend_df["Compound"].unique():
        compound_data = stint_trend_df[stint_trend_df["Compound"] == compound]
        
        if compound_data.empty:
            continue
        
        median_trend = compound_data["FuelCorrectedTrend"].median()
        
        for _, row in compound_data.iterrows():
            trend_vs_median = row["FuelCorrectedTrend"] - median_trend
            trend_percentile = stats.percentileofscore(
                compound_data["FuelCorrectedTrend"].values,
                row["FuelCorrectedTrend"]
            )
            tyre_score = 100 - trend_percentile
            
            results.append({
                "Driver": row["Driver"],
                "DriverName": row["DriverName"],
                "Team": row["Team"],
                "IsRookie": row["IsRookie"],
                "Compound": compound,
                "FuelCorrectedTrend": row["FuelCorrectedTrend"],
                "MedianTrend": median_trend,
                "TrendVsMedian": trend_vs_median,
                "TyreManagementScore": tyre_score,
            })
    
    return pd.DataFrame(results)


def calculate_long_run_pace(
    fp1_session,
    fp2_session,
    fp1_evolution: pd.DataFrame,
    fp2_evolution: pd.DataFrame,
    min_stint_length: int = 6,
) -> pd.DataFrame:
    fp1_laps = get_lap_data(fp1_session)
    fp1_laps = add_fully_corrected_times(fp1_laps, fp1_evolution)
    fp1_laps = filter_representative_laps(fp1_laps)
    
    fp2_laps = get_lap_data(fp2_session)
    fp2_laps = add_fully_corrected_times(fp2_laps, fp2_evolution)
    fp2_laps = filter_representative_laps(fp2_laps)
    
    all_laps = pd.concat([fp1_laps, fp2_laps], ignore_index=True)
    
    results = []
    
    for driver in all_laps["Driver"].unique():
        driver_laps = all_laps[all_laps["Driver"] == driver]
        
        for stint in driver_laps["StintNumber"].unique():
            stint_laps = driver_laps[driver_laps["StintNumber"] == stint]
            
            if len(stint_laps) < min_stint_length:
                continue
            
            compound = stint_laps["Compound"].iloc[0]
            is_rookie = driver in ROOKIE_DRIVERS
            name = ALL_DRIVER_NAMES.get(driver, driver)
            
            results.append({
                "Driver": driver,
                "DriverName": name,
                "Team": TEAM_MAPPING.get(driver, "Unknown"),
                "IsRookie": is_rookie,
                "StintNumber": stint,
                "Compound": compound,
                "StintLength": len(stint_laps),
                "AvgPaceRaw": stint_laps["LapTimeSeconds"].mean(),
                "AvgPaceCorrected": stint_laps["FullyCorrectedTime"].mean(),
                "BestLap": stint_laps["LapTimeSeconds"].min(),
                "Consistency": stint_laps["LapTimeSeconds"].std(),
            })
    
    return pd.DataFrame(results)


def compare_long_run_pace(long_run_df: pd.DataFrame) -> pd.DataFrame:
    if long_run_df.empty:
        return pd.DataFrame()
    
    results = []
    
    for regular, rookie in DRIVER_ROOKIE_MAPPING.items():
        reg_runs = long_run_df[long_run_df["Driver"] == regular]
        rook_runs = long_run_df[long_run_df["Driver"] == rookie]
        
        if reg_runs.empty or rook_runs.empty:
            continue
        
        common_compounds = set(reg_runs["Compound"].unique()) & set(rook_runs["Compound"].unique())
        
        for compound in common_compounds:
            reg_compound = reg_runs[reg_runs["Compound"] == compound]
            rook_compound = rook_runs[rook_runs["Compound"] == compound]
            
            if reg_compound.empty or rook_compound.empty:
                continue
            
            reg_avg = reg_compound["AvgPaceCorrected"].mean()
            rook_avg = rook_compound["AvgPaceCorrected"].mean()
            
            results.append({
                "Regular": regular,
                "RegularName": REGULAR_FULL_NAMES.get(regular, regular),
                "Rookie": rookie,
                "RookieName": ROOKIE_FULL_NAMES.get(rookie, rookie),
                "Team": TEAM_MAPPING.get(rookie, "Unknown"),
                "Compound": compound,
                "RegularLongRunPace": reg_avg,
                "RookieLongRunPace": rook_avg,
                "LongRunDeficit": rook_avg - reg_avg,
                "RegularConsistency": reg_compound["Consistency"].mean(),
                "RookieConsistency": rook_compound["Consistency"].mean(),
            })
    
    return pd.DataFrame(results)


def calculate_advanced_sector_analysis(
    fp1_session,
    fp2_session,
    fp1_evolution: pd.DataFrame,
    fp2_evolution: pd.DataFrame,
) -> pd.DataFrame:
    fp1_laps = get_lap_data(fp1_session)
    fp1_laps = add_stint_info(fp1_laps)
    fp1_laps = add_fuel_corrected_times(fp1_laps)
    fp1_laps = filter_representative_laps(fp1_laps)
    
    fp2_laps = get_lap_data(fp2_session)
    fp2_laps = add_stint_info(fp2_laps)
    fp2_laps = add_fuel_corrected_times(fp2_laps)
    fp2_laps = filter_representative_laps(fp2_laps)
    
    results = []
    
    for regular, rookie in DRIVER_ROOKIE_MAPPING.items():
        rookie_laps = fp1_laps[fp1_laps["Driver"] == rookie]
        regular_laps = fp2_laps[fp2_laps["Driver"] == regular]
        
        if rookie_laps.empty or regular_laps.empty:
            continue
        
        common_compounds = set(rookie_laps["Compound"].unique()) & set(regular_laps["Compound"].unique())
        
        for compound in common_compounds:
            rook_compound = rookie_laps[rookie_laps["Compound"] == compound]
            reg_compound = regular_laps[regular_laps["Compound"] == compound]
            
            for sector in [1, 2, 3]:
                sector_col = f"Sector{sector}Seconds"
                
                reg_best = reg_compound[sector_col].min()
                rook_best = rook_compound[sector_col].min()
                deficit = rook_best - reg_best
                
                reg_avg = reg_compound[sector_col].mean()
                rook_avg = rook_compound[sector_col].mean()
                avg_deficit = rook_avg - reg_avg
                
                results.append({
                    "Regular": regular,
                    "Rookie": rookie,
                    "RookieName": ROOKIE_FULL_NAMES.get(rookie, rookie),
                    "Team": TEAM_MAPPING.get(rookie, "Unknown"),
                    "Compound": compound,
                    "Sector": sector,
                    "RegularBest": reg_best,
                    "RookieBest": rook_best,
                    "BestDeficit": deficit,
                    "RegularAvg": reg_avg,
                    "RookieAvg": rook_avg,
                    "AvgDeficit": avg_deficit,
                })
    
    return pd.DataFrame(results)


def generate_advanced_summary(
    compound_pace_df: pd.DataFrame,
    aggregate_pace_df: pd.DataFrame,
    stint_trend_df: pd.DataFrame,
    long_run_comparison: pd.DataFrame,
) -> Dict:
    summary = {
        "total_rookies": len(ROOKIE_DRIVERS),
        "rookies_with_data": 0,
        "compounds_analyzed": [],
        "avg_raw_deficit": None,
        "avg_corrected_deficit": None,
        "best_rookie": None,
        "best_corrected_deficit": None,
        "avg_rookie_trend": None,
        "avg_regular_trend": None,
        "best_tyre_manager_rookie": None,
    }
    
    if not aggregate_pace_df.empty:
        summary["rookies_with_data"] = len(aggregate_pace_df)
        summary["avg_raw_deficit"] = aggregate_pace_df["AvgRawDeficit"].mean()
        summary["avg_corrected_deficit"] = aggregate_pace_df["AvgCorrectedDeficit"].mean()
        
        best_idx = aggregate_pace_df["AvgCorrectedDeficit"].idxmin()
        summary["best_rookie"] = aggregate_pace_df.loc[best_idx, "RookieName"]
        summary["best_corrected_deficit"] = aggregate_pace_df.loc[best_idx, "AvgCorrectedDeficit"]
    
    if not compound_pace_df.empty:
        summary["compounds_analyzed"] = compound_pace_df["Compound"].unique().tolist()
    
    if not stint_trend_df.empty:
        rookie_trends = stint_trend_df[stint_trend_df["IsRookie"] == True]
        regular_trends = stint_trend_df[stint_trend_df["IsRookie"] == False]
        
        if not rookie_trends.empty:
            summary["avg_rookie_trend"] = rookie_trends["FuelCorrectedTrend"].mean()
        if not regular_trends.empty:
            summary["avg_regular_trend"] = regular_trends["FuelCorrectedTrend"].mean()
        
        if not rookie_trends.empty:
            best_trend_idx = rookie_trends["FuelCorrectedTrend"].idxmin()
            summary["best_tyre_manager_rookie"] = rookie_trends.loc[best_trend_idx, "DriverName"]
    
    return summary