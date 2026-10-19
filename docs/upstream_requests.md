# Upstream requests

## MiusPlayer: live data-mismatch check in the lobby

Where to post: https://github.com/VampyrCat/MiusPlayer/issues (or the thread where the release was announced).
Status: draft, not yet posted.

> **Feature request: detect mismatched game data between host and joiner**
>
> Because each PC simulates the whole battle with its own data, two players whose data differs (a different mod version, one add-on
> missing, a different dependency) get silently different battles: damage is decided on the owner's PC with the owner's shells and
> weapons tables. Nothing warns them. With data overhauls appearing for Mius-Front this will be the most common cause of "the game
> desynced" reports, and it is cheap to detect.
>
> Proposed behaviour:
> 1. On connect, each side builds a data fingerprint: for every add-on registered in `data\common\shared\config\paths.cfgpack`, in
>    order, the add-on folder name, the `version` from its `desc.addpack`, and the SHA-256 of each `shared\packed_data\*.flatdata`
>    file it holds; plus the SHA-256 of `starter_x64.exe` and of `basic_network.codelib`. Hash that list once (SHA-256, first 6–8 hex
>    digits are enough to display).
> 2. The joiner sends its fingerprint and the per-add-on list with the join request; the host compares.
> 3. The lobby shows `DATA MATCH <code>` in green, or `DATA MISMATCH` in red with the first differing add-on named
>    (`mfo_overhaul v305 differs`, `rbvfxpart2 missing on joiner`). READY could be blocked while mismatched, or just warned.
> 4. Optional: an env var `MP_DATA_CHECK=0` to skip it, for testing.
>
> Cost: one directory walk and a few megabytes hashed at connect time, a few hundred bytes on the wire, two lobby strings.
>
> Reference implementation of the fingerprint (PowerShell, reads the same files): `tools\mp_fingerprint.ps1` in the MF Overhaul
> repository; the overhaul also stamps its own build fingerprint into the add-on name shown in the Version menu.

Why this matters to us: the overhaul's multiplayer design (DESIGN.md 1.1) rests on identical data on both PCs, and today the only
protection is a version tag in names that players compare by eye.
