# Transcriptor

Trascrive tutti i file audio di una cartella in documenti `.docx` (stesso nome, estensione diversa).
Funziona offline: faster-whisper con modello `medium`, solo CPU, int8.

## Sviluppo

```bash
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_model.py medium
python run.py
```

## Build installer Windows

Su una macchina Windows con Python 3.12 e Inno Setup 6:

```bat
build\build_windows.bat
```

Output: `dist\installer\Transcriptor-Setup-0.1.0.exe` (modello incluso, ~1,7 GB).

## Ripresa del lavoro

- Ogni `.docx` viene scritto in `<nome>.docx.part` e poi rinominato in modo atomico:
  se esiste un `.docx` finale, è completo.
- Nel documento è salvato un marcatore (proprietà *Commenti*) con la dimensione del file sorgente.
  All'avvio i file già trascritti vengono saltati; se l'audio sorgente è cambiato, viene ritrascritto.
- I `.part` rimasti da un'interruzione vengono eliminati all'avvio successivo.
- Un `.docx` non creato da Transcriptor non viene mai sovrascritto.

## Benchmark su un PC reale

```bash
python scripts/benchmark.py prova.mp3 medium it
python scripts/benchmark.py prova.mp3 large-v3-turbo it
```
