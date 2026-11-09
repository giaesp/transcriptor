"""Scrittura atomica dei DOCX e controllo di completamento (ripresa del lavoro).

Strategia di ripresa:
1. Il documento viene salvato in un file temporaneo "<nome>.docx.part" nella stessa
   cartella e poi rinominato con os.replace (operazione atomica). Quindi un .docx finale
   esiste solo se la scrittura è terminata: un'interruzione (crash, spegnimento,
   Annulla) lascia al massimo un .part, che viene ignorato ed eliminato.
2. Nelle proprietà del documento salviamo un marcatore JSON con dimensione e data di
   modifica del file sorgente. Se il .docx esiste e il marcatore corrisponde, il file
   è già trascritto e viene saltato. Se il sorgente è cambiato, si ritrascrive.
3. Un .docx senza marcatore (non creato da Transcriptor) non viene mai sovrascritto.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor

from . import APP_NAME, APP_VERSION

MARKER_KEY = "transcriptor"
PART_SUFFIX = ".part"


@dataclass
class Segment:
    start: float
    end: float
    text: str


class OutputState(Enum):
    MISSING = "missing"          # da trascrivere
    COMPLETE = "complete"        # già fatto, saltare
    STALE = "stale"              # fatto da noi ma sorgente cambiato: ritrascrivere
    FOREIGN = "foreign"          # .docx non nostro: non toccare


def source_signature(src: Path) -> dict:
    st = src.stat()
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


def _read_marker(docx_path: Path) -> dict | None:
    try:
        comments = Document(str(docx_path)).core_properties.comments or ""
        data = json.loads(comments)
        if isinstance(data, dict) and data.get(MARKER_KEY):
            return data
    except Exception:
        pass
    return None


def output_state(src: Path, out: Path) -> OutputState:
    if not out.exists():
        return OutputState.MISSING
    marker = _read_marker(out)
    if marker is None:
        return OutputState.FOREIGN
    if not marker.get("complete"):
        return OutputState.STALE
    sig = source_signature(src)
    if marker.get("source_size") != sig["size"]:
        return OutputState.STALE
    return OutputState.COMPLETE


def cleanup_partials(output_dir: Path) -> int:
    """Elimina i .part lasciati da esecuzioni interrotte."""
    n = 0
    if output_dir.exists():
        for p in output_dir.rglob("*.docx" + PART_SUFFIX):
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
    return n


def _fmt_ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _paragraphs(segments: list[Segment], pause: float = 2.0, max_chars: int = 900) -> list[tuple[float, str]]:
    """Raggruppa i segmenti in paragrafi: un nuovo paragrafo dopo una pausa o quando è troppo lungo."""
    paras: list[tuple[float, str]] = []
    cur: list[str] = []
    start = 0.0
    last_end = None
    for seg in segments:
        if not seg.text:
            continue
        new_para = cur and (
            (last_end is not None and seg.start - last_end > pause)
            or sum(len(t) for t in cur) > max_chars
        )
        if new_para:
            paras.append((start, " ".join(cur)))
            cur = []
        if not cur:
            start = seg.start
        cur.append(seg.text)
        last_end = seg.end
    if cur:
        paras.append((start, " ".join(cur)))
    return paras


def write_transcript(
    src: Path,
    out: Path,
    segments: list[Segment],
    language: str,
    duration: float,
    model_name: str,
    timestamps: bool,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    doc.add_heading(src.stem, level=1)
    meta = doc.add_paragraph()
    run = meta.add_run(
        f"File: {src.name}  ·  Durata: {_fmt_ts(duration)}  ·  Lingua: {language}  ·  "
        f"Trascritto il {datetime.now():%d/%m/%Y %H:%M}"
    )
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    paras = _paragraphs(segments)
    if not paras:
        doc.add_paragraph("(Nessun parlato rilevato)")
    for start, text in paras:
        p = doc.add_paragraph()
        if timestamps:
            ts = p.add_run(f"[{_fmt_ts(start)}] ")
            ts.bold = True
            ts.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        p.add_run(text)

    sig = source_signature(src)
    cp = doc.core_properties
    cp.title = src.stem
    cp.author = APP_NAME
    cp.comments = json.dumps({
        MARKER_KEY: APP_VERSION,
        "complete": True,
        "source_name": src.name,
        "source_size": sig["size"],
        "source_mtime": sig["mtime"],
        "model": model_name,
    })

    tmp = out.with_name(out.name + PART_SUFFIX)
    doc.save(str(tmp))
    # flush su disco prima del rename, così un blackout non lascia un docx vuoto
    with open(tmp, "rb+") as fh:
        os.fsync(fh.fileno())
    os.replace(tmp, out)
