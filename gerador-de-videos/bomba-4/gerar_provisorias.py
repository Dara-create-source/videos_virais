#!/usr/bin/env python3
"""Imagens PROVISÓRIAS da bomba 4. Troque pelas artes reais com os mesmos nomes."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

P = Path(__file__).resolve().parent / "imagens"
W, H = 1080, 1920
OUT = (10, 10, 14)
F = ImageFont.truetype(str(Path(__file__).resolve().parent.parent / "fontes" / "Anton-Regular.ttf"), 70)


def ceu():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        f = y / H
        d.line([(0, y), (W, y)], fill=(int(8 + 12 * f), int(10 + 12 * f), int(24 + 18 * f)))
    d.ellipse((800, 180, 940, 320), fill=(215, 215, 200), outline=OUT, width=5)
    return img, d


def posto(d, chao=1350, separar=True):
    d.rectangle((0, chao, W, H), fill=(28, 28, 34), outline=OUT, width=5)
    d.rectangle((60, chao - 640, 1020, chao - 560), fill=(150, 35, 35), outline=OUT, width=6)
    for px in (140, 940):
        d.rectangle((px - 18, chao - 560, px + 18, chao), fill=(80, 80, 90), outline=OUT, width=5)
    xs = (260, 420, 580, 860 if separar else 740)
    for i, px in enumerate(xs, 1):
        d.rounded_rectangle((px - 45, chao - 260, px + 45, chao), radius=10, fill=(140, 40, 40), outline=OUT, width=5)
        d.rectangle((px - 28, chao - 230, px + 28, chao - 190), fill=(20, 40, 28), outline=OUT, width=3)
        d.text((px, chao - 120), str(i), font=F, fill=(230, 230, 230), anchor="mm", stroke_width=4, stroke_fill=OUT)
    return xs[-1]


def luz(img, caixa, cor=(255, 240, 190, 70), blur=40):
    l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(l).polygon(caixa, fill=cor)
    return Image.alpha_composite(img.convert("RGBA"), l.filter(ImageFilter.GaussianBlur(blur))).convert("RGB")


def carro(d, x, chao):
    d.rounded_rectangle((x - 260, chao - 260, x + 200, chao - 80), radius=40, fill=(160, 165, 175), outline=OUT, width=7)
    d.rounded_rectangle((x - 180, chao - 360, x + 110, chao - 250), radius=30, fill=(150, 155, 165), outline=OUT, width=7)
    d.rectangle((x - 160, chao - 340, x + 90, chao - 260), fill=(15, 18, 24), outline=OUT, width=4)
    for wx in (x - 170, x + 110):
        d.ellipse((wx - 55, chao - 140, wx + 55, chao - 30), fill=(20, 20, 24), outline=OUT, width=6)
    d.ellipse((x + 160, chao - 230, x + 210, chao - 180), fill=(255, 250, 210), outline=OUT, width=4)


# posto à noite com a bomba 4 em destaque
img, d = ceu()
x4 = posto(d)
img = luz(img, [(x4 - 60, 600), (x4 + 60, 600), (x4 + 200, 1350), (x4 - 200, 1350)])
img.save(P / "posto_bomba4.png")

# posto visto da estrada
img, d = ceu()
d.rectangle((0, 1100, W, H), fill=(18, 18, 22))
d.polygon([(0, 1500), (W, 1380), (W, 1700), (0, 1820)], fill=(30, 30, 36), outline=OUT)
d.rectangle((560, 820, 900, 860), fill=(150, 35, 35), outline=OUT, width=5)
for px in (620, 700, 780, 860):
    d.rectangle((px - 14, 960, px + 14, 1060), fill=(140, 40, 40), outline=OUT, width=3)
d.rounded_rectangle((520, 640, 760, 720), radius=10, fill=(40, 40, 50), outline=OUT, width=5)
img = luz(img, [(510, 630), (770, 630), (770, 730), (510, 730)], cor=(255, 70, 70, 90), blur=25)
img.save(P / "posto_estrada.png")

# carro prata na bomba 4, farol alto
img, d = ceu()
x4 = posto(d)
carro(d, x4 - 20, 1420)
img = luz(img, [(x4 + 180, 1210), (W, 1000), (W, 1500), (x4 + 180, 1260)], cor=(255, 255, 220, 120), blur=30)
img.save(P / "posto_carro.png")

# visor da bomba
img = Image.new("RGB", (W, H), (12, 12, 16))
d = ImageDraw.Draw(img)
d.rounded_rectangle((140, 360, 940, 1560), radius=40, fill=(120, 30, 30), outline=OUT, width=10)
d.rounded_rectangle((220, 520, 860, 860), radius=20, fill=(8, 22, 14), outline=OUT, width=8)
d.text((540, 1250), "4", font=ImageFont.truetype(str(Path(__file__).resolve().parent.parent / "fontes" / "Anton-Regular.ttf"), 260),
       fill=(230, 230, 230), anchor="mm", stroke_width=8, stroke_fill=OUT)
img.save(P / "visor.png")

# telefone na parede
img = Image.new("RGB", (W, H), (34, 36, 46))
d = ImageDraw.Draw(img)
d.rounded_rectangle((330, 620, 750, 1240), radius=40, fill=(200, 190, 160), outline=OUT, width=10)
d.rounded_rectangle((300, 560, 420, 1300), radius=50, fill=(210, 200, 170), outline=OUT, width=10)
for r in range(3):
    for c in range(3):
        d.rounded_rectangle((470 + c * 80, 760 + r * 90, 530 + c * 80, 820 + r * 90), radius=10, fill=(230, 225, 205), outline=OUT, width=5)
d.line((360, 1300, 380, 1500, 340, 1650, 400, 1800), fill=OUT, width=10, joint="curve")
img.save(P / "telefone.png")
print("provisórias prontas")
