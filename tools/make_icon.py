"""Generate assets/icon.ico (run once; the .ico is committed). Requires Pillow (dev only)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GREEN, DARK, WHITE = (46, 125, 50), (27, 94, 32), (255, 255, 255)


def draw(size: int) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=s // 5, fill=GREEN)
    # spreadsheet grid
    m = s // 5
    d.rectangle((m, m, s - m, s - m), fill=WHITE)
    d.rectangle((m, m, s - m, m + (s - 2 * m) // 4), fill=DARK)
    for i in range(1, 3):
        x = m + i * (s - 2 * m) // 3
        d.line((x, m, x, s - m), fill=GREEN, width=max(scale, s // 64))
    for i in range(2, 4):
        y = m + i * (s - 2 * m) // 4
        d.line((m, y, s - m, y), fill=GREEN, width=max(scale, s // 64))
    # check mark
    w = max(2 * scale, s // 14)
    d.line((s * 0.38, s * 0.62, s * 0.48, s * 0.72, s * 0.70, s * 0.47), fill=(255, 167, 38), width=w, joint='curve')
    return img.resize((size, size), Image.LANCZOS)


if __name__ == '__main__':
    out = Path(__file__).resolve().parent.parent / 'assets' / 'icon.ico'
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [draw(s) for s in sizes]
    images[-1].save(out, sizes=[(s, s) for s in sizes], append_images=images[:-1])
    images[-1].save(out.with_suffix('.png'))
    print('wrote', out)
