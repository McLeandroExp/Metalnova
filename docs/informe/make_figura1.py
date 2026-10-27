"""Genera la Figura 1 (árbol del problema) del informe MetalNova.

Salida: docs/informe/figuras/figura1_arbol_problema.png
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
OUT = BASE / "figuras" / "figura1_arbol_problema.png"
W, H = 1800, 1100
AZUL = "#1F3864"
AZUL_CLARO = "#D9E2F3"
NARANJA = "#C55A11"
NARANJA_CLARO = "#FBE5D6"
GRIS = "#404040"
GRIS_CLARO = "#F2F2F2"
VERDE = "#375623"
VERDE_CLARO = "#E2EFDA"


def font(name: str, size: int):
    for candidate in [
        Path(r"C:\Windows\Fonts") / name,
        Path(r"C:\Windows\Fonts") / "arial.ttf",
    ]:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


F_TITULO = font("arialbd.ttf", 40)
F_SUB = font("arial.ttf", 25)
F_CAJA = font("arialbd.ttf", 28)
F_TEXTO = font("arial.ttf", 23)
F_NOTA = font("arial.ttf", 19)


def caja(draw, xy, fill, outline, width=3):
    draw.rounded_rectangle(xy, radius=14, fill=fill, outline=outline, width=width)


def texto_centrado(draw, xy, text, fnt, fill=GRIS, spacing=8):
    x0, y0, x1, y1 = xy
    lineas = text.split("\n")
    alturas = []
    for linea in lineas:
        b = draw.textbbox((0, 0), linea, font=fnt)
        alturas.append(b[3] - b[1])
    total = sum(alturas) + spacing * (len(lineas) - 1)
    y = y0 + (y1 - y0 - total) / 2
    for linea, h in zip(lineas, alturas):
        b = draw.textbbox((0, 0), linea, font=fnt)
        draw.text((x0 + (x1 - x0 - (b[2] - b[0])) / 2, y - b[1]), linea, font=fnt, fill=fill)
        y += h + spacing


def flecha(draw, x1, y1, x2, y2, color=GRIS, width=4):
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    # punta
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    l = 18
    for sign in (-1, 1):
        draw.line(
            (x2, y2, x2 - l * math.cos(ang + sign * 0.45), y2 - l * math.sin(ang + sign * 0.45)),
            fill=color,
            width=width,
        )


img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

# Título
d.text((60, 35), "Árbol del problema: la caída del OEE y sus efectos", font=F_TITULO, fill=AZUL)

# Caja superior
caja(d, (500, 115, 1300, 255), AZUL, AZUL, 3)
texto_centrado(d, (515, 125, 1285, 245), "Caída del OEE\n78,02 % → 66,00 % en ventanas de 30 días", F_CAJA, "white")

# Tres causas
cajas = [
    (80, 360, 580, 540, "Pérdida de rendimiento\n82,5 % · 2,91 M min", NARANJA_CLARO, NARANJA),
    (650, 360, 1150, 540, "Pérdida de calidad\n13,2 % · 465 mil min", NARANJA_CLARO, NARANJA),
    (1220, 360, 1720, 540, "Pérdida de disponibilidad\n4,3 % · 152 mil min", NARANJA_CLARO, NARANJA),
]
for x0, y0, x1, y1, txt, fill, outline in cajas:
    caja(d, (x0, y0, x1, y1), fill, outline, 3)
    texto_centrado(d, (x0 + 15, y0 + 10, x1 - 15, y1 - 10), txt, F_CAJA, GRIS)

# Flechas del título a causas
flecha(d, 780, 255, 330, 360)
flecha(d, 900, 255, 900, 360)
flecha(d, 1020, 255, 1470, 360)

# Consecuencias
cons = [
    (110, 700, 570, 850, "Throughput\n4,27 M unidades\nno producidas", GRIS_CLARO, GRIS),
    (640, 700, 1160, 850, "Calidad\n684.643 unidades\nscrap (4,84 %)", GRIS_CLARO, GRIS),
    (1230, 700, 1690, 850, "Costo hipotético\nUSD 10,67 M + 0,56 M\n+ 12,32 M / 180 días", GRIS_CLARO, GRIS),
]
for x0, y0, x1, y1, txt, fill, outline in cons:
    caja(d, (x0, y0, x1, y1), fill, outline, 3)
    texto_centrado(d, (x0 + 15, y0 + 10, x1 - 15, y1 - 10), txt, F_TEXTO, GRIS)

# Flechas de causas a consecuencias
flecha(d, 330, 540, 330, 700)
flecha(d, 900, 540, 900, 700)
flecha(d, 1470, 540, 1470, 700)

# Causa raíz
caja(d, (150, 930, 1650, 1040), VERDE_CLARO, VERDE, 3)
texto_centrado(
    d,
    (170, 940, 1630, 1030),
    "Datos fragmentados y definiciones inconsistentes: IoT/SCADA, MES, CMMS, calidad y turnos sin un KPI único",
    F_SUB,
    GRIS,
)

# Nota
d.text(
    (60, 1060),
    "Datos sintéticos. Elaboración propia con cifras del prototipo (corte 2026-10-24).",
    font=F_NOTA,
    fill="#7F7F7F",
)

# Recortar el título y la nota internos: la caption y la nota APA los aportan.
img = img.crop((0, 90, W, 1045))
from PIL import ImageOps
img = ImageOps.expand(img, border=20, fill="white")
img.save(OUT, dpi=(200, 200))
print(OUT)
