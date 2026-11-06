#!/usr/bin/env python3
"""Envia um vídeo pronto para a pasta "Videos virais" no Google Drive.

O n8n (workflow "Canal Terror · 5 · Iniciar upload de vídeo") abre um upload retomável
no Drive com a credencial do Google que já está nele e devolve um link temporário.
Este script manda o arquivo em partes para esse link. Nenhuma chave passa por aqui.

Uso: python3 enviar_drive.py video.mp4 [--nome "Nome no Drive.mp4"]
O endereço do webhook vem de ../n8n/canal-terror/workflows_publicados.json (fora do git).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

PUBLICADOS = Path(__file__).resolve().parent.parent / "n8n" / "canal-terror" / "workflows_publicados.json"
PARTE = 8 * 1024 * 1024  # múltiplo de 256 KB, exigido pelo Drive


def enviar(caminho: Path, nome: str | None = None) -> dict:
    url_webhook = json.loads(PUBLICADOS.read_text(encoding="utf-8"))["webhooks"]["upload"]
    tamanho = caminho.stat().st_size
    nome = nome or caminho.name
    r = subprocess.run(["curl", "-sS", "--max-time", "60", "-X", "POST", url_webhook, "-H", "Content-Type: application/json",
                        "-d", json.dumps({"nome": nome, "tamanho": tamanho, "mime": "video/mp4"})],
                       capture_output=True, text=True)
    upload_url = json.loads(r.stdout or "{}").get("upload_url")
    if not upload_url:
        sys.exit(f"O n8n não devolveu o link de upload: {r.stdout[:300]} {r.stderr[:300]}")

    with open(caminho, "rb") as f:
        inicio = 0
        while inicio < tamanho:
            dados = f.read(PARTE)
            fim = inicio + len(dados) - 1
            r = subprocess.run(["curl", "-sS", "--max-time", "300", "-X", "PUT", upload_url,
                                "-H", f"Content-Range: bytes {inicio}-{fim}/{tamanho}",
                                "--data-binary", "@-", "-w", "\n%{http_code}"],
                               input=dados, capture_output=True)
            corpo, _, codigo = r.stdout.decode(errors="replace").rpartition("\n")
            if codigo in ("200", "201"):
                info = json.loads(corpo)
                print(f"   enviado: {nome} → https://drive.google.com/file/d/{info['id']}/view")
                return info
            if codigo != "308":
                sys.exit(f"Falha no upload (HTTP {codigo}): {corpo[:300]}")
            inicio = fim + 1
            print(f"   {inicio * 100 // tamanho}%", flush=True)
    sys.exit("Upload terminou sem confirmação do Drive.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--nome")
    a = ap.parse_args()
    enviar(Path(a.video).resolve(), a.nome)
