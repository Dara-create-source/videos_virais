#!/usr/bin/env python3
"""Desenha imagens PROVISÓRIAS para testar o gerador sem as artes de verdade.

Troque estes arquivos pelas imagens geradas no ChatGPT (mesmos nomes) e rode o
gerador de novo: o vídeo sai com as artes reais.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

P = Path(__file__).resolve().parent / "imagens"
P.mkdir(exist_ok=True)
W, H = 1080, 1920
OUT = (12, 12, 16)  # cor do contorno
rnd = random.Random(3)


def ceu(cor_topo, cor_base):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        f = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * f) for a, b in zip(cor_topo, cor_base)))
    return img, d


def predios(d, acesos, base=1250):
    x = -20
    while x < W:
        w = rnd.randint(110, 200)
        h = rnd.randint(250, 650)
        d.rectangle((x, base - h, x + w, base), fill=(28, 32, 48), outline=OUT, width=5)
        for wy in range(base - h + 30, base - 40, 60):
            for wx in range(x + 20, x + w - 30, 45):
                cor = (255, 214, 102) if acesos and rnd.random() < 0.7 else (22, 25, 38)
                d.rectangle((wx, wy, wx + 22, wy + 30), fill=cor)
        x += w + rnd.randint(-10, 15)


def chao(d, y=1250, cor=(30, 30, 36)):
    d.rectangle((0, y, W, H), fill=cor, outline=OUT, width=5)


def posto(d, aceso, y=1250):
    # cobertura
    d.rectangle((140, y - 620, 940, y - 540), fill=(200, 40, 40) if aceso else (70, 30, 30), outline=OUT, width=6)
    for px in (220, 840):
        d.rectangle((px - 18, y - 540, px + 18, y), fill=(90, 90, 100), outline=OUT, width=5)
    # bombas
    for i, px in enumerate((330, 470, 610, 750)):
        d.rounded_rectangle((px - 40, y - 230, px + 40, y), radius=10,
                            fill=(170, 170, 180) if aceso else (60, 60, 70), outline=OUT, width=5)
        d.rectangle((px - 25, y - 205, px + 25, y - 165),
                    fill=(110, 230, 140) if aceso else (20, 30, 25), outline=OUT, width=3)
    if aceso:
        luz = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(luz).polygon([(160, y - 540), (920, y - 540), (1080, y), (0, y)], fill=(255, 240, 180, 60))
        return luz
    return None


def salvar(img, nome):
    img.save(P / nome)
    print("ok", nome)


# 1. cidade acesa e apagada (vista do posto)
for aceso, nome in ((True, "cidade_acesa.png"), (False, "cidade_apagada.png")):
    img, d = ceu((10, 14, 35), (40, 45, 80) if aceso else (14, 16, 28))
    d.ellipse((780, 220, 900, 340), fill=(230, 230, 210), outline=OUT, width=5)
    predios(d, aceso, base=1150)
    chao(d, 1150)
    rnd.seed(3)
    luz = posto(d, aceso, y=1700)
    if luz:
        img = Image.alpha_composite(img.convert("RGBA"), luz).convert("RGB")
    salvar(img, nome)

# 2. posto apagado (perto)
img, d = ceu((8, 10, 24), (20, 22, 36))
d.ellipse((120, 200, 230, 310), fill=(200, 200, 185), outline=OUT, width=5)
chao(d, 1350)
posto(d, False, y=1350)
salvar(img, "posto_apagado.png")

# 3. estrada escura
img, d = ceu((5, 6, 14), (14, 15, 24))
d.polygon([(470, 900), (610, 900), (1080, 1920), (0, 1920)], fill=(26, 26, 32), outline=OUT)
for i in range(8):
    y0 = 920 + i * i * 18
    y1 = y0 + 8 + i * 6
    d.rectangle((535 - i * 2, y0, 545 + i * 2, y1), fill=(200, 190, 120))
nevoa = Image.new("L", (W, H), 0)
ImageDraw.Draw(nevoa).rectangle((0, 820, W, 1050), fill=170)
nevoa = nevoa.filter(ImageFilter.GaussianBlur(80))
img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, nevoa)
salvar(img, "estrada_escura.png")

# 4. loja escura
img, d = ceu((14, 16, 22), (20, 22, 30))
for yy in (420, 700, 980):  # prateleiras
    d.rectangle((60, yy, 1020, yy + 24), fill=(50, 45, 40), outline=OUT, width=4)
    for xx in range(80, 1000, 70):
        d.rectangle((xx, yy - rnd.randint(60, 120), xx + 45, yy), fill=(rnd.randint(40, 80), 40, 50), outline=OUT, width=3)
d.rectangle((0, 1350, W, 1600), fill=(55, 45, 38), outline=OUT, width=6)  # balcão
d.rectangle((0, 1600, W, H), fill=(24, 24, 28))
salvar(img, "loja_escura.png")

# 5. porta de vidro com a criatura na beirada da luz
img, d = ceu((6, 7, 12), (10, 10, 16))
d.rectangle((200, 300, 880, 1650), fill=(18, 22, 34), outline=(70, 70, 80), width=14)
d.line((540, 300, 540, 1650), fill=(70, 70, 80), width=10)
luz = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(luz).ellipse((80, 650, 620, 1900), fill=(255, 220, 120, 95))
luz = luz.filter(ImageFilter.GaussianBlur(40))
img = Image.alpha_composite(img.convert("RGBA"), luz).convert("RGB")
d = ImageDraw.Draw(img)
# silhueta alta e magra
cx = 700
d.ellipse((cx - 45, 420, cx + 45, 530), fill=(3, 3, 5))
d.line((cx, 530, cx, 1150), fill=(3, 3, 5), width=34)
for s in (-1, 1):
    d.line((cx, 600, cx + s * 70, 900, cx + s * 85, 1250), fill=(3, 3, 5), width=16, joint="curve")
    d.line((cx, 1150, cx + s * 55, 1640), fill=(3, 3, 5), width=20)
d.ellipse((cx - 22, 465, cx - 8, 475), fill=(235, 235, 235))
d.ellipse((cx + 8, 465, cx + 22, 475), fill=(235, 235, 235))
salvar(img, "porta_criatura.png")

# 6. bateria 20%
img, d = ceu((8, 8, 12), (8, 8, 12))
d.rounded_rectangle((240, 760, 800, 1060), radius=30, outline=(220, 220, 220), width=18)
d.rectangle((800, 860, 850, 960), fill=(220, 220, 220))
d.rounded_rectangle((270, 790, 370, 1030), radius=12, fill=(230, 50, 50))
salvar(img, "bateria.png")

# 7. amanhecer no posto
img, d = ceu((90, 70, 120), (250, 170, 110))
d.ellipse((440, 1050, 640, 1250), fill=(255, 220, 150))
chao(d, 1350, cor=(60, 55, 60))
posto(d, False, y=1350)
salvar(img, "amanhecer.png")


# ---------------- Lucas (cabeção + corpo de palito) ----------------
def lucas(nome, olhos="normal", pose="pe", lanterna=False, celular=False):
    S = 900
    img = Image.new("RGB", (S, S + 400), "white")
    d = ImageDraw.Draw(img)
    cx, hy, r = S // 2, 330, 200  # centro da cabeça
    pele = (240, 210, 180)
    corpo_y = hy + r - 10
    preto = OUT

    if pose == "sentado":
        quadril = (cx, corpo_y + 260)
        d.line((cx, corpo_y, *quadril), fill=preto, width=12)
        d.line((*quadril, cx + 150, quadril[1] - 90, cx + 170, quadril[1] + 120), fill=preto, width=12, joint="curve")
        d.line((*quadril, cx + 110, quadril[1] - 70, cx + 130, quadril[1] + 130), fill=preto, width=12, joint="curve")
        bracos = [((cx, corpo_y + 70), (cx + 170, corpo_y + 140))]
    else:
        quadril = (cx, corpo_y + 330)
        d.line((cx, corpo_y, *quadril), fill=preto, width=12)
        abert = 70 if olhos == "medo" else 55
        for s in (-1, 1):
            d.line((*quadril, cx + s * abert, quadril[1] + 300), fill=preto, width=12)
            d.ellipse((cx + s * abert - 22, quadril[1] + 290, cx + s * abert + 22, quadril[1] + 316), fill="white", outline=preto, width=5)
        if lanterna or celular:
            bracos = [((cx, corpo_y + 70), (cx + 190, corpo_y + 120)), ((cx, corpo_y + 70), (cx + 170, corpo_y + 150))]
        elif olhos == "medo":
            bracos = [((cx, corpo_y + 70), (cx - 170, corpo_y - 10)), ((cx, corpo_y + 70), (cx + 170, corpo_y - 10))]
        else:
            bracos = [((cx, corpo_y + 70), (cx - 110, corpo_y + 260)), ((cx, corpo_y + 70), (cx + 110, corpo_y + 260))]

    # camisa cinza
    d.rounded_rectangle((cx - 70, corpo_y - 5, cx + 70, corpo_y + 200), radius=18, fill=(120, 120, 128), outline=preto, width=6)
    d.rectangle((cx + 15, corpo_y + 40, cx + 55, corpo_y + 62), fill="white", outline=preto, width=3)
    for a, b in bracos:
        d.line((*a, *b), fill=preto, width=12)
        d.ellipse((b[0] - 18, b[1] - 18, b[0] + 18, b[1] + 18), fill="white", outline=preto, width=5)
    if lanterna:
        bx, by = bracos[0][1]
        d.rounded_rectangle((bx - 10, by - 22, bx + 90, by + 22), radius=8, fill=(60, 60, 70), outline=preto, width=5)
        d.rectangle((bx + 82, by - 28, bx + 100, by + 28), fill=(255, 225, 120), outline=preto, width=4)
    if celular:
        bx, by = bracos[0][1]
        d.rounded_rectangle((bx - 25, by - 60, bx + 25, by + 20), radius=8, fill=(180, 220, 255), outline=preto, width=5)

    # cabeça
    d.ellipse((cx - r, hy - r, cx + r, hy + r), fill=pele, outline=preto, width=8)
    # cabelo espetado
    for a in range(200, 341, 18):
        ang = math.radians(a)
        x0, y0 = cx + math.cos(ang) * r * 0.95, hy + math.sin(ang) * r * 0.95
        x1, y1 = cx + math.cos(ang) * (r + 55), hy + math.sin(ang) * (r + 55) - 10
        d.polygon([(x0 - 22, y0), (x1, y1), (x0 + 22, y0 + 5)], fill=(20, 20, 24), outline=preto)
    # boné vermelho
    d.chord((cx - r + 10, hy - r - 10, cx + r - 10, hy + r - 150), 180, 360, fill=(220, 35, 40), outline=preto, width=8)
    d.rounded_rectangle((cx - 40, hy - 105, cx + r + 70, hy - 75), radius=14, fill=(190, 25, 30), outline=preto, width=7)
    # rosto
    oy = hy + 20
    if olhos == "medo":
        for s in (-1, 1):
            d.ellipse((cx + s * 70 - 38, oy - 38, cx + s * 70 + 38, oy + 38), fill="white", outline=preto, width=6)
            d.ellipse((cx + s * 70 - 9, oy - 9, cx + s * 70 + 9, oy + 9), fill=preto)
            d.line((cx + s * 40, oy - 75, cx + s * 105, oy - 95), fill=preto, width=10)
        d.ellipse((cx - 22, oy + 75, cx + 22, oy + 115), fill=(60, 20, 20), outline=preto, width=5)
    elif olhos == "sorriso":
        for s in (-1, 1):
            d.ellipse((cx + s * 70 - 12, oy - 12, cx + s * 70 + 12, oy + 12), fill=preto)
        d.arc((cx - 110, oy + 10, cx + 110, oy + 130), 10, 170, fill=preto, width=8)
    else:
        for s in (-1, 1):
            d.ellipse((cx + s * 70 - 14, oy - 14, cx + s * 70 + 14, oy + 14), fill=preto)
            d.line((cx + s * 40, oy - 60, cx + s * 100, oy - 60), fill=preto, width=10)
        d.line((cx - 30, oy + 90, cx + 30, oy + 90), fill=preto, width=7)
    img.save(P / nome)
    print("ok", nome)


lucas("lucas_neutro.png")
lucas("lucas_medo.png", olhos="medo")
lucas("lucas_celular.png", celular=True)
lucas("lucas_lanterna.png", olhos="medo", lanterna=True)
lucas("lucas_sentado.png", olhos="medo", pose="sentado", lanterna=True)
