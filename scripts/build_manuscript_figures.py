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
    add_title(bundle, "Figure 1. Recoverability budget map", "Conceptual workflow. Verification gates acceptance.")
    draw_box(bundle, 50, 250, 180, 100, ["Task and", "risk contract"], "CONTRACT", "#dce9fa", (220, 233, 250))
    draw_box(bundle, 270, 250, 180, 100, ["Recoverability", "budget"], "BUDGET", "#dbf1f1", (219, 241, 241))
    draw_box(bundle, 490, 250, 230, 100, ["Representation", "and native decoder"], "REP DEC", "#e7f4e6", (231, 244, 230))
    draw_box(bundle, 770, 250, 190, 100, ["Independent", "verifier"], "VERIFY", "#fff1dc", (255, 241, 220))
    draw_box(bundle, 1010, 110, 150, 90, ["Accept"], "ACCEPT", "#f5e8fb", (245, 232, 251))
    draw_box(bundle, 1010, 250, 150, 90, ["Fallback"], "FALLBACK", "#f9e0e0", (249, 224, 224))
    draw_box(bundle, 1010, 390, 150, 90, ["Abstain"], "ABSTAIN", "#eef0f4", (238, 240, 244))
    for x1, y1, x2, y2, color in [
        (230, 300, 270, 300, PALETTE["blue"]),
        (450, 300, 490, 300, PALETTE["blue"]),
        (720, 300, 770, 300, PALETTE["blue"]),
        (960, 275, 1010, 155, PALETTE["green"]),
        (960, 300, 1010, 295, PALETTE["orange"]),
        (960, 325, 1010, 435, PALETTE["slate"]),
    ]:
        bundle.svg.arrow(x1, y1, x2, y2, stroke=rgb_hex(color))
        bundle.png.line(x1, y1, x2, y2, color, 3)
    bundle.svg.text(1015, 225, "yes", size=14, fill=rgb_hex(PALETTE["green"]), weight="bold")
    bundle.svg.text(975, 298, "retry", size=14, fill=rgb_hex(PALETTE["orange"]), anchor="end", weight="bold")
    bundle.svg.text(1015, 370, "no safe answer", size=14, fill=rgb_hex(PALETTE["slate"]), weight="bold")
    bundle.svg.text(110, 150, "Accepted results cannot bypass independent verification.", size=18, fill=rgb_hex(PALETTE["ink"]), weight="bold")
    bundle.svg.text(110, 520, "R1-R14 name where authority or cost is paid: dimension, precision, structure,", size=17, fill=rgb_hex(PALETTE["muted"]))
    bundle.svg.text(110, 546, "exact side information, context, compute, temporal state, fallback, or abstention.", size=17, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(90, 140, "ACCEPTANCE NEVER BYPASSES VERIFICATION", PALETTE["ink"], scale=2)
    bundle.png.text(90, 520, "R1 TO R14 TRACK WHERE COST MOVES", PALETTE["muted"], scale=2)
    bundle.svg.save(FIG_DIR / "figure1_budget_map.svg")
    bundle.png.save_png(FIG_DIR / "figure1_budget_map.png")


def figure2_evidence_atlas() -> None:
    payload = load_json(PAPER_DIR / "evidence_registry.yaml")
    entries = payload["entries"]
    status_counts: dict[str, int] = {}
    disposition_counts: dict[str, int] = {}
    for entry in entries:
        status_counts[entry["evidence_status"]] = status_counts.get(entry["evidence_status"], 0) + 1
        disposition_counts[entry["architectural_disposition"]] = disposition_counts.get(entry["architectural_disposition"], 0) + 1
    status_order = [
        "ADOPTED_ENGINEERING_BASELINE",
        "REPRODUCED_IN_REPO",
        "PARTIALLY_REPRODUCED",
        "PAPER_REPRODUCTION",
        "IMPLEMENTATION_AUDITED",
        "DEFERRED_HYPOTHESIS",
        "BLOCKED_WITH_EVIDENCE",
    ]
    disposition_palette = {
        "ADOPTED_ENGINEERING_BASELINE": PALETTE["blue"],
        "REPRODUCED_IN_REPO": PALETTE["green"],
        "PARTIALLY_REPRODUCED": PALETTE["teal"],
        "IMPLEMENTATION_AUDITED": PALETTE["violet"],
        "DEFERRED_HYPOTHESIS": PALETTE["yellow"],
        "BLOCKED_WITH_EVIDENCE": PALETTE["red"],
        "PAPER_REPRODUCTION": PALETTE["orange"],
    }
    bundle = make_bundle(1360, 860, "Evidence status summary")
    add_title(bundle, "Figure 2. Repository evidence status summary", "Descriptive derived summary from 24 normalized repository evidence entries.")
    panels = [
        ("Evidence status counts", 60, status_counts, status_order, STATUS_COLORS, 24),
        ("Architectural disposition counts", 700, disposition_counts, status_order, {k: rgb_hex(v) for k, v in disposition_palette.items()}, 24),
    ]
    for title, left, counts, order, color_map, label_limit in panels:
        panel_w = 560
        top = 150
        height = 560
        max_count = max(counts.values())
        bundle.svg.text(left, 120, title, size=20, fill=rgb_hex(PALETTE["ink"]), weight="bold")
        bundle.svg.line(left, top + height, left + panel_w, top + height, stroke=rgb_hex(PALETTE["ink"]), stroke_width=2)
        bundle.svg.line(left, top, left, top + height, stroke=rgb_hex(PALETTE["ink"]), stroke_width=2)
        bundle.png.line(left, top + height, left + panel_w, top + height, PALETTE["ink"], 2)
        bundle.png.line(left, top, left, top + height, PALETTE["ink"], 2)
        for tick in range(0, max_count + 1):
            y = top + height - tick / max_count * height
            bundle.svg.line(left, y, left + panel_w, y, stroke=rgb_hex(PALETTE["grid"]), stroke_width=1)
            bundle.svg.text(left - 10, y + 4, str(tick), size=12, fill=rgb_hex(PALETTE["muted"]), anchor="end")
            bundle.png.line(left, int(y), left + panel_w, int(y), PALETTE["grid"], 1)
        bar_w = 56
        gap = 18
        for idx, key in enumerate(order):
            count = counts.get(key, 0)
            x = left + 22 + idx * (bar_w + gap)
            h = 0 if max_count == 0 else count / max_count * (height - 30)
            y = top + height - h
            fill = color_map.get(key, "#cccccc")
            fill_rgb = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
            bundle.svg.rect(x, y, bar_w, h, fill=fill, stroke=rgb_hex(PALETTE["ink"]), stroke_width=1, rx=8)
            bundle.svg.text(x + bar_w / 2, y - 10, str(count), size=15, fill=rgb_hex(PALETTE["ink"]), anchor="middle", weight="bold")
            bundle.svg.text(x + bar_w / 2, top + height + 24, key[:label_limit].replace("_", " "), size=11, fill=rgb_hex(PALETTE["muted"]), anchor="middle")
            bundle.png.rect(int(x), int(y), bar_w, max(1, int(h)), fill_rgb, PALETTE["ink"])
            bundle.png.text(int(x + 8), top + height + 8, key[:8].replace("_", ""), PALETTE["muted"], scale=1)
    bundle.svg.text(60, 790, "This figure summarizes registry counts only; the full 24-entry per-hypothesis atlas remains supplementary.", size=14, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(60, 790, "FULL 24 ENTRY ATLAS REMAINS IN THE SUPPLEMENT", PALETTE["muted"], scale=2)
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
            series[label].append(
                (
                    int(row["domain_size"]),
                    float(row["exact_recovery_rate"]),
                    float(row["exact_recovery_ci_low"]),
                    float(row["exact_recovery_ci_high"]),
                    int(row["trials"]),
                )
            )
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
        for xval, yval, ci_low, ci_high, trials in pts:
            x = left + (math.log10(xval) - math.log10(10)) / (math.log10(68) - math.log10(10)) * width
            y = top + height - yval * height
            y_low = top + height - ci_low * height
            y_high = top + height - ci_high * height
            svg_pts.append((x, y))
            bundle.svg.line(x, y_low, x, y_high, stroke=rgb_hex(color), stroke_width=2)
            bundle.svg.line(x - 6, y_low, x + 6, y_low, stroke=rgb_hex(color), stroke_width=2)
            bundle.svg.line(x - 6, y_high, x + 6, y_high, stroke=rgb_hex(color), stroke_width=2)
            bundle.svg.circle(x, y, 5, fill=rgb_hex(color), stroke=rgb_hex(color))
            bundle.svg.text(x + 8, y - 8, f"n={trials}", size=11, fill=rgb_hex(PALETTE["muted"]))
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
    bundle.svg.text(left + width / 2, 700, "Domain size M", size=16, fill=rgb_hex(PALETTE["ink"]), anchor="middle", weight="bold")
    bundle.svg.text(26, top + height / 2, "Exact recovery rate", size=16, fill=rgb_hex(PALETTE["ink"]), weight="bold")
    bundle.svg.text(90, 690, "Scope: clean, F=3, single product. X spacing uses log10(M) only for readability.", size=13, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(60, 690, "DOMAIN SIZE M", PALETTE["muted"], scale=2)
    bundle.png.text(8, 100, "EXACT RECOVERY", PALETTE["ink"], scale=1)
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
        bundle.svg.text(x + 12, y - 2, label, size=13, fill=rgb_hex(PALETTE["ink"]), weight="bold")
        bundle.svg.text(x + 12, y + 16, f"{bits:.0f} bits | {recall:.3f}", size=12, fill=rgb_hex(PALETTE["muted"]))
        bundle.png.circle(int(x), int(y), 6, color)
        bundle.png.text(int(x) + 12, int(y) - 6, label.replace(" ", ""), PALETTE["ink"], scale=1)
    bundle.svg.text(left + width / 2, 700, "Physical bits per bundle", size=16, fill=rgb_hex(PALETTE["ink"]), anchor="middle", weight="bold")
    bundle.svg.text(24, top + height / 2, "Full-member enumeration recall", size=16, fill=rgb_hex(PALETTE["ink"]), weight="bold")
    bundle.svg.text(110, 690, "Equal-bit extra dimensions and scalar residue remain the key engineering controls for this plot.", size=13, fill=rgb_hex(PALETTE["muted"]))
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
    bundle = make_bundle(1140, 780, "Sequential escalation economics")
    add_title(bundle, "Figure 5. Sequential escalation economics", "Clean non-easy common F=3 cell. Panel A uses rates; Panel B uses seconds.")
    bundle.svg.text(100, 120, "Panel A. Verified exit versus break-even exit", size=20, fill=rgb_hex(PALETTE["ink"]), weight="bold")
    bundle.svg.text(100, 420, "Panel B. Expected cascade latency versus always-BCF latency", size=20, fill=rgb_hex(PALETTE["ink"]), weight="bold")
    bundle.png.text(100, 110, "PANEL A EXIT RATES", PALETTE["ink"], scale=2)
    bundle.png.text(100, 410, "PANEL B LATENCY", PALETTE["ink"], scale=2)
    # Panel A
    left = 130
    top = 150
    rate_height = 190
    rate_labels = [("Actual verified exit", exit_rate, PALETTE["blue"]), ("Break-even exit", break_even, PALETTE["orange"])]
    for idx, (label, value, color) in enumerate(rate_labels):
        x = left + idx * 260
        h = value * rate_height
        y = top + rate_height - h
        bundle.svg.rect(x, y, 180, h, fill=rgb_hex(color), stroke=rgb_hex(PALETTE["ink"]), stroke_width=1, rx=8)
        bundle.svg.text(x + 90, top + rate_height + 24, label, size=13, fill=rgb_hex(PALETTE["ink"]), anchor="middle")
        bundle.svg.text(x + 90, y - 8, f"{value:.3f}", size=14, fill=rgb_hex(PALETTE["ink"]), anchor="middle", weight="bold")
        bundle.png.rect(x, int(y), 180, max(1, int(h)), color, PALETTE["ink"])
        bundle.png.text(x + 12, top + rate_height + 8, label.split()[0].upper(), PALETTE["ink"], scale=1)
    bundle.svg.text(640, 255, "Observed exit stays below the break-even threshold.", size=15, fill=rgb_hex(PALETTE["muted"]))
    bundle.svg.text(640, 278, f"0.250 < {break_even:.3f}", size=18, fill=rgb_hex(PALETTE["red"]), weight="bold")
    # Panel B
    cost_top = 450
    cost_height = 190
    scale_max = max(cascade, bcf) * 1.2
    cost_labels = [("Expected cascade", cascade, PALETTE["violet"]), ("Always BCF", bcf, PALETTE["green"])]
    for idx, (label, value, color) in enumerate(cost_labels):
        x = left + idx * 260
        h = value / scale_max * cost_height
        y = cost_top + cost_height - h
        bundle.svg.rect(x, y, 180, h, fill=rgb_hex(color), stroke=rgb_hex(PALETTE["ink"]), stroke_width=1, rx=8)
        bundle.svg.text(x + 90, cost_top + cost_height + 24, label, size=13, fill=rgb_hex(PALETTE["ink"]), anchor="middle")
        bundle.svg.text(x + 90, y - 8, f"{value:.4f}s", size=14, fill=rgb_hex(PALETTE["ink"]), anchor="middle", weight="bold")
        bundle.png.rect(x, int(y), 180, max(1, int(h)), color, PALETTE["ink"])
        bundle.png.text(x + 12, cost_top + cost_height + 8, label.split()[0].upper(), PALETTE["ink"], scale=1)
    bundle.svg.text(640, 555, "Measured p50 costs imply that probing with MAP does not amortize on non-easy cells.", size=15, fill=rgb_hex(PALETTE["muted"]))
    bundle.svg.text(640, 578, f"Cascade {cascade:.4f}s > BCF {bcf:.4f}s", size=18, fill=rgb_hex(PALETTE["red"]), weight="bold")
    bundle.svg.text(100, 715, "Break-even uses p_exit > C_fast / C_fallback. This plot supports sequential economics only.", size=13, fill=rgb_hex(PALETTE["muted"]))
    bundle.png.text(90, 715, "SEQUENTIAL ECONOMICS ONLY", PALETTE["muted"], scale=2)
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
    bundle.svg.text(645, 132, "yes", size=14, fill=rgb_hex(PALETTE["green"]), weight="bold")
    bundle.svg.text(645, 208, "no", size=14, fill=rgb_hex(PALETTE["orange"]), weight="bold")
    bundle.svg.text(970, 103, "verify", size=14, fill=rgb_hex(PALETTE["green"]), anchor="end", weight="bold")
    bundle.svg.text(970, 223, "decode or abstain", size=14, fill=rgb_hex(PALETTE["orange"]), anchor="end", weight="bold")
    bundle.svg.text(840, 310, "still worthwhile?", size=14, fill=rgb_hex(PALETTE["slate"]), anchor="middle", weight="bold")
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
