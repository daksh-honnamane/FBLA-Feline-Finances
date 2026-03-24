import json
import os

from core.config import CAT_TYPES, PERSONALITIES, SAVE_FILE, STORE_ITEMS
from core.models import Cat
from core.utils import clamp


def create_default_progress():
    return {
        "money": 50,
        "total_spent": 0,
        "total_earned": 0,
        "inventory": {item["name"]: 0 for item in STORE_ITEMS},
        "expense_breakdown": {"Food": 0, "Toys": 0, "Grooming": 0, "Vet": 0},
        "vet_visits": 0,
        "care_actions": 0,
        "chores_completed": 0,
        "achievements": [],
        "last_status": "Welcome to Feline Finances!",
    }


def sanitize_inventory(raw_inventory):
    inventory = {item["name"]: 0 for item in STORE_ITEMS}
    if not isinstance(raw_inventory, dict):
        return inventory
    for item_name in inventory:
        value = raw_inventory.get(item_name, 0)
        inventory[item_name] = max(0, int(value)) if isinstance(value, (int, float)) else 0
    return inventory


def sanitize_expenses(raw_expenses):
    categories = {"Food": 0, "Toys": 0, "Grooming": 0, "Vet": 0}
    if not isinstance(raw_expenses, dict):
        return categories
    for category in categories:
        value = raw_expenses.get(category, 0)
        categories[category] = max(0, int(value)) if isinstance(value, (int, float)) else 0
    return categories


def sanitize_save_data(raw_data):
    if not isinstance(raw_data, dict):
        return None

    name = raw_data.get("name")
    cat_type = raw_data.get("type")
    personality = raw_data.get("personality")
    stats = raw_data.get("stats")

    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 10:
        return None
    if cat_type not in CAT_TYPES or personality not in PERSONALITIES:
        return None
    if not isinstance(stats, dict):
        return None

    cat = Cat(name.strip(), cat_type, personality)
    for stat_name in ("hunger", "happiness", "energy", "cleanliness", "health"):
        stat_value = stats.get(stat_name, getattr(cat, stat_name))
        if not isinstance(stat_value, (int, float)):
            return None
        setattr(cat, stat_name, clamp(int(stat_value)))

    age_days = stats.get("age_days", 1)
    cat.age_days = max(1, int(age_days)) if isinstance(age_days, (int, float)) else 1

    progress = create_default_progress()
    for key in ("money", "total_spent", "total_earned", "vet_visits", "care_actions", "chores_completed"):
        value = raw_data.get(key, progress[key])
        progress[key] = max(0, int(value)) if isinstance(value, (int, float)) else progress[key]

    progress["inventory"] = sanitize_inventory(raw_data.get("inventory", {}))
    progress["expense_breakdown"] = sanitize_expenses(raw_data.get("expense_breakdown", {}))

    achievements = raw_data.get("achievements", [])
    if isinstance(achievements, list):
        progress["achievements"] = [str(entry) for entry in achievements[:10]]

    last_status = raw_data.get("last_status", progress["last_status"])
    if isinstance(last_status, str):
        progress["last_status"] = last_status[:120]

    return cat, progress


def save_game(cat, progress):
    data = cat.as_dict()
    data.update(progress)
    with open(SAVE_FILE, "w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=4)


def load_game():
    if not os.path.exists(SAVE_FILE):
        return None
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file_handle:
            raw_data = json.load(file_handle)
    except (json.JSONDecodeError, OSError):
        return None
    return sanitize_save_data(raw_data)


def reset_save_file():
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)