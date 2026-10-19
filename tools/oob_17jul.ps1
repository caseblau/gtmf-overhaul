<#
.SYNOPSIS
  MF Overhaul M2: bring the OOB of "Stepanovka-Marinovka, 17 July 1943" (operation files 07_17_Stepanovka_NA_RUS /
  _GER, the ones the game plays) up to the standard of "Stepanovka, 30 July 1943" (07_30_Stepanovka_RUS).

.DESCRIPTION
  Four passes over each side's desc table (docs\oob_stepanowka_17jul.md has the rules in full):
  1. Formations. The 30 July platoon set of a counterpart (or structural twin) formation is merged into the 17 July one:
     same code + same role = composition and support fields from 30 July (node name, uid, text key, params, mobility kept);
     unmatched 30 July platoons are added as reserves; vehicles only where the company has none; HQs, battle groups and
     reserve squad pools untouched. Artillery regiments that the 17 July file lacks (1012, 84, 90, 234 Gds AR; 294, 146,
     128 AR; 306/302 AR cloned from 294 AR) are created as formations under their division with HQ, FO teams and batteries,
     and the division batteries the 17 July file attached to rifle regiments are moved into them.
  2. Tank/SPG companies modelled as one platoon (company command tank + 2-3 sections in one pool) are split into a
     company command node and one node per section, as the 30 July file does; the original node keeps its name (battle
     groups reference it) and becomes the 1st platoon.
  3. Battle groups: a SCT slot is added where missing; following the 30 July pattern the first battle group of a rifle
     regiment gets the FO team of a division artillery battery, the next one the regiment's own FO or recon platoon,
     armour battle groups a recon platoon or nothing; a battle group holding a split tank company gets a third STR slot
     so the company's platoons stay together; empty STR/UNI/SUP slots are filled with unused platoons of the same battalion.
  4. Text: name keys that exist only in the 30 July text are copied into the 17 July packs (loc_eng, loc_rus), unit numbers
     substituted for cloned formations.

  Output (both sides): src\m2_oob\camps\1943_07_Mius\07_17_Stepanovka_NA_<SIDE>\ desc.config.loc_def.01_oob.delta,
  text.text.loc_eng.bin, text.text.loc_rus.bin, !flatlist; and docs\oob_stepanowka_17jul_changes.md.

.EXAMPLE
  tools\oob_17jul.ps1 -Verbose2        # needs GTMF_ROOT; ~5 min for both sides
#>
param(
    [string]$GameRoot = $env:GTMF_ROOT,
    [string]$Work = '',
    [string[]]$Sides = @('RUS', 'GER'),
    [switch]$Verbose2     # one summary line per mapping
)
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'gt3.ps1') lib
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
if (-not $GameRoot) { throw 'set GTMF_ROOT or pass -GameRoot (folder with starter_x64.exe)' }
if (-not $Work) { $Work = Join-Path $repo 'build\oob17' }
$campDir = Join-Path $GameRoot 'data\oprum\shared\camps\1943_07_Mius'
$ops = @{ RUS = '07_17_Stepanovka_NA_RUS'; GER = '07_17_Stepanovka_NA_GER' }
$tplOp = '07_30_Stepanovka_RUS'
$outRoot = Join-Path $repo 'src\m2_oob\camps\1943_07_Mius'
$globalText = Join-Path $GameRoot 'users\modwork\_orig\3598\text_loc'

# ---------------------------------------------------------------- helpers on the gt3 document model
function Unpack-Op([string]$op) {
    $dir = Join-Path $Work "vanilla\$op"
    if (-not (Test-Path (Join-Path $dir 'desc.config.loc_def.bin'))) {
        New-Item -ItemType Directory -Force $dir | Out-Null
        Cmd-Unpack (Join-Path $campDir "$op.campack2") $dir | Out-Null
    }
    $dir
}
function Fld([object]$node, [string]$name) { foreach ($r in $node.rows) { if ($r.name -eq $name) { return $r } }; $null }
function FV([object]$node, [string]$name) { $r = Fld $node $name; if ($r) { Cell-Encode $r.c[0] } else { '' } }
function FS([object]$node, [string]$name) { $r = Fld $node $name; if ($r -and $r.c[0].k -eq 2) { $r.c[0].s } else { '' } }
function FU([object]$node, [string]$name) { $r = Fld $node $name; if ($r) { [uint32]$r.c[0].v[0] } else { 0 } }
function SetF([object]$node, [string]$name, [string]$text) { $r = Fld $node $name; if (-not $r) { throw "no field $name in $($node.name)" }; $r.c[0] = Cell-Decode $text }
function Fcc([object]$node, [string]$name) { $v = FV $node $name; if ($v -match "^u:'(.+)'$") { $Matches[1] } else { $v -replace '^u:', '' } }
function Fcc-Row([object]$row) { $v = Cell-Encode $row.c[1]; if ($v -match "^u:'(.+)'$") { $Matches[1] } else { $v -replace '^u:', '' } }   # slot role of a 'slots' row
function Clone-Cell([hashtable]$c) { @{ k = $c.k; v = [uint32[]]$c.v.Clone(); s = $c.s } }
function Clone-Node([object]$n) {
    $cl = Azcf-NewNode $n.name $n.type $n.cols $n.types
    foreach ($r in $n.rows) { $cl.rows.Add(@{ name = $r.name; c = @($r.c | ForEach-Object { Clone-Cell $_ }) }) }
    foreach ($k in $n.kids) { $cl.kids.Add((Clone-Node $k)) }
    $cl
}
function Kid([object]$n, [string]$name) { foreach ($k in $n.kids) { if ($k.name -eq $name) { return $k } }; $null }
function Code([object]$p) { [int](FU $p 'code') }
function Real([object]$p) { Fcc $p 'real_type' }
function Spr([object]$p) { FS $p 'str_sprite' }
function Pool([object]$p) { FS $p 'pool' }
function IsBg([object]$p) { (FU $p 'bg') -ne 0 }
function SpriteClass([string]$s) {
    if ($s -match '^plu_(field_com|batcmd|commander|tankbncmd|tankcmd|rgt|div|bde|corp|bn|camp)') { return 'cmd' }
    if ($s -match '^plu_(rifles|smg|fthrow)$') { return 'inf' }
    if ($s -eq 'plu_saps') { return 'sap' }
    if ($s -match '^plu_(scouts|patrol|cavalary)$') { return 'sct' }
    if ($s -eq 'plu_fo') { return 'fo' }
    if ($s -eq 'plu_mortars') { return 'mort' }
    if ($s -match '^pl_(maxim|mg42)$') { return 'mg' }
    if ($s -eq 'plu_atrs') { return 'atr' }
    $s
}
function IsVehicle([object]$p) {
    $r = Real $p; $s = Spr $p
    if ($r -eq 'STR' -or $r -eq 'SUPM') { return $true }
    if ($s -match '^pl_(t34|t70|t60|kv|su|pz|stug|marder|sdkfz|ba64|wscout|stuig|m3|t30)') { return $true }
    $false
}
function PoolSummary([object]$p) {
    $pool = Kid $p 'pool'; if (-not $pool) { return '' }
    ($pool.rows | ForEach-Object { $q = Cell-Encode $_.c[1]; ($_.c[0].s) + ' x' + ($q -replace '^a:', '') + $(if ($_.c[4].s) { '(' + $_.c[4].s + ')' } else { '' }) }) -join ', '
}
function New-PoolRow([string]$squad, [string]$qty, [object]$like) {
    # a 5-column pool row (savvs): squad id, quantity (a), two v cells copied from $like, support id
    @{ name = $null; c = @((Cell-Decode "s:$squad"), (Cell-Decode "a:$qty"), (Clone-Cell $like.c[2]), (Clone-Cell $like.c[3]), (Cell-Decode 's:')) }
}

# ---------------------------------------------------------------- AZTX text packs (read / write)
function Read-Text([string]$path) { Read-Aztx ([IO.File]::ReadAllBytes($path)) }
function Write-Aztx([string]$path, [string]$loc, [object[]]$keys) {
    # Layout as in the vanilla packs: header 0x50; bucket table (N = pow2 >= 3*keys) of {0x80000000|home, record
    # offset}; key records 0x30 {char[0x20] key, u32 items, u32 items offset, u32 home, u32 0}; item records 0x10
    # {u32 len, u32 string offset, u64 0} contiguous in key order; strings NUL-terminated cp1251 in item order.
    $enc = [Text.Encoding]::GetEncoding(1251)
    $n = $keys.Count
    $nb = Azcf-Buckets $n 1; if ($nb -lt 16) { $nb = 16 }
    $kr = 0x50 + $nb * 8
    $items = $kr + $n * 0x30
    $nItems = 0; foreach ($k in $keys) { $nItems += $k.items.Count }
    $strOff = $items + $nItems * 0x10
    $strBytes = New-Object Collections.Generic.List[byte]
    $itemRecs = New-Object Collections.Generic.List[byte]
    $keyRecs = New-Object Collections.Generic.List[byte]
    $ip = $items
    foreach ($k in $keys) {
        $kb = New-Object byte[] 0x20; [Text.Encoding]::ASCII.GetBytes($k.key).CopyTo($kb, 0)
        $keyRecs.AddRange($kb)
        $keyRecs.AddRange([BitConverter]::GetBytes([uint32]$k.items.Count))
        $keyRecs.AddRange([BitConverter]::GetBytes([uint32]$ip))
        $keyRecs.AddRange([BitConverter]::GetBytes([uint32](Azcf-Hash $k.key $nb)))
        $keyRecs.AddRange([BitConverter]::GetBytes([uint32]0))
        foreach ($s in $k.items) {
            $sb = $enc.GetBytes([string]$s)
            $itemRecs.AddRange([BitConverter]::GetBytes([uint32]$sb.Length))
            $itemRecs.AddRange([BitConverter]::GetBytes([uint32]($strOff + $strBytes.Count)))
            $itemRecs.AddRange([BitConverter]::GetBytes([uint64]0))
            $strBytes.AddRange($sb); $strBytes.Add(0)
            $ip += 0x10
        }
    }
    $slots = New-Object uint32[] ($nb * 2)
    for ($i = 0; $i -lt $n; $i++) {
        $h = Azcf-Hash $keys[$i].key $nb; $s = $h
        for ($t = 0; $t -lt $nb; $t++) { if (($slots[$s * 2] -band 0x80000000) -eq 0) { break }; $s = ($s + 1) % $nb }
        $slots[$s * 2] = 0x80000000 -bor $h; $slots[$s * 2 + 1] = [uint32]($kr + $i * 0x30)
    }
    $out = New-Object Collections.Generic.List[byte]
    $hdr = New-Object byte[] 0x50
    [Text.Encoding]::ASCII.GetBytes('AZTX').CopyTo($hdr, 0)
    [BitConverter]::GetBytes([uint32]1).CopyTo($hdr, 4); [BitConverter]::GetBytes([uint32]0x20).CopyTo($hdr, 8); [BitConverter]::GetBytes([uint32]0x20).CopyTo($hdr, 0x10)
    [Text.Encoding]::ASCII.GetBytes($loc).CopyTo($hdr, 0x20)
    [BitConverter]::GetBytes([uint32]$n).CopyTo($hdr, 0x40); [BitConverter]::GetBytes([uint32]$kr).CopyTo($hdr, 0x44)
    [BitConverter]::GetBytes([uint32]$nb).CopyTo($hdr, 0x48); [BitConverter]::GetBytes([uint32]0x50).CopyTo($hdr, 0x4c)
    $out.AddRange($hdr)
    foreach ($w in $slots) { $out.AddRange([BitConverter]::GetBytes([uint32]$w)) }
    $out.AddRange($keyRecs); $out.AddRange($itemRecs); $out.AddRange($strBytes)
    [IO.File]::WriteAllBytes($path, $out.ToArray())
}

# ---------------------------------------------------------------- the mapping table
# form: 17 July formation (p_*); tpl: regex on 30 July platoon names; tplPrefix: regex replaced by naPrefix to name
# added nodes; shift: added to the 30 July code (keeps division troops out of the regiment's code space);
# exclude: regex on 30 July names to leave out; overrideUNI: matched rifle platoons take the 30 July composition;
# params: params of added platoons (17 July strength); keySub: text substitutions for cloned units;
# create: @{ parent; after; code; ext; move = regex of 17 July platoons re-pooled into the new formation } makes the
# formation (struct cloned from the parent division) when the 17 July file lacks it; its 30 July HQ (code 0) is added too.
$M = @()
function Map($form, $tpl, $tplPrefix, $naPrefix, $shift, $exclude, $overrideUNI, $params, $keySub, $note, $create = $null) {
    $script:M += [pscustomobject]@{ form = $form; tpl = $tpl; tplPrefix = $tplPrefix; naPrefix = $naPrefix; shift = $shift; exclude = $exclude; overrideUNI = $overrideUNI; params = $params; keySub = $keySub; note = $note; create = $create }
}
$pSov = 'v:0.5;0.5;1;0.1'       # fresh formations on the first day of the offensive (30 July: 0.3-0.5 fill after two weeks)
$pSovMech = 'v:0.5;0.6;1;0.1'
$pGerID = 'v:0.5;0.5;0.8;0.2'   # 294/306/302 ID: worn divisions holding a long front
$pGerMot = 'v:0.5;0.6;1;0.1'    # 16 PzGr, 23 PzD: refitted, arriving fresh
# --- 315 RD (362, 724, 1328 RR; 1012 AR; division troops 700 sap bn, 431 AT bn, recon)
Map 'p_ra_362rr'  '^ra_362_'  '^ra_362_'  'ra_362rr_'  0 $null $false $pSov $null '362 RR: 30 July 362 RR structure'
Map 'p_ra_362rr'  '^ra_315_(rcoy|rc_)' '^ra_315_' 'ra_362rr_' 0x800 $null $false $pSov $null '315 RD recon company -> 362 RR'
Map 'p_ra_362rr'  '^ra_315_atbn_(hq|1c_)' '^ra_315_' 'ra_362rr_' 0x800 $null $false $pSov $null '431 AT bn HQ + 1 battery -> 362 RR'
Map 'p_ra_724rr'  '^ra_724_'  '^ra_724_'  'ra_724rr_'  0 $null $false $pSov $null '724 RR: 30 July 724 RR structure'
Map 'p_ra_724rr'  '^ra_315_sbn_(hq|1c_)' '^ra_315_' 'ra_724rr_' 0x800 $null $false $pSov $null '700 sap bn HQ + 1 coy -> 724 RR'
Map 'p_ra_724rr'  '^ra_315_atbn_2c_' '^ra_315_' 'ra_724rr_' 0x800 $null $false $pSov $null '431 AT bn 2 battery -> 724 RR'
Map 'p_ra_1328rr' '^ra_1328_' '^ra_1328_' 'ra_1328rr_' 0 $null $false $pSov $null '1328 RR: 30 July 1328 RR structure'
Map 'p_ra_1328rr' '^ra_315_sbn_2c_' '^ra_315_' 'ra_1328rr_' 0x800 $null $false $pSov $null '700 sap bn 2 coy -> 1328 RR'
Map 'p_ra_1328rr' '^ra_315_atbn_(3c_|atrc)' '^ra_315_' 'ra_1328rr_' 0x800 $null $false $pSov $null '431 AT bn 3 battery + ATR coy -> 1328 RR'
Map 'p_ra_1012ar' '^ra_1012ar_' '^ra_1012ar_' 'ra_1012ar_' 0 $null $false $pSov $null '1012 AR: new formation under 315 RD (30 July 1012 AR: HQ, FO teams, batteries) + the 17 July division batteries' @{ parent = 'p_ra_315rd'; after = 'p_ra_1328rr'; code = 18; ext = 1012; move = '^ra_315_[123]arty$' }
# --- 34 Gds RD (103, 105, 107 Gds RR; 84 Gds AR; 37 sap bn, 38 AT bn, recon)
Map 'p_ra_103rr'  '^ra_103_'  '^ra_103_'  'ra_103rr_'  0 $null $false $pSov $null '103 Gds RR: 30 July structure'
Map 'p_ra_103rr'  '^ra_34_(rcoy|rc_)' '^ra_34_' 'ra_103rr_' 0x800 $null $false $pSov $null '34 Gds RD recon company -> 103 RR'
Map 'p_ra_103rr'  '^ra_34_atbn_(hq|1c_)' '^ra_34_' 'ra_103rr_' 0x800 $null $false $pSov $null '38 AT bn HQ + 1 battery -> 103 RR'
Map 'p_ra_105rr'  '^ra_105_'  '^ra_105_'  'ra_105rr_'  0 $null $false $pSov $null '105 Gds RR: 30 July structure'
Map 'p_ra_105rr'  '^ra_34_sbn_(hq|1c_)' '^ra_34_' 'ra_105rr_' 0x800 $null $false $pSov $null '37 sap bn HQ + 1 coy -> 105 RR'
Map 'p_ra_105rr'  '^ra_34_atbn_2c_' '^ra_34_' 'ra_105rr_' 0x800 $null $false $pSov $null '38 AT bn 2 battery -> 105 RR'
Map 'p_ra_107rr'  '^ra_107_'  '^ra_107_'  'ra_107rr_'  0 $null $false $pSov $null '107 Gds RR: 30 July structure'
Map 'p_ra_107rr'  '^ra_34_sbn_2c_' '^ra_34_' 'ra_107rr_' 0x800 $null $false $pSov $null '37 sap bn 2 coy -> 107 RR'
Map 'p_ra_107rr'  '^ra_34_atbn_(3c_|atrc)' '^ra_34_' 'ra_107rr_' 0x800 $null $false $pSov $null '38 AT bn 3 battery + ATR coy -> 107 RR'
Map 'p_ra_84ar'   '^ra_84ar_' '^ra_84ar_' 'ra_84ar_'   0 $null $false $pSov $null '84 Gds AR: new formation under 34 Gds RD (30 July 84 AR) + the 17 July division batteries' @{ parent = 'p_ra_34rd'; after = 'p_ra_107rr'; code = 132; ext = 84; move = '^ra_34_[123]arty$' }
# --- 40 Gds RD (only 116 Gds RR on the map; 90 Gds AR; 42 sap bn, 41 AT bn, recon)
Map 'p_ra_116rr'  '^ra_111_'  '^ra_111_'  'ra_116rr_'  0 $null $false $pSov @{ '111' = '116' } '116 Gds RR: 30 July 111 Gds RR structure (116 RR has no platoons in the 30 July file)'
Map 'p_ra_116rr'  '^ra_40_(rcoy|rc_|sbn_hq|sbn_1c_|atbn_hq|atbn_1c_|atbn_atrc)' '^ra_40_' 'ra_116rr_' 0x800 $null $false $pSov $null '40 Gds RD recon, 42 sap bn 1 coy, 41 AT bn 1 battery + ATR coy -> 116 RR'
Map 'p_ra_90ar'   '^ra_90ar_' '^ra_90ar_' 'ra_90ar_'   0 $null $false $pSov $null '90 Gds AR: new formation under 40 Gds RD (30 July 90 AR) + the 17 July division batteries' @{ parent = 'p_ra_40rd'; after = 'p_ra_119rr'; code = 144; ext = 90; move = '^ra_40_[123]arty$' }
# --- 96 Gds RD (only 291 Gds RR on the map; 234 Gds AR; 111 sap bn, 102 AT bn, recon)
Map 'p_ra_291rr'  '^ra_291_'  '^ra_291_'  'ra_291rr_'  0 $null $false $pSov $null '291 Gds RR: 30 July structure'
Map 'p_ra_291rr'  '^ra_96_(rcoy|rc_|sbn_hq|sbn_1c_|atbn_hq|atbn_1c_|atbn_atrc)' '^ra_96_' 'ra_291rr_' 0x800 $null $false $pSov $null '96 Gds RD recon, 111 sap bn 1 coy, 102 AT bn 1 battery + ATR coy -> 291 RR'
Map 'p_ra_234ar'  '^ra_234ar_' '^ra_234ar_' 'ra_234ar_' 0 $null $false $pSov $null '234 Gds AR: new formation under 96 Gds RD (30 July 234 AR) + the 17 July division batteries' @{ parent = 'p_ra_96rd'; after = 'p_ra_295rr'; code = 52; ext = 234; move = '^ra_234_[123]arty$' }
# --- armour and mechanised
Map 'p_ra_32tbde' '^ra_32tbde_' '^ra_32tbde_' 'ra_32tbde_' 0 $null $true $pSovMech $null '32 Gds TBde: recon, sappers, AT battery, AA, MR bn structure, mortar coy'
Map 'p_ra_37tbde' '^ra_37tbde_' '^ra_37tbde_' 'ra_37tbde_' 0 '^ra_37tbde_aac' $true $pSovMech $null '37 Gds TBde: recon, sappers, AT battery, MR bn structure, mortar coy'
Map 'p_ra_22stp'  '^ra_22tr_'  '^ra_22tr_'  'ra_22stp_'  0 $null $true $pSovMech $null '22 Gds det TR: recon, sapper and SMG platoons'
Map 'p_ra_1543tsap' '^ra_1543(tsap|spgr)_' '^ra_1543(tsap|spgr)_' 'ra_1543tsap_' 0 '_res[12]$' $false $pSovMech $null '1543 SAP: regiment command group and SU-152 FO team'
Map 'p_ra_4mrbde' '^ra_13mbde_' '^ra_13mbde_' 'ra_4mr_' 0 $null $true $pSovMech $null '4 Gds MBde: 30 July mech brigade standard (13 Gds MBde)'
Map 'p_ra_5mrbde' '^ra_13mbde_' '^ra_13mbde_' 'ra_5mr_' 0 $null $true $pSovMech $null '5 Gds MBde: 30 July mech brigade standard (13 Gds MBde)'
Map 'p_ra_6mrbde' '^ra_13mbde_' '^ra_13mbde_' 'ra_6mr_' 0 $null $true $pSovMech $null '6 Gds MBde: 30 July mech brigade standard (13 Gds MBde)'
Map 'p_ra_8iptabr' '^ra_1destr_(smgc|engbn_hq|engbn_1c)' '^ra_1destr_' 'ra_8iptabr_' 0 $null $false $pSov $null '8 AT Bde: SMG company and sapper company (1 Gds AT Bde pattern)'
Map 'p_ra_15iptabr' '^ra_1destr_(smgc|engbn_hq|engbn_1c)' '^ra_1destr_' 'ra_15iptabr_' 0 $null $false $pSov $null '15 AT Bde: SMG company and sapper company (1 Gds AT Bde pattern)'
# --- 294 ID (513 IR on the map; 294 AR; 294 AT bn)
Map 'p_we_513ir'  '^we_513_'  '^we_513_'  'wer_513ir_' 0 '^we_513_(13c_com|leig1|leig2)$' $false $pGerID $null '513 IR: 30 July 513 IR structure (13th coy guns already in the 17 July supcoy)'
Map 'p_we_294id'  '^we_294at_' '^we_294at_' 'wer_294at_' 0x800 $null $false $pGerID $null '294 AT bn: recon coy + 3 AT companies'
Map 'p_we_294ar'  '^we_294ar_' '^we_294ar_' 'wer_294ar_' 0 $null $false $pGerID $null '294 AR: new formation under 294 ID (30 July 294 AR: HQ, FO teams, 3rd/4th/5th batteries) + the 17 July I/294 AR batteries' @{ parent = 'p_we_294id'; after = 'p_we_515ir'; code = 150; ext = 294; move = '^wer_294ar_1c_[23]b$' }
# --- 306 ID (581 IR) and 302 ID (572 IR, III bn only): 513 IR / 294 ID templates renamed
Map 'p_we_581ir'  '^we_513_'  '^we_513_'  'wer_581ir_' 0 '^we_513_14c_' $false $pGerID @{ '513' = '581'; '294' = '306' } '581 IR: 513 IR structure (14th coy already in the 17 July 14at)'
Map 'p_we_572ir'  '^we_513_(bicp|3b_|9c_|10c_|12c|13c_)' '^we_513_' 'wer_572ir_' 0 $null $false $pGerID @{ '513' = '572'; '294' = '302' } 'III/572 IR: battalion FO, 10th coy, 12th MG coy, 13th coy'
Map 'p_we_306id'  '^we_294at_' '^we_294at_' 'wer_306at_' 0x800 $null $false $pGerID @{ '294' = '306' } '306 AT bn (294 AT bn pattern)'
Map 'p_we_306ar'  '^we_294ar_' '^we_294ar_' 'wer_306ar_' 0 $null $false $pGerID @{ '294' = '306' } '306 AR: new formation under 306 ID (294 AR pattern)' @{ parent = 'p_we_306id'; after = 'p_we_581ir'; code = 151; ext = 306; move = $null; tplForm = 'p_we_294ar' }
Map 'p_we_302id'  '^we_294at_(hq|atc)' '^we_294at_' 'wer_302at_' 0x800 $null $false $pGerID @{ '294' = '302' } '302 AT bn companies (294 AT bn pattern; recon coy already present)'
Map 'p_we_302ar'  '^we_294ar_' '^we_294ar_' 'wer_302ar_' 0 $null $false $pGerID @{ '294' = '302' } '302 AR: new formation under 302 ID (294 AR pattern)' @{ parent = 'p_we_302id'; after = 'p_we_572ir'; code = 152; ext = 302; move = $null; tplForm = 'p_we_294ar' }
# --- 16 PzGr Div (60, 156 MIR; 146 AR)
Map 'p_we_60mir'  '^we_156_'  '^we_156_'  'wer_60mir_' 0 $null $true $pGerMot @{ '156' = '60' } '60 MIR: 30 July 156 MIR structure'
Map 'p_we_156mir' '^we_156_'  '^we_156_'  'wer_156mir_' 0 $null $true $pGerMot $null '156 MIR: 30 July 156 MIR structure'
Map 'p_we_146ar'  '^we_146ar_' '^we_146ar_' 'wer_146ar_' 0 $null $false $pGerMot $null '146 AR: new formation under 16 PzGr Div (30 July 146 AR: HQ, FO teams, 4th battery)' @{ parent = 'p_we_16mid'; after = 'p_we_156mir'; code = 70; ext = 146; move = $null }
# --- 23 PzD (126, 128 MIR; 51 eng bn, 23 recon bn, 128 AR)
Map 'p_we_126mir' '^we_126_'  '^we_126_'  'wer_126mir_' 0 '^we_126_8c_' $true $pGerMot $null '126 MIR: 30 July 126 MIR structure (8th coy already present)'
Map 'p_we_128mir' '^we_128_'  '^we_128_'  'wer_128mir_' 0 $null $true $pGerMot $null '128 MIR: 30 July 128 MIR structure'
Map 'p_we_23td'   '^we_51eb_(com|1c_)' '^we_51eb_' 'wer_51sbn_' 0 $null $false $pGerMot $null '51 eng bn HQ + 1 coy (2 and 3 coy already present)'
Map 'p_we_23td'   '^we_23rb_(com|ac81|1c_|3c_|4c_|5c_)' '^we_23rb_' 'wer_23rb_' 0 $null $false $pGerMot $null '23 recon bn: HQ, FO, armoured-car coy, 2 scout coys, heavy coy (APC coy already present)'
Map 'p_we_128ar'  '^we_128ar_' '^we_128ar_' 'wer_128ar_' 0 $null $false $pGerMot $null '128 AR: new formation under 23 PzD (30 July 128 AR: HQ, FO teams, 3rd battery) + the 17 July I/128 AR batteries' @{ parent = 'p_we_23td'; after = 'p_we_128mir'; code = 168; ext = 128; move = '^wer_128ar_[123]abat$' }

# ---------------------------------------------------------------- load the template and the global text keys
$tplDir = Unpack-Op $tplOp
$T = Azcf-Load (Join-Path $tplDir 'desc.config.loc_def.bin')
$tAct = Kid $T.root 'act_platoons'
$tText = @{ eng = Read-Text (Join-Path $tplDir 'text.text.loc_eng.bin'); rus = Read-Text (Join-Path $tplDir 'text.text.loc_rus.bin') }
$tTextIdx = @{ eng = @{}; rus = @{} }
foreach ($l in 'eng', 'rus') { foreach ($k in $tText[$l].keys) { $tTextIdx[$l][$k.key] = $k } }
$gKeys = @{}
foreach ($f in Get-ChildItem $globalText -Filter '*.text.loc_eng.bin') { foreach ($k in (Read-Text $f.FullName).keys) { $gKeys[$k.key] = 1 } }

$changeLog = New-Object Collections.Generic.List[string]
foreach ($side in $Sides) {
    $op = $ops[$side]
    $vDir = Unpack-Op $op
    $D = Azcf-Load (Join-Path $vDir 'desc.config.loc_def.bin')
    $act = Kid $D.root 'act_platoons'; $res = Kid $D.root 'reserves'
    $byName = @{}; $uids = @{}; $maxHi = [uint32]0
    foreach ($p in $act.kids) { $byName[$p.name] = $p; $u = [uint32](FU $p 'uid'); $uids[$u] = 1; if (($u -shr 12) -gt $maxHi) { $maxHi = $u -shr 12 } }
    $naText = @{ eng = Read-Text (Join-Path $vDir 'text.text.loc_eng.bin'); rus = Read-Text (Join-Path $vDir 'text.text.loc_rus.bin') }
    $naKeys = @{}; foreach ($k in $naText.eng.keys) { $naKeys[$k.key] = 1 }
    $needKeys = New-Object Collections.Specialized.OrderedDictionary   # new key -> @{ src = template key; sub = hashtable }
    $added = 0; $merged = 0; $skipped = 0
    $changeLog.Add(""); $changeLog.Add("## $op"); $changeLog.Add("")
    function Need-Key([string]$key, [hashtable]$sub) {
        # returns the key to use; registers a copy from the 30 July text when neither the global nor the 17 July pack has it
        $newKey = $key
        if ($sub) { foreach ($kv in $sub.GetEnumerator()) { $newKey = $newKey.Replace($kv.Key, $kv.Value) } }
        if (-not $gKeys.ContainsKey($newKey) -and -not $naKeys.ContainsKey($newKey) -and -not $needKeys.Contains($newKey)) {
            if ($tTextIdx.eng.ContainsKey($key)) { $needKeys[$newKey] = @{ src = $key; sub = $sub } }
            else { Write-Warning "$side : text key $key exists nowhere" }
        }
        $newKey
    }
    function New-Uid([uint32]$hi, [int]$code) { $uid = ($hi -shl 12) -bor [uint32]$code; while ($uids.ContainsKey($uid)) { $uid += 0x1000 }; $uids[$uid] = 1; $uid }

    # ---------------- pass 1: formations
    foreach ($mp in $M) {   # not $m: PowerShell variable names are case-insensitive and $m would overwrite $M
        $fnode = Kid $res $mp.form
        if (-not $fnode -and $mp.create) {
            $cr = $mp.create
            $parent = Kid $res $cr.parent; $after = Kid $res $cr.after
            if (-not $parent -or -not $after) { Write-Warning "$side : cannot create $($mp.form): parent or anchor missing"; continue }
            $fnode = Clone-Node $parent; $fnode.kids.Clear(); $fnode.name = $mp.form
            SetF $fnode 'code' "u:$($cr.code)"; SetF $fnode 'ext_code' "u:$($cr.ext)"; SetF $fnode 'parent' "s:$($cr.parent)"
            SetF $fnode 'div_sprite' 's:divh_reg'; SetF $fnode 'attr_side' 'u:0'; SetF $fnode 'rgk' 'b:0'
            # ai: the first sibling formation (same parent) that has platoons; division formations are AI placeholders
            $aiSrc = $null
            foreach ($f in $res.kids) { if ((FS $f 'parent') -eq $cr.parent) { foreach ($p in $act.kids) { if ((Pool $p) -eq $f.name) { $aiSrc = $f; break } }; if ($aiSrc) { break } } }
            if (-not $aiSrc) { $aiSrc = $after }
            (Fld $fnode 'ai').c[0] = Clone-Cell (Fld $aiSrc 'ai').c[0]
            $tplForm = $(if ($cr.tplForm) { $cr.tplForm } else { $mp.form })
            $fname = Need-Key ("op_$($tplForm.Substring(2))") $mp.keySub
            SetF $fnode 'name' "s:$fname"
            $res.kids.Insert($res.kids.IndexOf($after) + 1, $fnode)
            $changeLog.Add("### $($mp.form)  NEW FORMATION under $($cr.parent) (name key $fname, ai $(Fcc $fnode 'ai'))")
            # re-pool the 17 July division batteries into it
            if ($cr.move) {
                # the 17 July division batteries become the gun platoons of batteries 1-3 of the new regiment, coded and
                # named as on 30 July: battery n of battalion ceil(n/3) -> code (bn << 8) | (n << 4) | k, k = 2 (1st platoon),
                # 3 (2nd)...; codes already used by the 30 July template platoons of this regiment are skipped
                $taken = @{}
                foreach ($t in $tAct.kids) { if ($t.name -match $mp.tpl) { $taken[(Code $t)] = 1 } }
                $gunKeyTpl = $null   # German: a 30 July gun-platoon key of this regiment to clone the name from
                foreach ($t in $tAct.kids) { if ($t.name -match $mp.tpl -and (FS $t 'name') -match '_(\d)b2$') { $gunKeyTpl = FS $t 'name'; break } }
                $mvIdx = 0
                foreach ($p in $act.kids) { if ($p.name -match $cr.move) {
                    $oldPool = Pool $p; $mvIdx++
                    SetF $p 'pool' "s:$($mp.form)"
                    $bat = $mvIdx; if ($p.name -match '(\d)(arty|abat)$') { $bat = [int]$Matches[1] } elseif ($p.name -match '_(\d)b$') { $bat = [int]$Matches[1] }
                    $bn = [math]::Ceiling($bat / 3); $k = 2
                    while ($taken.ContainsKey((($bn -shl 8) -bor ($bat -shl 4) -bor $k))) { $k++ }
                    $c = ($bn -shl 8) -bor ($bat -shl 4) -bor $k; $taken[$c] = 1
                    SetF $p 'code' "u:$c"
                    $oldName = FS $p 'name'; $newName = $oldName
                    if ((Fcc $p 'side') -eq 'USSR') { $cand = "oppl_ussr_ar_${bat}b$k"; if ($gKeys.ContainsKey($cand)) { $newName = $cand } }
                    elseif ($gunKeyTpl -and $gunKeyTpl -match '^(.*_)(\d)b2$') {
                        $pre = $Matches[1]; $mBat = $Matches[2]
                        $sub = @{ "${mBat}b2" = "${bat}b$k"; "${mBat}./" = "${bat}./"; '1 arty plt' = "$($k - 1) arty plt" }
                        if ($mp.keySub) { foreach ($kv in $mp.keySub.GetEnumerator()) { $sub[$kv.Key] = $kv.Value } }
                        $newName = Need-Key $gunKeyTpl $sub
                    }
                    if ($newName -ne $oldName) { SetF $p 'name' "s:$newName" }
                    $changeLog.Add("- MOVED ``$($p.name)`` (0x$('{0:x}' -f $c), $(Real $p), name $newName) from ${oldPool}: gun platoon of battery $bat")
                } }
            }
        }
        if (-not $fnode) { Write-Warning "$side : formation $($mp.form) not found"; continue }
        $mine = New-Object Collections.Generic.List[object]
        foreach ($p in $act.kids) { if ((Pool $p) -eq $mp.form) { $mine.Add($p) } }
        if ($mine.Count -eq 0 -and -not $mp.create) { Write-Warning "$side : $($mp.form) has no platoons; skipped ($($mp.note))"; continue }
        $hq = $null; foreach ($p in $mine) { if ((Code $p) -eq 0 -and -not (IsBg $p)) { $hq = $p; break } }
        if ($hq) { $hi = [uint32]((FU $hq 'uid') -shr 12) } elseif ($mine.Count -and -not $mp.create) { $hi = [uint32]((FU $mine[0] 'uid') -shr 12) } else { $maxHi++; $hi = $maxHi }
        $lastIdx = -1; for ($i = 0; $i -lt $act.kids.Count; $i++) { if ($mine.Contains($act.kids[$i])) { $lastIdx = $i } }
        if ($lastIdx -lt 0) {
            # new formation without platoons yet: after the last platoon of the anchor formation
            for ($i = 0; $i -lt $act.kids.Count; $i++) { if ((Pool $act.kids[$i]) -eq $mp.create.after) { $lastIdx = $i } }
            if ($lastIdx -lt 0) { $lastIdx = $act.kids.Count - 1 }
        }
        $tpls = @($tAct.kids | Where-Object { $_.name -match $mp.tpl -and -not (IsBg $_) -and ((Code $_) -ne 0 -or ($mp.create -and -not $hq)) })
        if ($tpls.Count -eq 0) { Write-Warning "$side : no 30 July platoons match $($mp.tpl)"; continue }
        $changeLog.Add("### $($mp.form)  ($($mp.note))")
        $a0 = $added; $m0 = $merged; $s0 = $skipped
        foreach ($t in $tpls) {
            if ($mp.exclude -and $t.name -match $mp.exclude) { continue }
            $code = (Code $t) + $mp.shift; $grp = $code -band 0xFF0
            $n = $null; foreach ($p in $mine) { if ((Code $p) -eq $code) { $n = $p; break } }
            $tVeh = IsVehicle $t
            if ($n) {
                $same = ((Real $n) -eq (Real $t)) -and ((SpriteClass (Spr $n)) -eq (SpriteClass (Spr $t)))
                if ($same) {
                    if ((Real $t) -ne 'UNI' -or $mp.overrideUNI) {
                        $np = Kid $n 'pool'; $tp = Kid $t 'pool'
                        if ($np -and $tp) {
                            $before = PoolSummary $n
                            $np.rows.Clear(); foreach ($r in $tp.rows) { $np.rows.Add(@{ name = $r.name; c = @($r.c | ForEach-Object { Clone-Cell $_ }) }) }
                            $after2 = PoolSummary $n
                            if ($before -ne $after2) { $changeLog.Add("- ``$($n.name)`` (0x$('{0:x}' -f $code), $(Real $n)): composition $before -> $after2"); $merged++ }
                        }
                    }
                    foreach ($f in 'max_squads', 'range', 'eng_caps', 'scout_caps') { $tr = Fld $t $f; $nr = Fld $n $f; if ($tr -and $nr) { $nr.c[0] = Clone-Cell $tr.c[0] } }
                    continue
                }
                if ($tVeh -or (IsVehicle $n)) { $skipped++; continue }
                $free = -1
                for ($k = 8; $k -le 15; $k++) { $c2 = $grp + $k; $taken = $false; foreach ($p in $mine) { if ((Code $p) -eq $c2) { $taken = $true; break } }; if (-not $taken) { $free = $c2; break } }
                if ($free -lt 0) { Write-Warning "$side : no free code near 0x$('{0:x}' -f $code) for $($t.name)"; $skipped++; continue }
                $code = $free
            } elseif ($tVeh) {
                $vehHere = $false; foreach ($p in $mine) { if (((Code $p) -band 0xFF0) -eq $grp -and (IsVehicle $p)) { $vehHere = $true; break } }
                if ($vehHere) { $skipped++; continue }
            }
            # add
            $c = Clone-Node $t
            $nm = $t.name -replace $mp.tplPrefix, $mp.naPrefix
            $base = $nm; $x = 2; while ($byName.ContainsKey($nm)) { $nm = "${base}_$x"; $x++ }
            $c.name = $nm
            SetF $c 'code' "u:$code"
            SetF $c 'uid' "u:$(New-Uid $hi $code)"
            SetF $c 'pool' "s:$($mp.form)"
            (Fld $c 'ai').c[0] = Clone-Cell (Fld $fnode 'ai').c[0]
            if ($mp.params -and $code -ne 0) { SetF $c 'params' $mp.params }
            $newKey = Need-Key (FS $c 'name') $mp.keySub
            if ($newKey -ne (FS $c 'name')) { SetF $c 'name' "s:$newKey" }
            $act.kids.Insert($lastIdx + 1, $c); $lastIdx++
            $mine.Add($c); $byName[$nm] = $c; $added++
            if ($code -eq 0) { $hq = $c }
            $changeLog.Add("- NEW ``$nm`` (0x$('{0:x}' -f $code), $(Real $c), $(Spr $c)): $(PoolSummary $c)")
        }
        if ($Verbose2) { "  $side $($mp.form) <- $($mp.tpl): $($tpls.Count) template platoons, +$($added - $a0) added, ~$($merged - $m0) merged, -$($skipped - $s0) skipped (17 July platoons in formation: $($mine.Count))" }
    }
    # created formations: nodes in code order (HQ, then battery by battery), as the 30 July file lists them
    foreach ($mp in $M) {
        if (-not $mp.create) { continue }
        $idx = @(); for ($i = 0; $i -lt $act.kids.Count; $i++) { if ((Pool $act.kids[$i]) -eq $mp.form) { $idx += $i } }
        if ($idx.Count -lt 2) { continue }
        $nodes = @($idx | ForEach-Object { $act.kids[$_] })
        for ($j = $idx.Count - 1; $j -ge 0; $j--) { $act.kids.RemoveAt($idx[$j]) }
        $sorted = @($nodes | Sort-Object { Code $_ })
        $at = $idx[0]; foreach ($n in $sorted) { $act.kids.Insert($at, $n); $at++ }
    }

    # ---------------- pass 2: split tank / SPG companies into command + platoons
    # A company pool of the 17 July file: [company command '*_ccom' (+ extra tanks)] then sections, each '*_com' x1 + tanks.
    $changeLog.Add("### Tank and SPG companies split into command + platoons (30 July pattern)")
    $splitCount = 0
    $coyOf = @{}      # platoon node name -> company key ("<formation>/<company code>") for every split company (pass 3 keeps a company together)
    $snapshot = New-Object Collections.Generic.List[object]; foreach ($q in $act.kids) { $snapshot.Add($q) }
    # ($cmd is taken: gt3.ps1's [string]$Cmd parameter lives in this scope after the dot-source, and names are case-insensitive)
    foreach ($p in $snapshot) {
        if ((IsBg $p) -or (Code $p) -eq 0) { continue }
        if ((Real $p) -ne 'STR' -and (Real $p) -ne 'SUPM') { continue }
        $pool = Kid $p 'pool'; if (-not $pool -or $pool.rows.Count -lt 3) { continue }
        if ($pool.rows[0].c[0].s -notmatch '_ccom$') { continue }
        $segs = @(); $cur = @($pool.rows[0])
        for ($i = 1; $i -lt $pool.rows.Count; $i++) {
            $sq = $pool.rows[$i].c[0].s
            if ($sq -match '_com$' -and $sq -notmatch '_ccom$|_bcom$') { $segs += ,$cur; $cur = @($pool.rows[$i]) } else { $cur += $pool.rows[$i] }
        }
        $segs += ,$cur
        if ($segs.Count -lt 3) { continue }      # command + at least two sections
        $code = Code $p; $coy = ($code -shr 4) -band 0xF; if ($coy -lt 1) { $coy = 1 }; $form = Pool $p; $hi = [uint32]((FU $p 'uid') -shr 12)
        $isGer = (Fcc $p 'side') -eq 'GER'; $spr = Spr $p
        if ($isGer) {
            if ($spr -match 'stug') { $kc = "oppl_ger_stug_${coy}b"; $kp = "oppl_ger_stug_${coy}b{0}" }
            elseif ($spr -match 'marder') { $kc = "oppl_ger_${coy}atspgc"; $kp = "oppl_ger_${coy}atspgc{0}" }
            else { $kc = "oppl_ger_tr_${coy}med"; $kp = "oppl_ger_tr_${coy}med{0}" }   # also the 9./201 sIG 33B company: "9 tank coy, N platoon"
        } else { $kc = "oppl_ussr_tr_${coy}c"; $kp = "oppl_ussr_tr_${coy}c{0}" }
        $like = $pool.rows[0]
        # company command node (new), code = company code
        $cmdNode = Clone-Node $p; $cmdNode.name = "$($p.name)_com"; $x = 2; while ($byName.ContainsKey($cmdNode.name)) { $cmdNode.name = "$($p.name)_com$x"; $x++ }
        SetF $cmdNode 'real_type' "u:'COMC'"; SetF $cmdNode 'str_sprite' 's:plu_tankcmd'; SetF $cmdNode 'name' "s:$(Need-Key $kc $null)"
        SetF $cmdNode 'uid' "u:$(New-Uid $hi ($code + 15))"
        $cp = Kid $cmdNode 'pool'; $cp.rows.Clear(); foreach ($r in $segs[0]) { $cp.rows.Add(@{ name = $null; c = @($r.c | ForEach-Object { Clone-Cell $_ }) }) }
        $cnt = 0; foreach ($r in $segs[0]) { $cnt += [int][BitConverter]::ToInt32([BitConverter]::GetBytes([uint32]$r.c[1].v[0]), 0) }
        SetF $cmdNode 'max_squads' "u:$($cnt + 1)"
        $idx = $act.kids.IndexOf($p)
        $act.kids.Insert($idx, $cmdNode); $byName[$cmdNode.name] = $cmdNode
        # the original node becomes platoon 1, further sections become new nodes; platoon codes are the free codes of
        # the company group (the 17 July file keeps Marder platoons at company code + 1 in the 116 tank bn)
        $usedCodes = @{}; foreach ($q in $act.kids) { if ((Pool $q) -eq $form) { $usedCodes[(Code $q)] = 1 } }
        $platNodes = @(); $pc = $code
        for ($s = 1; $s -lt $segs.Count; $s++) {
            if ($s -eq 1) { $pn = $p } else {
                $pn = Clone-Node $p; $pn.name = "$($p.name)_${s}p"; $x = 2; while ($byName.ContainsKey($pn.name)) { $pn.name = "$($p.name)_${s}p$x"; $x++ }
                $act.kids.Insert($act.kids.IndexOf($platNodes[-1]) + 1, $pn); $byName[$pn.name] = $pn
            }
            do { $pc++ } while ($usedCodes.ContainsKey($pc) -and $pc -lt $code + 15)
            $usedCodes[$pc] = 1
            SetF $pn 'code' "u:$pc"
            if ($s -gt 1) { SetF $pn 'uid' "u:$(New-Uid $hi $pc)" }
            SetF $pn 'name' "s:$(Need-Key ($kp -f $s) $null)"
            $pp = Kid $pn 'pool'; $pp.rows.Clear(); foreach ($r in $segs[$s]) { $pp.rows.Add(@{ name = $null; c = @($r.c | ForEach-Object { Clone-Cell $_ }) }) }
            $cnt = 0; foreach ($r in $segs[$s]) { $cnt += [int][BitConverter]::ToInt32([BitConverter]::GetBytes([uint32]$r.c[1].v[0]), 0) }
            SetF $pn 'max_squads' "u:$($cnt + 1)"
            $platNodes += $pn
        }
        foreach ($pn in $platNodes) { $coyOf[$pn.name] = "$form/$code" }
        $splitCount++
        $changeLog.Add("- ``$($p.name)`` (0x$('{0:x}' -f $code)) -> ``$($cmdNode.name)`` command ($(PoolSummary $cmdNode)) + " + (($platNodes | ForEach-Object { "``$($_.name)`` ($(PoolSummary $_))" }) -join ' + '))
    }

    # ---------------- pass 2b (0.5.10, user: "some artillery batteries lack their FO; FO lacks guns"): complete batteries.
    # The engine counts an FO team's guns from the gun platoons of its own company group (code & 0xFF0) in the same
    # formation, so every FO gets a gun platoon of its type in its group (or moves into the group that holds the guns
    # of its type) and every indirect-fire gun platoon gets an FO team. Same code as tools\oob_saur.ps1 pass 2h.
    $changeLog.Add("### Batteries completed: FO <-> gun platoon in the same group")
    $famOf = @{ 'rkka_artsup_zis3_plat' = 'zis3'; 'rkka_artsup_zis3_sq' = 'zis3'; 'rkka_artsup_m30_plat' = 'm30'; 'rkka_artsup_pp27_plat' = 'pp27'; 'rkka_artsup_mt82_plat' = 'mt82'; 'rkka_artsup_mt82d_plat' = 'mt82'; 'rkka_artsup_mt82_coy' = 'mt82'; 'rkka_artsup_mt120_plat' = 'mt120'; 'rkka_artsup_mt120_coy' = 'mt120'; 'rkka_artsup_mt120_bn' = 'mt120'; 'rkka_artsup_mt120_bat' = 'mt120'; 'wer_artsup_lefh_plat' = 'lefh'; 'wer_artsup_sfh414f_plat' = 'sfh'; 'wer_artsup_leig_plat' = 'leig'; 'wer_artsup_grw34_sec' = 'grw34'; 'wer_artsup_grw34_plat' = 'grw34' }
    $famGun = @{ zis3 = @{ rx = '^(rkka_zis3|rn_rkka_div_gun)$'; squad = 'rkka_zis3'; tpl = 'ra_84ar_7b_1p'; sprite = 'pl_zis3'; mob = 'HORS'; sup = 'rkka_artsup_zis3_plat'; foTpl = 'ra_90ar_1b_ac' }
                 m30 = @{ rx = '^rkka_m30'; squad = 'rkka_m30_m38'; tpl = 'ra_84ar_9b_1p'; sprite = 'pl_m30'; mob = 'HORS'; sup = 'rkka_artsup_m30_plat'; foTpl = 'ra_90ar_3b_ac' }
                 pp27 = @{ rx = '^rkka_pp27$'; squad = 'rkka_pp27'; tpl = 'ra_9_gunc_1p'; sprite = 'pl_pp27'; mob = 'HORS'; sup = 'rkka_artsup_pp27_plat'; foTpl = 'ra_9_ac76gun' }
                 mt82 = @{ rx = '^rkka_mt82$'; squad = 'rkka_mt82'; tpl = 'ra_9_1mt_1p'; sprite = 'plu_mortars'; mob = 'FOOT'; sup = 'rkka_artsup_mt82_plat'; foTpl = 'ra_9_1b_ac82mt' }
                 mt120 = @{ rx = '^rkka_pm38$'; squad = 'rkka_pm38'; tpl = 'ra_9_1mt_1p'; sprite = 'plu_mortars'; mob = 'HORS'; sup = 'rkka_artsup_mt120_plat'; foTpl = 'ra_9_ac120mt2' }
                 lefh = @{ rx = '^wer_lefh'; squad = 'wer_lefh18m'; tpl = 'we_75ar_3b_1p'; sprite = 'pl_lefh'; mob = 'HORS'; sup = 'wer_artsup_lefh_plat'; foTpl = 'we_tk_ar_4b_ac' }
                 sfh = @{ rx = '^wer_sfh'; squad = 'wer_sfh414f'; tpl = 'we_6mir_13c_sfh1'; sprite = 'pl_c17s_howit'; mob = 'HORS'; sup = 'wer_artsup_sfh414f_plat'; foTpl = 'we_tk_ar_10b_ac' }
                 leig = @{ rx = '^(wer_leig|rn_wer_leig)'; squad = 'wer_leig18'; tpl = 'we_6mir_4c_leig1'; sprite = 'pl_leig'; mob = 'HORS'; sup = 'wer_artsup_leig_plat'; foTpl = 'we_6mir_1b_ac75' }
                 grw34 = @{ rx = '^wer_grw34$'; squad = 'wer_grw34'; tpl = 'we_6mir_15c_mt'; sprite = 'plu_mortars'; mob = 'FOOT'; sup = 'wer_artsup_grw34_sec'; foTpl = 'we_6mir_1b_ac81' } }
    function Fo-Sup([object]$p) { $pk = Kid $p 'pool'; if (-not $pk) { return '' }; foreach ($r in $pk.rows) { if ($r.c[0].s -match 'corr_art' -and $r.c[4].s) { return $r.c[4].s } }; '' }
    function Gun-Fams([object]$p) { $out = @(); $pk = Kid $p 'pool'; if (-not $pk -or (Real $p) -ne 'SUP') { return $out }; foreach ($r in $pk.rows) { foreach ($fk in $famGun.Keys) { if ($r.c[0].s -match $famGun[$fk].rx -and $out -notcontains $fk) { $out += $fk } } }; $out }
    function Tpl-Node([string]$name) { $tAct.kids | Where-Object { $_.name -eq $name } | Select-Object -First 1 }
    $batFixed = 0
    $formNames = @($res.kids | ForEach-Object { $_.name })
    foreach ($fn in $formNames) {
        $nodes = @($act.kids | Where-Object { (Pool $_) -eq $fn -and -not (IsBg $_) -and (Code $_) -ne 0 })
        if (-not $nodes.Count) { continue }
        $isAr = ($fn -match 'ar$'); $sideCc = Fcc $nodes[0] 'side'
        $hiF = [uint32]((FU $nodes[0] 'uid') -shr 12)
        $usedF = @{}; foreach ($q in $act.kids) { if ((Pool $q) -eq $fn) { $usedF[(Code $q)] = 1 } }
        function FreeIn([int]$g, [int]$pref) { $c = $g + $pref; while ($usedF.ContainsKey($c)) { $c++; if (($c -band 0xFF0) -ne $g) { return -1 } }; $usedF[$c] = 1; $c }
        function Insert-After([object]$anchor, [object]$n) { $act.kids.Insert($act.kids.IndexOf($anchor) + 1, $n); $byName[$n.name] = $n }
        function Ar-Key([string]$fnName, [int]$bat, [string]$suffix, [string]$fallback) {
            if ($sideCc -eq 'USSR' -and $isAr) { return (Need-Key "oppl_ussr_ar_${bat}b$suffix" $null) }
            if ($isAr) { foreach ($q in $act.kids) { if ((Pool $q) -eq $fnName) { $k = FS $q 'name'; if ($k -match '^(.*_)(\d)b' + $suffix + '$') {
                $m = $Matches[2]; $sub = @{ "${m}b$suffix" = "${bat}b$suffix"; "${m}./" = "${bat}./" }
                # a sibling key that is itself a copy with substitutions (306/302 AR cloned from 294 AR): go back to its
                # 30 July source key and merge the substitutions, so the text pack gets the new key too
                if (-not $tTextIdx.eng.ContainsKey($k) -and $needKeys.Contains($k)) { $spec = $needKeys[$k]; if ($spec.sub) { foreach ($kv in $spec.sub.GetEnumerator()) { $sub[$kv.Key] = $kv.Value } }; $k = $spec.src }
                return (Need-Key $k $sub) } } } }
            Need-Key $fallback $null
        }
        $groups = @{}; foreach ($n in $nodes) { $g = (Code $n) -band 0xFF0; if (-not $groups.ContainsKey($g)) { $groups[$g] = @() }; $groups[$g] += $n }
        foreach ($g in @($groups.Keys)) {
            $bat = ($g -shr 4) -band 0xF
            $fos = @($groups[$g] | Where-Object { (Real $_) -eq 'CTRL' -and $famOf.ContainsKey((Fo-Sup $_)) })
            $gunsByFam = @{}; foreach ($n in $groups[$g]) { foreach ($fk in (Gun-Fams $n)) { if (-not $gunsByFam.ContainsKey($fk)) { $gunsByFam[$fk] = @() }; $gunsByFam[$fk] += $n } }
            $foFams = @{}; foreach ($f0 in $fos) { $foFams[$famOf[(Fo-Sup $f0)]] = $f0 }
            foreach ($f0 in $fos) {
                $fam = $famOf[(Fo-Sup $f0)]; if ($gunsByFam.ContainsKey($fam)) { continue }
                $moved = $false
                # candidate groups: same battalion first (1st bn mortar FO -> 1 MT coy), then the rest
                $cands = @($groups.Keys | Where-Object { $_ -ne $g } | Sort-Object { $(if (($_ -shr 8) -eq ($g -shr 8)) { 0 } else { 1 }) }, { $_ })
                foreach ($g2 in $cands) {
                    $g2guns = @($groups[$g2] | Where-Object { (Gun-Fams $_) -contains $fam }); if (-not $g2guns.Count) { continue }
                    $g2fo = @($groups[$g2] | Where-Object { (Real $_) -eq 'CTRL' -and $famOf.ContainsKey((Fo-Sup $_)) -and $famOf[(Fo-Sup $_)] -eq $fam }); if ($g2fo.Count) { continue }
                    $nc = FreeIn $g2 1; if ($nc -lt 0) { continue }
                    $usedF.Remove((Code $f0)); SetF $f0 'code' "u:$nc"; $groups[$g2] += $f0; $moved = $true; $batFixed++
                    $changeLog.Add("- ``$($f0.name)`` ($fn) moved to group 0x$('{0:x}' -f $g2) (code 0x$('{0:x}' -f $nc)) where its $fam guns are: " + (($g2guns | ForEach-Object { $_.name }) -join ', '))
                    break
                }
                if ($moved) { continue }
                $spec = $famGun[$fam]
                $tpl = $act.kids | Where-Object { (Pool $_) -eq $fn -and ((Gun-Fams $_) -contains $fam) } | Select-Object -First 1
                if (-not $tpl) { $tpl = Tpl-Node $spec.tpl }
                if (-not $tpl) { Write-Warning "$side : no gun template for $fam"; continue }
                $nc = FreeIn $g 2; if ($nc -lt 0) { Write-Warning "$side : no free code in group 0x$('{0:x}' -f $g) of $fn"; continue }
                $n = Clone-Node $tpl; $n.name = "$($f0.name -replace '_ac\w*$', '')_guns"; $x = 2; $base = $n.name; while ($byName.ContainsKey($n.name)) { $n.name = "${base}_$x"; $x++ }
                SetF $n 'code' "u:$nc"; SetF $n 'pool' "s:$fn"; (Fld $n 'ai').c[0] = Clone-Cell (Fld $f0 'ai').c[0]; (Fld $n 'params').c[0] = Clone-Cell (Fld $f0 'params').c[0]; (Fld $n 'side').c[0] = Clone-Cell (Fld $f0 'side').c[0]
                SetF $n 'uid' "u:$(New-Uid $hiF $nc)"; SetF $n 'real_type' "u:'SUP'"; SetF $n 'str_sprite' "s:$($spec.sprite)"; SetF $n 'mobility' "u:'$($spec.mob)'"; SetF $n 'bg' 'u:0'
                $pk = Kid $n 'pool'; $pk.rows.Clear()
                $pk.rows.Add(@{ name = $null; c = @((Cell-Decode "s:$(if ($sideCc -eq 'USSR') { 'rkka_com_art_fplat' } else { 'wer_com_art_plat' })"), (Cell-Decode 'a:1'), (Cell-Decode 'v:-1;-1;-1;-1'), (Cell-Decode 'v:-1;-1;-1;-1'), (Cell-Decode 's:')) })
                $pk.rows.Add(@{ name = $null; c = @((Cell-Decode "s:$($spec.squad)"), (Cell-Decode 'a:2'), (Cell-Decode 'v:-1;-1;-1;-1'), (Cell-Decode 'v:-1;-1;-1;-1'), (Cell-Decode 's:')) })
                SetF $n 'max_squads' 'u:3'
                SetF $n 'name' "s:$(Ar-Key $fn $bat '2' (FS $tpl 'name'))"
                Insert-After $f0 $n; $groups[$g] += $n; $batFixed++; $added++
                $changeLog.Add("- NEW ``$($n.name)`` (0x$('{0:x}' -f $nc), SUP, $($spec.squad) x2) in $fn for FO ``$($f0.name)``")
            }
            foreach ($fam in @($gunsByFam.Keys)) {
                if ($foFams.ContainsKey($fam)) { continue }
                if ($fn -match 'iptabr|destr|atbn|atb$' -or $gunsByFam[$fam][0].name -match 'destr|iptabr|_atg|_atb') { continue }   # anti-tank units: direct fire, no FO
                $spec = $famGun[$fam]
                $tpl = $act.kids | Where-Object { (Pool $_) -eq $fn -and (Real $_) -eq 'CTRL' -and $famOf.ContainsKey((Fo-Sup $_)) -and $famOf[(Fo-Sup $_)] -eq $fam } | Select-Object -First 1
                if (-not $tpl) { $tpl = Tpl-Node $spec.foTpl }
                if (-not $tpl) { Write-Warning "$side : no FO template for $fam"; continue }
                $nc = FreeIn $g 1; if ($nc -lt 0) { Write-Warning "$side : no free code in group 0x$('{0:x}' -f $g) of $fn"; continue }
                $gun = $gunsByFam[$fam][0]
                $n = Clone-Node $tpl; $n.name = "$($gun.name)_ac"; $x = 2; $base = $n.name; while ($byName.ContainsKey($n.name)) { $n.name = "${base}_$x"; $x++ }
                SetF $n 'code' "u:$nc"; SetF $n 'pool' "s:$fn"; (Fld $n 'ai').c[0] = Clone-Cell (Fld $gun 'ai').c[0]; (Fld $n 'params').c[0] = Clone-Cell (Fld $gun 'params').c[0]; (Fld $n 'side').c[0] = Clone-Cell (Fld $gun 'side').c[0]
                SetF $n 'uid' "u:$(New-Uid $hiF $nc)"; SetF $n 'bg' 'u:0'
                $pk = Kid $n 'pool'; foreach ($r in $pk.rows) { if ($r.c[0].s -match 'corr_art') { $r.c[4] = Cell-Decode "s:$($spec.sup)" } }
                SetF $n 'name' "s:$(Ar-Key $fn $bat '1' (FS $tpl 'name'))"
                Insert-After $gun $n; $groups[$g] += $n; $foFams[$fam] = $n; $batFixed++; $added++
                $changeLog.Add("- NEW ``$($n.name)`` (0x$('{0:x}' -f $nc), CTRL, FO $fam) in $fn for ``$($gun.name)``")
            }
            # (0.5.11, user: "they lack commander") an artillery-regiment battery with FO and guns gets a battery command
            if ($isAr -and $g -ge 0x100) {
                $hasFo = @($groups[$g] | Where-Object { (Real $_) -eq 'CTRL' }).Count -gt 0
                $hasGun = @($groups[$g] | Where-Object { (Gun-Fams $_).Count -gt 0 }).Count -gt 0
                $hasCmd = @($groups[$g] | Where-Object { (Real $_) -eq 'COMC' }).Count -gt 0
                if ($hasFo -and $hasGun -and -not $hasCmd -and -not $usedF.ContainsKey($g)) {
                    $tplC = $act.kids | Where-Object { (Pool $_) -eq $fn -and (Real $_) -eq 'COMC' } | Select-Object -First 1
                    if (-not $tplC) { $tplC = Tpl-Node $(if ($sideCc -eq 'USSR') { 'ra_1012ar_4b_hq' } else { 'we_294ar_4b_hq' }) }
                    if ($tplC) {
                        $usedF[$g] = 1
                        $fo0 = @($groups[$g] | Where-Object { (Real $_) -eq 'CTRL' })[0]
                        $n = Clone-Node $tplC; $n.name = "$($fo0.name -replace '_ac\w*$', '')_hq"; $x = 2; $base = $n.name; while ($byName.ContainsKey($n.name)) { $n.name = "${base}_$x"; $x++ }
                        SetF $n 'code' "u:$g"; SetF $n 'pool' "s:$fn"; (Fld $n 'ai').c[0] = Clone-Cell (Fld $fo0 'ai').c[0]; (Fld $n 'params').c[0] = Clone-Cell (Fld $fo0 'params').c[0]; (Fld $n 'side').c[0] = Clone-Cell (Fld $fo0 'side').c[0]
                        SetF $n 'uid' "u:$(New-Uid $hiF $g)"; SetF $n 'bg' 'u:0'
                        SetF $n 'name' "s:$(Ar-Key $fn $bat '' (FS $tplC 'name'))"
                        $act.kids.Insert($act.kids.IndexOf($fo0), $n); $byName[$n.name] = $n
                        $groups[$g] += $n; $batFixed++; $added++
                        $changeLog.Add("- NEW ``$($n.name)`` (0x$('{0:x}' -f $g), COMC, battery command) in $fn")
                    }
                }
            }
        }
    }
    $changeLog.Add("- $batFixed battery fixes")

    # ---------------- pass 3: battle-group slots (SCT slot with FO/recon, fill empty slots from the battalion)
    $changeLog.Add("### Battle-group slots")
    $used = @{}
    foreach ($p in $act.kids) { if (IsBg $p) { $sl = Kid $p 'slots'; if ($sl) { foreach ($r in $sl.rows) { if ($r.c[0].s) { $used[$r.c[0].s] = 1 } } } } }
    $formOf = @{}; foreach ($f in $res.kids) { $formOf[$f.name] = $f }
    function Bn([object]$p) { ((Code $p) -shr 8) -band 0xF }
    function Pick([string]$form, [string[]]$roles, [int]$bn, [string]$sprPref) {
        # an unused platoon of $form with one of $roles, same battalion first, sprite preference first
        $cands = @()
        foreach ($p in $act.kids) { if ((Pool $p) -eq $form -and -not (IsBg $p) -and (Code $p) -ne 0 -and $roles -contains (Real $p) -and -not $used.ContainsKey($p.name)) { $cands += $p } }
        if (-not $cands.Count) { return $null }
        $ranked = $cands | Sort-Object { $(if ((Bn $_) -eq $bn) { 0 } else { 1 }) }, { $(if ($sprPref -and (Spr $_) -match $sprPref) { 0 } else { 1 }) }, { Code $_ }
        @($ranked)[0]
    }
    function PickCoy([string[]]$coyKeys, [string]$role) {
        # an unused platoon of one of the split companies $coyKeys (keeps a tank company's platoons in one battle group)
        foreach ($p in $act.kids) { if ($coyOf.ContainsKey($p.name) -and $coyKeys -contains $coyOf[$p.name] -and (Real $p) -eq $role -and -not $used.ContainsKey($p.name)) { return $p } }
        $null
    }
    # (0.5.12, user: "corresponding FO and their batteries are in different BGs") a battery and its FO team stay
    # together: a group that holds an artillery regiment's gun platoon gets the FO of that battery; a group without
    # guns gets an FO whose battery is not in any other group (the battery stays in reserve as its reinforcement)
    $gunGroupsInBgs = @{}   # "<formation>/<group>" of every artillery gun platoon sitting in a battle-group slot
    foreach ($b0 in $act.kids) { if (IsBg $b0) { $s0 = Kid $b0 'slots'; if ($s0) { foreach ($r in $s0.rows) { if ($r.c[0].s -and $byName.ContainsKey($r.c[0].s)) { $q = $byName[$r.c[0].s]; if ((Real $q) -eq 'SUP' -and (Pool $q) -match 'ar$') { $gunGroupsInBgs["$(Pool $q)/$((Code $q) -band 0xFF0)"] = $b0.name } } } } } }
    function Pick-Fo([string]$arF, [int[]]$groupsHere) {
        $cands = @($act.kids | Where-Object { (Pool $_) -eq $arF -and -not (IsBg $_) -and (Real $_) -eq 'CTRL' -and -not $used.ContainsKey($_.name) })
        if ($groupsHere.Count) { foreach ($c in $cands) { if ($groupsHere -contains ((Code $c) -band 0xFF0)) { return $c } }; return $null }
        foreach ($c in ($cands | Sort-Object { Code $_ })) { if (-not $gunGroupsInBgs.ContainsKey("$arF/$((Code $c) -band 0xFF0)")) { return $c } }
        $null
    }
    $slotFills = 0; $slotAdds = 0; $bgIdx = @{}
    foreach ($bg in $act.kids) {
        if (-not (IsBg $bg)) { continue }
        $sl = Kid $bg 'slots'; if (-not $sl -or $sl.rows.Count -eq 0) { continue }
        $form = Pool $bg
        if (-not $bgIdx.ContainsKey($form)) { $bgIdx[$form] = 0 }; $bgIdx[$form]++; $nth = $bgIdx[$form]
        $com = $null; foreach ($r in $sl.rows) { if ($r.c[0].s -and $byName.ContainsKey($r.c[0].s)) { $com = $byName[$r.c[0].s]; break } }
        $bn = $(if ($com) { Bn $com } else { 1 })
        $isArmour = ((Fcc $bg 'bg') -in @('TANK', 'TNK', 'SUPM', 'STR', 'SCT'))
        # division artillery regiment of this formation (parent's child whose name ends in 'ar')
        $arForm = $null; $isDiv = $false
        # a division's own battle groups (306 ID, 294 ID, 23 PzD): the regiment is a child of the formation
        foreach ($f in $res.kids) { if ((FS $f 'parent') -eq $form -and $f.name -match 'ar$') { $arForm = $f.name; $isDiv = $true; break } }
        if (-not $arForm -and $formOf.ContainsKey($form)) { $par = FS $formOf[$form] 'parent'; foreach ($f in $res.kids) { if ((FS $f 'parent') -eq $par -and $f.name -match 'ar$') { $arForm = $f.name; break } } }
        # reserve links (0.5.9, user: "the artillery regiments are not accessible to the divisions"): a battle group may
        # take units only from the formations in pool, pool2, pool3, pool4. 30 July: pool2 = division, pool3 = its
        # artillery regiment, pool4 = an attachment. The 17 July file had only one attachment; the division and the
        # regiment are put first, the old attachments after them (at most three, the rest logged).
        $par = $(if ($formOf.ContainsKey($form)) { FS $formOf[$form] 'parent' } else { '' })
        $links = New-Object Collections.Generic.List[string]
        if (-not $isDiv -and $par -and $formOf.ContainsKey($par) -and $par -ne $form) { $links.Add($par) }   # a division's own group needs no parent link (that would be the corps)
        if ($arForm -and $arForm -ne $form) { $links.Add($arForm) }
        foreach ($pf in 'pool2', 'pool3', 'pool4') { $v = FS $bg $pf; if ($v -and $v -ne $form -and -not $links.Contains($v)) { $links.Add($v) } }
        $dropped = @(); while ($links.Count -gt 3) { $dropped += $links[$links.Count - 1]; $links.RemoveAt($links.Count - 1) }
        $old = "$(FS $bg 'pool2')/$(FS $bg 'pool3')/$(FS $bg 'pool4')"
        for ($li = 0; $li -lt 3; $li++) { SetF $bg ("pool$($li + 2)") "s:$(if ($li -lt $links.Count) { $links[$li] } else { '' })" }
        $new = "$(FS $bg 'pool2')/$(FS $bg 'pool3')/$(FS $bg 'pool4')"
        if ($new -ne $old) { $changeLog.Add("- ``$($bg.name)``: reserve links $old -> $new$(if ($dropped.Count) { ' (dropped ' + ($dropped -join ', ') + ')' })") }
        $hasSct = $false; foreach ($r in $sl.rows) { if ((Fcc-Row $r) -eq 'SCT') { $hasSct = $true } }
        if (-not $hasSct) { $sl.rows.Insert(1, @{ name = $null; c = @((Cell-Decode 's:'), (Cell-Decode "u:'SCT'")) }) }
        # split tank companies in this battle group: a third STR slot (30 July tank battle groups hold three platoons)
        $coyKeys = @(); $strRows = 0; $lastStr = -1
        for ($i = 0; $i -lt $sl.rows.Count; $i++) { $r = $sl.rows[$i]; if ((Fcc-Row $r) -eq 'STR') { $strRows++; $lastStr = $i; if ($r.c[0].s -and $coyOf.ContainsKey($r.c[0].s)) { $coyKeys += $coyOf[$r.c[0].s] } } }
        if ($coyKeys.Count -and $strRows -lt 3 -and (PickCoy $coyKeys 'STR')) {
            $sl.rows.Insert($lastStr + 1, @{ name = $null; c = @((Cell-Decode 's:'), (Cell-Decode "u:'STR'")) }); $slotAdds++
            $changeLog.Add("- ``$($bg.name)``: third STR slot added")
        }
        foreach ($r in $sl.rows) {
            if ($r.c[0].s) { continue }
            $role = Fcc-Row $r; $pick = $null
            switch ($role) {
                'SCT' {
                    # 30 July pattern: armour battle groups carry a recon platoon or nothing; the first battle group of a rifle
                    # regiment carries the FO of a division artillery battery, the next one the regiment's own FO (76 mm guns,
                    # 120 mm mortars, battalion mortars) or its recon platoon
                    $arGroupsHere = @(); if ($arForm) { foreach ($r2 in $sl.rows) { if ($r2.c[0].s -and $byName.ContainsKey($r2.c[0].s)) { $q = $byName[$r2.c[0].s]; if ((Pool $q) -eq $arForm -and (Real $q) -eq 'SUP') { $arGroupsHere += ((Code $q) -band 0xFF0) } } } }
                    # (0.5.13, user: "remove artillery batteries from the BG if their own FO is in it") the battery that
                    # the chosen FO belongs to leaves the group's SUP slot and stays in reserve, firing through the FO
                    $dropBattery = { param($bgNode, $slotTbl, $foNode) if (-not $foNode -or (Pool $foNode) -notmatch 'ar$') { return }; $gq = (Code $foNode) -band 0xFF0; foreach ($r3 in $slotTbl.rows) { if ($r3.c[0].s -and $byName.ContainsKey($r3.c[0].s)) { $q3 = $byName[$r3.c[0].s]; if ((Pool $q3) -eq (Pool $foNode) -and (Real $q3) -eq 'SUP' -and (((Code $q3) -band 0xFF0) -eq $gq)) { $r3.c[0] = Cell-Decode 's:'; $used.Remove($q3.name); $changeLog.Add("- ``$($bgNode.name)``: battery ``$($q3.name)`` removed from the group (its FO ``$($foNode.name)`` is in it); it stays in reserve") } } } }
                    if ($isArmour) { $pick = Pick $form @('SCT') $bn 'scout|wscout|cavalary' }
                    elseif ($arForm -and $arGroupsHere.Count) { $pick = Pick-Fo $arForm $arGroupsHere; if (-not $pick) { $pick = Pick $form @('CTRL') $bn $null } }   # the group holds a battery: its own FO
                    elseif ($nth % 2 -eq 1) { if ($arForm) { $pick = Pick-Fo $arForm @() }; if (-not $pick) { $pick = Pick $form @('CTRL') $bn $null }; if (-not $pick) { $pick = Pick $form @('SCT') $bn $null } }
                    else { $pick = Pick $form @('CTRL') $bn $null; if (-not $pick) { $pick = Pick $form @('SCT') $bn $null } }
                }
                'STR'  { if ($coyKeys.Count) { $pick = PickCoy $coyKeys 'STR' }; if (-not $pick) { $pick = Pick $form @('STR') $bn $null } }
                'UNI'  { $pick = Pick $form @('UNI') $bn 'rifles' }
                'SUP'  { $pick = Pick $form @('SUP') $bn 'mortars' }
                'SUPM' { $pick = Pick $form @('SUPM') $bn $null }
            }
            if ($pick) { $r.c[0] = Cell-Decode "s:$($pick.name)"; $used[$pick.name] = 1; $slotFills++; $changeLog.Add("- ``$($bg.name)``: $role slot <- ``$($pick.name)``"); if ($role -eq 'SCT') { & $dropBattery $bg $sl $pick } }
        }
    }

    # ---------------- pass 4: map placement (plat_pos: uid; cell px; pz; map node | arrival turn)
    # Every platoon has a plat_pos row; -1;-1;-1 = not on the map (reserve of its formation). A formation whose HQ has
    # no map node never becomes available (its platoons stay in state 11, blank in the OOB panel), so the HQ of each
    # created artillery regiment is placed where 30 July puts it: with the division HQ when the division has one on the
    # map (German side), otherwise with the first sibling regiment HQ, and it arrives on the same turn.
    $changeLog.Add("### Map placement")
    $pp = Kid $D.root 'plat_pos'
    $posByUid = @{}; foreach ($r in $pp.rows) { $posByUid[[uint32]$r.c[0].v[0]] = $r }
    function S32([uint32]$x) { [BitConverter]::ToInt32([BitConverter]::GetBytes($x), 0) }   # array cells hold signed values as uint32
    function Placed-HqRow([string]$formName) {
        foreach ($p in $act.kids) {
            if ((Pool $p) -eq $formName -and (Code $p) -eq 0 -and -not (IsBg $p)) {
                $r = $posByUid[[uint32](FU $p 'uid')]
                if ($r -and (S32 $r.c[0].v[3]) -ne -1) { return $r }
            }
        }
        $null
    }
    # No vanilla operation puts two units on one map node (checked: 17 July NA, 30 July, Saur-Mogila), so a new HQ takes a
    # free node next to its anchor: a node linked to the anchor's node in the same cell, else any free node of the cell,
    # else a linked node of a neighbouring cell. mg_nodes row: col 0 = a:cell x; cell z; ..., col 1 = a:side; mg_links
    # row: a:from; to; ...
    $mgNodes = Kid $D.root 'mg_nodes'; $mgLinks = Kid $D.root 'mg_links'
    $nodeTaken = @{}; foreach ($r in $pp.rows) { $n = S32 $r.c[0].v[3]; if ($n -ne -1) { $nodeTaken[$n] = 1 } }
    function Node-Cell([int]$n) { $r = $mgNodes.rows[$n]; @{ px = (S32 $r.c[0].v[0]); pz = (S32 $r.c[0].v[1]); side = [uint32]$r.c[1].v[0] } }
    function Free-Node([int]$anchorNode) {
        if (-not $nodeTaken.ContainsKey($anchorNode)) { return $anchorNode }
        $a = Node-Cell $anchorNode
        $linked = @(); foreach ($r in $mgLinks.rows) { $f = S32 $r.c[0].v[0]; $t = S32 $r.c[0].v[1]; if ($f -eq $anchorNode) { $linked += $t } elseif ($t -eq $anchorNode) { $linked += $f } }
        foreach ($n in $linked) { if ($nodeTaken.ContainsKey($n)) { continue }; $c = Node-Cell $n; if ($c.px -eq $a.px -and $c.pz -eq $a.pz -and $c.side -eq $a.side) { return $n } }
        for ($n = 0; $n -lt $mgNodes.rows.Count; $n++) { if ($nodeTaken.ContainsKey($n)) { continue }; $c = Node-Cell $n; if ($c.px -eq $a.px -and $c.pz -eq $a.pz -and $c.side -eq $a.side) { return $n } }
        foreach ($n in $linked) { if ($nodeTaken.ContainsKey($n)) { continue }; $c = Node-Cell $n; if ($c.side -eq $a.side) { return $n } }
        # breadth-first over the link graph (up to 4 hops) for any free node of the same side
        $seen = @{ $anchorNode = 1 }; $frontier = @($linked); foreach ($n in $linked) { $seen[$n] = 1 }
        for ($hop = 0; $hop -lt 4; $hop++) {
            $next = @()
            foreach ($f0 in $frontier) {
                foreach ($r in $mgLinks.rows) {
                    $f = S32 $r.c[0].v[0]; $t = S32 $r.c[0].v[1]; $o = -1
                    if ($f -eq $f0) { $o = $t } elseif ($t -eq $f0) { $o = $f }
                    if ($o -lt 0 -or $seen.ContainsKey($o)) { continue }
                    $seen[$o] = 1; $next += $o
                    if (-not $nodeTaken.ContainsKey($o) -and ((Node-Cell $o).side -eq $a.side)) { return $o }
                }
            }
            $frontier = $next; if (-not $frontier.Count) { break }
        }
        -1
    }
    $placedHq = 0
    foreach ($mp in $M) {
        if (-not $mp.create) { continue }
        $hqNode = $null; foreach ($p in $act.kids) { if ((Pool $p) -eq $mp.form -and (Code $p) -eq 0 -and -not (IsBg $p)) { $hqNode = $p; break } }
        if (-not $hqNode) { Write-Warning "$side : $($mp.form) has no HQ node to place"; continue }
        $anchor = Placed-HqRow $mp.create.parent; $anchorName = $mp.create.parent
        if (-not $anchor) { foreach ($f in $res.kids) { if ((FS $f 'parent') -eq $mp.create.parent -and $f.name -ne $mp.form) { $anchor = Placed-HqRow $f.name; if ($anchor) { $anchorName = $f.name; break } } } }
        if (-not $anchor) { Write-Warning "$side : no placed HQ to anchor $($mp.form)"; continue }
        $turn = S32 $anchor.c[1].v[0]
        $mn = Free-Node (S32 $anchor.c[0].v[3])
        if ($mn -lt 0) { Write-Warning "$side : no free map node near the HQ of $anchorName for $($mp.form)"; continue }
        $cell = Node-Cell $mn; $px = $cell.px; $pz = $cell.pz; $nodeTaken[$mn] = 1
        $uid = [uint32](FU $hqNode 'uid')
        $row = @{ name = $null; c = @((Cell-Decode "a:$uid;$px;$pz;$mn"), (Cell-Decode "a:$turn")) }
        if ($posByUid.ContainsKey($uid)) { $pp.rows[$pp.rows.IndexOf($posByUid[$uid])] = $row } else { $pp.rows.Add($row) }
        $posByUid[$uid] = $row; $placedHq++
        $changeLog.Add("- ``$($hqNode.name)`` placed next to the HQ of $anchorName (cell $px;$pz, own map node $mn, turn $turn)")
    }
    $posAdded = 0
    foreach ($p in $act.kids) {
        $uid = [uint32](FU $p 'uid')
        if (-not $posByUid.ContainsKey($uid)) { $row = @{ name = $null; c = @((Cell-Decode "a:$uid;-1;-1;-1"), (Cell-Decode 'a:1')) }; $pp.rows.Add($row); $posByUid[$uid] = $row; $posAdded++ }
    }
    $changeLog.Add("- $posAdded reserve placement rows added (one per new platoon)")
    # mg_nodes column 2 element 0 = uid of the unit standing on the node (-1 if none); every vanilla file mirrors
    # plat_pos there and the engine looks units up by it (crash on a mismatch, found in the Saur-Mogila work, 0.5.7)
    $occ = @{}; foreach ($r in $pp.rows) { $n = S32 $r.c[0].v[3]; if ($n -ne -1) { $occ[$n] = [uint32]$r.c[0].v[0] } }
    $synced = 0
    for ($n = 0; $n -lt $mgNodes.rows.Count; $n++) {
        $c2 = $mgNodes.rows[$n].c[2]; $want = $(if ($occ.ContainsKey($n)) { $occ[$n] } else { [uint32]4294967295 })
        if ([uint32]$c2.v[0] -ne $want) { $c2.v[0] = $want; $synced++ }
    }
    $changeLog.Add("- mg_nodes occupants synced with plat_pos: $synced nodes changed")

    # ---------------- pass 3b (0.5.13, user): "move 2 tank coy, 2 tank platoon to 2/22 det gds TR in place of 4 tank
    # coy, 1 tank platoon and move it to reserve": the 22 Gds TR 2nd group gets the 2nd company's 2nd platoon in the
    # STR slot that held the 4th company's platoon (now reserve); the group that held the 2nd platoon gets another
    # platoon of its own company or an empty slot
    $swaps = @(@{ bg = 'ra_22stp_bg2'; out = 'ra_22stp_4c'; in = 'ra_22stp_2c_2p' })
    foreach ($sw in $swaps) {
        $bgN = $byName[$sw.bg]; $inN = $byName[$sw.in]; if (-not $bgN -or -not $inN) { Write-Warning "$side : swap $($sw.bg): node missing"; continue }
        $sl = Kid $bgN 'slots'; $done = $false
        foreach ($r in $sl.rows) { if ($r.c[0].s -eq $sw.out) { $r.c[0] = Cell-Decode "s:$($sw.in)"; $used.Remove($sw.out); $used[$sw.in] = 1; $done = $true; $changeLog.Add("- ``$($sw.bg)``: ``$($sw.out)`` -> reserve, ``$($sw.in)`` in its slot") } }
        if (-not $done) { Write-Warning "$side : $($sw.out) not in $($sw.bg)"; continue }
        # the slot the incoming platoon leaves in another group: refilled from the companies the other platoons of that group belong to
        foreach ($b0 in $act.kids) {
            if ($b0.name -eq $sw.bg -or -not (IsBg $b0)) { continue }
            $s0 = Kid $b0 'slots'; if (-not $s0) { continue }
            foreach ($r0 in $s0.rows) {
                if ($r0.c[0].s -ne $sw.in) { continue }
                $r0.c[0] = Cell-Decode 's:'
                $coys = @(); foreach ($r1 in $s0.rows) { $n1 = $r1.c[0].s; if ($n1 -and $coyOf.ContainsKey($n1) -and $coys -notcontains $coyOf[$n1]) { $coys += $coyOf[$n1] } }
                $repl = $(if ($coys.Count) { PickCoy $coys 'STR' } else { $null })
                if ($repl) { $r0.c[0] = Cell-Decode "s:$($repl.name)"; $used[$repl.name] = 1 }
                $changeLog.Add("- ``$($b0.name)``: ``$($sw.in)`` taken out, slot now ``$($r0.c[0].s)``")
            }
        }
    }

    # ---------------- text packs: vanilla keys + copied ones
    foreach ($l in 'eng', 'rus') {
        $keys = New-Object Collections.Generic.List[object]
        foreach ($k in $naText[$l].keys) { $keys.Add(@{ key = $k.key; items = @($k.items) }) }
        foreach ($e in $needKeys.GetEnumerator()) {
            $src = $tTextIdx[$l][$e.Value.src]
            if (-not $src) { $src = $tTextIdx.eng[$e.Value.src] }
            $items = @($src.items | ForEach-Object { $s = [string]$_; if ($e.Value.sub) { foreach ($kv in $e.Value.sub.GetEnumerator()) { $s = $s.Replace($kv.Key, $kv.Value) } }; $s })
            $keys.Add(@{ key = $e.Key; items = $items })
        }
        $outDir = Join-Path $outRoot $op
        New-Item -ItemType Directory -Force $outDir | Out-Null
        Write-Aztx (Join-Path $outDir "text.text.loc_$l.bin") "loc_$l" $keys.ToArray()
    }
    # ---------------- desc: save, diff against vanilla, write the delta
    $genDir = Join-Path $Work "gen\$op"; New-Item -ItemType Directory -Force $genDir | Out-Null
    $gen = Join-Path $genDir 'desc.config.loc_def.bin'
    Azcf-Save $D $gen | Out-Null
    $outDir = Join-Path $outRoot $op
    $delta = Join-Path $outDir 'desc.config.loc_def.01_oob.delta'
    $r = Cmd-Diff (Join-Path $vDir 'desc.config.loc_def.bin') $gen $delta
    $lines = [IO.File]::ReadAllLines($delta)
    $hdr = @("# MF Overhaul 0.5.2 M2: OOB of 17 July 1943 brought to the 30 July 1943 standard; generated by tools\oob_17jul.ps1",
             "# $added platoons added, $merged compositions changed, $skipped 30 July platoons skipped (vehicles already present / no free code), $splitCount tank/SPG companies split, $slotFills battle-group slots filled. See docs\oob_stepanowka_17jul.md")
    [IO.File]::WriteAllLines($delta, [string[]]($hdr + $lines), (New-Object Text.UTF8Encoding $false))
    [IO.File]::WriteAllLines((Join-Path $outDir '!flatlist'), [string[]]@('i_unflat:unflat()', '{', "`tdesc                          , config          , loc_def ;", "`ttext                          , text            , loc_eng ;", "`ttext                          , text            , loc_rus ;", '}'), [Text.Encoding]::ASCII)
    "$op : $added added, $merged merged, $skipped skipped, $splitCount companies split, $slotAdds STR slots added, $slotFills slots filled, $($needKeys.Count) text keys copied; $r"
}
[IO.File]::WriteAllLines((Join-Path $repo 'docs\oob_stepanowka_17jul_changes.md'), [string[]](@('# Generated change list (tools\oob_17jul.ps1)', '', 'One line per platoon: NEW = added to the formation reserve; MOVED = re-pooled into a new artillery regiment formation; otherwise a composition change, a company split or a battle-group slot change.') + $changeLog), (New-Object Text.UTF8Encoding $false))
"change list: docs\oob_stepanowka_17jul_changes.md"
