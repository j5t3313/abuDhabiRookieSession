YEAR = 2025
GP_NAME = "Abu Dhabi"
SESSIONS = ["FP1", "FP2"]

DRIVER_ROOKIE_MAPPING = {
    "PIA": "OWA",
    "TSU": "LIN",
    "HAM": "ALE",
    "ALB": "BRO",
    "LAW": "IWA",
    "ALO": "SHI",
    "STR": "CRA",
    "OCO": "HIR",
    "GAS": "ARO",
}

ROOKIE_DRIVERS = ["OWA", "LIN", "ALE", "BRO", "IWA", "SHI", "CRA", "HIR", "ARO"]

REGULAR_DRIVERS = list(DRIVER_ROOKIE_MAPPING.keys())

ROOKIE_FULL_NAMES = {
    "OWA": "Pato O'Ward",
    "LIN": "Arvid Lindblad",
    "ALE": "Arthur Leclerc",
    "BRO": "Luke Browning",
    "IWA": "Ayumu Iwasa",
    "SHI": "Cian Shields",
    "CRA": "Jak Crawford",
    "HIR": "Ryo Hirakawa",
    "ARO": "Paul Aron",
}

REGULAR_FULL_NAMES = {
    "PIA": "Oscar Piastri",
    "TSU": "Yuki Tsunoda",
    "HAM": "Lewis Hamilton",
    "ALB": "Alex Albon",
    "LAW": "Liam Lawson",
    "ALO": "Fernando Alonso",
    "STR": "Lance Stroll",
    "OCO": "Esteban Ocon",
    "GAS": "Pierre Gasly",
}

ALL_DRIVER_NAMES = {
    "VER": "Max Verstappen",
    "NOR": "Lando Norris",
    "LEC": "Charles Leclerc",
    "SAI": "Carlos Sainz",
    "RUS": "George Russell",
    "HAM": "Lewis Hamilton",
    "PIA": "Oscar Piastri",
    "ALO": "Fernando Alonso",
    "STR": "Lance Stroll",
    "GAS": "Pierre Gasly",
    "OCO": "Esteban Ocon",
    "ALB": "Alex Albon",
    "COL": "Franco Colapinto",
    "TSU": "Yuki Tsunoda",
    "LAW": "Liam Lawson",
    "HUL": "Nico Hulkenberg",
    "BEA": "Oliver Bearman",
    "BOT": "Valtteri Bottas",
    "ZHO": "Guanyu Zhou",
    "MAG": "Kevin Magnussen",
    "BOR": "Gabriel Bortoleto",
    "HAD": "Isack Hadjar",
    "DOO": "Jack Doohan",
    "ANT": "Kimi Antonelli",
    "LEL": "Arthur Leclerc",
    "OWA": "Pato O'Ward",
    "LIN": "Arvid Lindblad",
    "ALE": "Arthur Leclerc",
    "BRO": "Luke Browning",
    "IWA": "Ayumu Iwasa",
    "SHI": "Cian Shields",
    "CRA": "Jak Crawford",
    "HIR": "Ryo Hirakawa",
    "ARO": "Paul Aron",
}

TEAM_MAPPING = {
    "VER": "Red Bull",
    "LAW": "Red Bull",
    "NOR": "McLaren",
    "PIA": "McLaren",
    "OWA": "McLaren",
    "LEC": "Ferrari",
    "HAM": "Ferrari",
    "ALE": "Ferrari",
    "LEL": "Ferrari",
    "RUS": "Mercedes",
    "ANT": "Mercedes",
    "ALO": "Aston Martin",
    "STR": "Aston Martin",
    "SHI": "Aston Martin",
    "CRA": "Aston Martin",
    "GAS": "Alpine",
    "DOO": "Alpine",
    "ARO": "Alpine",
    "ALB": "Williams",
    "SAI": "Williams",
    "BRO": "Williams",
    "COL": "Williams",
    "TSU": "RB",
    "HAD": "RB",
    "LIN": "RB",
    "IWA": "RB",
    "HUL": "Sauber",
    "BOR": "Sauber",
    "OCO": "Haas",
    "BEA": "Haas",
    "HIR": "Haas",
}

TEAM_COLORS = {
    "Red Bull": "#3671C6",
    "McLaren": "#FF8000",
    "Ferrari": "#E8002D",
    "Mercedes": "#27F4D2",
    "Aston Martin": "#229971",
    "Alpine": "#0093CC",
    "Williams": "#64C4FF",
    "RB": "#6692FF",
    "Sauber": "#52E252",
    "Haas": "#B6BABD",
}

CACHE_DIR = "fastf1_cache"
OUTPUT_DIR = "output"

FUEL_EFFECT_PER_KG = 0.035
FUEL_CONSUMPTION_KG_PER_LAP = 1.5
ESTIMATED_START_FUEL_KG = 80

TIRE_DEGRADATION_ESTIMATES = {
    "SOFT": 0.08,
    "MEDIUM": 0.05,
    "HARD": 0.03,
    "INTERMEDIATE": 0.10,
    "WET": 0.12,
}

MIN_LAPS_FOR_DEGRADATION = 4
TRACK_EVOLUTION_WINDOW_MINUTES = 5
OUTLIER_THRESHOLD_PERCENT = 107