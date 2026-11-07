#!/usr/bin/env python3
"""Converte o roteiro do Google Doc (formato da tarefa agendada) em roteiro.json de montagem.

Uso: python3 doc_para_roteiro.py roteiro.txt projeto/ [--contador "DIA 3"]
- roteiro.txt: o texto do Doc (exportado como texto simples)
- projeto/: pasta do vídeo; cria projeto/roteiro.json e espera as imagens em projeto/imagens/

Cada cena vira: fundo = imagens/<nome_do_cenario>.png; pose do Lucas pela descrição
("com lanterna", "de costas"...) usando as artes de ../personagens/; efeitos e sons pelas palavras-chave.
Depois de gerado, o roteiro.json pode ser ajustado à mão (tempos de som, brilho, foco).
"""
import argparse
import json
import re
from pathlib import Path

POSES = [  # (palavras na descrição da imagem, arquivo em personagens/)
    (("sorriso", "sorrindo", "estranho"), "lucas_sorriso.png"),
    (("costas",), "lucas_costas.png"),
    (("sentado",), "lucas_sentado.png"),
    (("celular", "telefone"), "lucas_celular.png"),
    (("lanterna", "medo", "assustado"), "lucas_lanterna.png"),
    (("andando", "caminhando", "correndo"), "lucas_andando.png"),
    (("valdir",), "seu_valdir.png"),
]
SONS = ["impacto", "batida", "chiado", "bip", "telefone", "buzina", "sino", "toc", "estalo"]


def efeito_de(txt: str) -> tuple[str, dict]:
    t = txt.lower()
    extra = {}
    if "corte seco" in t or "preto" in t:
        extra["final_preto"] = True
    if "zoom rápido" in t or "zoom rapido" in t:
        return "zoom_rapido", extra
    if "tremor" in t:
        return "tremor", extra
    if "piscar" in t or "pisca" in t:
        return "piscar", extra
    if "afastar" in t or "zoom out" in t:
        return "afastar", extra
    if "zoom" in t:
        return "zoom_lento", extra
    return "nenhum", extra


def converter(texto: str, contador: str | None = None) -> dict:
    tipo = (re.search(r"TIPO:\s*(.+)", texto) or [None, "Avulso"])[1].strip()
    titulo = (re.search(r"T[IÍ]TULO:\s*(.+)", texto) or [None, ""])[1].strip()
    blocos = re.split(r"\n\s*CENA\s+\d+\s*\n", texto.split("IMAGENS NOVAS PARA GERAR")[0])[1:]
    cenas = []
    for b in blocos:
        b = b.replace("\\_", "_").replace("\\[", "[").replace("\\]", "]")
        narr = re.search(r"Narra[cç][aã]o:\s*[\"“](.+?)[\"”]\s*$", b, re.M | re.S)
        img = re.search(r"Imagem:\s*(.+)", b)
        efe = re.search(r"Efeitos:\s*(.+)", b)
        son = re.search(r"Sons:\s*(.+)", b)
        if not narr:
            continue
        c = {"narracao": narr.group(1).strip()}
        partes = [p.strip() for p in (img.group(1) if img else "").split("+")]
        if partes and partes[0]:
            c["fundo"] = f"imagens/{re.sub(r'[^a-z0-9_]', '', partes[0].lower())}.png"
        for p in partes[1:]:
            for chaves, arq in POSES:
                if any(k in p.lower() for k in chaves):
                    c.update(personagem=f"../personagens/{arq}", tamanho=0.42, chao=0.9)
                    break
        ef, extra = efeito_de(efe.group(1) if efe else "")
        c["efeito"] = ef
        c.update(extra)
        if c.get("personagem") and ef == "tremor":
            c["personagem_efeito"] = "tremer"
        sons = [s for s in SONS if son and s in son.group(1).lower()]
        if sons:
            c["sons"] = sons
        cenas.append(c)
    if cenas:
        cenas[-1].setdefault("final_preto", True)
        cenas[-1]["pausa_depois"] = 1.0
    serie = "parte" in tipo.lower()
    cfg = {"formato": "9:16", "pasta_audio": "audio", "palavras_legenda": 3, "pausa": 0.9, "brilho_fundo": 1.4,
           "modelo_voz": "../vozes/pt_BR-faber-medium.onnx",
           "chamada": "serie" if serie else "avulso", "chamada_personagem": "../personagens/lucas_lanterna.png"}
    if contador:
        cfg["contador"] = {"valor": contador}
    return {"titulo": titulo, "tipo": tipo, "config": cfg, "cenas": cenas}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("texto")
    ap.add_argument("projeto")
    ap.add_argument("--contador")
    a = ap.parse_args()
    rot = converter(Path(a.texto).read_text(encoding="utf-8"), a.contador)
    pasta = Path(a.projeto)
    (pasta / "imagens").mkdir(parents=True, exist_ok=True)
    (pasta / "roteiro.json").write_text(json.dumps(rot, ensure_ascii=False, indent=2), encoding="utf-8")
    fundos = sorted({c["fundo"] for c in rot["cenas"] if c.get("fundo")})
    print(f"{len(rot['cenas'])} cenas · imagens necessárias: {', '.join(Path(f).name for f in fundos)}")
