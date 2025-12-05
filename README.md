# F1 Rookie FP1 Performance Analysis

Analysis of rookie driver performance during mandatory FP1 rookie running session at the 2025 Abu Dhabi Grand Prix, comparing against regular drivers with fuel-corrected lap times.

## Overview

Formula 1 regulations require teams to run rookie drivers during at least two FP1 sessions per season. This project analyzes rookie performance by comparing their FP1 lap times against regular drivers' FP2 times on matching tyre compounds.

## Methodology

### Corrections Applied

| Factor | Method | Source |
|--------|--------|--------|
| Fuel load | 0.035 s/kg effect, 1.5 kg/lap consumption | FIA technical data |
| Tyre compound | Only compare laps on matching compounds | — |

Track evolution and tyre degradation corrections are not applied to cross-session comparisons since FP1 and FP2 have independent track states.

### Stint Trend Analysis

For within-session analysis, the tool calculates lap time trends over each stint after fuel correction. At low-degradation circuits like Abu Dhabi, negative trends (lap times getting faster) are expected as track evolution exceeds tyre wear.

## Usage

```bash
pip install -r requirements.txt
python discover_drivers.py   # Run after FP1 to verify driver codes
python main_advanced.py      # Run after FP2 completes
```

FastF1 data is typically available 2-3 hours after session end.

## Output

Results are saved to `output/`:

| File | Contents |
|------|----------|
| `compound_matched_pace.csv` | Rookie vs regular driver pace by compound |
| `aggregate_pace_deficit.csv` | Overall rookie ranking |
| `stint_pace_trends.csv` | Lap time trends per stint |
| `tyre_management_scores.csv` | Relative tyre management ranking |
| `sector_analysis.csv` | Sector-by-sector deficits |
| `rookie_analysis_report.md` | Full markdown report |
| `*.png` | Visualizations |

## Configuration

Edit `config.py` to modify driver mappings or parameters:

| Parameter | Default | Notes |
|-----------|---------|-------|
| `DRIVER_ROOKIE_MAPPING` | — | Maps regular driver to their rookie replacement |
| `FUEL_EFFECT_PER_KG` | 0.035 | Seconds per kg (0.03-0.04 typical) |
| `FUEL_CONSUMPTION_KG_PER_LAP` | 1.5 | Circuit-dependent (1.4-2.2 range) |
| `MIN_LAPS_FOR_DEGRADATION` | 4 | Minimum stint length for trend calculation |
| `OUTLIER_THRESHOLD_PERCENT` | 107 | Exclude laps slower than 107% of best |

## Limitations

- **Cross-session comparison**: Rookies (FP1) vs regulars (FP2) means different track conditions, temperatures, and grip levels
- **Fuel loads estimated**: Actual team fuel loads are unknown; assumes uniform 80kg start
- **Run programs vary**: Teams may run different programs (quali sims vs race runs) affecting comparability
- **Engine modes not visible**: Power unit settings are not available in public data

## Project Structure

```
├── config.py                 # Driver mappings, parameters
├── data_collector.py         # FastF1 data loading
├── advanced_analysis.py      # Pace, stint, sector analysis
├── advanced_visualizations.py # Chart generation
├── advanced_report.py        # Markdown report generation
├── main_advanced.py          # Main execution script
├── discover_drivers.py       # Driver code verification
└── requirements.txt          # Dependencies
```

## Requirements

- Python 3.10+
- FastF1 3.3+
- pandas, numpy, matplotlib, seaborn, scipy
