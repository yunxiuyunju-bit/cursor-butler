# -*- coding: utf-8 -*-
"""生成 app.ico（应用图标）。打包前运行一次即可：python make_icon.py"""
from PIL import Image, ImageDraw

BG      = (31, 36, 48, 255)
BORDER  = (79, 140, 255, 255)
ARROW   = (232, 234, 240, 255)
BADGE   = (57, 217, 138, 255)
ARROW_INK = (31, 36, 48, 255)

def make(size):
    S = size * 4
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(S * 0.20)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=BG)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, outline=BORDER,
                        width=max(1, int(S * 0.045)))
    k = S / 100.0
    pts = [(34, 22), (34, 74), (47, 61), (57, 82), (66, 77), (56, 57), (71, 55)]
    d.polygon([(x * k, y * k) for x, y in pts], fill=ARROW)
    cx, cy = 74 * k, 76 * k
    d.ellipse([cx - 15 * k, cy - 15 * k, cx + 15 * k, cy + 15 * k], fill=BADGE)
    d.line([(cx - 7 * k, cy + 1 * k), (cx - 2 * k, cy + 6 * k), (cx + 8 * k, cy - 6 * k)],
           fill=ARROW_INK, width=max(2, int(3.2 * k)), joint='curve')
    return img.resize((size, size), Image.LANCZOS)

if __name__ == '__main__':
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [make(s) for s in sizes]
    imgs[-1].save('app.ico', format='ICO', sizes=[(s, s) for s in sizes],
                  append_images=imgs[:-1])
    print('app.ico generated')
