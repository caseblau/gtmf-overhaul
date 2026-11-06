r"""Hand-drawn briefing sketches for the Prokhorovka operation (the F2 'View briefing' picture), written as an AZSC
script pack in the vanilla style (tools/azsc.py has the format; the Stepanovka pack was the model: blue German and red
Soviet unit symbols traced from it: circle + strokes infantry (motorised variant), two rhombs tanks, two half-rhombs mechanised,
flag HQ, triangle artillery, semicircle + dashed stem attack sector, small circle + dashed line a position with a planned move;
smooth curves for the front lines (each side its own colour) and for movements - no arrowheads; dashed = boundaries / planned).

Coordinates: op-map squares of the 7 x 5 frame (X east 0..14, Y south 0..10; the 9 x 9 block adds prokh_gen SQ_DX / SQ_DY),
scaled to the 0..1 canvas the engine maps onto the square area with line_scale / text_scale(w, h, ..., -(w/2 + 1024),
-(h/2 + 1024)) - (14336, 10240, -8192, -6144) on the Mius-sized block.
Labels are text-pack keys (the formation keys of the OOB and the op_tm_* marker keys prokh_op.py adds), so they follow
the game language.

  write_scripts(out_path, frames, template_path)   frames = the layout's frames rows (brief key per turn)
"""
import math
import azsc

RED, RED2, BLUE, BLUE2, BLACK, TEXT = 0xffff0000, 0xffff3333, 0xff3333ff, 0xff0000ff, 0xff000000, 0xff333333
W, D = 0.003774, 0.02641          # vanilla pen width and dash length of the symbol strokes / planned lines
WL, DL = 0.001321, 0.01909        # the thin black dashed leader lines of the border labels
SYM = {RED: RED, RED2: RED, BLUE: BLUE, BLUE2: BLUE}     # polygons / flags of a side
LIN = {RED: RED2, RED2: RED2, BLUE: BLUE2, BLUE2: BLUE2}  # front lines and movement curves of a side
CIRC = {RED: RED2, RED2: RED2, BLUE: BLUE, BLUE2: BLUE}   # the unit circles

# the vanilla glyphs, traced from the Stepanovka pack (draw_brief_01) in op-map squares, centred, axis = +y (south);
# ('poly' | 'line', dash, points)
FLAG = [("line", 0, [(-0.125, 0.211), (-0.125, -0.211)]), ("poly", 0, [(-0.125, 0.211), (0.125, 0.121), (-0.125, 0.0)])]
ARTY = [("poly", 0, [(0.0, 0.079), (0.106, -0.079), (-0.106, -0.079)])]
TANK = [("poly", 0, [(0.234, -0.214), (-0.003, -0.327), (-0.234, -0.204), (0.003, -0.089)]),
        ("poly", 0, [(0.234, 0.203), (-0.003, 0.09), (-0.234, 0.214), (0.003, 0.328)]), ("line", 0, [(0.003, -0.124), (0.009, 0.114)])]
MECH = [("poly", 0, [(0.189, -0.323), (0.215, -0.324), (0.215, -0.135), (-0.044, -0.135), (-0.225, -0.23), (-0.044, -0.323)]),
        ("poly", 0, [(0.189, 0.12), (0.215, 0.12), (0.215, 0.308), (-0.044, 0.308), (-0.225, 0.214), (-0.044, 0.12)]), ("line", 0, [(0.055, -0.17), (0.055, 0.155)])]
STEM = [("line", D, [(0.0, 0.0), (-0.35, 0.0)])]       # the dashed stroke the vanilla sketch adds to German tank / mech symbols
_C = [(0.211 * math.cos(t), 0.211 * math.sin(t)) for t in [i * 2 * math.pi / 84 for i in range(85)]]
INF = [("line", 0, _C), ("line", 0, [(-0.098, -0.041), (-0.008, -0.094)]), ("line", 0, [(-0.012, 0.104), (0.078, 0.051)]), ("line", 0, [(-0.145, 0.085), (0.127, -0.076)])]
MOT = [("line", 0, _C), ("line", 0, [(0.091, 0.053), (-0.006, 0.093)]), ("line", 0, [(0.027, -0.101), (-0.07, -0.06)]), ("line", 0, [(0.156, -0.064), (-0.097, 0.045)]),
       ("line", 0, [(-0.064, 0.03), (-0.101, 0.122)]), ("line", 0, [(-0.065, 0.03), (-0.156, -0.004)])]
# semicircle (r 0.536) bulging along the axis with a dashed stem from its apex: the vanilla attack-sector symbol
_A = [(0.536 * math.sin(t), -0.3 + 0.536 * math.cos(t)) for t in [math.pi / 2 - i * math.pi / 124 for i in range(125)]]
ARC = [("line", 0, _A), ("line", D, [(0.0, -0.15), (0.0, 1.15)])]
# small circle (r 0.134) with a dashed line out of it: a position with a planned move
_S = [(0.134 * math.cos(t), 0.134 * math.sin(t)) for t in [i * 2 * math.pi / 20 for i in range(21)]]
SPOT = [("line", 0, _S), ("line", D, [(0.12, 0.06), (0.9, 0.5)])]


import prokh_gen as G
W_SQ, H_SQ = G.COLS * 2, G.ROWS * 2
def N(X, Y): return ((X + G.SQ_DX) / W_SQ, (Y + G.SQ_DY) / H_SQ)   # drawings are authored in the old 7 x 5 frame's squares (x -4..14, y -4..14 on the 9 x 9 block)


def chaikin(pts, passes=3):
    """corner cutting: rounds the kinks of a hand-drawn polyline without overshooting"""
    for _ in range(passes):
        out = [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            out += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        pts = out + [pts[-1]]
    return pts


def smooth(pts, n=103):
    """Catmull-Rom through the (corner-cut) control points, resampled to n points (the vanilla curves are 103 / 206 points)"""
    if len(pts) < 3: return [pts[0]] + [pts[-1]] * (n - 1) if len(pts) == 2 else pts
    if len(pts) > 3: pts = chaikin(pts)
    P = [pts[0]] + list(pts) + [pts[-1]]; out = []
    segs = len(pts) - 1
    for k in range(n):
        u = k / (n - 1) * segs; i = min(int(u), segs - 1); t = u - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(tuple(0.5 * ((2 * p1[d]) + (-p0[d] + p2[d]) * t + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t * t + (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * t ** 3) for d in (0, 1)))
    return out


class Sketch:
    def __init__(self, lean=True): self.ins = []; self.lean = lean   # lean: no HQ flags / artillery triangles (4 Nov: the sketches were cluttered)
    def _pen(self, col, cap=0, w=W): self.ins.append((azsc.OP['pen'], [(3, cap), (4, col), (0, w)]))
    def _style(self, dash=0.0): self.ins.append((azsc.OP['line_style'], [(3, 1), (0, 0.0), (3, 1), (0, dash)]))
    # the engine's line / polygon canvas has y = 0 at the SOUTH edge (text y = 0 at the north edge): seen in game on
    # 25 Oct - the labels sat right, every drawing was mirrored top to bottom - so drawings are flipped here
    def _line(self, pts): self.ins.append((azsc.OP['line'], [(0, v) for (x, y) in pts for v in (x, 1.0 - y)]))
    def _poly(self, col, pts):
        self.ins.append((azsc.OP['brush'], [(4, col)])); self.ins.append((azsc.OP['polygon'], [(0, v) for (x, y) in pts for v in (x, 1.0 - y)]))
    def _glyph(self, tpl, c, col, ang=0.0, line_col=None, scale=1.0):
        """draw a traced template at c (squares), rotated by ang; polygons in the side's symbol colour, strokes in line_col"""
        ca, sa = math.cos(ang), math.sin(ang)
        def R(x, y): return N(c[0] + (x * ca - y * sa) * scale, c[1] + (x * sa + y * ca) * scale)
        for kind, dash, pts in tpl:
            if kind == 'poly': self._poly(SYM[col], [R(*p) for p in pts])
            else: self._pen(line_col or SYM[col]); self._style(dash); self._line([R(*p) for p in pts])
    # --- symbols (positions in squares; ang = direction the unit faces / moves, radians, 0 = east, pi/2 = south)
    def line(self, pts, col, dash=0.0, w=W, cap=0, n=0):
        self._pen(col, cap, w); self._style(dash); self._line([N(*p) for p in (smooth(pts, n) if n else pts)])
    def curve(self, pts, col, dash=0.0): self.line(pts, LIN[col], dash, n=103 if len(pts) < 9 else 206)
    def front(self, pts, col): self.curve(pts, col)
    def boundary(self, pts, col): self.curve(pts, col, dash=D)
    def leader(self, a, b): self.line([a, b], BLACK, dash=DL, w=WL, n=22)
    def inf(self, c, col, motor=False, scale=1.0): self._glyph(MOT if motor else INF, c, col, 0.0, CIRC[col], scale)
    def tank(self, c, col, ang=0.0, scale=1.0): self._glyph(TANK + (STEM if SYM[col] == BLUE else []), c, col, ang, None, scale)   # rhombs abreast, long axis along ang
    def mech(self, c, col, ang=0.0, scale=1.0): self._glyph(MECH + (STEM if SYM[col] == BLUE else []), c, col, ang, None, scale)
    def flag(self, c, col):
        if not self.lean: self._glyph(FLAG, c, col)
    def arty(self, c, col, scale=1.0):
        if not self.lean: self._glyph(ARTY, c, col, 0.0, None, scale)
    def arc(self, c, col, ang=0.0): self._glyph(ARC, c, col, ang - math.pi / 2, LIN[col])   # semicircle bulging towards ang, stem onward
    def spot(self, c, col, ang=0.0): self._glyph(SPOT, c, col, ang - 0.5, LIN[col])
    def thrust(self, tail, head, col, bow=0.25):
        """a movement / attack: a bowed curve without a head, as the vanilla sketch draws them"""
        (x0, y0), (x1, y1) = tail, head; dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy) or 1e-6
        mid = ((x0 + x1) / 2 - dy / L * bow, (y0 + y1) / 2 + dx / L * bow)
        self.curve([tail, mid, head], col)
    def ellipse(self, c, col, a=0.95, b=0.37, ang=0.0):
        pts = [(a * math.cos(t), b * math.sin(t)) for t in [i * 2 * math.pi / 51 for i in range(52)]]
        self._glyph([("line", 0, pts)], c, col, ang, LIN[col])
    def height(self, c, col=RED): pass   # the vanilla sketch marks heights with a label only
    def label(self, key, c, scale=0.7143, w=0.09, h=0.036):
        cx, cy = N(*c)
        self.ins.append((azsc.OP['text_color'], [(4, TEXT)]))
        self.ins.append((azsc.OP['text'], [(2, key), (0, cx - w / 2), (0, cy - h / 2), (0, cx + w / 2), (0, cy + h / 2), (0, scale), (4, 0), (3, 3)]))
    def end(self):
        self.ins.append((azsc.OP['commit_lines'], [])); self.ins.append((azsc.OP['commit_text'], [])); self.ins.append((azsc.OP['ret'], []))
        return self.ins


# ------------------------------------------------------------------ the situations (Zamulin ch. 5-9, Lawrence ch. 7-9)
HEIGHTS = [('op_tm_h252_2', (8.81, 3.53)), ('op_tm_h241_6', (5.38, 5.95)), ('op_tm_h226_6', (2.56, 1.22)), ('op_tm_h258_2', (2.48, 8.95)),
           ('op_tm_h230_5', (13.19, 3.31)), ('op_tm_h245_8', (8.97, 5.0)), ('op_tm_h252_4', (12.41, 0.3))]
# fronts in the old 7 x 5 frame's squares (N() shifts them into the 9 x 9 block: x + 4, y + 4; the block's west edge is
# x = -4, its north edge y = -4, south edge y = 14).  WEST_RIVER: the Psel from the west edge round the Psel bend to the
# Krasny Oktyabr crossing - the line of all four days west of the bridgehead (Totenkopf's west bank).  South of
# Ivanovsky Vyselok the line runs down the railway: Yasnaya Polyana German, Belenikhino Soviet until 14 July.
WEST_RIVER = [(-4.0, -1.58), (-2.54, -1.24), (-1.74, -1.73), (-1.65, -1.16), (-1.8, 0.01), (-1.75, 0.66)]
SOUTH_RAIL = [(4.5, 11.1), (4.7, 12.5), (5.2, 13.2), (6.0, 14.0)]
FRONT_10 = WEST_RIVER + [(-1.05, 1.46), (-0.75, 1.76), (-0.14, 2.18), (0.3, 2.38), (0.55, 2.7), (1.0, 2.9), (1.1, 3.5), (2.0, 3.95), (2.55, 3.97), (2.62, 4.5), (3.0, 4.55), (3.0, 8.0), (3.5, 8.02), (3.5, 8.48), (4.0, 8.5), (4.0, 10.0)] + SOUTH_RAIL
FRONT_10e = WEST_RIVER + [(-1.05, 1.46), (-0.75, 1.76), (-0.14, 2.18), (0.3, 2.38), (0.55, 2.7), (1.0, 2.9), (1.1, 3.5), (2.3, 3.9), (3.0, 4.3), (4.2, 5.2), (5.2, 6.0), (5.4, 7.0), (5.0, 8.1), (4.6, 8.9), (4.4, 10.0)] + SOUTH_RAIL
FRONT_11 = WEST_RIVER + [(-0.8, 0.7), (0.6, 0.9), (2.0, 1.1), (3.2, 1.9), (2.4, 2.9), (3.6, 3.6), (5.2, 4.2), (6.6, 4.6), (7.1, 5.6), (7.0, 7.0), (6.5, 8.0), (5.6, 9.0), (5.3, 10.0), (4.8, 10.8), (4.6, 11.5), (4.7, 12.5), (5.2, 13.2), (6.0, 14.0)]
FRONT_11e = WEST_RIVER + [(-0.8, 0.7), (0.6, 0.9), (2.0, 1.1), (3.2, 1.9), (2.4, 2.9), (3.6, 3.6), (5.5, 3.0), (7.2, 3.3), (8.2, 3.2), (8.9, 3.9), (8.3, 4.9), (7.6, 5.6), (7.9, 7.0), (7.4, 8.4), (6.5, 9.2), (6.0, 10.0), (5.0, 10.8), (4.6, 11.5), (4.7, 12.5), (5.2, 13.2), (6.0, 14.0)]
# 06:00 13 July: Totenkopf's bridgehead Veselyi - 226.6 - Polezhayev (12 July), Das Reich at Storozhevoye and Vinogradovka, Belenikhino still Soviet
FRONT_13 = [(-4.0, -1.58), (-2.54, -1.24), (-1.74, -1.73), (0.0, -1.9), (1.5, -1.6), (3.2, -1.2), (4.2, -0.6), (4.6, 0.3), (4.0, 1.1), (3.6, 1.7), (2.6, 2.9), (3.8, 3.6), (5.6, 3.1), (7.3, 3.3), (8.4, 3.3), (9.0, 4.0), (8.3, 4.9), (7.8, 5.7), (8.0, 7.0), (7.5, 8.4), (6.6, 9.2), (6.2, 10.0), (7.0, 10.0), (7.6, 10.5), (7.2, 11.5), (5.6, 12.3), (5.2, 13.2), (6.0, 14.0)]


def offset(pts, d):
    out = []
    for i, (x, y) in enumerate(pts):
        (x0, y0), (x1, y1) = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy) or 1e-6
        out.append((x - dy / L * d, y + dx / L * d))
    return out


def common(s, front, heights=True):
    if heights:
        for key, c in HEIGHTS:
            s.height(c); s.label(key, (c[0] + 0.45, c[1] - 0.25), 0.5714, 0.07, 0.03)
    # each side draws its own line: the German one 0.22 squares on its side of the front (the normal of a north-to-south
    # front points west), the Soviet one on the other
    s.line(offset(smooth(front, 206), -0.22), RED2); s.line(offset(smooth(front, 206), 0.22), BLUE2)


def brief_01(s):
    """06:00 10 July: LSSAH about to attack from Teterevino, Totenkopf at Kozlovka, Das Reich SE of Teterevino"""
    common(s, FRONT_10)
    # Germans
    s.label('op_we_2tc_ss', (1.2, 9.3), 1.0, 0.12)
    s.inf((2.6, 8.7), BLUE, True); s.label('op_we_lah_2mir', (1.7, 8.3), 0.5714, 0.12); s.flag((1.3, 8.9), BLUE); s.arty((1.7, 7.9), BLUE)
    s.arc((3.5, 7.4), BLUE, -0.6); s.arc((3.6, 8.6), BLUE, -0.2)
    s.tank((2.0, 7.4), BLUE, 0.3); s.label('op_we_lah_tr', (1.3, 7.1), 0.5714, 0.08)
    s.inf((3.3, 9.6), BLUE, True); s.label('op_we_dr', (2.2, 9.9), 0.7143, 0.14); s.arc((4.4, 9.3), BLUE, -0.3); s.flag((2.6, 9.9), BLUE)
    s.inf((1.6, 4.5), BLUE, True); s.label('op_we_tk', (1.0, 5.0), 0.7143, 0.14); s.flag((0.7, 5.3), BLUE); s.arty((0.9, 6.1), BLUE)
    s.tank((2.0, 5.5), BLUE, 0.0); s.label('op_we_tk_tr', (1.3, 5.9), 0.5714, 0.08)
    s.arc((1.0, 3.2), BLUE, -1.8); s.arc((2.3, 3.4), BLUE, -1.0)
    # Soviets
    s.label('op_ra_183rd', (4.2, 6.6), 0.7143, 0.1); s.inf((3.6, 5.9), RED); s.inf((4.4, 7.7), RED); s.inf((7.5, 7.2), RED); s.flag((7.7, 9.5), RED); s.arty((7.2, 9.2), RED)
    s.tank((2.6, 3.2), RED, 0.2); s.label('op_ra_99tbr', (3.3, 2.7), 0.5714, 0.08)
    s.tank((6.0, 4.6), RED, 0.3); s.label('op_ra_26tbr', (6.7, 4.2), 0.5714, 0.08)
    s.tank((7.6, 6.2), RED, 0.3); s.label('op_ra_169tbr', (8.4, 6.0), 0.5714, 0.09)
    s.label('op_ra_2tc', (6.3, 7.5), 1.0, 0.1); s.flag((6.9, 8.1), RED); s.ellipse((6.5, 5.4), RED, 1.1, 0.5, 0.9)
    s.inf((1.0, 1.4), RED); s.arty((1.6, 0.7), RED); s.label('op_ra_52grd', (1.9, 0.6), 0.7143, 0.1)
    s.mech((3.9, 1.0), RED, 0.3); s.label('op_ra_11mrbr', (4.6, 0.6), 0.5714, 0.09)
    s.label('op_ra_9gabd', (11.5, 2.4), 0.7143, 0.12); s.inf((9.5, 3.0), RED); s.inf((12.3, 3.3), RED)
    s.label('op_ra_2gtc', (6.8, 13.4), 1.0, 0.1); s.tank((5.9, 12.2), RED, 0.5); s.tank((6.8, 12.8), RED, 0.5); s.flag((7.6, 13.5), RED); s.inf((7.0, 10.6), RED)
    s.label('op_ra_5gta', (12.5, 6.5), 1.429, 0.14, 0.05); s.spot((13.3, 5.2), RED, math.pi); s.spot((13.3, 7.7), RED, math.pi)
    s.flag((13.6, 2.1), RED); s.label('op_ra_48rc', (13.0, 1.6), 0.5714, 0.08)
    s.inf((-0.6, 11.7), BLUE, True); s.label('op_we_dr', (-1.6, 12.2), 0.5714, 0.1)
    s.inf((-2.6, 1.2), BLUE, True); s.flag((-3.2, 0.4), BLUE); s.inf((-0.5, -0.4), RED)


def brief_02(s):
    """10:00 10 July: the attack on svkh. Komsomolets starts (10:45), Totenkopf's assault group at Kozlovka driven off by 99 TBde"""
    brief_01(s)
    s.thrust((3.0, 6.3), (4.2, 6.3), BLUE); s.thrust((2.9, 7.3), (4.3, 7.9), BLUE)
    s.thrust((3.0, 3.3), (1.8, 3.9), RED)


def brief_03(s):
    """14:00 10 July: Komsomolets taken, 285 RR falls back to Ivanovsky Vyselok - Storozhevoye wood; 169 TBde counter-attacks"""
    common(s, FRONT_10e)
    s.label('op_we_2tc_ss', (1.2, 9.3), 1.0, 0.12)
    s.inf((4.2, 6.6), BLUE, True); s.label('op_we_lah_2mir', (3.3, 6.2), 0.5714, 0.12); s.tank((3.3, 7.6), BLUE, 0.3); s.flag((1.3, 8.9), BLUE); s.arty((2.4, 7.4), BLUE)
    s.arc((5.3, 5.9), BLUE, -0.5); s.arc((5.4, 7.3), BLUE, 0.1)
    s.inf((3.7, 9.4), BLUE, True); s.label('op_we_dr', (2.4, 9.9), 0.7143, 0.14); s.arc((4.8, 8.8), BLUE, -0.5); s.flag((2.6, 9.9), BLUE)
    s.inf((1.6, 3.5), BLUE, True); s.label('op_we_tk', (1.0, 5.0), 0.7143, 0.14); s.tank((2.0, 5.5), BLUE, 0.0); s.flag((0.7, 5.3), BLUE)
    s.arc((1.0, 2.6), BLUE, -1.7); s.arc((2.2, 2.6), BLUE, -1.1)
    s.label('op_ra_183rd', (5.6, 8.0), 0.7143, 0.1); s.inf((5.2, 7.0), RED); s.inf((7.5, 7.2), RED); s.flag((7.7, 9.5), RED); s.arty((7.2, 9.2), RED)
    s.tank((2.6, 3.2), RED, 0.2); s.label('op_ra_99tbr', (3.3, 2.7), 0.5714, 0.08)
    s.tank((6.0, 4.6), RED, 0.3); s.label('op_ra_26tbr', (6.7, 4.2), 0.5714, 0.08)
    s.tank((7.3, 6.4), RED, 0.3); s.label('op_ra_169tbr', (8.3, 6.2), 0.5714, 0.09); s.thrust((7.0, 6.4), (5.6, 6.6), RED)
    s.label('op_ra_2tc', (6.3, 7.5), 1.0, 0.1); s.flag((6.9, 8.1), RED); s.ellipse((6.5, 5.4), RED, 1.1, 0.5, 0.9)
    s.inf((1.0, 1.4), RED); s.arty((1.6, 0.7), RED); s.label('op_ra_52grd', (1.9, 0.6), 0.7143, 0.1)
    s.label('op_ra_9gabd', (11.5, 2.4), 0.7143, 0.12); s.inf((9.5, 3.0), RED); s.inf((12.3, 3.3), RED)
    s.label('op_ra_2gtc', (6.8, 13.4), 1.0, 0.1); s.tank((5.9, 12.2), RED, 0.5); s.tank((6.8, 12.8), RED, 0.5); s.inf((7.0, 10.6), RED)
    s.label('op_ra_5gta', (12.5, 6.5), 1.429, 0.14, 0.05); s.spot((13.3, 5.2), RED, math.pi); s.spot((13.3, 7.7), RED, math.pi)
    s.inf((-0.6, 11.7), BLUE, True); s.inf((-2.6, 1.2), BLUE, True); s.flag((-3.2, 0.4), BLUE); s.inf((-0.5, -0.4), RED)


def brief_04(s):
    """18:00 10 July: LSSAH at Ivanovsky Vyselok and the Komsomolets wood, Totenkopf's bridgehead at Klyuchi"""
    brief_03(s)
    s.inf((1.5, 1.7), BLUE, True); s.thrust((1.6, 1.5), (2.4, 1.0), BLUE)
    s.label('op_ra_95grd', (5.5, -2.6), 0.7143, 0.1); s.thrust((5.2, -2.2), (3.0, 0.3), RED)


def brief_07(s):
    """06:00 11 July: LSSAH attacks svkh. Oktyabrsky and 252.2 (9 gds AB Div), Das Reich towards Storozhevoye, Totenkopf in the bridgehead; 5 gds TA arriving"""
    common(s, FRONT_11)
    s.label('op_we_2tc_ss', (1.2, 9.3), 1.0, 0.12)
    s.inf((6.0, 5.2), BLUE, True); s.label('op_we_lah_2mir', (5.0, 5.9), 0.5714, 0.12); s.tank((5.2, 6.2), BLUE, 0.3); s.flag((3.6, 7.4), BLUE); s.arty((4.4, 6.6), BLUE)
    s.arc((7.3, 4.1), BLUE, -0.6); s.arc((6.6, 3.6), BLUE, -1.0)
    s.inf((5.6, 8.6), BLUE, True); s.label('op_we_dr', (4.4, 9.1), 0.7143, 0.14); s.arc((6.8, 7.8), BLUE, -0.4); s.flag((3.4, 9.6), BLUE)
    s.inf((2.0, 1.6), BLUE, True); s.label('op_we_tk', (1.0, 0.6), 0.7143, 0.14); s.tank((1.6, 3.3), BLUE, 0.0); s.flag((0.7, 4.6), BLUE)
    s.arc((3.2, 1.0), BLUE, -0.3)
    s.label('op_ra_9gabd', (10.4, 2.0), 0.7143, 0.12); s.inf((8.6, 3.4), RED); s.inf((9.7, 3.3), RED); s.flag((11.6, 3.0), RED); s.arty((10.6, 4.2), RED)
    s.tank((6.0, 3.6), RED, 0.3); s.label('op_ra_26tbr', (6.7, 3.0), 0.5714, 0.08)
    s.tank((8.0, 6.5), RED, 0.3); s.label('op_ra_169tbr', (8.9, 6.3), 0.5714, 0.09); s.label('op_ra_2tc', (7.6, 8.0), 1.0, 0.1)
    s.inf((3.8, 1.0), RED); s.label('op_ra_52grd', (4.6, 0.5), 0.7143, 0.1)
    s.label('op_ra_95grd', (6.5, 0.4), 0.7143, 0.1)
    s.label('op_ra_5gta', (12.0, 6.0), 1.429, 0.14, 0.05); s.tank((12.0, 3.0), RED, 0.5); s.label('op_ra_18tc', (12.8, 2.6), 0.5714, 0.08); s.flag((13.4, 6.4), RED); s.ellipse((12.4, 3.6), RED, 1.3, 0.6, 1.2)
    s.tank((12.5, 4.6), RED, 0.5); s.label('op_ra_29tc', (13.2, 4.3), 0.5714, 0.08)
    s.label('op_ra_2gtc', (6.8, 13.4), 1.0, 0.1); s.tank((5.9, 12.2), RED, 0.5); s.tank((6.8, 12.8), RED, 0.5); s.inf((7.0, 10.6), RED); s.inf((-0.6, 11.7), BLUE, True); s.inf((-2.6, 1.2), BLUE, True); s.flag((-3.2, 0.4), BLUE)


def brief_10(s):
    """18:00 11 July: svkh. Oktyabrsky and 252.2 taken, LSSAH 2.5 km from the station; Das Reich at Storozhevoye; the counter-attack is ordered"""
    common(s, FRONT_11e)
    s.label('op_we_2tc_ss', (1.2, 9.3), 1.0, 0.12)
    s.inf((7.4, 3.9), BLUE, True); s.label('op_we_lah_2mir', (6.3, 4.6), 0.5714, 0.12); s.tank((7.8, 4.5), BLUE, 0.3); s.label('op_we_lah_tr', (7.0, 5.1), 0.5714, 0.08); s.flag((5.0, 6.2), BLUE); s.arty((6.0, 5.6), BLUE)
    s.inf((7.0, 7.4), BLUE, True); s.label('op_we_dr', (5.8, 7.9), 0.7143, 0.14); s.flag((4.6, 9.2), BLUE)
    s.inf((2.4, 1.6), BLUE, True); s.label('op_we_tk', (1.0, 0.6), 0.7143, 0.14); s.tank((1.6, 3.3), BLUE, 0.0)
    s.label('op_ra_9gabd', (10.8, 2.2), 0.7143, 0.12); s.inf((9.6, 3.2), RED); s.inf((10.4, 3.9), RED)
    s.tank((8.6, 5.6), RED, 0.3); s.label('op_ra_169tbr', (9.4, 5.4), 0.5714, 0.09); s.label('op_ra_2tc', (9.0, 7.6), 1.0, 0.1)
    s.inf((4.2, 1.0), RED); s.label('op_ra_52grd', (5.0, 0.5), 0.7143, 0.1); s.label('op_ra_95grd', (6.6, 0.4), 0.7143, 0.1)
    s.label('op_ra_5gta', (12.0, 6.0), 1.429, 0.14, 0.05)
    s.tank((12.0, 2.6), RED, 0.5); s.label('op_ra_18tc', (12.8, 2.2), 0.5714, 0.08); s.tank((12.3, 4.4), RED, 0.5); s.label('op_ra_29tc', (13.1, 4.0), 0.5714, 0.08)
    s.tank((13.0, 8.0), RED, 0.5); s.label('op_ra_5gmc', (13.0, 8.6), 0.5714, 0.09)
    s.label('op_ra_2gtc', (6.8, 13.4), 1.0, 0.1); s.tank((5.9, 12.2), RED, 0.5); s.tank((6.8, 12.8), RED, 0.5); s.inf((7.0, 10.6), RED); s.inf((-0.6, 11.7), BLUE, True); s.inf((-2.6, 1.2), BLUE, True); s.flag((-3.2, 0.4), BLUE)
    s.boundary([(9.0, 3.0), (11.0, 3.4), (13.9, 3.2)], RED); s.flag((13.4, 6.4), RED); s.flag((11.6, 3.0), RED)


def brief_13(s):
    """06:00 12 July: the counter-attack of 5 gds TA (18 and 29 TC along the railway, 2 gds TC on Belenikhino) and Totenkopf's attack out of the bridgehead"""
    common(s, FRONT_13)
    s.label('op_we_2tc_ss', (1.2, 9.3), 1.0, 0.12)
    s.inf((7.6, 3.9), BLUE, True); s.label('op_we_lah_2mir', (6.4, 4.6), 0.5714, 0.12); s.tank((7.9, 4.7), BLUE, 0.3); s.label('op_we_lah_tr', (7.0, 5.2), 0.5714, 0.08); s.flag((5.0, 6.2), BLUE); s.arty((6.0, 5.6), BLUE)
    s.inf((7.2, 7.4), BLUE, True); s.label('op_we_dr', (6.0, 7.9), 0.7143, 0.14); s.tank((6.8, 8.4), BLUE, 0.3); s.flag((4.6, 9.2), BLUE)
    s.inf((2.6, 1.5), BLUE, True); s.inf((0.4, -0.8), BLUE, True); s.label('op_we_tk', (1.0, 0.6), 0.7143, 0.14); s.tank((3.2, -0.2), BLUE, 0.0); s.label('op_we_tk_tr', (4.0, -0.7), 0.5714, 0.08)
    s.arc((4.8, -0.5), BLUE, -0.3); s.arc((4.2, 2.1), BLUE, 0.4); s.arc((2.0, -1.8), BLUE, -1.5)
    s.label('op_ra_9gabd', (10.8, 2.2), 0.7143, 0.12); s.inf((9.6, 3.2), RED); s.inf((10.4, 3.9), RED)
    s.tank((10.4, 2.4), RED, 0.5); s.label('op_ra_18tc', (11.2, 2.0), 0.5714, 0.08); s.thrust((10.0, 2.6), (7.2, 3.3), RED, -0.3); s.thrust((10.0, 2.0), (6.5, 2.6), RED, -0.3)
    s.tank((10.8, 4.0), RED, 0.5); s.label('op_ra_29tc', (11.6, 4.4), 0.5714, 0.08); s.thrust((10.4, 4.1), (8.2, 4.1), RED); s.thrust((10.6, 4.8), (8.6, 5.6), RED)
    s.tank((7.4, 12.4), RED, 0.5); s.tank((8.2, 11.4), RED, 0.5); s.label('op_ra_2gtc', (8.6, 13.0), 1.0, 0.1); s.thrust((7.2, 12.2), (5.0, 12.6), RED); s.thrust((8.0, 11.2), (7.0, 10.0), RED); s.inf((-0.6, 11.7), BLUE, True); s.inf((-2.6, 1.2), BLUE, True); s.flag((-3.2, 0.4), BLUE); s.inf((-1.0, -2.6), RED); s.flag((13.4, 6.0), RED); s.flag((11.6, 3.0), RED)
    s.tank((13.0, 6.5), RED, 0.5); s.label('op_ra_5gmc', (13.0, 7.1), 0.5714, 0.09)
    s.inf((5.6, -1.6), RED); s.label('op_ra_52grd', (2.6, -2.6), 0.7143, 0.1); s.label('op_ra_95grd', (6.4, -2.2), 0.7143, 0.1); s.inf((3.0, -2.4), RED)
    s.label('op_ra_5gta', (12.0, 5.5), 1.429, 0.14, 0.05); s.label('op_ra_2tc', (9.5, 7.3), 1.0, 0.1)


def brief_14(s):
    """10:00 12 July: 29 TC into the anti-tank ditch at 252.2, 18 TC in Vasilyevka - Andreyevka, Totenkopf across the Psel"""
    brief_13(s)
    s.tank((8.6, 3.2), RED, 0.5); s.tank((8.9, 4.4), RED, 0.5); s.tank((8.3, 4.2), BLUE, 0.3); s.tank((5.6, 2.6), RED, 0.5)


def brief_15(s):
    """14:00 12 July: the field between the sovkhoz and the ditch, Storozhevoye lost, Totenkopf on the Kartashevka road"""
    brief_13(s)
    s.tank((9.0, 3.6), RED, 0.5); s.tank((8.4, 4.4), BLUE, 0.3); s.tank((6.0, 3.0), RED, 0.5); s.tank((7.0, 0.8), BLUE, 0.0)
    s.thrust((7.6, 7.0), (8.8, 7.4), BLUE)


def brief_19(s):
    """06:00 13 July: both sides on the 12 July lines, Totenkopf gives up the bridgehead on 13-14 July"""
    common(s, FRONT_13)
    s.label('op_we_2tc_ss', (1.2, 9.3), 1.0, 0.12)
    s.inf((7.6, 3.9), BLUE, True); s.label('op_we_lah_2mir', (6.4, 4.6), 0.5714, 0.12); s.tank((7.6, 4.8), BLUE, 0.3)
    s.inf((7.6, 7.4), BLUE, True); s.label('op_we_dr', (6.4, 7.9), 0.7143, 0.14)
    s.inf((2.8, 1.5), BLUE, True); s.inf((0.4, -0.8), BLUE, True); s.label('op_we_tk', (1.0, 0.6), 0.7143, 0.14); s.tank((3.4, -0.2), BLUE, 0.0); s.thrust((3.6, 0.6), (2.2, 2.6), BLUE); s.flag((5.0, 6.2), BLUE); s.flag((4.6, 9.2), BLUE)
    s.label('op_ra_9gabd', (10.8, 2.2), 0.7143, 0.12); s.inf((9.6, 3.2), RED)
    s.tank((9.8, 2.6), RED, 0.5); s.label('op_ra_18tc', (10.6, 2.2), 0.5714, 0.08); s.tank((10.4, 4.2), RED, 0.5); s.label('op_ra_29tc', (11.2, 4.6), 0.5714, 0.08)
    s.tank((7.6, 12.4), RED, 0.5); s.tank((8.4, 11.4), RED, 0.5); s.label('op_ra_2gtc', (8.8, 13.0), 1.0, 0.1); s.inf((-0.6, 11.7), BLUE, True); s.inf((-2.6, 1.2), BLUE, True); s.flag((-3.2, 0.4), BLUE); s.inf((-1.0, -2.6), RED)
    s.inf((5.6, -1.6), RED); s.label('op_ra_52grd', (2.6, -2.6), 0.7143, 0.1); s.label('op_ra_95grd', (6.4, -2.2), 0.7143, 0.1); s.inf((3.0, -2.4), RED); s.label('op_ra_42grd', (6.4, 1.6), 0.7143, 0.1)
    s.label('op_ra_5gta', (12.0, 5.5), 1.429, 0.14, 0.05); s.label('op_ra_2tc', (9.5, 7.3), 1.0, 0.1)


# ------------------------------------------------------------------ the operation starts, drawn from the layouts: the 06:00 10 July
# picture (brief_01, also under brief_02) from layout_10jul.json and the 06:00 12 July one (brief_13, under brief_14 / brief_15) from
# layout_12jul.json.  4 Nov (user: "too much stuff, it all messes up"): drawn like the vanilla Stepanovka sketches - ONE symbol per
# division / corps / independent brigade (FORMATIONS: the battle groups are aggregated, the symbol is the formation's main arm),
# at the centre of its manoeuvre battle groups (HQs, artillery, AT and support groups are left out of the centre and not drawn),
# one label per formation, army / corps names as big labels behind their troops, the army artillery group as the one triangle.
# Symbols are pushed apart along the front until they clear each other, labels take the free spot around their symbol.
import json, os
def _layout(name):
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (os.path.join(here, '..', 'docs', 'm11_prokhorovka'), os.path.join(here, 'docs', 'm11_prokhorovka')):
        p = os.path.join(d, name)
        if os.path.exists(p): return json.load(open(p, encoding='utf-8'))
    raise FileNotFoundError(name)

def _sq(x, y):
    """DEM-lattice metres -> squares of the old 7 x 5 frame (what N() expects)"""
    return (x / 1024.0 - G.SQ_DX, (20480.0 - y) / 1024.0 - G.SQ_DY)

# (text key, main arm, battle groups by the FIRST form of their layout entry) - only the manoeuvre groups set the centre
FORMATIONS = [
    ('op_we_lah', 'mech', ['we_lah_1mir', 'we_lah_2mir', 'we_lah_tr', 'we_lah_stug', 'we_lah_rb']),
    ('op_we_dr', 'mech', ['we_dr_3mir', 'we_dr_4mir', 'we_dr_tr', 'we_dr_stug', 'we_dr_rb']),
    ('op_we_tk', 'mech', ['we_tk_5mir', 'we_tk_6mir', 'we_tk_tr', 'we_tk_stug']),
    ('op_ra_183rd', 'inf', ['ra_285', 'ra_295', 'ra_227']),
    ('op_ra_52grd', 'inf', ['ra_151', 'ra_153', 'ra_155']),
    ('op_ra_95grd', 'inf', ['ra_284', 'ra_287', 'ra_290']),
    ('op_ra_42grd', 'inf', ['ra_127', 'ra_132', 'ra_136']),
    ('op_ra_9gabd', 'inf', ['ra_23gab', 'ra_26gab', 'ra_28gab']),
    ('op_ra_93grd', 'inf', ['ra_278']),
    ('op_ra_97grd', 'inf', ['ra_289']),
    ('op_ra_2tc', 'tank', ['ra_99tbr', 'ra_26tbr', 'ra_169tbr', 'ra_58mrbr', 'ra_15gtr']),
    ('op_ra_2gtc', 'tank', ['ra_4gtbr', 'ra_25gtbr', 'ra_26gtbr', 'ra_4gmrbr', 'ra_47gtr']),
    ('op_ra_18tc', 'tank', ['ra_181tbr', 'ra_170tbr', 'ra_110tbr', 'ra_32mrbr', 'ra_36gtr']),
    ('op_ra_29tc', 'tank', ['ra_32tbr', 'ra_31tbr', 'ra_25tbr', 'ra_53mrbr']),
    ('op_ra_5gmc', 'mech', ['ra_10gmbr']),
    ('op_ra_11mrbr', 'mech', ['ra_11mrbr']),
    (None, 'arty', ['ra_678har']),                       # 5 gds TA long-range artillery group (12 July): the one army-level group
]
# army / corps names: big labels at their HQ (layout entry with that first form), as the vanilla sketches name them in a corner
GROUPS = [('op_we_2tc_ss', 'we_2tc_ss'), ('op_ra_5gta', 'ra_5gta'), ('op_ra_5ga', 'ra_5ga')]
SC = 1.25                          # formation symbols a quarter larger than the traced glyphs (the 9 x 9 block is 18 squares wide, vanilla 14)
R_SYM = 0.42 * SC                  # symbol radius in squares (the traced glyphs reach about 0.33)
LBL_W, LBL_H = 0.12, 0.036         # label box (canvas units) of a formation; group labels are wider (GRP_W, GRP_H)
GRP_W, GRP_H = 0.14, 0.045

def _near(front, p):
    """nearest point of the front polyline to p, the unit tangent there and the signed distance (+ = German side)"""
    best = None
    for (x0, y0), (x1, y1) in zip(front, front[1:]):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((p[0] - x0) * dx + (p[1] - y0) * dy) / L2))
        q = (x0 + t * dx, y0 + t * dy); d = math.hypot(p[0] - q[0], p[1] - q[1])
        if best is None or d < best[0]: best = (d, q, (dx, dy))
    d, q, (dx, dy) = best; L = math.hypot(dx, dy) or 1e-9; tx, ty = dx / L, dy / L
    side = (p[0] - q[0]) * -ty + (p[1] - q[1]) * tx          # offset() puts the German line on the (-ty, tx) side
    return q, (tx, ty), side

def _declutter(syms, front, lo=-3.6, hi=13.6):
    """push symbols apart (along the front where they sit near it) and keep each on its own side, >= 0.7 squares off the line"""
    for _ in range(400):
        moved = False
        for i, a in enumerate(syms):
            fx = fy = 0.0
            for j, b in enumerate(syms):
                if i == j: continue
                dx, dy = a['c'][0] - b['c'][0], a['c'][1] - b['c'][1]; d = math.hypot(dx, dy)
                need = a['r'] + b['r'] + 0.15
                if d < need:
                    if d < 1e-6: dx, dy, d = (1.0, 0.0, 1.0) if i < j else (-1.0, 0.0, 1.0)
                    k = (need - d) / 2; fx += dx / d * k; fy += dy / d * k
            q, (tx, ty), side = _near(front, a['c'])
            if abs(side) < 2.0 and (fx or fy):                  # near the line: slide along it
                k = fx * tx + fy * ty; fx, fy = tx * k, ty * k
            x, y = a['c'][0] + fx, a['c'][1] + fy
            q, (tx, ty), side = _near(front, (x, y)); want = 1.0 if a['ger'] else -1.0
            if side * want < 0.7:                               # back onto its own side of the line
                x, y = q[0] - ty * want * 0.7, q[1] + tx * want * 0.7
            x, y = min(hi, max(lo, x)), min(hi, max(lo, y))
            if abs(x - a['c'][0]) + abs(y - a['c'][1]) > 1e-4: moved = True
            a['c'] = (x, y)
        if not moved: break
    return syms

def _box(c, w, h):   # label box in squares around centre c (w, h in canvas units)
    return (c[0] - w * W_SQ / 2, c[1] - h * H_SQ / 2, c[0] + w * W_SQ / 2, c[1] + h * H_SQ / 2)

def _ov(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))

def _place(c, w, h, taken, lines, prefer=(0.0, 0.0), dist=0.0, front=None, ger=None):
    """the free spot for a label: ring of candidates around c, scored by overlap with taken boxes / symbols and the front lines"""
    bw, bh = w * W_SQ, h * H_SQ; best = None
    for rad in (dist, dist + 0.3, dist + 0.6, dist + 1.0, dist + 1.5, dist + 2.2):
        for k in range(16):
            t = k * math.pi / 8
            ox, oy = math.cos(t) * (bw / 2 + rad), math.sin(t) * (bh / 2 + rad)
            p = (c[0] + ox, c[1] + oy); b = _box(p, w, h)
            sc = sum(_ov(b, o) for o in taken) * 40.0
            sc += sum(1 for (x, y) in lines if b[0] - 0.1 < x < b[2] + 0.1 and b[1] - 0.1 < y < b[3] + 0.1) * 0.25
            sc += 5.0 * (max(0.0, -3.9 - b[0]) + max(0.0, b[2] - 13.9) + max(0.0, -3.9 - b[1]) + max(0.0, b[3] - 13.9))
            if front is not None:   # a label never crosses to the other side of the front
                want = 1.0 if ger else -1.0
                sc += sum(5.0 for q in ((b[0], b[1]), (b[2], b[1]), (b[0], b[3]), (b[2], b[3]), p) if _near(front, q)[2] * want < 0.25)
            sc -= 0.05 * (ox * prefer[0] + oy * prefer[1])
            sc += 0.1 * (rad - dist)
            if best is None or sc < best[0] - 1e-9: best = (sc, p, b)
        if best[0] < 0.05: break
    return best[1], best[2]

def from_layout(s, name):
    L = _layout(name)
    front = [_sq(x, y) for x, y in L['front']]
    sm = smooth(front, 206)
    common(s, front, heights=False)
    lines = offset(sm, -0.22) + offset(sm, 0.22)
    pos = {}
    for u in L['units']:
        if u.get('turn', 1) != 1: continue
        pos.setdefault(u['form'][0], []).extend(_sq(x, y) for x, y in u['pos'])
    syms = []
    for key, kind, members in FORMATIONS:
        pts = [p for m in members for p in pos.get(m, [])]
        if not pts: continue
        c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        ger = members[0].startswith('we')
        syms.append(dict(key=key, kind=kind, c=c, c0=c, ger=ger, r=R_SYM * (0.6 if kind == 'arty' else 1.0)))
    _declutter(syms, sm)
    taken = [(a['c'][0] - a['r'], a['c'][1] - a['r'], a['c'][0] + a['r'], a['c'][1] + a['r']) for a in syms]
    # heights: the vanilla sketches label the key heights; they go first and the unit labels keep clear of them
    for key, c in HEIGHTS:
        p, b = _place((c[0] + 0.45, c[1] - 0.25), 0.07, 0.024, taken, lines, dist=0.0); taken.append(b)
        s.label(key, p, 0.5714, 0.07, 0.03)
    for a in syms:
        col = BLUE if a['ger'] else RED
        q, (tx, ty), side = _near(sm, a['c'])
        ang = math.atan2(q[1] - a['c'][1], q[0] - a['c'][0])        # facing the front: rhombs abreast along it
        if a['kind'] == 'tank': s.tank(a['c'], col, ang, SC)
        elif a['kind'] == 'mech': s.mech(a['c'], col, ang, SC)
        elif a['kind'] == 'arty': s._glyph(ARTY, a['c'], col, 0.0, None, SC)   # the army artillery group is drawn even on a lean sketch
        else: s.inf(a['c'], col, a['kind'] == 'mot', SC)
    for a in syms:
        if not a['key']: continue
        q, (tx, ty), side = _near(sm, a['c'])
        rear = (a['c'][0] - q[0], a['c'][1] - q[1]); rl = math.hypot(*rear) or 1.0
        p, b = _place(a['c'], LBL_W, LBL_H, taken, lines, (rear[0] / rl, rear[1] / rl), a['r'], sm, a['ger'])
        taken.append(b); s.label(a['key'], p, 0.7143, LBL_W, LBL_H)
    for key, hq in GROUPS:
        if hq not in pos: continue
        c = pos[hq][0]; c = (min(12.4, max(-2.6, c[0])), min(13.3, max(-3.3, c[1])))
        p, b = _place(c, GRP_W, GRP_H, taken, lines, (0.0, 0.0), 0.0, sm, hq.startswith('we'))
        taken.append(b); s.label(key, p, 1.0, GRP_W, GRP_H)

def brief_01(s):
    """06:00 10 July from layout_10jul.json"""
    from_layout(s, 'layout_10jul.json')

def brief_13(s):
    """06:00 12 July from layout_12jul.json"""
    from_layout(s, 'layout_12jul.json')

# turns 2-3 of each start keep the layout picture: the extra thrusts / tank symbols they used to add were authored on the
# hand-drawn fronts and landed across the layout's line (4 Nov)
brief_02 = brief_01
brief_14 = brief_15 = brief_13

SKETCHES = dict(brief_01=brief_01, brief_02=brief_02, brief_03=brief_03, brief_04=brief_04, brief_07=brief_07, brief_10=brief_10,
                brief_13=brief_13, brief_14=brief_14, brief_15=brief_15, brief_19=brief_19)


def write_scripts(out_path, brief_keys, turns=24, turn_offset=0):
    """brief_keys: the 'brief' values of the frames rows (empty ones skipped); turn_offset: campaign turn of the operation's
    turn 1 minus 1 (the 12-13 July operation starts at campaign turn 13 -> 12), so ai_orders stay indexed by campaign turn"""
    keys = [k for k in dict.fromkeys(brief_keys) if k]
    funcs = {}   # name -> instruction list
    for k in keys:
        s = Sketch(); SKETCHES.get(k, brief_01)(s); funcs['draw_' + k] = s.end()
    funcs['settings'] = [(azsc.OP['font'], [(2, 'handw')]),
                         (azsc.OP['line_scale'], [(0, W_SQ * 1024.0), (0, H_SQ * 1024.0), (0, 1.0), (0, -(W_SQ * 512.0 + 1024)), (0, -(H_SQ * 512.0 + 1024))]),
                         (azsc.OP['text_scale'], [(0, W_SQ * 1024.0), (0, H_SQ * 1024.0), (0, 0.4), (0, -(W_SQ * 512.0 + 1024)), (0, -(H_SQ * 512.0 + 1024))]),
                         (azsc.OP['ret'], [])]
    for k in keys: funcs[k] = None   # filled once the entry indices are known (call settings; call draw_k; break)
    funcs['at_start'] = [(azsc.OP['log'], [(2, 'at_start()')]), (azsc.OP['dump'], []), (azsc.OP['break'], [])]
    funcs['at_end'] = [(azsc.OP['log'], [(2, 'at_end()')]), (azsc.OP['dump'], []), (azsc.OP['break'], [])]
    funcs['turn_any'] = [(azsc.OP['log'], [(2, 'turn_any()')]), (azsc.OP['break'], [])]
    import ai_orders
    for t in range(1, turns + 1):   # the AI orders of the turn (tools/ai_orders.py): order(kind, ai_id, x, y)
        funcs['turn_%02d' % t] = [(azsc.OP['log'], [(2, 'turn_%02d()' % t)])] + \
            [(azsc.OP['order'], [(2, k), (2, i), (3, x + G.SQ_DX), (3, y + G.SQ_DY)]) for k, i, x, y in ai_orders.ORDERS.get(t + turn_offset, [])] + [(azsc.OP['break'], [])]
    names = sorted(funcs)
    # lay out: draw functions first, then settings, then the stubs (any order works; indices are resolved below)
    order = ['draw_' + k for k in keys] + ['settings'] + keys + ['at_start', 'at_end', 'turn_any'] + ['turn_%02d' % t for t in range(1, turns + 1)]
    start = {}; pos = 0
    for n in order:
        start[n] = pos
        pos += 3 if funcs[n] is None else len(funcs[n])
    for k in keys:
        funcs[k] = [(azsc.OP['call'], [(4, start['settings'])]), (azsc.OP['call'], [(4, start['draw_' + k])]), (azsc.OP['break'], [])]
    instrs = []
    for n in order: instrs += funcs[n]
    # strings: argument strings in first-use order, then the function names (sorted), then the builtins (sorted)
    args = []
    for op, a in instrs:
        for t, v in a:
            if t == 2 and v not in args: args.append(v)
    strs = args + names + sorted(azsc.BUILTINS)
    func_table = [start[n] for n in names]
    azsc.write(out_path, func_table, strs, instrs, a=len(args), b=len(args) + len(names))
    return len(instrs), len(names)
