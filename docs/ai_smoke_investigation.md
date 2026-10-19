# Hand smoke grenades: what decides a throw, and is any of it data? (2026-10-16)

Question from 0.4.16: a 10-man squad throws all its smoke grenades at once; the user wants vanilla counts but fewer
throws at a time. Is there a table value the engine's AI reads for this decision?

**Verdict: no. Only code constants.** Every number in the decision chain is an immediate or a float from the code
libraries' constant pools. The data tables enter only through (a) which shells count as smoke (`shells` c2 = `SMK`),
(b) how many each soldier carries (`ammo_hum`), and (c) the hand-grenade weapon row `GREN_TR` (range by posture,
reload). None of them sets a rate, a fraction of the squad, or a trigger threshold.

Build 3598, read-only disassembly of `adv_game.codelib` (squad/order layer) and `adv_physic.codelib` (soldier
simulation: `human`, `tactics`, `fireact`, `manhu`, the readers of `hum_params`, `ammo_hum`, `tac_plans`). Addresses
are image-relative at the default base 0x180000000. File offsets: `.text` = VA - 0x180000C00 in both libraries;
`.rdata` = VA - 0x180001200 (adv_game) and VA - 0x180001800 (adv_physic). SHA-256 of the files read:
adv_game `b8fc26e7…3e12c` (1 420 288 bytes), adv_physic `e57891ec…92d16` (931 328 bytes).

## 1. The decision chain

### 1.1 adv_game: order modifier → squad flag

The order record carries a modifier bit mask at `order+0x40`. When an order is applied to its squads
(`0x1800D4700`, reached from the per-tick order driver `0x1800D07F0` once the previous orders are done, and
immediately for a freshly created order from `0x1800D3910`), the bits are copied into squad byte flags at
`0x1800D5052..0x1800D50ED`: bit 0 → `squad+0x26B`, bit 1 → `+0x26A`, bit 2 → `+0x26C`, bit 3 → `+0x267`,
bit 4 → `+0x268`, bit 5 → `+0x269`, bit 6 → `+0x26D`, bit 8 → `+0x26F` (only for order kind 1), **bit 9 →
`+0x26E` = "lay smoke"**, bit 28 → `+0x272`, bit 29 → `+0x271`. Only order types 0 and 1 (the movement orders;
jump table at `0x1800D5328`) take this path. A new order resets the whole flag block (`0x180049816`: `+0x267..+0x26E`
cleared). This is the player's "smoke" order modifier (UI strings `in_pl_smk` / `in_sq_smk`; the squad panel greys the
item when the squad's smoke-shell count `squad+0x3B4` is 0, adv_interf `0x1800327B0`).

### 1.2 adv_game: the squad smoke routine `0x18004B560`

Called from the squad think `0x180049910`, which runs once per accumulated game second (`squad+0x220 >= 1.0`).

1. Returns at once unless `squad+0x26E` is set.
2. Counts the squad's strength (vtable `+0x178` of every live member) and the strength of members whose order-progress
   value `member+0x88` exceeds **0.95**. The ratio must reach a threshold or the routine returns and tries again next
   second: **0.75** if `+0x26C` is clear, **0.25** if `+0x267` is clear, **0.33** otherwise, **0.10** when the squad's
   movement kind `squad+0x1B0` is 2.
3. Clears `+0x26E` (the request is consumed; the body below runs once per application of the modifier).
4. If `+0x267` (modifier bit 3) is clear: "prepare" pass only. Every eligible member gets state 8 (vtable `+0x310`)
   facing the squad's movement direction; `+0x277 = 1`, `+0x278 = 1` (hold), `+0x1C8 = 0`. No smoke is thrown.
5. Otherwise the throw pass. Two variants:
   - **kind ≠ 2** (`0x18004B886..0x18004BA36`): for each eligible member (alive; same squad id; not in the mounted
     state, vtable `+0x230`; a human with a current target, vtable `+0x5B0`, is skipped) the member's order is pointed at
     the squad position, then **vehicles are flagged unconditionally** (vtable `+0xD8` true) and **humans with
     probability 0.20** (`rand < 0.2`, constant `0x180131A0C`, loaded at `0x18004B886`, compared at `0x18004BA1F`).
   - **kind = 2** (`0x18004BB09..0x18004BEB3`): the throw point is the member position plus
     `max(50 m, squad+0x244) * (rand+0.5)` along the move direction, rotated by `rand * 22.5°` alternately left and right
     (per list, 50 % chance); vehicles always, **humans with probability 0.10** (`xmm11`, constant `0x1801319DC`,
     loaded at `0x18004B64C`, compared at `0x18004BE68`).
   - Flagging = call of the unit's vtable slot `+0x590` with `dl = 1` (`0x18004BA30`, `0x18004BE7A`). These two calls
     are the only places in adv_game that give a unit the smoke order.
6. After the pass: `+0x272 = 1`, `+0x267 = 0`, squad position recentred on the flagged members, timers
   `+0x22C`/`+0x230` multiplied by 0.25.

The per-soldier smoke count is never consulted here. Nothing in the routine reads a table.

### 1.3 adv_physic: the soldier

Slot `+0x590` on a human (vtables `0x1800C6518` / `0x1800C70A8`) is `0x180061BF0`: `human+0x752 = dl`. On a vehicle
(vtable `0x1800C7790`) it is `0x180031500`: sets `+0x752` on every crew member that is alive and not flagged out.
Readers:

- **Fire update `0x18004A720`** (called from the per-human tick `0x1800489B0` → `0x1800497D0`). The fire-interval
  timer `human+0x2154` is skipped when `+0x752` is set (`0x18004A9BC`). A "forced" flag is set when `+0x752` or
  `+0x751` is set (`0x18004AA83`–`0x18004AAB3`). Forced ⇒ ammo mode 1 (`r12d = 1`, `0x18004AF4C`, kept at
  `0x18004B1B1`), and mode 1 accepts **only shells whose `shells` c2 is `SMK`** (`0x18004B375: cmp eax,'SMK'`; mode 2
  = FRAG/HE/SH, mode 0 = any). The throw point is the soldier's position plus **50 m** along his velocity if he moves
  faster than 0.01 m/s (`0x18004AE4C`, constant `0x1800C8E40`), else a point from the squad object. For a smoke
  shell the hit-probability check is floored to 2.0 when below 0.1 (`0x180049F3B`), so range is the only limit
  (`shells` c4 = 35;30;25;20 m by posture for RDG/ND_39/No. 79).
- **Moving-fire routine `0x180054C40` → `0x180070E90`**: smoke mode (`human+0x1E28 = 1`, `0x180071555`) when
  `+0x752` is set, or when a second soldier-level condition holds (`+0x751`, or a target-type flag `+0x230E` read
  through vtable `+0x790`, and not under heavy fire: `+0x1F14 > 3`, or `> 1` with `+0x2084 > 10`).
- **After the shot** (`0x180067CE0`, the spawn through `i_shellphys` slot `+0x18`): if the shell fired has type `SMK`,
  `+0x752` is cleared (`0x180068309`/`0x180068313`; same for vehicles at `0x1800AC7C5`/`0x1800AC7CF`). **One
  grenade per flagging.** A flagged soldier who has no smoke shell left keeps the flag until the squad flags again.

Soldier-initiated smoke (no order):

- `+0x751` is set in the target-evaluation code (`0x18002B97A`) when the chosen target has flag bit 12 (armoured
  vehicle) within `max(20 m, target size)` and `human+0x1268 < 20` (constant 20 m at `0x1800C8570`), and in
  `0x18006C903` from an accumulated stress value (`(+0x1FEC + +0x1F10) * dt` summed in `+0x21B4`, thresholds 0.8 /
  1.1). That is the "infantry smokes an approaching tank" behaviour.
- A third trigger (`0x18004AA95`: incoming-fire pressure `+0x1F14 > 0.5·K` **and** stress `+0x1FEC > 3·K`, with
  `K = human+0x1D40 = 0.85 + 0.3·rand`) is dead code: `+0x1FEC` is clamped to ≤ 1 at `0x180049112`, 3·K ≥ 2.55. Both
  thresholds are function-local statics initialised from the first soldier processed.

### 1.4 What is read from data in this chain

| table / node / column | use | lever? |
|---|---|---|
| `common_res_mod.shells` c2 (`SMK`) | which shells the smoke mode may pick; `SMK` also sets shell flag bit 31 (no damage) at load (`adv_game 0x18006C021`) | yes, but only "is / is not smoke" |
| `common_res_mod.shells` c4 (35;30;25;20) | throw range by posture | yes (range) |
| `common_res_mod.weapons` `GREN_TR` c13/c14 (6 s, 5;0.5;7) | grenade reload / aim timing shared with HE grenades | shared with HE |
| `ammo_hum` per class | how many smoke grenades a soldier carries | yes (0.4.15 tried it) |
| `hum_params`, `tac_plans`, `ai_plans`, `base_params` | postures, speeds, operational AI | **not** read by any routine above |

No table holds a per-pass fraction, a throw interval for smoke, or a trigger threshold. The squad object's smoke
count (`+0x3B4`, summed in `adv_game 0x18003E520` from the shells of type `SMK` carried by the squad) is used only to
enable the UI button.

## 2. Why "all at once"

Per pass only 20 % (kind ≠ 2) or 10 % (kind 2) of the eligible soldiers are flagged, so a single pass over 10 men
gives ~2 (or 1) throws, which is what the user asked for. The observed "everyone throws" therefore comes from the
pass being repeated: the body runs again whenever `+0x26E` is set again, i.e. whenever a movement order with the
smoke modifier is (re)applied to the squad, and on every pass another 20 % are flagged. I did not finish tracing the
re-application sequence (the hold handler `0x18004BF50` / `0x18004C590`, the kind-2 continuation `0x1800D1160`, and
the platoon AI's own order issue). Vehicles (and their crews, through `0x180031500`) are flagged on every pass without
any probability, so a tank-riding or mechanised squad smokes with all crews at once by design.

## 3. If a binary patch were considered

Both libraries are in MiusPlayer's integrity list (`mpmod1\game_build_3598.sha256` covers all 18 `bin\rel\x64`
codelibs, `starter_x64.exe` and `programs.flatdata`), so a patched `adv_game.codelib` fails the hash check on both
PCs unless both players patch identically and the check is ignored; Steam's file verification and any game update
revert it; the MF Overhaul's `.gt3ext` cannot carry it (data archives only, `ships_codelib=no` in `manifest.txt`).
Not recommended. For the record, the smallest edits that change the behaviour:

| patch | VA | file offset (adv_game) | bytes now | change | effect |
|---|---|---|---|---|---|
| P1 fraction per pass, kind ≠ 2 | `0x18004B886` `movss xmm7,[rip+0xE617E]` | `0x4AC86` (disp at `0x4AC8A`) | `f3 0f 10 3d 7e 61 0e 00` | disp `4e 61 0e 00` → 0.1 (`0x1801319DC`); `2e 61 0e 00` → 0.05 (`0x1801319BC`); `02 61 0e 00` → 0.02 (`0x180131990`) | fewer soldiers flagged per pass; constants are shared pool entries, so only the displacement is changed, never the constant |
| P2 fraction per pass, kind 2 | `0x18004B64C` `movss xmm11,[rip+0xE6387]` | `0x4AA4C` (disp at `0x4AA51`) | `f3 44 0f 10 1d 87 63 0e 00` | disp `67 63 0e 00` → 0.05 | also lowers a 0.1 m distance epsilon in the same routine (harmless) |
| P3 no human smoke on order, kind ≠ 2 | `0x18004BA22` `jae +0x12` | `0x4AE22` | `73 12` | `eb 12` | vehicles only |
| P3b same, kind 2 | `0x18004BE6C` `jae +0x12` | `0x4B26C` | `73 12` | `eb 12` | vehicles only |

adv_physic candidates (same caveats): the 50 m throw-ahead vector `0x1800C8E40` is a four-lane constant shared with
other code; the one-grenade-per-flag clear at `0x180068309` (`75 0e`) must stay as is, it is what limits each soldier
to one throw. There is no single byte that implements "throw one grenade every N seconds per squad"; that would need
new code in the squad routine (a timer on the squad object before the throw pass) and is beyond a byte patch.

## 4. Open items

- Finish the re-application trace (section 2) if the exact rhythm matters: `0x18004BF50`, `0x18004C590`,
  `0x1800D1160`, and where the platoon AI (`aicolonel`, adv_game) issues orders with modifier bit 9.
- `warn_smk` ("Smoke screen is being setup") is in the event-name table at `0x18012E560` (index 3); the emitter was not
  located.
- Member record field `+0x88` (the 0.95 "progress" gate) was inferred from use, not from its writer.

## 5. Method and leftovers

capstone 5.0.9 from the earlier VFX session would not load from the long scratchpad path (WinError 206); it was copied
to `C:\Users\konid\AppData\Local\Temp\gtcs\` together with `fulldis.py`, and `adv_physic`, `basic_game` and
`adv_interf` were disassembled into this session's scratchpad (`*_dis.txt`, 7–13 MB each; `adv_game_dis.txt` is the
VFX session's). Helper scripts there: `locate.py` (strings and 4-char tag immediates), `refs.py` (pointer references),
`ctx.py`/`callers.py` (context and callers in a listing), `vtslot.py`/`vtfunc.py` (MSVC vtable slot ↔ function),
`bytes.py` (file offsets and constant-pool search), `jt.py` (jump tables). The 4-char tags are compared as little-endian
immediates: `SMK` = `0x4B4D53`, `FRAG` = `0x47415246`, `GREN` = `0x4E455247`. Nothing in the game folder or the repo
was modified by this investigation.
