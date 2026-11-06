"""Bisect the 'squads stack on one spot' bug on the Prokh map (27 Oct 2026).

Swaps chosen entries of every generated cell (build\\prokhorovka\\cellsrc\\<cell>) for the vanilla Mius MgG3 entry
(docs\\m12_terrain\\samples\\cells\\MgG3) or an empty one, keeping a backup, so a quick battle shows which entry is to
blame. Then tools\\build_prokh_cells.cmd repacks the touched cells.

  python stack_test.py A        pen_* (passability) + landchar + class_map from vanilla
  python stack_test.py B        no plants, no trenches, no ambush positions (flora_quads / trench_pos / op_pos empty)
  python stack_test.py C        vars_map + grass_map from vanilla
  python stack_test.py D        EVERY entry of the vanilla cell except cell_desc (the whole map becomes copies of
                                Mius MgG3: if squads still stack, the cause is not in the cell packs at all)
  python stack_test.py E        heights + normals from vanilla
  python stack_test.py F        ground types (mat_map) + detail / ambient colour from vanilla
  python stack_test.py G        objects (houses, fences, rails) from vanilla
  python stack_test.py H        op-map pictures, ambients, aiplaces from vanilla
  python stack_test.py restore  put every backed-up entry back
"""
import os, sys, shutil, struct, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
CELLS = os.path.join(ROOT, 'build', 'prokhorovka', 'cellsrc')
VAN = os.path.join(ROOT, 'docs', 'm12_terrain', 'samples', 'cells', 'MgG3')
SUF = '.cell.loc_def.bin'
EMPTY = struct.pack('<I', 0)

GROUPS = {
    'A': {e: 'vanilla' for e in ('pen_tanks', 'pen_hums', 'pen_cars', 'pen_apcs', 'landchar', 'class_map')},
    'B': {'flora_quads': 'empty', 'trench_pos': 'empty', 'op_pos': 'empty'},
    'C': {'vars_map': 'vanilla', 'grass_map': 'vanilla'},
    'E': {'hei_map': 'vanilla', 'nor_map': 'vanilla'},
    'F': {'mat_map': 'vanilla', 'det_map': 'vanilla', 'land_ambient_col': 'vanilla'},
    'G': {'obj_quads': 'vanilla'},
    'H': {e: 'vanilla' for e in ('back', 'opmap', 'opmap_tri', 'ambients', 'spr_map_side', 'aiplaces')},
}
if os.path.isdir(VAN):
    GROUPS['D'] = {f[:-len(SUF)]: 'vanilla' for f in os.listdir(VAN) if f.endswith(SUF) and not f.startswith('cell_desc')}

def cells():
    return sorted(d for d in glob.glob(os.path.join(CELLS, 'M*')) if os.path.isdir(d))

def touch(d):
    # build_prokh.ps1 -CellsOnly repacks a cell only when its !flatlist is newer than the installed pack
    fl = os.path.join(d, '!flatlist')
    if os.path.exists(fl): os.utime(fl, None)

def restore():
    n = 0
    for d in cells():
        bak = os.path.join(d, '_stacktest_bak')
        if not os.path.isdir(bak): continue
        for f in os.listdir(bak):
            shutil.copy(os.path.join(bak, f), os.path.join(d, f)); n += 1   # copy (new mtime) so the build repacks it
        shutil.rmtree(bak); touch(d)
    print('restored %d entries' % n)

def swap(group):
    spec = GROUPS[group]; n = 0
    for d in cells():
        bak = os.path.join(d, '_stacktest_bak'); os.makedirs(bak, exist_ok=True)
        for e, how in spec.items():
            dst = os.path.join(d, e + SUF)
            if not os.path.exists(dst): continue          # border cells carry no AI layers
            if not os.path.exists(os.path.join(bak, e + SUF)): shutil.copy(dst, os.path.join(bak, e + SUF))
            if how == 'vanilla':
                src = os.path.join(VAN, e + SUF)
                if not os.path.exists(src): print('  missing vanilla', src); continue
                shutil.copy(src, dst)
            else:
                open(dst, 'wb').write(EMPTY)
            n += 1
        touch(d)
    print('test %s: %d entries replaced in %d cells (%s)' % (group, n, len(cells()), ', '.join('%s=%s' % kv for kv in spec.items())))

if __name__ == '__main__':
    arg = (sys.argv[1] if len(sys.argv) > 1 else '').upper()
    if arg == 'RESTORE': restore()
    elif arg in GROUPS: restore(); swap(arg)
    else: print(__doc__); sys.exit(1)
