import re
import csv
import math
from pathlib import Path
from xml.sax.saxutils import escape

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SUMMARY_DIR = BASE_DIR / "data" / "launch" / "summary"
INPUT_PATH = SUMMARY_DIR / "simulation.csv"
OUTPUT_PATH = SUMMARY_DIR / "equity-drawdown-curve.svg"
INPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{INPUT_PATH.relative_to(BASE_DIR)}"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_PATH.relative_to(BASE_DIR)}"

PORTFOLIO_NAME = "InstitutionsForeignDomestic"
DECIMALS = 2
WIDTH, HEIGHT = 1000, 760
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 110, 40, 60, 100
PANEL_GAP = 70
EQUITY_HEIGHT_RATIO = 0.6
Y_TICKS = 6
EQUITY_Y_TICKS = 9
LAKH = 100000

MARGIN_COLOR = "#000000"
LINE_COLOR = "#00008B"
DRAWDOWN_COLOR = "#8B0000"
GRID_COLOR = "#E0E0E0"
BACKGROUND = "#FFFFFF"
FONT = "font-family='Helvetica, Arial, sans-serif'"
PERIOD_PATTERN = re.compile(r"^(\d{4})_(0[1-9]|1[0-2])$")

def period_index(value):
    match = PERIOD_PATTERN.match(value or "")
    if not match:
        raise ValueError()
    return int(match[1]) * 12 + int(match[2]) - 1

def label(index):
    return f"{index // 12}-{index % 12 + 1:02}"

def build_curve():
    curve = []
    labels = {}
    previous_end = None
    previous_capital = None
    with open(INPUT_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"start", "end", "capital_start", "capital_end"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError()

        for row in reader:
            start_index = period_index(row["start"])
            end_index = period_index(row["end"])
            try:
                capital_start = float(row["capital_start"])
                capital_end = float(row["capital_end"])
            except (TypeError, ValueError):
                raise ValueError() from None
            if (
                end_index < start_index
                or not math.isfinite(capital_start)
                or not math.isfinite(capital_end)
                or capital_start <= 0
                or capital_end < 0
                or (previous_end is not None and start_index <= previous_end)
            ):
                raise ValueError()

            if not curve:
                curve.append((start_index, capital_start))
                labels[start_index] = label(start_index)
            elif not math.isclose(capital_start, previous_capital, abs_tol=0.01):
                raise ValueError()

            curve.append((end_index + 1, capital_end))
            labels[end_index + 1] = label(end_index)
            previous_end = end_index
            previous_capital = capital_end

    return (curve, labels) if len(curve) > 1 else ([], {})

def build_drawdown_curve(curve):
    drawdown = []
    peak = curve[0][1]
    for x, equity in curve:
        peak = max(peak, equity)
        drawdown.append((x, (equity / peak - 1) * 100))
    return drawdown

def nice_ticks(low, high, count):
    if high == low:
        high, low = high + 1, low - 1
    raw = (high - low) / (count - 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    first = math.floor(low / step)
    last = math.ceil(high / step)
    return [i * step for i in range(first, last + 1)]

def format_lakhs(value):
    lakhs = value / LAKH
    if lakhs == 0:
        return "0"
    text = f"{lakhs:g}" if lakhs == round(lakhs, 1) else f"{lakhs:.1f}"
    return f"{text}L"

def render_panel(data, sx, left, right, top, bottom, color, title, y_axis_label, value_fmt, x_labels=None, fill_baseline=None, y_ticks=Y_TICKS, floor_at_zero=False):
    plot_w = right - left
    plot_h = bottom - top

    low = 0 if floor_at_zero else min(v for _, v in data)
    ticks = nice_ticks(low, max(v for _, v in data), y_ticks)
    y_min, y_max = ticks[0], ticks[-1]

    def sy(y):
        return bottom - (y - y_min) / (y_max - y_min) * plot_h

    out = [
        f"<text x='{left}' y='{top - 14}' font-size='15' font-weight='bold' fill='{MARGIN_COLOR}' {FONT}>{escape(title)}</text>",
    ]

    for tick in ticks:
        y = sy(tick)
        out.append(f"<line x1='{left}' y1='{y:.2f}' x2='{right}' y2='{y:.2f}' stroke='{GRID_COLOR}'/>")
        out.append(f"<line x1='{left - 6}' y1='{y:.2f}' x2='{left}' y2='{y:.2f}' stroke='{MARGIN_COLOR}'/>")
        out.append(
            f"<text x='{left - 10}' y='{y + 4:.2f}' text-anchor='end' font-size='12' fill='{MARGIN_COLOR}' {FONT}>{value_fmt(tick)}</text>"
        )

    for x, _ in data:
        px = sx(x)
        out.append(f"<line x1='{px:.2f}' y1='{top}' x2='{px:.2f}' y2='{bottom}' stroke='{GRID_COLOR}'/>")
        if x_labels:
            out.append(f"<line x1='{px:.2f}' y1='{bottom}' x2='{px:.2f}' y2='{bottom + 6}' stroke='{MARGIN_COLOR}'/>")
            out.append(
                f"<text x='{px:.2f}' y='{bottom + 20}' text-anchor='end' font-size='12' fill='{MARGIN_COLOR}' "
                f"transform='rotate(-45 {px:.2f} {bottom + 20})' {FONT}>{x_labels[x]}</text>"
            )

    if fill_baseline is not None:
        baseline_y = sy(fill_baseline)
        area = [(sx(x), sy(v)) for x, v in data]
        path = f"M {area[0][0]:.2f},{baseline_y:.2f} " + " ".join(f"L {x:.2f},{y:.2f}" for x, y in area) + f" L {area[-1][0]:.2f},{baseline_y:.2f} Z"
        out.append(f"<path d='{path}' fill='{color}' fill-opacity='0.15' stroke='none'/>")

    points = " ".join(f"{sx(x):.2f},{sy(v):.2f}" for x, v in data)
    out.append(f"<polyline points='{points}' fill='none' stroke='{color}' stroke-width='2.5' stroke-linejoin='round'/>")
    for x, v in data:
        out.append(f"<circle cx='{sx(x):.2f}' cy='{sy(v):.2f}' r='3.5' fill='{color}'/>")

    out.append(f"<rect x='{left}' y='{top}' width='{plot_w}' height='{plot_h}' fill='none' stroke='{MARGIN_COLOR}' stroke-width='1.5'/>")
    out.append(
        f"<text x='22' y='{top + plot_h / 2}' text-anchor='middle' font-size='13' fill='{MARGIN_COLOR}' "
        f"transform='rotate(-90 22 {top + plot_h / 2})' {FONT}>{y_axis_label}</text>"
    )
    return out

def render_svg(name, curve, drawdown, labels):
    plot_w = WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    total_plot_h = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM - PANEL_GAP
    equity_h = round(total_plot_h * EQUITY_HEIGHT_RATIO)
    drawdown_h = total_plot_h - equity_h

    left = MARGIN_LEFT
    right = left + plot_w

    equity_top = MARGIN_TOP
    equity_bottom = equity_top + equity_h

    drawdown_top = equity_bottom + PANEL_GAP
    drawdown_bottom = drawdown_top + drawdown_h

    x_min, x_max = curve[0][0], curve[-1][0]

    def sx(x):
        return left + (x - x_min) / (x_max - x_min) * plot_w

    out = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{WIDTH}' height='{HEIGHT}' viewBox='0 0 {WIDTH} {HEIGHT}'>",
        f"<rect width='{WIDTH}' height='{HEIGHT}' fill='{BACKGROUND}'/>",
        f"<text x='{WIDTH / 2}' y='32' text-anchor='middle' font-size='20' font-weight='bold' fill='{MARGIN_COLOR}' {FONT}>{escape(name)}</text>",
    ]

    out += render_panel(
        curve, sx, left, right, equity_top, equity_bottom, LINE_COLOR,
        "Equity Curve", "Portfolio value", format_lakhs,
        y_ticks=EQUITY_Y_TICKS, floor_at_zero=True,
    )
    out += render_panel(
        drawdown, sx, left, right, drawdown_top, drawdown_bottom, DRAWDOWN_COLOR,
        "Drawdown", "Drawdown (%)", lambda v: f"{v:,.{DECIMALS}f}%",
        x_labels=labels, fill_baseline=0.0,
    )

    out.append(
        f"<text x='{left + plot_w / 2}' y='{HEIGHT - 10}' text-anchor='middle' font-size='13' fill='{MARGIN_COLOR}' {FONT}>Period end month (first point = portfolio start)</text>"
    )
    out.append("</svg>")
    return "\n".join(out)

def save_curve(curve, drawdown, labels):
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(render_svg(PORTFOLIO_NAME, curve, drawdown, labels))

def generate_curve():
    if not INPUT_PATH.is_file():
        raise FileNotFoundError()

    curve, labels = build_curve()
    if not curve:
        raise ValueError()

    drawdown = build_drawdown_curve(curve)
    save_curve(curve, drawdown, labels)

    print(f"Equity and drawdown curves generated and saved to {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        generate_curve()
    except Exception as e:
        print(f"ERROR : {e}")

if __name__ == "__main__":
    main()
