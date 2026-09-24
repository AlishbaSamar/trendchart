from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
from PIL import Image, ImageDraw, ImageFont

SRC = ROOT / 'source_images' / 'monthly_traffic_source.webp'
OUT = ROOT / 'generated' / 'monthly_traffic_jan_aug_2026.png'
FONT_PATH = ROOT / 'fonts' / 'LiberationSans-Regular.ttf'

src = Image.open(SRC).convert('RGB')
assert src.size == (2048, 1073)

# Add one 2K band above because August Fecon (21,739) exceeds the source's 20K ceiling.
# The source chart remains a pixel-identical block, shifted down by this added band.
TOP = 100
W, H = 2708, src.height + TOP
base = Image.new('RGB', (W, H), 'white')
base.paste(src, (0, TOP))
draw = ImageDraw.Draw(base)

# Exact source value-to-pixel calibration, fitted from the existing labeled points.
axis_intercept = 983.580273
axis_slope = 0.0481314467

def source_y(value):
    return axis_intercept - axis_slope * value

def out_y(value):
    return source_y(value) + TOP

# Add the new 22K grid band above the untouched source chart.
grid_color = (249, 249, 249)
y_22k = out_y(22000)
draw.line((62, round(y_22k), W - 1, round(y_22k)), fill=grid_color, width=2)
axis_font = ImageFont.truetype(FONT_PATH, 20)
axis_color = (113, 113, 113)
draw.text((8, round(y_22k) - 11), '22K', font=axis_font, fill=axis_color)

# Continue the source horizontal grid into the appended right-side canvas.
source_grid_rows = [20, 116, 213, 308, 406, 503, 599, 694, 790, 886]
for sy in source_grid_rows:
    y = sy + TOP
    # Use a source-matched pale grid line.
    draw.line((2048, y, W - 1, y), fill=(249, 249, 249), width=1)
# Continue the zero baseline as a light dash pattern.
zero_y = round(out_y(0))
for x in range(2048, W, 6):
    draw.line((x, zero_y, min(x + 2, W - 1), zero_y), fill=(220, 220, 220), width=1)

# Render only the added chart content on a supersampled transparent layer.
S = 4
OX = 1830
overlay_hi = Image.new('RGBA', ((W - OX) * S, H * S), (0, 0, 0, 0))
d = ImageDraw.Draw(overlay_hi)
font_value = ImageFont.truetype(FONT_PATH, 22 * S)
font_date = ImageFont.truetype(FONT_PATH, 22 * S)

x_jun, x_jul, x_aug = 1880, 2210, 2540

# July and August exact Organic Traffic US values supplied by the user.
series = [
    # name, source June anchor, July, August, RGB
    ('Fecon', 286.5, 18047, 21739, (224, 4, 28, 255)),
    ('Virnig', 421.5, 19022, 12839, (239, 108, 190, 255)),
    ('FAE Group', 672.5, 7726, 7079, (4, 158, 8, 255)),
    ('Diamond Mowers', 619.0, 10722, 8939, (250, 187, 78, 255)),
    ('Loftness', 750.0, 4013, 3898, (198, 198, 198, 255)),
    ('Prinoth', 927.0, 1818, 1370, (8, 194, 209, 255)),
    ('Denis Cimaf', 935.8, 965, 1313, (252, 120, 6, 255)),
    ('Shearex', 972.0, 253, 326, (145, 80, 68, 255)),
    ('Mastodon', 982.0, 30, 61, (252, 178, 206, 255)),
]

for name, june_sy, july, august, color in series:
    pts = [
        ((x_jun - OX) * S, (june_sy + TOP) * S),
        ((x_jul - OX) * S, out_y(july) * S),
        ((x_aug - OX) * S, out_y(august) * S),
    ]
    d.line(pts, fill=color, width=4 * S, joint='curve')
    radius = 4 * S
    for px, py in pts[1:]:
        d.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)

TEXT = (48, 48, 48, 255)
DATE = (108, 108, 108, 255)

def centered(text, x, visible_top, font=font_value, fill=TEXT):
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = (x - OX) * S - tw / 2 - bbox[0]
    ty = visible_top * S - bbox[1]
    d.text((tx, ty), text, font=font, fill=fill)

# July labels.
centered('19,022', x_jul, 137)
centered('18,047', x_jul, 222)
centered('10,722', x_jul, 535)
centered('7,726', x_jul, 679)
centered('4,013', x_jul, 858)
centered('1,818', x_jul - 55, 963)
centered('965', x_jul + 58, 1008)
centered('253', x_jul - 48, 1042)
centered('30', x_jul + 57, 1087)

# August labels.
centered('21,739', x_aug, 6)
centered('12,839', x_aug, 433)
centered('8,939', x_aug, 622)
centered('7,079', x_aug, 709)
centered('3,898', x_aug, 864)
centered('1,370', x_aug - 58, 986)
centered('1,313', x_aug + 60, 1011)
centered('326', x_aug - 50, 1040)
centered('61', x_aug + 58, 1085)

# Month labels align with the source's date row after the added top band.
centered('Jul 26', x_jul, 1142, font=font_date, fill=DATE)
centered('Aug 26', x_aug, 1142, font=font_date, fill=DATE)

# Composite the antialiased overlay without resampling the source chart itself.
overlay = overlay_hi.resize((W - OX, H), Image.Resampling.LANCZOS)
region = base.crop((OX, 0, W, H)).convert('RGBA')
region = Image.alpha_composite(region, overlay)
base.paste(region.convert('RGB'), (OX, 0))

# Restore exact June label/date glyph pixels where new continuation strokes intersect them.
restore_rects_source = [
    (1875, 274, 1960, 300),   # Fecon
    (1875, 430, 1955, 455),   # Virnig
    (1875, 606, 1950, 632),   # Diamond Mowers
    (1875, 660, 1950, 685),   # FAE Group
    (1875, 737, 1950, 763),   # Loftness
    (1845, 895, 1925, 920),   # Denis Cimaf
    (1875, 923, 1930, 946),   # Prinoth
    (1875, 959, 1930, 983),   # Shearex
    (1875, 991, 1915, 1013),  # Mastodon
    (1840, 1038, 1920, 1062), # Jun 26
]
pix_src = src.load()
pix_out = base.load()
for x1, y1, x2, y2 in restore_rects_source:
    for sy in range(y1, y2):
        oy = sy + TOP
        for x in range(x1, x2):
            r, g, b = pix_src[x, sy]
            if max(r, g, b) < 242 and max(r, g, b) - min(r, g, b) < 24:
                pix_out[x, oy] = (r, g, b)

base.save(OUT, format='PNG', optimize=True)
print(OUT)
print('size', base.size)
print('22k_y', round(y_22k, 2), 'zero_y', zero_y)
print('july_y', {name: round(out_y(july), 2) for name, _, july, _, _ in series})
print('august_y', {name: round(out_y(august), 2) for name, _, _, august, _ in series})
