# Third-party content: what is in it, how it collides, how we include it

Analysed 2026-10-15 from the files in Downloads and the copies installed in the game (build 3598).
Entry-level override matrix: `docs/addon_matrix.txt` (regenerate with `tools\addon_matrix.ps1`).

## 1. Inventory

| File | Add-on name (descriptor) | Author | Engine ver | Payload | Verdict |
|---|---|---|---|---|---|
| `T-D-Battlefield-SFX-Mod_V250919.gt3ext` (10.2 MB) | T-D-Battlefield-SFX-Mod, version 5 | Anton (Toni on Steam) | 1536 = 6.00 | `ch_textures.flatdata`, 63.25 MB | **Identical to RBVFX Part 1** (same SHA-256). "T-D" = Toned-Down, the pre-release name. Drop it, keep Part 1. |
| `Realistic Battlefield VFX Part 1.gt3ext` (10.2 MB) | Realistic Battlefield VFX Part 1, version 1 | Anton | 1536 | `ch_textures.flatdata`, 63.25 MB: VFX sprites (flames, smoke, blasts, flashes, tracers) | Include as **M8 textures**. Overrides 17 vanilla `tex_misc` textures, rest are new entries. |
| (installed only, not in Downloads) `rbvfxpart2` | Realistic Battlefield VFX Part 2, version 100 | Anton | 0 | `rvfxmod.flatdata`: `common_res_mod`, `parts`, `sfx` configs | Include as **M8 configs**. It is the half that actually drives the effects. The user listed "Part 1" twice; this is the missing second part. |
| `Achtung_Panzer_Ostfront_Mius_Configs.gt3ext` (1.1 MB) | Achtung Panzer Ostfront Mius Configs, version 1118 | night_postman | 1291 (2021 engine) | `MIUS_Configs_Files.flatdata`: 14 config tables + 2 marking textures | **Cannot be included as-is.** Tables are a 2021 snapshot that deletes 6.00 content (see §3). Port as **M9 delta**. |
| `Achtung_Panzer_Ostfront_Mius_DataBase.gt3ext` (1 204.7 MB) | Achtung Panzer Ostfront Mius DataBase, version 1118 | night_postman | 1291 | 9 archives: soldier/equipment meshes and textures by nation and season, blood textures | Keep as a **separate required download**, not bundled (size, permission). Overrides 20 vanilla entries, rest new. |

Readmes (Russian, Windows-1251): Configs = "configuration files that register the mod's models and textures in the game", requires DataBase; config version August 2021 ("German machine guns and 1941 units added"). DataBase = "models and textures", requires Configs.

## 2. Permissions

Neither author publishes a licence or a redistribution statement. Toni's threads say nothing; night_postman's files were re-hosted by others "hoping the OP doesn't mind".
**Rule:** nothing of theirs ships inside `mfo_overhaul_*.gt3ext` until written permission exists. Until then:
- Part 1 and Part 2 of RBVFX and both Achtung Panzer files are **dependencies**: the README links the authors' own downloads and the build never copies their archives.
- The M9 delta (our re-expression of night_postman's bindings on 6.00 tables) is a derived work and also needs his OK before release. It can be developed and tested privately meanwhile.
- Ask: Toni via the RBVFX 1.1 Steam thread (596286707636141131); night_postman via the skin mod thread (1642041106353358037) or the Graviteam forum. Record answers here.

## 3. What each one overrides (from the matrix)

Vanilla entries overridden, by add-on: AP Configs 16, AP DataBase 20, RBVFX Part 1 17, RBVFX Part 2 3, Kuli Kraut Fix 21, RukiSoundMod 244, T-D 17 (same as Part 1).

Collisions between add-ons:
- `common_res_mod` (config): **AP Configs vs RBVFX Part 2**. Both registered; which one the engine takes is unknown. One of them is silently dead.
- `trans_sfx_03_dift` (texture): RBVFX Part 1 vs AP DataBase `Edelveys_blood`. Cosmetic.
- Everything in Part 1 vs T-D: identical bytes, harmless.

### 3.1 Achtung Panzer Configs is a 2021 snapshot, not a delta
Node-level diff against 6.00 vanilla (`tools\gt3.ps1 nodes`):

| Table | Vanilla 6.00 | AP Configs | Effect if AP wins |
|---|---|---|---|
| `common_res_mod` | 7 nodes: tracks, shells, sights, weapons, links, addins(1232 rows) | 2 nodes: addins(101 rows) | loses every shell, weapon, sight, track and link definition added since 2021 |
| `div_units_ger` | units 197, squads 362, + trophy/supports/randoms | units 276, squads 189, no trophy/supports/randoms | adds 1941 units, drops 173 squads and three whole nodes |
| `div_units_ussr` | units 156, squads 347, + trophy/supports/randoms | units 186, squads 155 | same pattern |
| `qbattle` | ccombat 343 rows | ccombat 168 rows | half the quick-battle entries gone |
| `hum_params` | 29 nodes | 27 nodes: adds links_aut_*, drops speech_arab/far and links_sum_ir/iq/ija; `links_sum_wer` 16→64, `links_sum_rkka` 12→45 rows | far richer soldier-model links for 1943 Eastern Front, but every post-2021 nation removed |
| `outfit_hum*`, `ger_hum_base*`, `rus_hum_base*` | 70 / 84 / 75 nodes | 207 / 198 / 173 nodes | the real payload: ~120 new German and ~100 new Soviet soldier outfits and models |

This explains the known bugs people report with the mod on current builds (missing SdKfz 251 in some scenarios, mixed-nation crews, quick-battle crashes).
The bindings are valuable; the snapshot is not. M9 = take 6.00 vanilla tables, add night_postman's new `outfit_hum*`, `*_hum_base*` and `hum_params.links_*` entries, keep his `div_units` unit rows that reference his models, keep vanilla squads/trophy/supports/randoms, keep vanilla `common_res_mod` and `qbattle` entirely, carry the two `trans_marks0_dift*` textures.

### 3.2 Realistic Battlefield VFX Part 2 is a clean delta on 6.00
- `common_res_mod`: same 7 nodes, same row counts. **41 rows of `shells` differ, all in column 22 only** (the effect-class fourcc, e.g. `17736`→`GREM`, `LLHE`→`GREN`). No mass, velocity or fragmentation column changes. The author's "shell physics unchanged" claim is verified.
- `parts`: `parts_desc` +4 rows, `pgens_desc` +5 rows (new generators such as `ext_flare_obj*`, `torch_ksc`), `pgens_desc_wint` emptied.
- `sfx`: same shape, 55 changed lines in `expl_desc`, `expl_snds`, `expl_dect` (effect selection per shell class). **Correction (2026-10-15, 0.3.2):** the 19 `expl_snds` changes are not intentional. Every vanilla cell of the form `"expl_smk*, acts"` (sound pattern, mixer group) is split across two columns in Toni's table, shifting the row and dropping its tail. Effect in game: explosion and smoke sounds are bound without their mixer group (default group: loud, long range) and the engine logs `Bind() Unable to find audio fragment 'acts'` / similar per event. This is the cause of the "smoke grenade too loud" report. The overhaul ships `sfx` with vanilla `expl_snds` and Toni's `expl_desc`/`expl_dect`. Report to Toni with the permission request.
- Multiplayer: identical data on both PCs is still mandatory, but nothing here changes simulation results. Visual effects are local in MiusPlayer anyway.

### 3.3 Overlap with the overhaul's own modules
- M1 (weapons, ammunition) edits `common_res_mod.shells` and `weapons`. **M1 must start from RBVFX Part 2's `common_res_mod`**, not vanilla, or we revert Toni's 41 class changes. Build rule: the M8 config is the base, M1 patches rows on top, one archive ships the result.
- M1/M2/M3 edit `div_units_*` and `qbattle`. M9 edits `div_units_*.units`. Same rule: one merged table per entry name, assembled by the build from (vanilla → M9 delta → M1/M2/M3 delta). The conflict checker already refuses two modules shipping the same entry, so the merge has to be explicit in `build.ps1`, not accidental.
- M7 textures: AP DataBase and Kuli Kraut Fix both retexture German infantry (`reg_g*`, `reg_pzgr*`). Our uniform corrections must be checked against both.

## 4. Load order observed (paths.cfgpack, top first)
mfo_overhaul, RukiSoundMod 3/2/1, AP Configs, AP DataBase, rbvfxpart2, RBVFX Part 1, T-D, Kuli Kraut Fix, then the 17 DLC folders.
The second column is 1 for mfo_overhaul and the DLCs, 0 for the community add-ons; meaning unknown.

### 4.1 Order or flag? (milestone 0b, 2026-10-15)
Supporting evidence for the result below: the divergence-baseline battle (154 units, 687 s, 0 shots refused) ran with AP
Configs *and* rbvfxpart2 registered and no overhaul `common_res_mod` yet. AP's table has no `weapons`/`shells` nodes,
so the table in use was Toni's (or vanilla): AP Configs, although *above* rbvfxpart2 in the registry, did not win.

To tell "first in `paths.cfgpack` wins" from "flag 1 beats flag 0", a throwaway add-on `mfo_coltest` (id `gtmfct`,
version 1, eng_ver 1536 like the overhaul, `_work\coltest\mfo_coltest_1.gt3ext`) ships the same `01_loc_kit_units`
text entry as `mfo_overhaul`, with `rkka_squad_inf_43a` named **"MFX Riflemen (e.1943)"** instead of the overhaul's
**"MFO Riflemen (e.1943)"** (same length). Both are registered at the next game start (`new_updates\` holds
`mfo_overhaul_0.2.5` and `mfo_coltest_1`). Read the name in the quick-battle squad list, then `paths.cfgpack`:
"MFX" with coltest on top = position decides; "MFO" with coltest on top = something else (flag, id, install time).
Text and config entries go through the same pack system (`i_objman`), so the rule is taken to hold for both.
**Result (user, 2026-10-15, on 0.2.9):** the squad list showed **"MFX Riflemen (e.1943)"** with `paths.cfgpack` =
`mfo_coltest, mfo_overhaul, AP Configs, AP DataBase, rbvfxpart2, …` (both overhaul add-ons flag 1 at that moment; the
flag also flipped 1/0 between runs for the same add-ons, so it is updater state, not a type). **Rule: the first entry in
`paths.cfgpack` wins a same-name collision, and the updater puts the most recently installed add-on first.** This also
explains the earlier observation that AP Configs (above rbvfxpart2) did not win `common_res_mod`: it was installed
after rbvfxpart2 but *below* it in the registry only because the updater re-sorts on every (re)install, and the user's
baseline ran with the registry order of that day. Practical consequence: the overhaul stays on top only while it is the
last add-on installed; any later add-on install (or reinstall of another) shadows our entries. The build-time merge
(§5 item 5) remains the design answer; the README must tell players to install the overhaul last.

**Live test since 0.2.1 (2026-10-15):** the overhaul now ships `expl_smk_0` (quiet hiss; competes with RukiSoundMod Part 3 and vanilla) and `common_res_mod` (competes with RBVFX Part 2 and AP Configs). Ruki's own `expl_smk_0` is at −38 dBFS, so a loud hiss heard before 0.2.1 already meant Ruki's entry was not the one playing. If the smoke-grenade hiss is clearly quieter with 0.2.1 installed, mfo_overhaul (first in `paths.cfgpack`) wins over later entries. Record the result here.

**Result (user test, 2026-10-15):** both the smoke-grenade hiss and the artillery smoke-round burst were audibly quieter with 0.2.1. The hiss needs our `expl_smk_0` to beat RukiSoundMod Part 3 and vanilla; the burst change needs our `common_res_mod` to beat RBVFX Part 2 and AP Configs. So **mfo_overhaul's entries win over every other registered add-on** on this install. Consistent explanations: the first entry in `paths.cfgpack` wins, or the add-ons whose second column is 1 (mfo_overhaul and the DLCs) take priority over those with 0. Either way the overhaul is on top as long as the updater keeps registering it first; the build-time merge (§5 item 5) is still the right design because it does not depend on that.
Open: which of the two explanations holds, and whether AP Configs' `common_res_mod` still shadows RBVFX Part 2's when the overhaul does not ship one. Both only matter for players who install those add-ons without the overhaul.

## 5. Decisions
1. Drop `T-D-Battlefield-SFX-Mod`; it is RBVFX Part 1 under its old name.
2. RBVFX Part 1 + Part 2 → module **M8 VFX**, dependency until Toni's permission, then bundled.
3. Achtung Panzer DataBase → required external download, never bundled.
4. Achtung Panzer Configs → **not installed** alongside the overhaul. Replaced by module **M9**, our port of its bindings onto 6.00 tables. Needs night_postman's permission to publish.
5. Build assembles merged tables in a fixed order: vanilla → M8 configs → M9 delta → M1 → M2 → M3. One entry, one archive, no engine-side collision.
6. Before any of this ships: resolve the collision-winner question (§4) with one in-game test.

## 5.1 M9 as built (2026-10-15)
`tools\m9_extract.ps1` diffs each of night_postman's 12 relevant tables against the pristine 3598 table with
`gt3.ps1 diff`, keeps only the binding operations and re-applies them to vanilla (deltas in
`src\m9_ap_port\mfo_tabs_ap\<table>.config.loc_def.delta`, which is what the module ships since the build-time merge of
2026-10-15; the merged tables it checks go to `build\m9_merged\`; log in `src\m9_ap_port\extract_report.txt`):

| Table group | Kept | Dropped |
|---|---|---|
| `outfit_hum`, `_autumn`, `_winter` | +314 / +294 / +316 outfit structs (1 127 / 1 085 / 1 187 rows) | 21 / 20 / 0 vanilla outfits he deleted (`ra36_*`, `ija_*`, `rkka_mr_*`, `uk_radio`) |
| `ger_hum_base`, `_autumn`, `_winter` | +125 / +137 / +125 soldier structs, 6 / 12 / 5 re-bound fields on vanilla soldiers (skins, `ammo_pat`) | 5 / 15 / 7 deleted vanilla soldiers, 1 / 8 / 0 deleted fields, 12 junk comment rows (kind 7) |
| `rus_hum_base`, `_autumn`, `_winter` | +101 / +101 / +103 soldier structs | nothing: his tables are pure additions, the merged tables equal his (`azcf_check.py` identical) |
| `hum_params` | +3 `links_aut_*` nodes, 346 `links_*` rows, 4 changed | `speech_far/arab`, `links_sum_ija/ir/iq`, 11 removed link points |
| `div_units_ger` / `_ussr` → `units` | 110 / 77 vanilla units re-pointed at his soldier types, 152 / 107 new unit rows | 247 / 273 unit removals, every `squads`/`randoms`/`trophy`/`supports` change, 9 + 1 bindings whose soldier type does not exist in his own tables (`ger_jager _at` typo, `ger_pionier_*`, `ger_regimentkommandeur`, `ger_avia_spotter`) |
| textures | `trans_marks0_dift`, `trans_marks0_dift_wint` | |
| `common_res_mod`, `qbattle` | | everything |

Reference checks on the merged tables: 463 `i_human` unit rows resolve to a soldier struct in all three seasons; 1 104
`ammo_pat` references exist in vanilla `ammo_hum`; 1 089 `outfit_pat` references exist in the merged outfit tables,
except three autumn ones that are wrong in his files too (`scharfschutze_1_s`, `unter_scharfschutze_s`,
`scout_lieuten_s`; the summer and `_aut` variants exist). Left as is. Shipped in `mfo_overhaul_0.2.5` as
`mfo_tabs_ap.flatdata` (14 entries, 4.4 MB). Needs the DataBase add-on for the meshes and textures.

## 6. Open items
- [ ] Permission from Toni (RBVFX Part 1 + 2)
- [ ] Permission from night_postman (DataBase as dependency, Configs port)
- [x] Collision-winner test: mfo_overhaul wins over Ruki Part 3, vanilla, RBVFX Part 2 and AP Configs (user test 2026-10-15, §4); the rule is registry position, first entry wins, newest install on top (`mfo_coltest` test, §4.1).
- [x] M9 port: diff tool done (`gt3.ps1 diff/apply` round-trips all 14 of his tables and Toni's 3 identically, `docs/toolchain.md` 3.1); port done (§5.1); user confirmed 2026-10-15 on 0.2.9 that German and Soviet infantry wear the Achtung Panzer uniforms from the ported tables (AP Configs still registered but shadowed by the overhaul). AP Configs removed via the Version label the same day (folder and registry entry gone, DataBase kept); the user confirmed infantry still wear the AP uniforms afterwards and quick battle lists both sides' formations; with no registered add-on shipping `qbattle` any more (`docs/addon_matrix.txt`), that list is vanilla's 28 Soviet + 26 German.
- [x] Build-time merge stage (vanilla → m8 → m9 → m1 → m2 → m3 deltas) in `build.ps1` (2026-10-15, `docs/toolchain.md` 7): m8 ships Toni's three tables as `gt3.ps1 diff` deltas (`sfx` without his `expl_snds` rows), m9 its twelve deltas, m1 its sound-class delta on top of m8's; first delta build byte-identical to the last whole-table build
- [ ] Verify AP DataBase's 20 vanilla overrides and Kuli Kraut Fix's 21 do not fight M7
