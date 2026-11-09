"""Scarica il modello da includere nell'installer in ./models/faster-whisper-<nome>.

Uso:  python scripts/download_model.py [medium|small]
"""
import sys
from pathlib import Path

from faster_whisper import download_model

name = sys.argv[1] if len(sys.argv) > 1 else "medium"
target = Path(__file__).resolve().parent.parent / "models" / f"faster-whisper-{name}"
target.mkdir(parents=True, exist_ok=True)
print(f"Scarico '{name}' in {target} ...")
download_model(name, output_dir=str(target))
print("Fatto.")
