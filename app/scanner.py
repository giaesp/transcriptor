"""Ricerca dei file audio e calcolo dei percorsi di output."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".flac",
    ".wma", ".amr", ".aiff", ".aif", ".webm", ".mp4", ".m4v", ".mkv",
    ".mov", ".3gp",
}


@dataclass
class Job:
    source: Path
    output: Path


def find_audio_files(input_dir: Path, recursive: bool) -> list[Path]:
    it = input_dir.rglob("*") if recursive else input_dir.glob("*")
    files = [
        p for p in it
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS and not p.name.startswith(".")
    ]
    return sorted(files, key=lambda p: str(p).lower())


def build_jobs(input_dir: Path, output_dir: Path, recursive: bool, mirror_tree: bool) -> tuple[list[Job], list[str]]:
    """Crea la lista dei lavori. Restituisce anche eventuali avvisi (es. nomi in conflitto)."""
    warnings: list[str] = []
    jobs: list[Job] = []
    used: dict[str, Path] = {}

    for src in find_audio_files(input_dir, recursive):
        rel_parent = src.parent.relative_to(input_dir) if mirror_tree else Path()
        out = output_dir / rel_parent / (src.stem + ".docx")
        key = str(out).lower()
        if key in used:
            # es. "intervista.mp3" e "intervista.wav": il secondo diventa "intervista.wav.docx"
            out = out.with_name(src.name + ".docx")
            warnings.append(
                f"Nome in conflitto con '{used[key].name}': '{src.name}' verrà salvato come '{out.name}'"
            )
            key = str(out).lower()
        used[key] = src
        jobs.append(Job(src, out))
    return jobs, warnings
