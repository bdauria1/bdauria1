import colorsys
import sys
from html import escape
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

FONT = "'Cascadia Code','SFMono-Regular',Consolas,'DejaVu Sans Mono','Liberation Mono',Menlo,monospace"
PAD = 26
ART_COLS, ART_FS, ART_CW, ART_LH = 120, 8, 4.8, 9.0

THEMES = {
    "dark": dict(card="#161b22", border="#30363d"),
    "light": dict(card="#f6f8fa", border="#d0d7de"),
}

RAMP = " .:-=+*#%@"

def wave_cells(path, cols, crop=(0.008, 0.01, 0.992, 0.99), char_aspect=ART_CW / ART_LH,
               blur=1.0, gamma=0.6):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    l, t, r, b = crop
    img = img.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
    rows = round(cols * img.size[1] / img.size[0] * char_aspect)
    img = img.filter(ImageFilter.GaussianBlur(blur)).resize((cols, rows), Image.BOX)
    a = np.asarray(img).astype(float)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    L = 0.299 * R + 0.587 * G + 0.114 * B
    blue = np.clip((B - R + 5) / 75, 0, 1)
    foam = np.clip((L - 198) / 18, 0, 1)
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1)
    boat = np.clip((sat - 0.33) / 0.15, 0, 1) * (R > B) * 0.55
    f = np.clip(np.maximum.reduce([blue, foam, boat]), 0, 1) ** gamma

    grid = []
    for y in range(rows):
        row = []
        for x in range(cols):
            ch = RAMP[min(len(RAMP) - 1, int(f[y, x] * len(RAMP)))]
            q = tuple(int(c) // 20 * 20 + 10 for c in a[y, x])
            row.append((ch, q))
        while row and row[-1][0] == " ":
            row.pop()
        grid.append(row)
    return grid

def tone(rgb, mode):
    h, s, v = colorsys.rgb_to_hsv(*(min(c, 255) / 255 for c in rgb))
    if mode == "dark":
        v = max(v, 0.62)
        if s < 0.25:
            v = max(v, 0.9)
    else:
        if s < 0.25:
            s, v = 0.18, 0.55
        else:
            s, v = max(s, 0.35), min(v, 0.62)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def art_svg(grid, x0, y0, mode):
    out = [f'<g font-size="{ART_FS}" font-weight="700">']
    for i, row in enumerate(grid):
        if not row:
            continue
        spans, cur_color, buf = [], None, ""
        for ch, rgb in row:
            color = None if ch == " " else tone(rgb, mode)
            if ch == " " and cur_color is not None:
                color = cur_color          # let spaces ride along with the current span
            if color != cur_color and buf:
                spans.append((cur_color, buf))
                buf = ""
            cur_color = color
            buf += ch
        if buf:
            spans.append((cur_color, buf))
        body = "".join(
            escape(t) if c is None else f'<tspan fill="{c}">{escape(t)}</tspan>' for c, t in spans
        )
        y = y0 + (i + 1) * ART_LH
        out.append(
            f'<text x="{x0}" y="{y:.1f}" textLength="{len(row) * ART_CW:.1f}" '
            f'lengthAdjust="spacingAndGlyphs">{body}</text>'
        )
    out.append("</g>")
    return "\n".join(out)


def build(image_path, mode):
    t = THEMES[mode]
    grid = wave_cells(image_path, ART_COLS)
    art_w, art_h = ART_COLS * ART_CW, len(grid) * ART_LH
    W = PAD + art_w + PAD
    H = PAD + art_h + PAD

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" font-family="{FONT}" role="img" xml:space="preserve">
<title>The Great Wave off Kanagawa</title>
<style>text {{ white-space: pre; }}</style>
<rect x="0.5" y="0.5" width="{W - 1:.0f}" height="{H - 1:.0f}" rx="10" fill="{t['card']}" stroke="{t['border']}"/>
{art_svg(grid, PAD, PAD, mode)}
</svg>
"""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python gen_profile.py path/to/great_wave.jpg")
    here = Path(__file__).resolve().parent
    for mode in ("dark", "light"):
        out = here / f"{mode}_mode.svg"
        out.write_text(build(sys.argv[1], mode), encoding="utf-8")
        print(f"wrote {out.name} ({out.stat().st_size / 1024:.0f} KB)")
