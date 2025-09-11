import os
import json
from typing import Any

DATA_DIR = "data"

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filename: str, default: Any):
    """
    Safe JSON loader. Returns `default` if file doesn't exist or parsing fails.
    """
    _ensure_dir()
    path = filename if filename.startswith(DATA_DIR) else os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(filename: str, data: Any):
    """
    Safe JSON writer. Ensures directory exists and writes atomically.
    """
    _ensure_dir()
    path = filename if filename.startswith(DATA_DIR) else os.path.join(DATA_DIR, filename)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return True
