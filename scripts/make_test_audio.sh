#!/bin/bash
# Genera 10 file audio di prova (solo macOS: usa `say` e `afconvert`, già inclusi nel sistema).
# Se è installato ffmpeg (brew install ffmpeg) crea anche mp3 e ogg, altrimenti li sostituisce.
#
# Uso:  scripts/make_test_audio.sh [cartella]     (default: ~/Desktop/audio-test)
#
# Casi coperti: formati diversi, sottocartelle, nome con spazi e accenti,
# conflitto di nomi (stesso nome, estensione diversa), audio lungo, lingua inglese, pause.
set -euo pipefail

OUT="${1:-$HOME/Desktop/audio-test}"
VOICE_IT="Alice"
VOICE_EN="Samantha"
mkdir -p "$OUT/riunioni" "$OUT/interviste/2026"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

HAS_FFMPEG=0; command -v ffmpeg >/dev/null && HAS_FFMPEG=1

# make <voce> <testo> <file di destinazione>  -> il formato si deduce dall'estensione
make() {
  local voice="$1" text="$2" dest="$3"
  local src="$TMP/src.aiff"
  say -v "$voice" -o "$src" "$text"
  case "${dest##*.}" in
    aiff) cp "$src" "$dest" ;;
    wav)  afconvert -f WAVE -d LEI16@16000 "$src" "$dest" ;;
    m4a)  afconvert -f m4af -d aac "$src" "$dest" ;;
    flac) afconvert -f flac -d flac "$src" "$dest" ;;
    mp3|ogg)
      if [ $HAS_FFMPEG = 1 ]; then
        ffmpeg -loglevel error -y -i "$src" "$dest"
      else
        dest="${dest%.*}.m4a"; afconvert -f m4af -d aac "$src" "$dest"
      fi ;;
  esac
  echo "  ✓ ${dest#$OUT/}"
}

LONG="Questa è una registrazione più lunga per verificare la barra di avanzamento e la stima del tempo rimanente. \
Il software deve dividere il testo in paragrafi quando trova una pausa. [[slnc 2500]] \
Dopo questa pausa dovrebbe iniziare un nuovo paragrafo. Parliamo ora del bilancio del terzo trimestre: \
i ricavi sono cresciuti del dodici per cento, mentre i costi operativi sono rimasti sostanzialmente stabili. \
[[slnc 3000]] Ultimo punto all'ordine del giorno: la pianificazione delle ferie estive. \
Si chiede a tutti di comunicare le proprie preferenze entro la fine del mese."

echo "Genero i file in: $OUT"
make "$VOICE_IT" "Buongiorno, questa è una prova di trascrizione automatica." "$OUT/01_saluto.aiff"
make "$VOICE_IT" "Il treno per Napoli partirà dal binario sette con quindici minuti di ritardo." "$OUT/02_annuncio.wav"
make "$VOICE_IT" "Ricordati di comprare il latte, il pane e due chili di mele." "$OUT/03_promemoria.m4a"
make "$VOICE_IT" "Questo file è in formato FLAC, un formato audio senza perdita di qualità." "$OUT/04_lossless.flac"
make "$VOICE_IT" "Questo file dovrebbe essere un MP3, il formato più diffuso." "$OUT/05_musica.mp3"
make "$VOICE_IT" "Il nome di questo file contiene spazi e lettere accentate." "$OUT/06 nota città è perché.m4a"
make "$VOICE_IT" "$LONG" "$OUT/riunioni/07_riunione_lunga.wav"
make "$VOICE_IT" "Prima versione: stesso nome del file successivo, ma in formato wav." "$OUT/riunioni/08_conflitto.wav"
make "$VOICE_IT" "Seconda versione: stesso nome del file precedente, ma in formato m4a." "$OUT/riunioni/08_conflitto.m4a"
make "$VOICE_EN" "This is an English recording, useful to test automatic language detection." "$OUT/interviste/2026/10_english.ogg"

echo "Fatto: $(find "$OUT" -type f | wc -l | tr -d ' ') file."
[ $HAS_FFMPEG = 0 ] && echo "Nota: ffmpeg non trovato, mp3/ogg creati come m4a (brew install ffmpeg per averli)."
exit 0
