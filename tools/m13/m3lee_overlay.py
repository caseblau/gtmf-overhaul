"""Draw the M3 Lee model's outline over the user's 4-view line drawing (side, plan, front, rear; 675 x 1055 px).

  set M13_GEAR=<folder with the extracted M4A2 meshes: m_m4a2bottom.bin, m_m4wheel.bin ... (game data, not in the repo)>
  python m3lee_overlay.py <m3lee mesh> <drawing.png> <out_prefix> [zoom]

Registration on the game's M4A2 running gear (the drawing itself is not in the repo):
  side   front left; sprocket / idler centres at u 101.6 / 613.4 -> 105 px/m along the hull, origin u 359.8;
         vertical 100 px/m (road-wheel centres v 294.9 at y -0.788), so v0 216.1
  plan   front left, vehicle's right side up; same 105 px/m along the hull and origin u; 100 px/m across, centre v 537.5
  front  track centres u 86 / 287 (the game's 2.014 m gauge -> 100 px/m), centre u 186.5, ground v 1041.5 (y -1.149)
  rear   track centres u 418.75 / 618.75, centre u 518.75, ground v 1044
The drawing's side and plan views are ~5 % longer than its front and rear views are wide (the game's M4A2 gear spacing
fits 105 px/m, the gauge 100 px/m), so the hull is registered 105 px/m along its length and 100 px/m across / up.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photo_match import Ortho, edges
from render_scene import Scene
import azg2
from PIL import Image

KL, KC = 105.0, 100.0
VIEWS = {
    'side':  (Ortho([0, 0, -1], [0, 1, 0], [1, 0, 0], 359.8, 216.1, KL, -KC), (0, 0, 675, 345)),
    'plan':  (Ortho([0, 0, -1], [1, 0, 0], [0, -1, 0], 359.8, 537.5, KL, -KC), (0, 385, 675, 690)),
    'front': (Ortho([-1, 0, 0], [0, 1, 0], [0, 0, -1], 186.5, 1041.5 - KC * 1.149, KC, -KC), (0, 715, 345, 1055)),
    'rear':  (Ortho([1, 0, 0], [0, 1, 0], [0, 0, 1], 518.75, 1044.0 - KC * 1.149, KC, -KC), (345, 715, 675, 1055)),
}
ADDINS = [('m4a2bottom', 'd_bottom'), ('m4bottom_fr', 'd_bottom_fr')]    # v3: the M4A2 wings are no longer fitted

def geometry(mesh, gear_dir=None):
    g = np.array([0.5, 0.5, 0.5]); s = Scene()
    s.add_vehicle(mesh, g, addins=[(gear_dir + '/m_%s.bin' % a, h, g) for a, h in ADDINS] if gear_dir else [])
    ids = []; Vs = []; Fs = []; off = 0
    for k, (V, N, UV, F, tex) in enumerate(s.parts):
        Vs.append(V); Fs.append(F + off); off += len(V); ids.append(np.full(len(F), k))
    if gear_dir:   # wheels and bogies, as the engine places them (right-side parts mirrored)
        n0 = len(s.parts)
        for name, Wm in s.nodes.items():
            p = Wm[3, :3]; M = np.eye(4); M[3, :3] = p
            if name.startswith('d_caret_'): nm = 'm4caret'
            elif name.startswith('d_wheel_'):
                k = int(name[-2:]); nm = 'm4star' if k in (1, 12) else 'm4lazy' if k in (8, 19) else 'm4roller' if k in (9, 10, 11, 20, 21, 22) else 'm4wheel'
            else: continue
            s._instance(gear_dir + '/m_%s.bin' % nm, g, M, mirror=p[0] > 0)
        for k, (V, N, UV, F, tex) in enumerate(s.parts[n0:]):
            Vs.append(V); Fs.append(F + off); off += len(V); ids.append(np.full(len(F), 1000 + k))
    return np.vstack(Vs), np.vstack(Fs), np.concatenate(ids)

def node_ids(mesh, F_main):
    m = azg2.read(mesh); b = m['blocks'][1]; bone = b['bone']; Fv = b['idx'][:len(b['idx']) // 3 * 3].reshape(-1, 3)
    return bone[Fv[:, 0]]

def run(mesh, drawing, prefix, zoom=3, gear_dir=None):
    V, F, part = geometry(mesh, gear_dir)
    nid = node_ids(mesh, F); obj = part.copy() * 10000 + 10000
    n = min(len(nid), int((part == 0).sum())); obj[:n] = nid[:n]       # outlines between nodes too
    im0 = Image.open(drawing).convert('RGB'); W0, H0 = im0.size
    W, H = W0 * zoom, H0 * zoom
    im = np.asarray(im0.resize((W, H), Image.LANCZOS), float) * 0.55 + 255 * 0.45
    for name, (cam, reg) in VIEWS.items():
        c = Ortho(cam.eu, cam.ev, cam.ed, cam.u0 * zoom, cam.v0 * zoom, cam.su * zoom, cam.sv * zoom)
        e, _ = edges(V, F, c, W, H, face_obj=obj)
        x0, y0, x1, y1 = (q * zoom for q in reg); mask = np.zeros_like(e); mask[y0:y1, x0:x1] = True
        im[e & mask] = (230, 0, 0)
    out = Image.fromarray(im.astype(np.uint8)); out.save(prefix + '_full.png')
    for name, (cam, reg) in VIEWS.items():
        out.crop(tuple(q * zoom for q in reg)).save('%s_%s.png' % (prefix, name))

if __name__ == '__main__':
    a = sys.argv[1:]
    run(a[0], a[1], a[2], int(a[3]) if len(a) > 3 else 3, os.environ.get('M13_GEAR'))
