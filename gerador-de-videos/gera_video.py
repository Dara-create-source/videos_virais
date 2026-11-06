#!/usr/bin/env python3
"""Gera um vídeo narrado (TikTok/Shorts/YouTube) a partir de um roteiro em JSON.

Uso:
    python3 gera_video.py projeto/roteiro.json [-o saida.mp4] [--rapido]

O roteiro descreve as cenas: fala, imagem de fundo, personagem, efeitos e sons.
Os caminhos de imagem e áudio são relativos à pasta do roteiro.
Veja README.md para o formato completo.
"""
import argparse
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

AQUI = Path(__file__).resolve().parent
FONTE_LEGENDA = AQUI / "fontes" / "Anton-Regular.ttf"
SR = 22050  # taxa de amostragem do áudio

FORMATOS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}


# --------------------------------------------------------------------------- #
# Texto para fala: números por extenso (pt-BR)
# --------------------------------------------------------------------------- #
_UNI = "zero um dois três quatro cinco seis sete oito nove dez onze doze treze catorze quinze dezesseis dezessete dezoito dezenove".split()
_DEZ = "_ _ vinte trinta quarenta cinquenta sessenta setenta oitenta noventa".split()
_CEN = "_ cento duzentos trezentos quatrocentos quinhentos seiscentos setecentos oitocentos novecentos".split()


def extenso(n: int) -> str:
    if n < 20:
        return _UNI[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _DEZ[d] + ("" if u == 0 else " e " + _UNI[u])
    if n == 100:
        return "cem"
    if n < 1000:
        c, r = divmod(n, 100)
        return _CEN[c] + ("" if r == 0 else " e " + extenso(r))
    if n < 1_000_000:
        m, r = divmod(n, 1000)
        pre = "mil" if m == 1 else extenso(m) + " mil"
        if r == 0:
            return pre
        return pre + (" e " if r < 100 or r % 100 == 0 else " ") + extenso(r)
    return str(n)


def texto_para_fala(t: str) -> str:
    t = re.sub(r"(\d{1,2})h(\d{2})", lambda m: f"{extenso(int(m[1]))} e {extenso(int(m[2]))}", t)
    t = re.sub(r"(\d+)\s?%", lambda m: f"{extenso(int(m[1]))} por cento", t)
    t = re.sub(r"\d+", lambda m: extenso(int(m[0])), t)
    return t


# --------------------------------------------------------------------------- #
# Áudio
# --------------------------------------------------------------------------- #
def ler_audio(caminho: Path) -> np.ndarray:
    """Lê qualquer arquivo de áudio como mono float32 em SR."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(caminho), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def gerar_voz(texto: str, cfg: dict, tmp: Path) -> np.ndarray:
    modelo = cfg.get("modelo_voz")
    if not modelo or not Path(modelo).exists():
        sys.exit(f"Modelo de voz não encontrado: {modelo}. Veja o README (seção Voz).")
    wav = tmp / f"voz_{abs(hash(texto))}.wav"
    subprocess.run(
        [sys.executable, "-m", "piper", "-m", str(modelo), "-f", str(wav),
         "--length-scale", str(cfg.get("velocidade_voz", 1.1))],
        input=texto.encode(), check=True, capture_output=True,
    )
    return ler_audio(wav)


def silencio(seg: float) -> np.ndarray:
    return np.zeros(int(SR * seg), dtype=np.float32)


def som_sintetico(nome: str) -> np.ndarray:
    """Pequena biblioteca de efeitos gerados por código (sem precisar baixar nada)."""
    rng = np.random.default_rng(7)
    if nome == "impacto":
        t = np.arange(int(SR * 1.6)) / SR
        f = 55 * np.exp(-t * 1.5) + 30
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2) * 0.9).astype(np.float32)
    if nome == "bip":
        t = np.arange(int(SR * 0.18)) / SR
        return (np.sin(2 * np.pi * 1100 * t) * 0.25 * np.minimum(1, (0.18 - t) * 40)).astype(np.float32)
    if nome == "chiado":
        n = int(SR * 1.2)
        env = np.minimum(1, np.arange(n) / (SR * 0.05)) * np.linspace(1, 0.2, n)
        return (rng.uniform(-1, 1, n) * 0.18 * env).astype(np.float32)
    if nome == "batida":  # batida de coração
        out = silencio(1.0)
        for ini in (0.0, 0.28):
            t = np.arange(int(SR * 0.25)) / SR
            b = np.sin(2 * np.pi * 50 * t) * np.exp(-t * 18) * 0.8
            i = int(ini * SR)
            out[i:i + len(b)] += b.astype(np.float32)
        return out
    if nome == "estalo":  # clique de lanterna / interruptor
        n = int(SR * 0.05)
        return (rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / (SR * 0.006)) * 0.6).astype(np.float32)
    if nome in ("buzina", "buzina_longe"):  # buzina de carro (dois tons quadrados)
        t = np.arange(int(SR * 0.7)) / SR
        x = np.sign(np.sin(2 * np.pi * 415 * t)) + np.sign(np.sin(2 * np.pi * 523 * t))
        env = np.minimum(1, t / 0.02) * np.minimum(1, (0.7 - t) / 0.05)
        x = (x * env * 0.16).astype(np.float32)
        if nome == "buzina_longe":  # abafada: filtro passa-baixa simples
            x = np.convolve(x, np.ones(40) / 40, mode="same").astype(np.float32) * 0.5
        return x
    if nome == "telefone":  # telefone antigo tocando (2 toques)
        out = silencio(3.2)
        for ini in (0.0, 1.8):
            t = np.arange(int(SR * 1.0)) / SR
            b = (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 480 * t)) * (np.sin(2 * np.pi * 20 * t) > 0) * 0.12
            i = int(ini * SR)
            out[i:i + len(b)] += b.astype(np.float32)
        return out
    if nome == "toc":  # batida seca na madeira/parede
        t = np.arange(int(SR * 0.18)) / SR
        x = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 45) + rng.uniform(-1, 1, len(t)) * np.exp(-t * 120) * 0.4
        return (x * 0.7).astype(np.float32)
    if nome == "sino":  # sininho de porta
        t = np.arange(int(SR * 1.5)) / SR
        x = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1870, 1), (2730, 0.6), (4100, 0.3)))
        return (x * np.exp(-t * 4) * 0.15).astype(np.float32)
    sys.exit(f"Som desconhecido: {nome}")


def drone(segundos: float) -> np.ndarray:
    """Clima de fundo grave e baixo."""
    t = np.arange(int(SR * segundos)) / SR
    x = (np.sin(2 * np.pi * 43 * t) + 0.6 * np.sin(2 * np.pi * 43.7 * t) + 0.3 * np.sin(2 * np.pi * 86.3 * t))
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)
    return (x * lfo * 0.05).astype(np.float32)


def mixar(base: np.ndarray, som: np.ndarray, inicio: float, vol: float = 1.0):
    i = int(inicio * SR)
    if i >= len(base):
        return
    j = min(len(base), i + len(som))
    base[i:j] += som[: j - i] * vol


def salvar_wav(x: np.ndarray, caminho: Path):
    x = np.clip(x, -1, 1)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


# --------------------------------------------------------------------------- #
# Imagens
# --------------------------------------------------------------------------- #
def tirar_fundo_branco(img: Image.Image, tolerancia: int = 40) -> Image.Image:
    """Deixa transparente o fundo branco ligado às bordas (para personagens em fundo branco)."""
    img = img.convert("RGBA")
    if img.getextrema()[3][0] < 250:  # já tem transparência
        return img
    rgb = img.convert("RGB")
    marca = (255, 0, 255)
    w, h = rgb.size
    for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1)]:
        if sum(rgb.getpixel(p)) > 3 * (255 - tolerancia):
            ImageDraw.floodfill(rgb, p, marca, thresh=tolerancia)
    a = np.array(rgb)
    mascara = np.all(a == marca, axis=-1)
    alfa = np.where(mascara, 0, 255).astype(np.uint8)
    alfa = Image.fromarray(alfa).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    img.putalpha(alfa)
    return img.crop(img.getbbox())


def cobrir(img: Image.Image, W: int, H: int, folga: float = 1.12) -> Image.Image:
    """Redimensiona para cobrir a tela com folga para zoom/tremor."""
    img = img.convert("RGB")
    esc = max(W / img.width, H / img.height) * folga
    return img.resize((int(img.width * esc), int(img.height * esc)), Image.LANCZOS)


def vinheta(W: int, H: int, forca: float) -> Image.Image:
    y, x = np.ogrid[:H, :W]
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    a = np.clip((d - 0.35) / 0.65, 0, 1) ** 1.6 * 255 * forca
    v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    v.putalpha(Image.fromarray(a.astype(np.uint8)))
    return v


_cache_linhas = {}


def _linhas_cctv(W: int, H: int) -> Image.Image:
    if (W, H) not in _cache_linhas:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for y in range(0, H, 6):
            d.line((0, y, W, y), fill=(0, 0, 0, 70), width=2)
        _cache_linhas[(W, H)] = img
    return _cache_linhas[(W, H)]


_cache_fontes = {}


def fonte(tam: int):
    if tam not in _cache_fontes:
        try:
            _cache_fontes[tam] = ImageFont.truetype(str(FONTE_LEGENDA), tam)
        except OSError:
            _cache_fontes[tam] = ImageFont.truetype("DejaVuSans-Bold.ttf", tam)
    return _cache_fontes[tam]


def texto_contorno(draw, xy, txt, tam, cor=(255, 255, 255), contorno=(0, 0, 0), ancora="mm", larg=None):
    f = fonte(tam)
    draw.text(xy, txt, font=f, fill=cor, anchor=ancora,
              stroke_width=larg or max(3, tam // 12), stroke_fill=contorno)



CHAMADAS = AQUI / "chamadas"
TEXTO_FAIXA = {"serie": "CURTE E SEGUE PRO PRÓXIMO DIA", "avulso": "CURTE E SEGUE PRA MAIS HISTÓRIAS"}


def coracao(d, cx, cy, r, cor=(235, 45, 70)):
    """Coração desenhado com dois círculos e um triângulo."""
    d.ellipse((cx - r, cy - r * 0.6, cx, cy + r * 0.4), fill=cor)
    d.ellipse((cx, cy - r * 0.6, cx + r, cy + r * 0.4), fill=cor)
    d.polygon([(cx - r * 0.97, cy), (cx + r * 0.97, cy), (cx, cy + r * 1.1)], fill=cor)


def faixa_chamada(canvas, d, W, H, tl, dur, texto):
    """Faixa que entra pela lateral no meio do vídeo (tl = tempo desde que apareceu)."""
    entra = min(1, tl / 0.35)
    sai = min(1, max(0, (dur - tl) / 0.35))
    x_off = (1 - entra) * W - (1 - sai) * W
    tam = int(W * 0.05)
    f = fonte(tam)
    larg = d.textlength(texto, font=f) + tam * 2.4
    alt = tam * 1.9
    x0 = (W - larg) / 2 + x_off
    y0 = H * 0.115
    d.rounded_rectangle((x0, y0, x0 + larg, y0 + alt), radius=alt / 2, fill=(15, 15, 20, 225), outline=(235, 45, 70, 255), width=max(2, W // 270))
    pulso = 1 + 0.12 * abs(math.sin(tl * 6))
    coracao(d, x0 + tam * 1.1, y0 + alt / 2 - tam * 0.1, tam * 0.45 * pulso)
    d.text((x0 + tam * 1.9, y0 + alt / 2), texto, font=f, fill=(255, 255, 255), anchor="lm")


def cartao_chamada(d, W, H, t):
    """Botões de curtir e seguir no fim do vídeo."""
    pulso = 1 + 0.1 * abs(math.sin(t * 5))
    coracao(d, W * 0.33, H * 0.62, W * 0.07 * pulso)
    texto_contorno(d, (W * 0.33, H * 0.71), "CURTIR", int(W * 0.05))
    bw, bh = W * 0.30, W * 0.11
    bx, by = W * 0.67 - bw / 2, H * 0.62 - bh / 2
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=bh / 4, fill=(235, 45, 70))
    d.text((W * 0.67, H * 0.62), "SEGUIR", font=fonte(int(W * 0.055)), fill=(255, 255, 255), anchor="mm")


def blocos_legenda(texto: str, max_palavras: int):
    palavras = texto.replace("[pausa]", " ").split()
    return [" ".join(palavras[i:i + max_palavras]) for i in range(0, len(palavras), max_palavras)]


# --------------------------------------------------------------------------- #
# Montagem
# --------------------------------------------------------------------------- #
def preparar_cenas(rot: dict, pasta: Path, cfg: dict, tmp: Path):
    """Gera a voz de cada cena e calcula tempos de cena e de legendas."""
    cenas, trilha, t = [], [], 0.0
    pausa_padrao = cfg.get("pausa", 0.8)
    for i, c in enumerate(rot["cenas"], 1):
        print(f"  voz da cena {i}/{len(rot['cenas'])}…", flush=True)
        pedacos = re.split(r"\[pausa\]", c.get("fala", c.get("narracao", "")))
        legendas, audio = [], [silencio(c.get("respiro_antes", 0.15))]
        cursor = len(audio[0]) / SR
        audio_auto = None
        if cfg.get("pasta_audio"):
            for ext in ("mp3", "wav", "m4a", "ogg"):
                cand = pasta / cfg["pasta_audio"] / f"cena{i:02d}.{ext}"
                if cand.exists():
                    audio_auto = cand
                    break
        if c.get("audio") or audio_auto:  # áudio gravado (ElevenLabs, celular…)
            a = ler_audio(pasta / c["audio"] if c.get("audio") else audio_auto)
            audio.append(a)
            dur_fala = len(a) / SR
            blocos = blocos_legenda(c.get("narracao", ""), cfg["palavras_legenda"])
            tot = sum(len(b) for b in blocos) or 1
            for b in blocos:
                d = dur_fala * len(b) / tot
                legendas.append((cursor, cursor + d, b))
                cursor += d
        else:
            leg_pedacos = re.split(r"\[pausa\]", c.get("narracao", c.get("fala", "")))
            for k, pedaco in enumerate(pedacos):
                if pedaco.strip():
                    a = gerar_voz(texto_para_fala(pedaco.strip()), cfg, tmp)
                    audio.append(a)
                    dur = len(a) / SR
                    blocos = blocos_legenda(leg_pedacos[k] if k < len(leg_pedacos) else pedaco,
                                            cfg["palavras_legenda"])
                    tot = sum(len(b) for b in blocos) or 1
                    c0 = cursor
                    for b in blocos:
                        d = dur * len(b) / tot
                        legendas.append((c0, c0 + d, b))
                        c0 += d
                    cursor += dur
                if k < len(pedacos) - 1:
                    audio.append(silencio(pausa_padrao))
                    cursor += pausa_padrao
        depois = c.get("pausa_depois", 0.25)
        audio.append(silencio(depois))
        a = np.concatenate(audio)
        dur = len(a) / SR
        trilha.append(a)
        cenas.append({**c, "inicio": t, "dur": dur,
                      "legendas": [(t + a0, t + a1, txt) for a0, a1, txt in legendas]})
        t += dur
    return cenas, np.concatenate(trilha), t


def carregar_imagens(cenas, pasta: Path, W, H, cfg):
    cache = {}

    def abrir(nome, tipo, brilho=1.0):
        chave = (nome, tipo, brilho)
        if chave not in cache:
            caminho = pasta / nome
            if not caminho.exists():
                sys.exit(f"Imagem não encontrada: {caminho}")
            img = Image.open(caminho)
            if tipo == "fundo":
                img = cobrir(img, W, H)
                if brilho != 1.0:  # clareia cenários muito escuros
                    img = ImageEnhance.Brightness(img).enhance(brilho)
                    img = ImageEnhance.Contrast(img).enhance(1.08)
                cache[chave] = img
            else:
                cache[chave] = tirar_fundo_branco(img)
        return cache[chave]

    for c in cenas:
        b = c.get("brilho", cfg.get("brilho_fundo", 1.0))
        c["_fundo"] = abrir(c["fundo"], "fundo", b) if c.get("fundo") else None
        b2 = c.get("brilho_depois", b)
        c["_fundo2"] = abrir(c["fundo_depois"], "fundo", b2) if c.get("fundo_depois") else None
        p = c.get("personagem")
        c["_pers"] = abrir(p, "pers") if p else None
        p2 = c.get("personagem_depois")
        c["_pers2"] = abrir(p2, "pers") if p2 else None


def zoom_da_cena(efeito: str, t: float, dur: float) -> float:
    if efeito == "zoom_lento":
        return 1.0 + 0.12 * (t / max(dur, 0.01))
    if efeito == "zoom_rapido":
        return 1.0 + 0.22 * min(1, t / 0.35) ** 0.5 + 0.03 * (t / max(dur, 0.01))
    if efeito == "afastar":
        return 1.15 - 0.15 * (t / max(dur, 0.01))
    return 1.0 + 0.03 * (t / max(dur, 0.01))  # leve movimento sempre, para não parecer foto parada


def tremor(efeito: str, t: float, rng: random.Random):
    forte = efeito == "tremor" or (efeito == "zoom_rapido" and t < 0.5)
    if not forte:
        return 0, 0
    amp = 18 if efeito == "tremor" else 22 * (1 - t / 0.5)
    return rng.uniform(-amp, amp), rng.uniform(-amp, amp)


def quadro(c, t_global, W, H, vin, rng, cfg):
    t = t_global - c["inicio"]
    dur = c["dur"]
    efeito = c.get("efeito", "nenhum")

    # fundo (com troca no meio da cena, se houver)
    fundo = c["_fundo"]
    troca = c.get("troca_em")
    if c["_fundo2"] is not None and t >= (troca if troca is not None else dur / 2):
        fundo = c["_fundo2"]
    if fundo is None:
        canvas = Image.new("RGB", (W, H), (8, 8, 12))
    else:
        z = zoom_da_cena(efeito, t, dur)
        dx, dy = tremor(efeito, t, rng)
        # o fundo foi ampliado 1.12x além do necessário: 1 pixel do fundo = 1 pixel da tela no zoom 1,
        # e a sobra nas bordas serve para o zoom e o tremor
        bw, bh = W / z, H / z
        fx, fy = c.get("foco", [0.5, 0.5])  # ponto da imagem que fica no centro da tela
        cx = min(max(fundo.width * fx + dx, bw / 2), fundo.width - bw / 2)
        cy = min(max(fundo.height * fy + dy, bh / 2), fundo.height - bh / 2)
        caixa = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
        canvas = fundo.resize((W, H), Image.BILINEAR, box=caixa)

    # personagem
    pers = c["_pers"]
    tp = c.get("troca_personagem_em")
    if c["_pers2"] is not None and t >= (tp if tp is not None else dur / 2):
        pers = c["_pers2"]
    if pers is not None:
        alt = int(H * c.get("tamanho", 0.42))
        esc = alt / pers.height
        respira = 1 + 0.012 * math.sin(t * 2.4)
        pw, ph = int(pers.width * esc), int(pers.height * esc * respira)
        p = pers.resize((pw, ph), Image.BILINEAR)
        pos = c.get("posicao", "centro")
        x = {"esquerda": W * 0.28, "direita": W * 0.72}.get(pos, W / 2) - pw / 2
        base_y = H * c.get("chao", 0.80)
        y = base_y - ph
        if c.get("personagem_efeito") == "tremer":
            x += rng.uniform(-4, 4)
            y += rng.uniform(-3, 3)
        if c.get("personagem_efeito") == "entrar":
            x += (1 - min(1, t / 0.6)) * W
        canvas.paste(p, (int(x), int(y)), p)

    # piscar (luz falhando)
    if efeito == "piscar" and rng.random() < 0.18:
        canvas = ImageEnhance.Brightness(canvas).enhance(rng.uniform(0.15, 0.5))

    # glitch: faixas horizontais deslocadas em alguns quadros
    if c.get("glitch") and rng.random() < 0.3:
        g = canvas.copy()
        for _ in range(rng.randint(3, 7)):
            y0 = rng.randint(0, H - 40)
            hh = rng.randint(10, 80)
            faixa = canvas.crop((0, y0, W, y0 + hh))
            g.paste(faixa, (rng.randint(-60, 60), y0))
        canvas = g

    # câmera de segurança: preto e branco, linhas, chiado, REC e horário
    if c.get("filtro") == "cctv" and t >= c.get("filtro_em", 0):
        cinza = ImageEnhance.Contrast(canvas.convert("L")).enhance(1.3)
        ruido = Image.effect_noise((W // 4, H // 4), 40).resize((W, H))
        cinza = Image.blend(cinza, ruido, 0.12)
        canvas = Image.merge("RGB", (cinza, cinza.point(lambda v: min(255, v + 8)), cinza))
        linhas = _linhas_cctv(W, H)
        canvas = canvas.convert("RGBA")
        canvas.alpha_composite(linhas)
        dd = ImageDraw.Draw(canvas)
        tam = int(W * 0.045)
        if int(t * 2) % 2 == 0:
            dd.ellipse((40, H * 0.11, 40 + tam * 0.7, H * 0.11 + tam * 0.7), fill=(230, 40, 40))
        dd.text((40 + tam, H * 0.11 - tam * 0.1), "REC  CAM 04", font=fonte(tam), fill=(230, 230, 230))
        relogio = c.get("relogio", "03:17")
        seg = int(t) % 60
        dd.text((W - 40, H * 0.11 - tam * 0.1), f"{relogio}:{seg:02d}", font=fonte(tam), fill=(230, 230, 230), anchor="ra")
        canvas = canvas.convert("RGB")

    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(vin)
    d = ImageDraw.Draw(canvas)

    # texto na tela (ex.: "20%", "DIA 1"); pode trocar no meio da cena
    tt_atual = c.get("texto_tela")
    if c.get("texto_tela_depois") and t >= c.get("troca_texto_em", dur / 2):
        tt_atual = c["texto_tela_depois"]
    if tt_atual:
        tt = tt_atual
        if not (c.get("texto_piscando") and int(t * 3) % 2):
            tam = int(W * c.get("texto_tela_tamanho", 0.11))
            linhas = [tt]
            if d.textlength(tt, font=fonte(tam)) > W * 0.86 and " " in tt:  # quebra em 2 linhas
                p = tt.split()
                meio = len(p) // 2
                linhas = [" ".join(p[:meio]), " ".join(p[meio:])]
            y0 = H * c.get("texto_tela_altura", 0.25) - (len(linhas) - 1) * tam * 0.6
            for i, linha in enumerate(linhas):
                texto_contorno(d, (W / 2, y0 + i * tam * 1.2), linha, tam,
                               cor=tuple(c.get("texto_tela_cor", [255, 255, 255])))

    # contador fixo no canto (estilo "50" do exemplo)
    if cfg.get("contador"):
        cont = cfg["contador"]
        f = fonte(int(W * 0.07))
        txt = c.get("contador", cont.get("valor", ""))
        if txt:
            caixa = d.textbbox((0, 0), txt, font=f)
            bw, bh = caixa[2] - caixa[0] + 60, caixa[3] - caixa[1] + 40
            d.rounded_rectangle((40, 40, 40 + bw, 40 + bh), radius=18, fill=(15, 20, 30, 230), outline=(60, 70, 90, 255), width=4)
            d.text((40 + bw / 2, 40 + bh / 2), txt, font=f, fill=tuple(cont.get("cor", [110, 230, 140])), anchor="mm")

    # legendas
    if cfg.get("legendas", True):
        for a0, a1, txt in c["legendas"]:
            if a0 <= t_global < a1:
                texto_contorno(d, (W / 2, H * c.get("altura_legenda", cfg.get("altura_legenda", 0.36))), txt.upper(),
                               int(W * cfg.get("tamanho_legenda", 0.085)), larg=max(6, int(W * 0.008)))
                break

    # chamada para curtir e seguir
    if cfg.get("chamada") and not c.get("_cartao"):
        ini = cfg["_total_historia"] * cfg.get("chamada_meio", 0.45)
        if ini <= t_global < ini + 3.5:
            faixa_chamada(canvas, d, W, H, t_global - ini, 3.5, cfg.get("chamada_texto", TEXTO_FAIXA[cfg["chamada"]]))
    if c.get("_cartao"):
        cartao_chamada(d, W, H, t)

    # escurecer até o preto no fim da cena
    if c.get("final_preto"):
        f = max(0, (t - (dur - 0.7)) / 0.7)
        if f > 0:
            canvas.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * min(1, f)))))

    return canvas.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("-o", "--saida")
    ap.add_argument("--rapido", action="store_true", help="prévia em baixa resolução")
    ap.add_argument("--drive", action="store_true", help="envia o vídeo pronto para a pasta Videos virais no Drive")
    args = ap.parse_args()

    caminho = Path(args.roteiro).resolve()
    pasta = caminho.parent
    rot = json.loads(caminho.read_text(encoding="utf-8"))
    cfg = {"palavras_legenda": 3, **rot.get("config", {})}
    if cfg.get("modelo_voz") and not Path(cfg["modelo_voz"]).is_absolute():
        cfg["modelo_voz"] = str((pasta / cfg["modelo_voz"]).resolve())

    W, H = FORMATOS[cfg.get("formato", "9:16")]
    fps = cfg.get("fps", 30)
    if args.rapido:
        W, H, fps = W // 3, H // 3, 15
    saida = Path(args.saida or pasta / (caminho.stem + ".mp4")).resolve()

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("1/3 Gerando narração…", flush=True)
        if cfg.get("chamada"):
            ult = rot["cenas"][-1]
            textos = json.loads((CHAMADAS / "textos.json").read_text(encoding="utf-8"))
            rot["cenas"].append({
                "narracao": textos[cfg["chamada"]], "audio": str(CHAMADAS / f"{cfg['chamada']}.mp3"),
                "fundo": ult.get("fundo"), "foco": ult.get("foco", [0.5, 0.5]), "brilho": 0.45,
                "personagem": cfg.get("chamada_personagem"), "posicao": "centro", "tamanho": 0.30, "chao": 0.50,
                "efeito": "zoom_lento", "_cartao": True, "pausa_depois": 0.6, "altura_legenda": 0.80,
                "respiro_antes": 0.4,
            })
        cenas, voz, total = preparar_cenas(rot, pasta, cfg, tmp)
        cfg["_total_historia"] = cenas[-2]["inicio"] + cenas[-2]["dur"] if cfg.get("chamada") else total

        # mixagem: voz + clima + efeitos + música
        mix = voz * cfg.get("volume_voz", 1.0)
        if cfg.get("clima", True):
            mixar(mix, drone(total), 0, 1.0)
        if cfg.get("musica"):
            m = ler_audio(pasta / cfg["musica"])
            m = np.tile(m, int(np.ceil(len(mix) / len(m))))[: len(mix)]
            mixar(mix, m, 0, cfg.get("volume_musica", 0.12))
        for c in cenas:
            for s in c.get("sons", []):
                nome, quando = (s, 0.0) if isinstance(s, str) else (s["som"], s.get("em", 0.0))
                vol = 1.0 if isinstance(s, str) else s.get("volume", 1.0)
                som = ler_audio(pasta / nome) if "." in nome else som_sintetico(nome)
                mixar(mix, som, c["inicio"] + quando, vol)
        mix /= max(1.0, np.abs(mix).max() / 0.95)
        wav = tmp / "audio.wav"
        salvar_wav(mix, wav)

        print(f"2/3 Desenhando {int(total * fps)} quadros ({total:.1f}s)…", flush=True)
        carregar_imagens(cenas, pasta, W, H, cfg)
        vin = vinheta(W, H, cfg.get("vinheta", 0.6))
        rng = random.Random(42)
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(fps), "-i", "-", "-i", str(wav),
             "-c:v", "libx264", "-preset", "veryfast" if args.rapido else "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-c:a", "aac", "-b:a", "160k", "-shortest",
             "-movflags", "+faststart", str(saida)],
            stdin=subprocess.PIPE,
        )
        n = int(total * fps)
        ci = 0
        for k in range(n):
            t = k / fps
            while ci < len(cenas) - 1 and t >= cenas[ci + 1]["inicio"]:
                ci += 1
            ff.stdin.write(quadro(cenas[ci], t, W, H, vin, rng, cfg).tobytes())
            if k % (fps * 10) == 0:
                print(f"   {t:5.1f}s / {total:.1f}s", flush=True)
        ff.stdin.close()
        ff.wait()
        print(f"3/3 Pronto: {saida}")

        # resumo de tempos (útil para conferir o ritmo)
        for i, c in enumerate(cenas, 1):
            print(f"   cena {i:2d}: {c['inicio']:5.1f}s – {c['inicio'] + c['dur']:5.1f}s")

    if args.drive and not args.rapido:
        sys.path.insert(0, str(AQUI))
        from enviar_drive import enviar
        print("Enviando para o Drive (Videos virais)…", flush=True)
        enviar(saida)


if __name__ == "__main__":
    main()
