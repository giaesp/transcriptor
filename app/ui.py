"""Finestra principale."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from . import APP_NAME, APP_VERSION
from .worker import Options, Worker

LANGUAGES = [
    ("Italiano", "it"), ("Rilevamento automatico", None), ("Inglese", "en"),
    ("Francese", "fr"), ("Tedesco", "de"), ("Spagnolo", "es"),
]
QUALITIES = [
    ("Bilanciata (consigliata)", "medium"),
    ("Veloce (scarica ~500 MB al primo uso)", "small"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(760, 600)
        self.settings = QSettings(APP_NAME, APP_NAME)
        self.worker: Worker | None = None

        # --- Cartelle
        self.in_edit, in_row = self._folder_row("input_dir")
        self.out_edit, out_row = self._folder_row("output_dir")
        folders = QGroupBox("Cartelle")
        fl = QFormLayout(folders)
        fl.addRow("Cartella audio:", in_row)
        fl.addRow("Cartella documenti:", out_row)

        # --- Opzioni
        self.lang = QComboBox()
        for label, code in LANGUAGES:
            self.lang.addItem(label, code)
        self.quality = QComboBox()
        for label, key in QUALITIES:
            self.quality.addItem(label, key)
        self.recursive = QCheckBox("Includi le sottocartelle")
        self.mirror = QCheckBox("Ricrea la struttura delle sottocartelle nell'output")
        self.timestamps = QCheckBox("Inserisci i minutaggi nel documento")
        self.recursive.toggled.connect(self.mirror.setEnabled)

        opts = QGroupBox("Opzioni")
        ol = QFormLayout(opts)
        ol.addRow("Lingua:", self.lang)
        ol.addRow("Qualità:", self.quality)
        ol.addRow(self.recursive)
        ol.addRow(self.mirror)
        ol.addRow(self.timestamps)

        # --- Avanzamento
        self.file_label = QLabel("Pronto.")
        self.file_bar = QProgressBar()
        self.total_bar = QProgressBar()
        self.eta_label = QLabel("")
        self.log_view = QPlainTextEdit(readOnly=True)
        self.log_view.setMaximumBlockCount(5000)

        self.start_btn = QPushButton("Avvia trascrizione")
        self.start_btn.setMinimumHeight(36)
        self.stop_btn = QPushButton("Interrompi")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        btns = QHBoxLayout()
        btns.addWidget(self.start_btn, 3)
        btns.addWidget(self.stop_btn, 1)

        root = QWidget()
        v = QVBoxLayout(root)
        v.addWidget(folders)
        v.addWidget(opts)
        v.addLayout(btns)
        v.addWidget(self.file_label)
        v.addWidget(self.file_bar)
        v.addWidget(QLabel("Totale:"))
        v.addWidget(self.total_bar)
        v.addWidget(self.eta_label)
        v.addWidget(self.log_view, 1)
        self.setCentralWidget(root)

        self._load_settings()

    # ---------- helpers
    def _folder_row(self, key: str):
        edit = QLineEdit()
        btn = QPushButton("Sfoglia…")
        btn.clicked.connect(lambda: self._browse(edit))
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(edit, 1)
        h.addWidget(btn)
        edit.setObjectName(key)
        return edit, row

    def _browse(self, edit: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "Scegli cartella", edit.text() or str(Path.home()))
        if d:
            edit.setText(d)

    def _load_settings(self):
        s = self.settings
        self.in_edit.setText(s.value("input_dir", ""))
        self.out_edit.setText(s.value("output_dir", ""))
        self.lang.setCurrentIndex(int(s.value("lang_idx", 0)))
        self.quality.setCurrentIndex(int(s.value("quality_idx", 0)))
        self.recursive.setChecked(s.value("recursive", "true") == "true")
        self.mirror.setChecked(s.value("mirror", "true") == "true")
        self.timestamps.setChecked(s.value("timestamps", "false") == "true")
        self.mirror.setEnabled(self.recursive.isChecked())

    def _save_settings(self):
        s = self.settings
        s.setValue("input_dir", self.in_edit.text())
        s.setValue("output_dir", self.out_edit.text())
        s.setValue("lang_idx", self.lang.currentIndex())
        s.setValue("quality_idx", self.quality.currentIndex())
        s.setValue("recursive", "true" if self.recursive.isChecked() else "false")
        s.setValue("mirror", "true" if self.mirror.isChecked() else "false")
        s.setValue("timestamps", "true" if self.timestamps.isChecked() else "false")

    def _set_running(self, running: bool):
        for w in (self.in_edit, self.out_edit, self.lang, self.quality,
                  self.recursive, self.mirror, self.timestamps, self.start_btn):
            w.setEnabled(not running)
        if not running:
            self.mirror.setEnabled(self.recursive.isChecked())
        self.stop_btn.setEnabled(running)

    def _log(self, msg: str):
        self.log_view.appendPlainText(msg)

    # ---------- azioni
    def start(self):
        in_dir = Path(self.in_edit.text().strip())
        out_dir = Path(self.out_edit.text().strip())
        if not self.in_edit.text().strip() or not in_dir.is_dir():
            QMessageBox.warning(self, APP_NAME, "Seleziona una cartella audio valida.")
            return
        if not self.out_edit.text().strip():
            QMessageBox.warning(self, APP_NAME, "Seleziona una cartella di destinazione.")
            return
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, f"Impossibile creare la cartella di output:\n{e}")
            return

        self._save_settings()
        self.log_view.clear()
        self.file_bar.setValue(0)
        self.total_bar.setValue(0)
        self.eta_label.setText("")
        self._set_running(True)

        opts = Options(
            input_dir=in_dir, output_dir=out_dir,
            recursive=self.recursive.isChecked(),
            mirror_tree=self.recursive.isChecked() and self.mirror.isChecked(),
            timestamps=self.timestamps.isChecked(),
            language=self.lang.currentData(),
            model_key=self.quality.currentData(),
        )
        w = Worker(opts)
        w.log.connect(self._log)
        w.file_started.connect(lambda i, n, name: self.file_label.setText(f"File {i} di {n}: {name}"))
        w.file_progress.connect(lambda f: self.file_bar.setValue(int(f * 100)))
        w.overall_progress.connect(lambda f: self.total_bar.setValue(int(f * 100)))
        w.eta.connect(lambda t: self.eta_label.setText(f"Tempo stimato rimanente: {t}"))
        w.done.connect(self._finished)
        self.worker = w
        w.start()

    def stop(self):
        if self.worker:
            self.stop_btn.setEnabled(False)
            self.file_label.setText("Interruzione in corso…")
            self.worker.cancel()

    def _finished(self, done: int, skipped: int, errors: int, cancelled: bool):
        self._set_running(False)
        self.eta_label.setText("")
        head = "Interrotto." if cancelled else "Completato."
        msg = f"{head}\nTrascritti: {done}\nGià presenti (saltati): {skipped}\nErrori: {errors}"
        self.file_label.setText(head)
        self._log("\n" + msg.replace("\n", " · ", 1))
        QMessageBox.information(self, APP_NAME, msg)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            r = QMessageBox.question(
                self, APP_NAME,
                "Una trascrizione è in corso. Vuoi interromperla e chiudere?\n"
                "Al prossimo avvio riprenderà dai file non ancora completati.",
            )
            if r != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait(15000)
        self._save_settings()
        event.accept()
