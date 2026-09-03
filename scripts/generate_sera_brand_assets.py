"""Generate deterministic Sera application-icon derivatives from the master PNG."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "assets" / "branding"
MASTER = BRAND_DIR / "sera-icon-master.png"


def _resized(source: Image.Image, size: int) -> Image.Image:
    return source.resize((size, size), Image.Resampling.LANCZOS)


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ["seguisb.ttf", "segoeuib.ttf"] if bold else ["segoeui.ttf"]
    font_root = Path("C:/Windows/Fonts")
    for name in names:
        candidate = font_root / name
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _write_social_preview(icon: Image.Image) -> None:
    width, height = 1280, 640
    canvas = Image.new("RGBA", (width, height), "#090b28")
    draw = ImageDraw.Draw(canvas)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = (
            round(9 + 7 * ratio),
            round(11 + 8 * ratio),
            round(40 + 32 * ratio),
            255,
        )
        draw.line((0, y, width, y), fill=color)

    mark = _resized(icon, 410)
    canvas.alpha_composite(mark, (76, 115))
    draw.text((555, 185), "SeraEdit", font=_font(88, bold=True), fill="#F4FBFF")
    draw.text(
        (560, 302),
        "Reliable MusicXML editing",
        font=_font(36),
        fill="#67E8F9",
    )
    draw.text(
        (560, 360),
        "through structured score patches",
        font=_font(30),
        fill="#C8D2F3",
    )
    draw.rounded_rectangle((560, 445, 858, 497), radius=15, fill="#151B4F")
    draw.text((588, 456), "LOCAL-FIRST  •  MIT", font=_font(21, bold=True), fill="#FF7A66")
    canvas.convert("RGB").save(BRAND_DIR / "sera-github-social-preview.png", optimize=True)


def main() -> int:
    if not MASTER.is_file():
        raise FileNotFoundError(f"Missing master brand asset: {MASTER}")

    source = Image.open(MASTER).convert("RGBA")
    if source.width != source.height:
        raise ValueError("The master Sera icon must be square")

    for size in (1024, 512, 256, 128, 64, 32):
        _resized(source, size).save(BRAND_DIR / f"sera-icon-{size}.png", optimize=True)

    electron_icon = _resized(source, 512)
    electron_icon.save(ROOT / "electron" / "icon.png", optimize=True)
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    for ico_path in (BRAND_DIR / "sera-icon.ico", ROOT / "electron" / "icon.ico"):
        electron_icon.save(ico_path, format="ICO", sizes=ico_sizes)

    public_dir = ROOT / "frontend" / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    _resized(source, 32).save(public_dir / "favicon-32x32.png", optimize=True)
    _resized(source, 180).save(public_dir / "apple-touch-icon.png", optimize=True)
    _resized(source, 192).save(public_dir / "sera-icon-192.png", optimize=True)
    electron_icon.save(
        public_dir / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48)],
    )

    _write_social_preview(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
