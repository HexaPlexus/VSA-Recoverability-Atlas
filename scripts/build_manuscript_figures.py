from __future__ import annotations

import csv
import json
import math
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"
FIG_DIR = PAPER_DIR / "figures"


FONT_5X7 = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00100", "01000", "10000", "00000", "00000"],
    ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00110", "00110"],
    "%": ["11001", "11010", "00100", "01000", "10110", "00110", "00000"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "11100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00001", "00001", "00001", "00001", "10001", "10001", "01110"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}


PALETTE = {
    "bg": (248, 249, 251),
    "ink": (28, 34, 43),
    "muted": (108, 122, 137),
    "grid": (215, 221, 230),
    "blue": (42, 109, 198),
    "teal": (40, 151, 151),
    "green": (59, 145, 78),
    "orange": (214, 121, 36),
    "red": (194, 67, 67),
    "violet": (120, 90, 180),
    "yellow": (225, 180, 52),
    "slate": (85, 96, 110),
    "white": (255, 255, 255),
}


STATUS_COLORS = {
    "REPRODUCED_IN_REPO": "#2A6DC6",
    "PARTIALLY_REPRODUCED": "#D67924",
    "PAPER_REPRODUCTION": "#3B914E",
    "IMPLEMENTATION_AUDITED": "#289797",
    "LITERATURE_ONLY": "#785AB4",
    "DESIGN_ONLY": "#6C7A89",
    "DEFERRED_HYPOTHESIS": "#E1B434",
    "BLOCKED_WITH_EVIDENCE": "#C24343",
    "ADOPTED_ENGINEERING_BASELINE": "#355E95",
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def fmt_svg_number(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    rounded = round(float(value), 6)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.6f}".rstrip("0").rstrip(".")


def deterministic_zlib_store(data: bytes) -> bytes:
    stream = bytearray(b"\x78\x01")
    offset = 0
    while offset < len(data):
        chunk = data[offset : offset + 65535]
        offset += len(chunk)
        final_flag = 1 if offset >= len(data) else 0
        stream.append(final_flag)
        stream.extend(struct.pack("<H", len(chunk)))
        stream.extend(struct.pack("<H", 0xFFFF - len(chunk)))
        stream.extend(chunk)
    stream.extend(struct.pack(">I", zlib.adler32(data) & 0xFFFFFFFF))
    return bytes(stream)


class SvgFigure:
    def __init__(self, width: int, height: int, title: str):
        self.width = width
        self.height = height
        self.title = title
        self.parts: list[str] = []
        self.rect(0, 0, width, height, fill=rgb_hex(PALETTE["bg"]), stroke="none")

    def rect(self, x, y, w, h, fill, stroke="#000000", stroke_width=1, rx=0):
        self.parts.append(
            f'<rect x="{fmt_svg_number(x)}" y="{fmt_svg_number(y)}" width="{fmt_svg_number(w)}" height="{fmt_svg_number(h)}" rx="{fmt_svg_number(rx)}" fill="{fill}" stroke="{stroke}" stroke-width="{fmt_svg_number(stroke_width)}"/>'
        )

    def line(self, x1, y1, x2, y2, stroke="#000000", stroke_width=2, dash: str | None = None):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{fmt_svg_number(x1)}" y1="{fmt_svg_number(y1)}" x2="{fmt_svg_number(x2)}" y2="{fmt_svg_number(y2)}" stroke="{stroke}" stroke-width="{fmt_svg_number(stroke_width)}"{dash_attr}/>'
        )

    def polyline(self, pts: list[tuple[float, float]], stroke="#000000", stroke_width=2, fill="none"):
        data = " ".join(f"{fmt_svg_number(x)},{fmt_svg_number(y)}" for x, y in pts)
        self.parts.append(
            f'<polyline points="{data}" fill="{fill}" stroke="{stroke}" stroke-width="{fmt_svg_number(stroke_width)}"/>'
        )

    def circle(self, x, y, r, fill, stroke="#000000", stroke_width=1):
        self.parts.append(
            f'<circle cx="{fmt_svg_number(x)}" cy="{fmt_svg_number(y)}" r="{fmt_svg_number(r)}" fill="{fill}" stroke="{stroke}" stroke-width="{fmt_svg_number(stroke_width)}"/>'
        )

    def text(self, x, y, text: str, size=16, fill="#000000", anchor="start", weight="normal"):
        safe = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        self.parts.append(
            f'<text x="{fmt_svg_number(x)}" y="{fmt_svg_number(y)}" fill="{fill}" font-size="{fmt_svg_number(size)}" font-family="Segoe UI, Arial, sans-serif" font-weight="{weight}" text-anchor="{anchor}">{safe}</text>'
        )

    def arrow(self, x1, y1, x2, y2, stroke="#000000", stroke_width=2):
        self.line(x1, y1, x2, y2, stroke=stroke, stroke_width=stroke_width)
        ang = math.atan2(y2 - y1, x2 - x1)
        size = 8
        left = (x2 - size * math.cos(ang - math.pi / 6), y2 - size * math.sin(ang - math.pi / 6))
        right = (x2 - size * math.cos(ang + math.pi / 6), y2 - size * math.sin(ang + math.pi / 6))
        self.polyline([left, (x2, y2), right], stroke=stroke, stroke_width=stroke_width, fill="none")

    def save(self, path: Path) -> None:
        body = "\n".join(self.parts)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt_svg_number(self.width)}" height="{fmt_svg_number(self.height)}" viewBox="0 0 {fmt_svg_number(self.width)} {fmt_svg_number(self.height)}">\n'
            f"<title>{self.title}</title>\n{body}\n</svg>\n",
            encoding="utf-8",
        )


class RasterFigure:
    def __init__(self, width: int, height: int, bg: tuple[int, int, int]):
        self.width = width
        self.height = height
        self.pixels = [[list(bg) for _ in range(width)] for _ in range(height)]

    def set_px(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = list(color)

    def rect(self, x: int, y: int, w: int, h: int, fill: tuple[int, int, int], border: tuple[int, int, int] | None = None) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set_px(xx, yy, fill)
        if border:
            for xx in range(x, x + w):
                self.set_px(xx, y, border)
                self.set_px(xx, y + h - 1, border)
            for yy in range(y, y + h):
                self.set_px(x, yy, border)
                self.set_px(x + w - 1, yy, border)

    def line(self, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int], thickness: int = 1) -> None:
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        x, y = x1, y1
        while True:
            for ox in range(-(thickness // 2), thickness // 2 + 1):
                for oy in range(-(thickness // 2), thickness // 2 + 1):
                    self.set_px(x + ox, y + oy, color)
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx: int, cy: int, r: int, color: tuple[int, int, int]) -> None:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set_px(x, y, color)

    def text(self, x: int, y: int, text: str, color: tuple[int, int, int], scale: int = 2) -> None:
        cursor = x
        for ch in text.upper():
            glyph = FONT_5X7.get(ch, FONT_5X7[" "])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        for sy in range(scale):
                            for sx in range(scale):
                                self.set_px(cursor + gx * scale + sx, y + gy * scale + sy, color)
            cursor += (5 + 1) * scale

    def save_png(self, path: Path) -> None:
        raw = bytearray()
        for row in self.pixels:
            raw.append(0)
            for pixel in row:
                raw.extend(pixel)
        payload = deterministic_zlib_store(bytes(raw))

        def chunk(name: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

        png = bytearray()
        png.extend(b"\x89PNG\r\n\x1a\n")
        png.extend(chunk(b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)))
        png.extend(chunk(b"IDAT", payload))
        png.extend(chunk(b"IEND", b""))
        path.write_bytes(bytes(png))


@dataclass
class FigureBundle:
    svg: SvgFigure
    png: RasterFigure


def make_bundle(width: int, height: int, title: str) -> FigureBundle:
    return FigureBundle(SvgFigure(width, height, title), RasterFigure(width, height, PALETTE["bg"]))


def draw_box(bundle: FigureBundle, x: int, y: int, w: int, h: int, label_svg: list[str], label_png: str, fill: str, fill_rgb: tuple[int, int, int]) -> None:
    bundle.svg.rect(x, y, w, h, fill=fill, stroke=rgb_hex(PALETTE["ink"]), stroke_width=1, rx=12)
    bundle.png.rect(x, y, w, h, fill_rgb, PALETTE["ink"])
    sy = y + 28
    for line in label_svg:
        bundle.svg.text(x + w / 2, sy, line, size=18, fill=rgb_hex(PALETTE["ink"]), anchor="middle", weight="bold")
        sy += 22
    bundle.png.text(x + 12, y + h // 2 - 8, label_png, PALETTE["ink"], scale=2)


def add_title(bundle: FigureBundle, title: str, subtitle: str) -> None:
    bundle.svg.text(24, 34, title, size=24, fill=rgb_hex(PALETTE["ink"]), weight="bold")
    bundle.svg.text(24, 58, subtitle, size=13, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(16, 12, title.upper(), PALETTE["ink"], scale=2)


def figure1_budget_map() -> None:
    bundle = make_bundle(1200, 700, "Recoverability budget map")
    add_title(bundle, "Figure 1. Recoverability budget map", "Conceptual workflow. Not a measured result.")
    fill1 = "#dce9fa"
    fill2 = "#dbf1f1"
    fill3 = "#e7f4e6"
    fill4 = "#fff1dc"
    fill5 = "#f5e8fb"
    draw_box(bundle, 60, 120, 210, 100, ["Task and", "risk contract"], "CONTRACT", fill1, (220, 233, 250))
    draw_box(bundle, 330, 120, 220, 100, ["Budget", "allocation"], "BUDGET", fill2, (219, 241, 241))
    draw_box(bundle, 620, 70, 220, 100, ["Representation", "and decoder"], "REP DEC", fill3, (231, 244, 230))
    draw_box(bundle, 620, 190, 220, 100, ["Verification", "and abstention"], "VERIFY", fill4, (255, 241, 220))
    draw_box(bundle, 910, 70, 220, 100, ["Accepted", "result"], "ACCEPT", fill5, (245, 232, 251))
    draw_box(bundle, 910, 190, 220, 100, ["Fallback or", "abstention"], "FALLBACK", "#f9e0e0", (249, 224, 224))
    bundle.svg.arrow(270, 170, 330, 170, stroke=rgb_hex(PALETTE["blue"]))
    bundle.svg.arrow(550, 145, 620, 120, stroke=rgb_hex(PALETTE["blue"]))
    bundle.svg.arrow(550, 195, 620, 240, stroke=rgb_hex(PALETTE["blue"]))
    bundle.svg.arrow(840, 120, 910, 120, stroke=rgb_hex(PALETTE["green"]))
    bundle.svg.arrow(840, 240, 910, 240, stroke=rgb_hex(PALETTE["orange"]))
    bundle.png.line(270, 170, 330, 170, PALETTE["blue"], 3)
    bundle.png.line(550, 145, 620, 120, PALETTE["blue"], 3)
    bundle.png.line(550, 195, 620, 240, PALETTE["blue"], 3)
    bundle.png.line(840, 120, 910, 120, PALETTE["green"], 3)
    bundle.png.line(840, 240, 910, 240, PALETTE["orange"], 3)
    bundle.svg.text(340, 340, "R1-R14 identify where additional authority or cost is paid.", size=17, fill=rgb_hex(PALETTE["muted"]))
    bundle.svg.text(340, 366, "Promote extra mechanisms only if they create a verified nondominated point.", size=17, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(200, 320, "R1 TO R14 TRACK COST", PALETTE["muted"], scale=2)
    bundle.png.text(120, 350, "PROMOTE ONLY NONDOMINATED MECHANISMS", PALETTE["muted"], scale=2)
    bundle.svg.save(FIG_DIR / "figure1_budget_map.svg")
    bundle.png.save_png(FIG_DIR / "figure1_budget_map.png")


def figure2_evidence_atlas() -> None:
    payload = load_json(PAPER_DIR / "evidence_registry.yaml")
    entries = payload["entries"]
    bundle = make_bundle(1400, 900, "Evidence atlas overview")
    add_title(bundle, "Figure 2. Repository evidence atlas overview", "Twenty-four normalized repository hypotheses grouped by category and colored by evidence status.")
    cols = 4
    cell_w, cell_h = 300, 110
    start_x, start_y = 40, 110
    for idx, entry in enumerate(entries):
        col = idx % cols
        row = idx // cols
        x = start_x + col * 335
        y = start_y + row * 125
        fill = STATUS_COLORS.get(entry["evidence_status"], "#cccccc")
        fill_rgb = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
        title = entry["title"].split(":")[0][:28]
        dispo = entry["architectural_disposition"][:26]
        bundle.svg.rect(x, y, cell_w, cell_h, fill=fill, stroke=rgb_hex(PALETTE["ink"]), stroke_width=1, rx=10)
        bundle.svg.text(x + 12, y + 24, f"{idx + 1:02d}. {entry['hypothesis_id']}", size=13, fill=rgb_hex(PALETTE["white"]), weight="bold")
        bundle.svg.text(x + 12, y + 48, title, size=16, fill=rgb_hex(PALETTE["white"]), weight="bold")
        bundle.svg.text(x + 12, y + 72, f"Category: {entry['category']}", size=12, fill=rgb_hex(PALETTE["white"]))
        bundle.svg.text(x + 12, y + 92, f"Disposition: {dispo}", size=12, fill=rgb_hex(PALETTE["white"]))
        bundle.png.rect(x, y, cell_w, cell_h, fill_rgb, PALETTE["ink"])
        bundle.png.text(x + 8, y + 8, f"{idx+1:02d}", PALETTE["white"], scale=2)
        bundle.png.text(x + 8, y + 26, entry["evidence_status"][:12].replace("_", ""), PALETTE["white"], scale=1)
    legend_y = 820
    lx = 40
    for status, fill in list(STATUS_COLORS.items())[:5] + list(STATUS_COLORS.items())[5:]:
        fill_rgb = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
        bundle.svg.rect(lx, legend_y, 18, 18, fill=fill, stroke="none")
        bundle.svg.text(lx + 28, legend_y + 14, status, size=12, fill=rgb_hex(PALETTE["ink"]))
        bundle.png.rect(lx, legend_y, 18, 18, fill_rgb, fill_rgb)
        bundle.png.text(lx + 24, legend_y + 2, status[:12].replace("_", ""), PALETTE["ink"], scale=1)
        lx += 150
    bundle.svg.save(FIG_DIR / "figure2_evidence_atlas.svg")
    bundle.png.save_png(FIG_DIR / "figure2_evidence_atlas.png")


def figure3_capacity_frontier() -> None:
    rows = load_csv(ROOT / "results" / "level3_2" / "recovery_summary.csv")
    wanted = {(10, "MAP", "map_d512"), (10, "MAP", "map_d1024"), (10, "BCF", "bcf_d512_f3_b4"),
              (22, "MAP", "map_d512"), (22, "MAP", "map_d1024"), (22, "BCF", "bcf_d512_f3_b4"),
              (31, "MAP", "map_d512"), (31, "MAP", "map_d1024"), (31, "BCF", "bcf_d512_f3_b4"),
              (68, "MAP", "map_d512"), (68, "MAP", "map_d1024"), (68, "BCF", "bcf_d512_f3_b4")}
    series = {"MAP D512": [], "MAP D1024": [], "BCF": []}
    for row in rows:
        key = (int(row["domain_size"]), row["substrate"], row["config_id"])
        if key in wanted:
            label = "BCF" if row["substrate"] == "BCF" else ("MAP D512" if row["config_id"] == "map_d512" else "MAP D1024")
            series[label].append((int(row["domain_size"]), float(row["exact_recovery_rate"])))
    for label in series:
        series[label].sort()

    bundle = make_bundle(1100, 760, "Clean F=3 capacity frontier")
    add_title(bundle, "Figure 3. Clean F=3 capacity frontier", "Frozen common-envelope results from results/level3_2/recovery_summary.csv.")
    left, top, width, height = 90, 120, 900, 520
    bundle.svg.line(left, top + height, left + width, top + height, stroke=rgb_hex(PALETTE["ink"]), stroke_width=2)
    bundle.svg.line(left, top, left, top + height, stroke=rgb_hex(PALETTE["ink"]), stroke_width=2)
    bundle.png.line(left, top + height, left + width, top + height, PALETTE["ink"], 2)
    bundle.png.line(left, top, left, top + height, PALETTE["ink"], 2)
    xvals = [10, 22, 31, 68]
    colors = {"MAP D512": PALETTE["orange"], "MAP D1024": PALETTE["blue"], "BCF": PALETTE["green"]}
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = top + height - tick * height
        bundle.svg.line(left, y, left + width, y, stroke=rgb_hex(PALETTE["grid"]), stroke_width=1)
        bundle.svg.text(left - 12, y + 4, f"{tick:.2f}", size=12, fill=rgb_hex(PALETTE["muted"]), anchor="end")
        bundle.png.line(left, int(y), left + width, int(y), PALETTE["grid"], 1)
        bundle.png.text(8, int(y) - 5, f"{tick:.2f}", PALETTE["muted"], scale=1)
    for xv in xvals:
        x = left + (math.log10(xv) - math.log10(10)) / (math.log10(68) - math.log10(10)) * width
        bundle.svg.line(x, top, x, top + height, stroke=rgb_hex(PALETTE["grid"]), stroke_width=1)
        bundle.svg.text(x, top + height + 22, str(xv), size=12, fill=rgb_hex(PALETTE["muted"]), anchor="middle")
        bundle.png.line(int(x), top, int(x), top + height, PALETTE["grid"], 1)
        bundle.png.text(int(x) - 6, top + height + 8, str(xv), PALETTE["muted"], scale=1)

    for label, pts in series.items():
        svg_pts = []
        color = colors[label]
        for xval, yval in pts:
            x = left + (math.log10(xval) - math.log10(10)) / (math.log10(68) - math.log10(10)) * width
            y = top + height - yval * height
            svg_pts.append((x, y))
            bundle.svg.circle(x, y, 5, fill=rgb_hex(color), stroke=rgb_hex(color))
            bundle.png.circle(int(x), int(y), 4, color)
        bundle.svg.polyline(svg_pts, stroke=rgb_hex(color), stroke_width=3)
        for (x1, y1), (x2, y2) in zip(svg_pts, svg_pts[1:]):
            bundle.png.line(int(x1), int(y1), int(x2), int(y2), color, 2)
    legend_x = 740
    for idx, label in enumerate(["MAP D512", "MAP D1024", "BCF"]):
        cy = 150 + idx * 24
        bundle.svg.circle(legend_x, cy, 6, fill=rgb_hex(colors[label]), stroke=rgb_hex(colors[label]))
        bundle.svg.text(legend_x + 14, cy + 4, label, size=13, fill=rgb_hex(PALETTE["ink"]))
        bundle.png.circle(legend_x, cy, 5, colors[label])
        bundle.png.text(legend_x + 14, cy - 6, label.replace(" ", ""), PALETTE["ink"], scale=1)
    bundle.svg.text(90, 690, "X-axis uses common-envelope domain size M (log-scaled spacing only for readability).", size=13, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(60, 690, "DOMAIN SIZE M", PALETTE["muted"], scale=2)
    bundle.svg.save(FIG_DIR / "figure3_clean_f3_frontier.svg")
    bundle.png.save_png(FIG_DIR / "figure3_clean_f3_frontier.png")


def figure4_repair_costs() -> None:
    rows = load_csv(ROOT / "results" / "codebook_residue_v0_1" / "arm_summary.csv")
    chosen = []
    wanted = {
        ("A_MAP_B_HARD", "sign_only"): "HARD MAP",
        ("C_SCALAR_RESIDUE_EQUAL_RATE", "scalar_zlib_4level"): "SCALAR",
        ("E_BLOCK_CODEBOOK_C16", "C16"): "BLOCK C16",
        ("H_EQUAL_TOTAL_BIT_MAP_B", "equal_bits_for_C16"): "EXTRA-D",
        ("G_MAP_I_EXACT_ACCUMULATOR", "exact_accumulator_k31"): "MAP-I",
    }
    for row in rows:
        key = (row["arm_id"], row["variant_id"])
        if row["split_name"] == "FINAL_DEVELOPMENT_EVALUATION" and row["bundle_width"] == "31" and key in wanted:
            chosen.append(
                (
                    wanted[key],
                    float(row["mean_physical_bits_total"]),
                    float(row["mean_full_member_enumeration_recall"]),
                )
            )
    bundle = make_bundle(1100, 760, "Repair methods cost")
    add_title(bundle, "Figure 4. Where repair methods paid their cost", "Final K=31 residue and equal-bit controls from results/codebook_residue_v0_1/arm_summary.csv.")
    left, top, width, height = 110, 120, 880, 520
    max_x = max(x for _, x, _ in chosen) * 1.08
    colors = [PALETTE["slate"], PALETTE["orange"], PALETTE["teal"], PALETTE["blue"], PALETTE["green"]]
    bundle.svg.line(left, top + height, left + width, top + height, stroke=rgb_hex(PALETTE["ink"]), stroke_width=2)
    bundle.svg.line(left, top, left, top + height, stroke=rgb_hex(PALETTE["ink"]), stroke_width=2)
    bundle.png.line(left, top + height, left + width, top + height, PALETTE["ink"], 2)
    bundle.png.line(left, top, left, top + height, PALETTE["ink"], 2)
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = top + height - tick * height
        bundle.svg.line(left, y, left + width, y, stroke=rgb_hex(PALETTE["grid"]), stroke_width=1)
        bundle.svg.text(left - 12, y + 4, f"{tick:.2f}", size=12, fill=rgb_hex(PALETTE["muted"]), anchor="end")
        bundle.png.line(left, int(y), left + width, int(y), PALETTE["grid"], 1)
    for idx, tick in enumerate([1000, 2000, 3000, 4000, 5000, 6000]):
        x = left + tick / max_x * width
        bundle.svg.line(x, top, x, top + height, stroke=rgb_hex(PALETTE["grid"]), stroke_width=1)
        bundle.svg.text(x, top + height + 22, str(tick), size=12, fill=rgb_hex(PALETTE["muted"]), anchor="middle")
        bundle.png.line(int(x), top, int(x), top + height, PALETTE["grid"], 1)
    for idx, (label, bits, recall) in enumerate(chosen):
        x = left + bits / max_x * width
        y = top + height - recall * height
        color = colors[idx]
        bundle.svg.circle(x, y, 8, fill=rgb_hex(color), stroke=rgb_hex(PALETTE["ink"]), stroke_width=1)
        bundle.svg.text(x + 12, y + 4, label, size=13, fill=rgb_hex(PALETTE["ink"]))
        bundle.png.circle(int(x), int(y), 6, color)
        bundle.png.text(int(x) + 12, int(y) - 6, label.replace(" ", ""), PALETTE["ink"], scale=1)
    bundle.svg.text(110, 690, "Y-axis: full member enumeration recall. X-axis: physical bits per bundle.", size=13, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(140, 690, "BITS PER BUNDLE", PALETTE["muted"], scale=2)
    bundle.svg.save(FIG_DIR / "figure4_repair_costs.svg")
    bundle.png.save_png(FIG_DIR / "figure4_repair_costs.png")


def figure5_escalation() -> None:
    rows = load_csv(ROOT / "results" / "oracle_portfolio_v0_1" / "method_summary.csv")
    final_non_easy = {row["method_id"]: row for row in rows if row["subset"] == "FINAL_NON_EASY"}
    map_fast = float(final_non_easy["MAP_D1024_FAST"]["median_latency_sec"])
    bcf = float(final_non_easy["BCF_NATIVE"]["median_latency_sec"])
    exit_rate = float(final_non_easy["MAP_D1024_FAST"]["accepted_exact_coverage"])
    break_even = map_fast / bcf
    cascade = map_fast + (1.0 - exit_rate) * bcf
    bundle = make_bundle(1100, 760, "Sequential escalation economics")
    add_title(bundle, "Figure 5. Sequential escalation economics", "Clean non-easy common F=3 cell. Measured p50 latencies from oracle portfolio summary.")
    labels = ["ACTUAL EXIT", "BREAK EVEN", "CASCADE", "ALWAYS BCF"]
    values = [exit_rate, break_even, cascade, bcf]
    is_rate = [True, True, False, False]
    colors = [PALETTE["blue"], PALETTE["orange"], PALETTE["violet"], PALETTE["green"]]
    left, top = 120, 150
    bar_w, gap = 170, 60
    rate_height = 230
    cost_height = 230
    for idx, label in enumerate(labels):
        x = left + idx * (bar_w + gap)
        if is_rate[idx]:
            h = values[idx] * rate_height
            y = top + rate_height - h
            bundle.svg.rect(x, y, bar_w, h, fill=rgb_hex(colors[idx]), stroke=rgb_hex(PALETTE["ink"]), stroke_width=1, rx=8)
            bundle.svg.text(x + bar_w / 2, top + rate_height + 24, label, size=13, fill=rgb_hex(PALETTE["ink"]), anchor="middle")
            bundle.svg.text(x + bar_w / 2, y - 8, f"{values[idx]:.3f}", size=13, fill=rgb_hex(PALETTE["ink"]), anchor="middle")
            bundle.png.rect(x, int(y), bar_w, int(h), colors[idx], PALETTE["ink"])
        else:
            h = values[idx] / 0.05 * cost_height
            y = 420 + cost_height - h
            bundle.svg.rect(x, y, bar_w, h, fill=rgb_hex(colors[idx]), stroke=rgb_hex(PALETTE["ink"]), stroke_width=1, rx=8)
            bundle.svg.text(x + bar_w / 2, 420 + cost_height + 24, label, size=13, fill=rgb_hex(PALETTE["ink"]), anchor="middle")
            bundle.svg.text(x + bar_w / 2, y - 8, f"{values[idx]:.4f}s", size=13, fill=rgb_hex(PALETTE["ink"]), anchor="middle")
            bundle.png.rect(x, int(y), bar_w, int(h), colors[idx], PALETTE["ink"])
        bundle.png.text(x + 10, (top + rate_height + 10) if is_rate[idx] else (420 + cost_height + 10), label.replace(" ", ""), PALETTE["ink"], scale=1)
    bundle.svg.text(120, 130, "Verified exit rates", size=18, fill=rgb_hex(PALETTE["ink"]), weight="bold")
    bundle.svg.text(120, 400, "Latency economics", size=18, fill=rgb_hex(PALETTE["ink"]), weight="bold")
    bundle.png.text(120, 120, "EXIT RATES", PALETTE["ink"], scale=2)
    bundle.png.text(120, 390, "LATENCY COSTS", PALETTE["ink"], scale=2)
    bundle.svg.text(120, 690, "Break-even uses p_exit > C_fast / C_fallback. Here 0.250 < 0.261, so the probe does not amortize.", size=13, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(70, 690, "0.250 IS BELOW 0.261 BREAK EVEN", PALETTE["muted"], scale=2)
    bundle.svg.save(FIG_DIR / "figure5_escalation.svg")
    bundle.png.save_png(FIG_DIR / "figure5_escalation.png")


def figure6_architecture_flow() -> None:
    bundle = make_bundle(1250, 760, "Architecture guide flow")
    add_title(bundle, "Figure 6. Resource-aware architectural decision flow", "Conceptual design guide synthesized from the evidence atlas.")
    boxes = [
        (60, 120, 240, 90, ["Define task", "and risk"], "DEFINE", "#dce9fa", (220, 233, 250)),
        (360, 120, 260, 90, ["Authoritative", "exact state?"], "EXACT", "#fff1dc", (255, 241, 220)),
        (700, 60, 260, 90, ["Exact sidecar", "or DAG replay"], "SIDECAR", "#e7f4e6", (231, 244, 230)),
        (700, 180, 260, 90, ["Approximate VSA", "semantic view"], "APPROX", "#dbf1f1", (219, 241, 241)),
        (1020, 60, 170, 90, ["Verify", "and accept"], "VERIFY", "#f5e8fb", (245, 232, 251)),
        (1020, 180, 170, 90, ["Native decoder", "or abstain"], "DECODER", "#f9e0e0", (249, 224, 224)),
        (700, 320, 260, 90, ["Fallback only", "if nondominated"], "FALLBACK", "#eef0f4", (238, 240, 244)),
        (1020, 320, 170, 90, ["Stop or", "document limit"], "STOP", "#f3e6cf", (243, 230, 207)),
    ]
    for x, y, w, h, lines, png_label, fill, fill_rgb in boxes:
        draw_box(bundle, x, y, w, h, lines, png_label, fill, fill_rgb)
    arrows = [
        (300, 165, 360, 165),
        (620, 150, 700, 105),
        (620, 180, 700, 225),
        (960, 105, 1020, 105),
        (960, 225, 1020, 225),
        (830, 270, 830, 320),
        (960, 365, 1020, 365),
    ]
    for x1, y1, x2, y2 in arrows:
        bundle.svg.arrow(x1, y1, x2, y2, stroke=rgb_hex(PALETTE["blue"]))
        bundle.png.line(x1, y1, x2, y2, PALETTE["blue"], 3)
    bundle.svg.text(68, 460, "Exact structure and approximate similarity are complementary channels.", size=17, fill=rgb_hex(PALETTE["muted"]))
    bundle.svg.text(68, 486, "Promote extra mechanisms only when they create a verified nondominated point.", size=17, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(70, 460, "EXACT AND APPROXIMATE CHANNELS ARE COMPLEMENTARY", PALETTE["muted"], scale=2)
    bundle.png.text(70, 490, "PROMOTE ONLY VERIFIED NONDOMINATED MECHANISMS", PALETTE["muted"], scale=2)
    bundle.svg.save(FIG_DIR / "figure6_architecture_flow.svg")
    bundle.png.save_png(FIG_DIR / "figure6_architecture_flow.png")


def main() -> None:
    ensure_dir(FIG_DIR)
    figure1_budget_map()
    figure2_evidence_atlas()
    figure3_capacity_frontier()
    figure4_repair_costs()
    figure5_escalation()
    figure6_architecture_flow()
    print("Generated manuscript figures in", FIG_DIR)


if __name__ == "__main__":
    main()
