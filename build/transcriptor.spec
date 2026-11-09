# PyInstaller spec — eseguire dalla radice del progetto:
#   pyinstaller build/transcriptor.spec --noconfirm
# Il modello NON è incluso qui: lo copia Inno Setup in {app}\models.
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = SPECPATH + "/.."

datas = collect_data_files("faster_whisper")          # modello VAD silero (assets/)
binaries = collect_dynamic_libs("ctranslate2") + collect_dynamic_libs("onnxruntime")

a = Analysis(
    [ROOT + "/run.py"],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=["av", "psutil"],
    excludes=["tkinter", "matplotlib", "torch", "tensorflow",
              "PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.QtMultimedia"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Transcriptor",
    console=False,
    icon=ROOT + "/build/icon.ico" if __import__("os").path.exists(ROOT + "/build/icon.ico") else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Transcriptor")
