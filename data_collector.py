import fastf1
import pandas as pd
from pathlib import Path

from config import YEAR, GP_NAME, SESSIONS, CACHE_DIR


def setup_cache():
    cache_path = Path(CACHE_DIR)
    cache_path.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_path))


def load_session(session_name: str) -> fastf1.core.Session:
    session = fastf1.get_session(YEAR, GP_NAME, session_name)
    session.load()
    return session


def load_all_sessions() -> dict:
    setup_cache()
    sessions = {}
    for session_name in SESSIONS:
        sessions[session_name] = load_session(session_name)
    return sessions


def get_lap_data(session: fastf1.core.Session) -> pd.DataFrame:
    laps = session.laps.copy()
    laps = laps[laps["PitOutTime"].isna() & laps["PitInTime"].isna()]
    laps = laps[~laps["LapTime"].isna()]
    laps = laps[laps["IsAccurate"] == True]
    laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()
    laps["Sector1Seconds"] = laps["Sector1Time"].dt.total_seconds()
    laps["Sector2Seconds"] = laps["Sector2Time"].dt.total_seconds()
    laps["Sector3Seconds"] = laps["Sector3Time"].dt.total_seconds()
    return laps


def get_telemetry_for_lap(lap) -> pd.DataFrame:
    try:
        telemetry = lap.get_telemetry()
        return telemetry
    except Exception:
        return pd.DataFrame()


def get_best_lap_telemetry(session: fastf1.core.Session, driver: str) -> pd.DataFrame:
    laps = get_lap_data(session)
    driver_laps = laps[laps["Driver"] == driver]
    if driver_laps.empty:
        return pd.DataFrame()
    best_lap = driver_laps.loc[driver_laps["LapTimeSeconds"].idxmin()]
    return get_telemetry_for_lap(best_lap)