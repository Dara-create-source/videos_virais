#!/usr/bin/env bash
# Baixa a voz em português (Piper, roda offline) e instala o Piper.
set -e
cd "$(dirname "$0")"
pip install -q piper-tts
mkdir -p vozes
base="https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium"
for f in pt_BR-faber-medium.onnx pt_BR-faber-medium.onnx.json; do
  [ -f "vozes/$f" ] || curl -sSL -o "vozes/$f" "$base/$f"
done
echo "Voz pronta em vozes/"
