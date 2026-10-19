# Toolchain notes for Graviteam Tactics: Mius-Front 6.00 build 3598

Everything here was verified on 2026-10-15 against a Steam install (buildid 16070931) with MiusPlayer mpmod1 (network version 12) enabled.

## 1. What the launcher does with arguments
- The game root has `starter_x64.exe` (39 936 bytes) and no `starter.exe`. It loads `bin\rel\x64\base_shell.codelib` and nothing else.
- Arguments are comma-separated. The first is a *program name* looked up in `root\programs.flatdata` (kind `program`, loc `loc_def`),
  e.g. MiusPlayer's `run_tac.bat`: `starter_x64.exe root\programs\tacgame.progpack, data\common\shared\config\tacgame_image.cfgpack, users\profiles, cloud, *:*, 0, 1`.
- `root\programs.flatdata` contains exactly: `pack_default` (progdesc), `tacgame`, `opgame`, `updater`, `encycl`. There is no `unflat`, `mkflat`, `pd2cfgp`, `cfgp2pd`, `cfgfix`.
- Test: `starter_x64.exe unflat, data\common\Achtung_Panzer_Ostfront_Mius_DataBase\shared\packed_data\MIUS_DB_Equip_Weapons_Ger.flatdata, users\modwork\MIUS_DB_Equip_Weapons_Ger`
  run from the game root → exit code 0, `out\common_engine.log` holds only "Load data layouts...", nothing written, no error. Same with `starter.exe` is impossible (file absent).
- No codelib on this build contains the strings `unflat`, `mkflat` or `flatlist`. The Operation Star modding tools were never shipped with Mius-Front (Steam discussions 276237094323448217, 2016–2017).
- `starter_x64.exe` with no arguments starts the game normally (main menu reached in ~6 s on this machine).

## 2. AZP3 `.flatdata` pack format
```
0x00  'AZP3'
0x04  u32  entry count
0x08  u32  hash bucket count B (power of two, or 0)
0x10  u64  offset of first entry body region (= 0x40 + B*8 + count*0x80, rounded; informational)
0x20  char[0x20] 'GRAVITECH3 pack system v3.0' (mod archives also say GRAVITECH2; both load)
0x40  B × { u32 0x80000000|home_slot, u32 entry_index }   linear-probing hash table (slot = f(name) unknown)
then  count × 0x80 entry:
      u32 9 | u32 checksum | u64 offset | u64 size | u64 0 | char[0x20] name | char[0x20] kind | char[0x20] loc | 0x20 zero
then  entry bodies, each starting on a 0x1000 boundary; the first at 0x10000 in every archive seen.
```
- `checksum` = sum of all body bytes mod 2^32. Verified on every entry of `root\programs.flatdata` and of the installed mod `rvfxmod.flatdata`.
- The hash table is optional for lookups: all three entry lookups in `base_shell.codelib` (0x180007b10, 0x1800339b6, 0x18003734c) scan the entry table linearly when B = 0, which is why archives with fewer than 4 entries (`data_loc.flatdata`, `text_upd_loc.flatdata`, `rvfxmod.flatdata`) and the overhaul's early B = 0 archives load. The overhaul's sound entries not being heard (0.2.1–0.2.11 tests) is therefore **not** explained by the missing table; the cause is still open (see `docs/third_party.md` and the parent session's sound notes). Since milestone 0b `tools\gt3.ps1 pack` writes the table anyway, exactly as the engine does: B = smallest power of two ≥ 3·count for count ≥ 4, slots `{0x80000000|home, entry index}` filled in entry order with linear probing, home = `Azp3-Hash(name, kind, loc, B)`: the three strings hashed one after another with the AZCF step `h = (a·h + c) mod B; a = (a·0x6a2f) mod (B−1)`, `a` restarting at 0x7e9f for each string and `h` carrying over (`base_shell.codelib` 0x180007030; the lookup at 0x180007b10 then compares name, kind and loc). Reproduces the bucket tables of all 34 hashed vanilla/DataBase archives; repacking `tabs.flatdata`, `sounds.flatdata`, `text_loc.flatdata`, `music.flatdata` gives byte-identical files. Header 0x10 = 0x40 + B·8 + count·0x80. The engine's writer leaves archives with fewer than 4 entries without a table; `gt3.ps1 pack <out> <dir> hash` forces one (16 buckets minimum, the reader only masks with B−1) for add-ons that ship one or two sounds or textures. All three lookup sites scan linearly when B = 0, so a forced table changes nothing for lookups by name; it only matters if some code iterates bucket slots directly, which has not been seen.
- MiusPlayer's `azcf.py` assumes the entry table at 0xC0, which is only right for B = 16; use `0x40 + B*8`.
- Kinds seen: `config`, `text`, `texture`, `image`, `sound`, `armor`, `fontmap`, `program`, `progdesc`, plus mesh kinds in `gos_*`. Locs: `loc_def`, `loc_eng`, `loc_rus`.
- Override rule (developer statement): a mod entry replaces the game entry with the same name and kind, whatever archive it sits in. Our archives are therefore named `mfo_*` and carry vanilla *entry* names.

## 3. AZCF binary config (`.cfgpack`, `.addpack`, config entries)
Ported from MiusPlayer `_mp_research/tools/azcf.py` into `gt3.ps1` (`azcf`, `nodes`, `csv`, descriptor patching). Header 0x40, node table of 0x80 records
(name, type 1 struct / 2 table, cols, rows, type-string offset, data offset…). Each node has a *type string*, one char per column, using
Graviteam's text-format letters: `s` string, `u` unsigned/FCC code/date, `a` int vector, `v` float vector, `f` float, `b` bool.
A cell is 0x20 bytes: four 32-bit value slots (vectors use up to all four), the kind at +0x10 (2 string, 4 u32, 6 int, 1 float vector, 0 float, 5 bool), three zero words.
String cells are patched by appending the new string and re-pointing the cell (no other offsets move). This is how `build.ps1` writes `desc.addpack`.
`tools\gt3.ps1 csv <bin> <node|#index|*> [out]` exports a node (or every node) as CSV with decoded cells; `tools\gt3.ps1 text <bin> [out.csv]` dumps an AZTX text pack.
Column meanings of `div_units_*` (`units`, `squads`, `randoms`, `trophy`, `supports`) and `qbattle` (formations, pools, platoons) are in `docs\tables.md`.

### 3.1 Full AZCF layout, hash function and the row-delta tool (milestone 0b, 2026-10-15)
Decoded completely so that `gt3.ps1` can *write* tables with added rows and nodes, not only patch cells in place.
Verified by parsing and re-serialising all 78 config entries of `tabs.flatdata` and `tabs_oprum.flatdata`
(`tools\azcf_check.py` compares nodes, cells, kid lists and hash tables: 78/78 identical) and by round-tripping the
tables of both community add-ons (below).

```
0x00 'AZCF'   0x04 u32 node count   0x08 u32 node table offset (0x40)   0x0c u32 root hash buckets
0x10 u32 root hash offset   0x14..0x1f zero   0x20 char[0x20] name (e.g. 'common_res_mod'; Toni's files say 'common_res_mod.loc_def', harmless)
node record 0x80: char[0x20] name; u32 type (0 root, 1 struct, 2 table), cols, rows, type-string offset, data offset,
                  kids offset, kid count, 0, 0, hash buckets, hash offset, zeros
regions, in this order, no padding:
  cell data of every node in node order   struct row = cell[0x20] + char[0x20] field name; table row = cols × cell
  hash table of every node that has one   N × { u32 0x80000000|home slot, u32 kid index }
  kid-index array of every node with kids  (leaves point their kids offset at the first array)
  per node: its type string, then the strings that first appear in it (NUL-terminated cp1251, shared across nodes)
```
- Node order is a pre-order walk of the tree (parent, then its kids). `qbattle` nests `p_*` formations under
  `reserves` and each `pool` under its formation; `ammo`/`ammo_hum` nest dated tables under a struct per vehicle/soldier.
- **Hash table** (only for nodes with ≥ 4 kids): `N = smallest power of two ≥ 3·kids`. Kids are inserted in order with
  linear probing. The home slot comes from the engine's own routine, read out of `base_encycl.codelib` (the same code
  is linked into every codelib) at `0x180004910`:
  ```
  h = 0; a = 0x7e9f
  for each byte c of the name (signed char):  h = (a*h + c) mod N;  a = (a*0x6a2f) mod (N-1)     (32-bit wraparound)
  ```
  It matches all 7 415 hashed names in the vanilla tables and rebuilds every one of their 257 hash tables byte for byte.
  No standard hash (FNV, djb2, ELF, CRC, murmur, lookup2, ...) matched, so do not guess; use `Azcf-Hash`.
- A struct's type string equals the kinds of its fields and a table's the kinds of its columns in every vanilla node;
  `Azcf-Save` regenerates struct type strings and refuses a table row whose kinds disagree with the columns.
- The engine's writer orders the string pool by allocation time (it keeps duplicate texts and the order is not the row
  order), which a table cannot record. A rewritten file is therefore node- and cell-identical but not byte-identical
  (strings move, everything else is in place). Both engines' readers only follow offsets, so this does not matter.
- Community tables can carry junk: night_postman's `ger_hum_base_autumn` has struct rows of kind 7 with no field name
  and Russian comments appended to type strings. `Azcf-Save` keeps such a type string untouched; `m9_extract.ps1`
  drops the junk rows.

Commands (all PowerShell, no Python needed):
```powershell
tools\gt3.ps1 diff    <base.bin> <target.bin> [out.delta]   # row-level delta: node+/node-/shape~/types~/row+/row-/row~/order/kids/name~
tools\gt3.ps1 apply   <base.bin> <delta> <out.bin>          # base + delta; grows tables, adds nodes, rebuilds hash tables
tools\gt3.ps1 rewrite <in.bin> <out.bin>                    # parse + serialise (writer self-test)
tools\gt3.ps1 same    <a.bin> <b.bin>                       # node/cell comparison
python -I tools\azcf_check.py <a.bin> <b.bin>               # independent structural comparison (hash tables, kids, cells)
```
Delta format: one op per line, `|`-separated, documented at the top of the delta section in `gt3.ps1`. Rows are keyed
by column 0 (field name for structs); repeated keys get `#<md5-8>` so inserts and removals elsewhere do not shift them.
Cells are written reversibly: `s:text`, `u:150`, `u:'GREM'`, `u:0x19430801`, `a:1;2`, `v:0.5`, `f:`, `b:`.

Round-trip evidence (`apply(vanilla, diff(vanilla, mod))` compared to `mod` with `azcf_check.py`):
Realistic Battlefield VFX Part 2 `common_res_mod` (41 changed rows), `parts` (+9 rows, 1 node replaced), `sfx`
(55 changed rows): identical. All 14 Achtung Panzer Configs tables (up to 316 added nodes, 1 187 added rows, 273
removed rows, reordered rows and a reshaped `reserves` struct): identical. `qbattle` takes ~25 s because `ccombat`
has 343 rows sharing the same key; everything else is 1–12 s.

## 4. AZTX text entries
`'AZTX'`, loc name at 0x20; 0x40 u32 key count, 0x44 offset of the key records, 0x48 bucket count (4096), 0x4c bucket table offset (0x50; AZP3-style `{0x80000000|slot, record offset}` hash table).
Key records of 0x30 bytes `{char[0x20] key, u32 item count, u32 items offset, u32 hash?, u32 0}`;
items are `{u32 len, u32 str_off, u64 0}` (unit entries have two: short name, long name); strings are NUL-terminated cp1251 and packed back to back. `gt3.ps1 text` reads this.
Same-length in-place edits are safe. Longer strings need the table rebuilt (not implemented yet).

## 5. Add-ons (`.gt3ext`)
- A plain ZIP (deflate). Must contain `core/desc.addpack`; everything under `core/` is extracted to `data\common\<path>\` where `path` is the `path` field of the descriptor.
- `desc.addpack` is an AZCF with struct `i_updater:updater`: `path` (s), `desc` (s), `authors` (s), `version` (u32, higher wins; "prev ver >= new ver, skip!"), `type` (fourcc `RES` for mods, `ADDN` for DLC), `clear_prev` (bool), `eng_ver` (u32 1536 = 6.00), `id` (s `gtmf`). DLCs add `no_check_loc`, `sys_path`, `recover` and per-locale `desc` nodes.
- Installer: `base_updater.codelib`, program `updater`. At every start it scans `new_updates\` ("Auto install addon *new_updates\"), unzips, then rewrites `data\common\shared\config\paths.cfgpack` with the list of add-on folders. Log: `out\i_updater.log`. Our test install took 11 s and left the `.gt3ext` in `new_updates\` (same as the DLC files), skipped on later starts by version.
- The engine scans each registered add-on at startup (`[i_qbattle:qbattle] data\common\mfo_overhaul\shared\camps\qb\` in `out\common_engine.log`).
- The in-game wrench builder (main menu → `player: NN` → wrench → sounds/textures → source files / build) produces add-ons of the same shape (`data\common\<GUID>\desc.addpack` + `shared\packed_data\ch_sounds.flatdata`).

## 5.1 How entries are resolved (read from the codelibs, 2026-10-15)
- Configs and text: looked up per request by name/kind/loc; `base_shell` walks the mounted packs in order and returns the first match (0x180007b10 / 0x1800339b6; linear scan when the pack has no bucket table). In game the first entry of `paths.cfgpack` wins (user test, `docs/third_party.md` 4.1).
- Sounds: at audio start `basic_sound` enumerates **every** entry of kind `sound` in **every** mounted pack (resource manager vtable slot 0x38, `base_shell` 0x180033c20, duplicates included) into its own sorted fragment table and resolves patterns like `expl_smk*` there. A same-named add-on entry does not replace the vanilla one (observed through 0.2.1–0.3.1; the duplicate rule in `basic_sound` 0x180008b93 was not fully decoded). **Rule for the overhaul: give sounds new names and reference them from our `sfx` table instead of overriding vanilla names.**
- Textures and meshes follow their own managers; not read yet.

## 6. Vanilla archives of interest
`docs\archive_catalog.txt` lists all 106 archives and their entries. Squads/pools/vehicles: `data\common\shared\packed_data\tabs_oprum.flatdata`; weapons/shells/soldiers/ammo: `tabs.flatdata`; English text: `data\common\loc_eng\packed_data\text_loc.flatdata`; base-game campaigns `data\oprum\shared\camps\`. See DESIGN.md 3.4.

## 7. Build: the merge stage, how to edit a table, known good commands

### 7.1 One entry per name, assembled at build time (since 2026-10-15, build 0.3.4 sources)
The engine takes one entry per name from one archive and cannot layer add-ons (DESIGN.md 1.3). Several modules change
the same vanilla tables (Toni's effect classes, night_postman's soldier bindings, our own edits), so `tools\build.ps1`
assembles every such entry itself, in the fixed order of `manifest.txt` `table_merge_order`
(`vanilla > m8_vfx > m9_ap_port > m1_core > m2_oob > m3_quickbattle`), and ships the result once.

**Source layout.** `src\<module>\<archive>\!flatlist` lists the entries the module contributes to that archive
(`<name>, <kind>, <loc> ;` lines, the unflat format). Each listed entry is one of
```
<name>.<kind>.<loc>.bin                 whole entry: replaces vanilla. The only form for text, texture and sound entries.
<name>.<kind>.<loc>[.<tag>].delta       row-level AZCF delta (gt3.ps1 diff format, section 3.1) on top of whatever the
                                        modules before it left. A module may stack several on one entry; they apply in
                                        tag order, so number the tags (m8: 1_rbvfx2, 2_mfo).
```
The archive folder name says where the entry ships, and every module that touches an entry uses the same one
(`common_res_mod` → `mfo_tabs`, `parts`/`sfx` → `mfo_vfx`, the 12 soldier tables → `mfo_tabs_ap`). Today:

| Module | Archive | Ships |
|---|---|---|
| `m8_vfx` | `mfo_tabs` | `common_res_mod.config.loc_def.1_rbvfx2.delta` (Toni's 41 effect-class cells) |
| `m8_vfx` | `mfo_vfx` | `parts…1_rbvfx2.delta` (+9 rows, 13 changed, `pgens_desc_wint` emptied), `parts…2_mfo.delta` (our 4 flare rows), `sfx…1_rbvfx2.delta` (`expl_desc`/`expl_dect`, his broken `expl_snds` rows left out), `sfx…2_mfo.delta` (our 2 `expl_snds` rows, 0.3.4) |
| `m9_ap_port` | `mfo_tabs_ap` | 12 `<table>.config.loc_def.delta` from `tools\m9_extract.ps1`, 2 whole `trans_marks0_dift*` textures |
| `m9_ap_port` | `mfo_tabs` | `common_res_mod.config.loc_def.delta` (0.3.5, hand-written: the 63 `addins` rows his outfits reference; not produced by `m9_extract.ps1`, keep it when regenerating) |
| `m1_core` | `mfo_tabs` | `common_res_mod.config.loc_def.delta` (31 sound-class cells, applied after m8's and m9's) |

**Operation packs (since 0.5.0).** `src\<module>\camps\<chapter>\<op>\!flatlist` lists entries of the vanilla
`data\oprum\shared\camps\<chapter>\<op>.campack2` (an AZP3 pack: `desc` and `div_pool` configs, `scripts`, two `text` packs,
`op_image`); the same `.bin` / `.delta` forms apply, the archive id is `camps/<chapter>/<op>`, and the build unpacks the vanilla
pack, merges, and rebuilds it as `core\shared\camps\<chapter>\<op>.campack2` (installed under `data\common\<addon>\shared\camps\`,
the layout the DLCs use). `tools\gt3.ps1 lib` dot-sources the AZCF/AZTX functions for generators such as `tools\oob_17jul.ps1`.
Column meanings of the operation `desc` (formations, platoons, battle groups) are in `docs\oob_stepanowka_17jul.md` 1.

**Rules** (`tools\check_conflicts.ps1`, run by the build, exit 1 on any of these): an entry ships in one archive only;
at most one module ships it whole, and only the first contributing module may (a later module's whole copy would
silently discard the earlier deltas, so it is refused with the hint to convert it); a module contributes an entry whole
or as deltas, not both; deltas come only from modules named in `table_merge_order` and only for `config` entries
(AZCF); every file is listed in `!flatlist` and every listed entry has a file; nothing on the MiusPlayer do-not-touch
list; archive folders carry the `mfo_` prefix (or are `ch_sounds` / `ch_textures`). With `-Plan` it prints one
`plan|<archive>|<name>|<kind>|<loc>|<module>|whole/delta|<path>` line per contribution in application order; that is
what `build.ps1` executes.

**What the build does.** For every entry: a whole first contribution is copied; otherwise the pristine vanilla entry is
taken from `-VanillaRoot` (default `GTMF_VANILLA`, else `<GameRoot>\users\modwork\_orig\3598`, searched recursively, so
`tabs\`, `tabs_oprum\`, `text_loc\` as unpacked in milestone 0). Each delta is applied with `gt3.ps1 apply`; every
intermediate table is kept as `build\merge\_steps\<archive>\<name>.<kind>.<loc>.<n>_<module>.bin`, the final entries are
staged in `build\merge\<archive>\` with a generated `!flatlist`, and `gt3.ps1 pack` packs from there. Entry order inside
an archive = order of first appearance over the modules in merge order. A full build takes ~30 s (the 15 applies).
`-BuildDir <dir>` builds somewhere else, for verification builds that must not touch `build\`.

**Verified 2026-10-15:** the first delta build was compared with the last whole-table build (0.3.2 sources, staged
14:38): all 5 archives byte-identical, all 22 entries byte-identical, and `azcf_check.py` IDENTICAL on the 15 config
entries (`common_res_mod`, `parts`, `sfx`, the 12 M9 tables). The writer's string-pool order happens to match Toni's
files too, so even the entries that used to be his bytes plus in-place patches reproduce exactly. Against the installed
0.3.4 package (whose `sfx`/`parts` edits were made in place on the whole tables and recovered into the `2_mfo` deltas):
4 archives byte-identical, `parts` byte-identical, `sfx` IDENTICAL in every node, cell and hash table and 16 bytes
shorter (the in-place string edit had left slack behind the shortened string; the writer pools it once).

### 7.2 How to change a table
1. Build once (`tools\build.ps1`, needs `GTMF_ROOT` for the vanilla tables). The table *as your module receives it*
   is `build\merge\_steps\<archive>\<name>.config.loc_def.<n>_<module>.bin` of the last module before yours
   (vanilla itself if none; for `m1_core` on `common_res_mod` that is `…1_m8_vfx.bin`). The table as shipped is
   `build\merge\<archive>\<name>.config.loc_def.bin`.
2. Copy that base somewhere, edit the copy (`tools\azcf_setcell.ps1` for cells; `gt3.ps1 csv` to inspect).
   If your module already has a delta for the entry, start from the shipped table instead and edit that: the new
   diff then contains the old and the new changes together.
3. `tools\gt3.ps1 diff <base> <edited copy> src\<module>\<archive>\<name>.config.loc_def[.<tag>].delta`, add a
   provenance comment at the top (`#` lines are ignored), list the entry in that folder's `!flatlist`, add the
   `docs\sources.md` line, build again. Diff against the right base: a diff taken against vanilla would re-state (or
   revert) what the earlier modules did.
4. Third-party deltas are regenerated, never edited: `gt3.ps1 diff <vanilla> <his table>` for Toni's three (then
   drop the `row~|expl_snds|` lines of `sfx` by hand, see `docs\third_party.md` 3.2); `tools\m9_extract.ps1` for
   night_postman's twelve (writes the deltas into `src\m9_ap_port\mfo_tabs_ap\`, the merged tables it checks into
   `build\m9_merged\`, the unfiltered diffs into `build\m9_raw\`).
5. A delta that no longer applies (`row 'x' not found`) means an earlier module or a game update changed the row
   key: fix the delta or regenerate it from a fresh diff.

### 7.3 Known good commands
```powershell
$env:GTMF_ROOT = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front'
tools\gt3.ps1 list   "$env:GTMF_ROOT\data\common\shared\packed_data\tabs_oprum.flatdata"
tools\gt3.ps1 unpack "$env:GTMF_ROOT\data\common\loc_eng\packed_data\text_loc.flatdata" "$env:GTMF_ROOT\users\modwork\text_loc"
tools\gt3.ps1 pack   "$env:GTMF_ROOT\users\modwork\text_loc_repack.flatdata" "$env:GTMF_ROOT\users\modwork\text_loc"   # 20/20 entries byte-identical
tools\gt3.ps1 nodes  "$env:GTMF_ROOT\users\modwork\tabs_oprum\div_units_ussr.config.loc_def.bin"
tools\check_conflicts.ps1 -SrcRoot src -MergeOrder 'vanilla > m8_vfx > m9_ap_port > m1_core > m2_oob > m3_quickbattle' -Prefix mfo_ -Plan
tools\build.ps1                                   # merge + pack + zip into build\
tools\build.ps1 -BuildDir $env:TEMP\mfo_check      # same, elsewhere
tools\build.ps1 -Install
tools\gt3.ps1 same build\merge\mfo_tabs\common_res_mod.config.loc_def.bin <other.bin>
python -I tools\azcf_check.py <a.bin> <b.bin>
tools\catalog.ps1 -GameRoot $env:GTMF_ROOT
```

## 8. Machine notes (2026-10-15)
- `d3d9.dll` in the game root is DXVK 3.1 (user-installed renderer wrapper); it is not in the vanilla hash list and is harmless to us.
- Installed community add-ons: Achtung Panzer Ostfront Mius Configs + DataBase (2021 model/texture/config mod), RukiSoundMod, Realistic Battlefield VFX Part 2, Kuli Kraut Fix and two more texture packs. They override some of the same tables we will touch (`div_units_*`, `qbattle`, `common_res_mod`). Which add-on wins when two override the same entry is **unknown** and must be tested before release; for clean tests disable them (remove via the *Version:* label).
- Python 3.12.10 installed 2026-10-15 via `winget install Python.Python.3.12` (`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`). Git: not installed. MiusPlayer repo fetched as a ZIP with `curl.exe`.
- MiusPlayer two-copy rig: `MP_WINDOW` must not be used on this machine (fullscreen window moved to a half screen loses mouse input); `MP_DUMP=1` writes `out\mp_units_<pid>_<ms>.txt` at 10 ms / 1 s / 5 s / 20 s battle time (a moment can be skipped if no step lands on it exactly), `MP_DEBUG=1` writes `out\mp_trace_tacgame_<pid>.txt` per second. The battle runs in a separate `starter_x64.exe` process per copy (`basic_network_tacgame_<pid>.log`); it logs `objman=0x7FDF20`, not the 0x7FDEF0 hard-coded in MiusPlayer's `objs.py`. `tools\mp_compare.ps1` evaluates the files; it never reads process memory.
