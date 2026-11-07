#!/usr/bin/env python3
"""Baixa todos os arquivos de uma pasta do Google Drive para uma pasta local.

Uso: python3 baixar_drive.py ID_DA_PASTA destino/ [--so mp3,png]
Passa pelo workflow "Canal Terror · 8 · Drive (listar e baixar)" do n8n; nenhuma chave passa por aqui.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

PUBLICADOS = Path(__file__).resolve().parent.parent / "n8n" / "canal-terror" / "workflows_publicados.json"


def url_drive() -> str:
    return json.loads(PUBLICADOS.read_text(encoding="utf-8"))["webhooks"]["drive"]


def listar(pasta: str) -> list[dict]:
    r = subprocess.run(["curl", "-sS", "--max-time", "60", f"{url_drive()}?pasta={pasta}"], capture_output=True, text=True)
    return json.loads(r.stdout or "{}").get("arquivos", [])


def baixar(arquivo_id: str, destino: Path) -> bool:
    r = subprocess.run(["curl", "-sS", "--max-time", "300", "-o", str(destino), "-w", "%{http_code}",
                        f"{url_drive()}?id={arquivo_id}"], capture_output=True, text=True)
    return r.stdout.strip() == "200" and destino.exists() and destino.stat().st_size > 0


def baixar_pasta(pasta: str, destino: Path, extensoes: set[str] | None = None) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    feitos = []
    for f in sorted(listar(pasta), key=lambda x: x["name"]):
        if f.get("mimeType", "").endswith("folder"):
            continue
        if extensoes and Path(f["name"]).suffix.lower().lstrip(".") not in extensoes:
            continue
        alvo = destino / f["name"]
        if baixar(f["id"], alvo):
            feitos.append(alvo)
            print(f"   baixado: {f['name']}", flush=True)
        else:
            print(f"   FALHOU: {f['name']}", file=sys.stderr)
    return feitos


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("destino")
    ap.add_argument("--so", help="extensões separadas por vírgula (ex.: mp3,png)")
    a = ap.parse_args()
    ext = {e.strip().lower() for e in a.so.split(",")} if a.so else None
    n = baixar_pasta(a.pasta, Path(a.destino), ext)
    print(f"{len(n)} arquivo(s) baixado(s) em {a.destino}")
