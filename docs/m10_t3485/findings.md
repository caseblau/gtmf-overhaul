# M10 — porting a T-34-85 into Mius-Front: probe findings (2026-10-21)

Probes: `tools\sf_probe.ps1` (report `probe_report.txt`, Mius-Front rows in `mf_rows\`), `tools\sf_probe2.ps1`
(`probe2_report.txt`, Steel Fury text files in `sf_cfg\`). Both read-only.

## 1. What a Mius-Front vehicle is (reference: T-34 mod. 1942 UTZ, `t34_utz_m42`)

Assets (`gos_techn*.flatdata`, `tex_techn*.flatdata`, kinds `mesh` / `texture` / `armor`):
- hull mesh `t34_42_utz` (1.7 MB, `mesh_lods=3`), wreck `rtank_ostov*` via `tabs\ostovs.cfgpack`
- running gear meshes bound by name: `T34UTZ_LAZY` (idler), `T34UTZ_STAR` (sprocket), `T34UTZ_WHEEL_LIT/_VA`,
  `T34UTZ_LBAL/LBAL2/RBAL/RBAL2` (suspension arms, `addins` node), track `t34_500` (`cpillars` node)
- textures `reg_t34_42_utz_dift` (diffuse), `bump_t34_42_utz_norsp` (normal+spec), `*_wint` winter set
- armour entry `arm_t34_42_utz_dift` (24 KB, referenced by `props.armor_map`), plus `arm`/`arm_week`/`armor_thick`
  numbers in `props`

Config (`tabs\techn_base.config`): one node per vehicle with 36 child tables, exported in `mf_rows\techn_base\0037..0072`:
`props` (73 fields: mesh, type, mass, engine, fuel, armour, sounds, AI ranges), `gears`, `wheels` (14 rows → mesh
nodes `d_wheel_01..14`), `cpillars` (track runs), `col_pts`/`col_bounds` (collision: `d_hull`, `d_head`, `d_gun`),
`weapons` (`F34` on `d_gun`/`head1`, two `DT`, `GREN_TR` smoke), `shells` (ammo load by shell id), `heads` (turret
`head1` = `d_head`+`d_gunmask`, bow MG `head2`), `work_places` (driver, gunner, loader, mgunner + 12 riders), `sights`
(camera sockets `s_camera_*`), `damages` (hit points `p_engine`, `p_ammo_01..03`, `p_fueltank_01..04`, `p_radio`,
`p_rotgun`, `p_rothead`, `p_transm`, `p_accum_*`), `mslots` (number/slogan decals), `flames`, `random` (optional
parts), `smk_gen`, `carets` (arm→wheel), `lights`, `hatchs` (`d_hatch_01..03`, `d_cap_*`), `addins`, `detachable`
(`BR_KRYUK`, wings, tubes, boxes) and empty ones (`glass`, `bridges`, `stanins`, `rot_elems`, `propellers`,
`shell_paths`, `swim_vols`, `pick_points`, `head_limit`, `crew_paths`, `crew_fireplaces`).
Other tables that name the vehicle: `common_res_mod.addins`, `div_units_ussr` (`units`, `squads`, `randoms`),
`qbattle` pools, `ui_params.techns`, `sb_tms_def.sprites`, `common_res.tm_remap`, plus the `text_loc` names.

Consequence: every mesh must carry the named node hierarchy the tables point at (`d_*` parts, `s_*` sockets, `p_*`
damage points). A port is (a) a mesh in the Mius-Front `mesh` format with those nodes, (b) textures, (c) an `armor`
entry, (d) a cloned `techn_base` node with new gun/ammo rows, (e) squads/pools/UI/text rows.

## 2. Steel Fury - Kharkov 1942 (user's install, base game + unofficial patch + compass mod)

- No flatdata. Data is `data\k42\loc_rus\cd\*.datapack` (gos 35 MB = objects, tex_pack0-9 = textures, armor_maps,
  main = `levels\tech_cfg\*.engcfg` vehicle configs, sounds, misc) and `envs\*\*.polypack` (28 terrains ~34 MB each,
  lightmaps as `.raw`), loose `.engcfg`/`.text` files.
- Container `AZP2` (header `AZP2`, u32 0x14, u32 entry count, u32 ?, u32 data size; entry table of variable-length
  records `<name>,<source path>,<loc>,<ext>,` + binary fields). Predecessor of the AZP3 that `gt3.ps1` reads; entry
  bodies look compressed or scrambled (high entropy right after the table). Not yet decoded.
- Meshes are `.go` files ("graphic object"), textures `.tga`/`.dds`, armour maps `.tga` in `armor_maps.datapack`
  (`t34_76_armor`), vehicle configs are text `.engcfg` (`t34_76`, `t34_76stz`, `coc_t34`, `shpaths_t34`,
  `t34_places`). Same concepts as Mius-Front (named parts, armour map, shell paths, crew places) one engine
  generation earlier.
- **The base game has no T-34-85.** Its Soviet tanks are the T-34 mod. 1941 (plant 183 and STZ). A T-34-85 in
  Steel Fury comes from the community STA mod (Steel Tank Add-on), which is not installed here.
- `docs\editor_manual.pdf` (1.3 MB) is the Steel Fury mission editor manual (height maps as TGA) — worth reading for
  the terrain question, not for vehicles.

## 3. Where that leaves the T-34-85

Routes, best first:
1. A T-34-85 from a Graviteam game of the Mius-Front generation (Operation Star / Achtung Panzer / Steel Armor
   lineage): same `mesh` kind expected, port = steps (b)-(e) above. Needs that game installed; no such DLC is known
   on this Mius-Front install (`an87`, `ir80`, `mlc` packs are 1969-1988 content).
2. STA mod's T-34-85 from Steel Fury: needs STA installed, the STA authors' permission, an AZP2 unpacker (feasible),
   and a `.go` → `mesh` converter (reverse-engineering both formats: the hard tier).
3. Build the mesh ourselves once the `mesh` format is decoded (same converter work, no third-party asset).

Decision pending: which source the user can provide.
