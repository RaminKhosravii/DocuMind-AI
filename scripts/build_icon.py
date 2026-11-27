"""Generate matching PNG and multi-resolution Windows ICO assets."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

SIZE = 1024
base = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
pixels = base.load()
for y in range(SIZE):
    for x in range(SIZE):
        t = (x + y) / (2 * (SIZE - 1))
        pixels[x, y] = (
            int(26 + 70 * t),
            int(5 + 5 * t),
            int(105 + 130 * t),
            255,
        )

mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle((48, 48, 976, 976), radius=210, fill=255)
base.putalpha(mask)
draw = ImageDraw.Draw(base)

# Folded document silhouette.
draw.rounded_rectangle((250, 170, 770, 850), radius=70, fill=(255, 255, 255, 245))
draw.polygon([(610, 170), (770, 330), (610, 330)], fill=(202, 166, 255, 255))

# Neural nodes and links in the upper half.
nodes = [(365, 390), (510, 300), (650, 390), (430, 535), (590, 545)]
links = [(0,1),(1,2),(0,3),(1,3),(1,4),(2,4),(3,4)]
for a, b in links:
    draw.line((nodes[a], nodes[b]), fill=(103, 39, 210, 255), width=22)
for x, y in nodes:
    draw.ellipse((x-35, y-35, x+35, y+35), fill=(129, 63, 255, 255), outline=(255,255,255,255), width=8)

# Text-like document lines.
for box, fill in [
    ((340, 665, 680, 705), (119, 61, 230, 255)),
    ((340, 740, 680, 780), (155, 103, 245, 255)),
]:
    draw.rounded_rectangle(box, radius=20, fill=fill)

png = ASSETS / "documind.png"
ico = ASSETS / "documind.ico"
base.save(png, "PNG", optimize=True)
base.save(ico, "ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(f"Created {png} and {ico}")
