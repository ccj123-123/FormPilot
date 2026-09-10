"""Render FormPilot's architecture diagram as a deterministic PNG asset."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 1600
HEIGHT = 900
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "portfolio" / "architecture.png"


def font(size: int, _weight: str = "regular") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load Pillow's bundled scalable font without consulting the host OS."""
    return ImageFont.load_default(size=size)


FONTS = {
    "eyebrow": font(18, "semibold"),
    "title": font(43, "bold"),
    "subtitle": font(22),
    "zone": font(17, "semibold"),
    "step": font(14, "bold"),
    "card": font(20, "bold"),
    "body": font(15),
    "mono": font(15, "mono"),
    "badge": font(13, "semibold"),
    "footer": font(17, "semibold"),
}


def rounded_gradient(
    base: Image.Image,
    box: tuple[int, int, int, int],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    radius: int,
) -> None:
    x1, y1, x2, y2 = box
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    pixels = layer.load()
    for y in range(y1, y2):
        ratio = (y - y1) / max(1, y2 - y1 - 1)
        color = tuple(round(a + (b - a) * ratio) for a, b in zip(start, end))
        for x in range(x1, x2):
            pixels[x, y] = (*color, 255)
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
    base.alpha_composite(Image.composite(layer, Image.new("RGBA", base.size), mask))


def glow(base: Image.Image, xy: tuple[int, int], radius: int, color: tuple[int, int, int, int]) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = xy
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius // 2)))


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = "#5EDBFF",
    width: int = 4,
) -> None:
    draw.line((start, end), fill=color, width=width)
    x, y = end
    draw.polygon(((x, y), (x - 11, y - 7), (x - 11, y + 7)), fill=color)


def down_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str,
) -> None:
    draw.line((start, end), fill=color, width=4)
    x, y = end
    draw.polygon(((x, y), (x - 7, y - 11), (x + 7, y - 11)), fill=color)


def pill(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fill: str,
    outline: str,
    text_color: str,
) -> None:
    draw.rounded_rectangle(box, radius=17, fill=fill, outline=outline, width=1)
    draw.text(
        ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2 - 1),
        text,
        font=FONTS["badge"],
        fill=text_color,
        anchor="mm",
    )


def card(
    image: Image.Image,
    box: tuple[int, int, int, int],
    step: str,
    title: str,
    lines: tuple[str, ...],
    accent: str,
    *,
    featured: bool = False,
) -> None:
    x1, y1, x2, y2 = box
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (x1 + 5, y1 + 10, x2 + 5, y2 + 10), radius=20, fill=(0, 0, 0, 110)
    )
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))

    draw = ImageDraw.Draw(image)
    fill = "#17263B" if not featured else "#123347"
    outline = accent if featured else "#30435D"
    draw.rounded_rectangle(box, radius=20, fill=fill, outline=outline, width=2)
    draw.rounded_rectangle((x1, y1, x1 + 7, y2), radius=4, fill=accent)
    draw.text((x1 + 22, y1 + 18), step.upper(), font=FONTS["step"], fill=accent)
    draw.text((x1 + 22, y1 + 46), title, font=FONTS["card"], fill="#F5F9FF")
    body_y = y1 + 80
    for line in lines:
        draw.text((x1 + 22, body_y), line, font=FONTS["body"], fill="#AFC0D5")
        body_y += 23


def build_image() -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), "#081321")
    glow(image, (230, 405), 310, (112, 78, 255, 65))
    glow(image, (1180, 480), 470, (0, 193, 229, 48))
    draw = ImageDraw.Draw(image)

    for x in range(0, WIDTH, 40):
        draw.line((x, 0, x, HEIGHT), fill="#102136", width=1)
    for y in range(0, HEIGHT, 40):
        draw.line((0, y, WIDTH, y), fill="#102136", width=1)

    draw.text((62, 48), "FORMPILOT / SYSTEM MAP", font=FONTS["eyebrow"], fill="#67E8F9")
    draw.text((62, 79), "Intent in. Verified geometry out.", font=FONTS["title"], fill="#F7FAFF")
    draw.text(
        (64, 139),
        "A typed contract separates probabilistic interpretation from deterministic manufacturing.",
        font=FONTS["subtitle"],
        fill="#9FB2C8",
    )
    pill(draw, (1265, 67, 1538, 105), "REPRODUCIBLE PIPELINE", "#102A38", "#28748A", "#80E6F7")
    pill(draw, (1338, 116, 1538, 154), "V1 -> V2 LOOP", "#251F45", "#6956B7", "#C9BDFF")

    # Semantic zones make the confidence boundary legible before the cards are read.
    draw.rounded_rectangle((46, 218, 472, 726), radius=26, fill="#15172B", outline="#4F447F", width=2)
    draw.rounded_rectangle((500, 218, 1554, 726), radius=26, fill="#0C1E2A", outline="#245D6B", width=2)
    pill(draw, (70, 239, 261, 274), "AI / UNCERTAIN", "#2A2250", "#6756B0", "#D1C7FF")
    pill(draw, (524, 239, 815, 274), "DETERMINISTIC / MANUFACTURING", "#103541", "#26738A", "#91EBFA")

    draw.line((486, 204, 486, 744), fill="#8A7DE1", width=2)
    for y in range(204, 744, 15):
        draw.line((486, y, 486, min(y + 7, 744)), fill="#C0B7FF", width=3)
    draw.rounded_rectangle((395, 183, 578, 213), radius=14, fill="#312855")
    draw.text((486, 198), "TYPED CONTRACT", font=FONTS["badge"], fill="#E2DDFF", anchor="mm")

    y1, y2 = 330, 510
    cards = (
        ((70, y1, 260, y2), "01 / INPUT", "User intent", ("Natural language", "+ manual input"), "#9F8CFF", False),
        ((282, y1, 472, y2), "02 / PARSE", "Interpret", ("Structured parser", "manual fallback"), "#9F8CFF", False),
        ((510, y1, 700, y2), "03 / CONTRACT", "DesignSpec", ("Typed parameters", "single source of truth"), "#55E6FF", True),
        ((722, y1, 912, y2), "04 / GUARD", "Validate", ("Deterministic rules", "actionable errors"), "#55E6FF", False),
        ((934, y1, 1124, y2), "05 / BUILD", "OpenSCAD", ("Parametric solid", "STL export"), "#55E6FF", False),
        ((1146, y1, 1336, y2), "06 / INSPECT", "Trimesh", ("Mesh + bounds", "manufacturability"), "#55E6FF", False),
        (
            (1358, y1, 1548, y2),
            "07 / SHIP",
            "Preview",
            ("Interactive 3D", "STL preview + downloads", "spec JSON + STL"),
            "#55E6FF",
            False,
        ),
    )
    for box, step, title, lines, accent, featured in cards:
        card(image, box, step, title, lines, accent, featured=featured)

    draw = ImageDraw.Draw(image)
    centers = [260, 472, 700, 912, 1124, 1336]
    starts = [282, 510, 722, 934, 1146, 1358]
    for end_x, start_x in zip(starts, centers):
        arrow(draw, (start_x + 5, 420), (end_x - 6, 420), "#76DFF4")

    # Physical learning is intentionally presented as a pending feedback loop.
    card(
        image,
        (1226, 590, 1518, 692),
        "08 / REAL WORLD",
        "Physical feedback",
        ("Print, fit, measure",),
        "#FFB86B",
    )
    pill(draw, (1393, 602, 1501, 632), "PENDING", "#492F1D", "#A66A36", "#FFD1A0")
    card(
        image,
        (894, 590, 1188, 692),
        "09 / REVISE",
        "Deterministic V2",
        ("Feedback -> parameter deltas",),
        "#65E6A8",
        featured=True,
    )

    down_arrow(draw, (1453, 516), (1453, 580), "#FFB86B")
    arrow(draw, (1220, 641), (1193, 641), "#65E6A8")
    draw.line((894, 641, 806, 641, 806, 529), fill="#65E6A8", width=4)
    draw.polygon(((806, 517), (799, 529), (813, 529)), fill="#65E6A8")

    draw.rounded_rectangle((64, 770, 1536, 836), radius=20, fill="#0F2032", outline="#243B53", width=1)
    draw.ellipse((88, 792, 108, 812), fill="#9F8CFF")
    draw.text((123, 801), "AI proposes intent", font=FONTS["footer"], fill="#D8D1FF", anchor="lm")
    draw.line((308, 801, 351, 801), fill="#49617A", width=2)
    draw.ellipse((370, 792, 390, 812), fill="#55E6FF")
    draw.text(
        (405, 801),
        "Deterministic code owns dimensions, validation, geometry, inspection, and revision math",
        font=FONTS["footer"],
        fill="#C9F7FF",
        anchor="lm",
    )
    draw.text((1536, 866), "FORMPILOT / ARCHITECTURE / V1", font=FONTS["badge"], fill="#557089", anchor="ra")
    return image.convert("RGB")


def render(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    build_image().save(output, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="PNG path (default: portfolio/architecture.png)",
    )
    args = parser.parse_args()
    render(args.output.resolve())
    print(f"Rendered {args.output.resolve()}")


if __name__ == "__main__":
    main()
