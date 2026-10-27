"""Genera las figuras F2-F10 del informe (Pillow, sin dependencias externas)."""
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE = Path(__file__).resolve().parent
FIG = BASE / "figuras"
FIG.mkdir(exist_ok=True)

AZUL = "#1F3864"
AZUL2 = "#2F5597"
AZUL_CLARO = "#D9E2F3"
NARANJA = "#C55A11"
NARANJA_CLARO = "#FBE5D6"
VERDE = "#375623"
VERDE_CLARO = "#E2EFDA"
GRIS = "#404040"
GRIS_CLARO = "#F2F2F2"
GRIS_MEDIO = "#7F7F7F"

W, H = 1800, 1050


def font(name="arial.ttf", size=28):
    for candidate in (Path(r"C:\Windows\Fonts") / name, Path(r"C:\Windows\Fonts") / "arial.ttf"):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


F_TIT = font("arialbd.ttf", 38)
F_SUB = font("arial.ttf", 26)
F_CAJA = font("arialbd.ttf", 27)
F_TEXTO = font("arial.ttf", 23)
F_SMALL = font("arial.ttf", 26)
F_NOTE = font("arial.ttf", 22)


def canvas(w=W, h=H):
    img = Image.new("RGB", (w, h), "white")
    return img, ImageDraw.Draw(img)


def caja(d, xy, fill, outline, width=3, radius=14):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def texto_centrado(d, xy, text, fnt, fill=GRIS, spacing=6):
    x0, y0, x1, y1 = xy
    lineas = text.split("\n")
    alturas = []
    for linea in lineas:
        b = d.textbbox((0, 0), linea, font=fnt)
        alturas.append(b[3] - b[1])
    total = sum(alturas) + spacing * (len(lineas) - 1)
    y = y0 + (y1 - y0 - total) / 2
    for linea, h in zip(lineas, alturas):
        b = d.textbbox((0, 0), linea, font=fnt)
        d.text((x0 + (x1 - x0 - (b[2] - b[0])) / 2, y - b[1]), linea, font=fnt, fill=fill)
        y += h + spacing


def flecha(d, x1, y1, x2, y2, color=GRIS, width=4, head=18):
    d.line((x1, y1, x2, y2), fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    for sign in (-1, 1):
        d.line(
            (x2, y2, x2 - head * math.cos(ang + sign * 0.45), y2 - head * math.sin(ang + sign * 0.45)),
            fill=color,
            width=width,
        )


def guardar(img, name):
    img.save(FIG / name, dpi=(200, 200))
    print(FIG / name)


# ---------------------------------------------------------------------------
# F2 · Marco conceptual
# ---------------------------------------------------------------------------
def f2():
    img, d = canvas(1800, 900)
    boxes = [
        (60, 200, 430, 520, "Datos fragmentados\nIoT/SCADA · MES · CMMS\nCalidad · Turnos", AZUL_CLARO, AZUL),
        (500, 200, 870, 520, "Modelo dimensional\nHechos + dimensiones\nKPI único y ponderado", AZUL_CLARO, AZUL),
        (940, 200, 1310, 520, "Diagnóstico\nLoss Tree · confiabilidad\ncalidad/energía · alertas", NARANJA_CLARO, NARANJA),
        (1380, 200, 1750, 520, "Decisión\nPriorización por impacto\ny criticidad", VERDE_CLARO, VERDE),
    ]
    for x0, y0, x1, y1, txt, fill, outline in boxes:
        caja(d, (x0, y0, x1, y1), fill, outline)
        texto_centrado(d, (x0 + 15, y0 + 10, x1 - 15, y1 - 10), txt, F_CAJA)
    for x in (430, 870, 1310):
        flecha(d, x + 10, 360, x + 60, 360)
    caja(d, (60, 640, 1750, 770), GRIS_CLARO, GRIS)
    texto_centrado(
        d,
        (80, 650, 1730, 760),
        "Gobierno del dato: definición única de KPI, calidad, trazabilidad y validación independiente",
        F_SUB,
    )
    guardar(img, "figura2_marco_conceptual.png")


# ---------------------------------------------------------------------------
# F3 · Fases metodológicas
# ---------------------------------------------------------------------------
def f3():
    img, d = canvas(1800, 900)
    fases = [
        ("1. Comprensión\ndel negocio", 70, 180),
        ("2. Comprensión\nde los datos", 500, 180),
        ("3. Preparación\nde los datos", 930, 180),
        ("4. Modelado\ndimensional", 1360, 180),
        ("5. Evaluación\ny validación", 930, 500),
        ("6. Despliegue\ny demo", 500, 500),
    ]
    for txt, x, y in fases:
        caja(d, (x, y, x + 330, y + 170), AZUL_CLARO, AZUL)
        texto_centrado(d, (x + 10, y + 10, x + 320, y + 160), txt, F_CAJA)
    flecha(d, 400, 265, 490, 265)
    flecha(d, 830, 265, 920, 265)
    flecha(d, 1260, 265, 1350, 265)
    d.line((1525, 350, 1525, 585), fill=GRIS, width=4)
    flecha(d, 1525, 585, 1270, 585)
    flecha(d, 930, 585, 840, 585)
    # Feedback
    flecha(d, 500, 585, 250, 585, color=NARANJA, width=3)
    flecha(d, 250, 585, 250, 355, color=NARANJA, width=3)
    caja(d, (70, 720, 1730, 820), NARANJA_CLARO, NARANJA)
    texto_centrado(
        d,
        (90, 730, 1710, 810),
        "SDD: spec → plan → tasks → verification · cada fase deja evidencia reproducible",
        F_SUB,
    )
    guardar(img, "figura3_fases_metodologicas.png")


# ---------------------------------------------------------------------------
# F4 · Arquitectura
# ---------------------------------------------------------------------------
def f4():
    img, d = canvas(1800, 1000)
    caja(d, (60, 150, 430, 470), AZUL_CLARO, AZUL)
    texto_centrado(d, (75, 160, 415, 460), "Python 3.13\nGenerador · Ingesta\nValidación · Simulación", F_CAJA)
    caja(d, (520, 120, 1040, 520), AZUL, AZUL)
    texto_centrado(d, (535, 130, 1025, 510), "PostgreSQL 16.4\nEsquema + hechos\n+ 20 vistas KPI\nDirectQuery", F_CAJA, "white")
    caja(d, (1130, 150, 1740, 470), VERDE_CLARO, VERDE)
    texto_centrado(d, (1145, 160, 1725, 460), "Power BI Desktop\n4 páginas principales\n+ drill-through + tooltip", F_CAJA)
    flecha(d, 440, 310, 510, 310, width=5)
    flecha(d, 1050, 310, 1120, 310, width=5)
    caja(d, (520, 650, 1040, 790), GRIS_CLARO, GRIS)
    texto_centrado(d, (535, 660, 1025, 780), "pgAdmin 9.18\nverificación visual de tablas y vistas", F_TEXTO)
    d.line((1040, 500, 1040, 650), fill=GRIS_MEDIO, width=3)
    caja(d, (60, 650, 430, 790), GRIS_CLARO, GRIS)
    texto_centrado(d, (75, 660, 415, 780), "CSV / manifiesto\nstreaming · ~99 MB", F_TEXTO)
    flecha(d, 245, 470, 245, 640, width=3)
    flecha(d, 430, 690, 560, 525, width=3)
    caja(d, (1130, 650, 1740, 790), GRIS_CLARO, GRIS)
    texto_centrado(d, (1145, 660, 1725, 780), "Docker Desktop (WSL2)\nloopback 127.0.0.1 · volumen local", F_TEXTO)
    caja(d, (60, 860, 1740, 950), VERDE_CLARO, VERDE)
    texto_centrado(d, (80, 870, 1720, 940), "Sin nube, sin API REST, sin aplicación web: demo local y reproducible", F_SUB)
    guardar(img, "figura4_arquitectura.png")


# ---------------------------------------------------------------------------
# F5 · Modelo estrella
# ---------------------------------------------------------------------------
def f5():
    img, d = canvas(1800, 1000)
    # dimensiones izquierdas
    dims_l = [
        (80, 150, 380, 270, "dim_planta\ndim_linea\ndim_maquina"),
        (80, 330, 380, 430, "dim_tiempo"),
        (80, 510, 380, 610, "dim_turno"),
        (80, 690, 380, 790, "dim_causa"),
    ]
    for x0, y0, x1, y1, txt in dims_l:
        caja(d, (x0, y0, x1, y1), AZUL_CLARO, AZUL)
        texto_centrado(d, (x0 + 10, y0 + 10, x1 - 10, y1 - 10), txt, F_TEXTO)
    # dimensiones derechas
    dims_r = [
        (1420, 150, 1720, 270, "dim_familia\ndim_producto"),
        (1420, 330, 1720, 430, "dim_tecnico"),
        (1420, 510, 1720, 610, "dim_orden"),
    ]
    for x0, y0, x1, y1, txt in dims_r:
        caja(d, (x0, y0, x1, y1), VERDE_CLARO, VERDE)
        texto_centrado(d, (x0 + 10, y0 + 10, x1 - 10, y1 - 10), txt, F_TEXTO)
    # hechos
    facts = [
        (620, 210, 930, 330, "fact_produccion"),
        (960, 210, 1270, 330, "fact_parada"),
        (620, 430, 930, 550, "fact_mantenimiento"),
        (960, 430, 1270, 550, "fact_calidad"),
    ]
    for x0, y0, x1, y1, txt in facts:
        caja(d, (x0, y0, x1, y1), NARANJA_CLARO, NARANJA)
        texto_centrado(d, (x0 + 10, y0 + 10, x1 - 10, y1 - 10), txt, F_CAJA)
    # buses
    d.line((500, 200, 500, 750), fill=GRIS_MEDIO, width=4)
    d.line((1340, 200, 1340, 610), fill=GRIS_MEDIO, width=4)
    for x0, y0, x1, y1, _ in dims_l:
        yc = (y0 + y1) / 2
        d.line((x1, yc, 500, yc), fill=GRIS_MEDIO, width=3)
    for x0, y0, x1, y1, _ in dims_r:
        yc = (y0 + y1) / 2
        d.line((x0, yc, 1340, yc), fill=GRIS_MEDIO, width=3)
    for x0, y0, x1, y1, _ in facts:
        yc = (y0 + y1) / 2
        d.line((500, yc, x0, yc), fill=GRIS_MEDIO, width=3)
        d.line((x1, yc, 1340, yc), fill=GRIS_MEDIO, width=3)
    # Redibujar hechos para tapar las líneas que los atraviesan.
    for x0, y0, x1, y1, txt in facts:
        caja(d, (x0, y0, x1, y1), NARANJA_CLARO, NARANJA)
        texto_centrado(d, (x0 + 10, y0 + 10, x1 - 10, y1 - 10), txt, F_CAJA)
    caja(d, (80, 860, 1720, 940), GRIS_CLARO, GRIS)
    texto_centrado(
        d,
        (95, 870, 1705, 930),
        "27 relaciones hecho → dimensión · jerarquías Planta→Línea→Máquina y Familia→Producto",
        F_SUB,
    )
    d.text((80, 815), "Hechos analíticos + 2 capas crudas (fact_evento, fact_evento_rechazado)", font=F_SMALL, fill=GRIS)
    guardar(img, "figura5_modelo_estrella.png")


# ---------------------------------------------------------------------------
# F6 · OEE y A/P/Q
# ---------------------------------------------------------------------------
def f6():
    img, d = canvas(1800, 1000)
    margen_l, margen_b, margen_t = 150, 150, 90
    ancho, alto = 1500, 700
    d.line((margen_l, margen_t, margen_l, margen_t + alto), fill=GRIS, width=3)
    d.line((margen_l, margen_t + alto, margen_l + ancho, margen_t + alto), fill=GRIS, width=3)
    grupos = ["Disponibilidad", "Rendimiento", "Calidad", "OEE"]
    inicio = [99.0250, 81.7800, 96.3448, 78.0226]
    cierre = [98.5455, 71.3074, 93.9177, 65.9961]
    maxv = 100
    gw = ancho / len(grupos)
    bw = gw * 0.22
    for gi, g in enumerate(grupos):
        x0 = margen_l + gi * gw + gw * 0.18
        for j, (val, color, label) in enumerate([(inicio[gi], AZUL2, "Inicio"), (cierre[gi], NARANJA, "Cierre")]):
            h = val / maxv * alto
            x = x0 + j * (bw + 8)
            y = margen_t + alto - h
            d.rectangle((x, y, x + bw, margen_t + alto), fill=color)
            d.text((x + 2, y - 38), f"{val:.1f}%".replace(".", ","), font=F_SMALL, fill=GRIS)
        d.text((margen_l + gi * gw + 20, margen_t + alto + 20), g, font=F_SUB, fill=GRIS)
    # leyenda
    d.rectangle((1250, 20, 1280, 45), fill=AZUL2)
    d.text((1290, 18), "Inicio 30 d", font=F_SMALL, fill=GRIS)
    d.rectangle((1450, 20, 1480, 45), fill=NARANJA)
    d.text((1490, 18), "Cierre 30 d", font=F_SMALL, fill=GRIS)
    d.text((margen_l, 20), "OEE y componentes: 78,02 % → 66,00 %", font=F_TIT, fill=AZUL)
    guardar(img, "figura6_oee_componentes.png")


# ---------------------------------------------------------------------------
# F7 · Loss Tree
# ---------------------------------------------------------------------------
def f7():
    img, d = canvas(1800, 800)
    datos = [
        ("Rendimiento", 2911218.08, 82.51, NARANJA),
        ("Calidad", 465420.00, 13.19, AZUL2),
        ("Disponibilidad", 151831, 4.30, GRIS_MEDIO),
    ]
    maxv = max(x[1] for x in datos)
    left, top, width, barh = 420, 120, 1100, 90
    for i, (label, val, pct, color) in enumerate(datos):
        y = top + i * 170
        d.text((60, y + 20), label, font=F_CAJA, fill=GRIS)
        w = val / maxv * width
        d.rectangle((left, y, left + w, y + barh), fill=color)
        etiqueta = f"{val:,.0f} min · {pct:.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
        d.text((left + w + 15, y + 20), etiqueta, font=F_TEXTO, fill=GRIS)
    d.text((60, 680), "Total: 3.528.469 min equivalentes · 4.269.957 unidades no producidas", font=F_SUB, fill=GRIS)
    guardar(img, "figura7_loss_tree.png")


# ---------------------------------------------------------------------------
# F8 · Pareto
# ---------------------------------------------------------------------------
def f8():
    img, d = canvas(1800, 1000)
    datos = [
        ("Microparada", 109020),
        ("F-MEC", 15356),
        ("F-ELE", 10546),
        ("F-NEU", 6803),
        ("F-HID", 6242),
        ("AJUSTE", 4260),
    ]
    total = sum(v for _, v in datos)
    left, top, width, height = 150, 100, 1450, 700
    d.line((left, top, left, top + height), fill=GRIS, width=3)
    d.line((left, top + height, left + width, top + height), fill=GRIS, width=3)
    maxv = max(v for _, v in datos)
    gw = width / len(datos)
    cum = 0
    puntos = []
    for i, (label, val) in enumerate(datos):
        h = val / maxv * height
        x0 = left + i * gw + gw * 0.15
        x1 = x0 + gw * 0.70
        y = top + height - h
        d.rectangle((x0, y, x1, top + height), fill=AZUL2)
        d.text((x0, y - 35), f"{val:,}".replace(",", "."), font=F_SMALL, fill=GRIS)
        d.text((x0 - 10, top + height + 15), label, font=F_SMALL, fill=GRIS)
        cum += val
        puntos.append((x0 + (x1 - x0) / 2, top + height - (cum / total) * height))
    # línea acumulada
    for i in range(len(puntos) - 1):
        d.line((puntos[i][0], puntos[i][1], puntos[i + 1][0], puntos[i + 1][1]), fill=NARANJA, width=4)
    for i, (x, y) in enumerate(puntos):
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=NARANJA)
    d.text((1150, 45), "Línea naranja: porcentaje acumulado", font=F_SMALL, fill=NARANJA)
    d.text((left, 30), "Pareto de downtime no planificado (minutos)", font=F_TIT, fill=AZUL)
    guardar(img, "figura8_pareto.png")


# ---------------------------------------------------------------------------
# F9 · Confiabilidad
# ---------------------------------------------------------------------------
def f9():
    img, d = canvas(1800, 1000)
    puntos = [
        ("M-047", 6473, 3007.6, NARANJA),
        ("M-024", 3634, 2548.5, AZUL2),
        ("M-049", 3520, 2280.4, AZUL2),
        ("M-041", 3434, 2002.8, AZUL2),
        ("M-015", 3095, 2433.4, VERDE),
        ("M-025", 2609, 2216.8, VERDE),
    ]
    left, top, width, height = 190, 120, 1450, 640
    xmin, xmax = 2400, 6800
    ymin, ymax = 1800, 3200
    # rejilla
    for xv in range(2500, 7000, 500):
        px = left + (xv - xmin) / (xmax - xmin) * width
        d.line((px, top, px, top + height), fill="#E6E6E6", width=1)
        d.text((px - 25, top + height + 10), str(xv), font=F_NOTE, fill=GRIS_MEDIO)
    for yv in range(1800, 3400, 200):
        py = top + height - (yv - ymin) / (ymax - ymin) * height
        d.line((left, py, left + width, py), fill="#E6E6E6", width=1)
        d.text((left - 70, py - 10), str(yv), font=F_NOTE, fill=GRIS_MEDIO)
    d.line((left, top, left, top + height), fill=GRIS, width=3)
    d.line((left, top + height, left + width, top + height), fill=GRIS, width=3)
    for name, x, y, color in puntos:
        px = left + (x - xmin) / (xmax - xmin) * width
        py = top + height - (y - ymin) / (ymax - ymin) * height
        d.ellipse((px - 12, py - 12, px + 12, py + 12), fill=color)
        d.text((px + 16, py - 12), name, font=F_SMALL, fill=GRIS)
    d.text((left + width / 2 - 180, top + height + 45), "Downtime no planificado (min)", font=F_SUB, fill=GRIS)
    d.text((left - 160, top + height / 2 - 60), "Microparadas\npor 100 h", font=F_SUB, fill=GRIS)
    d.text((left, 30), "Confiabilidad: downtime vs. microparadas por 100 h", font=F_TIT, fill=AZUL)
    d.text((left + 20, top + 25), "M-015 y M-025: MTBF alto, microparadas frecuentes", font=F_SMALL, fill=VERDE)
    guardar(img, "figura9_confiabilidad.png")


# ---------------------------------------------------------------------------
# F10 · Panel integrado
# ---------------------------------------------------------------------------
def f10():
    files = ["01-executive.png", "02-oee-loss-tree.png", "03-maintenance.png", "04-quality-energy.png"]
    imgs = [Image.open(BASE.parent / "capturas" / f).convert("RGB") for f in files]
    thumb = (980, 516)
    comp = Image.new("RGB", (thumb[0] * 2 + 30, thumb[1] * 2 + 30), "white")
    pos = [(10, 10), (thumb[0] + 20, 10), (10, thumb[1] + 20), (thumb[0] + 20, thumb[1] + 20)]
    for im, p in zip(imgs, pos):
        comp.paste(im.resize(thumb), p)
    guardar(comp, "figura10_panel_integrado.png")


CROPS = {
    "figura2_marco_conceptual.png": (30, 150, 1770, 800),
    "figura3_fases_metodologicas.png": (30, 150, 1770, 850),
    "figura4_arquitectura.png": (30, 100, 1770, 980),
    "figura5_modelo_estrella.png": (30, 120, 1770, 960),
    "figura6_oee_componentes.png": (80, 0, 1720, 900),
    "figura7_loss_tree.png": (40, 80, 1760, 780),
    "figura8_pareto.png": (100, 20, 1750, 950),
    "figura9_confiabilidad.png": (20, 20, 1750, 900),
}


def crop_all():
    for name, box in CROPS.items():
        path = FIG / name
        im = Image.open(path)
        im = im.crop(box)
        im = ImageOps.expand(im, border=10, fill="white")
        im.save(path, dpi=(200, 200))
        print("cropped", path)


if __name__ == "__main__":
    f2()
    f3()
    f4()
    f5()
    f6()
    f7()
    f8()
    f9()
    f10()
    crop_all()
