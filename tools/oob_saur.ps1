<#
.SYNOPSIS
  MF Overhaul M2: bring "Saur-Mogila tumulus, 28 August 1943" (08_28_Saur_RUS / _GER, 2015 format: every platoon placed
  on its own, no battle groups) to the battle-group system of the current operations, with the 34th Guards Rifle
  Division copied from "Stepanovka, 30 July 1943" (07_30_Stepanovka_RUS).

.DESCRIPTION
  Per side (the RUS and GER files differ only in campgen and the ai fields):
  1. 34 Gds RD: the old 103/105/107 Gds RR formations and their 37 platoons are removed; the 30 July formations
     p_ra_103rr, p_ra_105rr, p_ra_107rr, p_ra_84ar (structs) and every 30 July platoon of p_ra_34rd / 103rr / 105rr /
     107rr / 84ar (305 nodes: division HQ, recon, training bn, sappers, AT bn, three regiments with two battle groups
     each, the artillery regiment) are copied verbatim (names, codes, uids, compositions, 30 July strengths), ai from
     the side file. Slot references to formations that are not in this operation (665 destr bn, 16 mortar) are cleared
     and refilled from the operation (9 iptabr batteries as SUP, 84 AR FO teams / own FO as SCT, 30 July pattern).
     Map placement (plat_pos): regiment HQ at the old regiment HQ node, 1st battle group at the old first company
     command's node, 2nd battle group at the old battalion command's node, division HQ and 84 AR HQ at the old
     105 Gds RR HQ node (rear), everything else in reserve.
  2. Every other formation (60 Gds TPP, 7 Gds OTPP, 9 iptabr, 140 STBde, 293 Gds RR, 306 ID, 581/570 IR, 294 ID, 514 IR,
     335 ID): each company that had placed platoons becomes one battle group (COM = company command, UNI/STR/SUP/SUPM
     slots = its platoons) placed at the company command's node; tank companies without a company command become a
     battle group with an empty COM slot (as ra_22stp_bg2 in the 17 July file); standalone placed units without a
     company (HQ, depot, supply, StuG battery, Marder company, AT platoon) keep their own placement.
  3. campgen features 0x2000008 -> 0x200000B (the current-format flags of the 17 July NA and 30 July files).
  4. Text packs: vanilla keys + the 30 July keys the copied nodes use.
  Output: src\m2_oob\camps\1943_08_Mius\<op>\ desc.config.loc_def.01_oob.delta, text.text.loc_eng/rus.bin, !flatlist;
  docs\oob_saur_mogila_changes.md.

.EXAMPLE
  tools\oob_saur.ps1          # needs GTMF_ROOT
#>
param(
    [string]$GameRoot = $env:GTMF_ROOT,
    [string]$Work = '',
    [string[]]$Sides = @('RUS', 'GER')
)
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'gt3.ps1') lib
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
if (-not $GameRoot) { throw 'set GTMF_ROOT or pass -GameRoot (folder with starter_x64.exe)' }
if (-not $Work) { $Work = Join-Path $repo 'build\oob17' }
$ops = @{ RUS = '08_28_Saur_RUS'; GER = '08_28_Saur_GER' }
$chapter = '1943_08_Mius'
$tplOp = '07_30_Stepanovka_RUS'; $tplChapter = '1943_07_Mius'
$outRoot = Join-Path $repo "src\m2_oob\camps\$chapter"
$globalText = Join-Path $GameRoot 'users\modwork\_orig\3598\text_loc'
$copyForms = @('p_ra_34rd', 'p_ra_103rr', 'p_ra_105rr', 'p_ra_107rr', 'p_ra_84ar', 'p_ra_293rr')   # 30 July formations copied
# old Saur formation -> 30 July formation replacing it (0.5.10: 293 Gds RR too, user: "two battle groups, 1st bn with
# companies 1-3 and 2nd bn with 4-6, with their organic regimental and battalion support units")
$oldRegs = @{ 'p_ra_103gds_rr' = 'p_ra_103rr'; 'p_ra_105gds_rr' = 'p_ra_105rr'; 'p_ra_107gds_rr' = 'p_ra_107rr'; 'p_ra_293gds_rr' = 'p_ra_293rr' }

# ---------------------------------------------------------------- helpers (as in oob_17jul.ps1)
function Unpack-Op([string]$chap, [string]$op) {
    $dir = Join-Path $Work "vanilla\$op"
    if (-not (Test-Path (Join-Path $dir 'desc.config.loc_def.bin'))) {
        New-Item -ItemType Directory -Force $dir | Out-Null
        Cmd-Unpack (Join-Path $GameRoot "data\oprum\shared\camps\$chap\$op.campack2") $dir | Out-Null
    }
    $dir
}
function Fld([object]$node, [string]$name) { foreach ($r in $node.rows) { if ($r.name -eq $name) { return $r } }; $null }
function FV([object]$node, [string]$name) { $r = Fld $node $name; if ($r) { Cell-Encode $r.c[0] } else { '' } }
function FS([object]$node, [string]$name) { $r = Fld $node $name; if ($r -and $r.c[0].k -eq 2) { $r.c[0].s } else { '' } }
function FU([object]$node, [string]$name) { $r = Fld $node $name; if ($r) { [uint32]$r.c[0].v[0] } else { 0 } }
function SetF([object]$node, [string]$name, [string]$text) { $r = Fld $node $name; if (-not $r) { throw "no field $name in $($node.name)" }; $r.c[0] = Cell-Decode $text }
function Fcc([object]$node, [string]$name) { $v = FV $node $name; if ($v -match "^u:'(.+)'$") { $Matches[1] } else { $v -replace '^u:', '' } }
function Fcc-Row([object]$row) { $v = Cell-Encode $row.c[1]; if ($v -match "^u:'(.+)'$") { $Matches[1] } else { $v -replace '^u:', '' } }
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
function S32([uint32]$x) { [BitConverter]::ToInt32([BitConverter]::GetBytes($x), 0) }
function Read-Text([string]$path) { Read-Aztx ([IO.File]::ReadAllBytes($path)) }
function Write-Aztx([string]$path, [string]$loc, [object[]]$keys) {
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
function PosRow([uint32]$uid, [int]$px, [int]$pz, [int]$node, [int]$turn) { @{ name = $null; c = @((Cell-Decode "a:$uid;$px;$pz;$node"), (Cell-Decode "a:$turn")) } }
function AddSlot([object]$sl, [string]$role, [string]$ref) { $sl.rows.Add(@{ name = $null; c = @((Cell-Decode "s:$ref"), (Cell-Decode "u:'$role'")) }) | Out-Null }

# ---------------------------------------------------------------- template (30 July)
$tplDir = Unpack-Op $tplChapter $tplOp
$T = Azcf-Load (Join-Path $tplDir 'desc.config.loc_def.bin')
$tAct = Kid $T.root 'act_platoons'; $tRes = Kid $T.root 'reserves'
$tText = @{ eng = Read-Text (Join-Path $tplDir 'text.text.loc_eng.bin'); rus = Read-Text (Join-Path $tplDir 'text.text.loc_rus.bin') }
$tTextIdx = @{ eng = @{}; rus = @{} }
foreach ($l in 'eng', 'rus') { foreach ($k in $tText[$l].keys) { $tTextIdx[$l][$k.key] = $k } }
$gKeys = @{}
foreach ($f in Get-ChildItem $globalText -Filter '*.text.loc_eng.bin') { foreach ($k in (Read-Text $f.FullName).keys) { $gKeys[$k.key] = 1 } }
$tplBg = @{ USSR = ($tAct.kids | Where-Object { $_.name -eq 'ra_103_1' }); GER = ($tAct.kids | Where-Object { $_.name -eq 'we_513_1b' }) }
$tplBgTank = @{ USSR = ($tAct.kids | Where-Object { $_.name -eq 'ra_32tbde_1' }); GER = ($tAct.kids | Where-Object { $_.name -eq 'we_tk_stug_1' }) }

$changeLog = New-Object Collections.Generic.List[string]
foreach ($side in $Sides) {
    $op = $ops[$side]
    $vDir = Unpack-Op $chapter $op
    $D = Azcf-Load (Join-Path $vDir 'desc.config.loc_def.bin')
    $act = Kid $D.root 'act_platoons'; $res = Kid $D.root 'reserves'; $pp = Kid $D.root 'plat_pos'; $cg = $D.root.kids[0]
    $byName = @{}; $uids = @{}
    foreach ($p in $act.kids) { $byName[$p.name] = $p; $uids[[uint32](FU $p 'uid')] = 1 }
    $posByUid = @{}; foreach ($r in $pp.rows) { $posByUid[[uint32]$r.c[0].v[0]] = $r }
    function PosOf([object]$p) { $r = $posByUid[[uint32](FU $p 'uid')]; if ($r) { @{ px = (S32 $r.c[0].v[1]); pz = (S32 $r.c[0].v[2]); node = (S32 $r.c[0].v[3]); turn = (S32 $r.c[1].v[0]) } } else { $null } }
    function Placed([object]$p) { $q = PosOf $p; ($q -and $q.node -ne -1) }
    # No vanilla operation puts two units on one map node, so every placement takes a free node: the wanted node if free,
    # else a free node linked to it in the same cell, else any free node of the cell, else a linked node next door.
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
    function SetPos([object]$p, [int]$px, [int]$pz, [int]$node, [int]$turn) {
        $uid = [uint32](FU $p 'uid')
        $old = $posByUid[$uid]; if ($old) { $on = S32 $old.c[0].v[3]; if ($on -ne -1) { $nodeTaken.Remove($on) } }
        if ($node -ne -1) {
            $node = Free-Node $node
            if ($node -lt 0) { Write-Warning "$side : no free map node for $($p.name) near cell $px;$pz"; $node = -1; $px = -1; $pz = -1 }
            else { $c = Node-Cell $node; $px = $c.px; $pz = $c.pz; $nodeTaken[$node] = 1 }
        }
        $row = PosRow $uid $px $pz $node $turn
        if ($old) { $pp.rows[$pp.rows.IndexOf($old)] = $row } else { $pp.rows.Add($row) }
        $posByUid[$uid] = $row
    }
    $naText = @{ eng = Read-Text (Join-Path $vDir 'text.text.loc_eng.bin'); rus = Read-Text (Join-Path $vDir 'text.text.loc_rus.bin') }
    $naKeys = @{}; foreach ($k in $naText.eng.keys) { $naKeys[$k.key] = 1 }
    $needKeys = New-Object Collections.Specialized.OrderedDictionary
    function Need-Key([string]$key) {
        if ($key -and -not $gKeys.ContainsKey($key) -and -not $naKeys.ContainsKey($key) -and -not $needKeys.Contains($key)) {
            if ($tTextIdx.eng.ContainsKey($key)) { $needKeys[$key] = @{ src = $key; sub = $null } } else { Write-Warning "$side : text key $key exists nowhere" }
        }
        $key
    }
    function Need-KeySub([string]$newKey, [string]$srcKey, [hashtable]$sub) {
        # a new key whose text is the 30 July text of $srcKey with substitutions (e.g. "1/103" -> "3/103")
        if (-not $gKeys.ContainsKey($newKey) -and -not $naKeys.ContainsKey($newKey) -and -not $needKeys.Contains($newKey)) {
            if ($tTextIdx.eng.ContainsKey($srcKey)) { $needKeys[$newKey] = @{ src = $srcKey; sub = $sub } } else { Write-Warning "$side : text key $srcKey exists nowhere" }
        }
        $newKey
    }
    function New-Uid([uint32]$hi, [int]$code) { $uid = ($hi -shl 12) -bor [uint32]$code; while ($uids.ContainsKey($uid)) { $uid += 0x1000 }; $uids[$uid] = 1; $uid }
    $changeLog.Add(""); $changeLog.Add("## $op"); $changeLog.Add("")

    # ---------------- 1. the 34 Gds RD block from 30 July
    $changeLog.Add("### 34 Gds RD: 30 July structure")
    # remember the old regiments' placements (hq, first company command, battalion command)
    $anchors = @{}; $oldStructIdx = @{}; $oldNodeIdx = @{}
    foreach ($old in $oldRegs.Keys) {
        $nodes = @($act.kids | Where-Object { (Pool $_) -eq $old })
        $hq = $nodes | Where-Object { (Code $_) -eq 0 } | Select-Object -First 1
        $oldStructIdx[$oldRegs[$old]] = $res.kids.IndexOf((Kid $res $old)); $oldNodeIdx[$oldRegs[$old]] = $(if ($hq) { $act.kids.IndexOf($hq) } else { $act.kids.IndexOf($nodes[0]) })
        $coms = @($nodes | Where-Object { (Real $_) -eq 'COMC' -and (Placed $_) } | Sort-Object { Code $_ })
        $bns = @($nodes | Where-Object { (Real $_) -eq 'COM' -and (Placed $_) } | Sort-Object { Code $_ })
        $a = @{ hq = (PosOf $hq); bg1 = $null; bg2 = $null }
        if ($coms.Count) { $a.bg1 = PosOf $coms[0] }
        if ($bns.Count) { $a.bg2 = PosOf $bns[0] } elseif ($coms.Count -gt 1) { $a.bg2 = PosOf $coms[1] }
        if (-not $a.bg1) { $a.bg1 = $a.hq }; if (-not $a.bg2) { $a.bg2 = $a.hq }
        $anchors[$oldRegs[$old]] = $a
        $aiOld = Clone-Cell (Fld (Kid $res $old) 'ai').c[0]
        $anchors["$($oldRegs[$old])_ai"] = $aiOld
        $changeLog.Add("- old $old removed: $($nodes.Count) platoons (HQ at node $($a.hq.node), 1st coy at $($a.bg1.node), bn cmd at $($a.bg2.node))")
        foreach ($n in $nodes) { $act.kids.Remove($n) | Out-Null; $byName.Remove($n.name); $u = [uint32](FU $n 'uid'); if ($posByUid.ContainsKey($u)) { $on = S32 $posByUid[$u].c[0].v[3]; if ($on -ne -1) { $nodeTaken.Remove($on) }; $pp.rows.Remove($posByUid[$u]) | Out-Null; $posByUid.Remove($u) } }
        $res.kids.Remove((Kid $res $old)) | Out-Null
    }
    $divForm = Kid $res 'p_ra_34rd'; $divAi = Clone-Cell (Fld $divForm 'ai').c[0]
    $rear = $anchors['p_ra_105rr'].hq
    # formation structs after p_ra_34rd (keep the old division struct; its name key exists in this pack)
    $at = $res.kids.IndexOf($divForm) + 1
    foreach ($fn in 'p_ra_103rr', 'p_ra_105rr', 'p_ra_107rr', 'p_ra_84ar', 'p_ra_293rr') {
        $f = Clone-Node (Kid $tRes $fn); $f.kids.Clear()
        $ai = $(if ($anchors.ContainsKey("${fn}_ai")) { $anchors["${fn}_ai"] } else { $divAi })
        (Fld $f 'ai').c[0] = Clone-Cell $ai
        Need-Key (FS $f 'name') | Out-Null
        if ($fn -eq 'p_ra_293rr') { $res.kids.Insert([Math]::Min($oldStructIdx[$fn], $res.kids.Count), $f) }   # where the old 293 struct stood (under 96 Gds RD)
        else { $res.kids.Insert($at, $f); $at++ }
        $changeLog.Add("- formation $fn (code $(FU $f 'code'), parent $(FS $f 'parent'), ai $(Fcc $f 'ai'))")
    }
    # platoons: the 34 Gds RD block after the last old p_ra_34rd-tree node (the 60 TPP / 7 OTPP stay where they are),
    # the 293 Gds RR block where the old 293 nodes stood
    $lastIdx = -1; for ($i = 0; $i -lt $act.kids.Count; $i++) { if ((Pool $act.kids[$i]) -match '^p_ra_(34rd|60gds_tpp|7gds_stpp)$') { $lastIdx = $i } }
    if ($lastIdx -lt 0) { $lastIdx = $act.kids.Count - 1 }
    $idx293 = [Math]::Min($oldNodeIdx['p_ra_293rr'], $act.kids.Count) - 1
    $copied = New-Object Collections.Generic.List[object]
    foreach ($t in $tAct.kids) {
        if ($copyForms -notcontains (Pool $t)) { continue }
        $c = Clone-Node $t
        $form = Pool $c
        $ai = $(if ($anchors.ContainsKey("${form}_ai")) { $anchors["${form}_ai"] } else { $divAi })
        (Fld $c 'ai').c[0] = Clone-Cell $ai
        $u = [uint32](FU $c 'uid'); if ($uids.ContainsKey($u)) { $u = New-Uid ($u -shr 12) (Code $c); SetF $c 'uid' "u:$u" } else { $uids[$u] = 1 }
        $x = 2; $base = $c.name; while ($byName.ContainsKey($c.name)) { $c.name = "${base}_$x"; $x++ }
        Need-Key (FS $c 'name') | Out-Null
        if ($form -eq 'p_ra_293rr') { $idx293++; $act.kids.Insert($idx293, $c); if ($idx293 -le $lastIdx) { $lastIdx++ } }
        else { $act.kids.Insert($lastIdx + 1, $c); $lastIdx++; if ($lastIdx -le $idx293) { $idx293++ } }
        $byName[$c.name] = $c; $copied.Add($c)
    }
    $changeLog.Add("- $($copied.Count) platoons copied from 30 July (p_ra_34rd division troops, 103/105/107 Gds RR, 84 Gds AR, 293 Gds RR), 30 July compositions and strengths")
    # user: 293 Gds RR with two battle groups (1st and 2nd bn); the 30 July regiment has a third one for the 3rd bn -> dropped
    $bg3 = $byName['ra_293_3']
    if ($bg3) { $act.kids.Remove($bg3) | Out-Null; $byName.Remove('ra_293_3'); $copied.Remove($bg3) | Out-Null; $u3 = [uint32](FU $bg3 'uid'); if ($posByUid.ContainsKey($u3)) { $pp.rows.Remove($posByUid[$u3]) | Out-Null; $posByUid.Remove($u3) }; $changeLog.Add("- ``ra_293_3`` (3rd bn battle group of the 30 July regiment) dropped: the user asked for two groups") }
    # battle groups: pool4 (the 1 Gds destroyer bde) -> 9 iptabr; reserve links to formations not in this operation
    # cleared; slot refs to units not in this operation cleared
    $used = @{}
    foreach ($p in $act.kids) { if (IsBg $p) { $sl = Kid $p 'slots'; if ($sl) { foreach ($r in $sl.rows) { if ($r.c[0].s -and $byName.ContainsKey($r.c[0].s)) { $used[$r.c[0].s] = 1 } } } } }
    $formSet = @{}; foreach ($f in $res.kids) { $formSet[$f.name] = 1 }
    foreach ($bg in $copied) {
        if (-not (IsBg $bg)) { continue }
        if ((FS $bg 'pool4') -eq 'p_ra_1destr') { SetF $bg 'pool4' 's:p_ra_9_iptabr' }
        foreach ($pf in 'pool2', 'pool3', 'pool4') { $v = FS $bg $pf; if ($v -and -not $formSet.ContainsKey($v)) { SetF $bg $pf 's:'; $changeLog.Add("- ``$($bg.name)``: reserve link $pf ``$v`` not in this operation, cleared") } }
        $sl = Kid $bg 'slots'
        foreach ($r in $sl.rows) { if ($r.c[0].s -and -not $byName.ContainsKey($r.c[0].s)) { $changeLog.Add("- ``$($bg.name)``: slot $(Fcc-Row $r) ``$($r.c[0].s)`` not in this operation, cleared"); $r.c[0] = Cell-Decode 's:' } }
    }
    function Pick([string]$form, [string[]]$roles, [string]$sprPref) {
        $cands = @($act.kids | Where-Object { (Pool $_) -eq $form -and -not (IsBg $_) -and (Code $_) -ne 0 -and $roles -contains (Real $_) -and -not $used.ContainsKey($_.name) })
        if (-not $cands.Count) { return $null }
        @($cands | Sort-Object { $(if ($sprPref -and (Spr $_) -match $sprPref) { 0 } else { 1 }) }, { Code $_ })[0]
    }
    # user (0.5.8): a third battle group (3rd battalion, 7th company) for 103 and 105 Gds RR, like the 30 July 1st/2nd
    foreach ($reg in '103', '105') {
        $form = "p_ra_${reg}rr"; $bg2 = $byName["ra_${reg}_2"]; $com = $byName["ra_${reg}_7c_com"]
        if (-not $bg2 -or -not $com) { Write-Warning "$side : no 3rd battle group for $reg (bg2 or 7c_com missing)"; continue }
        $bg = Clone-Node $bg2; $bg.name = "ra_${reg}_3"
        SetF $bg 'code' 'u:3843'; SetF $bg 'uid' "u:$(New-Uid ([uint32]((FU $bg2 'uid') -shr 12)) 0xF03)"
        SetF $bg 'name' "s:$(Need-KeySub "op_ra_${reg}_3b" "op_ra_${reg}_1b" @{ "1/$reg" = "3/$reg" })"
        $sl = Kid $bg 'slots'; $sl.rows.Clear()
        AddSlot $sl 'COM' $com.name; $used[$com.name] = 1
        AddSlot $sl 'SCT' ''
        foreach ($k in 1, 2, 3) { $u = $byName["ra_${reg}_7c_${k}p"]; if ($u -and -not $used.ContainsKey($u.name)) { AddSlot $sl 'UNI' $u.name; $used[$u.name] = 1 } }
        AddSlot $sl 'SUP' ''; AddSlot $sl 'SUP' ''
        $act.kids.Insert($act.kids.IndexOf($bg2) + 1, $bg); $byName[$bg.name] = $bg; $copied.Add($bg)
        $changeLog.Add("- ``$($bg.name)`` NEW battle group (3rd bn): " + (($sl.rows | ForEach-Object { "$(Fcc-Row $_)=$($_.c[0].s)" }) -join ' '))
    }
    $nth = @{}
    foreach ($bg in $copied) {
        if (-not (IsBg $bg)) { continue }
        $form = Pool $bg; if (-not $nth.ContainsKey($form)) { $nth[$form] = 0 }; $nth[$form]++
        $sl = Kid $bg 'slots'
        foreach ($r in $sl.rows) {
            if ($r.c[0].s) { continue }
            $role = Fcc-Row $r; $pick = $null
            switch ($role) {
                'SCT' { $arF = $null; $parF = FS (Kid $res $form) 'parent'; foreach ($f in $res.kids) { if ((FS $f 'parent') -eq $parF -and $f.name -match 'ar$') { $arF = $f.name; break } }; if ($nth[$form] % 2 -eq 1 -and $arF) { $pick = Pick $arF @('CTRL') $null }; if (-not $pick) { $pick = Pick $form @('CTRL') $null }; if (-not $pick) { $pick = Pick $form @('SCT') $null } }
                'SUP' { $pick = Pick 'p_ra_9_iptabr' @('SUP') 'zis3'; if (-not $pick) { $pick = Pick $form @('SUP') 'mortars' } }
                'UNI' { $pick = Pick $form @('UNI') 'rifles' }
            }
            if ($pick) { $r.c[0] = Cell-Decode "s:$($pick.name)"; $used[$pick.name] = 1; SetPos $pick -1 -1 -1 1; $changeLog.Add("- ``$($bg.name)``: $role slot <- ``$($pick.name)`` (its own placement removed: it deploys with the group)") }
        }
    }
    # placement of the copied block
    foreach ($p in $copied) {
        $form = Pool $p; $q = $null
        if ((Code $p) -eq 0 -and -not (IsBg $p)) { $q = $(if ($anchors.ContainsKey($form)) { $anchors[$form].hq } else { $rear }) }
        elseif (IsBg $p) { $q = $(if ((Code $p) -eq 0xF01) { $anchors[$form].bg1 } elseif ((Code $p) -eq 0xF02) { $anchors[$form].bg2 } else { $anchors[$form].hq }) }   # 3rd group: a free node in the HQ cell
        if ($q) { SetPos $p $q.px $q.pz $q.node 1; $np = PosOf $p; $changeLog.Add("- ``$($p.name)`` placed: cell $($np.px);$($np.pz) node $($np.node) (wanted $($q.node))") }
        else { SetPos $p -1 -1 -1 1 }
    }
    # (0.5.13, user, from two map screenshots with a white X) the 3rd-battalion groups move forward: 3/105 to the
    # south-centre node of cell 3;5 (between 1/105 and 2/105), 3/103 to the south-east node of cell 2;5 (between
    # 1/103 and 2/103); both nodes are free Soviet-side nodes
    $manualPos = @{ 'ra_105_3' = 65; 'ra_103_3' = 115 }
    foreach ($mn in $manualPos.Keys) {
        $p = $byName[$mn]; if (-not $p) { continue }
        $cell = Node-Cell $manualPos[$mn]
        SetPos $p $cell.px $cell.pz $manualPos[$mn] 1; $np = PosOf $p
        $changeLog.Add("- ``$mn`` moved to node $($np.node) (cell $($np.px);$($np.pz)) at the user's map mark")
    }

    # ---------------- 2. battle groups for the other formations
    $changeLog.Add("### Battle groups for the other formations")
    $bgCount = 0
    $forms = @($res.kids | ForEach-Object { $_.name })
    foreach ($fn in $forms) {
        if ($copyForms -contains $fn) { continue }
        $nodes = @($act.kids | Where-Object { (Pool $_) -eq $fn -and -not (IsBg $_) })
        if (-not $nodes.Count) { continue }
        $sideCc = Fcc $nodes[0] 'side'
        $hqNode = $nodes | Where-Object { (Code $_) -eq 0 } | Select-Object -First 1
        if (-not $hqNode) {
            # every vanilla battle group belongs to a formation with an HQ node (code 0); 0.5.5 built groups for 60 Gds TPP,
            # 210 StuG bn and 335 ID, which have none, and the engine crashed on an index -1 while scanning the platoons.
            # Such formations keep their old single-unit placements.
            $changeLog.Add("- $fn has no HQ node: no battle group, its units keep their own placement"); continue
        }
        $hi = [uint32]((FU $hqNode 'uid') -shr 12)
        $groups = @{}
        foreach ($n in $nodes) { $c = Code $n; if ($c -eq 0) { continue }; $g = $c -band 0xFF0; if (-not $groups.ContainsKey($g)) { $groups[$g] = @() }; $groups[$g] += $n }
        $bgN = 0
        $tankOnly = New-Object Collections.Generic.List[object]
        foreach ($g in ($groups.Keys | Sort-Object)) {
            $members = @($groups[$g] | Sort-Object { Code $_ })
            $com = $members | Where-Object { (Real $_) -eq 'COMC' -and (Code $_) -eq $g } | Select-Object -First 1
            $placedMembers = @($members | Where-Object { Placed $_ })
            if (-not $placedMembers.Count) { continue }
            if (-not $com) {
                # no company command: tank/SPG companies of this formation gather in one battle group later; others stay standalone
                foreach ($m in $placedMembers) { if ((Real $m) -in 'STR', 'SUPM' -and (Kid $m 'pool') -and (Kid $m 'pool').rows.Count -ge 2) { $tankOnly.Add($m) } }
                continue
            }
            $isTank = (Real $com) -eq 'COMC' -and (Spr $com) -match '^pl_'
            $tpl = $(if ($isTank) { $tplBgTank[$sideCc] } else { $tplBg[$sideCc] })
            $bgN++; $bg = Clone-Node $tpl; $bg.kids.Clear()
            $bg.name = "$($fn -replace '^p_', '')_bg$bgN"
            $code = 0xF00 + $bgN
            SetF $bg 'code' "u:$code"; SetF $bg 'uid' "u:$(New-Uid $hi $code)"; SetF $bg 'pool' "s:$fn"
            SetF $bg 'pool2' "s:$(FS (Kid $res $fn) 'parent')"; SetF $bg 'pool3' 's:'; SetF $bg 'pool4' 's:'
            (Fld $bg 'ai').c[0] = Clone-Cell (Fld $com 'ai').c[0]
            SetF $bg 'name' "s:$(FS $com 'name')"
            $strSpr = $(if ($isTank) { Spr $com } else { 'plu_rifles' })
            foreach ($m in $members) { if ((Real $m) -eq 'STR') { $strSpr = Spr $m; break } }
            SetF $bg 'str_sprite' "s:$strSpr"
            $slots = Azcf-NewNode 'slots' 2 2 'su'
            AddSlot $slots 'COM' $com.name; $used[$com.name] = 1
            AddSlot $slots 'SCT' ''
            $uni = @($members | Where-Object { (Real $_) -eq 'UNI' -and $_ -ne $com }); $str = @($members | Where-Object { (Real $_) -eq 'STR' }); $sup = @($members | Where-Object { (Real $_) -in 'SUP', 'SUPM' })
            $sct = @($members | Where-Object { (Real $_) -eq 'SCT' })
            if ($sct.Count) { $slots.rows[1].c[0] = Cell-Decode "s:$($sct[0].name)"; $used[$sct[0].name] = 1 }
            foreach ($m in ($str | Select-Object -First 3)) { AddSlot $slots 'STR' $m.name; $used[$m.name] = 1 }
            foreach ($m in ($uni | Select-Object -First 3)) { AddSlot $slots 'UNI' $m.name; $used[$m.name] = 1 }
            while (($slots.rows | Where-Object { (Fcc-Row $_) -eq 'UNI' }).Count -lt 2 -and -not $isTank) { AddSlot $slots 'UNI' '' }
            foreach ($m in ($sup | Select-Object -First 2)) { AddSlot $slots $(if ((Real $m) -eq 'SUPM') { 'SUPM' } else { 'SUP' }) $m.name; $used[$m.name] = 1 }
            while (($slots.rows | Where-Object { (Fcc-Row $_) -match 'SUP' }).Count -lt 2) { AddSlot $slots 'SUP' '' }
            $bg.kids.Add($slots)
            $idx = $act.kids.IndexOf($com); $act.kids.Insert($idx, $bg); $byName[$bg.name] = $bg
            $q = $(if (Placed $com) { PosOf $com } else { PosOf $placedMembers[0] })
            $turn = ($placedMembers | ForEach-Object { (PosOf $_).turn } | Measure-Object -Minimum).Minimum
            foreach ($m in $members) { if ($used.ContainsKey($m.name)) { SetPos $m -1 -1 -1 1 } }   # free their nodes first
            SetPos $bg $q.px $q.pz $q.node $turn
            $bgCount++
            $changeLog.Add("- ``$($bg.name)`` ($(Fcc $bg 'bg'), node $($q.node), turn $turn): " + (($slots.rows | ForEach-Object { "$(Fcc-Row $_)=$($_.c[0].s)" }) -join ' '))
        }
        if ($tankOnly.Count) {
            # tank companies without a company command node (7 Gds OTPP, 140 STBde): one battle group, COM slot empty
            $bgN++; $bg = Clone-Node $tplBgTank[$sideCc]; $bg.kids.Clear()
            $bg.name = "$($fn -replace '^p_', '')_bg$bgN"; $code = 0xF00 + $bgN
            SetF $bg 'code' "u:$code"; SetF $bg 'uid' "u:$(New-Uid $hi $code)"; SetF $bg 'pool' "s:$fn"
            SetF $bg 'pool2' "s:$(FS (Kid $res $fn) 'parent')"; SetF $bg 'pool3' 's:'; SetF $bg 'pool4' 's:'
            (Fld $bg 'ai').c[0] = Clone-Cell (Fld $tankOnly[0] 'ai').c[0]
            SetF $bg 'name' "s:$(FS $tankOnly[0] 'name')"; SetF $bg 'str_sprite' "s:$(Spr $tankOnly[0])"
            SetF $bg 'bg' $(if ((Real $tankOnly[0]) -eq 'SUPM') { "u:'SUPM'" } else { "u:'TANK'" })
            $slots = Azcf-NewNode 'slots' 2 2 'su'
            AddSlot $slots 'COM' ''; AddSlot $slots 'SCT' ''
            foreach ($m in ($tankOnly | Select-Object -First 3)) { AddSlot $slots $(if ((Real $m) -eq 'SUPM') { 'SUPM' } else { 'STR' }) $m.name; $used[$m.name] = 1 }
            $extra = @($nodes | Where-Object { -not $used.ContainsKey($_.name) -and (Code $_) -ne 0 -and (Real $_) -in 'UNI', 'SUP' -and (Placed $_) })
            foreach ($m in ($extra | Where-Object { (Real $_) -eq 'UNI' } | Select-Object -First 1)) { AddSlot $slots 'UNI' $m.name; $used[$m.name] = 1 }
            foreach ($m in ($extra | Where-Object { (Real $_) -eq 'SUP' } | Select-Object -First 1)) { AddSlot $slots 'SUP' $m.name; $used[$m.name] = 1 }
            $bg.kids.Add($slots)
            $idx = $act.kids.IndexOf($tankOnly[0]); $act.kids.Insert($idx, $bg); $byName[$bg.name] = $bg
            $q = PosOf $tankOnly[0]
            $turn = ($tankOnly | ForEach-Object { (PosOf $_).turn } | Measure-Object -Minimum).Minimum
            foreach ($m in $nodes) { if ($used.ContainsKey($m.name) -and -not (IsBg $m)) { $r0 = PosOf $m; if ($r0 -and $r0.node -ne -1) { SetPos $m -1 -1 -1 1 } } }   # free their nodes first
            SetPos $bg $q.px $q.pz $q.node $turn
            $bgCount++
            $changeLog.Add("- ``$($bg.name)`` ($(Fcc $bg 'bg'), node $($q.node), turn $turn): " + (($slots.rows | ForEach-Object { "$(Fcc-Row $_)=$($_.c[0].s)" }) -join ' '))
        }
    }

    # ---------------- 2c. (0.5.8, user) SPG companies split into command + platoons: the 306 ID Marder company and the
    # 210 StuG battery are one node each (company command + two sections in one pool); as in the 17 July file they
    # become a command node (COMC, plu_tankcmd) and one SUPM node per section. The battle group holding the company
    # gets the command in its COM slot and a second SUPM slot for platoon 2; a standalone battery (210 AT bn, no HQ,
    # no battle group) has its new nodes placed next to the original one.
    $changeLog.Add("### SPG companies split into command + platoons")
    $snapshot = New-Object Collections.Generic.List[object]; foreach ($q in $act.kids) { $snapshot.Add($q) }
    foreach ($p in $snapshot) {
        if ((IsBg $p) -or (Code $p) -eq 0 -or (Real $p) -notin 'STR', 'SUPM') { continue }
        $pool = Kid $p 'pool'; if (-not $pool -or $pool.rows.Count -lt 3 -or $pool.rows[0].c[0].s -notmatch '_ccom$') { continue }
        $segs = @(); $cur = @($pool.rows[0])
        for ($i = 1; $i -lt $pool.rows.Count; $i++) { $sq = $pool.rows[$i].c[0].s; if ($sq -match '_com$' -and $sq -notmatch '_ccom$|_bcom$') { $segs += ,$cur; $cur = @($pool.rows[$i]) } else { $cur += $pool.rows[$i] } }
        $segs += ,$cur
        if ($segs.Count -lt 3) { continue }
        $code = Code $p; $coy = ($code -shr 4) -band 0xF; if ($coy -lt 1) { $coy = 1 }; $form = Pool $p; $hi = [uint32]((FU $p 'uid') -shr 12); $spr = Spr $p
        if ($spr -match 'stug') { $kc = "oppl_ger_stug_${coy}b"; $kp = "oppl_ger_stug_${coy}b{0}" }
        elseif ($spr -match 'marder') { if (-not $gKeys.ContainsKey("oppl_ger_${coy}atspgc")) { $coy = 1 }; $kc = "oppl_ger_${coy}atspgc"; $kp = "oppl_ger_${coy}atspgc{0}" }
        else { $kc = "oppl_ger_tr_${coy}med"; $kp = "oppl_ger_tr_${coy}med{0}" }
        $usedCodes = @{}; foreach ($q in $act.kids) { if ((Pool $q) -eq $form) { $usedCodes[(Code $q)] = 1 } }
        $cmdNode = Clone-Node $p; $cmdNode.name = "$($p.name)_com"
        SetF $cmdNode 'real_type' "u:'COMC'"; SetF $cmdNode 'str_sprite' 's:plu_tankcmd'; SetF $cmdNode 'name' "s:$(Need-Key $kc)"
        $cc = $code; while ($usedCodes.ContainsKey($cc)) { $cc++ }; $usedCodes[$cc] = 1   # command keeps the company code when free
        if ($cc -ne $code) { SetF $cmdNode 'code' "u:$cc" }
        SetF $cmdNode 'uid' "u:$(New-Uid $hi ($cc + 15))"
        $cp = Kid $cmdNode 'pool'; $cp.rows.Clear(); foreach ($r in $segs[0]) { $cp.rows.Add(@{ name = $null; c = @($r.c | ForEach-Object { Clone-Cell $_ }) }) }
        SetF $cmdNode 'max_squads' "u:$(($segs[0] | ForEach-Object { S32 $_.c[1].v[0] } | Measure-Object -Sum).Sum + 1)"
        $act.kids.Insert($act.kids.IndexOf($p), $cmdNode); $byName[$cmdNode.name] = $cmdNode
        $platNodes = @(); $pc = $code
        for ($s = 1; $s -lt $segs.Count; $s++) {
            if ($s -eq 1) { $pn = $p } else { $pn = Clone-Node $p; $pn.name = "$($p.name)_${s}p"; $act.kids.Insert($act.kids.IndexOf($platNodes[-1]) + 1, $pn); $byName[$pn.name] = $pn }
            do { $pc++ } while ($usedCodes.ContainsKey($pc)); $usedCodes[$pc] = 1
            SetF $pn 'code' "u:$pc"; if ($s -gt 1) { SetF $pn 'uid' "u:$(New-Uid $hi $pc)" }
            SetF $pn 'name' "s:$(Need-Key ($kp -f $s))"
            $pp2 = Kid $pn 'pool'; $pp2.rows.Clear(); foreach ($r in $segs[$s]) { $pp2.rows.Add(@{ name = $null; c = @($r.c | ForEach-Object { Clone-Cell $_ }) }) }
            SetF $pn 'max_squads' "u:$(($segs[$s] | ForEach-Object { S32 $_.c[1].v[0] } | Measure-Object -Sum).Sum + 1)"
            $platNodes += $pn
        }
        # the battle group holding the company: command into COM (if empty), platoon 2 into a new SUPM/STR slot
        $holder = $null; foreach ($bg in $act.kids) { if (IsBg $bg) { $sl = Kid $bg 'slots'; foreach ($r in $sl.rows) { if ($r.c[0].s -eq $p.name) { $holder = $bg } } } }
        if ($holder) {
            $sl = Kid $holder 'slots'
            foreach ($r in $sl.rows) { if ((Fcc-Row $r) -eq 'COM' -and -not $r.c[0].s) { $r.c[0] = Cell-Decode "s:$($cmdNode.name)"; $used[$cmdNode.name] = 1; break } }
            $idx = 0; for ($i = 0; $i -lt $sl.rows.Count; $i++) { if ($sl.rows[$i].c[0].s -eq $p.name) { $idx = $i } }
            for ($s = 1; $s -lt $platNodes.Count; $s++) { $sl.rows.Insert($idx + $s, @{ name = $null; c = @((Cell-Decode "s:$($platNodes[$s].name)"), (Cell-Decode "u:'$(Real $p)'")) }); $used[$platNodes[$s].name] = 1 }
            SetPos $cmdNode -1 -1 -1 1; foreach ($pn in $platNodes) { SetPos $pn -1 -1 -1 1 }
            $changeLog.Add("- ``$($p.name)`` split: ``$($cmdNode.name)`` + " + (($platNodes | ForEach-Object { "``$($_.name)``" }) -join ' + ') + " in ``$($holder.name)``: " + (($sl.rows | ForEach-Object { "$(Fcc-Row $_)=$($_.c[0].s)" }) -join ' '))
        } else {
            $q = PosOf $p
            if ($q -and $q.node -ne -1) { SetPos $cmdNode $q.px $q.pz $q.node $q.turn; for ($s = 1; $s -lt $platNodes.Count; $s++) { SetPos $platNodes[$s] $q.px $q.pz $q.node $q.turn } }
            else { SetPos $cmdNode -1 -1 -1 1; for ($s = 1; $s -lt $platNodes.Count; $s++) { SetPos $platNodes[$s] -1 -1 -1 1 } }
            $changeLog.Add("- ``$($p.name)`` split: ``$($cmdNode.name)`` + " + (($platNodes | ForEach-Object { "``$($_.name)`` (node $((PosOf $_).node))" }) -join ' + ') + ", standalone, placed next to the original")
        }
    }

    # ---------------- 2d. (0.5.8, user) reserve squads of the German formations become platoons: every German formation
    # carries the same reserve pool (Pak 38, 2x Pak 184/1(r), Pak 97/38, 2x MG 42, 2x leIG 18, 2x GrW 34, light
    # mortars, AT teams, trucks); the guns, MGs and mortars become platoon nodes (two ATG platoons, an MG platoon, an
    # IG platoon with its FO team, a mortar platoon with its FO team) that a battle group can take; the pool rows go.
    # Templates: 30 July 14./513 ATG platoon, 12./513 MG platoon, 8./513 mortar section, 13./513 FO 75 mm, I/513 FO 81 mm.
    $changeLog.Add("### German reserve guns, MGs and mortars as platoons (+ FO teams)")
    $tplAtg = $tAct.kids | Where-Object { $_.name -eq 'we_513_14c_atg1' }; $tplMg = $tAct.kids | Where-Object { $_.name -eq 'we_513_12cmg_1p' }
    $tplMt = $tAct.kids | Where-Object { $_.name -eq 'we_513_8cmg_4pmo_1s' }; $tplFo75 = $tAct.kids | Where-Object { $_.name -eq 'we_513_13c_ac75' }; $tplFo81 = $tAct.kids | Where-Object { $_.name -eq 'we_513_1b_ac81' }
    $madePl = 0
    $resSnap = New-Object Collections.Generic.List[object]; foreach ($x in $res.kids) { $resSnap.Add($x) }
    foreach ($f in $resSnap) {
        if ((Fcc $f 'side') -ne 'GER' -or -not $f.kids.Count) { continue }
        $pool = $f.kids[0]; $rows = @{}; foreach ($r in $pool.rows) { $rows[$r.c[0].s] = $r }
        if (-not ($rows.ContainsKey('rn_wer_atg') -and $rows.ContainsKey('wer_mg42') -and $rows.ContainsKey('rn_wer_leig') -and $rows.ContainsKey('wer_grw34'))) { continue }
        $hqNode = $null; foreach ($p in $act.kids) { if ((Pool $p) -eq $f.name -and (Code $p) -eq 0 -and -not (IsBg $p)) { $hqNode = $p; break } }
        if (-not $hqNode) { continue }
        $hi = [uint32]((FU $hqNode 'uid') -shr 12); $prefix = $hqNode.name -replace '_hq$', ''
        $usedCodes = @{}; foreach ($q in $act.kids) { if ((Pool $q) -eq $f.name) { $usedCodes[(Code $q)] = 1 } }
        $nextCode = 0x141; function Free-Code { while ($usedCodes.ContainsKey($script:nextCode)) { $script:nextCode++ }; $usedCodes[$script:nextCode] = 1; $script:nextCode }
        $lastIdx = -1; for ($i = 0; $i -lt $act.kids.Count; $i++) { if ((Pool $act.kids[$i]) -eq $f.name) { $lastIdx = $i } }
        $params = Clone-Cell (Fld $hqNode 'params').c[0]; $ai = Clone-Cell (Fld $hqNode 'ai').c[0]
        function Make-Node([object]$tpl, [string]$name, [string]$key, [string]$sprite, [string]$mob, [object[]]$poolRows) {
            $n = Clone-Node $tpl; $n.name = $name
            $c = Free-Code; SetF $n 'code' "u:$c"; SetF $n 'uid' "u:$(New-Uid $hi $c)"; SetF $n 'pool' "s:$($f.name)"
            (Fld $n 'params').c[0] = Clone-Cell $params; (Fld $n 'ai').c[0] = Clone-Cell $ai
            SetF $n 'name' "s:$(Need-Key $key)"; if ($sprite) { SetF $n 'str_sprite' "s:$sprite" }; if ($mob) { SetF $n 'mobility' "u:'$mob'" }
            $hasRows = ($poolRows -and $poolRows.Count -gt 0 -and $null -ne $poolRows[0])
            if ($hasRows) { $pk = Kid $n 'pool'; $pk.rows.Clear(); $cnt = 0; foreach ($pr in $poolRows) { $pk.rows.Add(@{ name = $null; c = @((Cell-Decode "s:$($pr[0])"), (Cell-Decode "a:$($pr[1])"), (Cell-Decode 'v:-1;-1;-1;-1'), (Cell-Decode 'v:-1;-1;-1;-1'), (Cell-Decode "s:$($pr[2])")) }); $cnt += $pr[1] }; SetF $n 'max_squads' "u:$($cnt + 1)" }
            $script:lastIdx++; $act.kids.Insert($script:lastIdx, $n); $byName[$n.name] = $n; SetPos $n -1 -1 -1 1; $script:madePl++
            $desc = $(if ($hasRows) { ($poolRows | ForEach-Object { "$($_[0]) x$($_[1])" }) -join ', ' } else { 'FO team (30 July composition)' })
            $changeLog.Add("- NEW ``$($n.name)`` (0x$('{0:x}' -f $c), $(Real $n), $(Spr $n)) in $($f.name): $desc")
            $n
        }
        $nAtg = S32 $rows['rn_wer_atg'].c[1].v[0]; $nHatg = $(if ($rows.ContainsKey('rn_wer_hatg')) { S32 $rows['rn_wer_hatg'].c[1].v[0] } else { 0 }); $nPak184 = $(if ($rows.ContainsKey('wer_pak184_1r')) { S32 $rows['wer_pak184_1r'].c[1].v[0] } else { 0 })
        $atgRows = New-Object Collections.Generic.List[object]; $atgRows.Add(@('wer_com_art_plat', 1, '')); $atgRows.Add(@('rn_wer_atg', $nAtg, '')); if ($nHatg) { $atgRows.Add(@('rn_wer_hatg', $nHatg, '')) }
        Make-Node $tplAtg "${prefix}_atg_1p" 'oppl_ger_14c_1p' 'pl_pak38' 'WHEL' $atgRows.ToArray() | Out-Null
        if ($nPak184) { Make-Node $tplAtg "${prefix}_atg_2p" 'oppl_ger_14c_2p' 'pl_pak38' 'WHEL' @(@('wer_com_art_plat', 1, ''), @('wer_pak184_1r', $nPak184, '')) | Out-Null }
        Make-Node $tplMg "${prefix}_mg_1p" 'oppl_ger_12c_1p' 'pl_mg42' 'FOOT' @(@('wer_com_art_plat', 1, ''), @('wer_mg42', (S32 $rows['wer_mg42'].c[1].v[0]), '')) | Out-Null
        Make-Node $tplAtg "${prefix}_ig_1p" 'oppl_ger_13c_1p' 'pl_leig' 'HORS' @(@('wer_com_art_plat', 1, ''), @('rn_wer_leig', (S32 $rows['rn_wer_leig'].c[1].v[0]), '')) | Out-Null
        Make-Node $tplFo75 "${prefix}_ig_ac" 'oppl_ger_13ac1' $null $null $null | Out-Null
        Make-Node $tplMt "${prefix}_mt_1p" 'oppl_ger_8c_4p' 'plu_mortars' 'FOOT' @(@('wer_com_art_plat', 1, ''), @('wer_squad_phone', 1, ''), @('wer_grw34', (S32 $rows['wer_grw34'].c[1].v[0]), '')) | Out-Null
        Make-Node $tplFo81 "${prefix}_mt_ac" 'oppl_ger_1b_1p' $null $null $null | Out-Null
        foreach ($sq in 'rn_wer_atg', 'rn_wer_hatg', 'wer_pak184_1r', 'wer_mg42', 'rn_wer_leig', 'wer_grw34') { if ($rows.ContainsKey($sq)) { $pool.rows.Remove($rows[$sq]) | Out-Null } }
        $changeLog.Add("- $($f.name): reserve rows for the guns, MGs and mortars removed (now platoons)")
    }
    $changeLog.Add("- $madePl platoons made from reserve rows")

    # ---------------- 2e. (0.5.8, user) 293 Gds RR gets its organic artillery FO and support units from its 30 July
    # counterpart (p_ra_293rr of 96 Gds RD): every 30 July platoon of the regiment whose code the Saur file does not
    # already use (the HQ, 1st bn command and 1st company stay as they are) is added as a reserve, like the 34 Gds RD
    # regiments: HQ coy sappers, regimental gun battery with FO, 120 mm mortar battery, ATR coy, 76 mm gun battery FO
    # and platoon, battalion mortar/ATG/ATR units, company mortar platoons, MG and mortar companies, 2nd/3rd battalions.
    # User: "1/293 FO and support units: base it off reserves". The 293 Gds RR reserve pool holds two artillery spotters
    # (120 mm mortars, 76 mm ZiS-3), 2 x 45 mm 53-K, 1 x 76 mm regimental gun, 2 x 82 mm mortars, 2 x Maxim, 2 x SMG
    # squads. They become platoons shaped like the 30 July 103 Gds RR ones (template node, name key and support id),
    # with the reserve quantities: FO 120 mm, FO 76 mm, ATG platoon, gun platoon, mortar platoon + its FO team, MG
    # platoon, SMG platoon; the pool rows go.
    $changeLog.Add("### 293 Gds RR: FO and support platoons from its reserve pool (superseded in 0.5.10 by the full 30 July regiment)")
    $form293 = 'p_ra_293gds_rr'; $f293 = Kid $res $form293
    if ($f293 -and $f293.kids.Count -and -not (Kid $res 'p_ra_293rr')) {
        $pool293 = $f293.kids[0]; $rows = @{}; foreach ($r in $pool293.rows) { $rows[$r.c[0].s + '|' + $r.c[4].s] = $r }
        $codes = @{}; $hq293 = $null; $lastIdx = -1
        for ($i = 0; $i -lt $act.kids.Count; $i++) { $p = $act.kids[$i]; if ((Pool $p) -eq $form293) { $codes[(Code $p)] = 1; $lastIdx = $i; if ((Code $p) -eq 0 -and -not (IsBg $p)) { $hq293 = $p } } }
        if ($hq293) {
            $hi = [uint32]((FU $hq293 'uid') -shr 12); $ai = Clone-Cell (Fld $f293 'ai').c[0]; $params293 = Clone-Cell (Fld $hq293 'params').c[0]; $added293 = 0
            # (template 30 July node, new name, pool row key to consume, squad id, quantity override (0 = row quantity), support id override)
            $specs = @(
                @('ra_103_ac120mt2', 'ra_293rr_ac120mt', 'rkka_corr_art|rkka_artsup_mt120_plat', 'rkka_corr_art', 1, 'rkka_artsup_mt120_plat'),
                @('ra_103_ac76gun', 'ra_293rr_ac76gun', 'rkka_corr_art|rkka_artsup_zis3_plat', 'rkka_corr_art', 1, 'rkka_artsup_zis3_plat'),
                @('ra_103_1b_atg', 'ra_293rr_1b_atg', 'rn_rkka_atg_old|', 'rn_rkka_atg_old', 0, ''),
                @('ra_103_gunc_2p', 'ra_293rr_gunc_1p', 'rkka_pp27|', 'rkka_pp27', 0, ''),
                @('ra_103_1mt_1p', 'ra_293rr_1mt_1p', 'rkka_mt82|', 'rkka_mt82', 0, ''),
                @('ra_103_1b_ac82mt', 'ra_293rr_1b_ac82mt', '', '', 0, ''),
                @('ra_103_1mg_1p', 'ra_293rr_1mg_1p', 'rkka_maxim|', 'rkka_maxim', 0, ''),
                @('ra_103_1smgc_1p', 'ra_293rr_1smgc_1p', 'rkka_squad_smg_43m|', 'rkka_squad_smg_43m', 0, '')
            )
            foreach ($sp in $specs) {
                $t = $tAct.kids | Where-Object { $_.name -eq $sp[0] } | Select-Object -First 1
                if (-not $t) { Write-Warning "$side : 30 July template $($sp[0]) missing"; continue }
                if ($sp[2] -and -not $rows.ContainsKey($sp[2])) { $changeLog.Add("- $($sp[1]): reserve row $($sp[2]) not in the pool, skipped"); continue }
                $n = Clone-Node $t; $n.name = $sp[1]; $x = 2; $base = $n.name; while ($byName.ContainsKey($n.name)) { $n.name = "${base}_$x"; $x++ }
                $c = Code $t; while ($codes.ContainsKey($c)) { $c++ }; $codes[$c] = 1
                SetF $n 'code' "u:$c"; SetF $n 'pool' "s:$form293"; (Fld $n 'ai').c[0] = Clone-Cell $ai; (Fld $n 'params').c[0] = Clone-Cell $params293; SetF $n 'uid' "u:$(New-Uid $hi $c)"
                Need-Key (FS $n 'name') | Out-Null
                if ($sp[2]) {
                    $row = $rows[$sp[2]]; $qty = $(if ($sp[4]) { $sp[4] } else { S32 $row.c[1].v[0] })
                    $pk = Kid $n 'pool'
                    foreach ($pr in $pk.rows) { if ($pr.c[0].s -eq $sp[3] -or ($sp[3] -eq 'rn_rkka_atg_old' -and $pr.c[0].s -match 'atg') -or ($sp[3] -eq 'rkka_squad_smg_43m' -and $pr.c[0].s -match 'squad_smg')) { $pr.c[0] = Cell-Decode "s:$($sp[3])"; $pr.c[1] = Cell-Decode "a:$qty"; if ($sp[5]) { $pr.c[4] = Cell-Decode "s:$($sp[5])" } } }
                    $cnt = 0; foreach ($pr in $pk.rows) { $cnt += S32 $pr.c[1].v[0] }; SetF $n 'max_squads' "u:$($cnt + 1)"
                    $pool293.rows.Remove($row) | Out-Null
                }
                $lastIdx++; $act.kids.Insert($lastIdx, $n); $byName[$n.name] = $n; SetPos $n -1 -1 -1 1; $added293++
                $changeLog.Add("- NEW ``$($n.name)`` (0x$('{0:x}' -f $c), $(Real $n), $(Spr $n), from 30 July $($sp[0])): " + (((Kid $n 'pool').rows | ForEach-Object { "$($_.c[0].s) x$(S32 $_.c[1].v[0])$(if ($_.c[4].s) { ' (' + $_.c[4].s + ')' })" }) -join ', '))
            }
            $changeLog.Add("- $added293 platoons made for $form293; its reserve pool now holds $($pool293.rows.Count) rows")
        } else { Write-Warning "$side : $form293 has no HQ node" }
    }

    # ---------------- 2f. (0.5.8, user) 140 STBde: tank companies, SMG coy, ATR coy, mortar battery and AA MG coy split
    # into command + platoons; T-3 tanks, the SdKfz 250 and the six motor-rifle squads of the reserve pool become
    # platoons (the T-20 tractor stays in reserve); the brigade battle group gets two tank slots.
    $changeLog.Add("### 140 STBde: companies split, reserve pool units as platoons, two tank slots")
    $form140 = 'p_ra_140_stbde'; $f140 = Kid $res $form140
    if ($f140) {
        $hq140 = $null; foreach ($p in $act.kids) { if ((Pool $p) -eq $form140 -and (Code $p) -eq 0 -and -not (IsBg $p)) { $hq140 = $p; break } }
        $hi140 = [uint32]((FU $hq140 'uid') -shr 12)
        $used140 = @{}; foreach ($q in $act.kids) { if ((Pool $q) -eq $form140) { $used140[(Code $q)] = 1 } }
        function Free140([int]$from) { $c = $from; while ($used140.ContainsKey($c)) { $c++ }; $used140[$c] = 1; $c }
        function Split-Coy([object]$p, [string]$segStart, [string]$cmdSprite, [string]$cmdKey, [string]$platKeyFmt, [int]$platKeyBase) {
            # segments: command = rows before the first row matching $segStart (after row 0), one platoon per further start
            $pool = Kid $p 'pool'; $segs = @(); $cur = @($pool.rows[0])
            for ($i = 1; $i -lt $pool.rows.Count; $i++) { if ($pool.rows[$i].c[0].s -match $segStart) { $segs += ,$cur; $cur = @($pool.rows[$i]) } else { $cur += $pool.rows[$i] } }
            $segs += ,$cur
            if ($segs.Count -lt 2) { $changeLog.Add("- $($p.name): nothing to split"); return $null }
            $code = Code $p
            $cmd = Clone-Node $p; $cmd.name = "$($p.name)_com"
            SetF $cmd 'real_type' "u:'COMC'"; SetF $cmd 'str_sprite' "s:$cmdSprite"; SetF $cmd 'name' "s:$(Need-Key $cmdKey)"; SetF $cmd 'uid' "u:$(New-Uid $hi140 ($code + 15))"
            $cp = Kid $cmd 'pool'; $cp.rows.Clear(); foreach ($r in $segs[0]) { $cp.rows.Add(@{ name = $null; c = @($r.c | ForEach-Object { Clone-Cell $_ }) }) }
            SetF $cmd 'max_squads' "u:$(($segs[0] | ForEach-Object { S32 $_.c[1].v[0] } | Measure-Object -Sum).Sum + 1)"
            $act.kids.Insert($act.kids.IndexOf($p), $cmd); $byName[$cmd.name] = $cmd; SetPos $cmd -1 -1 -1 1
            $plats = @()
            for ($s = 1; $s -lt $segs.Count; $s++) {
                if ($s -eq 1) { $pn = $p } else { $pn = Clone-Node $p; $pn.name = "$($p.name)_${s}p"; $act.kids.Insert($act.kids.IndexOf($plats[-1]) + 1, $pn); $byName[$pn.name] = $pn }
                $pc = Free140 ($code + 1); SetF $pn 'code' "u:$pc"; if ($s -gt 1) { SetF $pn 'uid' "u:$(New-Uid $hi140 $pc)" }
                SetF $pn 'name' "s:$(Need-Key ($platKeyFmt -f ($platKeyBase + $s)))"
                $pp2 = Kid $pn 'pool'; $pp2.rows.Clear(); foreach ($r in $segs[$s]) { $pp2.rows.Add(@{ name = $null; c = @($r.c | ForEach-Object { Clone-Cell $_ }) }) }
                SetF $pn 'max_squads' "u:$(($segs[$s] | ForEach-Object { S32 $_.c[1].v[0] } | Measure-Object -Sum).Sum + 1)"
                SetPos $pn -1 -1 -1 1
                $plats += $pn
            }
            $changeLog.Add("- ``$($p.name)`` split: ``$($cmd.name)`` ($(($segs[0] | ForEach-Object { "$($_.c[0].s) x$(S32 $_.c[1].v[0])" }) -join ', ')) + " + (($plats | ForEach-Object { "``$($_.name)`` ($(((Kid $_ 'pool').rows | ForEach-Object { "$($_.c[0].s) x$(S32 $_.c[1].v[0])" }) -join ', '))" }) -join ' + '))
            @{ cmd = $cmd; plats = $plats }
        }
        $tc1 = Split-Coy $byName['ra_140stbde_coy1'] '_ccom$|_com$' 'plu_tankcmd' 'oppl_ussr_tr_1c' 'oppl_ussr_tr_1c{0}' 0
        $tc2 = Split-Coy $byName['ra_140stbde_coy2'] '_ccom$|_com$' 'plu_tankcmd' 'oppl_ussr_tr_2c' 'oppl_ussr_tr_2c{0}' 0
        $smg = Split-Coy $byName['ra_140stbde_smg'] '^rkka_com_smg_plat$' 'plu_field_com' 'oppl_ussr_rr_1smgc' 'oppl_ussr_rr_1smgc{0}' 0
        $atr = Split-Coy $byName['ra_140stbde_atr'] '^rkka_com_art_fplat$' 'plu_field_com' 'oppl_ussr_rr_atrc' 'oppl_ussr_rr_atrc{0}' 0
        $mtb = Split-Coy $byName['ra_140stbde_mtb'] '^rkka_com_art_fplat$' 'plu_batcmd' 'oppl_ussr_1mtca' 'oppl_ussr_1mtca{0}' 1
        $aamg = Split-Coy $byName['ra_140stbde_aamg'] '^rkka_com_art_fplat$' 'plu_field_com' 'oppl_ussr_1mgc' 'oppl_ussr_1mgc{0}' 0
        # FO team for the mortar battery (30 July battalion mortar FO, 82 mm support)
        $tFo = $tAct.kids | Where-Object { $_.name -eq 'ra_103_1b_ac82mt' } | Select-Object -First 1
        if ($mtb -and $tFo) {
            $fo = Clone-Node $tFo; $fo.name = 'ra_140stbde_mtb_ac'; $c = Free140 0x224
            SetF $fo 'code' "u:$c"; SetF $fo 'pool' "s:$form140"; (Fld $fo 'ai').c[0] = Clone-Cell (Fld $hq140 'ai').c[0]; (Fld $fo 'params').c[0] = Clone-Cell (Fld $hq140 'params').c[0]
            SetF $fo 'uid' "u:$(New-Uid $hi140 $c)"; SetF $fo 'name' "s:$(Need-Key 'oppl_ussr_1mtca1')"
            $act.kids.Insert($act.kids.IndexOf($mtb.cmd) + 1, $fo); $byName[$fo.name] = $fo; SetPos $fo -1 -1 -1 1
            $changeLog.Add("- NEW ``$($fo.name)`` (0x$('{0:x}' -f $c), CTRL, plu_fo): FO team of the mortar battery")
        }
        # reserve pool units as platoons
        $pool140 = $f140.kids[0]; $rows140 = @{}; foreach ($r in $pool140.rows) { $rows140[$r.c[0].s] = $r }
        function New140([object]$tpl, [string]$name, [string]$key, [string]$real, [string]$sprite, [string]$mob, [object[]]$poolRows, [int]$codeFrom) {
            $n = Clone-Node $tpl; $n.name = $name; $c = Free140 $codeFrom
            SetF $n 'code' "u:$c"; SetF $n 'pool' "s:$form140"; (Fld $n 'ai').c[0] = Clone-Cell (Fld $hq140 'ai').c[0]; (Fld $n 'params').c[0] = Clone-Cell (Fld $hq140 'params').c[0]
            SetF $n 'uid' "u:$(New-Uid $hi140 $c)"; SetF $n 'name' "s:$(Need-Key $key)"; SetF $n 'real_type' "u:'$real'"; SetF $n 'str_sprite' "s:$sprite"; SetF $n 'mobility' "u:'$mob'"; SetF $n 'bg' 'u:0'
            $pk = Kid $n 'pool'; $pk.rows.Clear(); $cnt = 0
            foreach ($pr in $poolRows) { $pk.rows.Add(@{ name = $null; c = @((Cell-Decode "s:$($pr[0])"), (Cell-Decode "a:$($pr[1])"), (Cell-Decode 'v:-1;-1;-1;-1'), (Cell-Decode 'v:-1;-1;-1;-1'), (Cell-Decode 's:')) }); $cnt += $pr[1] }
            SetF $n 'max_squads' "u:$($cnt + 1)"
            $li = -1; for ($i = 0; $i -lt $act.kids.Count; $i++) { if ((Pool $act.kids[$i]) -eq $form140) { $li = $i } }
            $act.kids.Insert($li + 1, $n); $byName[$n.name] = $n; SetPos $n -1 -1 -1 1
            $changeLog.Add("- NEW ``$($n.name)`` (0x$('{0:x}' -f $c), $real, $sprite): " + (($poolRows | ForEach-Object { "$($_[0]) x$($_[1])" }) -join ', '))
            $n
        }
        $tplTank = $byName['ra_140stbde_coy1']; $tplInf = $tAct.kids | Where-Object { $_.name -eq 'ra_103_1c_1p' } | Select-Object -First 1
        $t3 = $null; $apc = $null; $mr = @()
        if ($rows140.ContainsKey('rkka_t3')) { $t3 = New140 $tplTank 'ra_140stbde_t3_plat' 'oppl_ussr_tr_2c2' 'STR' 'pl_pz3l' 'PIL' @(, @('rkka_t3', (S32 $rows140['rkka_t3'].c[1].v[0]))) 0x213; $pool140.rows.Remove($rows140['rkka_t3']) | Out-Null }
        if ($rows140.ContainsKey('rkka_sdkfz250_1')) { $apc = New140 $tplTank 'ra_140stbde_apc_plat' 'oppl_ussr_tr_hq1' 'SCT' 'pl_wscout' 'WHEL' @(, @('rkka_sdkfz250_1', (S32 $rows140['rkka_sdkfz250_1'].c[1].v[0]))) 0x241; $pool140.rows.Remove($rows140['rkka_sdkfz250_1']) | Out-Null }
        if ($rows140.ContainsKey('rkka_squad_mrifles_43a') -and $tplInf) {
            $nSq = S32 $rows140['rkka_squad_mrifles_43a'].c[1].v[0]; $k = 0
            while ($nSq -gt 0) { $k++; $take = [Math]::Min(3, $nSq); $mr += New140 $tplInf "ra_140stbde_mr_${k}p" (FS $tplInf 'name') 'UNI' 'plu_rifles' 'FOOT' @(@('rkka_com_mr_plat', 1), @('rkka_squad_mrifles_43a', $take)) 0x251; $nSq -= $take }
            $pool140.rows.Remove($rows140['rkka_squad_mrifles_43a']) | Out-Null
        }
        $changeLog.Add("- $form140 reserve pool now: " + (($pool140.rows | ForEach-Object { "$($_.c[0].s) x$(S32 $_.c[1].v[0])" }) -join ', '))
        # the brigade battle group: COM = 1st tank coy command, SCT = APC recon, two tank slots, two SMG slots, AA MG + mortars
        $bg140 = $byName['ra_140_stbde_bg1']
        if ($bg140 -and $tc1) {
            $sl = Kid $bg140 'slots'; $sl.rows.Clear()
            AddSlot $sl 'COM' $tc1.cmd.name
            AddSlot $sl 'SCT' $(if ($apc) { $apc.name } else { '' })
            AddSlot $sl 'STR' $tc1.plats[0].name
            AddSlot $sl 'STR' $(if ($tc2) { $tc2.plats[0].name } elseif ($t3) { $t3.name } else { '' })
            if ($smg) { AddSlot $sl 'UNI' $smg.plats[0].name; AddSlot $sl 'UNI' $(if ($smg.plats.Count -gt 1) { $smg.plats[1].name } else { '' }) } else { AddSlot $sl 'UNI' ''; AddSlot $sl 'UNI' '' }
            AddSlot $sl 'SUP' $(if ($aamg) { $aamg.plats[0].name } else { '' })
            AddSlot $sl 'SUP' $(if ($mtb) { $mtb.plats[0].name } else { '' })
            foreach ($r in $sl.rows) { if ($r.c[0].s) { $used[$r.c[0].s] = 1; SetPos $byName[$r.c[0].s] -1 -1 -1 1 } }
            $changeLog.Add("- ``$($bg140.name)`` slots: " + (($sl.rows | ForEach-Object { "$(Fcc-Row $_)=$($_.c[0].s)" }) -join ' '))
        }
    }

    # ---------------- 2h. (0.5.10, user: "some artillery batteries lack their FO; FO lacks guns") complete batteries.
    # The engine counts an FO team's guns from the gun platoons of its own company group (code & 0xFF0) in the same
    # formation (save: FO row cell 25 = 2 for 4b_ac next to 4b_1p with two ZiS-3, 4 for 1b_ac next to the moved
    # four-gun battery, 0 where the group has none). So every FO gets a gun platoon of its type in its group (or moves
    # into the group that already holds the guns of its type) and every indirect-fire gun platoon gets an FO team.
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
        function Insert-After([object]$anchor, [object]$n) { $act.kids.Insert($act.kids.IndexOf($anchor) + 1, $n); $byName[$n.name] = $n; SetPos $n -1 -1 -1 1 }
        # key for a German AR battery node from a sibling key of the same regiment: '<prefix>_<n>b<k>'
        function Ar-Key([string]$fnName, [int]$bat, [string]$suffix, [string]$fallback) {
            if ($sideCc -eq 'USSR' -and $isAr) { return (Need-Key "oppl_ussr_ar_${bat}b$suffix") }
            if ($isAr) { foreach ($q in $act.kids) { if ((Pool $q) -eq $fnName) { $k = FS $q 'name'; if ($k -match '^(.*_)(\d)b' + $suffix + '$') { $pre = $Matches[1]; $m = $Matches[2]; return (Need-KeySub "${pre}${bat}b$suffix" $k @{ "${m}b$suffix" = "${bat}b$suffix"; "${m}./" = "${bat}./" }) } } } }
            Need-Key $fallback
        }
        $groups = @{}; foreach ($n in $nodes) { $g = (Code $n) -band 0xFF0; if (-not $groups.ContainsKey($g)) { $groups[$g] = @() }; $groups[$g] += $n }
        foreach ($g in @($groups.Keys)) {
            $bat = ($g -shr 4) -band 0xF
            $fos = @($groups[$g] | Where-Object { (Real $_) -eq 'CTRL' -and $famOf.ContainsKey((Fo-Sup $_)) })
            $gunsByFam = @{}; foreach ($n in $groups[$g]) { foreach ($fk in (Gun-Fams $n)) { if (-not $gunsByFam.ContainsKey($fk)) { $gunsByFam[$fk] = @() }; $gunsByFam[$fk] += $n } }
            $foFams = @{}; foreach ($f0 in $fos) { $foFams[$famOf[(Fo-Sup $f0)]] = $f0 }
            # FO without guns of its type in the group
            foreach ($f0 in $fos) {
                $fam = $famOf[(Fo-Sup $f0)]; if ($gunsByFam.ContainsKey($fam)) { continue }
                # a group elsewhere in the formation with guns of that type and no FO of that type -> move the FO there
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
                Insert-After $f0 $n; $groups[$g] += $n; $batFixed++
                $changeLog.Add("- NEW ``$($n.name)`` (0x$('{0:x}' -f $nc), SUP, $($spec.squad) x2) in $fn for FO ``$($f0.name)``")
            }
            # gun platoons without an FO of their type in the group
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
                Insert-After $gun $n; $groups[$g] += $n; $foFams[$fam] = $n; $batFixed++
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
                        $act.kids.Insert($act.kids.IndexOf($fo0), $n); $byName[$n.name] = $n; SetPos $n -1 -1 -1 1
                        $groups[$g] += $n; $batFixed++
                        $changeLog.Add("- NEW ``$($n.name)`` (0x$('{0:x}' -f $g), COMC, battery command) in $fn")
                    }
                }
            }
        }
    }
    $changeLog.Add("- $batFixed battery fixes")

    # ---------------- 2b. map nodes: column 2 element 0 of every mg_nodes row is the uid of the unit standing on the
    # node (-1 when empty); in every vanilla file it mirrors plat_pos exactly. The engine looks the occupant up by that
    # uid and crashes on a stale one (adv_opgame.codelib+0x36e34, 0.5.4-0.5.6), so the column is rebuilt from plat_pos.
    $occ = @{}; foreach ($r in $pp.rows) { $n = S32 $r.c[0].v[3]; if ($n -ne -1) { $occ[$n] = [uint32]$r.c[0].v[0] } }
    $synced = 0
    for ($n = 0; $n -lt $mgNodes.rows.Count; $n++) {
        $c2 = $mgNodes.rows[$n].c[2]; $want = $(if ($occ.ContainsKey($n)) { $occ[$n] } else { [uint32]4294967295 })
        if ([uint32]$c2.v[0] -ne $want) { $c2.v[0] = $want; $synced++ }
    }
    $changeLog.Add("### mg_nodes occupants synced with plat_pos: $synced nodes changed")

    # ---------------- 3. current-format flags
    SetF $cg 'features' 'u:33554443'
    $changeLog.Add("### campgen features 0x2000008 -> 0x200000B")

    # ---------------- 4. text packs
    foreach ($l in 'eng', 'rus') {
        $keys = New-Object Collections.Generic.List[object]
        foreach ($k in $naText[$l].keys) { $keys.Add(@{ key = $k.key; items = @($k.items) }) }
        foreach ($e in $needKeys.Keys) {
            $spec = $needKeys[$e]
            $src = $tTextIdx[$l][$spec.src]; if (-not $src) { $src = $tTextIdx.eng[$spec.src] }
            $items = @($src.items | ForEach-Object { $s = [string]$_; if ($spec.sub) { foreach ($kv in $spec.sub.GetEnumerator()) { $s = $s.Replace($kv.Key, $kv.Value) } }; $s })
            $keys.Add(@{ key = $e; items = $items })
        }
        $outDir = Join-Path $outRoot $op
        New-Item -ItemType Directory -Force $outDir | Out-Null
        Write-Aztx (Join-Path $outDir "text.text.loc_$l.bin") "loc_$l" $keys.ToArray()
    }
    # ---------------- 5. desc: save, diff, delta, flatlist
    $genDir = Join-Path $Work "gen\$op"; New-Item -ItemType Directory -Force $genDir | Out-Null
    $gen = Join-Path $genDir 'desc.config.loc_def.bin'
    Azcf-Save $D $gen | Out-Null
    $outDir = Join-Path $outRoot $op
    $delta = Join-Path $outDir 'desc.config.loc_def.01_oob.delta'
    $r = Cmd-Diff (Join-Path $vDir 'desc.config.loc_def.bin') $gen $delta
    $hdr = @("# MF Overhaul 0.5.4 M2: Saur-Mogila 28 Aug 1943 brought to the battle-group system; 34 Gds RD copied from 30 July; generated by tools\oob_saur.ps1",
             "# $($copied.Count) platoons copied, $bgCount battle groups built for the other formations. See docs\oob_saur_mogila.md")
    [IO.File]::WriteAllLines($delta, [string[]]($hdr + (Get-Content $delta)), [Text.Encoding]::UTF8)
    [IO.File]::WriteAllLines((Join-Path $outDir '!flatlist'), [string[]]@('i_unflat:unflat()', '{', "`tdesc                          , config          , loc_def ;", "`ttext                          , text            , loc_eng ;", "`ttext                          , text            , loc_rus ;", '}'), [Text.Encoding]::ASCII)
    "$op : $($copied.Count) platoons copied, $bgCount battle groups built, $($needKeys.Count) text keys copied, platoons now $($act.kids.Count); wrote $delta : $r"
}
$doc = Join-Path $repo 'docs\oob_saur_mogila_changes.md'
[IO.File]::WriteAllLines($doc, [string[]](@('# Saur-Mogila 28 Aug 1943: generated change list (tools\oob_saur.ps1)', '') + $changeLog), [Text.Encoding]::UTF8)
"change list: docs\oob_saur_mogila_changes.md"
