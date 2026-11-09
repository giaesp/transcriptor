@echo off
REM Build completo su Windows: venv, modello, exe, installer.
REM Richiede: Python 3.12 x64, Inno Setup 6 (iscc nel PATH).
setlocal
cd /d "%~dp0.."

if not exist .venv (
    py -3.12 -m venv .venv || goto :err
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-build.txt || goto :err

if not exist models\faster-whisper-medium\model.bin (
    python scripts\download_model.py medium || goto :err
)

pyinstaller build\transcriptor.spec --noconfirm --distpath dist --workpath build\work || goto :err
iscc build\installer.iss || goto :err

echo.
echo Installer creato in dist\installer\
exit /b 0

:err
echo BUILD FALLITO
exit /b 1
