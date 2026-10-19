# Play-by-save operational campaign (two PCs, asynchronous)

## Why this still exists
MiusPlayer runs skirmishes and missions online, but its operation mode syncs units by position only and losses diverge between PCs.
Until that is fixed upstream, this is the honest way to play a full operation between two people. For single battles, use MiusPlayer.

## What it is
Two players run one operation. Each operational turn belongs to one player. They make their operational moves,
fight the tactical battles of that turn against the AI (which fields the opponent's forces exactly as the opponent left them),
and send the save to the other player. The other player does the same for their side.

## What it is not
It is not simultaneous multiplayer. In each tactical battle the AI plays the absent human's units.
The human opponent decides deployment, reserves, reinforcements and operational movement. State this plainly to anyone you invite.

## Flow
1. Host creates the operation, plays turn 1 as side A, zips the campaign save folder, sends it.
2. Guest unzips into their own save location, plays the turn as side B, zips, sends back.
3. Repeat until the operation ends. Final screens on both sides should match; if they do not, the last turn is replayed.

## Companion tool (`tools/pbs/`, planned)
Standalone console tool, no game hooks:
- `pbs init <save folder> <sideA> <sideB>` writes a `pbs.json` with the turn counter and both player names.
- `pbs seal` hashes the save folder, increments the turn, zips it as `turn_<n>_<side>.zip`.
- `pbs open <zip>` checks the hash chain and that the turn number is the expected next one before unpacking. Refuses otherwise.
- Hash chain is the anti-tamper measure. It is honour-system against a determined cheat, which is fine for two friends.

The tool owns "whose turn is it" and "which state is authoritative". A future real multiplayer transport could replace the zip exchange with a direct connection and reuse that logic.

## Save folder location (verified 2026-10-15, build 3598)
`<game root>\users\profiles\<profile id>\`. The current profile is named in `users\profiles\cur_profile.engcfg`
(`cur_profile = <name>; cur_id = <id>;`); on the build machine the profile "xyz" has id `cloud`, so saves are in
`users\profiles\cloud\`. One operation save is a pair of files:
- `<campaign>_<op>_<side>.opsave` and a `.opsave_` backup of the previous state, e.g. `1943_07_Mius_07_17_Stepanovka_ger.opsave` (5–13 MB each);
- `<same prefix>_<cell>_<map>.polypack2.damsav2` per battle cell with terrain damage (0.5 KB–1 MB each).
MiusPlayer additionally copies operation saves to `users\mp_saves\<host>_vs_<player>\` and keeps replaced ones in `users\mp_saves\_replaced`.
The play-by-save tool should seal the `.opsave` plus all `.damsav2` files sharing its prefix; the `.opsave_` backup is not needed.
