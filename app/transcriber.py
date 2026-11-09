"""Wrapper su faster-whisper (solo CPU, int8)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .docx_writer import Segment


class Cancelled(Exception):
    pass


@dataclass
class Result:
    language: str
    duration: float
    segments: list[Segment]


def physical_cores() -> int:
    try:
        import psutil
        n = psutil.cpu_count(logical=False)
        if n:
            return n
    except Exception:
        pass
    return max(1, (os.cpu_count() or 2) // 2)


def ensure_model(name: str, target: Path, log: Callable[[str], None]) -> Path:
    """Scarica il modello se manca (usato solo per i modelli non inclusi nell'installer)."""
    if (target / "model.bin").exists():
        return target
    from faster_whisper import download_model
    log(f"Download del modello '{name}' in corso (una sola volta)...")
    target.mkdir(parents=True, exist_ok=True)
    download_model(name, output_dir=str(target))
    return target


class Transcriber:
    def __init__(self, model_path: Path, language: str | None):
        from faster_whisper import WhisperModel

        self.language = language
        self.model = WhisperModel(
            str(model_path),
            device="cpu",
            compute_type="int8",
            cpu_threads=physical_cores(),
        )

    def transcribe(
        self,
        path: Path,
        on_progress: Callable[[float], None],
        is_cancelled: Callable[[], bool],
    ) -> Result:
        segments, info = self.model.transcribe(
            str(path),
            language=self.language,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            beam_size=5,
            condition_on_previous_text=False,  # riduce le ripetizioni "in loop"
        )
        out: list[Segment] = []
        duration = info.duration or 0.0
        for seg in segments:  # generatore: la trascrizione avviene qui
            if is_cancelled():
                raise Cancelled()
            out.append(Segment(seg.start, seg.end, seg.text.strip()))
            if duration:
                on_progress(min(seg.end / duration, 1.0))
        on_progress(1.0)
        return Result(info.language, duration, out)
