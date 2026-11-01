"""compare.py CROP "codes" OUT.png - scan on top, draft drawn in Noto Sans Khojki below, with token labels."""
import sys
from PIL import Image, ImageDraw, ImageFont
import os
import ktype as k
crop, codes, out = sys.argv[1], sys.argv[2], sys.argv[3]
scan = Image.open(crop).convert("L")
F = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoSansKhojki-Regular.ttf"), 120); L = ImageFont.load_default(26)
toks = codes.split(); x = 20; W = max(scan.width, 3400)
row = Image.new("L", (W, 260), 255); d = ImageDraw.Draw(row)
for t in toks:
    g = k.encode_token(t); d.text((x, 10), g, font=F, fill=0)
    w = max(d.textlength(g, font=F), d.textlength(t, font=L)) + 18
    d.text((x, 200), t, font=L, fill=90); x += w
row = row.crop((0, 0, int(x) + 20, 260))
im = Image.new("L", (max(scan.width, row.width), scan.height + row.height + 10), 255)
im.paste(scan, (0, 0)); im.paste(row, (0, scan.height + 10)); im.save(out)
print(k.encode(codes))
