import colorsys
import sys
from html import escape
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

FONT = "'Cascadia Code','SFMono-Regular',Consolas,'DejaVu Sans Mono','Liberation Mono',Menlo,monospace"
PAD = 26
ART_COLS, ART_FS, ART_CW, ART_LH = 130, 6.2, 3.7, 7.0
CAPTION = "The Great Wave off Kanagawa — Katsushika Hokusai, c. 1831"
CAP_FS, CAP_GAP = 11, 22
INFO_COLS, INFO_FS, INFO_CW, INFO_LH = 50, 12, 7.2, 19.0
GAP = 34

INFO = [
    "# bdauria1@github",
    ("OS", "Windows"),
    ("Host", "Boston, MA"),
    ("Kernel", "Software Engineer"),
    ("IDE", "Visual Studio Code"),
    None,
    ("Languages.Programming", "Python, TypeScript, SAS"),
    ("Languages.Infra", "Terraform, Kubernetes"),
    ("Cloud", "AWS"),
    ("Homelab", "Proxmox"),
    None,
    "# Contact",
    ("Website", "bdauria1.github.io"),
    ("LinkedIn", "in/bdauria"),
]

THEMES = {
    "dark": dict(card="#161b22", border="#30363d", fg="#e6edf3", muted="#6e7681", key="#ffa657", head="#58a6ff"),
    "light": dict(card="#f6f8fa", border="#d0d7de", fg="#1f2328", muted="#8c959f", key="#bc4c00", head="#0969da"),
}

RAMP = " .:;+*x#%@"


def wave_cells(path, cols, crop=(0.006, 0.06, 0.994, 0.985), char_aspect=ART_CW / ART_LH):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    img.paste(img.getpixel((int(0.15 * w), int(0.04 * h))), (0, 0, int(0.12 * w), int(0.32 * h)))
    l, t, r, b = crop
    img = img.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
    rows = round(cols * img.size[1] / img.size[0] * char_aspect)
    img = img.filter(ImageFilter.GaussianBlur(0.8)).resize((cols, rows), Image.BOX)
    a = np.asarray(img).astype(float)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    L = 0.299 * R + 0.587 * G + 0.114 * B
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1)
    blue = np.clip((B - R + 5) / 70, 0, 1)
    foam = np.clip((L - 196) / 22, 0, 1)
    boat = np.clip((sat - 0.33) / 0.15, 0, 1) * (R > B) * 0.6
    sky = 0.3 * np.clip((165 - L) / 60, 0, 1)
    f = np.clip(np.maximum.reduce([blue, foam, boat, sky]), 0, 1) ** 0.6

    grid = []
    for y in range(rows):
        row = []
        for x in range(cols):
            ch = RAMP[min(len(RAMP) - 1, int(f[y, x] * len(RAMP)))]
            q = tuple(int(c) // 16 * 16 + 8 for c in a[y, x])
            row.append((ch, q, round(f[y, x], 1)))
        while row and row[-1][0] == " ":
            row.pop()
        grid.append(row)
    return grid


def hexrgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def tone(rgb, ink, mode):
    h, s, v = colorsys.rgb_to_hsv(*(min(c, 255) / 255 for c in rgb))
    if mode == "dark":
        v = max(v, 0.62)
        if s < 0.22:
            s, v = s * 0.7, max(v, 0.92)
    else:
        if s < 0.22:
            s, v = 0.25, 0.5
        else:
            s, v = max(s, 0.45), min(v, 0.6)
    fg = [c * 255 for c in colorsys.hsv_to_rgb(h, s, v)]
    bg = hexrgb(THEMES[mode]["card"])
    lo = 0.3 if mode == "dark" else 0.55
    k = lo + (1 - lo) * min(1, ink * 1.4)
    return "#%02x%02x%02x" % tuple(round(bg[i] + (fg[i] - bg[i]) * k) for i in range(3))


def art_svg(grid, x0, y0, mode):
    out = [f'<g font-size="{ART_FS}" font-weight="700">']
    for i, row in enumerate(grid):
        if not row:
            continue
        spans, cur_color, buf = [], None, ""
        for ch, rgb, ink in row:
            color = None if ch == " " else tone(rgb, ink, mode)
            if ch == " " and cur_color is not None:
                color = cur_color
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


def info_svg(x0, y0, t):
    out = [f'<g font-size="{INFO_FS}">']
    for i, item in enumerate(INFO):
        if item is None:
            continue
        if isinstance(item, str):
            title = item[2:]
            lead = "" if i == 0 else "— "
            rule = "—" * (INFO_COLS - len(lead + title) - 1)
            body = (f'<tspan fill="{t["head"]}">{escape(lead + title)}</tspan>'
                    f'<tspan fill="{t["muted"]}"> {rule}</tspan>')
        else:
            k, v = item
            dots = INFO_COLS - len(k) - len(v) - 3
            assert dots >= 2, f"INFO row too long: {k}"
            body = (f'<tspan fill="{t["key"]}">{escape(k)}:</tspan>'
                    f'<tspan fill="{t["muted"]}"> {"." * dots} </tspan>'
                    f'<tspan fill="{t["fg"]}">{escape(v)}</tspan>')
        y = y0 + (i + 1) * INFO_LH
        out.append(f'<text x="{x0}" y="{y:.1f}" textLength="{INFO_COLS * INFO_CW:.1f}" '
                   f'lengthAdjust="spacingAndGlyphs">{body}</text>')
    out.append("</g>")
    return "\n".join(out)


def build(image_path, mode):
    t = THEMES[mode]
    grid = wave_cells(image_path, ART_COLS)
    art_w, art_h = ART_COLS * ART_CW, len(grid) * ART_LH + CAP_GAP
    info_w, info_h = INFO_COLS * INFO_CW, len(INFO) * INFO_LH + 6
    W = PAD + art_w + GAP + info_w + PAD
    H = PAD + max(art_h, info_h) + PAD

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" font-family="{FONT}" role="img" xml:space="preserve">
<title>bdauria1: Hokusai's The Great Wave off Kanagawa in ASCII beside a terminal-style profile</title>
<style>text {{ white-space: pre; }}</style>
<rect x="0.5" y="0.5" width="{W - 1:.0f}" height="{H - 1:.0f}" rx="10" fill="{t['card']}" stroke="{t['border']}"/>
{art_svg(grid, PAD, (H - art_h) / 2, mode)}
<text x="{PAD + art_w / 2:.1f}" y="{(H + art_h) / 2:.1f}" text-anchor="middle" font-size="{CAP_FS}" font-style="italic" fill="{t['muted']}">{escape(CAPTION)}</text>
{info_svg(PAD + art_w + GAP, (H - info_h) / 2, t)}
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