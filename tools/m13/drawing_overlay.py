"""Draw the model's outline over a 4-view scale drawing (side, plan, front, rear), each view registered on parts the
SU-122 shares with the T-34 (road wheels, idler, sprocket, engine deck, rear hull).

  set M13_GEAR=<folder with the extracted T-34 wheel / sprocket / idler meshes>
  python drawing_overlay.py <su122.mesh.loc_def.bin> <A|B> <drawing.png> <out_prefix>

Registrations (pixels of the user's two drawings, 2026-10-30; the drawings themselves are not in the repo):
  A  line drawing with a 0-3 m bar, 792 x 1034 px, 105 px/m; side view front left, plan front left
  B  shaded drawing, 774 x 1040 px, 101 px/m; side view front right, plan front right (the plan is registered on
     the engine hatch and exhausts on its own: it sits 17 px left of the side view)
Writes <prefix>_full.png and 3x crops of the views.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photo_match import drawing_views, scene_geometry, edges
import azg2
from PIL import Image

REG = {
  'A': dict(k=105.0, side=(405.5, 155.5), plan=(405.5, 480.0), front=(209.0, 945.0 - 105 * 1.14), rear=(561.5, 945.0 - 105 * 1.14),
            regions={'side': (0, 0, 792, 300), 'plan': (0, 300, 792, 660), 'front': (0, 680, 400, 1034), 'rear': (395, 680, 792, 1034)},
            crops={'sfront': (90, 20, 480, 200), 'srear': (330, 20, 730, 200), 'plan': (90, 310, 450, 650), 'front': (40, 690, 380, 960), 'rear': (390, 690, 730, 960)}),
  'B': dict(k=101.0, side=(342.3, 187.5, 'right'), plan=(360.0, 515.0, 'right'), front=(220.0, 985.0 - 101 * 1.14), rear=(566.0, 985.0 - 101 * 1.14),
            regions={'side': (0, 0, 774, 320), 'plan': (0, 340, 774, 690), 'front': (0, 700, 395, 1040), 'rear': (395, 700, 774, 1040)},
            crops={'sfront': (300, 40, 740, 220), 'srear': (30, 40, 400, 220), 'plan': (330, 350, 690, 680), 'front': (50, 700, 395, 1000), 'rear': (400, 700, 740, 1000)}),
}

def run(mesh, which, drawing, prefix, elev=0.0, color=(230, 0, 0)):
    R = REG[which]
    views = drawing_views(R['k'], side=R['side'], plan=R['plan'], front=R['front'], rear=R['rear'])
    V, F = scene_geometry(mesh, elevation=elev)
    m = azg2.read(mesh); bone = m['blocks'][1]['bone']; Fv = m['blocks'][1]['idx']; nfv = len(Fv) // 3
    obj = np.full(len(F), -1); obj[:nfv] = bone[Fv[:nfv * 3].reshape(-1, 3)[:, 0]]      # node per face: part outlines in plan views
    im = np.asarray(Image.open(drawing).convert('RGB'), float) * 0.6 + 255 * 0.4
    H, W = im.shape[:2]
    for name, cam in views.items():
        e, _ = edges(V, F, cam, W, H, face_obj=obj)
        x0, y0, x1, y1 = R['regions'][name]; mask = np.zeros_like(e); mask[y0:y1, x0:x1] = True
        im[e & mask] = color
    out = Image.fromarray(im.astype(np.uint8)); out.save(prefix + '_full.png')
    for name, box in R['crops'].items():
        c = out.crop(box); c.resize((c.width * 3, c.height * 3), Image.NEAREST).save('%s_%s.png' % (prefix, name))

if __name__ == '__main__':
    run(*sys.argv[1:5], elev=float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
