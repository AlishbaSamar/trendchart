from PIL import Image, ImageDraw, ImageFont

SRC = '/home/ubuntu/work/top100_extend/source.webp'
OUT = '/home/ubuntu/work/top100_extend/top_100_keywords_jan_aug_2026.png'
FONT_PATH = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'

src = Image.open(SRC).convert('RGB')
assert src.size == (2048, 1087)
W, H = 2727, 1087
base = Image.new('RGB', (W, H), 'white')
base.paste(src, (0, 0))
draw = ImageDraw.Draw(base)

# Continue the original horizontal grid and zero baseline into the appended canvas.
for y in [79, 228, 375, 522, 669, 816]:
    draw.line((2048, y, W - 1, y), fill=(249, 249, 249), width=1)
for x in range(2048, W, 6):
    draw.line((x, 963, min(x + 2, W - 1), 963), fill=(220, 220, 220), width=1)

# Source-chart value-to-pixel calibration.
axis_intercept = 963.0
axis_slope = 0.0294667

def y_for(value):
    return axis_intercept - axis_slope * value

S = 4
OX = 1830
overlay_hi = Image.new('RGBA', ((W - OX) * S, H * S), (0, 0, 0, 0))
d = ImageDraw.Draw(overlay_hi)
font_value = ImageFont.truetype(FONT_PATH, 22 * S)
font_date = ImageFont.truetype(FONT_PATH, 22 * S)

x_jun, x_jul, x_aug = 1892, 2226, 2560

# Exact July and August Top 100 keyword counts.
series = [
    # name, source June anchor y, July, August, RGBA
    ('New Holland', 144.0, 28040, 28967, (150, 101, 190, 255)),
    ('Vermeer', 561.0, 13611, 13507, (132, 223, 128, 255)),
    ('Virnig', 852.5, 3765, 3642, (239, 108, 193, 255)),
    ('Diamond Mowers', 848.0, 3822, 3523, (253, 120, 4, 255)),
    ('FAE Group', 870.5, 3020, 3377, (10, 156, 8, 255)),
    ('Fecon', 879.5, 2769, 2546, (222, 6, 29, 255)),
    ('Loftness', 935.0, 880, 780, (196, 196, 196, 255)),
    ('Prinoth', 959.5, 114, 102, (18, 190, 202, 255)),
    ('Denis Cimaf', 962.4, 26, 22, (249, 181, 112, 255)),
    ('Shearex', 960.8, 85, 66, (145, 83, 72, 255)),
    ('Mastodon', 961.0, 79, 85, (252, 180, 208, 255)),
]

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

def centered(text, x, visible_top, font=font_value, fill=TEXT):
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = (x - OX) * S - tw / 2 - bbox[0]
    ty = visible_top * S - bbox[1]
    d.text((tx, ty), text, font=font, fill=fill)

# July labels.
centered('28,040', x_jul, 116)
centered('13,611', x_jul, 574)
centered('3,822', x_jul - 50, 821)
centered('3,765', x_jul + 50, 842)
centered('3,020', x_jul + 48, 878)
centered('2,769', x_jul - 48, 901)
centered('880', x_jul, 910)
centered('114', x_jul - 86, 972)
centered('85', x_jul + 4, 996)
centered('79', x_jul + 90, 972)
centered('26', x_jul + 90, 1018)

# August labels.
centered('28,967', x_aug, 88)
centered('13,507', x_aug, 576)
centered('3,642', x_aug - 50, 821)
centered('3,523', x_aug + 50, 846)
centered('3,377', x_aug - 48, 878)
centered('2,546', x_aug + 48, 907)
centered('780', x_aug, 913)
centered('102', x_aug - 86, 972)
centered('66', x_aug + 4, 996)
centered('85', x_aug + 90, 972)
centered('22', x_aug + 90, 1018)

# Month labels use the source chart's date-label row.
centered('Jul 26', x_jul, 1050, font=font_date, fill=DATE)
centered('Aug 26', x_aug, 1050, font=font_date, fill=DATE)

# Composite the antialiased continuation layer while leaving the source unscaled.
overlay = overlay_hi.resize((W - OX, H), Image.Resampling.LANCZOS)
region = base.crop((OX, 0, W, H)).convert('RGBA')
region = Image.alpha_composite(region, overlay)
base.paste(region.convert('RGB'), (OX, 0))

# Restore exact June text/date glyph pixels where continuation lines pass beneath labels.
restore_rects = [
    (1885, 130, 1980, 158),
    (1885, 548, 1980, 575),
    (1830, 815, 1965, 865),
    (1880, 887, 1965, 913),
    (1880, 923, 1945, 948),
    (1845, 968, 1930, 994),
    (1845, 1045, 1940, 1070),
]
pix_src = src.load()
pix_out = base.load()
for x1, y1, x2, y2 in restore_rects:
    for y in range(y1, y2):
        for x in range(x1, x2):
            r, g, b = pix_src[x, y]
            if max(r, g, b) < 242 and max(r, g, b) - min(r, g, b) < 24:
                pix_out[x, y] = (r, g, b)

base.save(OUT, format='PNG', optimize=True)
print(OUT)
print('size', base.size)
print('july_y', {name: round(y_for(july), 2) for name, _, july, _, _ in series})
print('august_y', {name: round(y_for(august), 2) for name, _, _, august, _ in series})
