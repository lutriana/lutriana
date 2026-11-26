#!/usr/bin/env python3
"""Build the few README "cards" that are drawn as images (luisacoded/cards/*.svg):
the zsh terminal, the Sentinel HMI handheld and the New Message window,
styled like luisatriana.dev. Everything else in the README is plain markdown.

Usage:  python3 tools/build-cards.py      (needs internet for the fonts)

GitHub can't load web fonts in a README, so the site's fonts are downloaded
from Google Fonts, subset to the characters each card uses and embedded.
Backgrounds are transparent; colours follow prefers-color-scheme.
"""
import base64
import html
import importlib.util
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "luisacoded" / "cards"

_spec = importlib.util.spec_from_file_location("pixels", ROOT / "tools" / "build-pixels.py")
px = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(px)
ICONS = px.parse((ROOT / "luisacoded" / "pixels.src.txt").read_text(encoding="utf-8"))

THEME = {  # site tokens (styles/variables.css): (light, dark)
    "blue": ("#5F8FC4", "#9CC3F0"),
    "ink": ("#4C4636", "#EDE6CF"),
    "ink-muted": ("#6E6553", "#BDB59D"),
    "pink": ("#C2338F", "#FF8AE6"),
    "window": ("#FFFFFF", "#2A3246"),
    "window-bar": ("#EFEDE8", "#343D54"),
    "line": ("rgba(76,70,54,.12)", "rgba(237,230,207,.14)"),
    "btn-text": ("#FFFFFF", "#1C2232"),
}

FONTS = {
    "script": "Fraunces:ital,opsz,wght@1,9..144,500",
    "mono": "JetBrains+Mono:wght@{w}",
    "ui": "Plus+Jakarta+Sans:wght@{w}",
}

CSS = """
.script{font-family:'Fraunces',Georgia,serif;font-style:italic;font-weight:500}
.mono{font-family:'JetBrains Mono',ui-monospace,Menlo,monospace}
.ui{font-family:'Plus Jakarta Sans',-apple-system,'Segoe UI',sans-serif}
.px{shape-rendering:crispEdges}
"""


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


def embed_fonts(svg):
    """@font-face rules with only the weights and characters each font draws."""
    used = {}
    for attrs, inner in re.findall(r"<text\b([^>]*)>(.*?)</text>", svg, re.S):
        font = re.search(r'class="(\w+)"', attrs).group(1)
        weights, chars = used.setdefault(font, (set(), set()))
        base = re.search(r'font-weight="(\d+)"', attrs)
        base = base.group(1) if base else "400"
        spans = re.findall(r"<tspan\b([^>]*)>(.*?)</tspan>", inner, re.S)
        for sattrs, span in spans:
            w = re.search(r'font-weight="(\d+)"', sattrs)
            weights.add(w.group(1) if w else base)
            chars.update(html.unescape(span))
        if not spans:
            weights.add(base)
            chars.update(html.unescape(inner))
    css = ""
    for font, (weights, chars) in used.items():
        family = FONTS[font].format(w=";".join(sorted(weights)))
        css += fetch(f"https://fonts.googleapis.com/css2?family={family}&text="
                     + urllib.parse.quote("".join(sorted(chars)))).decode()
    css = re.sub(r"url\((https://[^)]+)\)",
                 lambda m: "url(data:font/ttf;base64,"
                 + base64.b64encode(fetch(m.group(1))).decode() + ")", css)
    return re.sub(r"\s+", " ", css)


def esc(s):
    return html.escape(s, quote=False)


def text(x, y, s, cls, attrs=""):
    return f'<text x="{x}" y="{y}" class="{cls}" {attrs}>{esc(s)}</text>'


def icon(name, x, y, size, rot=0):
    t = f"translate({x} {y})" + (f" rotate({rot} {size / 2} {size / 2})" if rot else "")
    return (f'<g class="px" transform="{t} scale({size / 16:.4f})">'
            + px.grid_rects(px.pixel_grid(ICONS[name])) + "</g>")


def traffic(x, y):
    return "".join(f'<circle cx="{x + i * 18}" cy="{y}" r="6" fill="{c}"/>'
                   for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")))


def bar(w, h=34, fill='style="fill:var(--window-bar)"'):
    return f'<path d="M0 12 Q0 0 12 0 H{w - 12} Q{w} 0 {w} 12 V{h} H0 Z" {fill}/>'


SHADOW = ('<filter id="sh" x="-20%" y="-20%" width="140%" height="150%">'
          '<feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity=".18"/></filter>')


def card(name, w, h, body, label):
    light = "".join(f"--{k}:{v[0]};" for k, v in THEME.items())
    dark = "".join(f"--{k}:{v[1]};" for k, v in THEME.items())
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           f'role="img" aria-label="{esc(label)}"><defs>{SHADOW}</defs>{body}</svg>')
    style = (embed_fonts(svg) + CSS
             + f"svg{{{light}}}@media (prefers-color-scheme: dark){{svg{{{dark}}}}}"
             + px.palette_css(list(px.PALETTE)))
    svg = svg.replace("<defs>", f"<style>{style}</style><defs>", 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.svg").write_text(svg + "\n", encoding="utf-8")
    print(f"  {name}.svg  {len(svg) // 1024} KB")


def terminal():
    x, y, w, h = 60, 40, 600, 330
    b = [f'<g transform="translate({x} {y})">',
         f'<g filter="url(#sh)"><rect width="{w}" height="{h}" rx="14" fill="#1F2633"/></g>',
         bar(w, 34, 'fill="#2C3547"'), traffic(20, 17),
         text(w / 2, 22, "~/luisa — zsh", "ui", 'text-anchor="middle" font-size="12.5" font-weight="600" fill="#AEB9CC"')]
    rows = [("$", "whoami"), ("", "luisa triana — systems & computing engineering student @ UTB"), None,
            ("$", "cat interests.txt"), ("", "web · cloud · data · iot"), None,
            ("$", "./build --ideas"), ("ok", "✓ turning ideas into things that actually work")]
    ty = 70
    for r in rows:
        if r is None:
            ty += 10
            continue
        kind, s = r
        if kind == "$":
            b.append(f'<text x="26" y="{ty}" class="mono" font-size="14"><tspan fill="#FF8AE6">$ </tspan>'
                     f'<tspan fill="#E8EEF7">{esc(s)}</tspan></text>')
        else:
            colour = "#B9E6A6" if kind == "ok" else "#A9C6EC"
            b.append(text(26, ty, s, "mono", f'font-size="14" fill="{colour}"'))
        ty += 23
    b.append(f'<rect x="{26 + 46 * 8.43:.0f}" y="{ty - 23 - 12}" width="9" height="16" fill="#B9E6A6"/>')
    b.append(text(w / 2, h - 30, "dev portfolio", "script", 'text-anchor="middle" font-size="58" fill="#FFFBEA"'))
    b.append("</g>")
    b.append(icon("heart", 590, 6, 72, rot=14))
    b.append(icon("rocket", 12, 300, 76, rot=-12))
    card("terminal", 720, 400, "".join(b),
         "~/luisa — zsh: $ whoami → luisa triana, systems & computing engineering student @ UTB; "
         "$ cat interests.txt → web · cloud · data · iot; $ ./build --ideas → turning ideas into things "
         "that actually work. dev portfolio")


def device():
    b = ['<linearGradient id="dev" x1="0" y1="0" x2=".3" y2="1"><stop offset="0" stop-color="#FFF0A0"/>'
         '<stop offset=".6" stop-color="#F4DC6A"/><stop offset="1" stop-color="#E9CC55"/></linearGradient>'
         '<linearGradient id="btn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F9E78C"/>'
         '<stop offset="1" stop-color="#E2C350"/></linearGradient>',
         '<g transform="translate(36 30) rotate(3 104 160)">',
         '<g filter="url(#sh)"><rect width="208" height="318" rx="48" fill="url(#dev)"/></g>',
         "".join(f'<circle cx="{88 + i * 16}" cy="30" r="3.6" fill="#6B5A1E"/>' for i in range(3)),
         '<rect x="20" y="50" width="168" height="158" rx="10" fill="#1F2633" stroke="#3B3A33" stroke-width="6"/>',
         text(34, 72, "11:11", "mono", 'font-size="9" fill="#A9C6EC"'),
         '<circle cx="132" cy="69" r="2.6" fill="#A9C6EC"/>',
         text(138, 72, "GPS", "mono", 'font-size="9" fill="#A9C6EC"'),
         "".join(f'<rect x="{160 + i * 4}" y="64" width="2.5" height="8" fill="#A9C6EC"/>' for i in range(3)),
         '<rect x="32" y="80" width="144" height="76" rx="5" fill="#273044"/>',
         '<path d="M38 140 C 60 118, 80 106, 104 116 S 140 146, 156 138" fill="none" stroke="#F2A7C3" stroke-width="1.6"/>',
         '<path d="M156 138 L172 126" fill="none" stroke="#F2A7C3" stroke-opacity=".4" stroke-dasharray="2 3"/>',
         '<circle cx="156" cy="138" r="5" fill="#F2A7C3" opacity=".25"/><circle cx="156" cy="138" r="2.4" fill="#F2A7C3"/>',
         text(104, 178, "WANT TO TAKE A LOOK?", "mono", 'text-anchor="middle" font-size="10.5" font-weight="500" fill="#E8EEF7"'),
         text(34, 198, "Telemetry", "mono", 'font-size="9" fill="#B9E6A6"'),
         text(174, 198, "Map", "mono", 'text-anchor="end" font-size="9" fill="#A9C6EC"'),
         '<ellipse cx="104" cy="262" rx="44" ry="21" fill="url(#btn)" stroke="#D4B64A" stroke-opacity=".5"/>',
         "</g>",
         icon("star", 6, 10, 40, rot=-12),
         icon("star", 238, 300, 26, rot=10)]
    card("device", 280, 390, "".join(b),
         "Sentinel HMI handheld: telemetry map with the vehicle route — want to take a look?")


def mail():
    w, h = 520, 236
    ink, muted = 'style="fill:var(--ink)"', 'style="fill:var(--ink-muted)"'
    line = f'style="fill:var(--line)"'
    b = [f'<g transform="translate(20 16)">',
         f'<g filter="url(#sh)"><rect width="{w}" height="{h}" rx="12" style="fill:var(--window)"/></g>',
         bar(w), traffic(18, 17),
         text(w / 2, 22, "New Message", "ui", f'text-anchor="middle" font-size="12.5" font-weight="600" {muted}'),
         f'<text x="22" y="66" class="ui" font-size="14"><tspan {muted}>To:  </tspan>'
         f'<tspan font-weight="700" {ink}>codesluli@gmail.com</tspan></text>',
         f'<rect x="22" y="80" width="{w - 44}" height="1" {line}/>',
         f'<text x="22" y="106" class="ui" font-size="14"><tspan {muted}>Subject:  </tspan>'
         f'<tspan font-weight="600" {ink}>let’s build something ♡</tspan></text>',
         f'<rect x="22" y="120" width="{w - 44}" height="1" {line}/>',
         text(22, 154, "Feel free to reach out for collaborations,", "ui", f'font-size="15" {ink}'),
         text(22, 178, "questions, or just to say hi!", "ui", f'font-size="15" {ink}'),
         f'<rect x="{w - 104}" y="{h - 50}" width="82" height="32" rx="16" style="fill:var(--blue)"/>',
         text(w - 63, h - 29, "Send ↗", "ui", 'text-anchor="middle" font-size="13" font-weight="700" style="fill:var(--btn-text)"'),
         "</g>"]
    card("mail", 560, 280, "".join(b),
         "New Message — To: codesluli@gmail.com · Subject: let’s build something ♡ · "
         "Feel free to reach out for collaborations, questions, or just to say hi!")


if __name__ == "__main__":
    print("building cards -> luisacoded/cards/")
    terminal()
    device()
    mail()
