#!/usr/bin/env python3
"""Build the pixel-art SVG icons from luisacoded/pixels.src.txt.

Usage:  python3 tools/build-pixels.py

Each `@name` block in the source is a 16x16 grid. Every filled pixel gets a
1px ink outline on its empty 4-neighbours, except "line" colours (~ ! *) and
explicit ink (k), which are drawn as-is. Output: luisacoded/<name>.svg, with
light/dark colours switched via prefers-color-scheme.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "luisacoded" / "pixels.src.txt"
OUT = ROOT / "luisacoded"
SIZE = 16

# css variable -> (light, dark)
PALETTE = {
    "blue": ("#8FB6E6", "#5C8DD0"),
    "blue-2": ("#4F86C6", "#9CC3F0"),
    "django": ("#3E9A6C", "#2F8A5E"),
    "green": ("#9BD18B", "#6FAE6A"),
    "green-2": ("#6FAE6A", "#4E8A4C"),
    "ink": ("#2B3550", "#F3EDD8"),
    "navy": ("#2B3550", "#2B3550"),
    "orange": ("#F6A04D", "#F0A24A"),
    "pink": ("#FF9EDB", "#E070C0"),
    "pink-2": ("#E66BBF", "#B04F96"),
    "purple": ("#B98AF0", "#9A6BDB"),
    "purple-2": ("#9566D6", "#6E46AE"),
    "red": ("#F27C6B", "#E0614E"),
    "surface": ("#FFFFFF", "#2B3449"),
    "teal": ("#5FC9B9", "#3FA89A"),
    "teal-2": ("#3FA89A", "#2C7E73"),
    "ts": ("#4F86C6", "#3F6FA8"),
    "white": ("#FFFFFF", "#FFF8E6"),
    "yellow": ("#FFD66B", "#E8B93C"),
    "yellow-2": ("#F0B43C", "#B8892A"),
}

CHARS = {
    "k": "ink", "K": "navy",
    "w": "surface", "W": "white",
    "b": "blue", "B": "blue-2",
    "y": "yellow", "Y": "yellow-2", "o": "orange",
    "p": "pink", "P": "pink-2",
    "g": "green", "G": "green-2",
    "t": "teal", "E": "teal-2",
    "r": "red", "u": "purple", "U": "purple-2",
    "d": "django", "T": "ts",
    "~": "blue-2", "!": "red", "*": "orange",
}
NO_OUTLINE = set("~!*k")


def parse(text):
    icons, name, rows = {}, None, []
    for line in text.splitlines():
        line = line.rstrip()
        if line.startswith("#") or not line:
            continue
        if line.startswith("@"):
            name, rows = line[1:].strip(), []
            icons[name] = rows
            continue
        rows.append(line)
    for name, rows in icons.items():
        if len(rows) != SIZE or any(len(r) != SIZE for r in rows):
            raise SystemExit(f"@{name}: must be {SIZE}x{SIZE}")
        for r in rows:
            for c in r:
                if c != "." and c not in CHARS:
                    raise SystemExit(f"@{name}: unknown colour {c!r}")
    return icons


def pixel_grid(rows):
    """Colour grid (css variable names or None) with the ink outline added."""
    grid = [[None if c == "." else CHARS[c] for c in r] for r in rows]
    out = [row[:] for row in grid]
    for y in range(SIZE):
        for x in range(SIZE):
            if rows[y][x] == "." or rows[y][x] in NO_OUTLINE:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < SIZE and 0 <= ny < SIZE and grid[ny][nx] is None:
                    out[ny][nx] = "ink"
    return out


def grid_rects(grid):
    """One <rect> per horizontal run of the same colour."""
    rects = []
    for y, row in enumerate(grid):
        x = 0
        while x < SIZE:
            colour = row[x]
            start = x
            while x < SIZE and row[x] == colour:
                x += 1
            if colour:
                rects.append(
                    f'<rect x="{start}" y="{y}" width="{x - start}" height="1" '
                    f'style="fill:var(--d-{colour})"/>'
                )
    return "".join(rects)


def palette_css(names, selector="svg"):
    light = "".join(f"--d-{v}:{PALETTE[v][0]};" for v in names)
    dark = "".join(f"--d-{v}:{PALETTE[v][1]};" for v in names)
    return (
        f"{selector}{{{light}}}"
        f"@media (prefers-color-scheme: dark){{{selector}{{{dark}}}}}"
    )


def render(rows):
    grid = pixel_grid(rows)
    used = sorted({c for row in grid for c in row if c})
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" '
        f'shape-rendering="crispEdges"><style>{palette_css(used)}</style>'
        + grid_rects(grid)
        + "</svg>\n"
    )


def main():
    icons = parse(SRC.read_text(encoding="utf-8"))
    for name, rows in icons.items():
        (OUT / f"{name}.svg").write_text(render(rows), encoding="utf-8")
    print(f"built {len(icons)} icons -> {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
