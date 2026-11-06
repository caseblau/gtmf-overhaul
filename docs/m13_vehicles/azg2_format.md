# M13 — new vehicles for Prokhorovka (SU-122, SU-76, M3 Lee): mesh format notes

Started 2026-10-30. Goal: real models for the SU-122 (1943), SU-76 (1943, early open-top/roofed) and M3 Lee, the three
vehicles the Prokhorovka operations currently replace with stand-ins (SU-152 sections, T-34 sections).

## Source check (2026-10-30)

None of the three exists in the user's games:
- Mius-Front `techn_base` (91 vehicles) + `techn_base_oprum` (50): no SU-76, SU-122 or M3 Lee. Closest kin:
  `su152` / `su152_late` (KV chassis), `t70m` (the SU-76 runs on a lengthened T-70 chassis), `m4a2_sherman`
  (same VVSS bogies, idler and sprocket family as the M3 Lee), `t34_*` (SU-122 hull and running gear).
- Operation Star base game (75 vehicles): none either.
So every vehicle needs new geometry. Parts that can be reused from existing meshes: SU-122 running gear from the
T-34 (1942/43); SU-76 running gear from the T-70; M3 Lee bogies / tracks from the M4A2.

Openly licensed models (checked 2026-10-30): none found that may be redistributed in a public mod. The free
SU-122 / M3 Lee models on Free3D are under its royalty-free / "editorial only" licence (no redistribution of the
model itself); CGTrader, RenderHub, 3dcadbrowser and Wargaming3D listings are paid or print-only (STL, no UVs).
Decision (user, 2026-10-30): model the three vehicles ourselves in Blender.

## AZG2 mesh (`*.mesh.loc_def.bin`), decoded so far (sample: `t50` from `gos_techn_02.flatdata`)

Header (0x80 bytes): `AZG2`, u32 file size, then (offset, count) pairs:
| pair | example (t50) | content |
|---|---|---|
| 1 | 0x90 × 111 | node table, 0x140 bytes per node |
| 2 | 35680 × 2 | materials, 0x68 bytes: name[0x20] (`t50_dift`), 0x20 pad, 4 floats 1.0 (colour), 3 floats (100, 128, 100), then texture names (`t50_dift`, `t50_norsp`) |
| 3 | 35888 × 109 | `[MATRICES]`: 4×4 float matrices (row-major, translation in the last row), one per node with geometry |
| 4 | 0 | – |
| 5 | 47296 × 4 | geometry blocks, 0xC0 bytes each (see below) |
| 6 | 46992 × 3 | index lists (u32 offset, count, 0x40, 1) of node numbers, e.g. which nodes belong to each LOD |
| 7 | 0 | – |
| 8 | 42880 × 512 | (u32 node \| 0x80000000, u32 value) pairs – lookup table, meaning open |

`[CHUNKS]` tag at 0x80, `[GEOMETRY]` tag just before the geometry blocks.

### Node record (0x140)
`name[0x20]` (`s_root`, `d_hull`, `d_drv_hatch`, `s_head` …), then 8 × u32 (parent / flags with bit 31, kind,
matrix index …), then four LOD slots of 0x40 bytes, one per geometry block:
`u32 vertex_count, u32 index_count, u32 0, u32 0, u32 lod, i32 -1, u32 ×3, float bbox[8]` (min xyz, 1, max xyz, 0).
The sums of the slot counts equal the block totals (t50: slot 0 → 11 109 / 14 538, slot 1 → 33 168 / 46 074 …).

### Geometry block (0xC0)
`tag` (`PNTl` for block 0, `GXT2` for the LODs), u32 version (5 / 4), u32 lod (0 for PNTl; 1, 1, 1),
u32 index_offset, u32 vertex_offset, u32 index_count, u32 vertex_count, i32 lod index (-1 for PNTl),
float bbox[8], then a D3D9 vertex declaration (D3DVERTEXELEMENT9: stream u16, offset u16, type u8, method u8,
usage u8, usage index u8, ended by stream 0xff):
- `GXT2`, stride 32: POSITION float3 @0, TEXCOORD0 SHORT2N @0x0c, BLENDINDICES D3DCOLOR @0x10, NORMAL UBYTE4N
  @0x14, TANGENT UBYTE4N @0x18, BINORMAL UBYTE4N @0x1c. Indices u16, triangle list (checked by rendering the
  t50 hull: a clean wireframe of the hull).
- `PNTl`, stride 48: POSITION float4, NORMAL float4, TEXCOORD float4; u32 indices. A simplified copy of the model
  (hull 3 102 vertices against 23 943 in LOD 0) – most likely the shadow / hit-test mesh.
Axes: x right, y up, z forward, metres.

### Still open
- How node geometry maps onto the buffers (per-node index ranges are absolute and not strictly contiguous in vertex
  space – probably a per-node base vertex taken from another field).
- BLENDINDICES (node index per vertex for rigid skinning?) and the TEXCOORD scale.
- Pair 8 table, the 8 × u32 node header fields, material floats.
- Then: a writer, verified by round-tripping an existing mesh byte-for-byte, before any new model goes in.

## Plan
1. Finish the reader (export to OBJ/glTF with nodes, UVs, normals) – check on t50, t34_42_utz, su152, m4a2_sherman.
2. Writer + round-trip test; install a re-written vanilla mesh in game to prove it loads.
3. Source models: user-made or openly licensed (licence must allow modification and redistribution in a free mod;
   credit the author). Build to the node naming the configs need (`d_hull`, `d_head`, `d_gun`, `d_hatch_*`,
   `s_camera_*`, `p_*` damage points, wheel / track nodes).
4. Textures (ATF1 DXT1/DXT5, known), armour map (ATF1 ART8, 24 576 bytes – to decode), wreck mesh.
5. Config: clone `su152` (SU-122: M-30S 122 mm, 40 rounds), `t70m` (SU-76: ZiS-3, open crew compartment),
   `m4a2_sherman` (M3 Lee: 75 mm M2 in the sponson + 37 mm M6 turret, 6 crew); squads in `div_units_ussr`,
   UI icons, text names; then swap them into the Prokhorovka OOB (1446 / 1447 / 1549 SAP, 245 TR).
First vehicle: SU-122 (most of it is a T-34; the casemate and howitzer are the only new parts).

## Progress 2026-10-30 (session 2)

Reader / writer (`tools\m13\azg2.py`):
- Node header u32 #0 = matrix index (bit 31 a flag; -1 for `s_root`, `d_hull`), #1 kind (4 movable part,
  3 fixed part, 1 damage point `p_*`, 0 socket `s_*`), #2 parent, #3 first child, #4 child count.
  Matrices are local (row vectors, translation in row 3); world = local x parent world. Verified: the T-34
  exports fully assembled.
- LOD slot: `nv, ni, vertex_start, index_start, lod, -1, 3 x u32, bbox (centre xyz, 0, half-size xyz, 0)`.
- Vertex BLENDINDICES byte 0 = the k-th node (table order) that has geometry in that block; the vertex ranges
  per node are given by the slot starts (any order).
- Sections are tagged: `[CHUNKS]` (nodes), `[MATERIALS]` (0x60 each: diffuse name, normal/spec name, 8 floats),
  `[MATRICES]`, `[CHUNKS_HASH]` (node-name hash table, same hash as AZCF, 2^k >= 3n buckets, linear probing -
  reproduced exactly), `[ITABS]` (per LOD: list of the nodes with geometry), `[GEOMETRY]`.
- Geometry block u32 #2 = material index. One material per LOD block in every vehicle file; parts with another
  texture are separate mesh files attached through the `addins` table (e.g. SU-152 gun shield).
- `PNTl` block = the hit-test mesh, stored structure-of-arrays: positions (float4), normals, armour-map UVs; u32
  indices. Damage points `p_*` only have PNTl boxes.
- `write(parse(x)) == x` byte for byte for 68 of 70 vanilla meshes (both T-34s included); two track meshes differ
  in padding only. Two layouts: 64 KB-aligned buffers (older) and packed (newer Mius-Front).
- Armour map `ATF1/ART8`: 0x40 header, 8 128 bytes of flags, then 16 384 bytes that decode as a 256 x 128
  single-channel block-compressed image (thickness values) - decoding not finished.

SU-122 draft v1 (`tools\m13\su122_geom.py`, `su122_preview.py` -> `build\m13\su122_v1.obj`):
T-34 mod. 1942 hull with the turret and bow MG removed and the hull clipped by the casemate; casemate front 50 deg,
sides 20 deg from the fender line, rear 10 deg, roof 2.235 m above the ground; bell mantlet right of centre; barrel
and breech taken from the game's M-30 howitzer (user's suggestion), armoured recoil sleeve. In game the gun will be
an `addins` mesh with the M-30's own texture; SU-76 will use the ZiS-3 the same way (`zis3`: d_gunmask + d_gun).
Next: UVs for the casemate (T-34 texture), PNTl hit mesh, armour map, node table (s_rotation, d_gunmask, d_gun,
s_gun, hatches, crew sockets, p_* points), config row from t34_utz_m42 + su152 heads/weapons, pack and test.

## SU-122 v3: matched to drawings and photos (2026-10-30)

References: two 1943 scale drawings (the-blueprints.com #33200 "SU-122 (1943)" and #36929, viewed only, not stored),
the Kubinka museum SU-122 photos on Wikimedia Commons, ru.wikipedia "СУ-122", Modelist-Konstruktor "Танк СУ-122",
memo-randum.net armour table. Drawings were registered on the T-34 road-wheel centres of the game mesh (wheel z
2.602 / 1.808 / 0.875 / -0.167 / -1.035 / -1.907 / -2.658, ~139 px per metre on #36929), so every reading is in the
mesh frame (x right, y up, z forward, ground y = -1.08).

| item | v2 | drawings / photos / text | v3 |
|---|---|---|---|
| roof above ground | 2.235 m | 1.97-2.07 m; 2.235 m = top of the panorama hood | 2.00 m (hood top 2.235) |
| casemate rear (z at roof) | -0.70 (cut into the engine deck) | -0.01..-0.17, between road wheels 2 and 3 | -0.08, leaning forward 10 deg |
| bore height | 1.92 m | 1.39-1.43 m | 1.38 m |
| bore offset | 0.20 m right | 0.16-0.19 m right | 0.20 m right |
| mantlet | bell + round sleeve | cast cap reaching the roof, 1.04 m across with its side covers; trapezoid apron below it; flat-sided box over the recoil gear, 0.36 wide at the cap / 0.29 at the front, +0.30/-0.34 about the bore, front face leaning back | fixed cap on d_hull (elliptical in plan), apron on the plate, box on d_gunmask |
| muzzle ahead of box | ~1 m | 0.72-0.80 m | 0.80 m; 6.95 m overall |
| traverse / elevation | +-5 / -3..+26 | 20 deg sector, -3..+25 | +-10 / -3..+25 (config + UI) |
| entry hatch | left rear, rear hinge | right rear, lid 0.64 x 0.46 in a 0.83 x 0.62 frame, hinges on the front edge | (0.27, z 0.26), front hinge, raised frame |
| panorama hood | small, left | 0.72 x 0.60 box at the left front edge, 0.235 high | (-0.21, z 0.89) |
| PTK | right | right front corner | (0.73, z 1.03) |
| fan | right rear | left rear, 0.45 dome | (-0.35, z 0.135) |
| headlight | front plate | left side plate near the front edge (photos) | side plate, y 0.50 |
| external tanks | T-34 box tank, z -1.25/-2.15 | 90 l cylinders, 2 per side end to end from the casemate rear | 0.36 x 0.95 m cylinders at x +-1.25, z -0.80 / -1.82 |
| driver | T-34 seat | under the hatch, left of the gun | seat and cameras moved 0.28 m left; hatch (-0.55, y 0.50) |

v4 (same day): hatch, cap width, apron, box section, fan, hood size and the front / right visors re-read from #36929 at 8x.

Still approximate: the lower nose plate is the T-34's (one armour table gives 45 deg, but the SU-122 kept the T-34
lower hull, so it was left); the cap's curved side covers are folded into one elliptical casting; mirror-visor positions (front right, right side, rear) are
read off the drawings to ~0.1 m; the drawings put the front plate / roof edge ~0.15 m further forward than a 50 deg
plate from the T-34 nose allows - the documented 50 deg was kept. Early SU-122s had no fighting-compartment fan;
the 1943 drawings show it, so it stays.

## SU-122 v5: texturing and small fittings (2026-10-30)

- UVs (`tools\m13\uvtools.py`): flat parts are projected on their own plate (texture up = up the plate) and cut
  into cells mapped at a fixed 0.10 uv/m (the T-34 hull is ~0.11) onto a plain weathered-plate area of the T-34
  texture that only the removed turret used (u 0.12-0.365, v 0.04-0.12). Before, every face was stretched over
  a whole strip. Cap, fan and fuel tanks get wrapped cylindrical UVs and smooth normals; the barrel is mapped
  round its bore onto the T-34 barrel island (u 0.38-0.595, v 0.072-0.125); tanks use the light part of the
  T-34 tank island (u 0.72-0.875, v 0.795-0.855). No game texture is changed or shipped.
- New fittings: riders' handrails on both casemate sides (y 0.41, z -0.03..1.60, three brackets), pistol-port
  plug on the left side (y 0.68, z 1.13; drawings 33200 / 36929 and Kubinka photos), lifting eyes at the front
  plate's top corners and on the gun box, bolt heads on the gun box, hatch handle and hinges.
- Small fittings are left out of the far LOD and of the hit-test mesh.
- `tools\m13\tex_preview.py`: textured preview of an exported OBJ.

## SU-122 v6: details from the user's reference renders (2026-10-30)

Reference: wireframe renders of a detailed SU-122 model supplied by the user (used as a visual reference only;
no geometry taken from it).
- Gun hood: now a rounded-rectangle casting (superellipse plan, 0.72 x 0.94 m) with a flat top level with the roof,
  rounded top edge and a base flaring into the front plate; bolt heads along its rear edge, lifting eye on top.
  Box-projected UVs (no swirl on the flat top).
- Gun box: rounded top edges.
- PTK: periscope head (round base, armoured cylinder, domed top, front window) instead of a block.
- Panorama hood: shuttered openings on its front and right faces.
- Riders' grab loops along the bottom of both casemate sides; three spare track links with a retaining bar on the
  front plate right of the gun; 9R aerial base and whip at the left front corner of the roof.

Where the renders and the 1943 drawings disagree (PTK side, hatch position), the drawings and the documented
crew layout (commander right of the gun, using the PTK) were kept.

## SU-122 v7: texture fixes (2026-10-30)

- The plate texture area contained the T-34 turret's baked vision slot, an edge line and a shadow band, which
  showed up as fake slots repeated over the casemate and roof. Now only the clean part is used
  (u 0.207-0.371, v 0.046-0.115).
- Mirrored tiling: neighbouring texture cells are mirrored, so they meet edge to edge with no seam in the weathering;
  the box-projected parts (hood, fan) repeat the same way instead of clamping into stretched strips.
- Texel density unchanged at 0.10 uv/m; rain streaks run down every plate.

## SU-122 v8: geometry checked by overlay on the scale drawing (2026-10-30)

`tools\m13\overlay_render.py` draws the model's outline (silhouette + creases) in orthographic side / top / front
view at the drawing's scale; the outlines were laid over screenshots of drawing 36929 registered on the T-34 wheel
centres (138.8 px/m). Side view: casemate, roof fittings, gun box, barrel, fenders and wheels already matched within
a few cm. Fixed from the overlays:
- front plate 49 deg instead of 50: both drawings put the roof edge 0.10-0.14 m further forward than a 50 deg plate
  from the T-34 nose allows;
- driver's hatch: the SU-122's own narrow, long hatch (0.38 m wide, y 0.20-0.79 on the front plate) with its
  periscope housing, hinged at the top edge, replaces the reused T-34 hatch; driver camera moved to its periscope;
- gun hood base flares to ~1.0 m across where it meets the plate (top-view U of the drawing);
- fan cover 0.09 m forward, right-side vision device 0.14 m forward, headlight at the left front corner of the
  casemate (drawing: z 1.8, y 0.48).

## SU-122 v9: finish (2026-10-30)
- Weld beads (r 12 mm) along every casemate plate junction above the fender line (front/side, side/roof,
  front/roof, rear/roof, rear/side), generated from the casemate polytope's edges.
- Smooth shading (40 deg crease) on the gun box's rounded edges and the PTK head.
- External tanks: filler cap, two brackets and a cradle on the fender.
- Mesh: 137 nodes, LOD vertices 34.2k / 27.3k / 13.3k (u16 limit 65 535).

## SU-122 v10: checked against photographs (2026-10-30)
`tools\m13\persp_preview.py` renders the model with a perspective camera; `export_elev.py` exports it with the gun
elevated. Renders were set beside the Kubinka museum photos (Wikimedia Commons) from matching viewpoints, with the
gun raised 15-22 deg as on the museum vehicle. Changes:
- gun drum: 0.96 m across (was 0.72), rounder plan (superellipse n=3), domed top meeting the roof edge, centre
  0.06 m further forward so it stands proud of the front plate lower down (z 1.21-2.25); the hood-top bolt row
  (from the reference renders) dropped, the lifting eye kept;
- gun box: about as wide as tall (0.44 x 0.58 m at the drum, 0.38 x 0.51 m at the front), as in the photos.
Open question: the close-up photo suggests the barrel leaves the box in its upper part (recoil gear below the
barrel), both drawings show it near the middle; the drawings were kept.

## SU-122 v11 (2026-10-30)
More museum photos (Kubinka front view, Patriot-park "138" side view, Kubinka left/right sides):
- Barrel position: all photos show the barrel leaving the gun box in its upper part, the box hanging below it over
  the recoil gear. Trunnion raised to y 0.37 (bore 1.50 m above the ground); box section about the bore
  +0.22/-0.48 at the drum, +0.17/-0.44 at the front, so the box keeps the drawings' outline (1.06-1.70 m).
  This settles the open question from v10 in favour of the photos.
- Gun hood: the lower part now follows the front plate down to the fender line as one casting (front photo:
  the hood's outline runs down to the fender), 0.31 m proud of the plate at y 0.30 tapering to 0.10 m; the
  separate flat apron plate is gone.
- Second, plain plug below the pistol port on the left casemate side.

## SU-122 v12: gun and hood refitted to the drawing (2026-10-30)
The user pointed out (overlay screenshot) that after v11 the gun and hood no longer lined up with drawing 36929.
Refitted on the side-view overlay (registered on the wheel centres, 411.6 px/m at the zoom used):
- bore back at y 0.255 (1.335 m above the ground) as drawn; trunnion y 0.203; muzzle z 3.90 (drawn tip);
- gun box about the bore +0.34 / -0.29 at the drum, +0.30 / -0.30 at the front, front face at z 3.04-3.08;
- drum front at z 2.17 (was 2.25), top at y 0.90 (drawn 0.88-0.90), no lifting eye on its top;
- the drum's lower part is now nearly flush with the front plate below the box (side view shows no step there).
Side, top and front outlines now match the drawing within a few cm. (v11's photo-based barrel position is dropped.)

## SU-122 v13 (2026-10-30)
- Spare track links on the front plate removed (user request; not on the drawings or the museum vehicles).
- External tanks raised to y 0.37 (drawn 0.19-0.53, top level with the engine deck), x +-1.22, on brackets
  running in to the hull's sloping side.
- Lifting eye on the gun box moved 0.22 m back, bolt heads on its sides and the lifting eye on the drum top placed
  where the drawing shows them.

## SU-122 v14: every part checked on the drawing overlay (2026-10-30)
Side view at 555 px/m, plan and front views at 350-420 px/m, part by part:
- gun box: lower front (recoil-gear part, bore -0.08 .. -0.29) stands 8 cm proud of the upper face, as drawn;
- round bosses (d 0.23 m) on both sides of the gun drum at z 1.85, y 0.435;
- roof: entry hatch 0.10 m forward and 0.05 m right (x 0.32, z 0.36), PTK 0.11 m forward (z 1.14), sight hood
  0.08 m forward (z 0.97); casemate rear plate 0.04 m forward (z -0.04 at the roof);
- front towing hooks moved to x +-0.72 on the front plate at y -0.03; the driver's periscope flaps sit on the
  hatch's periscope housing;
- fuel-tank straps / legs at z +0.24 / -0.34 of each tank, as drawn;
- removed (not on the drawing): radio aerial, tank filler caps, the second plug on the left side.

## SU-122 v15: residual check (2026-10-30)
Residual map: every dark drawing pixel further than 4 px (~3 cm) from a model edge is marked. Above the hull side
line, what remains is drawing shading (shadows under the tanks and hood, hatching), not missing parts. Below it:
road-wheel spokes and the track, which in game come from the T-34 wheel / track parts, not from this mesh.
Changes: filler caps back on the external tanks (a dot mid-tank in the plan view), tanks 0.03 m further out (front view).

## SU-122 v16: mantlet, driver's hatch, panorama hood from close-up photos (2026-10-30)
- Gun housing: ends of the rotating gun drum (0.60 m discs with a ring and centre boss) on both housing sides about
  the trunnion; bolted U-shaped flange round the housing base on the front plate.
- Driver's hatch: flat plate (0.42 m wide) with a raised centre panel and a small periscope hood with a brow near
  its top, y 0.25-0.66 on the plate (photos); the tall periscope box is gone; the periscope flaps sit over the slot.
- Panorama hood: cast, rounded edges, flat top (drawing height 0.235 m), forward viewing slot with a rain lip;
  the louvres are gone.

## SU-122 v17: full audit (2026-10-30)
`tools\m13\su122_audit.py <mesh>` runs five automatic checks (exit code 1 on failure). v16 failed three of them:
1. Casemate walls over the tracks: the casemate volume reached down to the nose at full width, so a 0.4 m plate
   hung over the upper track run along the front 2.8 m (x +-1.29, y -0.41..-0.03) and the T-34 sponson
   underside and lower hull side were cut away there. Now two volumes: the casemate proper sits on the sponsons
   (y >= -0.022, measured sponson underside -0.026), and only the front plate continues down to the nose between
   the tracks (|x| <= 0.897; T-34 lower hull side at 0.899). Sponson underside and lower hull sides are kept.
2. T-34 kit inside the casemate: the two-man saw and its holder (half inside the casemate wall) removed; the T-34
   riders' rails and brackets that ran through the casemate (d_hullparts_late / _late_01 pieces) removed piece
   by piece. The T-34 right rear fender box moved forward to the right fender beside the casemate
   (z 0.55-1.52), where drawing 36929 shows it in plan and front view; the fuel tanks take the rear fender.
3. Unit-marking sockets (mslots): they had the SU-152 positions (up to 0.4 m off the SU-122's sides) and no
   orientation, so numbers / slogans / badge would float edge-on. Now on the casemate side plates, local z =
   plate normal: numbers above the riders' rail behind the pistol port, slogans below the rail, badge at the
   right rear (photos).
Also: SU-152 sockets keep their orientation and scale (crew seats, head-out poses, the 0.35-scaled periscope
cameras); the driver's camera sits at the periscope of the new hatch; clipped-away vertices are dropped from the
buffers (about 4 000 fewer per LOD).
Gun mask: the drum discs of v16 were removed (the drawn circle there is the headlight and the discs sat behind the
front plate); the moving mask now has a drum face (cylinder about the trunnion, r 0.49, 0.52 m wide) standing
2 cm proud of the fixed cap at bore height, as the seam in the photos and the drawn cap line at z 2.2.
Fixed: v16's su122_geom.py had a syntax error (the hood ring list); the v16 mesh was built from the previous file.

## SU-122 v18-v19: matched to six period factory photos (2026-10-30)

Photos supplied by the user (left and right profiles, 3/4 front, front, top-front; not stored in the repo).
`tools\m13\photo_match.py` solves each photo's camera from landmarks (road-wheel hubs, idler, sprocket, roof corners;
2-5 px rms on the profiles) and draws the model's outline over the photo or renders it with the same camera
(`side_by_side`); `tools\m13\render_scene.py` is a shadowed, ambient-occluded preview renderer with the T-34
running gear and a generated track.

Fixed from the photos:
- Gun mount rebuilt. The fixed sphere cap (v18) was wrong: the photos show a cast cap with a flat top at roof height,
  vertical front, rounded edges, 0.93 m wide; a vertical slot in it (0.48 m) in which a curved shield (cylinder about
  the trunnion, r 0.74, with a round boss) and the recoil-gear box move with the gun; a bolted U-frame on the plate
  round the opening below. Gun axis 0.18 m right of the centre line (was 0.20).
- The cap traverses with the gun: new node `d_gunmount` (kind 3) under `s_rotation`, so the slot clears the shield
  and box through the whole +-10 deg traverse; its skirt runs 0.15 m on behind the front plate so no gap opens.
- Trunnion at z 1.45 (was 1.72): the shield must reach the cap top at 0 deg and stay under it up to +25 deg; that
  fixes its radius to the cap height above the trunnion (0.74 m). The elevated photos (15.5-19 deg) agree.
- Gun box: top 0.34 m above the bore, short chamfer with two bolts down to a ledge, barrel opening right under
  the ledge, face down to 0.28 m below the bore, sides narrowing toward the bottom (top-front photo: chamfer,
  ledge, opening and face positions within a few px at ~4 deg elevation; profiles at 1.5 and 18.5 deg).
- Muzzle at z 3.97 (6.96 m overall).
- Rear plate of the casemate 7 cm further back (z -0.11 at the roof): three calibrated profiles agree.
- Roof (top-front photo for x, profiles for z): panorama hood right behind the gun cap (x 0.17, z 1.02),
  0.58 x 0.44 m, 0.16 m high, flat top, sloped sides, three view ports; fan dome 0.32 m at the rear centre
  (x 0.10, z 0.14); PTK on the right roof edge (x 0.92). The drawing had the hood at the left front and the fan at
  the left rear. The entry hatch is not visible in any photo: placed at the left rear, clear of the dome (uncertain).
- Driver's hatch 0.34 m wide, y 0.20-0.55 on the plate, periscope housing with three vanes; armoured periscope box
  with a knob above it (y 0.56-0.71); the front mirror device moved to the top left of the front plate.
- Headlight 0.1 m further forward and out, on its bracket at the left front corner.
- `tools\m13\su122_audit.py` check 4 now tests the new mount: shield and gun box inside the cap slot and under the
  cap top at -3 / 0 / +12 / +25 deg.
Mesh: 136 nodes, LOD vertices 31.9k / 25.9k / 13.0k.

## SU-122 v20: fitted to two scale drawings (2026-10-30)

Two scale drawings from the user (A: line drawing with a 0-3 m bar; B: shaded drawing; not stored in the repo).
`tools\m13\drawing_overlay.py` registers each of their eight views on parts the SU-122 shares with the T-34 (road
wheels, idler, sprocket, engine deck, rear hull) and draws the model's outline over it (`photo_match.Ortho`,
`drawing_views`; `edges(face_obj=...)` adds the part outlines a plan view needs). The drawings disagree with each
other, and each with itself between views, by 5-15 cm: B's casemate sits 0.13 m further forward on the same hull,
A's side view has the roof 4 cm lower than its own front and rear views. Where they differ the value between them is
used and the factory photos decide (side photos re-solved on the road wheels only; the top-front photo re-solved on
the v20 roof).

- Roof 0.10 m lower, y 0.82: drawing A 0.745-0.785, B 0.84-0.90, photos 0.82-0.85 (one profile 0.93). Ground is
  y -1.14 (track bottom); the old comment's -1.08 was the bottom of the road wheels.
- Front plate at the documented 50 deg from the T-34 nose (v19 49): roof edge at z 1.29 (photos 1.20, A 1.26-1.31,
  B 1.30-1.35).
- Cast cap: top flush with the roof, front face at z 2.13 (A 2.08-2.11, B 2.13-2.18; v19 2.25 and 0.1 m too high),
  0.98 m wide, top edge and front corners rounded r 0.24, ends at the roof's front edge; its face comes out of the
  plate at y 0.12 as in both side views; slot 0.44 m with a back wall where the cap top is closed.
- Trunnion y 0.22, z 1.47; bore y 0.272 (A 0.25-0.29, B 0.27-0.28); curved shield r 0.61.
- Recoil-gear box: top 0.29 m above the bore, bottom at y 0, long chamfer down to just under the barrel, vertical
  face at z 3.13 (A 3.08, B 3.19), 0.34 m wide narrowing to 0.26 at the bottom; bolts where both drawings have
  them, lifting eye, loop handle on the right side. Muzzle socket z 3.93.
- Frame below the cap 0.94 / 0.69 m wide, bottom y -0.21; opening in the plate y -0.15..0.15 with a 0.6 m deep
  recess, so the shield shows through it when the gun is raised.
- Roof fittings: v19 had read the top-front photo mirrored (hood right, hatch left). Drawings A, B, #36929 and the
  re-solved photo agree: panorama hood front left (x -0.19, z 1.01; 0.62 x 0.52 m, 0.14 m high, three port covers on
  its front edge, shutter bars, knob), entry hatch rear right (x 0.27, z 0.33; 0.62 x 0.58 m, low coaming, hinged at
  the front, stop bar beside it), fan dome rear left (x -0.33, z 0.22; 0.42 m, 0.11 m high, four lugs), PTK front
  right (x 0.72, z 1.08; head 0.265 m above the roof).
- Antenna back, at the right front corner of the casemate (T-34 `d_antena_wire` / `d_noantena` moved, whip cut to
  0.65 m as drawn); headlight lowered to y 0.34 beside the front-left corner.
- Vision devices just under the roof (front plate top left, right side) and a round one in the middle of the rear
  plate under a new rear handrail; side handrails at y 0.33 (A 0.35, B 0.31); pistol ports on both sides (left from
  A, right from B); riders' grab loops and two upright handles on the right side (B); marking sockets moved clear.
- Crew sockets scaled to the lower roof.
- `su122_audit.py` check 4: the box may rise out of the open part of the slot (5 cm at +25 deg), not through the
  closed cap top.
Mesh: 138 nodes, LOD vertices 33.6k / 27.3k / 13.3k.

## SU-122 v21: cap profile and gun-box face (2026-10-31)

The user marked two shapes on drawing A that were still off; both were traced at 8-10x on drawings A and B.
- Cast cap, side view: the face is not vertical. It leans back about 8.5 deg toward the top (A: z 2.127 at y 0.07 to
  2.062 at y 0.49; B: 2.178 at 0.25 to 2.131 at 0.59) and runs into the flat top through a rounding 0.18-0.19 m long and
  0.19-0.25 m high. Now: face z 2.135 at y 0.30, lean dz/dy -0.15, foot on the plate at y 0.084 / z 2.167, elliptical
  rounding 0.185 x 0.21 m into the top (flat from z 1.90). The outer top edges are rounded 0.07 m as in the front views
  (v20: 0.14 m). The slot walls end on the front plate, so they no longer overlap the dark recess behind the opening.
- Gun box, front view: the cross-section is a "coffin" - flat narrow top, sides widening to 0.32 m at the bore, rounded
  bottom 0.28 m under the bore (half-widths about the gun axis, A / B: +0.20 0.119 / 0.131, 0 0.160 / 0.153, -0.15
  0.136 / 0.130, -0.24 0.070 / 0.057). v20 was a hexagon widest near the top with a flat bottom. Same length, chamfer
  and face as v20; the bolts moved to the drawn places (two high on the chamfer at x +-0.06, two on the face beside
  the barrel at x +-0.085, 0.085 m under the bore).
- On drawing B the new outlines lie on the drawn ones; on drawing A the shapes match but sit 8 cm higher, because A's
  roof is 8 cm lower than B's and the factory photos (the roof stays at y 0.82).
Mesh: 138 nodes, LOD vertices 34.7k / 28.3k / 14.5k.

## SU-122 v22: open slot and drum shield (2026-10-31)

The user marked the top of the gun mount in drawing B's front view and the mount under the raised gun box in the 3/4
factory photo. Both show what v21 lacked: the slot in the cast cap is open right back to the roof edge, so the cap is
two separate cheeks, and the moving shield is a "drum" that fills the slot from the box up to just above the cheeks.
- Slot open to the roof edge (v21: the cap top was closed behind z 1.78); the cheeks' inner walls follow the front
  profile down to the plate.
- Shield: a surface of revolution about the trunnion axis (so it slides through the slot at any elevation), 0.39 m wide
  (front views 0.38-0.39 in a 0.44-0.46 m slot), flat top with rounded corners (the outer 45 % of each half falls back by
  up to 4.5 cm; B's front view and the curved front edge in both plan views), top 1.5 cm above the cheeks; radius 0.625
  above the bore, 0.665 round it (stays behind the cap face up to +25 deg), 0.90 low down so that with the gun raised it
  fills the opening in the plate behind the frame, as in the photo. Coarse copy for the far LOD and the hit mesh.
- The lifting eye moved from the (now open) cap top onto the shield (A z 1.59, B 1.66; B front view: a knob on the drum).
- The recess behind the opening is dark olive (T-34 texture 0.738, 0.645) instead of black.
- Photo check: the 3/4 photo's camera re-solved on the fender tops, nose, hook and roof corner, the gun pose on the barrel
  and four box bolts (camera rms 7 px, gun 11 px): the gun stands at about +9 deg elevation and -8 deg traverse in that
  photo; with that pose the cheek, the box and the shield's curved edge lie within about 10 px of the photo. The real
  front fenders have vertical fronts (the T-34 mesh's are curved), so only their top corners are used as landmarks.
- `su122_audit.py` check 4 also fails a shield standing out of the slot in front of the cap face or through the plate
  below the opening, and anything of the mount above the roof behind the roof edge.
Mesh: 138 nodes, LOD vertices 40.0k / 33.6k / 15.0k.

## SU-122 v23: gun-box underside and front-plate details (2026-10-31)

The user circled the area under the raised gun box in the 3/4 factory photo and the cap / front plate / headlight area
in drawing A's side view.
- 3/4 photo camera: re-solved on the landmarks round the gun mount (the seven frame bolts, the barrel and four box
  bolts, nose_L, hook L, left roof corner, left fender top corners): hull 10 px, gun 8 px, frame 10 px rms; gun at
  +12 deg / -4 deg in that photo. The right fender, nose_R and hook R at the photo's left edge cannot be fitted together
  with the mount (40-50 px) and had pulled the v22 camera 10 cm sideways at the mount, so every v22 comparison showed
  the mount offset. `render_scene.Scene.render(view=...)` now renders with an exact photo camera (roll and principal
  point included) for these comparisons.
- Cast cap: the cheeks traverse with the gun but the opening in the plate does not, so with the gun traversed the part
  of a cheek below the plate surface showed in the opening. The cheeks now stop at the top of the opening (y 0.09), on
  the ends of the frame bars, as the ledge in the photo. Face rounding 0.185 x 0.235 m (row scans of both side views
  agree with this profile relative to the cap top).
- Gun box: the front 4 cm stand 1.2 cm proud all round (the rim both 3/4 photos show along the edge of the front);
  section resampled smoothly from the drawn "coffin". Box and shield get sweep UVs (`uvtools.sweep_uv`) so the
  texture's weathering streaks run down them; v22's triplanar UVs made rings on the shield and stripes on the box.
- Shield: smooth (smoothstep) blends between its radii; the v22 straight ramps left a ledge under the raised box.
- Frame round the opening: outline of drawing A's front view - straight sides under the cheeks, tapering to a bottom
  bar with rounded corners; bolt pattern as drawn (two up each side, one in each bottom corner, one in the middle).
- Front plate at 51.2 deg from the T-34 nose: its roof edge at z 1.227 (line fits: drawing A 50.0 deg with the roof
  edge at 1.221, the side photos 1.19-1.20; drawing B 48.5 deg). The panorama hood follows the roof edge.
- Driver's periscope flaps (`d_cap_01/02`): the SU-122's own small covers on the periscope housing; the reused T-34
  flaps stood up to 0.26 m out in front of the hatch (a floating 'leaf' above the headlight in the side view).
- Driver's hatch, periscope box and front visor flatter (4-8 cm proud, as drawn; v22 up to 14 cm).
- New: signal horn behind the headlight (drawing A side view: dome, body, flared bell, y 0.16-0.27), headlight
  bracket down to the casemate side, a bolt low on each cheek face.
- Roof height kept at y 0.82: drawn onto the two side photos (cameras from the road wheels only) the model's roof line
  lies on the photos' roof edge; drawing A's (y 0.745) runs 4-6 cm below it on both.
- New check (not in the audit): no part or sub-piece more than 2 cm from the rest of the model, except pieces inside
  the hull.
Mesh: 138 nodes, LOD vertices 43.7k / 37.9k / 15.3k.

## SU-122 v24: towing hooks, driver's hatch, gun mask (2026-10-31)

User: the hooks have no seam lines with the hull, the driver's hatch sticks out too much, the gun mask and the part
inside the mantlet are oddly shaped and should be joined by a seam, remove the two oval things on top of the gun mask.
- Towing hooks: v20-v23 had moved the T-34 hooks (`d_kryuk_01/02`) to x +-0.72 but left their welded lugs, part of the
  T-34 hull mesh, at the T-34 positions x +-0.555. Each hook now moves together with its two lugs as one assembly
  (`hook_assembly`, `split_hook_lugs` in `su122_mesh.py`): turned 8.4 deg so the T-34 glacis maps onto the 51.2 deg
  plate, placed at x +-0.72, y -0.09 (top-front photo: x +-0.73..0.74; drawing A front view: x +-0.72), lugs 0.5 mm into
  the plate.
- Driver's hatch: lid 2 cm proud (v23: 4, with the panel 6), embossed panel 0.6 cm, periscope housing 2.5 cm on the lid
  with three low teeth, flaps lying on it; at most 5 cm in all (v23: 9.5). Periscope box above it 5 cm (7), front visor
  4.5 cm (6).
- Gun mask: the shield's top 1 cm under the cheek tops (top-front photo; v22-v23: 1.5 cm above); a weld seam round the
  gun box where it comes out of the shield (`box_shield_seam`: the box section carried back to the shield surface,
  `tube` bead r 1.1 cm), so box and shield read as one assembly; the lifting eyes on the box top and on the shield top
  removed. Weld beads use one texel of plain steel (`bead_part`).
- Removed a remnant of the T-34 bow machine-gun ball mount that stood up to 7 cm out of the front plate beside the right
  cheek (x 0.36-0.73, y 0.05-0.28): the "lump" under the right cheek.
- Antenna base at x 1.075 so it stands on the side plate (x 1.10 left a 2 cm gap).
- Floating-parts check (every sub-piece against the rest of the model): no visible piece more than 1 cm from the rest.
Mesh: 138 nodes, LOD vertices 43.9k / 38.4k / 15.4k.

## SU-122 v25: gun box and its seam with the shield (2026-10-31)

User: two 2x crops of the v24 gun-limits picture (gun at +25 deg and at 0 deg: the gun box, and where it meets the shield
next to the left cheek), no text.
- The box was tapered (0.9 wide, 0.75 high) over its rear 0.17 m (z 1.95-2.12), a leftover of v21 when it went into the
  closed cap. Since v22 it comes out of the shield at z 1.97-2.13, inside that taper, so it narrowed just before the
  shield, and v24's weld seam (drawn on the full section) stood up to 6 cm off it - a "handle" over the box top. Now a
  straight prism back to z 1.92, inside the shield's solid for the whole section (4 cm under its outer surface, 4 cm
  above its inner one); the seam lies on the box / shield intersection line.
- Seam bead (`tube`): the cross-section frame now points out from the loop's centre; the fixed up-axis frame flipped
  where the bead ran down the box sides and twisted it.
- Box section: a sharp lengthwise edge along each side at the widest point, level with the foot of the chamfer (4 cm
  under the bore). All three side factory photos (left 5c2a9524 and 783321f8, right a417840d) show the side split into a
  light upper band and a dark lower band along a crisp line at that height; v21-v24 rounded the section through it with
  smooth normals, so the box read as a tube. Upper side straight (leaning out 8 deg), lower part rounded as before
  (`BOX_COFFIN`, `BOX_CREASE_I`, `_coffin` resamples above and below the edge separately); the box's normals are smoothed
  within 12 deg only (`BOX_SMOOTH`), so that edge and the top edges stay sharp. Drawn half-widths kept to 6 mm.
- The dark jagged "crack" beside the box in the v24 picture: the real 2.5 cm gap between the drum and the slot wall
  (the top-front and 3/4 photos show it too), drawn with the preview renderer's 6 mm shadow-map texels.
  `render_scene.py`: `shadow_focus=(centre, radius)` for close-ups, 3x3 percentage-closer filtering, bias in texels.
- The v25 gun-limits picture uses v24's camera (solved from the v24 picture: SIFT matches against renders that carry a
  3D point per pixel, then the pinhole fit).
Mesh: 138 nodes, LOD vertices 43.6k / 38.1k / 15.1k. Audit 5/5 OK; floating-parts check unchanged (no gun-mask piece).

## SU-122 v26: the gun mantle re-fitted to the factory photos (2026-10-31)

User: "the entirety of gun mantle is off". All five factory photos that show the mount were given exact cameras (the
top-front one re-solved with a free focal length, 4.9 px; the front-left one solved together with the gun pose from the
barrel) and the gun pose of each photo was solved from the muzzle, the barrel exit and the chamfer bolts. Photo crops were
compared with the model's part outlines and with same-camera renders.
- Shield: a curved PLATE 5 cm thick of constant radius 0.75 about the trunnion, not a solid drum. The photos of the
  raised gun (left side 783321f8 and 5c2a9524 at ~15 deg, front-left 1e9d02f0 at ~20 deg) show its top end standing
  above the cheeks as a thin crescent with a flat end; the top-front photo (gun at 5 deg) shows the end as a bright lip;
  the 3/4 photo shows a dark recess under the raised box, not a bulging drum (v20-v25: radius 0.90 low down, 0.665 round
  the bore, 0.60 on top, 25 cm thick, rounded corners). Top end 56 deg above the bore at 0 deg: flush with the cheek tops,
  8 cm above them at +12 deg, 13 cm at +26 deg. Trunnion moved back to z 1.38 (1.47) so the plate stays behind the
  cheek faces.
- The cap is one casting again: a bridge (`cap_bridge`) closes the slot between the cheeks, flush with their tops, from
  the roof edge to under the shield's top end (top-front photo: one band across the whole cap); the plate slides over
  it. Audit check 4 now also samples every shield / box triangle against the bridge, at -3 / 0 / 12 / 25 / 26 deg.
- Slot 0.47 m, shield 0.43 m wide (top-front photo; v25 0.44 / 0.39); the cheeks' outer top edges rounded 0.10 m (0.07).
- Gun box: ends inside the plate (top-rear edge at mid-thickness), so its visible top is 5-7 cm shorter, as in the
  top-front photo; top corners rounded r ~3.5 cm (was a 1.8 cm chamfer); chamfer bolts +-0.07.
- Boss at 37 deg on the plate (45) and 3.5 cm right of the gun axis (top-front photo).
Mesh: 138 nodes, LOD vertices 39.0k / 33.5k / 15.2k. Audit 5/5 OK; floating-parts check: no gun-mount piece.

## SU-122 v27: the front of the gun box (2026-10-31)

User: "the angle of the gun mantle should be eased and its shape corrected", then circled the front end of the gun box in
the v26 left-side render: "this part sticks out too much compared to the gunmask".
- The raised front rim of v23-v26 (the front 4 cm of the box 1.2 cm proud all round) read as a flange standing out above
  and below the box. Removed: the front is flush with the box, and its edges are rounded instead (`BOX_R_EDGE` 3 cm). The
  front-left and 3/4 factory photos show a crisp edge with a narrow highlight along it, the side photos a ~4 cm band
  along the front outline - a rounded edge, not a step.
- The two angles of the side profile are eased: top -> slope with r 5 cm (`BOX_R_TOP`), slope -> vertical face with
  r 12 cm (`BOX_R_FACE`); the right-side photo (a417840d) shows the front as one smooth convex curve, the top-front photo
  a highlight band where slope and face meet. The sharp outline (top 0.29 above the bore, slope from z 2.91 down to
  z 3.13 at 4 cm under the bore, vertical face) is unchanged (drawings A and B).
- The section's top corners rounded 5 cm (3.5) and its bottom closes smoothly on the centre line.
- `mantlet()` is now one closed solid built as the exact offset of the box shrunk by `BOX_R_EDGE`: side surface, a strip
  rounding the front edge (10 deg steps, so the 12 deg normal smoothing keeps the side's lengthwise edge sharp but not the
  roundings), front surface. `mantlet(coarse=True)` for the far LOD and the hit mesh. `box_profile()` gives the eased
  profile, `box_front_point(y)` a point and normal on it; the slope and face bolts sit on it (face bolts 1.5 cm lower,
  at -0.10, below the eased corner), the side bolts at z 2.94 again (drawings; v23-v26 2.90, behind the rim).
Mesh: 138 nodes, LOD vertices 44.2k / 38.7k / 15.1k. Audit 5/5 OK; floating-parts check: no gun-mount piece.

## SU-122 v28: the driver's hatch (2026-10-31)

User: "drivers hatch needs improvement" (Blender view of v27: a flat slab with thin outline panels, three teeth and a
handle). Re-modelled from the top-front factory photo (40807adf: it sees the front plate almost square-on; features
back-projected onto the plate with the v26 camera, checked on the frame bolt next to the hatch to 3 px) and the front
views of drawings A and B (same layout); model edges drawn over the photo match to a few pixels.
- Lid: x -0.334..-0.690, y 0.16..0.415 on the plate (0.40 m along it), rounded corners r 3 cm, softened top edge, 2 cm
  proud. v20-v27 had it 14 cm too long and 8-13 cm too high (y 0.196..0.546).
- Periscope housing: a block on the lid's upper part (x -0.386..-0.585, 1-14 cm below the top edge), 5.5 cm proud, with a
  lower step beside it towards the outer edge (drawing A; in the housing's shadow in the photo). The periscope flap nodes
  (`d_cap_01/02`) are kept but now lie inside the housing (the photos show one plain block).
- Lower part: a pressed panel with a small oval boss near its outer bottom corner (drawing A).
- Hinge: five knuckles along the top edge (photo: four gaps); the lid's three are part of `d_hatch_01`, the hull's two (with
  pads above the hinge line) part of `d_hull` (`hatch_hinge_fixed`). The node now turns about the knuckles' axis (1.6 cm
  out of the plate) instead of the plate line.
- On the plate: a bar under the lid (x -0.33..-0.69, y 0.105..0.145, new); the box above the hatch with its knob moved
  down 7 cm to the photo (x -0.342..-0.512, y 0.48..0.66; knob r 3.8 cm at y 0.568), rounded; the front visor rounded,
  with a dark slit (`dark_fittings`, black texture area) instead of a brow.
- Shapes are `rounded_slab` (rounded-rectangle block on a plane, bevelled top) and `oval_dome`; far LOD and hit mesh use a
  simplified lid (lid, housing, step).
- Found by the floating-parts check: the two bolts low on the cap cheeks (v23) sat on the line of the flat face, 6-9 cm in
  front of the cheeks' rounded corners; now on the corner surface, along its normal.
Mesh: 138 nodes, LOD vertices 47.8k / 42.3k / 14.6k. Audit 5/5 OK.

## SU-122 v29: sights, vision devices and pistol ports (2026-10-31)

User: "improve on vision ports, gunners sight, other sights etc". Every device was checked on the factory photos with the
calibrated cameras (back-projection onto its plate, triangulation from two or three photos) and on the drawings.
- Commander's PTK (`ptk`, node `d_sight`): only the top-front photo shows it (in the factory photos the raised gun box
  hides it). A round head tapering from 0.14 m to 0.10 m under a rounded top, with a round window (4.6 cm, dark,
  `ptk_window`) high on its front, a band low on the head (rear views A and B), on a base flange 0.21 m across with three
  lugs (drawing A plan); 0.245 m high. x 0.70 (photo 0.69), z 1.09 (drawings). v20-v28: a square head with a half-round
  top and a brow. Far LOD / hit mesh: `ptk(simple=True)`.
- Gunner's panorama hood (`roof_parts` body, `pano_details`, `pano_windows`): 0.64 m wide at the roof, 0.47 m at the top
  (top-front photo; was 0.62 / 0.50), centred at x -0.185; a raised flap on the front slope with a round handle at its left
  end (handle triangulated from three photos to 3-5 px), a bar along the top's front edge with three dark windows, lifting
  staples on the two rear corners of the top (the top-front photo shows arches with a dark gap under them; in the 3/4 and
  front-left factory photos the bright background shows through the left one), shutter bars along the sides and back.
- Vision devices (`visor_device`): a rounded housing with a brow above the slit and a lip under it, the slit dark (black
  texture area). Front plate top left as before; right side plate moved back 10 cm to z 0.63-0.85 (photo a417840d:
  0.61-0.84; drawing B: 0.64-0.86).
- Pistol ports (`pistol_port`): a domed plug in a horseshoe guard open at the bottom (drawings A and B side and rear
  views). Left side y 0.68, z 1.05 (photos: 0.63-0.70 / 1.01-1.06; drawing A 0.69 / 1.10); right side y 0.53, z 0.765
  (photo a417840d 0.52 / 0.75, drawing B 0.54 / 0.79; was 0.56 / 0.88); the round device in the middle of the rear plate
  is a pistol port too (rear views), now the same plug and guard.
- `tube(..., normal=)`: a plane normal for the cross-section frame of open bent bars (guards, staples).
- Front-plate lifting eyes seated on the plate (they floated 1.3 cm off it; floating-parts check).
- Not modelled: in the factory photos something stands up at the rear left corner of the hood (bigger than the staple; the
  field photo 40807adf shows only the staple there) - possibly the raised panorama head or an open cover.
Mesh: 138 nodes, LOD vertices 54.2k / 48.7k / 15.1k (u16 limit 65,535). Audit 5/5 OK.

## SU-122 v30: the cap is fixed to the hull, only the gun mask moves (2026-10-31)

User: "the gunmask alone should move when gun moves, the gunmount should stay fixed to the hull". v19-v29 had the cast cap
(cheeks, slot walls, bridge, cheek bolts; node `d_gunmount`) as a child of `s_rotation`, so the whole cap swung with the
gun through the +-10 deg traverse.
- `d_gunmount` (kind 3) is now a child of `d_hull`, placed at the trunnion; only `d_gunmask` (box, shield, bolts, boss,
  seam) with `d_gun` traverses and elevates.
- Traverse axis: `s_rotation` moved 0.40 m in front of the trunnion (`TRAVERSE_DZ`; `G.TRAVERSE` = (0.18, 0.22, 1.78));
  `d_gunmask` sits on the trunnion (local (0, 0, -0.40)) and elevates about it. With the axis on the trunnion the shield's
  front swept +-13 cm in the 0.47 m slot (2 cm gaps): the box cut 5.5 cm into the cheek faces and the frame and the
  shield's top end crossed the cheek tops. With the axis 0.40 m forward the shield edge moving toward a cheek slides in
  under the cheek's surface (it moves back as it goes, so it stays hidden inside the casting), a gap opens on the other
  side (up to 8 cm at bore height), the box clears the cheek faces and the frame, and the shield's top end, standing up
  when the gun is raised, passes over the cheek tops (at +20..+25 deg and full traverse its corner overhangs the cheek's
  inner edge by 1.5-2.6 cm, clear of it). Axis positions tried: on the trunnion, 0.20, 0.30, 0.35, 0.40 m (0.35: the
  weld seam round the box still touched the slot wall at -3..+5 deg).
- `p_rothead` (the T-34 turret-ring disc, r 0.84, as damage volume) stays centred on the trunnion through a local
  offset: on the new axis it would stand 0.65 m out in front of the plate. Open: an SPG-sized volume like the SU-152's
  box (0.36 x 0.85 x 0.31 m).
- Audit check 4 rewritten for the fixed cap: `d_gunmount` must not hang under `s_rotation` / `d_gunmask`; the axes must
  match su122_geom; at traverse -10/-5/0/5/10 x elevation -3/0/5/12/20/25 no crossing (triangle against triangle) of the
  box, the shield and their fittings with the cap's outer surfaces, the frame or its bolts in front of the front plate
  (the slot walls are left out - the shield's edges slide in through them); nothing through the roof or through the plate
  below the opening; the bridge nowhere above the shield's outer surface where the plate covers it; centred, the shield
  stays behind the cap face. Negative test: axis on the trunnion 2540 crossings, 0.30 m 478; dense sweep at 0.40 m
  (traverse every 2.5 deg, elevation every 2 deg) 0.
- render_scene.py: elevation about `d_gunmask`'s origin, traverse about `s_rotation` (v25-v29 turned both about
  `s_rotation`).
- Rest pose unchanged: the four geometry blocks are byte-identical to v29 (26 bytes of the node table differ), so
  build\m13\su122_v29.obj still shows the current shape. Previews: build\m13\su122_v30_gun_limits.png (same camera and
  poses as v24-v29) and su122_v30_traverse.png (front and top close-ups at 0 / +20 deg, traverse -10 / 0 / +10).
Mesh: 138 nodes, LOD vertices 54.2k / 48.7k / 15.1k. Audit 5/5 OK.

## SU-122 v31: the gun from the M-30 - config rows and texture (2026-10-31)

User: "use the M-30 gun as source for the gun" (both the game config and the texture; the barrel geometry has been the
M-30's since v1). First in-game look (encyclopedia): the SU-122 showed with NO barrel - the add-ins were not registered
(v31a below).
- Add-in meshes are the vanilla way to put a second texture on a vehicle; a GUN as an add-in is vanilla too: the Pz III
  L / M carry `PZ3_GUN` / `PZ3M_GUN` on their recoil node `d_gun`, which is a kind-1 node with a hit shape only. The
  SU-122 does the same: `su122_barrel` and `su122_breech` (`src\m13_vehicles\mfo_gos`, listed in its `!flatlist`) carry
  the M-30's `d_gun` / `d_zatvor` geometry with the M-30's own UVs (written by su122_mesh.py next to the main mesh;
  `assemble_addin`: s_root + one kind-3 node named like the holder, three GXT2 LODs, no hit mesh, no matrices, 64 KB-
  aligned like every vanilla add-in; the breech block has no LOD3 in the M-30 file, LOD2 is reused). The vehicle's
  `addins` table attaches them: `SU122_BARREL | d_gun`, `SU122_BREECH | d_zatvor`.
- **Add-in registry (v31a - the missing piece):** every add-in name must have a row in the `addins` table of
  `common_res_mod` (tabs.flatdata): name, mesh, shader, textures (diffuse + norsp), flags, LOD count - e.g.
  `PZ3_GUN | pz3_gun | sh_object_wea | 0 | 0 | 1 | pz3gun_dift | pz3gun_norsp | ... | 1 | ... | 3`. The textures come
  from HERE, not from the mesh file's material (the SU-152's gun-shield mesh says su152_late_dift, the registry
  su152_early_dift). su122_config.py now writes `common_res_mod.config.loc_def.13_addins.delta` (two rows modelled on
  PZ3_GUN with `m30m38_dift` / `m30m38_norsp`; m13's mfo_tabs `!flatlist` lists common_res_mod, on top of the m1 / m8
  / m9 deltas per table_merge_order). Without the rows the game silently draws nothing.
- Main mesh: `d_gun` (kind 1, child of d_gunmask at the M-30's offset from the trunnion, muzzle socket s_gun at z 3.93)
  keeps only its hit shape; `d_zatvor` (kind 1, child of d_gun at the M-30's own local offset (0.155, -0.011, -2.014),
  hit shape only). v19-v30 re-UVed the barrel onto the T-34 barrel strip and folded the breech block into d_gun. 139
  nodes, LOD vertices 52.3k / 47.4k / 14.6k.
- Config (su122_config.py, `techn_base_oprum.config.loc_def.delta`): the weapons row is the M-30's own (`M30`, breech
  block `d_zatvor` swinging -110 deg, as on the towed gun) plus the SU-152's smoke-grenade row; shells: the M-30's four
  types in the SU-122's 40 rounds (OF-462 30, BP-460A 6, SH-460 2, D-462A 2) plus the SU-152's hand grenades; the
  gunner's sight on the panorama camera `s_camera_gunner_01` (in the hood) is the M-30's panoramic sight `pg` (was mk4);
  the gun's damage rows stay the SU-152's (the mount sits inside an armoured casemate). Everything else unchanged.
- Audit check 6: holders d_gun / d_zatvor kind 1 with hit shapes only, add-in files next to the mesh with the M-30
  material, one node named like the holder, three LODs, barrel end 6 cm behind the muzzle socket, d_zatvor at the M-30
  offset. 6/6 OK.
- render_scene.py `add_vehicle(addins=[(path, holder, texture)])` draws add-ins in the holder's frame and poses them
  with it; the M-30 texture is not extracted here (tex_techn.flatdata is too big to stage), so the previews show the
  barrel in a plain olive. The preview OBJ (build\m13\su122_v31.obj) carries the add-ins as objects `su122_barrel` /
  `su122_breech` placed on their holders.
- The M-30's d_gun geometry includes the two recoil rods beside the barrel (y +-0.2 about the bore, back from z 2.66):
  they lie inside the gun box, as they did since v19.
- The user's Mius-Front has no D-30 mesh (base, an87, ir80, mlc packs) - "D-30" in the request meant the M-30.
Previews: build\m13\su122_v31_gun_limits.png, su122_v31_gun.png (barrel from the right, front-left at +12 / -10, the
gun alone). Still to see in game: the barrel with the M-30 texture (the norsp name is assumed from the naming convention
of all 190 texture pairs in the registry), recoil, and the breech animation (invisible anyway).

## SU-122 v32: openings under the hatches (2026-10-31)

User (after the first battle): the opened roof hatch and the driver's hatch "have no opening" - the lids swung up over
solid plate. The casemate is a closed polytope, so an open lid showed the plate underneath.
- `hatch_openings()`: holes cut into the casemate (geom.subtract_convex, the way the gun slot is cut) under both lids,
  3 cm (`HATCH_INSET`) inside the lids' outlines: the driver's hatch in the front plate (x -0.66..-0.36, y 0.18..0.40 -
  a rectangle on the sloped plate, since its x is world x and its slope is constant), the entry hatch in the roof
  (x 0.01..0.55, z 0.07..0.59).
- `hatch_pockets()`: recesses behind the holes so an open hatch shows a dark interior and not the far side of the hull
  through culled back faces - four walls (dark olive, INNER_UV) and a back wall (black, DARK_UV); 0.35 m into the hull
  behind the driver's hatch, 0.55 m down under the roof hatch. In all three LODs.
- The hit mesh (PNTl) and the weld seams are built from the plates before the holes (`cV0`): the armour stays closed
  under the lids, no seam beads round the holes.
- Preview: build\m13\su122_v32_hatches.png (both lids open, both rotation signs - the game's hatchs rows decide the
  sign). The lids themselves are unchanged (the roof lid is still a plain plate with two hinge blocks and a grab handle).
Mesh: 139 nodes, LOD vertices 52.5k / 47.6k / 14.8k. Audit 6/6 OK. manifest 0.5.16 / 211 (the updater installs only a
higher version than the one in place).

## SU-122 v33: the cap's upper front is one big arc (2026-10-31)

User (circling the cap in the right-side factory photo): "this part is much more angled than what you've built". It is.
The cap's silhouette in that photo (a417840d, gun at 0 deg, a bright brick wall behind the cap) was traced at 6x and
back-projected with its calibrated camera, and the attached SU-122 model was read at its slot edges; the two agree
against the drawings (v21 traced the drawings' rounding as 0.185 long and 0.235 high over a face leaning 8.5 deg):
- the face is straight (lean 8.5 deg) only up to y ~0.42; above that it is one arc of r ~0.6 leaning further and
  further back, so the flat top starts at z 1.81-1.86 instead of 1.90, with a ~0.15 fillet into the top. Photo: z 2.089
  at y 0.566, 2.017 at 0.69, 1.924 at 0.79, 1.81 at the top; attached model: 2.12 at 0.50, 2.035 at 0.67, 1.935 at
  0.80, 1.84 at 0.82; v32 had 2.094 / 2.071 / 2.01 / 1.906 - up to 7 cm too far forward in the upper half.
- `CAP_ARC_Y0, CAP_ARC_R = 0.42, 0.60`, `CAP_TOP_R = 0.15` replace `CAP_RA, CAP_RB`; `_cap_arc()` derives the arc centre
  (tangent to the leaning face at CAP_ARC_Y0), the fillet centre and their tangent point; `cap_front_z()` and
  `cap_profile()` follow (face, arc, fillet), so the cap loft, the slot walls and the audit's "through the cap" test all
  use the new profile. `CAP_TOP_FRONT` (1.81) is the front edge of the flat top.
- plan corners `CAP_RS` 0.24 -> 0.30 (attached model: its outer edge is 0.28 behind the front at |x| 0.51 and 0.087 at
  0.40; r 0.24 gives 0.24 / 0.053). With r 0.30 the flat part of the face is narrower than the slot, so each cheek's
  front is one curve - the dome-like look of the 3/4 and top-front photos. The cheek bolts sit on the new corner.
- the shield is unchanged: at 0 deg its top end (y 0.84, z 1.80) is 3 cm behind the new top edge - the bright lip at the
  front edge of the band in the top-front photo - and its outer surface stays 1-6 cm inside the cheek fronts.
- the model's silhouette on the right-side photo is now within 1-2 px (~1.5 cm) of the photo's from the top to the box;
  v32 was 5-9 cm outside it.
Preview: build\m13\su122_v33_cap.png (v32 left, v33 right; 3/4 front and right side, gun at 0 deg).
Mesh: 139 nodes, LOD vertices 52.7k / 47.7k / 14.9k. Audit 6/6 OK. manifest 0.5.17 / 212. Add-in meshes unchanged.

## SU-122 v34: hood ports, roof hatch, fan dome, vision port, hatch rim, heavier welds (2026-10-31)

User: a 1/35 kit photo ("look at the detail on the top hull hatch, the vent cover and other details"), then "the mantle
has 3 vision ports, from the front, left and right, nothing else" (the hood), then a grey reference model of the roof
with "remove things on the second image, improve onto the first one" - the hinges I had built were blocks with straps,
the reference has thin hinge rods with small knuckles; its roof hatch has a long rod along its side; its fan dome is a
plain mushroom; its vision ports are box housings.
- `port_box(c, R, w, h, d, flap_deg, knob)`: an armoured vision port as a box housing d out of its plate, a dark slot in
  its front face (dark_fittings), a thin hinge rod with small knuckles along the top-front edge and a flap on the rod
  (used for the driver's port; the hood's covers are `pano_cover`).
- Panorama hood (`pano_details`, `_pano_ports`, `pano_cover`) - final, after the user's second kit photo (hood at 5x,
  seen from the right-rear: "JUST MAKE IT 100% like real SU-122"): THREE bevelled covers 1.5 cm thick and nothing else -
  on the front slope one (x +0.02..-0.335, 0.355 x 0.12, knob at its left end, three knuckles), on each sloped side one
  0.22 x 0.12 with four knuckles and a knob at the rear end; rooted 1.2 cm into the face, 1.5 cm proud (a small second
  front cover was tried and removed - user: "the part on the front right side is wrong", three ports only). The hinges are SIX chunky block knuckles per cover (up to 3.5 x 2.4 x 2.4 cm) along the top edge, alternating -
  three on the cover's edge, three up on the hood face (user: "each have 6 hinges") - not rods, not round sleeves (five tries: window bar, stub knuckles
  with straps, six-knuckle bars, rod with small sleeves, slim boxes - all rejected). Gone: staples, top plates, bars.
- Hull vision ports (`vision_port`, front plate top-left and right side plate at the v29 positions): closed armoured
  covers of the same make as the hood's (`pano_cover`, six knuckles, knob) on a thin welded base plate with a bead
  round it and a dark slit under the cover (user: both earlier ports - a box with a lifted flap, a roof-edge box - were
  "wrong"; `port_box` / `roof_edge_port` are no longer used).
- Roof hatch (`roof_parts`) - final, from the user's second kit photo (hatch at 4x): a thin flat lid (1.6 cm, rounded
  corners) sunk 1.1 cm into the roof, its top 5 mm proud (user: "sink the hatch a little more into the hull"; the
  audit's inside-casemate check now allows d_hatch_02) with a raised rim round its edge, a small knob at its rear-left corner, and TWO separate
  hinge units on the FRONT edge, each a rounded pad over the edge (with a foot down to the roof) carrying a pair of
  knuckles. No coaming ("the weird edges from the sides"), no long rod (v34e), no side hinge (v34c). The node's axis is
  on the knuckles; the hatchs row's angle is 120 deg so the lid tips over forward (user: "move it so it opens to the
  front of the tank"). Regenerated techn_base_oprum delta (only that angle changed).
- Fan dome: a smooth dome straight off the roof with FOUR vent openings at its foot on the diagonals - front-right,
  front-left, rear-left, rear-right (`fan_notches`; user: "it should have 4 vent holes", then "rotate every vent hole
  so it's correct like in the image" - both kit photos show the opening facing the hatch / front corner; these are the
  drawings' lug angles of v20).
- Commander's PTK (`ptk`): a plain cylinder 0.14 across on a low round flange, softly rounded top, a round window hole
  high on its front - no band, no lugs (grey reference; v29 had a tapered head with a band and three lugs).
- Driver's hatch lid: a raised rim 1.2 cm wide round its edge, the small oval boss is a round knob (kit).
- Weld beads r 1.7 cm (1.2); a bead round the knob box above the hatch.
Preview: build\m13\su122_v34_details.png (the roof from the right-rear, as the kit photo). Mesh: 139 nodes, LOD
vertices 58.0k / 53.0k / 16.5k. Audit 6/6 OK. manifest 0.5.18 / 213.
