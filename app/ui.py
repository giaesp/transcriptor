"""Finestra principale."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from . import APP_NAME, APP_VERSION
from .worker import (
    STATUS_DONE, STATUS_ERROR, STATUS_FOREIGN, STATUS_PRESENT, STATUS_RUNNING,
    Options, Worker,
)

STATUS_COLORS = {
    STATUS_DONE: "#2e7d32", STATUS_PRESENT: "#2e7d32", STATUS_RUNNING: "#1565c0",
    STATUS_ERROR: "#c62828", STATUS_FOREIGN: "#ef6c00",
}
ROLE_SRC = Qt.ItemDataRole.UserRole
ROLE_OUT = Qt.ItemDataRole.UserRole + 1


def open_path(path: Path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def reveal_in_folder(path: Path):
    """Apre la cartella selezionando il file (Esplora risorse / Finder)."""
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)])
        else:
            open_path(path.parent)
    except OSError:
        open_path(path.parent)

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

        # --- Lista file
        self.files = QTreeWidget()
        self.files.setHeaderLabels(["Stato", "File audio", "Documento"])
        self.files.setRootIsDecorated(False)
        self.files.setAlternatingRowColors(True)
        self.files.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.files.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        hdr = self.files.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.files.itemDoubleClicked.connect(lambda item, _c: self._open_doc(item))
        self.files.customContextMenuRequested.connect(self._files_menu)
        self.files.currentItemChanged.connect(lambda *_: self._update_file_buttons())

        self.open_btn = QPushButton("Apri documento")
        self.reveal_btn = QPushButton("Mostra nella cartella")
        self.open_out_btn = QPushButton("Apri cartella documenti")
        self.open_btn.clicked.connect(lambda: self._open_doc(self.files.currentItem()))
        self.reveal_btn.clicked.connect(lambda: self._reveal(self.files.currentItem()))
        self.open_out_btn.clicked.connect(self._open_output_dir)
        fbtns = QHBoxLayout()
        fbtns.addWidget(self.open_btn)
        fbtns.addWidget(self.reveal_btn)
        fbtns.addStretch(1)
        fbtns.addWidget(self.open_out_btn)

        files_box = QWidget()
        fv = QVBoxLayout(files_box)
        fv.setContentsMargins(0, 0, 0, 0)
        fv.addWidget(QLabel("File (doppio clic per aprire il documento):"))
        fv.addWidget(self.files, 1)
        fv.addLayout(fbtns)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(files_box)
        splitter.addWidget(self.log_view)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

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
        v.addWidget(splitter, 1)
        self.setCentralWidget(root)
        self.resize(900, 760)

        self._load_settings()
        self._update_file_buttons()

    # ---------- lista file
    def _populate(self, listing: list):
        self.files.clear()
        for src, out, status in listing:
            item = QTreeWidgetItem([status, Path(src).name, Path(out).name])
            item.setData(0, ROLE_SRC, src)
            item.setData(0, ROLE_OUT, out)
            item.setToolTip(1, src)
            item.setToolTip(2, out)
            self._paint(item, status)
            self.files.addTopLevelItem(item)
        self._update_file_buttons()

    def _paint(self, item: QTreeWidgetItem, status: str):
        item.setText(0, status)
        color = STATUS_COLORS.get(status)
        item.setForeground(0, QBrush(QColor(color)) if color else QBrush())

    def _set_status(self, idx: int, status: str):
        item = self.files.topLevelItem(idx)
        if item:
            self._paint(item, status)
            if status == STATUS_RUNNING:
                self.files.scrollToItem(item)
            if item is self.files.currentItem():
                self._update_file_buttons()

    def _doc_of(self, item) -> Path | None:
        if item is None:
            return None
        p = Path(item.data(0, ROLE_OUT))
        return p if p.exists() else None

    def _update_file_buttons(self):
        has_doc = self._doc_of(self.files.currentItem()) is not None
        self.open_btn.setEnabled(has_doc)
        self.reveal_btn.setEnabled(has_doc)

    def _open_doc(self, item):
        doc = self._doc_of(item)
        if doc:
            open_path(doc)
        elif item is not None:
            QMessageBox.information(self, APP_NAME, "Il documento non è ancora stato creato.")

    def _reveal(self, item):
        doc = self._doc_of(item)
        if doc:
            reveal_in_folder(doc)

    def _open_output_dir(self):
        d = Path(self.out_edit.text().strip())
        if self.out_edit.text().strip() and d.is_dir():
            open_path(d)

    def _files_menu(self, pos):
        item = self.files.itemAt(pos)
        if item is None:
            return
        doc = self._doc_of(item)
        src = Path(item.data(0, ROLE_SRC))
        menu = QMenu(self)
        a = menu.addAction("Apri documento", lambda: open_path(doc))
        a.setEnabled(doc is not None)
        b = menu.addAction("Mostra documento nella cartella", lambda: reveal_in_folder(doc))
        b.setEnabled(doc is not None)
        menu.addSeparator()
        menu.addAction("Apri file audio", lambda: open_path(src))
        menu.addAction("Mostra file audio nella cartella", lambda: reveal_in_folder(src))
        menu.exec(self.files.viewport().mapToGlobal(pos))

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
        self.files.clear()
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
        w.jobs_listed.connect(self._populate)
        w.job_status.connect(self._set_status)
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
