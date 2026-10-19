# Mius-Front Overhaul — Design Document

Working title: **MF Overhaul** (rename later). Target: Graviteam Tactics: Mius-Front **6.00 build 3598** (final Steam version), all DLC optional.
Multiplayer transport: **MiusPlayer** (https://github.com/VampyrCat/MiusPlayer, CC0-1.0, "test version", mpmod1 / network version 12).
Date: 2026-10-15. Status: draft v0.2.1, milestone 0 toolchain findings merged (see 3.2, 3.4, 8); third-party content analysed (1.3, M8, M9, `docs/third_party.md`).

---

## 1. The two layers

| Layer | Owner | What it touches | What it must never touch |
|---|---|---|---|
| **Transport** (MiusPlayer) | VampyrCat | `root\programs\opgame.progpack`, `root\programs\tacgame.progpack`, `bin\rel\x64\basic_network.codelib`, `steam_appid.txt`, `mp_join.exe`, `mpmod1\state`, `users\mp_saves` | game data archives |
| **Content** (this overhaul) | us | data archives only: squads, weapons, ammo, OOB, quick-battle pools, sounds, textures, strings | anything in the row above |

The two sets of files are disjoint, so both can be installed in any order and MiusPlayer's enable/disable scripts never see our files. That is the whole integration contract. Everything else in this document is about making the content layer **behave well over MiusPlayer's netcode**, which has specific weaknesses we design around.

### 1.1 How MiusPlayer actually works (and why it matters to a data mod)
- **Both PCs simulate the full battle.** The owner of a unit sends its position ~15 times/s and its full saved state when that state changes. Damage is decided on the owner's PC. Nothing is predicted; remote units are drawn ~0.1 s in the past.
  → Both PCs must run **byte-identical data**. A stat mismatch does not desync-crash, it silently produces different results on each side. The overhaul therefore ships one monolithic versioned package, not mix-and-match modules, for multiplayer use.
- **Skirmish: the host chooses both forces, the joiner cannot pick units.**
  → Quick-battle pools must come in matched pairs the host can select as a unit. Pool names carry the overhaul version so both players can see it in the lobby's "commanded forces" line.
- **Not transmitted:** mines, ammunition explosions, off-map artillery called by the joiner, flares untested. Shot effects, craters, smoke, building destruction and battle statistics are local. Deployment-dug trenches land in different positions on each PC.
  → The Duel ruleset bans mines and off-map artillery outright and discourages deployment trenches. These are data-level choices, so the overhaul can enforce them in the pools.
- **Operation battles: position-only sync.** Unit-state sync there crashes the host, so losses, damage and gun direction diverge between PCs. Each operation needs its other-side version (`..._rus` / `..._ger`) with identical formations.
  → Multiplayer operations are **experimental** in this design. Our OOB changes apply to them, but any custom operation we ship must come with both side files with identical formations, or MiusPlayer shows the second player the host's view with all host groups visible.
- **Two players only, no hot-seat.** Two copies on one PC (via `steam_appid.txt` and `127.0.0.1`) are for testing only.
  → Hot-seat and play-by-save remain as the no-internet and operation-scale fallbacks (section 4, M4/M5).
- **Hard version pin:** game 6.00 build 3598, both players on network version 12, module build 2026-10-11 22:54. The enable script checks the game build.
  → The overhaul pins the same build. Because 3598 is the final Steam version, the "Graviteam patch breaks the mod" risk mostly disappears; the risk that remains is a MiusPlayer update changing behaviour.

### 1.2 What MiusPlayer gives us for free
- A **two-copies-on-one-PC test rig** (`MP_BG_FPS`, `MP_FG_FPS`, `MP_SIM_HZ`, `MP_STATE_KBPS`, `MP_SYNC_STATE`). This is how we desync-test every Duel pool without a second person.
- `_mp_research/vanilla_hashes.sha256`: SHA-256 of unmodified game files. We reuse it to verify the game build in milestone 0 and to prove our package touches none of the transport files.
- `_mp_research/tools/`: Python scripts including `compare_units.py`, `combat_diff.py`, `trench_diff.py`, `mirror_opsave.py`, `make_progpack.py`. The compare scripts are the basis of our divergence test (section 7). Python is not installed on this machine yet; it is a milestone 0 prerequisite.
- A Ghidra project of the executable (`_mp_research/ghidra_project`, `decompiled/`). Out of scope for a data mod, but the fastest way to answer "which data file does the engine read for X".

### 1.3 The third layer: other people's content
The overhaul absorbs two existing mods (full analysis in `docs/third_party.md`, entry matrix in `docs/addon_matrix.txt`):

| Mod | Author | What it is | How it enters the overhaul |
|---|---|---|---|
| Realistic Battlefield VFX Part 1 + Part 2 (Part 1 is also distributed as `T-D-Battlefield-SFX-Mod_V250919`, byte-identical) | Toni (Anton) | 63 MB of effect sprites + a clean 6.00 delta on `common_res_mod` (41 shell rows, effect-class column only), `parts`, `sfx` | **M8**. Dependency until permission; its config tables become the *base* that M1 edits on top of. |
| Achtung Panzer Ostfront Mius DataBase (1.2 GB) + Configs | night_postman | ~220 new soldier outfits/models for 1943 Eastern Front, plus the tables that bind them | DataBase: external required download, never bundled. Configs: **not installed**; it is a 2021 snapshot of `common_res_mod`, `div_units_*`, `qbattle`, `hum_params` that deletes post-2021 content. **M9** re-expresses its bindings as a delta on 6.00 tables. |

Consequence for the build: several vanilla entries now have three or four authors of changes (vanilla → M8 → M9 → M1/M2/M3). The engine cannot layer them; it takes one entry per name from one archive. So `build.ps1` must **merge at build time in a fixed order** and ship a single entry. The conflict checker's "one entry, one module" rule still holds for what is shipped; the merge is explicit, never an engine-side collision.

Multiplayer: both players need the same third-party versions as well. The `[MFO x.y]` tag therefore stands for the whole stack, and the README lists the exact dependency versions per overhaul version.

---

## 2. Pillars

1. **Simulation first.** No arcade stat inflation. Changes must be defensible from TO&E and ballistics sources.
2. **Symmetry where the player asks for it, history where they don't.** Campaigns stay historical. A separate *Duel* ruleset is balanced.
3. **Data only.** Everything lives in replaceable data files. No binary patches, no injectors, no program packs. MiusPlayer owns the code side.
4. **One package, one version, both PCs.** For multiplayer the overhaul is all-or-nothing and the version is visible in the lobby.
5. **Designed for the netcode we have.** Every Duel feature is checked against what MiusPlayer does not transmit.

---

## 3. Technical foundation (how modding this engine actually works)

### 3.1 Load rule (from the developer)
A mod file **replaces a game file with the same name**. The package it sits in does not matter, only the file type does. Mods take priority over base data.
The overhaul is a set of same-named override files. No merging, no patching of archives in place.

### 3.2 Toolchain (verified on 6.00 build 3598, 2026-10-15; details in `docs/toolchain.md`)
**There is no `unflat` / `mkflat` on this build.** `starter_x64.exe` (39 KB launcher, no `starter.exe` exists) takes a *program name* as its first comma-separated argument and looks it up in `root\programs.flatdata`, which ships only `pack_default`, `tacgame`, `opgame`, `updater`, `encycl`. `starter_x64.exe unflat, <archive>, <dir>` exits 0 after "Load data layouts..." and writes nothing. The Operation Star tool programs were never shipped with Mius-Front (Steam forum, 2016–2017). We therefore read and write the archive format ourselves; it is simple and fully decoded.

| Need | Tool | Notes |
|---|---|---|
| List / unpack an archive | `tools\gt3.ps1 list <x.flatdata>` / `tools\gt3.ps1 unpack <x.flatdata> <dir>` | Pure PowerShell. Writes `<name>.<kind>.<loc>.bin` per entry plus a `!flatlist`. Round-trip verified byte-identical on `text_loc.flatdata` (20/20 entries). |
| Pack an archive | `tools\gt3.ps1 pack <out.flatdata> <dir with !flatlist>` | Writes the AZP3 pack with the engine's hash-bucket table (needed for sound and texture entries; decoded in milestone 0b, `docs/toolchain.md` 2) and the per-entry byte-sum checksum. Repacks vanilla `sounds.flatdata` and `tabs.flatdata` byte-identically. |
| Inspect a binary config | `tools\gt3.ps1 nodes <x.config.loc_def.bin>` / `azcf` | AZCF dump (port of MiusPlayer's `azcf.py`). |
| Build the add-on | `tools\build.ps1 [-Install]` (or `tools\build.cmd [install]`) | Packs every `src\<module>\<archive>\!flatlist`, writes `desc.addpack` from `manifest.txt`, zips `build\<addon_path>_<version>.gt3ext`; `-Install` drops it into `new_updates\`. |
| Install an add-on | `.gt3ext` in `new_updates\`; the game's updater installs it at the next start into `data\common\<addon_path>\` and registers it in `data\common\shared\config\paths.cfgpack` | Verified: installed in 11 s, `[i_qbattle]` scans `data\common\mfo_overhaul\shared\camps\qb\` at startup. Manage via the *Version:* label top-right. |
| Sounds and textures | In-game wrench tool: main menu → `player: NN` → wrench → *sounds* / *textures* → *source files* → *build* | Produces `ch_sounds.flatdata` / `ch_textures.flatdata` add-ons (the same format `gt3.ps1` writes). |
| Compressed audio | `xWMAEncode -b 160000 in.wav name.loc_def.wav` | Ambients, speech, music. Unverified on this build. |
| Verify game build | `mpmod1\game_build_3598.sha256` (full paths; the repo's `_mp_research/vanilla_hashes.sha256` has bare names) | 20 files: 18 codelib/reslib, `root\programs.flatdata`, `starter_x64.exe`. All match on this machine. |
| Divergence test | MiusPlayer two-copy rig (`MP_DUMP=1 MP_DEBUG=1 MP_BG_FPS=30`) + `tools\mp_compare.ps1` | Section 7 and `docs/miusplayer_compat.md` (baseline and tolerances). Reads only MiusPlayer's own dump/trace/log files; no Python needed for the comparison. |

### 3.3 Working folder convention
```
<game root>\
  users\modwork\            <- unpacked originals, never edited directly (text_loc, tabs, tabs_oprum done)
  users\modwork\_orig\3598\ <- pristine copy per game build, for diffing
  new_updates\              <- drop built .gt3ext here to install
  data\common\mfo_overhaul\ <- where the updater installs our add-on (desc.addpack + shared\packed_data\mfo_*.flatdata)
  data\common\shared\config\paths.cfgpack  <- updater-maintained add-on registry. Never edit by hand.
  users\profiles\<id>\      <- per-profile saves (this machine: users\profiles\cloud\, profile 'xyz')
  mpmod1\                   <- MiusPlayer. Never write here.
  root\programs\            <- MiusPlayer's progpacks. Never write here.
  bin\rel\x64\              <- MiusPlayer's codelib. Never write here.
```
Repo side: `src\<module>\<archive folder>\!flatlist` + `<entry>.<kind>.<loc>.bin` (whole entry) or `<entry>.<kind>.<loc>[.<tag>].delta` (row-level delta on the merged table, config entries only; `docs/toolchain.md` 7). Archive folders must start with `mfo_` so our archive names never collide with vanilla ones; the *entries* inside carry the vanilla names, which is what the engine overrides by. Several modules may contribute to one entry as long as they name the same archive folder; the build merges them in `table_merge_order`.

### 3.4 What is known to be moddable (community-verified)
- Squad composition and weapon stats; platoon composition; campaign order of battle; quick-battle platoon pools (`div_pool`)
- Signal troops; forward observers attached to mortar/artillery units; off-map artillery availability; shell damage
- Fuel, physics weight and similar per-unit values; sounds (easy); textures (doable); localization strings
- **Not practically moddable:** new 3D models, battle-editor logic, AI, UI, netcode (that last one is now MiusPlayer's job).

Real names on build 3598 (from `docs/archive_catalog.txt`, every entry of every archive; entries are `name / kind / loc` inside a `.flatdata`):

| What | Archive | Entry (kind config unless noted) | Inside |
|---|---|---|---|
| Squads, soldier slots, random vehicle picks, trophies, support platoons | `data\common\shared\packed_data\tabs_oprum.flatdata` | `div_units_ussr`, `div_units_ger`, `div_units_misc` | nodes `units` (156 rows ×17 cols), `squads` (347 ×30), `randoms`, `trophy`, `supports` (31 ×15) |
| Quick-battle pools (Operation Star's `div_pool`) | `tabs_oprum.flatdata` | `qbattle` (646 nodes) | `ccombat` (343 map/placement rows), one `p_<side>_<formation>` struct + `pool` table (4 cols: squad/platoon id, count, ?, support id) per pool |
| Weapon and shell stats | `data\common\shared\packed_data\tabs.flatdata` | `common_res_mod` | `weapons` (260 ×31), `shells` (364 ×43), `sights`, `addins`, `tracks`, `links` |
| Infantry weapon loadouts by soldier type and date | `tabs.flatdata` | `ammo_hum` | struct per soldier type (`rkka_rifle`, `#GERrkka_rifle`…) with `default` and `0xYYYYMMDD` dated tables |
| Vehicle ammunition loads by date | `tabs.flatdata` | `ammo` | struct per vehicle (`t34_stz_m41`…) with dated tables |
| Vehicles | `tabs_oprum.flatdata` | `techn_base` (3277 nodes), `techn_base_oprum` | per vehicle: `props`, `weapons`, `shells`, physics |
| Soldier types | `tabs.flatdata` / `tabs_oprum.flatdata` | `rus_hum_base`, `ger_hum_base` (+`_winter`, `_autumn`), `hum_params`, `outfit_hum*` | redirect chains per role |
| Sides, organisations, medals, unit types | `tabs.flatdata` | `sides` | |
| Campaign OOB (shipped operations) | `data\oprum\shared\camps\1943_07_Mius\*.campack2`, `1943_08_Mius\*.campack2`, `1941_10_Mius\*.campack2` | loose files, one `_GER` and one `_RUS` per operation (`_NA_` = the current-format rebuild the game plays) | AZP3 packs: `desc` (AZCF: campgen block, `reserves` formations with pools, `act_platoons` with `pool`/`slots` kids), `div_pool`, `scripts` (AZSC), `text` x2, `op_image`. Decoded 2026-10-16, see `docs\oob_stepanowka_17jul.md`; M2 ships them via `src\m2_oob\camps\` |
| Quick-battle maps | `data\oprum\shared\camps\qb\6M_Mius.qbdesc`, `6M_Mius_a.qbdesc` | loose files | |
| English unit / platoon / pool names | `data\common\loc_eng\packed_data\text_loc.flatdata` | `01_loc_kit_units`, `01_loc_kit_plats`, `00_loc_kit_weaps`, `02_loc_qbattle`, `11_loc_qbattle_common` (kind `text`, loc `loc_eng`) | AZTX: key records → (length, offset) string table; same-length in-place edits are safe |
| Text added by patches | `loc_eng\packed_data\text_upd_loc.flatdata` | `20_loc_kit_upd` | |

A community mod on this machine (Achtung Panzer Ostfront Mius Configs, 2021) overrides exactly `outfit_hum*`, `hum_params`, `common_res_mod`, `rus_hum_base*`, `ger_hum_base*`, `div_units_ger`, `div_units_ussr`, `qbattle` from one archive, which confirms these are the squad/OOB/pool override points.

---

## 4. Modules

For single-player, modules are independent. For multiplayer, players install the **full package** (section 1.1). The conflict checker still enforces that no two modules override the same file name.

### M1 — Core: squads, weapons, ammunition
- Rebuild squad tables from 1943 TO&E. Fix vanilla oddities (ammo loads, LMG per squad, SMG ratios).
- Weapon stat pass: rate of fire, effective ranges, ammo counts. Ballistics stay vanilla unless a source disagrees.
- Ammunition availability by month for the 1943 Mius sector.
- **MP note:** damage is decided on the owner's PC with the owner's data. Identical data on both PCs is the only requirement; no stat is "netcode-sensitive" beyond that.

### M2 — Orders of battle and reinforcement
- Campaign OOB overrides for shipped operations at actual strength.
- Replace wire-only signal sections with manpack radio where historically correct; attach dismounted FO teams to mortar and artillery platoons.
- Off-map artillery: remove or restrict by period. **MP note:** this also removes the "joiner's off-map artillery is not sent" problem for any pool that uses M2 units.
- Any custom operation ships with both `_rus` and `_ger` side files with identical formations, otherwise MiusPlayer cannot show the second player a correct map.

### M3 — Quick Battle and the *Duel* ruleset  (the multiplayer surface)
- Rework `div_pool` so quick battle offers coherent battlegroups.
- **Duel pools come in named pairs** the host picks together: `[MFO 0.x] Duel A1 — SOV rifle coy (+)` / `[MFO 0.x] Duel A1 — GER gren coy (+)`. The version tag is in the name because the lobby shows commanded forces and nothing else from our side.
- Each pair: same point total, same slot structure, point values written into the description.
- **Duel rules enforced in data:** no mines, no off-map artillery, no flares, no ammunition-dump objects. Deployment trenches allowed but flagged in the rules text as "visual only, positions differ per PC".
- Short-battle preset: ≤30 minutes, ≤10 platoons per side, ~150 units max, which keeps MiusPlayer under its 300–400 KB/s typical load.
- Every pair passes the divergence test (section 7) before release.

### M4 — Hot-seat co-op (fallback, one PC, no internet)
Unchanged from v0.1: role split, pause cadence, order phases. See `docs/hotseat.md`. MiusPlayer does not do hot-seat, so this stays.

### M5 — Play-by-save operational campaign (fallback for operations)
MiusPlayer's operation mode is position-only and diverges in losses. Until that is fixed upstream, play-by-save is the honest way to run a full operation between two people. See `docs/play_by_save.md`. The companion tool reuses `mirror_opsave.py` ideas from MiusPlayer's research folder for side mirroring.

### M6 — Sound (optional, single-player only by default)
Sound is local on both PCs and harmless to sync, but it breaks the "full package" rule. Ship as a separately versioned optional pack and say in the lobby-name convention that it is not part of the version tag.

### M7 — Textures and localization
- Uniform and vehicle marking corrections for the Mius sector, summer 1943. Checked against the Achtung Panzer DataBase (20 vanilla overrides) and Kuli Kraut Fix (21), which retexture the same German infantry sets.
- English loc pass: unit names, platoon descriptions, Duel pool text, rules text, hot-seat instructions.

### M8 — Battlefield VFX (Realistic Battlefield VFX by Toni)
- Part 1 textures: 17 vanilla `tex_misc` overrides plus new sprites. Shipped as-is once permitted; until then a dependency.
- Part 2 configs: `common_res_mod` (effect-class column of 41 shells), `parts` (+9 generator/part rows), `sfx` (effect selection). These tables are the **base layer** for everything M1 does to `common_res_mod`; the build applies M1's row edits on top so Toni's classes survive.
- Verified: no physics column changes, so no simulation effect. Visual effects are local in MiusPlayer anyway.
- Duel rule check: M8 adds flare generators (`ext_flare_obj*`); flares stay banned in Duel pools regardless.

### M9 — Achtung Panzer port (night_postman's soldier models on 6.00 tables)
- Keep: his `outfit_hum`, `outfit_hum_autumn`, `outfit_hum_winter` entries (+137 / +127 / +158 nodes), `ger_hum_base*` (+114), `rus_hum_base*` (+98), `hum_params.links_*` rows, `div_units_*.units` rows that reference his models, the two `trans_marks0_dift*` textures.
- Drop: his `common_res_mod` (2 nodes vs 7), his `qbattle` (half the rows), his `div_units_*.squads` (189 vs 362) and the deleted `trophy`/`supports`/`randoms` nodes. Vanilla 6.00 stays authoritative there.
- Mechanism: a diff tool over AZCF nodes (extend `tools\gt3.ps1`) produces the delta once; the build re-applies it to vanilla tables, then M1/M2/M3 edit the result.
- Requires the DataBase add-on installed; M9 only binds, it carries no models.
- Publishing M9 needs night_postman's permission (derived work). Development and private testing do not.

---

## 5. Source layout (this repo)

```
gtmf-overhaul\
  DESIGN.md                this file
  README.md                player-facing install and changelog
  manifest.txt             mod name, version, game build, transport version it was verified with
  src\
    m1_core\  m2_oob\  m3_quickbattle\  m6_sound\  m7_textures_loc\  m8_vfx\  m9_ap_port\
  docs\
    miusplayer_compat.md   install order, do-not-touch list, divergence test, known netcode gaps
    third_party.md         inventory, permissions, collision analysis and decisions for Toni's and night_postman's mods
    addon_matrix.txt       generated: every entry present in more than one archive, with its sources
    hotseat.md
    play_by_save.md
    sources.md
  tools\
    build.cmd              unpack / repack / stage helpers (wraps starter.exe)
    check_conflicts.ps1    merge plan + rules: one archive per entry, whole entries only from the first contributor, deltas only
                           from merge-order modules, nothing from the transport's do-not-touch list (-Plan feeds build.ps1)
    addon_matrix.ps1       lists every installed add-on archive and reports entry-level overrides and collisions
    pbs\                   play-by-save companion tool
  build\
```

---

## 6. Compatibility contract with MiusPlayer

1. **Never ship, modify or delete** `root\programs\*.progpack`, `bin\rel\x64\*.codelib`, `steam_appid.txt`, `mp_join.exe`, anything under `mpmod1\` or `users\mp_saves\`. The conflict checker fails the build if a staged file matches any of these names.
2. **Install order is irrelevant** because the file sets are disjoint. Document both orders as supported; test both in milestone 0.
3. **Version visibility:** every Duel pool name starts with `[MFO <version>]`. Players compare tags in the lobby. The manifest records the MiusPlayer network version and module build we tested against.
4. **Identical data on both PCs** is the player's responsibility; the README says so in the first paragraph of the multiplayer section.
5. **No reliance on untransmitted mechanics** in anything labelled Duel (mines, off-map artillery, flares, ammo dumps).
6. **Custom operations ship both side files** with identical formations.
7. **We never read or depend on MiusPlayer's state notes** (`mpmod1\state`). If MiusPlayer changes its internals, nothing on our side moves.
8. **Upstream first:** any netcode gap we hit gets filed as an issue on the MiusPlayer repo rather than worked around in data in a way that would misbehave once upstream fixes it.

---

## 7. Build and test pipeline

1. `tools\gt3.ps1 unpack <archive> <game>\users\modwork\<name>` → unpack a vanilla archive, keep a pristine copy in `_orig\3598\`.
2. Copy the entries you change into `src\<module>\mfo_<archive>\` with a `!flatlist` listing only them; edit there.
3. `tools\build.ps1` runs `tools\check_conflicts.ps1` → fails on any name on the MiusPlayer do-not-touch list, on an entry shipped whole by two modules (or whole by a module that comes after a delta), on an entry spread over two archives, or on a delta from a module outside the merge order.
   **Merge stage (since 2026-10-15, `docs/toolchain.md` 7):** before packing, the build assembles every entry from its contributions in the order vanilla → m8_vfx → m9_ap_port → m1_core → m2_oob → m3_quickbattle (`manifest.txt` `table_merge_order`). A module contributes a whole entry (`<name>.<kind>.<loc>.bin`, only the first contributor may) or row-level deltas (`<name>.<kind>.<loc>[.<tag>].delta`, `gt3.ps1 diff` format, applied with `gt3.ps1 apply` on the pristine `_orig\3598` table). `common_res_mod` = vanilla + Toni's delta (m8) + our sound-class delta (m1); `parts`/`sfx` = vanilla + Toni's deltas (+ our flare delta); the 12 soldier tables = vanilla + M9 deltas. Intermediate tables stay in `build\merge\_steps\`. First delta build verified byte-identical to the last whole-table build on all 22 entries.
   Run `tools\addon_matrix.ps1` after installing to confirm no entry is shipped by two registered add-ons.
4. `tools\build.ps1 -Install` → packs each `mfo_*.flatdata`, writes `desc.addpack`, zips `build\mfo_overhaul_<version>.gt3ext`, copies it into `new_updates\`. Start the game once; the updater installs it.
5. **Single-player smoke:** vanilla save loads, quick battle both sides, one campaign turn.
6. **Divergence test (per Duel pair):** two game copies on one PC with MiusPlayer (`MP_DUMP=1 MP_DEBUG=1 MP_BG_FPS=30`), host + join on `127.0.0.1`, fixed pool pair, 10-minute battle, end on both, then `tools\mp_compare.ps1`. Pass criteria (vanilla baseline measured 2026-10-15): equal unit counts every second, 0 states rejected or not loaded, 0 shots refused, clock drift ≤ 0.5 s, no unit beyond 5 m at the dump moments; kill totals compared by eye on both result screens. Any Duel pair that diverges more than vanilla is reworked or dropped.
7. **Install-order test:** overhaul then MiusPlayer, and MiusPlayer then overhaul; `vanilla_hashes.sha256` must still flag only MiusPlayer's five files as changed.
8. On a MiusPlayer update: re-run 6 and 7, bump `transport_tested` in the manifest.

---

## 8. Milestones

| # | Goal | Done when |
|---|---|---|
| 0 | Toolchain + transport proven on 6.00/3598 | **Done 2026-10-15.** Build verified 3598 (20/20 hashes). `unflat`/`mkflat` do not exist on this build; `tools\gt3.ps1` replaces them and round-trips byte-identically. Test add-on (`rkka_squad_inf_43a` renamed to "MFO Riflemen (e.1943)") built, installed by the game's updater, confirmed in game. Both install orders hash-clean. Python 3.12 installed; vanilla divergence baseline measured over MiusPlayer with `tools\mp_compare.ps1` (154 units, 687 s, zero rejected/unloaded/refused, drift ≤ 0.2 s; `docs/miusplayer_compat.md`). |
| 0b | Third-party integration groundwork | **Done 2026-10-15.** AZCF row-delta tool done (`gt3.ps1 diff/apply`, full format and hash decoded, `docs/toolchain.md` 3.1; round-trips all 14 AP Configs tables and Toni's 3 identically). M9 delta extracted (`tools/m9_extract.ps1`, `src/m9_ap_port`, `docs/third_party.md` 5.1) and built into 0.2.5. Collision winner settled: the first entry in `paths.cfgpack` wins and the updater puts the newest install first (`docs/third_party.md` 4, 4.1; user tests on 0.2.1 and 0.2.9). Ported models confirmed in game on 0.2.9 and again after AP Configs was removed via the Version label (DataBase kept); quick battle lists both sides' formations from vanilla `qbattle`. Also in 0b: struct field-name hash tables and the AZP3 bucket table decoded, so `gt3.ps1` now writes tables and archives the engine accepts (`docs/toolchain.md` 2, 3.1). Permission requests drafted (`docs/permission_requests.md`), not yet posted; nothing third-party ships. Open: the registry-position rule means players must install the overhaul last (README), and the build-time merge stage is still to be written. |
| 1 | M1 Core alpha | 1943 squads and weapon stats in, documented in `docs/sources.md`; edits applied on top of M8's tables |
| 2 | M3 Duel pairs | Three mirrored pairs playable in skirmish over MiusPlayer, each passing the divergence test |
| 3 | First real two-PC session | Two people finish a Duel over the internet, lobby tags match, no crash |
| 4 | M2 OOB + M7 loc | Shipped operations use corrected OOB; both side files present for any custom operation |
| 5 | M4 + M5 fallbacks documented and tooled | Hot-seat doc final; play-by-save tool v1 round-trips a 3-turn operation |
| 6 | M6 sound (optional) | Built with in-game tool, coexists with existing sound packs |
| 7 | Public 1.0 | `.gt3ext` on ModDB and the Graviteam forum, manifest pinned to 3598 and a MiusPlayer network version |

---

## 9. Risks

- **MiusPlayer is a test version with 0 stars and 6 commits.** It may stall or change radically. Mitigation: the content layer is useful single-player regardless, and the contract in section 6 keeps us decoupled.
- **Mod tools do not exist on 3598** (confirmed). Resolved by `tools\gt3.ps1`, which writes the archive format directly. The AZCF cell format and the column meanings of `div_units_*` and `qbattle` are documented in `docs\tables.md` (2026-10-15; member slots, dates, sides, text keys and pool/platoon fields are high-confidence, a few rating/flag columns remain to be tested in game). Row editing itself (relocating a table to append rows) is still to be implemented in `gt3.ps1`. The 2021 community Configs mod proves such edits load.
- **Silent divergence.** Players with mismatched versions get different battles without an error. Mitigation: version tag in pool names, README warning, and nothing else we can do at data level. Worth an upstream feature request: a data checksum in the lobby.
- **Operation multiplayer is fundamentally position-only today.** Do not market MP operations until upstream fixes state sync (`MP_SYNC_STATE` crash).
- **Point balance in Duel is subjective.** Publish the formula, iterate.
- **Python dependency** for the compare scripts. Acceptable for developers, not required for players.
- **No redistribution rights yet** for Toni's or night_postman's work. Until granted, the overhaul ships only our own files and the README lists their mods as dependencies with exact versions. If either refuses, M8 stays a dependency forever and M9 is withheld; the rest of the overhaul is unaffected.
- **Achtung Panzer Configs installed by players anyway.** It silently reverts `common_res_mod`, `qbattle` and the squad tables to 2021. The README says in bold not to install it; a future check in the build or a startup warning string in the quick-battle list is worth considering.
- **Collision winner.** Verified 2026-10-15 by ear (0.2.1 smoke sounds): mfo_overhaul's entries beat RukiSoundMod, RBVFX Part 2 and AP Configs on this install, so the overhaul sits on top of the dependency add-ons. Whether that is because it is registered first in `paths.cfgpack` or because of its type flag is still open (`docs/third_party.md` §4). We still merge at build time rather than rely on it, and the dependency add-ons we do not control can still collide with each other (RBVFX Part 1 vs AP DataBase on one texture).

---

## 10. Sources

- MiusPlayer repository and README (mechanism, limits, file list, test variables): https://github.com/VampyrCat/MiusPlayer
- MiusPlayer research tools and vanilla hashes: https://github.com/VampyrCat/MiusPlayer/tree/main/_mp_research
- Developer statements on multiplayer (Apr 2020): https://steamcommunity.com/app/312980/discussions/0/2264691117430387256/
- Official Addon Creation Guide (EN, 2009): https://graviteam.com/AP-STAR/TOOLS/modtools_(eng).pdf
- Official Addon Creation Guide (RU, 2011, has the unflat example): https://graviteam.com/AP-STAR/TOOLS/modtools_(rus).pdf
- Advanced sound modding, in-game wrench tool steps (2025), developer load-priority rule: https://steamcommunity.com/app/312980/discussions/0/2692512878709223043/
- Mod tools status for Mius-Front, div_pool and squad editing: https://steamcommunity.com/app/312980/discussions/0/276237094323448217/
- What has been modded (squads, OOB, FO teams, off-map arty): https://steamcommunity.com/app/312980/discussions/0/5750503966488820033/
- Third-party tooling that drives starter.exe the official way: https://github.com/murkzuk/sabow-ext-tools
- Mius-Front user guide (gt3ext / new_updates install): https://store.steampowered.com/manual/312980/?l=english
- Realistic Battlefield VFX 1.1 by Toni (parts, install, no licence stated): https://steamcommunity.com/app/312980/discussions/0/596286707636141131/
- Toned-Down (T-D) Battlefield SFX, the earlier name of the same work: https://www.youtube.com/watch?v=kTJS-htakjo
- Achtung Panzer! OstFront Mius skin mod by night_postman (files, re-hosts, known bugs, no licence stated): https://steamcommunity.com/app/312980/discussions/0/1642041106353358037/
- Mius-Front list of mods (authors and dates): https://steamcommunity.com/app/312980/discussions/0/343787920137827172/
