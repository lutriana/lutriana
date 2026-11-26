#!/usr/bin/env python3
"""Build the README panels (luisacoded/panels/*.svg), styled like luisatriana.dev.

Usage:  python3 tools/build-readme-art.py      (needs internet for the fonts)

GitHub READMEs can't load CSS or web fonts, so each section of the site is drawn
as a self-contained SVG: the site's fonts are downloaded from Google Fonts,
subset to the characters each panel uses and embedded as base64. Light / dark
colours follow prefers-color-scheme, like the site's theme toggle.
Pixel icons come from luisacoded/pixels.src.txt (see tools/build-pixels.py).
"""
import base64
import html
import importlib.util
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "luisacoded" / "panels"
W = 960

_spec = importlib.util.spec_from_file_location("pixels", ROOT / "tools" / "build-pixels.py")
px = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(px)
ICONS = px.parse((ROOT / "luisacoded" / "pixels.src.txt").read_text(encoding="utf-8"))

# ------------------------------------------------------------------ theme ---
# Same tokens as styles/variables.css on the site: (light, dark)
THEME = {
    "bg": ("#FFFBD1", "#1C2232"),
    "menubar": ("rgba(255,246,190,.86)", "rgba(28,34,50,.86)"),
    "grid": ("rgba(102,152,204,.16)", "rgba(143,182,230,.10)"),
    "star": ("#8FB6E6", "#3F5A86"),
    "blue": ("#5F8FC4", "#9CC3F0"),
    "blue-soft": ("#8FB6E6", "#7FA6D6"),
    "ink": ("#4C4636", "#EDE6CF"),
    "ink-muted": ("#6E6553", "#BDB59D"),
    "pink": ("#C2338F", "#FF8AE6"),
    "pink-bright": ("#FF8AE6", "#F27BD6"),
    "window": ("#FFFFFF", "#2A3246"),
    "window-bar": ("#EFEDE8", "#343D54"),
    "dock": ("rgba(255,255,255,.55)", "rgba(255,255,255,.07)"),
    "tile": ("#FFFFFF", "#2A3246"),
    "btn-text": ("#FFFFFF", "#1C2232"),
}

FONTS = {  # css class -> google fonts family (weights are picked per panel)
    "disp": "Lexend+Exa",
    "hand": "Gaegu",
    "script": "Fraunces",  # italic 500 only
    "mono": "JetBrains+Mono",
    "ui": "Plus+Jakarta+Sans",
}
BOLD_CLASSES = {"pp", "pb", "pk", "bp", "bb", "bk"}

BASE_CSS = """
.disp{font-family:'Lexend Exa','Helvetica Neue',Arial,sans-serif}
.hand{font-family:'Gaegu','Comic Sans MS',cursive}
.script{font-family:'Fraunces',Georgia,serif;font-style:italic;font-weight:500}
.mono{font-family:'JetBrains Mono',ui-monospace,Menlo,monospace}
.ui{font-family:'Plus Jakarta Sans',-apple-system,'Segoe UI',sans-serif}
.pp{fill:#C2338F;font-weight:700}.pb{fill:#3F6FA8;font-weight:700}.pk{fill:#4C4636;font-weight:700}
.bp{fill:var(--pink);font-weight:700}.bb{fill:var(--blue);font-weight:700}.bk{fill:var(--ink);font-weight:700}
.px{shape-rendering:crispEdges}
"""


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


def _weight(attrs, default=400):
    m = re.search(r'font-weight="(\d+)"', attrs)
    if m:
        return int(m.group(1))
    cls = re.search(r'class="([^"]*)"', attrs)
    if cls and BOLD_CLASSES & set(cls.group(1).split()):
        return 700
    return default


def embed_fonts(svg):
    """@font-face rules for the fonts the svg uses: only the weights and
    characters each font actually draws."""
    used = {}  # font class -> (weights, chars)
    for attrs, inner in re.findall(r"<text\b([^>]*)>(.*?)</text>", svg, re.S):
        cls = re.search(r'class="([^"]*)"', attrs)
        font = next((c for c in (cls.group(1).split() if cls else []) if c in FONTS), None)
        if not font:
            continue
        weights, chars = used.setdefault(font, (set(), set()))
        base = 500 if font == "script" else _weight(attrs)
        for span_attrs, span in re.findall(r"<tspan\b([^>]*)>(.*?)</tspan>", inner, re.S):
            weights.add(_weight(span_attrs, base))
            chars.update(html.unescape(span))
        rest = re.sub(r"<tspan\b.*?</tspan>", "", inner, flags=re.S)
        if rest.strip():
            weights.add(base)
            chars.update(html.unescape(rest))

    css = []
    for font, (weights, chars) in used.items():
        if font == "script":
            family = f"{FONTS[font]}:ital,opsz,wght@1,9..144,500"
        else:
            family = f"{FONTS[font]}:wght@" + ";".join(map(str, sorted(weights)))
        css.append(fetch(f"https://fonts.googleapis.com/css2?family={family}&text="
                         + urllib.parse.quote("".join(sorted(chars)))).decode())

    def inline(m):
        data = base64.b64encode(fetch(m.group(1))).decode()
        return f"url(data:font/ttf;base64,{data})"

    css = re.sub(r"url\((https://[^)]+)\)", inline, "".join(css))
    return re.sub(r"\s+", " ", css)


# ---------------------------------------------------------------- helpers ---
def esc(s):
    return html.escape(s, quote=False)


def text(x, y, s, cls, anchor="start", extra=""):
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    return f'<text x="{x}" y="{y}" class="{cls}"{a}{extra}>{esc(s)}</text>'


def rich(x, y, s, cls, ctx="b", anchor="start", extra=""):
    """Text with highlights: {p:pink} {b:blue} {k:bold ink}. ctx 'p' = on paper."""
    parts = []
    for chunk in re.split(r"(\{[pbk]:[^}]*\})", s):
        m = re.fullmatch(r"\{([pbk]):([^}]*)\}", chunk)
        if m:
            parts.append(f'<tspan class="{ctx}{m.group(1)}">{esc(m.group(2))}</tspan>')
        elif chunk:
            parts.append(esc(chunk))
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    return f'<text x="{x}" y="{y}" class="{cls}"{a}{extra}>{"".join(parts)}</text>'


def lines(x, y, rows, cls, step, ctx="b", anchor="start", extra=""):
    out = []
    for r in rows:
        if r is None:  # paragraph gap
            y += step * 0.5
            continue
        out.append(rich(x, y, r, cls, ctx, anchor, extra))
        y += step
    return "".join(out)


def icon(name, x, y, size, rot=0, light=False):
    """A pixel icon; light=True keeps light colours (icon on paper / white)."""
    s = size / 16
    t = f"translate({x} {y})"
    if rot:
        t += f" rotate({rot} {size / 2} {size / 2})"
    cls = "px lt" if light else "px"
    return (f'<g class="{cls}" transform="{t} scale({s:.4f})">'
            + px.grid_rects(px.pixel_grid(ICONS[name])) + "</g>")


def title(x, y, s, size, spacing=2, weight=600, anchor="start"):
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    return (f'<text x="{x}" y="{y}" class="disp" fill="url(#tg)" font-size="{size}" '
            f'font-weight="{weight}" letter-spacing="{spacing}"{a}>{esc(s)}</text>')


def traffic(x, y):
    return "".join(f'<circle cx="{x + i * 18}" cy="{y}" r="6" fill="{c}"/>'
                   for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")))


def window_bar(w, h=34):
    return (f'<path d="M0 12 Q0 0 12 0 H{w - 12} Q{w} 0 {w} 12 V{h} H0 Z" '
            'style="fill:var(--window-bar)"/>')


def folder(x, y, label):
    return (
        f'<g transform="translate({x} {y})">'
        '<path d="M2 8 Q2 2 8 2 H22 L27 8 H52 Q58 8 58 14 V40 H2 Z" fill="#F590DA"/>'
        '<rect x="0" y="12" width="60" height="36" rx="6" fill="url(#fold)"/>'
        '<rect x="4" y="15" width="52" height="3" rx="1.5" fill="#fff" opacity=".35"/>'
        + text(30, 66, label, "ui", "middle",
               ' font-size="11" font-weight="600" style="fill:var(--ink)"')
        + "</g>")


def pill(x, y, label, stroke, fill="none", txt=None, size=12, weight=600, h=24):
    w = round(len(label) * size * 0.62 + 22)
    txt = txt or stroke
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" '
        f'style="fill:{fill};stroke:{stroke}" stroke-width="1.4"/>'
        + text(x + w / 2, y + h / 2 + size * 0.36, label, "ui", "middle",
               f' font-size="{size}" font-weight="{weight}" style="fill:{txt}"')
    ), w


def pills_row(cx, y, labels, stroke, **kw):
    widths = [pill(0, 0, l, stroke, **kw)[1] for l in labels]
    gap = 7
    x = cx - (sum(widths) + gap * (len(widths) - 1)) / 2
    out = []
    for label, w in zip(labels, widths):
        out.append(pill(x, y, label, stroke, **kw)[0])
        x += w + gap
    return "".join(out)


def heart(x, y, s=1, colour="#C2338F"):
    return (f'<path transform="translate({x} {y}) scale({s})" '
            'd="M6 11 C2 8 0 6 0 3.5 C0 1.5 1.5 0 3.3 0 C4.6 0 5.5 .8 6 1.8 '
            'C6.5 .8 7.4 0 8.7 0 C10.5 0 12 1.5 12 3.5 C12 6 10 8 6 11 Z" '
            f'style="fill:none;stroke:{colour}" stroke-width="1.5" stroke-linejoin="round"/>')


STAR = ("M0 -9 L2.6 -3.2 L8.6 -2.8 L4 1.2 L5.3 7.3 L0 4.1 "
        "L-5.3 7.3 L-4 1.2 L-8.6 -2.8 L-2.6 -3.2 Z")

DEFS = (
    '<linearGradient id="tg" x1="0" x2="1">'
    '<stop offset="0" style="stop-color:var(--blue)"/>'
    '<stop offset=".55" style="stop-color:var(--blue)"/>'
    '<stop offset="1" style="stop-color:var(--blue-soft)"/></linearGradient>'
    '<linearGradient id="fold" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#FFB3EE"/>'
    '<stop offset="1" style="stop-color:var(--pink-bright)"/></linearGradient>'
    '<filter id="sh" x="-25%" y="-25%" width="150%" height="150%">'
    '<feDropShadow dx="0" dy="8" stdDeviation="9" flood-color="#4C4636" flood-opacity=".18"/></filter>'
    '<filter id="sh2" x="-25%" y="-25%" width="150%" height="150%">'
    '<feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#4C4636" flood-opacity=".2"/></filter>'
    '<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
    '<path d="M24 0H0V24" fill="none" style="stroke:var(--grid)" stroke-width="1"/></pattern>'
    '<pattern id="stars" width="76" height="72" patternUnits="userSpaceOnUse">'
    f'<path transform="translate(19 18)" d="{STAR}" style="fill:var(--star)"/>'
    f'<path transform="translate(57 54)" d="{STAR}" style="fill:var(--star)"/></pattern>'
)


def panel(name, h, body, label):
    theme_l = "".join(f"--{k}:{v[0]};" for k, v in THEME.items())
    theme_d = "".join(f"--{k}:{v[1]};" for k, v in THEME.items())
    names = list(px.PALETTE)
    light_icons = "".join(f"--d-{v}:{px.PALETTE[v][0]};" for v in names)
    css = (BASE_CSS
           + f"svg{{{theme_l}}}@media (prefers-color-scheme: dark){{svg{{{theme_d}}}}}"
           + px.palette_css(names) + f".lt{{{light_icons}}}")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
        f'viewBox="0 0 {W} {h}" role="img" aria-label="{esc(label)}">'
        f"<defs>{DEFS}"
        f'<clipPath id="clip"><rect width="{W}" height="{h}" rx="22"/></clipPath></defs>'
        f'<g clip-path="url(#clip)"><rect width="{W}" height="{h}" style="fill:var(--bg)"/>'
        f"{body}</g></svg>"
    )
    fonts = embed_fonts(svg)
    svg = svg.replace("<defs>", f"<style>{fonts}{css}</style><defs>", 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.svg").write_text(svg + "\n", encoding="utf-8")
    print(f"  {name}.svg  {len(svg) // 1024} KB")


PAPER = ' font-size="19" fill="#6B5E4D"'


# ----------------------------------------------------------------- panels ---
def hero():
    b = []
    # menubar
    ink = 'style="fill:var(--ink)"'
    b.append('<rect width="960" height="32" style="fill:var(--menubar)"/>')
    b.append(icon("rocket", 16, 7, 18))
    b.append(text(42, 21, "Luisa", "ui", extra=f' font-size="13" font-weight="700" {ink}'))
    x = 100
    for item in ("About", "Stack", "Spotlight", "Projects", "Contact"):
        b.append(text(x, 21, item, "ui", extra=f' font-size="13" font-weight="500" {ink}'))
        x += len(item) * 7.6 + 24
    b.append(text(872, 21, "100 %", "ui", "end", f' font-size="12" font-weight="500" {ink}'))
    b.append('<rect x="882" y="11" width="24" height="12" rx="3" style="fill:none;stroke:var(--ink)" stroke-width="1.3"/>'
             '<rect x="884.5" y="13.5" width="19" height="7" rx="1.5" style="fill:var(--ink)"/>'
             '<rect x="907" y="14.5" width="2" height="5" rx="1" style="fill:var(--ink)"/>')
    b.append(icon("star", 922, 8, 16))

    # big "Hi!"
    b.append('<text x="44" y="205" class="disp" font-size="118" font-weight="600" '
             'letter-spacing="-2" style="fill:var(--blue)">Hi!</text>')

    # terminal window
    tx, ty, tw, th = 290, 78, 420, 292
    b.append(f'<g filter="url(#sh)"><rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="14" fill="#1F2633"/></g>')
    b.append(f'<path d="M{tx} {ty + 14} Q{tx} {ty} {tx + 14} {ty} H{tx + tw - 14} Q{tx + tw} {ty} '
             f'{tx + tw} {ty + 14} V{ty + 32} H{tx} Z" fill="#2C3547"/>')
    b.append(f'<g transform="translate({tx} {ty})">{traffic(20, 16)}</g>')
    b.append(text(tx + tw / 2, ty + 21, "~/luisa — zsh", "ui", "middle",
                  ' font-size="12" font-weight="600" fill="#AEB9CC"'))
    term = [
        ("$", "whoami"),
        (None, "luisa triana — systems & computing"),
        (None, "engineering student @ UTB"),
        ("$", "cat interests.txt"),
        (None, "web · cloud · data · iot"),
        ("$", "./build --ideas"),
    ]
    y = ty + 62
    for prompt, cmd in term:
        if prompt:
            b.append(f'<text x="{tx + 22}" y="{y}" class="mono" font-size="13"><tspan fill="#FF8AE6">$ </tspan>'
                     f'<tspan fill="#E8EEF7">{esc(cmd)}</tspan></text>')
            y += 21
        else:
            b.append(text(tx + 22, y, cmd, "mono", extra=' font-size="13" fill="#A9C6EC"'))
            y += 21 if cmd.startswith("luisa") else 27
    b.append(text(tx + 22, y, "✓ turning ideas into things that actually work", "mono",
                  extra=' font-size="13" fill="#B9E6A6"'))
    b.append(f'<rect x="{tx + 384}" y="{y - 11}" width="8" height="14" fill="#B9E6A6"/>')
    b.append(text(tx + tw / 2, ty + th - 24, "dev portfolio", "script", "middle",
                  ' font-size="56" fill="#FFFBEA"'))

    # stickers
    b.append(icon("heart", 662, 44, 64, rot=14))
    b.append(icon("rocket", 236, 316, 72, rot=-12))

    # intro + hand-drawn arrow
    b.append(text(742, 132, "I’m Luisa", "disp", extra=' font-size="32" font-weight="500" style="fill:var(--blue)"'))
    b.append(text(744, 162, "and this is my", "disp", extra=' font-size="18" style="fill:var(--blue)"'))
    b.append('<path d="M830 178 C 840 225, 790 262, 728 262" style="fill:none;stroke:var(--blue)" '
             'stroke-width="2.5" stroke-linecap="round"/>'
             '<path d="M740 251 L726 262 L741 271" style="fill:none;stroke:var(--blue)" '
             'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')

    # desktop folders
    b.append(folder(64, 250, "sentinel hmi"))
    b.append(folder(150, 318, "say hi"))
    b.append(folder(782, 296, "projects"))
    b.append(folder(866, 232, "my stack"))

    # dock
    dock = ["react", "typescript", "javascript", "java", "python", "nodejs", "fastapi",
            "aws", "docker", "git", "terraform", "mysql", None, "ship", "mail"]
    tile, gap = 42, 8
    width = sum(14 if d is None else tile + gap for d in dock) - gap + 28
    x = (W - width) / 2
    b.append(f'<rect x="{x}" y="398" width="{width}" height="62" rx="20" style="fill:var(--dock)" '
             'stroke="#fff" stroke-opacity=".45"/>')
    x += 14
    for d in dock:
        if d is None:
            b.append(f'<rect x="{x + 6}" y="410" width="1.5" height="38" style="fill:var(--ink)" opacity=".25"/>')
            x += 14
            continue
        b.append(f'<g filter="url(#sh2)"><rect x="{x}" y="408" width="{tile}" height="{tile}" rx="11" '
                 'style="fill:var(--tile)"/></g>')
        b.append(icon(d, x + 6, 414, 30))
        x += tile + gap
    panel("hero", 480, "".join(b),
          "Hi! I’m Luisa and this is my dev portfolio — systems & computing engineering "
          "student @ UTB; web · cloud · data · iot; turning ideas into things that actually work")


def about():
    b = ['<rect width="960" height="430" fill="url(#stars)"/>']
    nx, ny, nw, nh = 70, 36, 820, 356
    b.append(f'<g filter="url(#sh)"><rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="12" fill="#DCD4C2"/></g>')
    b.append(f'<rect x="{nx + 7}" y="{ny + 7}" width="{nw - 14}" height="{nh - 14}" rx="8" fill="#F4F0E6"/>')
    b.append('<linearGradient id="spine" x1="0" x2="1"><stop offset="0" stop-color="#7A6A4F" stop-opacity="0"/>'
             '<stop offset=".5" stop-color="#7A6A4F" stop-opacity=".22"/>'
             '<stop offset="1" stop-color="#7A6A4F" stop-opacity="0"/></linearGradient>')
    b.append(f'<rect x="{nx + nw / 2 - 22}" y="{ny + 7}" width="44" height="{nh - 14}" fill="url(#spine)"/>')

    lx = 116
    b.append(text(lx, 100, "ABOUT ME", "hand",
                  extra=' font-size="36" font-weight="700" letter-spacing="6" fill="#4C4636"'))
    b.append(lines(lx, 142, [
        "I'm a {p:Systems & Computing Engineering} student",
        "at UTB who enjoys building {b:practical software}",
        "that solves real-world problems.",
        None,
        "Whether designing {k:responsive frontend interfaces},",
        "configuring {k:cloud infrastructure}, or connecting",
        "{k:telemetry data} from hardware devices, I thrive",
        "at the intersection of modern web development,",
        "cloud computing & data systems.",
    ], "hand", 24, ctx="p", extra=PAPER))

    # film strip
    b.append('<g transform="translate(528 66) rotate(-2 60 150)">'
             '<rect width="120" height="300" rx="4" fill="#23201B"/>')
    for i, name in enumerate(("laptop", "cloud", "chart")):
        fy = 12 + i * 96
        b.append(f'<rect x="12" y="{fy}" width="96" height="84" fill="#ECE9E2"/>')
        b.append(icon(name, 28, fy + 10, 64, light=True))
    b.append("</g>")
    b.append(icon("star", 618, 50, 36, rot=-18))

    bx = 676
    items = [
        ["software developer into", "{b:web, cloud, data & IoT}"],
        ["i like turning {p:ideas} into", "things that {k:actually work}"],
        ["always learning, always", "{b:shipping}"],
    ]
    y = 112
    for it in items:
        b.append(heart(bx - 22, y - 12, 1.15))
        b.append(lines(bx, y, it, "hand", 24, ctx="p", extra=' font-size="18" fill="#6B5E4D"'))
        y += 86
    panel("about", 430, "".join(b),
          "About me — I’m a Systems & Computing Engineering student at UTB who enjoys building "
          "practical software that solves real-world problems.")


def book(cx, top, rot, grad, tag, name, logos):
    w, h = 214, 284
    gid = f"bk{name[:3]}"
    out = [
        f'<linearGradient id="{gid}" x1="0" y1="0" x2=".6" y2="1">'
        f'<stop offset="0" stop-color="{grad[0]}"/><stop offset="1" stop-color="{grad[1]}"/></linearGradient>',
        f'<clipPath id="c{gid}"><rect width="{w}" height="{h}" rx="9"/></clipPath>',
        f'<g transform="translate({cx - w / 2} {top}) rotate({rot} {w / 2} {h / 2})">',
        f'<g filter="url(#sh)"><rect width="{w}" height="{h}" rx="9" fill="url(#{gid})"/></g>',
        f'<g clip-path="url(#c{gid})"><circle cx="{w - 20}" cy="{h - 20}" r="100" fill="#fff" opacity=".13"/>'
        f'<rect x="{w - 18}" width="18" height="{h}" fill="#000" opacity=".09"/></g>',
        f'<g transform="translate(22 26) rotate(-6)"><rect width="{len(tag) * 9 + 26}" height="26" rx="13" fill="#FFF4B0"/>'
        + text((len(tag) * 9 + 26) / 2, 18, tag, "hand", "middle", ' font-size="16" font-weight="700" fill="#4C4636"')
        + "</g>",
        text(26, 132, name, "disp", extra=' font-size="16.5" font-weight="600" letter-spacing="1" fill="#fff"'),
    ]
    for i, logo in enumerate(logos):
        lx, ly = 26 + (i % 4) * 44, 186 + (i // 4) * 44
        out.append(f'<circle cx="{lx + 19}" cy="{ly + 19}" r="20" fill="#fff" stroke="#000" stroke-opacity=".08"/>')
        out.append(icon(logo, lx + 5, ly + 5, 28, light=True))
    out.append("</g>")
    return "".join(out)


def stack():
    cap = ' font-size="20" style="fill:var(--ink-muted)"'
    b = [title(46, 100, "what’s in my stack", 58, spacing=1, weight=500),
         lines(214, 152, ["java, python,", "typescript + javascript"], "hand", 24, anchor="middle", extra=cap),
         lines(752, 152, ["aws, docker, terraform,", "mysql + git"], "hand", 24, anchor="middle", extra=cap),
         book(214, 212, -6, ("#F37B6B", "#DD4F48"), "fresh", "LANGUAGES",
              ["java", "python", "typescript", "javascript"]),
         book(482, 150, 3, ("#B77EE3", "#8E52C8"), "duo", "FRONT & BACK",
              ["react", "vite", "nodejs", "fastapi", "django"]),
         book(752, 212, 7, ("#7DB3EC", "#4E86CB"), "extra", "CLOUD & DATA",
              ["aws", "docker", "terraform", "mysql", "git"]),
         lines(482, 480, ["react, vite, node.js,", "fastapi + django"], "hand", 24, anchor="middle", extra=cap)]
    panel("stack", 540, "".join(b),
          "What’s in my stack — languages: java, python, typescript, javascript; front & back: "
          "react, vite, node.js, fastapi, django; cloud & data: aws, docker, terraform, mysql, git")


def spotlight():
    b = ['<rect width="960" height="620" fill="url(#grid)"/>',
         title(44, 128, "SENTINEL HMI.", 70, spacing=6)]

    # paper note
    b.append('<g transform="translate(46 196) rotate(-2 165 140)">'
             '<g filter="url(#sh)"><rect width="336" height="268" rx="3" fill="#F4F0E6"/></g>'
             '<rect x="0" y="264" width="336" height="4" fill="#DCD4C2"/>')
    b.append(text(30, 46, "MY SPOTLIGHT PROJECT.", "disp",
                  extra=' font-size="13" font-weight="500" letter-spacing="1.2" fill="#3F6FA8"'))
    b.append(lines(30, 86, [
        "A {p:human-machine interface} for an",
        "{k:unmanned surface vehicle}.",
        "Engineered for {b:telemetry monitoring},",
        "navigation control and real-time",
        "visualization.",
    ], "hand", 27, ctx="p", extra=PAPER))
    x = 30
    for t in ("IoT", "React", "TypeScript", "Python"):
        g, w = pill(x, 222, t, "#3F6FA8", size=11.5)
        b.append(g)
        x += w + 7
    b.append("</g>")
    b.append('<rect x="20" y="430" width="116" height="30" fill="#D9C9A3" opacity=".75" transform="rotate(32 78 445)"/>')
    b.append(icon("star", 34, 168, 48, rot=-12))

    # handheld device
    b.append('<linearGradient id="dev" x1="0" y1="0" x2=".3" y2="1"><stop offset="0" stop-color="#FFF0A0"/>'
             '<stop offset=".6" stop-color="#F4DC6A"/><stop offset="1" stop-color="#E9CC55"/></linearGradient>'
             '<linearGradient id="btn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F9E78C"/>'
             '<stop offset="1" stop-color="#E2C350"/></linearGradient>')
    b.append('<g transform="translate(400 214) rotate(3 104 160)">'
             '<g filter="url(#sh)"><rect width="208" height="318" rx="48" fill="url(#dev)"/></g>'
             + "".join(f'<circle cx="{88 + i * 16}" cy="30" r="3.6" fill="#6B5A1E"/>' for i in range(3))
             + '<rect x="20" y="50" width="168" height="158" rx="10" fill="#1F2633" stroke="#3B3A33" stroke-width="6"/>'
             + text(34, 72, "11:11", "mono", extra=' font-size="9" fill="#A9C6EC"')
             + '<circle cx="132" cy="69" r="2.6" fill="#A9C6EC"/>'
             + text(138, 72, "GPS", "mono", extra=' font-size="9" fill="#A9C6EC"')
             + "".join(f'<rect x="{160 + i * 4}" y="64" width="2.5" height="8" fill="#A9C6EC"/>' for i in range(3))
             + '<rect x="32" y="80" width="144" height="76" rx="5" fill="#273044"/>'
             + '<path d="M38 140 C 60 118, 80 106, 104 116 S 140 146, 156 138" fill="none" stroke="#F2A7C3" stroke-width="1.6"/>'
             + '<path d="M156 138 L172 126" fill="none" stroke="#F2A7C3" stroke-opacity=".4" stroke-dasharray="2 3"/>'
             + '<circle cx="156" cy="138" r="5" fill="#F2A7C3" opacity=".25"/><circle cx="156" cy="138" r="2.4" fill="#F2A7C3"/>'
             + text(104, 178, "WANT TO TAKE A LOOK?", "mono", "middle", ' font-size="10.5" font-weight="500" fill="#E8EEF7"')
             + text(34, 198, "Telemetry", "mono", extra=' font-size="9" fill="#B9E6A6"')
             + text(174, 198, "Map", "mono", "end", ' font-size="9" fill="#A9C6EC"')
             + '<ellipse cx="104" cy="262" rx="44" ry="21" fill="url(#btn)" stroke="#D4B64A" stroke-opacity=".5"/>'
             + "</g>")

    # polaroids
    for x_, y_, rot, bg, name in ((646, 182, -7, "#EEF4FB", "map"), (776, 166, 6, "#FFF6CC", "ship")):
        b.append(f'<g transform="translate({x_} {y_}) rotate({rot} 70 80)">'
                 '<g filter="url(#sh)"><rect width="142" height="164" fill="#fff"/></g>'
                 f'<rect x="10" y="10" width="122" height="118" fill="{bg}"/>'
                 + icon(name, 25, 23, 92, light=True) + "</g>")
    b.append(icon("star", 762, 150, 28, rot=10))
    b.append(icon("star", 912, 330, 22))

    b.append(lines(654, 392, [
        "{p:real-time sensor data} — live telemetry",
        "& analytical dashboards", None,
        "{k:maps & visualization} — spatial mapping",
        "& trajectory tracking", None,
        "{k:vehicle control} — command interfaces",
        "for remote operation", None,
        "{b:IoT / cloud integration} — data pipelines",
        "to the backend",
    ], "hand", 23, extra=' font-size="17.5" style="fill:var(--ink)"'))
    panel("spotlight", 620, "".join(b),
          "Sentinel HMI — a human-machine interface for an unmanned surface vehicle: real-time "
          "sensor data, maps & visualization, vehicle control, IoT / cloud integration")


def projects():
    b = [title(40, 108, "PROJECTS", 72, spacing=6),
         text(578, 150, "things I’ve built", "disp", "end",
              ' font-size="24" font-weight="600" letter-spacing="1" style="fill:var(--blue-soft)"'),
         text(480, 204, "from the idea to the code to the deploy", "hand", "middle",
              ' font-size="21" letter-spacing="1" style="fill:var(--ink-muted)"')]
    cards = [
        ("sentinel-hmi", "#FFF2B8", "ship", -1.5, "Sentinel HMI",
         ["Interface for monitoring unmanned surface", "vehicles | live maps, sensors & telemetry"],
         ["IoT", "React", "TypeScript", "Python"], None),
        ("telemetry-pipeline", "#DCEBFB", "cloud", 0, "Cloud Telemetry Pipeline",
         ["Scalable infrastructure for receiving,", "processing & storing sensor streams in real time"],
         ["AWS", "Docker", "FastAPI", "MySQL"], "GitHub"),
        ("dev-dashboard", "#FFE0F5", "chart", 1.5, "Developer Dashboard",
         ["Web app with real-time state management,", "data visualization & clean responsive UI"],
         ["Vite", "React", "Node.js", "Tailwind"], "GitHub"),
    ]
    cw, gap = 286, 21
    for i, (win, body, ic, rot, name, desc, tags, link) in enumerate(cards):
        x = 22 + i * (cw + gap)
        cx = x + cw / 2
        b.append(f'<g transform="translate({x} 238) rotate({rot} {cw / 2} 110)">'
                 f'<g filter="url(#sh)"><rect width="{cw}" height="222" rx="12" fill="{body}"/></g>'
                 + window_bar(cw) + traffic(18, 17)
                 + text(cw / 2, 22, win, "ui", "middle", ' font-size="12" font-weight="600" style="fill:var(--ink-muted)"')
                 + icon(ic, cw / 2 - 56, 70, 112, light=True) + "</g>")
        b.append(text(cx, 498, name, "hand", "middle",
                      ' font-size="23" font-weight="700" letter-spacing="1.5" style="fill:var(--ink)"'))
        b.append(lines(cx, 522, desc, "ui", 17, anchor="middle",
                       extra=' font-size="12" style="fill:var(--ink-muted)"'))
        b.append(pills_row(cx, 552, tags, "var(--blue)", size=11, h=22))
        if link:
            g, w = pill(0, 0, "GitHub  ↗", "var(--blue)", fill="var(--blue)", txt="var(--btn-text)",
                        size=11.5, weight=700)
        else:
            g, w = pill(0, 0, "★ featured system", "var(--pink)", size=11.5)
        b.append(f'<g transform="translate({cx - w / 2} 588)">{g}</g>')
    panel("projects", 636, "".join(b),
          "Projects — Sentinel HMI, Cloud Telemetry Pipeline, Developer Dashboard")


CONTACT = [  # (label, value) shown on the contact card
    ("Email:", "codesluli@gmail.com"),
    ("LinkedIn:", "/in/lutriana"),
    ("GitHub:", "lutriana"),
    ("Instagram:", "@luisatri4na"),
]


def contact():
    b = [title(40, 122, "Let’s work", 56, spacing=2),
         title(40, 196, "together!", 56, spacing=2),
         icon("mail", 70, 250, 96, rot=-8),
         icon("heart", 186, 316, 52, rot=12),
         icon("star", 250, 236, 30, rot=-10)]

    # compose window
    wx, wy, ww, wh = 492, 52, 428, 250
    muted, inkc = 'style="fill:var(--ink-muted)"', 'style="fill:var(--ink)"'
    b.append(f'<g transform="translate({wx} {wy})">'
             f'<g filter="url(#sh)"><rect width="{ww}" height="{wh}" rx="12" style="fill:var(--window)"/></g>'
             + window_bar(ww) + traffic(18, 17)
             + text(ww / 2, 22, "New Message", "ui", "middle", f' font-size="12" font-weight="600" {muted}')
             + f'<text x="20" y="64" class="ui" font-size="13"><tspan {muted}>To:  </tspan>'
               f'<tspan font-weight="700" {inkc}>{esc(CONTACT[0][1])}</tspan></text>'
             + f'<rect x="20" y="78" width="{ww - 40}" height="1" {inkc} opacity=".12"/>'
             + f'<text x="20" y="102" class="ui" font-size="13"><tspan {muted}>Subject:  </tspan>'
               f'<tspan font-weight="600" {inkc}>let’s build something</tspan></text>'
             + heart(214, 92, 1, "var(--pink)")
             + f'<rect x="20" y="116" width="{ww - 40}" height="1" {inkc} opacity=".12"/>'
             + lines(20, 150, ["Feel free to reach out for collaborations,", "questions, or just to say hi!"],
                     "ui", 22, extra=f' font-size="14" {inkc}')
             + "</g>")
    g, w = pill(0, 0, "Send  ↗", "var(--blue)", fill="var(--blue)", txt="var(--btn-text)", size=13, weight=700, h=32)
    b.append(f'<g transform="translate({wx + ww - w - 20} {wy + wh - 50})">{g}</g>')

    # contact card
    b.append('<g transform="translate(300 300) rotate(-2 150 85)">'
             '<g filter="url(#sh)"><rect width="310" height="176" rx="6" fill="#FBF5E9"/></g>'
             + text(26, 38, "CONTACT ME!", "hand",
                    extra=' font-size="20" font-weight="700" letter-spacing="3" fill="#4C4636"')
             + lines(26, 72, [f"{{k:{k}}} {{b:{v}}}" for k, v in CONTACT], "hand", 25, ctx="p",
                     extra=' font-size="18.5" fill="#6B5E4D"')
             + "</g>")
    b.append(folder(712, 352, "projects"))
    b.append(folder(820, 330, "about me"))

    b.append(text(480, 528, "build · learn · improve · repeat", "hand", "middle",
                  ' font-size="24" letter-spacing="2" style="fill:var(--blue)"'))
    b.append(text(480, 552, "© 2026 Luisa Triana", "ui", "middle",
                  ' font-size="11" style="fill:var(--ink-muted)"'))
    panel("contact", 576, "".join(b),
          "Let’s work together! " + " · ".join(f"{k} {v}" for k, v in CONTACT)
          + " — build · learn · improve · repeat")


def main():
    print("building panels -> luisacoded/panels/")
    for build in (hero, about, stack, spotlight, projects, contact):
        build()


if __name__ == "__main__":
    main()
