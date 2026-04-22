import os
import json

MEMORY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "assets", "memory"))
GUIDELINES_FILE = os.path.join(MEMORY_DIR, "core_guidelines.json")

def load_long_term_memory() -> list:
    if os.path.exists(GUIDELINES_FILE):
        with open(GUIDELINES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_long_term_memory(guidelines: list):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(GUIDELINES_FILE, "w", encoding="utf-8") as f:
        json.dump(guidelines, f, indent=4, ensure_ascii=False)