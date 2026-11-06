"""crisp overlay crops for the M3 Lee drawing comparison: the drawing thresholded (dark grey), the model edges red (from
m3lee_overlay.py's zoomed full image), pixel ruler.
python crisp.py <ov_full.png (zoom z, from m3lee_overlay)> <drawing.png> <z> x0 y0 x1 y1 <out> [step]"""
import sys, numpy as np
from PIL import Image, ImageDraw
def crop(full, drawing, z, box, out, step=10):
    x0, y0, x1, y1 = box
    ov = np.asarray(Image.open(full).convert('RGB').crop((x0 * z, y0 * z, x1 * z, y1 * z)))
    red = (ov[:, :, 0] > 200) & (ov[:, :, 1] < 80)
    dr = Image.open(drawing).convert('L').crop((x0, y0, x1, y1)).resize(((x1 - x0) * z, (y1 - y0) * z), Image.NEAREST)
    dk = np.asarray(dr) < 140
    im = np.full(ov.shape, 255, np.uint8); im[dk] = (110, 110, 110); im[red] = (230, 0, 0)
    c = Image.fromarray(im); d = ImageDraw.Draw(c)
    for x in range(x0 - x0 % step, x1 + 1, step):
        X = (x - x0) * z; d.line([(X, 0), (X, c.height)], fill=(205, 235, 205) if x % 50 else (0, 170, 0))
        if x % 50 == 0: d.text((X + 2, 2), str(x), fill=(0, 120, 0))
    for y in range(y0 - y0 % step, y1 + 1, step):
        Y = (y - y0) * z; d.line([(0, Y), (c.width, Y)], fill=(205, 205, 240) if y % 50 else (0, 0, 200))
        if y % 50 == 0: d.text((2, Y + 2), str(y), fill=(0, 0, 160))
    c.save(out)
if __name__ == '__main__':
    a = sys.argv[1:]; crop(a[0], a[1], int(a[2]), tuple(map(int, a[3:7])), a[7], int(a[8]) if len(a) > 8 else 10)
