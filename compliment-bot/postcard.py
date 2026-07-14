# -*- coding: utf-8 -*-
"""Генератор добрых открыток.

Рисует открытку средствами Pillow: мягкий градиент, «боке», сердечки
и короткая тёплая надпись. Тема (палитра) и надпись выбираются по дате,
поэтому каждый день открытка выглядит по-новому.
"""

import math
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 1080, 1350

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/TTF",
    "/usr/share/fonts/dejavu",
    "/Library/Fonts",
]


@dataclass
class Theme:
    top: tuple
    bottom: tuple
    accent: tuple      # сердечки и рамка
    text: tuple
    glow: tuple        # круги «боке»


THEMES = [
    Theme((255, 214, 194), (255, 160, 180), (232, 90, 122), (120, 40, 60), (255, 240, 230)),   # рассвет
    Theme((214, 204, 255), (170, 190, 250), (120, 110, 220), (60, 50, 120), (240, 236, 255)),  # лаванда
    Theme((201, 240, 225), (150, 216, 230), (60, 160, 150), (30, 90, 85), (235, 252, 246)),    # мята
    Theme((255, 232, 200), (255, 190, 150), (230, 120, 80), (130, 60, 30), (255, 246, 230)),   # персик
    Theme((205, 228, 255), (170, 200, 250), (90, 130, 220), (40, 65, 130), (238, 246, 255)),   # небо
    Theme((255, 210, 225), (240, 170, 210), (215, 80, 140), (115, 35, 75), (255, 238, 246)),   # роза
    Theme((250, 240, 200), (250, 205, 160), (225, 150, 70), (125, 80, 30), (255, 250, 235)),   # мёд
]

PHRASES = [
    "Доброе утро,\nсолнышко!",
    "Ты — моё\nсчастье",
    "Пусть день\nбудет добрым",
    "Думаю\nо тебе",
    "Ты чудесная.\nПомни это!",
    "Улыбнись —\nтебе идёт",
    "Сегодня твой\nдень!",
    "Люблю тебя\nбольше слов",
    "Ты делаешь мир\nтеплее",
    "Обнимаю тебя\nкрепко",
]


def _find_font(bold: bool = False) -> str | None:
    names = ["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"]
    for d in FONT_DIRS:
        for n in names:
            p = Path(d) / n
            if p.exists():
                return str(p)
    return None


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = _find_font(bold)
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def _lerp(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _draw_gradient(img: Image.Image, theme: Theme) -> None:
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        draw.line([(0, y), (WIDTH, y)], fill=_lerp(theme.top, theme.bottom, y / HEIGHT))


def _draw_bokeh(img: Image.Image, theme: Theme, rng: random.Random) -> None:
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(22):
        r = rng.randint(30, 160)
        x, y = rng.randint(-r, WIDTH + r), rng.randint(-r, HEIGHT + r)
        alpha = rng.randint(20, 70)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=theme.glow + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(layer)


def _heart_points(cx: float, cy: float, size: float, angle: float = 0.0) -> list:
    pts = []
    for i in range(60):
        t = math.pi * 2 * i / 60
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        if angle:
            xr = x * math.cos(angle) - y * math.sin(angle)
            yr = x * math.sin(angle) + y * math.cos(angle)
            x, y = xr, yr
        pts.append((cx + x * size, cy + y * size))
    return pts


def _draw_hearts(img: Image.Image, theme: Theme, rng: random.Random) -> None:
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(14):
        size = rng.uniform(0.8, 3.2)
        cx, cy = rng.randint(40, WIDTH - 40), rng.randint(40, HEIGHT - 40)
        angle = rng.uniform(-0.4, 0.4)
        alpha = rng.randint(60, 150)
        draw.polygon(_heart_points(cx, cy, size, angle), fill=theme.accent + (alpha,))
    # одно большое сердце над надписью
    draw.polygon(_heart_points(WIDTH / 2, HEIGHT * 0.28, 7.5), fill=theme.accent + (230,))
    img.alpha_composite(layer)


def _draw_frame(draw: ImageDraw.ImageDraw, theme: Theme) -> None:
    m = 36
    draw.rounded_rectangle(
        [m, m, WIDTH - m, HEIGHT - m], radius=48,
        outline=theme.accent + (200,), width=5,
    )
    m2 = 52
    draw.rounded_rectangle(
        [m2, m2, WIDTH - m2, HEIGHT - m2], radius=36,
        outline=theme.accent + (110,), width=2,
    )


def _draw_text(img: Image.Image, theme: Theme, phrase: str, footer: str) -> None:
    draw = ImageDraw.Draw(img)
    font = _load_font(96, bold=True)
    bbox = draw.multiline_textbbox((0, 0), phrase, font=font, align="center", spacing=18)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (WIDTH - tw) / 2, HEIGHT * 0.42

    shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).multiline_text(
        (x + 4, y + 6), phrase, font=font, fill=(255, 255, 255, 160),
        align="center", spacing=18,
    )
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(4)))
    draw.multiline_text((x, y), phrase, font=font, fill=theme.text + (255,),
                        align="center", spacing=18)

    small = _load_font(38)
    fb = draw.textbbox((0, 0), footer, font=small)
    draw.text(((WIDTH - (fb[2] - fb[0])) / 2, HEIGHT - 150), footer,
              font=small, fill=theme.text + (210,))


def make_postcard(out_path: str, when: date | None = None) -> str:
    """Создаёт открытку на дату `when` (по умолчанию сегодня) и возвращает путь."""
    when = when or date.today()
    day = when.toordinal()
    rng = random.Random(day)

    theme = THEMES[day % len(THEMES)]
    phrase = PHRASES[day % len(PHRASES)]
    footer = when.strftime("%d.%m.%Y") + "  ·  с любовью"

    img = Image.new("RGBA", (WIDTH, HEIGHT))
    _draw_gradient(img, theme)
    _draw_bokeh(img, theme, rng)
    _draw_hearts(img, theme, rng)
    _draw_frame(ImageDraw.Draw(img), theme)
    _draw_text(img, theme, phrase, footer)

    img.convert("RGB").save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    print(make_postcard("postcard.png"))
