"""Match the vehicle model to a photograph.

1. calibrate(): solve a pinhole camera (position, heading, pitch, roll, focal length) from 2D-3D landmark pairs
   (road-wheel centres, casemate corners ...) by least squares.
2. edges(): render the model's outline and creases with that camera at the photo's resolution.
3. overlay(): draw them over the photo, so every difference between model and photo is visible in place.

  from photo_match import Camera, calibrate, scene_geometry, edges, overlay
"""
import os, sys, numpy as np
from PIL import Image
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geom

class Camera:
    def __init__(self, C, yaw, pitch, roll, f, cx, cy):
        self.C = np.asarray(C, float); self.yaw, self.pitch, self.roll, self.f, self.cx, self.cy = yaw, pitch, roll, f, cx, cy
    @property
    def R(self):
        cp, sp = np.cos(self.pitch), np.sin(self.pitch); cyw, syw = np.cos(self.yaw), np.sin(self.yaw)
        fw = np.array([cp * syw, sp, cp * cyw])                                   # forward; yaw 0 = looking along +z
        r = np.cross([0, 1.0, 0], fw); r /= np.linalg.norm(r); u = np.cross(fw, r)
        cr, sr = np.cos(self.roll), np.sin(self.roll)
        return np.array([cr * r + sr * u, -sr * r + cr * u, fw])
    def project(self, P):
        Pc = (np.asarray(P, float) - self.C) @ self.R.T
        z = np.maximum(Pc[:, 2], 1e-6)
        return np.c_[self.cx + self.f * Pc[:, 0] / z, self.cy - self.f * Pc[:, 1] / z], Pc[:, 2]
    def params(self): return np.r_[self.C, self.yaw, self.pitch, self.roll, self.f]
    def __repr__(self):
        return 'Camera(C=%s, yaw=%.1f, pitch=%.1f, roll=%.2f, f=%.0f)' % (np.round(self.C, 2), np.degrees(self.yaw), np.degrees(self.pitch), np.degrees(self.roll), self.f)

def calibrate(P3, p2, size, init_C, init_target, f0=1500.0, weights=None, fix_f=False, free_pp=False):
    W, H = size; P3 = np.asarray(P3, float); p2 = np.asarray(p2, float)
    w = np.ones(len(P3)) if weights is None else np.asarray(weights, float)
    d = np.asarray(init_target, float) - np.asarray(init_C, float); d /= np.linalg.norm(d)
    x0 = np.r_[init_C, np.arctan2(d[0], d[2]), np.arcsin(d[1]), 0.0, f0, W / 2, H / 2]
    def cam(x): return Camera(x[:3], x[3], x[4], x[5], f0 if fix_f else x[6], x[7] if free_pp else W / 2, x[8] if free_pp else H / 2)
    def res(x):
        q, z = cam(x).project(P3); r = ((q - p2) * w[:, None]).ravel()
        prior = [0.2 * (x[7] - W / 2), 0.2 * (x[8] - H / 2)] if free_pp else []   # weak pull to the image centre
        return np.r_[r, 50 * np.minimum(z - 0.5, 0), prior]
    sol = least_squares(res, x0, x_scale=np.r_[1, 1, 1, 0.1, 0.1, 0.05, 300, 50, 50], loss='soft_l1', f_scale=3.0)
    c = cam(sol.x); q, _ = c.project(P3); err = np.linalg.norm(q - p2, axis=1)
    return c, err

def scene_geometry(mesh, elevation=0.0, traverse=0.0, gear=True, extra=()):
    """triangles of the model (+ running gear) in world space"""
    from render_scene import Scene
    sc = Scene().add_vehicle(mesh, np.array([0.5, 0.5, 0.5]), elevation=elevation, traverse=traverse)
    if gear:   # set M13_GEAR to a folder with the extracted wheel / sprocket / idler meshes (game data, not in the repo)
        G = os.environ['M13_GEAR']
        sc.add_running_gear(G + '/m_t34_183_wheel.bin', np.array([0.5, 0.5, 0.5]), G + '/m_t34_183_wh_star.bin',
                            G + '/m_t34_183_wh_lazy.bin', np.array([0.5, 0.5, 0.5]))
    Vs, Fs, off = [], [], 0
    for V, N, UV, F, tex in sc.parts:
        Vs.append(V); Fs.append(F + off); off += len(V)
    for V, F in extra: Vs.append(V); Fs.append(F + off); off += len(V)
    return np.vstack(Vs), np.vstack(Fs)

def edges(V, F, cam, W, H, crease_deg=35.0, face_obj=None):
    """outline + creases + depth jumps (3 % of the depth); face_obj (one id per face, e.g. the mesh node) adds the
    outlines where one part covers another, for orthographic drawing views where depth jumps do not show"""
    q, z = cam.project(V); X, Y = q[:, 0], q[:, 1]
    zb = np.full((H, W), np.inf); fid = np.full((H, W), -1, np.int64)
    for k, (a, b, c) in enumerate(F):
        zs = z[[a, b, c]]
        if zs.min() < 0.3: continue
        xs = X[[a, b, c]]; ys = Y[[a, b, c]]
        x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max()))); y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
        if x1 < x0 or y1 < y0: continue
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d; w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d; w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any(): continue
        zz = 1 / (w0 / zs[0] + w1 / zs[1] + w2 / zs[2])
        sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = m & (zz < sub)
        sub[upd] = zz[upd]; fid[y0:y1 + 1, x0:x1 + 1][upd] = k
    n = geom.normals(V, F); nb = np.where(fid[..., None] >= 0, n[np.maximum(fid, 0)], 0)
    c = np.cos(np.radians(crease_deg)); e = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a, b = nb[:H - dy, :W - dx], nb[dy:, dx:]; fa, fb = fid[:H - dy, :W - dx] >= 0, fid[dy:, dx:] >= 0
        za, zbb = zb[:H - dy, :W - dx], zb[dy:, dx:]
        jump = np.abs(np.where(fa, za, 0) - np.where(fb, zbb, 0)) > 0.03 * np.minimum(np.where(fa, za, 99), np.where(fb, zbb, 99))
        if face_obj is not None:
            oa = np.asarray(face_obj)[np.maximum(fid[:H - dy, :W - dx], 0)]; ob = np.asarray(face_obj)[np.maximum(fid[dy:, dx:], 0)]
            jump |= oa != ob
        e[:H - dy, :W - dx] |= (fa != fb) | (fa & fb & ((np.sum(a * b, -1) < c) | jump))
    return e, fid

def overlay(photo, e, out, color=(255, 30, 0), dim=0.75):
    im = np.asarray(Image.open(photo).convert('RGB'), float) * dim + 255 * (1 - dim) * 0.15
    im[e] = color
    Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)).save(out)

def backproject(cam, uv, axis, value):
    """3D points where the pixel rays meet the plane {axis} = value (axis 0/1/2 = x/y/z)"""
    uv = np.atleast_2d(np.asarray(uv, float)); R = cam.R
    d_cam = np.c_[(uv[:, 0] - cam.cx) / cam.f, -(uv[:, 1] - cam.cy) / cam.f, np.ones(len(uv))]
    d = d_cam @ R                                   # world directions
    t = (value - cam.C[axis]) / d[:, axis]
    return cam.C + d * t[:, None]

def shaded(V, F, cam, W, H, light=(-0.4, 0.8, 0.45)):
    """flat-shaded grey render with the photo's camera (same raster as edges())"""
    e, fid = edges(V, F, cam, W, H)
    n = geom.normals(V, F); L = np.asarray(light, float); L /= np.linalg.norm(L)
    s = np.clip(np.abs(n @ L) * 0.75 + 0.2, 0, 1)
    img = np.full((H, W), 0.0); m = fid >= 0; img[m] = s[fid[m]]
    return img, m, e

def side_by_side(photo, V, F, cam, out, crop=None, scale=1):
    im = Image.open(photo).convert('RGB'); W, H = im.size
    sh, m, e = shaded(V, F, cam, W, H)
    r = np.full((H, W, 3), 235.0); r[m] = (sh[m] * 255)[:, None]; r[e] = [200, 20, 0]
    R = Image.fromarray(r.astype(np.uint8))
    if crop: im = im.crop(crop); R = R.crop(crop)
    if scale != 1: im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS); R = R.resize((R.width * scale, R.height * scale), Image.LANCZOS)
    out_im = Image.new('RGB', (im.width * 2, im.height)); out_im.paste(im, (0, 0)); out_im.paste(R, (im.width, 0)); out_im.save(out)

class Ortho:
    """orthographic 'camera' for scale drawings: image u = u0 + su * (P . eu), v = v0 + sv * (P . ev); depth = P . ed + 100"""
    def __init__(self, eu, ev, ed, u0, v0, su, sv):
        self.eu, self.ev, self.ed = (np.asarray(a, float) for a in (eu, ev, ed)); self.u0, self.v0, self.su, self.sv = u0, v0, su, sv
    def project(self, P):
        P = np.asarray(P, float)
        return np.c_[self.u0 + self.su * (P @ self.eu), self.v0 + self.sv * (P @ self.ev)], P @ self.ed + 100.0

def drawing_views(scale, side=None, plan=None, front=None, rear=None):
    """Ortho cameras for a 4-view drawing. Each argument: (u_of_origin, v_of_origin) pixel position of the model origin
    in that view; side: front of the vehicle to the LEFT unless side=(u, v, 'right')"""
    out = {}
    if side:
        s = 1 if (len(side) < 3 or side[2] == 'left') else -1
        out['side'] = Ortho([0, 0, -s], [0, 1, 0], [s, 0, 0], side[0], side[1], scale, -scale)   # front left: left side seen; front right: right side
    if plan:
        s = 1 if (len(plan) < 3 or plan[2] == 'left') else -1
        out['plan'] = Ortho([0, 0, -s], [s, 0, 0], [0, -1, 0], plan[0], plan[1], scale, -scale)        # seen from above
    if front: out['front'] = Ortho([-1, 0, 0], [0, 1, 0], [0, 0, -1], front[0], front[1], scale, -scale)   # seen from the front
    if rear: out['rear'] = Ortho([1, 0, 0], [0, 1, 0], [0, 0, 1], rear[0], rear[1], scale, -scale)        # seen from behind
    return out
