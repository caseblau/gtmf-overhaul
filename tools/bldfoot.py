"""Ground footprints of the game's building models (14 Nov 2026, user: "the vehicles drive into houses, they can be placed
on houses in deployment mode").

DIM: the d_base / d_build box of each model's intact mesh (data\\common\\shared\\packed_data\\gos_objects*.flatdata,
<mesh>_s01_c0), in the model's own frame: size along local x and local z, the box centre, and the passability kind.
The box is NOT always centred on the object origin: the stone house build_cap0 stands 9.1 m off it, the church 7.6 m.

An object record (table, node, x, y, heading r, cell metres, x east / y north) turns the model so that
    local x = (cos r, -sin r)        local z = (sin r, cos r)
- measured on the vanilla houses against their yard fences (median 2.6 - 5.1 deg with this reading, 13 - 35 deg with the
plain counter-clockwise one) and on the fence pieces (97 - 98 % of 4800 neighbour pairs). So a model's local x lies along
the standard (counter-clockwise) angle a for r = pi - a, its local z for r = pi / 2 - a (tools/vstamps.py says the same).

kind: the class of the building zone in the passability maps (tools/pen.py BLD_COST), from the cost under the centre of
328 vanilla buildings: 1 shed (tanks ~305, half-tracks ~680), 2 wooden house (~600 / ~880), 3 heavy (closed: 1001);
wheeled vehicles are closed out of every zone.
"""
import math

#       node           x size  z size  centre x  z   kind
DIM = {'build0':      (12.7,   9.8,  -1.45,  0.0,  3),
       'build1':      (9.8,   10.0,   0.0,  -1.6,  2),
       'build2':      (6.8,    9.7,   0.0,   0.1,  2),
       'build3':      (6.8,    9.7,   0.0,   0.1,  2),
       'saray0':      (9.9,    5.6,   0.0,   0.0,  2),
       'saray1':      (12.6,   3.8,   0.0,  -0.2,  1),
       'saray2':      (9.9,    5.6,   0.0,   0.0,  1),
       'saray3':      (9.9,    5.6,   0.0,   0.0,  1),
       'izba1':       (11.4,  11.7,   0.0,   1.2,  2),
       'barn1':       (6.3,    7.3,   0.0,   0.0,  2),
       'build_cap0':  (7.9,   13.2,  -9.1,   0.0,  3),
       'build_cap1':  (13.0,  15.4,   0.0,   0.0,  3),
       'church_cap0': (15.2,  13.2,  -7.6,   0.0,  3),
       'church_cap1': (14.1,  13.2,   5.55,  0.0,  3),     # the other half of the brick hall (x -1.5 .. 12.6)
       'church_cap2': (10.2,  12.8,  16.3,   1.3,  3),     # the bell tower at the hall's end (x 11.2 .. 21.4)
       'farm0':       (3.3,   10.4,  -0.15,  0.0,  3),
       'farm1':       (9.0,   10.4,   0.0,   0.0,  3),
       'windmill1':   (5.9,    6.0,  -0.5,  -0.5,  3),
       # 14 Nov: whole buildings the game puts together from several models at one record (see tools/settle.py
       # expand_assemblies): a stand-in with the box of the whole set, its record in the middle, which the village code and
       # the cleanup move about as one house; the set is written out when nothing moves any more
       'build_asm_hall':   (27.8, 13.2, 0.0, 0.0, 3),   # church_cap0 + church_cap1: the brick hall (a station, a school, an office)
       'build_asm_church': (36.6, 14.3, 0.0, 0.0, 3),   # ... + church_cap2: the church with its tower
       'build_asm_brick2': (26.2, 15.4, 0.0, 0.0, 3),   # build_cap1 + build_cap0 twice: the two-storey brick house
       'farm_asm1': (15.8, 10.9, 0.0, 0.0, 3), 'farm_asm2': (24.7, 10.9, 0.0, 0.0, 3),   # farm0 + n farm1 + farm0: the long barn
       'farm_asm3': (33.7, 10.9, 0.0, 0.0, 3), 'farm_asm4': (42.7, 10.9, 0.0, 0.0, 3),
       # 17 Nov (M19): the Mazovian buildings (tabs\builds_wood mz_*, tools/m19/houses.py) - walls plus the corner log ends /
       # porch; local x along the ridge, the door side at local +z
       'mz_chata1':  (13.5,  7.5,  0.0,  0.0,  2), 'mz_chata2': (10.0,  6.0,  0.0,  0.0,  2),
       'mz_dom1':    (14.0,  8.0, -1.0,  0.0,  2), 'mz_dom2':   (12.5,  8.0,  0.0,  0.0,  2),
       'mz_stodola1': (16.0, 7.5, 0.0,  0.0,  2), 'mz_stodola2': (14.0, 7.0, 0.0, 0.0,  2),
       'mz_obora1':  (10.5,  6.0,  0.0,  0.0,  2), 'mz_miasto1': (13.5,  9.5,  0.0,  0.0,  2),
       'mz_kosciol1': (22.2, 9.0,  3.1,  0.0,  3), 'mz_dzwonnica1': (4.6, 4.6, 0.0,  0.0,  3),
       'mz_spichlerz1': (5.5, 4.5, 0.0,  0.0,  2), 'mz_chlew1': (7.5, 4.7,  0.0,  0.0,  1),
       'mz_kuznia1': (6.5,  5.5,  0.0,  0.0,  3), 'mz_remiza1': (12.6, 6.5, -1.3,  0.0,  2),
       'mz_szkola1': (18.0, 9.0,  0.0,  0.0,  3), 'mz_podcien1': (14.0, 11.4, 0.0,  1.2,  2),
       'mz_dwor1':   (24.0, 14.9, 0.0,  1.45, 3), 'mz_brog1':  (5.6,  5.6,  0.0,  0.0,  1),
       'mz_piwnica1': (5.2, 6.0,  0.0,  0.0,  3), 'mz_zuraw1': (6.6,  1.3, -1.9,  0.0,  1),
       'mz_kapliczka1': (1.2, 1.2, 0.0,  0.0,  3),
       # 19 Nov 2026: the town houses (tools/m19/houses.py kamienica1 / kamienica2 / miasto2)
       'mz_kamienica1': (15.0, 10.0, 0.0, 0.0, 3), 'mz_kamienica2': (13.0, 9.0, 0.0, 0.0, 3), 'mz_miasto2': (12.0, 8.0, 0.0, 0.0, 2)}
DEFAULT = (10.0, 8.0, 0.0, 0.0, 2)   # a building node not listed above
OFFSET = ('build_cap0', 'church_cap0', 'church_cap1', 'church_cap2')   # models whose box stands more than 3 m off the record's position

def pos(o):
    """where an object record stands for a point test: the middle of the box for the off-centre models, else its position"""
    return centre(o[2], o[3], o[4], o[1]) if o[1] in OFFSET else (o[2], o[3])

def spec(node):
    return DIM.get(node, DEFAULT)

def is_building(tab):
    """the object tables of the buildings: tabs\\builds.cfgpack, builds_wood.cfgpack, builds_cap.cfgpack"""
    return 'build' in tab

def axes(r):
    c, s = math.cos(r), math.sin(r)
    return (c, -s), (s, c)

def centre(x, y, r, node):
    """cell position of the middle of the model's box for an object record at (x, y) with heading r"""
    ax, az = axes(r); _, _, cx, cz, _ = spec(node)
    return x + ax[0] * cx + az[0] * cz, y + ax[1] * cx + az[1] * cz

def origin_for(x, y, r, node):
    """the record position that puts the middle of the model's box on (x, y)"""
    ax, az = axes(r); _, _, cx, cz, _ = spec(node)
    return x - ax[0] * cx - az[0] * cz, y - ax[1] * cx - az[1] * cz

def rect(x, y, r, node, grow=0.0):
    """the four corners of the model's box, grown by `grow` metres on every side"""
    ax, az = axes(r); sx, sz, _, _, _ = spec(node); mx, my = centre(x, y, r, node)
    hx, hz = sx / 2 + grow, sz / 2 + grow
    return [(mx + ax[0] * a * hx + az[0] * b * hz, my + ax[1] * a * hx + az[1] * b * hz) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

def samples(x, y, r, node, grow=0.0, step=2.0):
    """points over the model's box (edges and inside, about every `step` metres), for clearance tests"""
    ax, az = axes(r); sx, sz, _, _, _ = spec(node); mx, my = centre(x, y, r, node)
    hx, hz = sx / 2 + grow, sz / 2 + grow
    nx, nz = max(1, int(math.ceil(2 * hx / step))), max(1, int(math.ceil(2 * hz / step)))
    return [(mx + ax[0] * (-hx + 2 * hx * i / nx) + az[0] * (-hz + 2 * hz * j / nz), my + ax[1] * (-hx + 2 * hx * i / nx) + az[1] * (-hz + 2 * hz * j / nz))
            for i in range(nx + 1) for j in range(nz + 1)]

def long_x(node):
    """True when the model's long side runs along its local x (the barn sections farm0 / farm1 are chained along x)"""
    sx, sz = spec(node)[:2]
    return sx >= sz or node.startswith('farm')

def heading(node, ang):
    """the record heading that lays the model's long side along the standard (counter-clockwise) angle `ang`"""
    return (math.pi - ang) if long_x(node) else (math.pi / 2 - ang)

def half(node, along_long):
    """half the model's size along the side heading() lays along the angle (True) or across it (False)"""
    sx, sz = spec(node)[:2]
    return ((sx if long_x(node) else sz) if along_long else (sz if long_x(node) else sx)) / 2

def local(x, y, r, node, px, py):
    """the point (px, py) in the model's box frame: (along local x, along local z) from the middle of the box"""
    ax, az = axes(r); mx, my = centre(x, y, r, node)
    return (px - mx) * ax[0] + (py - my) * ax[1], (px - mx) * az[0] + (py - my) * az[1]

def inside(x, y, r, node, px, py, grow=0.0):
    """True when the point lies in the model's box grown by `grow` metres"""
    u, v = local(x, y, r, node, px, py); sx, sz = spec(node)[:2]
    return abs(u) <= sx / 2 + grow and abs(v) <= sz / 2 + grow

def overlap(a, b, grow=0.0):
    """True when the boxes of two object records (tab, node, x, y, r) intersect (each grown by `grow`; separating axes)"""
    ra, rb = rect(a[2], a[3], a[4], a[1], grow), rect(b[2], b[3], b[4], b[1], grow)
    for r_ in (a[4], b[4]):
        for ux, uy in axes(r_):
            pa = [p[0] * ux + p[1] * uy for p in ra]; pb = [p[0] * ux + p[1] * uy for p in rb]
            if max(pa) < min(pb) or max(pb) < min(pa): return False
    return True
