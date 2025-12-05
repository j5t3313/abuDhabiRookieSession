import fastf1
from pathlib import Path

from config import CACHE_DIR, YEAR, GP_NAME


def setup_cache():
    cache_path = Path(CACHE_DIR)
    cache_path.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_path))


def discover_driver_codes(session_name: str = "FP1"):
    setup_cache()
    
    session = fastf1.get_session(YEAR, GP_NAME, session_name)
    session.load()
    
    print(f"\n{YEAR} {GP_NAME} GP - {session_name}")
    print("=" * 50)
    print(f"\n{'Code':<8} {'Number':<8} {'Full Name':<25} {'Team'}")
    print("-" * 60)
    
    for driver_num in session.drivers:
        driver_info = session.get_driver(driver_num)
        code = driver_info.get("Abbreviation", "???")
        full_name = driver_info.get("FullName", "Unknown")
        team = driver_info.get("TeamName", "Unknown")
        print(f"{code:<8} {driver_num:<8} {full_name:<25} {team}")


if __name__ == "__main__":
    discover_driver_codes("FP1")