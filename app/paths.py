"""Risoluzione dei percorsi (sviluppo vs eseguibile PyInstaller)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from . import APP_NAME

# Modelli disponibili: chiave UI -> (nome faster-whisper, cartella locale)
MODELS = {
    "medium": "faster-whisper-medium",
    "small": "faster-whisper-small",
}
BUNDLED_MODEL = "medium"


def base_dir() -> Path:
    """Cartella di installazione (accanto all'exe) o radice del progetto in sviluppo."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = root / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def model_dir(key: str) -> Path:
    """Restituisce la cartella del modello: prima quella inclusa nell'installer, poi quella utente."""
    folder = MODELS[key]
    bundled = base_dir() / "models" / folder
    if (bundled / "model.bin").exists():
        return bundled
    return user_data_dir() / "models" / folder
