"""Thread di elaborazione: non blocca la UI."""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .docx_writer import OutputState, cleanup_partials, output_state, write_transcript
from .paths import MODELS, model_dir
from .scanner import build_jobs
from .transcriber import Cancelled, Transcriber, ensure_model


STATUS_WAITING = "In attesa"
STATUS_RUNNING = "In corso…"
STATUS_DONE = "Completato"
STATUS_PRESENT = "Già presente"
STATUS_FOREIGN = "Esistente (non sovrascritto)"
STATUS_ERROR = "Errore"


@dataclass
class Options:
    input_dir: Path
    output_dir: Path
    recursive: bool
    mirror_tree: bool
    timestamps: bool
    language: str | None   # None = rilevamento automatico
    model_key: str          # "medium" | "small"


class Worker(QThread):
    log = Signal(str)
    file_started = Signal(int, int, str)     # indice (1-based), totale, nome
    file_progress = Signal(float)             # 0..1
    overall_progress = Signal(float)          # 0..1
    eta = Signal(str)
    jobs_listed = Signal(list)                # [(sorgente, output, stato), ...]
    job_status = Signal(int, str)             # indice nella lista, stato
    done = Signal(int, int, int, bool)        # fatti, saltati, errori, annullato

    def __init__(self, opts: Options):
        super().__init__()
        self.opts = opts
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _audio_seconds(self, path: Path) -> float:
        try:
            import av
            with av.open(str(path)) as c:
                return (c.duration or 0) / 1_000_000
        except Exception:
            return 0.0

    def run(self):
        o = self.opts
        done = skipped = errors = 0
        try:
            removed = cleanup_partials(o.output_dir)
            if removed:
                self.log.emit(f"Rimossi {removed} file incompleti da un'esecuzione precedente.")

            jobs, warnings = build_jobs(o.input_dir, o.output_dir, o.recursive, o.mirror_tree)
            for w in warnings:
                self.log.emit("⚠ " + w)
            if not jobs:
                self.log.emit("Nessun file audio trovato nella cartella di input.")
                self.done.emit(0, 0, 0, False)
                return

            # Controllo di ripresa: separa i file già completati da quelli da fare
            todo = []          # (indice globale, job)
            listing = []
            for idx, job in enumerate(jobs):
                state = output_state(job.source, job.output)
                if state is OutputState.COMPLETE:
                    skipped += 1
                    status = STATUS_PRESENT
                elif state is OutputState.FOREIGN:
                    skipped += 1
                    status = STATUS_FOREIGN
                    self.log.emit(f"⚠ '{job.output.name}' esiste già e non è stato creato da Transcriptor: non lo sovrascrivo.")
                else:
                    if state is OutputState.STALE:
                        self.log.emit(f"Il file sorgente '{job.source.name}' è cambiato: verrà ritrascritto.")
                    status = STATUS_WAITING
                    todo.append((idx, job))
                listing.append((str(job.source), str(job.output), status))
            self.jobs_listed.emit(listing)

            self.log.emit(f"Trovati {len(jobs)} file audio: {skipped} già completati, {len(todo)} da trascrivere.")
            if not todo:
                self.overall_progress.emit(1.0)
                self.done.emit(0, skipped, 0, False)
                return

            durations = [self._audio_seconds(j.source) for _, j in todo]
            total_audio = sum(durations) or float(len(todo))

            model_name = o.model_key
            mpath = ensure_model(model_name, model_dir(model_name), self.log.emit)
            self.log.emit(f"Caricamento del modello '{model_name}'...")
            tr = Transcriber(mpath, o.language)

            processed_audio = 0.0
            t0 = time.monotonic()

            for i, ((gidx, job), dur) in enumerate(zip(todo, durations), start=1):
                if self._cancel:
                    break
                self.file_started.emit(i, len(todo), job.source.name)
                self.job_status.emit(gidx, STATUS_RUNNING)
                self.log.emit(f"[{i}/{len(todo)}] {job.source.name}")
                weight = dur or 1.0

                def on_progress(frac: float, _w=weight):
                    self.file_progress.emit(frac)
                    cur = processed_audio + frac * _w
                    self.overall_progress.emit(cur / total_audio)
                    elapsed = time.monotonic() - t0
                    if cur > 0 and elapsed > 5:
                        remaining = elapsed / cur * (total_audio - cur)
                        self.eta.emit(_fmt_eta(remaining))

                try:
                    res = tr.transcribe(job.source, on_progress, lambda: self._cancel)
                    write_transcript(job.source, job.output, res.segments, res.language,
                                     res.duration, model_name, o.timestamps)
                    done += 1
                    self.job_status.emit(gidx, STATUS_DONE)
                    self.log.emit(f"   ✓ salvato: {job.output}")
                except Cancelled:
                    self.job_status.emit(gidx, STATUS_WAITING)
                    self.log.emit("   Interrotto: questo file verrà ripreso al prossimo avvio.")
                    break
                except Exception as e:
                    errors += 1
                    self.job_status.emit(gidx, STATUS_ERROR)
                    self.log.emit(f"   ✗ errore: {e}")
                processed_audio += weight

            self.done.emit(done, skipped, errors, self._cancel)
        except Exception:
            self.log.emit("Errore imprevisto:\n" + traceback.format_exc())
            self.done.emit(done, skipped, errors + 1, self._cancel)


def _fmt_eta(seconds: float) -> str:
    s = int(seconds)
    h, m = s // 3600, s % 3600 // 60
    return f"{h} h {m:02d} min" if h else f"{m} min {s % 60:02d} s"
