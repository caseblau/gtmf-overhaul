# MiusPlayer compatibility

MiusPlayer (https://github.com/VampyrCat/MiusPlayer) is the multiplayer transport. MF Overhaul is content only. The two never touch the same files.

## Install order (both verified 2026-10-15 on build 3598, mpmod1 network version 12)
Either order works. Results are recorded in `manifest.txt` (`install_orders_tested`).
1. Install MF Overhaul (`.gt3ext` into `new_updates\`, start the game once so the updater installs it; or double-click it).
2. Copy `mpmod1` into the game folder (next to `starter_x64.exe`), close the game, run `mpmod1\Enable_Multiplayer.bat`.
3. Start the game through Steam. Both players must show the same `[MFO x.y]` tag on their Duel pools in the lobby.

What was tested:
- **MiusPlayer first, overhaul second:** mpmod1 enabled, then `mfo_overhaul_0.2.0.gt3ext` installed by the game's updater. Hash check: 20/20 vanilla files match, MiusPlayer's five files present and identical to `mpmod1\files`, add-on registered in `paths.cfgpack`.
- **Overhaul first, MiusPlayer second:** `Disable_Multiplayer.bat /quiet` (20/20 match, five files gone, add-on and its registration untouched), then `Enable_Multiplayer.bat /quiet` (20/20 match, five files back, add-on untouched).
- MiusPlayer's scripts never look at `data\`, `new_updates\` or `paths.cfgpack`, and our build never writes outside `data\common\mfo_overhaul\`.

Hash check used (run from the game root):
```powershell
foreach ($l in Get-Content mpmod1\game_build_3598.sha256) { if ($l -match '^(\w{64})\s+(.+)$') { $h=(Get-FileHash $Matches[2] -Algorithm SHA256).Hash; "$($h -eq $Matches[1].ToUpper())  $($Matches[2])" } }
```
`mpmod1\game_build_3598.sha256` carries full relative paths; the repo's `_mp_research/vanilla_hashes.sha256` has the same 20 hashes with bare file names.

## Both PCs must match
MiusPlayer simulates the whole battle on each PC and decides each unit's damage on its owner's PC.
If your data differs from the other player's, the game does not warn you. The battles will simply differ.
Same game build (6.00 / 3598), same MiusPlayer network version, same MF Overhaul version, same optional packs.

**How to check before a match (MiusPlayer has no check of its own, see `docs/upstream_requests.md`):**
1. Quick: both players open the Version menu and compare the overhaul's name, e.g. `MF Overhaul 0.3.6 [A1B2C3]`. The bracketed code is a
   fingerprint of every shipped entry, written at build time; same code = same overhaul data.
2. Thorough: both players run `tools\mp_fingerprint.ps1` and compare the `CODE` line. It covers the game build, MiusPlayer's files and
   every registered add-on (version + archive hashes). On a mismatch, `-Detail` names the add-on that differs.

## Files MF Overhaul never ships (MiusPlayer owns them)
```
root\programs\opgame.progpack
root\programs\tacgame.progpack
bin\rel\x64\basic_network.codelib
steam_appid.txt
mp_join.exe
mpmod1\**
users\mp_saves\**
```
`tools\check_conflicts.ps1` refuses to build if a staged file has one of these names.

## What the netcode does not carry (as of network version 12)
| Gap | Duel rule |
|---|---|
| Mines and ammunition explosions | banned in Duel pools |
| Off-map artillery called by the joiner | off-map artillery removed from Duel pools |
| Flares (untested) | none in Duel pools |
| Deployment-dug trenches at different positions | allowed, flagged as visual-only |
| Craters, smoke, building damage, battle statistics | local; expect small differences |
| Operation battles: position only, losses diverge | MP operations are experimental; use play-by-save for full operations |
| Two players max, no hot-seat | hot-seat doc covers one-PC play |

## Divergence test (per Duel pair)
Two copies on one PC, as MiusPlayer's README describes for testing. Set `MP_BG_FPS=30` for the background copy.
Host picks the pair, joiner connects to `127.0.0.1`, play 10 minutes, end the battle on both.
Run MiusPlayer's `_mp_research/tools/compare_units.py` and `combat_diff.py` on both end states.
Measure a vanilla pool first for the baseline tolerance. A Duel pair that diverges more than vanilla is reworked.

### Vanilla baseline (measured 2026-10-15, build 3598, mpmod1 network version 12, overhaul test add-on installed)
Two copies on one PC, vanilla skirmish: host commanded the Soviets (50 units), joiner the Germans (104 units), 154 units in all.
Battle time 687 s (11.5 min). Raw evidence: `docs\baseline_2026-10-15\` (MiusPlayer's own dumps, traces and logs, plus `mp_compare_report.txt`).

| Measure | Host (pid 23136) | Joiner (pid 7944) | Tolerance to adopt |
|---|---|---|---|
| Units in both games (every second of 690 traced) | 154 | 154 | unit counts must be equal every second |
| Object states received: rejected / "not loaded (render handles differ)" | 0 / 0 of 168 112 loaded | 0 / 0 of 81 947 loaded | 0 / 0 |
| Shots: refused (ammunition or unit not matched) | 0 of 1 841 received | 0 of 653 received | 0 |
| Shots sent vs received by the other side | 652 sent → 653 received | 1 913 sent → 1 841 received (rest in flight at end) | within ~5 % |
| Clock drift between games (max / average) | 0.20 s / 0.08 s | 0.10 s / 0.03 s | ≤ 0.5 s |
| Position gap at 20 s battle time (154 units compared) | largest 0.19 m, none over 5 m | same dump pair | no unit over 5 m at the fixed dump moments |
| Per-second position hash identical | never (0 of 690) | | expected: remote units are drawn 0.1 s behind, so hashes always differ; use the counts above, not the hash |
| Wire rate received by host | max 144 KB/s, avg 68 KB/s | | informational |
| Incidents | one "connection lost (nothing received for 8 s)" during loading at 12:05:11, recovered before the battle phase | none | none during the battle phase |

Kill totals are not in these files (MiusPlayer's end-of-battle statistics are local to each game, see the gap table); compare them by eye on the result screens.
A Duel pair passes when it shows the same zeros (rejected, not loaded, refused), equal unit counts every second, drift ≤ 0.5 s and no unit beyond 5 m at the dump moments.

How to run it:
```powershell
# from the game root, MiusPlayer enabled, no game running; clears old evidence, launches two copies
Get-ChildItem out -Include mp_units_*.txt,mp_trace_*.txt,basic_network_*.log -Recurse | Remove-Item
$env:MP_DUMP='1'; $env:MP_DEBUG='1'; $env:MP_BG_FPS='30'
Start-Process .\starter_x64.exe; Start-Sleep 15; Start-Process .\starter_x64.exe
# copy 1: MULTIPLAYER -> HOST A SKIRMISH -> SET UP THE BATTLE (pick the pool pair); copy 2: JOIN A GAME -> 127.0.0.1 -> CONNECT -> READY
# both press Start twice; play 10 min; end on both; then:
tools\mp_compare.ps1 -GameRoot .
```
Do **not** set `MP_WINDOW` (it moves the fullscreen window and the mouse stops working). Alt+Tab between the two copies.
`tools\mp_compare.ps1` reads only the files MiusPlayer writes; MiusPlayer's `combat_diff.py` (reads live process memory, and its
hard-coded object-manager address 0x7FDEF0 is stale: this build logs `objman=0x7FDF20`) is not needed.

## Reporting
Netcode gaps go to the MiusPlayer issue tracker, not into data workarounds.
