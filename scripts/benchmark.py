"""Misura la velocità di trascrizione su un PC reale.

Uso:  python scripts/benchmark.py file_di_prova.mp3 [medium|small|large-v3-turbo] [it]
Stampa il rapporto tempo di elaborazione / durata audio (RTF): < 1 significa più veloce del tempo reale.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faster_whisper import WhisperModel  # noqa: E402

from app.transcriber import physical_cores  # noqa: E402

audio = sys.argv[1]
model = sys.argv[2] if len(sys.argv) > 2 else "medium"
lang = sys.argv[3] if len(sys.argv) > 3 else "it"

local = Path(__file__).resolve().parent.parent / "models" / f"faster-whisper-{model}"
src = str(local) if (local / "model.bin").exists() else model

t = time.monotonic()
m = WhisperModel(src, device="cpu", compute_type="int8", cpu_threads=physical_cores())
print(f"Modello caricato in {time.monotonic() - t:.1f}s  (thread: {physical_cores()})")

t = time.monotonic()
segs, info = m.transcribe(audio, language=lang, vad_filter=True, beam_size=5)
text = " ".join(s.text.strip() for s in segs)
el = time.monotonic() - t
print(f"Audio: {info.duration:.0f}s  Elaborazione: {el:.0f}s  RTF: {el / info.duration:.2f}")
print(text[:500])
