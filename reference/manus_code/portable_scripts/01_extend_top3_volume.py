from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
from PIL import Image, ImageDraw, ImageFont

SRC = ROOT / 'source_images' / 'top3_volume_source.webp'
OUT = ROOT / 'generated' / 'seo_volume_top3_jan_aug_2026.png'
FONT_PATH = ROOT / 'fonts' / 'LiberationSans-Regular.ttf'

src = Image.open(SRC).convert('RGB')
assert src.size == (2048, 1082)

# Preserve the original 2048x1082 source pixels and add two month-columns to the right.
W, H = 2713, 1082
base = Image.new('RGB', (W, H), 'white')
base.paste(src, (0, 0))
base_draw = ImageDraw.Draw(base)

# Continue the original horizontal grid across only the appended canvas.
grid_rows = {
    81: (254, 254, 254),
    191: (254, 254, 254),
    302: (252, 251, 252),
    412: (255, 255, 255),
    522: (248, 248, 248),
    633: (254, 254, 254),
    743: (255, 255, 255),
    853: (247, 247, 247),
}
for y, color in grid_rows.items():
    base_draw.line((2048, y, W - 1, y), fill=color, width=1)
# Continue the light dashed zero baseline.
for x in range(2048, W, 6):
    base_draw.line((x, 964, min(x + 2, W - 1), 964), fill=(220, 220, 220), width=1)

# Supersampled transparent overlay gives the same soft antialiasing as the source chart
# without resampling any of the untouched original pixels.
S = 4
OX = 1840
ow = W - OX
overlay_hi = Image.new('RGBA', (ow * S, H * S), (0, 0, 0, 0))
d = ImageDraw.Draw(overlay_hi)
font_value = ImageFont.truetype(FONT_PATH, 22 * S)
font_date = ImageFont.truetype(FONT_PATH, 22 * S)

x_jun, x_jul, x_aug = 1887, 2220, 2552
axis_intercept = 966.112159
axis_slope = 0.0022055747635574964

def y_for(value):
    return axis_intercept - axis_slope * value

# Exact July/August Volume-of-Top-3 values supplied by the user.
series = [
    # name, source June anchor y, July, August, color
    ('New Holland', 147.0, 376380, 372890, (150, 99, 188, 255)),
    ('Vermeer', 281.0, 301340, 306210, (135, 221, 135, 255)),
    ('FAE Group', 878.5, 52320, 53850, (10, 158, 18, 255)),
    ('Fecon', 832.5, 54720, 64210, (221, 7, 31, 255)),
    ('Diamond Mower', 878.5, 44620, 49850, (249, 185, 112, 255)),
    ('Virnig', 851.5, 50890, 33270, (239, 121, 200, 255)),
    ('Loftness', 947.0, 7630, 6730, (196, 196, 196, 255)),
    ('Prinoth', 959.0, 3050, 2870, (22, 190, 202, 255)),
    ('Denis Cimaf', 963.5, 1260, 1320, (255, 120, 16, 255)),
    ('Shearex', 965.5, 880, 1270, (255, 170, 152, 255)),
    ('Mastodon', 967.0, 100, 120, (250, 194, 202, 255)),
]

# Draw continuation strokes and point markers in the source chart's order/style.
for name, y0, july, august, color in series:
    pts = [
        ((x_jun - OX) * S, y0 * S),
        ((x_jul - OX) * S, y_for(july) * S),
        ((x_aug - OX) * S, y_for(august) * S),
    ]
    d.line(pts, fill=color, width=4 * S, joint='curve')
    radius = 4 * S
    for px, py in pts[1:]:
        d.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)

TEXT = (48, 48, 48, 255)
DATE = (108, 108, 108, 255)

def draw_centered(text, x, visible_top, font, fill):
    # Position by visible glyph bounds so new labels align with the source labels.
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = (x - OX) * S - tw / 2 - bbox[0]
    ty = visible_top * S - bbox[1]
    d.text((tx, ty), text, font=font, fill=fill)

# New Holland and Vermeer labels follow the source's above/below placement.
draw_centered('376,380', x_jul, 103, font_value, TEXT)
draw_centered('372,890', x_aug, 111, font_value, TEXT)
draw_centered('301,340', x_jul, 311, font_value, TEXT)
draw_centered('306,210', x_aug, 301, font_value, TEXT)

# Stagger the dense 30K-65K labels while retaining the original numeric style.
# July
draw_centered('54,720', x_jul - 47, 810, font_value, TEXT)
draw_centered('52,320', x_jul + 48, 831, font_value, TEXT)
draw_centered('50,890', x_jul - 47, 858, font_value, TEXT)
draw_centered('44,620', x_jul + 48, 881, font_value, TEXT)
# August
draw_centered('64,210', x_aug, 792, font_value, TEXT)
draw_centered('53,850', x_aug - 47, 836, font_value, TEXT)
draw_centered('49,850', x_aug + 48, 861, font_value, TEXT)
draw_centered('33,270', x_aug, 903, font_value, TEXT)

# Low-value labels use the same two-row staggering already present near the baseline.
# July
draw_centered('7,630', x_jul, 919, font_value, TEXT)
draw_centered('3,050', x_jul - 92, 976, font_value, TEXT)
draw_centered('880', x_jul + 72, 976, font_value, TEXT)
draw_centered('1,260', x_jul - 15, 1000, font_value, TEXT)
draw_centered('100', x_jul + 87, 1000, font_value, TEXT)
# August
draw_centered('6,730', x_aug, 919, font_value, TEXT)
draw_centered('2,870', x_aug - 92, 976, font_value, TEXT)
draw_centered('1,270', x_aug + 72, 976, font_value, TEXT)
draw_centered('1,320', x_aug - 15, 1000, font_value, TEXT)
draw_centered('120', x_aug + 87, 1000, font_value, TEXT)

# Month labels align with the source date-label row.
draw_centered('Jul 26', x_jul, 1044, font_date, DATE)
draw_centered('Aug 26', x_aug, 1044, font_date, DATE)

# Downsample only the new transparent drawing layer, then composite it.
overlay = overlay_hi.resize((ow, H), Image.Resampling.LANCZOS)
region = base.crop((OX, 0, W, H)).convert('RGBA')
region = Image.alpha_composite(region, overlay)
base.paste(region.convert('RGB'), (OX, 0))

# Restore exact June text pixels where continuation strokes cross existing labels.
# This preserves the original label glyphs without erasing the new line behind them.
restore_rects = [
    (1878, 132, 1980, 160),
    (1878, 268, 1980, 295),
    (1878, 798, 1962, 825),
    (1878, 840, 1963, 865),
    (1878, 886, 1962, 912),
    (1878, 934, 1955, 958),
    (1838, 970, 1920, 995),
    (1840, 1038, 1920, 1064),
]
pix_src = src.load()
pix_out = base.load()
for x1, y1, x2, y2 in restore_rects:
    for y in range(y1, y2):
        for x in range(x1, x2):
            r, g, b = pix_src[x, y]
            # Restore dark/gray antialiased glyph pixels; colored line pixels remain extended.
            if max(r, g, b) < 242 and max(r, g, b) - min(r, g, b) < 24:
                pix_out[x, y] = (r, g, b)

base.save(OUT, format='PNG', optimize=True)
print(OUT)
print('size', base.size)
print('july_y', {name: round(y_for(july), 2) for name, _, july, _, _ in series})
print('august_y', {name: round(y_for(august), 2) for name, _, _, august, _ in series})
