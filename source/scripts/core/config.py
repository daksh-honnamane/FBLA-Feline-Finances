import sys
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = CORE_DIR.parent.parent

if getattr(sys, "frozen", False):
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    SAVE_ROOT = Path(sys.executable).resolve().parent
else:
    RESOURCE_ROOT = SOURCE_DIR
    SAVE_ROOT = SOURCE_DIR

ASSET_DIR = RESOURCE_ROOT / "assets"
SAVE_FILE = SAVE_ROOT / "save_data.json"

WIDTH, HEIGHT = 900, 600
CAPTION = "Feline Finances"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
COZY = (249, 230, 197)
BUTTON = (155, 182, 130)
BUTTON_HOVER = (135, 162, 110)
PANEL = (255, 248, 236)
RED = (212, 95, 95)
GOLD = (216, 180, 78)
BLUE = (122, 180, 224)

AUTOSAVE_INTERVAL = 10000
TIME_STEP_MS = 5000
CAT_TYPES = ["Orange", "Grey", "White", "Calico"]
PERSONALITIES = ["Playful", "Lazy", "Shy", "Energetic"]
STAT_NAMES = ("hunger", "happiness", "energy", "cleanliness", "health")

STORE_ITEMS = [
    {"name": "Meowmunch", "price": 5, "category": "Food", "description": "Crunchy food that restores hunger."},
    {"name": "Purrplay", "price": 10, "category": "Toys", "description": "A toy set that boosts happiness."},
    {"name": "Furbath", "price": 15, "category": "Grooming", "description": "Bath supplies for cleanliness."},
]
ITEM_DETAILS = {item["name"]: item for item in STORE_ITEMS}

VET_COST = 25
VET_HEAL = 35
SAVE_GOAL = 100


def asset_path(*parts: str) -> str:
    return str(ASSET_DIR.joinpath(*parts))