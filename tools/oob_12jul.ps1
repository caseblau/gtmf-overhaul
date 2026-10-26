<#
.SYNOPSIS
  M11: the 12 July 1943 Prokhorovka order of battle, built from the 30 July 1943 Stepanovka operation files by cloning
  whole formations (struct + reserve pool + every platoon, battle group and slot table) under new names and deleting the
  Mius formations that were not at Prokhorovka.

  Templates (30 July -> 12 July):
    Soviet  4 gds MC / 2 gds MC corps troops -> 18, 29, 2 gds, 2 TC and 5 gds MC HQs; 37 / 36 gds TBde -> every tank
            brigade; 13 / 14 gds MBde -> motor-rifle and mechanised brigades; 7 gds BTR (KV-1) -> 36 and 47 gds heavy TR
            (Churchill); 1543 SAP (SU-152) -> 1446 and 1529 SAP; 1 gds AT Bde -> 10 AT Bde; 24 gds RD -> 9 gds Airborne
            Div; 96 gds RD -> 95 gds RD; 34 gds RD -> 42 gds RD; 3 gds RD -> 52 gds RD; 315 RD -> 183 RD; 13 / 31 gds RC
            -> 33 gds RC and 48 RC; 2 gds A / 5 atk A -> 5 gds TA and 5 gds A.
    German  MID SS "Das Reich" -> LSSAH (1 and 2 SS-PzGr Rgt, 1 SS-Pz Rgt, StuG bn, AT bn, 1 SS AR); Das Reich,
            Totenkopf, II SS-Pz Corps troops and the OKH / air formations kept; XVII AK, XXIV PzK, XXIX AK families and
            3 PzD deleted.
  Vehicle, squad and strength values are the template's (30 July states); the 12 July strengths are the next pass.

.EXAMPLE
  tools\oob_12jul.ps1 -OpDir build\prokhorovka\op_GER        # in place: desc.config.loc_def.bin, text packs, uids.csv,
                                                              # oob_12jul.delta (against the 30 July desc kept as *.orig30)
#>
param([Parameter(Mandatory = $true)][string]$OpDir, [switch]$Quiet)
. (Join-Path $PSScriptRoot 'gt3.ps1') lib
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
trap { $m = ("!! " + $_.Exception.Message + " at line " + $_.InvocationInfo.ScriptLineNumber + ": " + $_.InvocationInfo.Line.Trim()); Write-Host $m; if ($liveLog) { Add-Content $liveLog $m -Encoding UTF8 }; break }

function Fld([object]$node, [string]$name) { foreach ($r in $node.rows) { if ($r.name -eq $name) { return $r } }; $null }
function FS([object]$node, [string]$name) { $r = Fld $node $name; if ($r -and $r.c[0].k -eq 2) { $r.c[0].s } else { '' } }
function FU([object]$node, [string]$name) { $r = Fld $node $name; if ($r) { [uint32]$r.c[0].v[0] } else { 0 } }
function SetS([object]$node, [string]$name, [string]$text) { $r = Fld $node $name; if (-not $r) { throw "no field $name in $($node.name)" }; $r.c[0] = @{ k = 2; v = (New-Object uint32[] 4); s = $text } }
function SetU([object]$node, [string]$name, [uint32]$val) { $r = Fld $node $name; if (-not $r) { throw "no field $name in $($node.name)" }; $v = New-Object uint32[] 4; $v[0] = $val; $r.c[0] = @{ k = 4; v = $v; s = $null } }
function Clone-Cell([hashtable]$c) { @{ k = $c.k; v = [uint32[]]$c.v.Clone(); s = $c.s } }
function Clone-Node([object]$n) {
    $cl = Azcf-NewNode $n.name $n.type $n.cols $n.types
    foreach ($r in $n.rows) { $cl.rows.Add(@{ name = $r.name; c = @($r.c | ForEach-Object { Clone-Cell $_ }) }) }
    foreach ($k in $n.kids) { $cl.kids.Add((Clone-Node $k)) }
    $cl
}
function Kid([object]$n, [string]$name) { foreach ($k in $n.kids) { if ($k.name -eq $name) { return $k } }; $null }
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

# ---------------------------------------------------------------- load
$descPath = Join-Path $OpDir 'desc.config.loc_def.bin'
$orig = "$descPath.orig30"
if (-not (Test-Path $orig)) { Copy-Item $descPath $orig }
foreach ($l in 'loc_eng', 'loc_rus') { $t = Join-Path $OpDir "text.text.$l.bin"; if ((Test-Path $t) -and -not (Test-Path "$t.orig30")) { Copy-Item $t "$t.orig30" } }
$D = Azcf-Load $orig
$res = Kid $D.root 'reserves'; $act = Kid $D.root 'act_platoons'; $pp = Kid $D.root 'plat_pos'; $aiO = Kid $D.root 'ai_orders'
$text = @{}
foreach ($l in 'eng', 'rus') { $t = Join-Path $OpDir "text.text.loc_$l.bin.orig30"; if (Test-Path $t) { $text[$l] = New-Object Collections.Specialized.OrderedDictionary; foreach ($k in (Read-Text $t).keys) { $text[$l][$k.key] = [string[]]$k.items } } }
$forms = @{}; foreach ($f in $res.kids) { $forms[$f.name] = $f }
$plats = @{}; foreach ($p in $act.kids) { $plats[$p.name] = $p }
$uidRow = @{}; foreach ($r in $pp.rows) { $uidRow[[uint32]$r.c[0].v[0]] = $r }
$uids = @{}; foreach ($p in $act.kids) { $uids[[uint32](FU $p 'uid')] = 1 }
$usedCodes = @{}; foreach ($f in $res.kids) { $usedCodes[[int](FU $f 'code')] = 1 }
$log = New-Object Collections.Generic.List[string]
$liveLog = Join-Path $OpDir 'oob_12jul_live.txt'; Set-Content $liveLog ("oob_12jul.ps1 started {0}" -f (Get-Date)) -Encoding UTF8
function Say([string]$s) { $log.Add($s); Add-Content $liveLog $s -Encoding UTF8; if (-not $Quiet) { Write-Host $s } }   # the live log survives a crash
function Family([string]$root) { $out = @($root); $more = $true; while ($more) { $more = $false; foreach ($f in $res.kids) { if ($out -notcontains $f.name -and $out -contains (FS $f 'parent')) { $out += $f.name; $more = $true } } }; $out }
function Free-Code() { $c = 1; while ($usedCodes.ContainsKey($c)) { $c++ }; $usedCodes[$c] = 1; $c }
function Free-Hi([uint32]$pref) {
    $hi = $pref
    while ($true) { $clash = $false; foreach ($u in $uids.Keys) { if (($u -shr 12) -eq $hi) { $clash = $true; break } }; if (-not $clash) { return $hi }; $hi += 0x10000 }
}
function Sub([string]$s, [object[]]$subs) { foreach ($kv in $subs) { $s = $s.Replace($kv[0], $kv[1]) }; $s }
function Trim31([string]$s) { if ($s.Length -le 31) { return $s }; $t = $s -replace '([a-z])[aeiou]', '$1'; if ($t.Length -le 31) { return $t }; $t.Substring(0, 31) }

$formMap = @{}      # template formation -> new formation (for pool / parent references of the clone family)
$platMap = @{}      # template platoon -> new platoon (for slot tables)
$newText = @{ eng = New-Object Collections.Specialized.OrderedDictionary; rus = New-Object Collections.Specialized.OrderedDictionary }
$created = New-Object Collections.Generic.List[object]
$insertAfter = $null

function New-Formation([string]$tpl, [string]$new, [string]$parent, [int]$ext, [string]$nameE, [string]$nameR, [string]$oldPrefix, [string]$newPrefix, [object[]]$subE, [object[]]$subR, [uint32]$hiPref, [string]$exclude = '') {
    $T = $forms[$tpl]; if (-not $T) { throw "template formation $tpl not found" }
    $F = Clone-Node $T; $F.name = $new; $tplParent = FS $T 'parent'
    $key = 'op_' + $new.Substring(2)
    SetS $F 'name' $key; SetS $F 'parent' $parent; SetU $F 'ext_code' ([uint32]$ext); SetU $F 'code' ([uint32](Free-Code))
    $script:newText.eng[$key] = [string[]]@($nameE); $script:newText.rus[$key] = [string[]]@($nameR)
    $ix = if ($script:insertAfter) { $res.kids.IndexOf($script:insertAfter) + 1 } else { $res.kids.Count }
    $res.kids.Insert($ix, $F); $script:insertAfter = $F; $forms[$new] = $F; $formMap[$tpl] = $new
    $hi = Free-Hi $hiPref
    $n = 0
    $members = @($act.kids | Where-Object { (FS $_ 'pool') -eq $tpl })
    foreach ($p in $members) {
        if ($exclude -and $p.name -match $exclude) { continue }
        $Q = Clone-Node $p
        $nn = if ($p.name -match "^$oldPrefix") { $newPrefix + $p.name.Substring($Matches[0].Length) } else { $newPrefix + ($p.name -replace '^(ra|wer|we)_', '') }
        $nn = Trim31 $nn
        if ($plats.ContainsKey($nn)) { $k = 2; while ($plats.ContainsKey("$nn$k")) { $k++ }; $nn = Trim31 "$nn$k" }
        $Q.name = $nn; $platMap[$p.name] = $nn; $plats[$nn] = $Q
        $code = FU $p 'code'; $uid = ($hi -shl 12) -bor ($code -band 0xFFF); while ($uids.ContainsKey($uid)) { $uid += 0x1000 }; $uids[$uid] = 1
        SetU $Q 'uid' $uid
        foreach ($pf in 'pool', 'pool2', 'pool3', 'pool4') { $v = FS $Q $pf; if ($v) { SetS $Q $pf $(if ($v -eq $tpl) { $new } elseif ($v -eq $tplParent -and $parent) { $parent } elseif ($formMap.ContainsKey($v)) { $formMap[$v] } else { '' }) } }
        $tk = FS $p 'name'
        if ($tk -like 'op_*' -and $text.eng.Contains($tk)) {
            $nk = Trim31 ('op_' + $nn)
            if (-not $script:newText.eng.Contains($nk)) {
                $script:newText.eng[$nk] = [string[]]@($text.eng[$tk] | ForEach-Object { Sub $_ $subE })
                if ($text.rus -and $text.rus.Contains($tk)) { $script:newText.rus[$nk] = [string[]]@($text.rus[$tk] | ForEach-Object { Sub $_ $subR }) }
            }
            SetS $Q 'name' $nk
        }
        $act.kids.Add($Q)
        $row = $uidRow[[uint32](FU $p 'uid')]
        $c1 = if ($row) { Clone-Cell $row.c[1] } else { Cell-Decode 'a:1' }
        $pp.rows.Add(@{ name = $null; c = @((Cell-Decode "a:$uid;-1;-1;-1"), $c1) })
        $n++
    }
    # slot tables of the new battle groups: member names -> cloned names
    foreach ($p in @($act.kids | Where-Object { (FS $_ 'pool') -eq $new })) {
        $sl = Kid $p 'slots'; if (-not $sl) { continue }
        foreach ($r in $sl.rows) { $s = $r.c[0].s; if ($s -and $platMap.ContainsKey($s)) { $r.c[0] = @{ k = 2; v = (New-Object uint32[] 4); s = $platMap[$s] } } }   # other formations' platoons (artillery observers) are resolved in the final pass
    }
    $created.Add([pscustomobject]@{ name = $new; tpl = $tpl; platoons = $n; hi = $hi })
    Say ("  {0,-16} <- {1,-14} {2,3} platoons  uid hi 0x{3:x}  '{4}'" -f $new, $tpl, $n, $hi, $nameE)
}
function Delete-Family([string]$root) {
    $fam = Family $root; $nP = 0
    foreach ($fn in $fam) {
        $f = $forms[$fn]; if (-not $f) { continue }
        foreach ($p in @($act.kids | Where-Object { (FS $_ 'pool') -eq $fn })) {
            $u = [uint32](FU $p 'uid'); $act.kids.Remove($p) | Out-Null; $plats.Remove($p.name); $nP++
            $r = $uidRow[$u]; if ($r) { $pp.rows.Remove($r) | Out-Null }
            if ($aiO) { for ($i = $aiO.rows.Count - 1; $i -ge 0; $i--) { if ([uint32]($aiO.rows[$i].c[1].v[0]) -eq $u) { $aiO.rows.RemoveAt($i) } } }
        }
        $res.kids.Remove($f) | Out-Null; $forms.Remove($fn)
    }
    Say ("  deleted {0,-14} ({1} formations, {2} platoons)" -f $root, $fam.Count, $nP)
}
# references of the remaining platoons to deleted formations are blanked at the end


# ---------------------------------------------------------------- strengths and vehicle numbers (12 July 1943 states)
$VEH = @{   # class -> line squad regex, command suffixes are the same name + _com/_ccom/_bcom
    t34 = 'rn_rkka_t34_42'; t70 = 'rkka_t70_42'; kv = 'rn_rkka_kv1a'; su152 = 'rkka_su152'
    church = 'rkka_church3'; stuart = 'rkka_m3a1_stuart'   # Churchill III (6-pdr) and M3A1 Stuart squads of the game's div_units (Stalingrad-Donets DLC models)
    pz4 = 'wer_pz4gl'; pz3 = '(rn_wer_pz3late|rn_wer_pz3lg)'; tiger = 'rn_wer_pz6e'; t34g = 'wer_pz747r'; stug = 'wer_stug3f8'
}
$CONV = @{ t70 = @{ to = 't34'; line = 'rn_rkka_t34_42'; sprite = 'pl_t34_42' }; t34g = @{ to = 'pz4'; line = 'wer_pz4gl'; sprite = 'pl_pz4g' }
           kv = @{ to = 'church'; line = 'rkka_church3'; sprite = 'pl_mk4'; sfx = @{ _bcom = '_rcom' } }   # the Churchill regiments: KV-1 template sections -> Churchill III (its battalion command squad is _rcom)
           stuart = @{ to = 'stuart'; line = 'rkka_m3a1_stuart'; sprite = 'pl_stuart' } }               # 245 TR: T-70 sections -> M3A1 Stuart (value '>stuart' in the targets)
function Set-Strength([string]$form, [string]$params) {
    # params = "v:a;b;c;d" for every platoon of the formation that has a strength (battle-group nodes carry 0)
    $n = 0
    foreach ($p in @($act.kids | Where-Object { (FS $_ 'pool') -eq $form })) {
        $r = Fld $p 'params'; if (-not $r) { continue }
        if ([BitConverter]::ToSingle([BitConverter]::GetBytes([uint32]$r.c[0].v[0]), 0) -eq 0) { continue }
        $r.c[0] = Cell-Decode $params; $n++
    }
    $n
}
function Set-Vehicles([string]$form, [hashtable]$targets) {
    # targets: class -> number of vehicles in the formation (0 = convert the class, see $CONV, or leave it). Command
    # vehicles (company / battalion commands) stay; the line sections get 1..3 vehicles each to come close to the target.
    $fp = New-Object Collections.Generic.List[object]; foreach ($p in $act.kids) { if ((FS $p 'pool') -eq $form) { $fp.Add($p) } }
    foreach ($cls in $targets.Keys) {
        $tv = $targets[$cls]; $cv = $null
        if ($tv -is [string] -and $tv -match '^>(\w+)$') { $cv = $CONV[$Matches[1]] }        # explicit conversion target, e.g. t70 = '>stuart'
        elseif ($tv -eq 0 -and $CONV.ContainsKey($cls)) { $cv = $CONV[$cls] }
        if ($cv) {
            foreach ($p in $fp) {
                $pk = Kid $p 'pool'; if (-not $pk) { continue }; $hit = $false
                foreach ($r in $pk.rows) {
                    $sq = $r.c[0].s
                    if ($sq -match ('^' + $VEH[$cls] + '(_com|_ccom|_bcom)?$')) { $sfx = $Matches[1]; if ($cv.sfx -and $sfx -and $cv.sfx.ContainsKey($sfx)) { $sfx = $cv.sfx[$sfx] }; $r.c[0] = @{ k = 2; v = (New-Object uint32[] 4); s = ($cv.line + $sfx) }; $hit = $true }
                }
                if ($hit -and (FS $p 'str_sprite') -notmatch 'cmd|com') { SetS $p 'str_sprite' $cv.sprite }
            }
        }
    }
    $report = @()
    foreach ($cls in $targets.Keys) {
        if ($targets[$cls] -is [string]) { continue }
        $want = [int]$targets[$cls]; if ($want -le 0) { continue }
        $rx = '^' + $VEH[$cls] + '$'; $rxc = '^' + $VEH[$cls] + '(_com|_ccom|_bcom|_rcom)$'; $rxany = '^' + $VEH[$cls] + '(_com|_ccom|_bcom|_rcom)?$'
        $Gather = {
            [int]$gc = 0; $gl = New-Object Collections.Generic.List[object]; $gp = New-Object Collections.Generic.List[object]
            foreach ($p in $fp) {
                $pk = Kid $p 'pool'; if (-not $pk) { continue }; $isLine = $pk.rows.Count -gt 0; $hasLine = $false
                foreach ($r in $pk.rows) { $sq = $r.c[0].s; if ($sq -match $rxc) { $gc = $gc + [int]$r.c[1].v[0]; if ($sq -notmatch '_com$') { $isLine = $false } } elseif ($sq -match $rx) { $gl.Add($r); $hasLine = $true } else { $isLine = $false } }
                if ($isLine -and $hasLine) { $gp.Add($p) }
            }
            @{ cmd = $gc; lines = $gl; plats = $gp }
        }
        $G = & $Gather; [int]$cmd = $G.cmd; $lines = $G.lines; $linePlats = $G.plats
        if ($lines.Count -eq 0) { $report += "$cls none"; continue }
        # too many line platoons for the target: drop whole sections (last first), keep one
        while ($linePlats.Count -gt 1 -and ($cmd + $lines.Count) -gt $want) {
            $p = $linePlats[-1]; $u = [uint32](FU $p 'uid')
            $act.kids.Remove($p) | Out-Null; $fp.Remove($p) | Out-Null; $plats.Remove($p.name)
            for ($i = $pp.rows.Count - 1; $i -ge 0; $i--) { if ([uint32]($pp.rows[$i].c[0].v[0]) -eq $u) { $pp.rows.RemoveAt($i) } }
            foreach ($bg in $fp) { $sl = Kid $bg 'slots'; if ($sl) { foreach ($sr in $sl.rows) { if ($sr.c[0].s -eq $p.name) { $sr.c[0] = @{ k = 2; v = (New-Object uint32[] 4); s = '' } } } } }
            $G = & $Gather; [int]$cmd = $G.cmd; $lines = $G.lines; $linePlats = $G.plats
            if ($lines.Count -eq 0) { break }
        }
        # too few: duplicate line sections (3 vehicles each) until the target is reachable
        $guard = 0; $maxCode = 0; foreach ($p in $fp) { $c = FU $p 'code'; if ($c -gt $maxCode) { $maxCode = $c } }
        while ($linePlats.Count -gt 0 -and ($cmd + 3 * $lines.Count) -lt $want) {
            $src = $linePlats[-1]; $Q = Clone-Node $src; $maxCode++
            $nn = Trim31 ($src.name + 'x'); $k = 2; while ($plats.ContainsKey($nn)) { $nn = Trim31 ($src.name + 'x' + $k); $k++ }
            $Q.name = $nn; $plats[$nn] = $Q; SetU $Q 'code' ([uint32]$maxCode)
            $uid = (([uint32](FU $src 'uid')) -band 0xFFFFF000) -bor ([uint32]$maxCode -band 0xFFF); while ($uids.ContainsKey($uid)) { $uid += 0x1000 }; $uids[$uid] = 1; SetU $Q 'uid' $uid
            $sl = Kid $Q 'slots'; if ($sl) { $Q.kids.Remove($sl) | Out-Null }
            $act.kids.Add($Q); $fp.Add($Q); $pp.rows.Add(@{ name = $null; c = @((Cell-Decode "a:$uid;-1;-1;-1"), (Cell-Decode 'a:1')) })
            $G = & $Gather; [int]$cmd = $G.cmd; $lines = $G.lines; $linePlats = $G.plats
            if ($guard++ -gt 60) { break }
        }
        $per = [Math]::Round(($want - $cmd) / $lines.Count); if ($per -lt 1) { $per = 1 }; if ($per -gt 3) { $per = 3 }
        $tot = $cmd; $left = $want - $cmd
        foreach ($r in $lines) { $q = [Math]::Min($per, [Math]::Max(1, $left)); $v = New-Object uint32[] 4; $v[0] = [uint32]$q; $r.c[1] = @{ k = 6; v = $v; s = $null }; $tot += $q; $left -= $q }
        $report += "$cls $tot/$want"
    }
    $report -join ', '
}

# ---------------------------------------------------------------- 12 July 1943 order of battle
Say '# Soviet: 5 gds Tank Army'
$insertAfter = $forms['p_ra_rgk']
New-Formation 'p_ra_2ga' 'p_ra_5gta' '' 5 '5 gds TA' '5 гв.ТА' 'ra_2ga_' 'ra_5gta_' @() @() 0xc5
$insertAfter = $forms['p_ra_5gta']
# 18 TC
New-Formation 'p_ra_4mc' 'p_ra_18tc' 'p_ra_5gta' 18 '18 TC' '18 ТК' 'ra_4mc_' 'ra_18tc_' @(@('4 MC', '18 TC'), @('4 gds MC', '18 TC'), @('138 gds sap bn', '115 sap bn')) @(@('4 МК', '18 ТК'), @('4 гв.МК', '18 ТК'), @('138 гв.сапбн', '115 сапбн')) 0xc18
$tbE = { param($n, $c) @(@('2 gds MC, 1/37 gds TBde', "$c, 1/$n TBde"), @('2 gds MC, 2/37 gds TBde', "$c, 2/$n TBde"), @('2 gds MC, MRBn/37 gds TBde', "$c, MRBn/$n TBde"), @('37 gds TBde', "$n TBde"), @('37 TBde', "$n TBde")) }
$tbR = { param($n, $c) @(@('2 гв.МК, 1/37 гв.ТБр', "$c, 1/$n ТБр"), @('2 гв.МК, 2/37 гв.ТБр', "$c, 2/$n ТБр"), @('2 гв.МК, МСБн/37 гв.ТБр', "$c, МСБн/$n ТБр"), @('37 гв.ТБр', "$n ТБр"), @('37 ТБр', "$n ТБр")) }
$gtbE = { param($n, $c) @(@('4 gds MC, 1/36 gds TBde', "$c, 1/$n gds TBde"), @('4 gds MC, 2/36 gds TBde', "$c, 2/$n gds TBde"), @('4 gds MC, MRBn/36 gds TBde', "$c, MRBn/$n gds TBde"), @('36 gds TBde', "$n gds TBde"), @('36 TBde', "$n gds TBde")) }
$gtbR = { param($n, $c) @(@('4 гв.МК, 1/36 гв.ТБр', "$c, 1/$n гв.ТБр"), @('4 гв.МК, 2/36 гв.ТБр', "$c, 2/$n гв.ТБр"), @('4 гв.МК, МСБн/36 гв.ТБр', "$c, МСБн/$n гв.ТБр"), @('36 гв.ТБр', "$n гв.ТБр"), @('36 ТБр', "$n гв.ТБр")) }
$mbE = { param($n, $c, $kind) @(@('4 gds MC, 1/13 gds MBde', "$c, 1/$n $kind"), @('4 gds MC, 2/13 gds MBde', "$c, 2/$n $kind"), @('13 gds MBde', "$n $kind"), @('13 MBde', "$n $kind")) }
$mbR = { param($n, $c, $kind) @(@('4 гв.МК, 1/13 гв.МБр', "$c, 1/$n $kind"), @('4 гв.МК, 2/13 гв.МБр', "$c, 2/$n $kind"), @('13 гв.МБр', "$n $kind"), @('13 МБр', "$n $kind")) }
$mb14E = { param($n, $c, $kind) @(@('4 gds MC, 1/14 gds MBde', "$c, 1/$n $kind"), @('4 gds MC, 2/14 gds MBde', "$c, 2/$n $kind"), @('14 gds MBde', "$n $kind"), @('14 MBde', "$n $kind")) }
$mb14R = { param($n, $c, $kind) @(@('4 гв.МК, 1/14 гв.МБр', "$c, 1/$n $kind"), @('4 гв.МК, 2/14 гв.МБр', "$c, 2/$n $kind"), @('14 гв.МБр', "$n $kind"), @('14 МБр', "$n $kind")) }
foreach ($b in 110, 170, 181) { New-Formation 'p_ra_37tbde' "p_ra_${b}tbr" 'p_ra_18tc' $b "$b TBde" "$b ТБр" 'ra_37tbde_' "ra_${b}tbr_" (& $tbE $b '18 TC') (& $tbR $b '18 ТК') ([uint32]('0xb' + $b)) }
New-Formation 'p_ra_13mbde' 'p_ra_32mrbr' 'p_ra_18tc' 32 '32 MRBde' '32 МСБр' 'ra_13mbde_' 'ra_32mrbr_' (& $mbE 32 '18 TC' 'MRBde') (& $mbR 32 '18 ТК' 'МСБр') 0xb032
New-Formation 'p_ra_7tr' 'p_ra_36gtr' 'p_ra_18tc' 36 '36 gds hvy TR' '36 гв.ТТП' 'ra_7tr_' 'ra_36gtr_' @(@('2 gds A, 7 gds det BTR', '18 TC, 36 gds hvy TR'), @('7 BTR', '36 gds TR')) @(@('2 гв.А, 7 гв.оТПП', '18 ТК, 36 гв.оТТП'), @('7 ТПП', '36 гв.ТТП')) 0x36
# 29 TC
New-Formation 'p_ra_2mc' 'p_ra_29tc' 'p_ra_5gta' 29 '29 TC' '29 ТК' 'ra_2mc_' 'ra_29tc_' @(@('2 MC', '29 TC'), @('2 gds MC', '29 TC'), @('483 MTR', '271 MTR'), @('55 gds sap Bn', '193 sap bn'), @('744 gds det AT bn', '747 det AT bn')) @(@('2 МК', '29 ТК'), @('2 гв.МК', '29 ТК'), @('483 МП', '271 МП'), @('55 гв.сапбн', '193 сапбн'), @('744 гв.оиптадн', '747 оиптадн')) 0xc29
foreach ($b in 25, 31, 32) { New-Formation 'p_ra_37tbde' "p_ra_${b}tbr" 'p_ra_29tc' $b "$b TBde" "$b ТБр" 'ra_37tbde_' "ra_${b}tbr_" (& $tbE $b '29 TC') (& $tbR $b '29 ТК') ([uint32]('0xb' + $b)) }
New-Formation 'p_ra_13mbde' 'p_ra_53mrbr' 'p_ra_29tc' 53 '53 MRBde' '53 МСБр' 'ra_13mbde_' 'ra_53mrbr_' (& $mbE 53 '29 TC' 'MRBde') (& $mbR 53 '29 ТК' 'МСБр') 0xb053
New-Formation 'p_ra_1543tsap' 'p_ra_1446sap' 'p_ra_29tc' 1446 '1446 SPGR' '1446 САП' 'ra_1543(tsap|spgr)_' 'ra_1446sap_' @(@('2 gds A, 1/1543 hvy SPGR', '29 TC, 1/1446 SPGR'), @('1543 SPGR', '1446 SPGR'), @('1543', '1446')) @(@('2 гв.А, 1/1543 ТСАП', '29 ТК, 1/1446 САП'), @('1543 ТСАП', '1446 САП'), @('1543', '1446')) 0x1446
# 2 gds TC
New-Formation 'p_ra_4mc' 'p_ra_2gtc' 'p_ra_5gta' 2 '2 gds TC' '2 гв.ТК' 'ra_4mc_' 'ra_2gtc_' @(@('4 MC', '2 gds TC'), @('4 gds MC', '2 gds TC'), @('138 gds sap bn', '51 gds sap bn')) @(@('4 МК', '2 гв.ТК'), @('4 гв.МК', '2 гв.ТК'), @('138 гв.сапбн', '51 гв.сапбн')) 0xc2
foreach ($b in 4, 25, 26) { New-Formation 'p_ra_36tbde' "p_ra_${b}gtbr" 'p_ra_2gtc' $b "$b gds TBde" "$b гв.ТБр" 'ra_36tbde_' "ra_${b}gtbr_" (& $gtbE $b '2 gds TC') (& $gtbR $b '2 гв.ТК') ([uint32]('0xb' + $b + '0')) }
New-Formation 'p_ra_14mbde' 'p_ra_4gmrbr' 'p_ra_2gtc' 4 '4 gds MRBde' '4 гв.МСБр' 'ra_14mbde_' 'ra_4gmrbr_' (& $mb14E 4 '2 gds TC' 'gds MRBde') (& $mb14R 4 '2 гв.ТК' 'гв.МСБр') 0xb004
New-Formation 'p_ra_7tr' 'p_ra_47gtr' 'p_ra_2gtc' 47 '47 gds hvy TR' '47 гв.ТТП' 'ra_7tr_' 'ra_47gtr_' @(@('2 gds A, 7 gds det BTR', '2 gds TC, 47 gds hvy TR'), @('7 BTR', '47 gds TR')) @(@('2 гв.А, 7 гв.оТПП', '2 гв.ТК, 47 гв.оТТП'), @('7 ТПП', '47 гв.ТТП')) 0x47
# 2 TC
New-Formation 'p_ra_2mc' 'p_ra_2tc' 'p_ra_5gta' 2 '2 TC' '2 ТК' 'ra_2mc_' 'ra_2tc_' @(@('2 MC', '2 TC'), @('2 gds MC', '2 TC'), @('483 MTR', '269 MTR'), @('55 gds sap Bn', '51 sap bn'), @('744 gds det AT bn', '1502 det AT bn')) @(@('2 МК', '2 ТК'), @('2 гв.МК', '2 ТК'), @('483 МП', '269 МП'), @('55 гв.сапбн', '51 сапбн'), @('744 гв.оиптадн', '1502 оиптадн')) 0xc20
foreach ($b in 26, 99, 169) { New-Formation 'p_ra_37tbde' "p_ra_${b}tbr" 'p_ra_2tc' $b "$b TBde" "$b ТБр" 'ra_37tbde_' "ra_${b}tbr_" (& $tbE $b '2 TC') (& $tbR $b '2 ТК') ([uint32]('0xb' + $b)) }
New-Formation 'p_ra_13mbde' 'p_ra_58mrbr' 'p_ra_2tc' 58 '58 MRBde' '58 МСБр' 'ra_13mbde_' 'ra_58mrbr_' (& $mbE 58 '2 TC' 'MRBde') (& $mbR 58 '2 ТК' 'МСБр') 0xb058
# 10 July attachments: 11 MRBde of 10 TC (left behind at Vasilyevka / 226.6 until 12 July), 15 gds separate heavy TR (12 Churchill at Storozhevoye; KV-1 stands in)
New-Formation 'p_ra_13mbde' 'p_ra_11mrbr' 'p_ra_2tc' 11 '11 MRBde' '11 МСБр' 'ra_13mbde_' 'ra_11mrbr_' (& $mbE 11 '10 TC' 'MRBde') (& $mbR 11 '10 ТК' 'МСБр') 0xb011
New-Formation 'p_ra_7tr' 'p_ra_15gtr' 'p_ra_2tc' 15 '15 gds hvy TR' '15 гв.ТТП' 'ra_7tr_' 'ra_15gtr_' @(@('2 gds A, 7 gds det BTR', '2 TC, 15 gds hvy TR'), @('7 BTR', '15 gds TR')) @(@('2 гв.А, 7 гв.оТПП', '2 ТК, 15 гв.оТТП'), @('7 ТПП', '15 гв.ТТП')) 0x15
# 5 gds MC
New-Formation 'p_ra_4mc' 'p_ra_5gmc' 'p_ra_5gta' 5 '5 gds MC' '5 гв.МК' 'ra_4mc_' 'ra_5gmc_' @(@('4 MC', '5 gds MC'), @('4 gds MC', '5 gds MC'), @('138 gds sap bn', '68 gds sap bn')) @(@('4 МК', '5 гв.МК'), @('4 гв.МК', '5 гв.МК'), @('138 гв.сапбн', '68 гв.сапбн')) 0xc50
foreach ($b in 10, 11, 12) { New-Formation 'p_ra_13mbde' "p_ra_${b}gmbr" 'p_ra_5gmc' $b "$b gds MBde" "$b гв.МБр" 'ra_13mbde_' "ra_${b}gmbr_" (& $mbE $b '5 gds MC' 'gds MBde') (& $mbR $b '5 гв.МК' 'гв.МБр') ([uint32]('0xb' + $b + '0')) }
foreach ($pair in @(@(10, 51), @(11, 54), @(12, 55))) { $b = $pair[0]; $t = $pair[1]
    New-Formation 'p_ra_36tbde' "p_ra_${t}gtr" "p_ra_${b}gmbr" $t "$t gds TR" "$t гв.ТП" 'ra_36tbde_' "ra_${t}gtr_" @(@('4 gds MC, 1/36 gds TBde', "$b gds MBde, 1/$t gds TR"), @('4 gds MC, 2/36 gds TBde', "$b gds MBde, 2/$t gds TR"), @('4 gds MC, MRBn/36 gds TBde', "$b gds MBde, $t gds TR"), @('36 gds TBde', "$t gds TR"), @('36 TBde', "$t gds TR")) @(@('4 гв.МК, 1/36 гв.ТБр', "$b гв.МБр, 1/$t гв.ТП"), @('4 гв.МК, 2/36 гв.ТБр', "$b гв.МБр, 2/$t гв.ТП"), @('4 гв.МК, МСБн/36 гв.ТБр', "$b гв.МБр, $t гв.ТП"), @('36 гв.ТБр', "$t гв.ТП"), @('36 ТБр', "$t гв.ТП")) ([uint32]('0x' + $t + '00')) '^ra_36tbde_(mr|mrbn)' }
New-Formation 'p_ra_36tbde' 'p_ra_24gtbr' 'p_ra_5gmc' 24 '24 gds TBde' '24 гв.ТБр' 'ra_36tbde_' 'ra_24gtbr_' (& $gtbE 24 '5 gds MC') (& $gtbR 24 '5 гв.МК') 0xb240
New-Formation 'p_ra_1543tsap' 'p_ra_1529sap' 'p_ra_5gta' 1529 '1529 hvy SPGR' '1529 ТСАП' 'ra_1543(tsap|spgr)_' 'ra_1529sap_' @(@('2 gds A', '5 gds TA'), @('1543', '1529')) @(@('2 гв.А', '5 гв.ТА'), @('1543', '1529')) 0x1529
# 5 gds TA army troops: 29 AT Bde, 53 gds TR, 1549 SAP (SU-76/SU-122 - no such squads in this desc, SU-152 sections stand in)
New-Formation 'p_ra_1destr' 'p_ra_10iptabr' 'p_ra_5gta' 10 '10 AT Bde' '10 оИПТАБр' 'ra_1destr_' 'ra_10iptabr_' @(@('1 gds det AT Bde', '10 AT Bde'), @('1 IBr', '10 AT Bde'), @('2 gds A', '5 gds TA')) @(@('1 гв.оИБр', '10 оИПТАБр'), @('1 ИБр', '10 ИПТАБр'), @('2 гв.А', '5 гв.ТА')) 0xad10
New-Formation 'p_ra_36tbde' 'p_ra_53gtr' 'p_ra_5gta' 53 '53 gds TR' '53 гв.ТП' 'ra_36tbde_' 'ra_53gtr_' @(@('4 gds MC, 1/36 gds TBde', '5 gds TA, 1/53 gds TR'), @('4 gds MC, 2/36 gds TBde', '5 gds TA, 2/53 gds TR'), @('4 gds MC, MRBn/36 gds TBde', '5 gds TA, 53 gds TR'), @('36 gds TBde', '53 gds TR'), @('36 TBde', '53 gds TR')) @(@('4 гв.МК, 1/36 гв.ТБр', '5 гв.ТА, 1/53 гв.ТП'), @('4 гв.МК, 2/36 гв.ТБр', '5 гв.ТА, 2/53 гв.ТП'), @('4 гв.МК, МСБн/36 гв.ТБр', '5 гв.ТА, 53 гв.ТП'), @('36 гв.ТБр', '53 гв.ТП'), @('36 ТБр', '53 гв.ТП')) 0x5300 '^ra_36tbde_(mr|mrbn)'
New-Formation 'p_ra_1543tsap' 'p_ra_1549sap' 'p_ra_5gta' 1549 '1549 SPGR' '1549 САП' 'ra_1543(tsap|spgr)_' 'ra_1549sap_' @(@('2 gds A, 1/1543 hvy SPGR', '5 gds TA, 1/1549 SPGR'), @('1543 SPGR', '1549 SPGR'), @('2 gds A', '5 gds TA'), @('1543', '1549')) @(@('2 гв.А, 1/1543 ТСАП', '5 гв.ТА, 1/1549 САП'), @('1543 ТСАП', '1549 САП'), @('2 гв.А', '5 гв.ТА'), @('1543', '1549')) 0x1549
New-Formation 'p_ra_1543tsap' 'p_ra_1447sap' 'p_ra_5gmc' 1447 '1447 SPGR' '1447 САП' 'ra_1543(tsap|spgr)_' 'ra_1447sap_' @(@('2 gds A, 1/1543 hvy SPGR', '5 gds MC, 1/1447 SPGR'), @('1543 SPGR', '1447 SPGR'), @('2 gds A', '5 gds MC'), @('1543', '1447')) @(@('2 гв.А, 1/1543 ТСАП', '5 гв.МК, 1/1447 САП'), @('1543 ТСАП', '1447 САП'), @('2 гв.А', '5 гв.МК'), @('1543', '1447')) 0x1447
# 5 gds TA artillery group (army troops + Front reinforcement of 11 July: 678 HAR, 689 IPTAP, 76 gds MR, 27 GABr, 522 and 1148 HAR of high power, 16 and 80 gds MR)
$arX = '^ra_1012ar_(4b_hq|4b_1p|6b_hq|6b_1p)$'   # FO platoons and HQ only (the towed gun platoons of the 1012 AR pattern are 76 / 122 mm)
function New-ArtRgt([string]$new, [string]$parent, [int]$ext, [string]$nameE, [string]$nameR, [string]$prefix, [uint32]$hi, [string]$support, [string]$calE, [string]$calR, [string]$exclude = '') {
    New-Formation 'p_ra_1012ar' $new $parent $ext $nameE $nameR 'ra_1012ar_' $prefix @(@('1012 AR', $nameE), @('1012', $nameE)) @(@('1012 АП', $nameR), @('1012', $nameR)) $hi $exclude
    foreach ($p in @($act.kids | Where-Object { (FS $_ 'pool') -eq $new })) {
        $pk = Kid $p 'pool'; if (-not $pk) { continue }; $fo = $false
        foreach ($r in $pk.rows) { if ($r.c[0].s -eq 'rkka_corr_art' -and $r.c[4].s) { $r.c[4] = @{ k = 2; v = (New-Object uint32[] 4); s = $support }; $fo = $true } }
        if ($fo) { $bat = if ($p.name -match '(\d+)b_ac$') { $Matches[1] } else { '1' }; $nk = Trim31 ('op_' + $p.name); SetS $p 'name' $nk
            $script:newText.eng[$nk] = [string[]]@("$bat./$nameE, FO $calE"); $script:newText.rus[$nk] = [string[]]@("$bat./$nameR, НП $calR") }
    }
}
New-ArtRgt 'p_ra_678har' 'p_ra_5gta' 678 '678 HAR' '678 ГАП' 'ra_678har_' 0xa678 'rkka_artsup_m30_plat' '122 mm' '122 мм'
New-ArtRgt 'p_ra_27gabr' 'p_ra_5gta' 27 '27 GABr' '27 ПАБр' 'ra_27gabr_' 0xa027 'rkka_artsup_ml20x4_coy' '152 mm' '152 мм' $arX
New-ArtRgt 'p_ra_522har' 'p_ra_5gta' 522 '522 HAR (hvy)' '522 ГАП БМ' 'ra_522har_' 0xa522 'rkka_artsup_b4x2_plat' '203 mm' '203 мм' $arX
New-ArtRgt 'p_ra_1148har' 'p_ra_5gta' 1148 '1148 HAR (hvy)' '1148 ГАП БМ' 'ra_1148har_' 0x1148 'rkka_artsup_b4x2_plat' '203 mm' '203 мм' $arX
New-ArtRgt 'p_ra_76gmr' 'p_ra_5gta' 76 '76 gds MR' '76 гв.МП' 'ra_76gmr_' 0xa076 'rkka_artsup_bm13_plat' 'BM-13' 'БМ-13' $arX
New-ArtRgt 'p_ra_16gmr' 'p_ra_5gta' 16 '16 gds MR' '16 гв.МП' 'ra_16gmr_' 0xa016 'rkka_artsup_bm13_plat' 'BM-13' 'БМ-13' $arX
New-ArtRgt 'p_ra_80gmr' 'p_ra_5gta' 80 '80 gds MR' '80 гв.МП' 'ra_80gmr_' 0xa080 'rkka_artsup_bm13_plat' 'BM-13' 'БМ-13' $arX
New-Formation 'p_ra_1destr' 'p_ra_689iptap' 'p_ra_5gta' 689 '689 AT Rgt' '689 ИПТАП' 'ra_1destr_' 'ra_689iptap_' @(@('1 gds det AT Bde', '689 AT Rgt'), @('1 IBr', '689 IPTAP'), @('2 gds A', '5 gds TA')) @(@('1 гв.оИБр', '689 ИПТАП'), @('1 ИБр', '689 ИПТАП'), @('2 гв.А', '5 гв.ТА')) 0x689 '^ra_1destr_(smgc|atbn|engbn|atr_|mt_|1mt|2mt|ac82|[123]$)'

Say '# Soviet: 5 gds Army'
New-Formation 'p_ra_5atka' 'p_ra_5ga' '' 5 '5 gds A' '5 гв.А' 'ra_5atka_' 'ra_5ga_' @() @() 0xc55
New-Formation 'p_ra_13rc' 'p_ra_33grc' 'p_ra_5ga' 33 '33 gds RC' '33 гв.СК' 'ra_13rc_' 'ra_33grc_' @(@('13 RC', '33 gds RC'), @('13 gds RC', '33 gds RC'), @('51 gds sap bn', '7 gds sap bn')) @(@('13 СК', '33 гв.СК'), @('13 гв.СК', '33 гв.СК'), @('51 гв.сапбн', '7 гв.сапбн')) 0xc33
# 9 gds Airborne Div (24 gds RD pattern)
New-Formation 'p_ra_24rd' 'p_ra_9gabd' 'p_ra_33grc' 9 '9 gds AB Div' '9 гв.ВДД' 'ra_24rd_' 'ra_9gabd_' @(@('24 gds RD', '9 gds AB Div'), @('24 RD', '9 AB Div'), @('484 MTR', '1 MTR'), @('485 MTR', '2 MTR')) @(@('24 гв.СД', '9 гв.ВДД'), @('24 СД', '9 ВДД'), @('484 МП', '1 МП'), @('485 МП', '2 МП')) 0x9
foreach ($pair in @(@(70, 23), @(71, 26), @(72, 28))) { $o = $pair[0]; $n = $pair[1]
    New-Formation "p_ra_${o}rr" "p_ra_${n}gabr" 'p_ra_9gabd' $n "$n gds AB Rgt" "$n гв.ВДСП" "ra_${o}_" "ra_${n}gab_" @(@("24 gds RD, 1/$o gds RR", "9 gds AB Div, 1/$n gds AB Rgt"), @("24 gds RD, 2/$o gds RR", "9 gds AB Div, 2/$n gds AB Rgt"), @("24 gds RD, 3/$o gds RR", "9 gds AB Div, 3/$n gds AB Rgt"), @("$o gds RR", "$n gds AB Rgt"), @("$o RR", "$n AB Rgt"), @("/$o", "/$n")) @(@("24 гв.СД, 1/$o гв.СП", "9 гв.ВДД, 1/$n гв.ВДСП"), @("24 гв.СД, 2/$o гв.СП", "9 гв.ВДД, 2/$n гв.ВДСП"), @("24 гв.СД, 3/$o гв.СП", "9 гв.ВДД, 3/$n гв.ВДСП"), @("$o гв.СП", "$n гв.ВДСП"), @("$o СП", "$n ВДСП"), @("/$o", "/$n")) ([uint32]('0x' + $n + '0')) }
New-Formation 'p_ra_50ar' 'p_ra_7gabar' 'p_ra_9gabd' 7 '7 gds AB AR' '7 гв.ВДАП' 'ra_50ar_' 'ra_7gabar_' @(@('50 gds LAR', '7 gds AB AR'), @('50 LAR', '7 AB AR'), @('50 AR', '7 AB AR')) @(@('50 гв.ЛАП', '7 гв.ВДАП'), @('50 ЛАП', '7 ВДАП'), @('50 АП', '7 ВДАП')) 0xa007
# 95 gds RD (96 gds RD pattern)
New-Formation 'p_ra_96rd' 'p_ra_95grd' 'p_ra_33grc' 95 '95 gds RD' '95 гв.СД' 'ra_96rd_' 'ra_95grd_' @(@('96 gds RD', '95 gds RD'), @('96 RD', '95 RD')) @(@('96 гв.СД', '95 гв.СД'), @('96 СД', '95 СД')) 0x95
foreach ($pair in @(@(291, 284), @(293, 287), @(295, 290))) { $o = $pair[0]; $n = $pair[1]
    New-Formation "p_ra_${o}rr" "p_ra_${n}grr" 'p_ra_95grd' $n "$n gds RR" "$n гв.СП" "ra_${o}_" "ra_${n}_" @(@("96 gds RD", "95 gds RD"), @("$o gds RR", "$n gds RR"), @("$o RR", "$n RR"), @("/$o", "/$n")) @(@("96 гв.СД", "95 гв.СД"), @("$o гв.СП", "$n гв.СП"), @("$o СП", "$n СП"), @("/$o", "/$n")) ([uint32]('0x' + $n)) }
New-Formation 'p_ra_234ar' 'p_ra_233gar' 'p_ra_95grd' 233 '233 gds AR' '233 гв.АП' 'ra_234ar_' 'ra_233ar_' @(@('234 gds AR', '233 gds AR'), @('234 AR', '233 AR'), @('234', '233')) @(@('234 гв.АП', '233 гв.АП'), @('234 АП', '233 АП'), @('234', '233')) 0xa233
# 42 gds RD (34 gds RD pattern)
New-Formation 'p_ra_34rd' 'p_ra_42grd' 'p_ra_33grc' 42 '42 gds RD' '42 гв.СД' 'ra_34rd_' 'ra_42grd_' @(@('34 gds RD', '42 gds RD'), @('34 RD', '42 RD')) @(@('34 гв.СД', '42 гв.СД'), @('34 СД', '42 СД')) 0x42
foreach ($pair in @(@(103, 127), @(105, 132), @(107, 136))) { $o = $pair[0]; $n = $pair[1]
    New-Formation "p_ra_${o}rr" "p_ra_${n}grr" 'p_ra_42grd' $n "$n gds RR" "$n гв.СП" "ra_${o}_" "ra_${n}_" @(@("34 gds RD", "42 gds RD"), @("$o gds RR", "$n gds RR"), @("$o RR", "$n RR"), @("/$o", "/$n")) @(@("34 гв.СД", "42 гв.СД"), @("$o гв.СП", "$n гв.СП"), @("$o СП", "$n СП"), @("/$o", "/$n")) ([uint32]('0x' + $n)) }
New-Formation 'p_ra_84ar' 'p_ra_91gar' 'p_ra_42grd' 91 '91 gds AR' '91 гв.АП' 'ra_84ar_' 'ra_91ar_' @(@('84 gds AR', '91 gds AR'), @('84 AR', '91 AR'), @('84', '91')) @(@('84 гв.АП', '91 гв.АП'), @('84 АП', '91 АП'), @('84', '91')) 0xa091
# 52 gds RD (3 gds RD pattern), under 5 gds A
New-Formation 'p_ra_3rd' 'p_ra_52grd' 'p_ra_5ga' 52 '52 gds RD' '52 гв.СД' 'ra_3rd_' 'ra_52grd_' @(@('3 gds RD', '52 gds RD'), @('3 RD', '52 RD')) @(@('3 гв.СД', '52 гв.СД'), @('3 СД', '52 СД')) 0x52
foreach ($pair in @(@(5, 151), @(9, 153), @(13, 155))) { $o = $pair[0]; $n = $pair[1]
    New-Formation "p_ra_${o}rr" "p_ra_${n}grr" 'p_ra_52grd' $n "$n gds RR" "$n гв.СП" "ra_${o}_" "ra_${n}_" @(@("3 gds RD", "52 gds RD"), @("$o gds RR", "$n gds RR"), @("$o RR", "$n RR"), @("/$o ", "/$n "), @("/$o", "/$n")) @(@("3 гв.СД", "52 гв.СД"), @("$o гв.СП", "$n гв.СП"), @("$o СП", "$n СП"), @("/$o", "/$n")) ([uint32]('0x' + $n)) }
New-Formation 'p_ra_22ar' 'p_ra_124gar' 'p_ra_52grd' 124 '124 gds AR' '124 гв.АП' 'ra_22ar_' 'ra_124ar_' @(@('22 gds AR', '124 gds AR'), @('22 AR', '124 AR'), @('/22', '/124')) @(@('22 гв.АП', '124 гв.АП'), @('22 АП', '124 АП'), @('/22', '/124')) 0xa124
# 245 separate TR (M3 Lee / Stuart: T-34 / T-70 sections stand in) - the tank company with 52 gds RD on 10 July
New-Formation 'p_ra_36tbde' 'p_ra_245otp' 'p_ra_52grd' 245 '245 TR' '245 оТП' 'ra_36tbde_' 'ra_245otp_' @(@('4 gds MC, 1/36 gds TBde', '52 gds RD, 1/245 TR'), @('4 gds MC, 2/36 gds TBde', '52 gds RD, 2/245 TR'), @('4 gds MC, MRBn/36 gds TBde', '52 gds RD, 245 TR'), @('36 gds TBde', '245 TR'), @('36 TBde', '245 TR')) @(@('4 гв.МК, 1/36 гв.ТБр', '52 гв.СД, 1/245 ТП'), @('4 гв.МК, 2/36 гв.ТБр', '52 гв.СД, 2/245 ТП'), @('4 гв.МК, МСБн/36 гв.ТБр', '52 гв.СД, 245 ТП'), @('36 гв.ТБр', '245 ТП'), @('36 ТБр', '245 ТП')) 0x245 '^ra_36tbde_(mr|mrbn)'
# 183 RD (315 RD pattern) under 48 RC
New-Formation 'p_ra_31rc' 'p_ra_48rc' 'p_ra_5ga' 48 '48 RC' '48 СК' 'ra_31rc_' 'ra_48rc_' @(@('31 gds RC', '48 RC'), @('31 RC', '48 RC')) @(@('31 гв.СК', '48 СК'), @('31 СК', '48 СК')) 0xc48
New-Formation 'p_ra_315rd' 'p_ra_183rd' 'p_ra_48rc' 183 '183 RD' '183 СД' 'ra_315rd_' 'ra_183rd_' @(@('315 RD', '183 RD')) @(@('315 СД', '183 СД')) 0x183
foreach ($pair in @(@(362, 227), @(724, 285), @(1328, 295))) { $o = $pair[0]; $n = $pair[1]
    $fn = if ($forms.ContainsKey("p_ra_${n}rr")) { "p_ra_${n}rr_183" } else { "p_ra_${n}rr" }   # 295 RR: the vanilla 96 gds RD has a p_ra_295rr too
    New-Formation "p_ra_${o}rr" $fn 'p_ra_183rd' $n "$n RR" "$n СП" "ra_${o}_" "ra_${n}_" @(@("315 RD", "183 RD"), @("$o RR", "$n RR"), @("/$o", "/$n")) @(@("315 СД", "183 СД"), @("$o СП", "$n СП"), @("/$o", "/$n")) ([uint32]('0x' + $n)) }
New-Formation 'p_ra_1012ar' 'p_ra_623ar' 'p_ra_183rd' 623 '623 AR' '623 АП' 'ra_1012ar_' 'ra_623ar_' @(@('1012 AR', '623 AR'), @('1012', '623')) @(@('1012 АП', '623 АП'), @('1012', '623')) 0xa623
# 27 AT Bde (Front anti-tank reserve at Prokhorovka on 10 July, under 69 A / 48 RC here)
New-Formation 'p_ra_1destr' 'p_ra_27iptabr' 'p_ra_48rc' 27 '27 AT Bde' '27 оИПТАБр' 'ra_1destr_' 'ra_27iptabr_' @(@('1 gds det AT Bde', '27 AT Bde'), @('1 IBr', '27 AT Bde'), @('2 gds A', '69 A')) @(@('1 гв.оИБр', '27 оИПТАБр'), @('1 ИБр', '27 ИПТАБр'), @('2 гв.А', '69 А')) 0xad27
New-Formation 'p_ra_1destr' 'p_ra_29iptabr' 'p_ra_5ga' 29 '29 AT Bde' '29 оИПТАБр' 'ra_1destr_' 'ra_29iptabr_' @(@('1 gds det AT Bde', '29 AT Bde'), @('1 IBr', '29 AT Bde'), @('2 gds A', '5 gds A')) @(@('1 гв.оИБр', '29 оИПТАБр'), @('1 ИБр', '29 ИПТАБр'), @('2 гв.А', '5 гв.А')) 0xad29
# 97 gds RD (96 gds RD pattern) - 33 gds RC second echelon, enters from the north
New-Formation 'p_ra_96rd' 'p_ra_97grd' 'p_ra_33grc' 97 '97 gds RD' '97 гв.СД' 'ra_96rd_' 'ra_97grd_' @(@('96 gds RD', '97 gds RD'), @('96 RD', '97 RD')) @(@('96 гв.СД', '97 гв.СД'), @('96 СД', '97 СД')) 0x97
foreach ($pair in @(@(291, 289), @(293, 292), @(295, 294))) { $o = $pair[0]; $n = $pair[1]
    New-Formation "p_ra_${o}rr" "p_ra_${n}grr" 'p_ra_97grd' $n "$n gds RR" "$n гв.СП" "ra_${o}_" "ra_${n}_" @(@("96 gds RD", "97 gds RD"), @("$o gds RR", "$n gds RR"), @("$o RR", "$n RR"), @("/$o", "/$n")) @(@("96 гв.СД", "97 гв.СД"), @("$o гв.СП", "$n гв.СП"), @("$o СП", "$n СП"), @("/$o", "/$n")) ([uint32]('0x' + $n)) }
New-Formation 'p_ra_234ar' 'p_ra_232gar' 'p_ra_97grd' 232 '232 gds AR' '232 гв.АП' 'ra_234ar_' 'ra_232ar_' @(@('234 gds AR', '232 gds AR'), @('234 AR', '232 AR'), @('234', '232')) @(@('234 гв.АП', '232 гв.АП'), @('234 АП', '232 АП'), @('234', '232')) 0xa232
# 13 gds RD (34 gds RD pattern) - 33 gds RC second echelon
New-Formation 'p_ra_34rd' 'p_ra_13grd' 'p_ra_33grc' 13 '13 gds RD' '13 гв.СД' 'ra_34rd_' 'ra_13grd_' @(@('34 gds RD', '13 gds RD'), @('34 RD', '13 RD')) @(@('34 гв.СД', '13 гв.СД'), @('34 СД', '13 СД')) 0x13
foreach ($pair in @(@(103, 34), @(105, 39), @(107, 42))) { $o = $pair[0]; $n = $pair[1]
    New-Formation "p_ra_${o}rr" "p_ra_${n}grr" 'p_ra_13grd' $n "$n gds RR" "$n гв.СП" "ra_${o}_" "ra_${n}_" @(@("34 gds RD", "13 gds RD"), @("$o gds RR", "$n gds RR"), @("$o RR", "$n RR"), @("/$o", "/$n")) @(@("34 гв.СД", "13 гв.СД"), @("$o гв.СП", "$n гв.СП"), @("$o СП", "$n СП"), @("/$o", "/$n")) ([uint32]('0x' + $n)) }
New-Formation 'p_ra_84ar' 'p_ra_32gar' 'p_ra_13grd' 32 '32 gds AR' '32 гв.АП' 'ra_84ar_' 'ra_32ar_' @(@('84 gds AR', '32 gds AR'), @('84 AR', '32 AR'), @('84', '32')) @(@('84 гв.АП', '32 гв.АП'), @('84 АП', '32 АП'), @('84', '32')) 0xa032
# 5 gds A army troops: 301 and 1510 IPTAP (HQ and the 76 mm gun companies of the 1 destr Bde pattern), 148 and 93 gds TR (Churchills - no such squads, KV sections stand in)
$iptapX = '^ra_1destr_(smgc|atbn|engbn|atr_|mt_|1mt|2mt|ac82|[123]$)'   # keep the HQ and the four 76 mm gun companies (the atr_* companies are AT rifles)
New-Formation 'p_ra_1destr' 'p_ra_301iptap' 'p_ra_5ga' 301 '301 AT Rgt' '301 ИПТАП' 'ra_1destr_' 'ra_301iptap_' @(@('1 gds det AT Bde', '301 AT Rgt'), @('1 IBr', '301 IPTAP'), @('2 gds A', '5 gds A')) @(@('1 гв.оИБр', '301 ИПТАП'), @('1 ИБр', '301 ИПТАП'), @('2 гв.А', '5 гв.А')) 0x301 $iptapX
New-Formation 'p_ra_1destr' 'p_ra_1510iptap' 'p_ra_5ga' 1510 '1510 AT Rgt' '1510 ИПТАП' 'ra_1destr_' 'ra_1510iptap_' @(@('1 gds det AT Bde', '1510 AT Rgt'), @('1 IBr', '1510 IPTAP'), @('2 gds A', '5 gds A')) @(@('1 гв.оИБр', '1510 ИПТАП'), @('1 ИБр', '1510 ИПТАП'), @('2 гв.А', '5 гв.А')) 0x1510 $iptapX
New-Formation 'p_ra_7tr' 'p_ra_148gtr' 'p_ra_5ga' 148 '148 gds TR' '148 гв.ТП' 'ra_7tr_' 'ra_148gtr_' @(@('2 gds A, 7 gds det BTR', '5 gds A, 148 gds TR'), @('7 BTR', '148 gds TR')) @(@('2 гв.А, 7 гв.оТПП', '5 гв.А, 148 гв.оТП'), @('7 ТПП', '148 гв.ТП')) 0x148
New-Formation 'p_ra_7tr' 'p_ra_93gtr' 'p_ra_5ga' 93 '93 gds TR' '93 гв.ТП' 'ra_7tr_' 'ra_93gtr_' @(@('2 gds A, 7 gds det BTR', '5 gds A, 93 gds TR'), @('7 BTR', '93 gds TR')) @(@('2 гв.А, 7 гв.оТПП', '5 гв.А, 93 гв.оТП'), @('7 ТПП', '93 гв.ТП')) 0x93

Say '# German: LSSAH from the Das Reich pattern'
$insertAfter = $forms['p_we_dr']
New-Formation 'p_we_dr' 'p_we_lah' 'p_we_2tc_ss' 1 'MID SS "LSSAH"' 'МПД СС "ЛАГ"' 'we_dr_' 'we_lah_' @(@('SS Reich', 'SS LAH'), @('MID SS "Das Reich"', 'MID SS "LSSAH"'), @('52 MTR', '55 MTR'), @('140 AR', '1 AR SS'), @('72 AR', 'IV./1 AR SS'), @('/2 recon', '/1 recon'), @('/2 eng', '/1 eng')) @(@('СС Рейх', 'СС ЛАГ'), @('МПД СС "Рейх"', 'МПД СС "ЛАГ"'), @('52 МП', '55 МП'), @('140 АП', '1 АП СС'), @('72 АП', 'IV./1 АП СС'), @('/2 разв', '/1 разв'), @('/2 сап', '/1 сап')) 0x8001
New-Formation 'p_we_dr_3mir' 'p_we_lah_1mir' 'p_we_lah' 1 '1 MIR SS "LSSAH"' '1 МПП СС "ЛАГ"' 'we_dr_3mir_' 'we_lah_1mir_' @(@('MID SS "Das Reich"', 'MID SS "LSSAH"'), @('3 MIR SS "Deutschland"', '1 MIR SS "LSSAH"'), @('/3 SS', '/1 SS'), @('3 SS', '1 SS')) @(@('МПД СС "Рейх"', 'МПД СС "ЛАГ"'), @('3 МПП СС "Германия"', '1 МПП СС "ЛАГ"'), @('/3 СС', '/1 СС'), @('3 СС', '1 СС')) 0x80d1
New-Formation 'p_we_dr_4mir' 'p_we_lah_2mir' 'p_we_lah' 2 '2 MIR SS "LSSAH"' '2 МПП СС "ЛАГ"' 'we_dr_4mir_' 'we_lah_2mir_' @(@('MID SS "Das Reich"', 'MID SS "LSSAH"'), @('4 MIR SS "Der Fuhrer"', '2 MIR SS "LSSAH"'), @('/4 SS', '/2 SS'), @('4 SS', '2 SS')) @(@('МПД СС "Рейх"', 'МПД СС "ЛАГ"'), @('4 МПП СС "Фюрер"', '2 МПП СС "ЛАГ"'), @('/4 СС', '/2 СС'), @('4 СС', '2 СС')) 0x80d2
New-Formation 'p_we_dr_tr' 'p_we_lah_tr' 'p_we_lah' 1 '1 TR SS' '1 ТП СС' 'we_dr_tr' 'we_lah_tr' @(@('MID SS "Das Reich"', 'MID SS "LSSAH"'), @('1./2 TR', '5./1 TR'), @('2./2 TR', '6./1 TR'), @('4./2 TR', '7./1 TR'), @('8./2 TR', '13./1 TR'), @('/2 TR', '/1 TR'), @('2 TR SS', '1 TR SS')) @(@('МПД СС "Рейх"', 'МПД СС "ЛАГ"'), @('1./2 ТП', '5./1 ТП'), @('2./2 ТП', '6./1 ТП'), @('4./2 ТП', '7./1 ТП'), @('8./2 ТП', '13./1 ТП'), @('/2 ТП', '/1 ТП'), @('2 ТП СС', '1 ТП СС')) 0x80f1
New-Formation 'p_we_dr_stug' 'p_we_lah_stug' 'p_we_lah' 1 '1 SPG Bn SS' '1 бн САУ СС' 'we_dr_stug' 'we_lah_stug' @(@('MID SS "Das Reich"', 'MID SS "LSSAH"'), @('2 SPG', '1 SPG')) @(@('МПД СС "Рейх"', 'МПД СС "ЛАГ"'), @('2 бн САУ', '1 бн САУ')) 0x80e1
New-Formation 'p_we_dr_2at' 'p_we_lah_1at' 'p_we_lah' 1 '1 AT bn SS' '1 ПТ бн СС' 'we_dr_2at' 'we_lah_1at' @(@('MID SS "Das Reich"', 'MID SS "LSSAH"'), @('2 AT', '1 AT')) @(@('МПД СС "Рейх"', 'МПД СС "ЛАГ"'), @('2 ПТ', '1 ПТ')) 0xd0f1
New-Formation 'p_we_dr_ar' 'p_we_lah_ar' 'p_we_lah' 1 '1 AR SS' '1 АП СС' 'we_dr_ar' 'we_lah_ar' @(@('MID SS "Das Reich"', 'MID SS "LSSAH"'), @('DR AR', 'LAH AR'), @('2 AR', '1 AR')) @(@('МПД СС "Рейх"', 'МПД СС "ЛАГ"'), @('АП ДР', 'АП ЛАГ'), @('2 АП', '1 АП')) 0x80a1

Say '# strengths and vehicle numbers (morning 10 July 1943 for the units on the map, 11 July states for 5 gds TA: Zamulin / Lawrence tables)'
$fresh = 'v:0.5;0.5;1;0.1'; $worn = 'v:0.5;0.5;0.6;0.2'; $ger = 'v:0.5;0.6;0.8;0.2'; $gerTk = 'v:0.5;0.6;0.85;0.15'
$strength = @{}
foreach ($f in $forms.Keys) { if ($f -match '^p_ra_(5gta|18tc|29tc|2gtc|5gmc|\d+tbr|\d+gtbr|\d+mrbr|\d+gmrbr|\d+gmbr|\d+gtr|\d+sap|9gabd|\d+gabr|\d+gabar|95grd|97grd|13grd|\d+grr|\d+gar|33grc|5ga|\d+iptabr|\d+iptap|\d+har|\d+gabr|\d+gmr)$') { $strength[$f] = $fresh } }
foreach ($f in 'p_ra_2tc', 'p_ra_26tbr', 'p_ra_99tbr', 'p_ra_169tbr', 'p_ra_58mrbr', 'p_ra_11mrbr', 'p_ra_15gtr', 'p_ra_52grd', 'p_ra_151grr', 'p_ra_153grr', 'p_ra_155grr', 'p_ra_124gar', 'p_ra_245otp', 'p_ra_48rc', 'p_ra_183rd', 'p_ra_227rr', 'p_ra_285rr', 'p_ra_295rr', 'p_ra_623ar') { $strength[$f] = $worn }
foreach ($f in 'p_ra_27iptabr', 'p_ra_2gtc', 'p_ra_4gtbr', 'p_ra_25gtbr', 'p_ra_26gtbr', 'p_ra_4gmrbr', 'p_ra_47gtr') { $strength[$f] = $fresh }
foreach ($f in $forms.Keys) { if ($f -match '^p_we_(lah|dr)') { $strength[$f] = $ger } elseif ($f -match '^p_we_tk') { $strength[$f] = $gerTk } }
$ns = 0; $na = 0
foreach ($p in $act.kids) {
    $f = FS $p 'pool'; if (-not $strength.ContainsKey($f)) { continue }
    $r = Fld $p 'params'; if (-not $r) { continue }
    if ([BitConverter]::ToSingle([BitConverter]::GetBytes([uint32]$r.c[0].v[0]), 0) -eq 0) { continue }
    $v = $strength[$f]
    # the third parameter is the manning fraction: vanilla keeps it at 1 for every armoured platoon (a 0.6 brigade gave
    # T-34s 2-3 men and T-70s a single man); the vehicle NUMBERS carry the losses (Set-Vehicles below)
    if ((FS $p 'str_sprite') -match '^(pl_(t34|t70|kv|su\d|stug|pz|sdkfz|ba\d|m3|marder|hummel|wespe|grille|bison|t60|mk|churchill|lee|stuart)|plu_(tankcmd|tankbncmd|bde_tank|rgt_tank))') {
        $q = $v.Substring(2).Split(';'); if ($q.Count -ge 3) { $q[2] = '1' }; $v = 'v:' + ($q -join ';'); $na++
    }
    $r.c[0] = Cell-Decode $v; $ns++
}
Say "  strength parameters set on $ns platoons ($na armoured platoons kept at full crews)"
$tanks = [ordered]@{
    # Soviet: Zamulin, Demolishing the Myth, Table 18 (5 gds TA at 17:00 11 July 1943, runners; TsAMO f. 332 / 18 tk / 29 tk)
    p_ra_110tbr = @{ t34 = 22; t70 = 21 }; p_ra_170tbr = @{ t34 = 22; t70 = 17 }; p_ra_181tbr = @{ t34 = 24; t70 = 20 }; p_ra_36gtr = @{ kv = 0; church = 18 }   # 18 TC: 36 gds hvy TR = 18 Churchill III
    p_ra_25tbr = @{ t34 = 31; t70 = 36 }; p_ra_31tbr = @{ t34 = 29; t70 = 38 }; p_ra_32tbr = @{ t70 = 0; t34 = 63 }; p_ra_1446sap = @{ su152 = 21 }   # 29 TC; 1446 SAP = 10 SU-76 + 11 SU-122 (SU-152 stands in)
    p_ra_4gtbr = @{ t34 = 28; t70 = 17 }; p_ra_25gtbr = @{ t34 = 28; t70 = 17 }; p_ra_26gtbr = @{ t34 = 27; t70 = 16 }; p_ra_47gtr = @{ kv = 0; church = 8 }   # 2 gds TC at 0800 10 July: 141 operational tanks, brigades at 88-89 % (Zamulin); 47 gds hvy TR Churchills
    p_ra_26tbr = @{ t34 = 16; t70 = 15 }; p_ra_99tbr = @{ t34 = 14; t70 = 15 }; p_ra_169tbr = @{ t34 = 16; t70 = 13 }; p_ra_15gtr = @{ kv = 0; church = 12 }   # 2 TC at 0800 10 July: 89 tanks in the three brigades (43 T-70), 58 / 55 / 55 % of 53 (Zamulin); 15 gds hvy TR 12 Churchill
    p_ra_245otp = @{ t34 = 6; t70 = '>stuart'; stuart = 4 }   # the tank company of 245 sep. TR with 52 gds RD: M3 Lee (T-34 stands in - no Lee in the game) and M3A1 Stuart
    p_ra_24gtbr = @{ t34 = 48; t70 = 0 }; p_ra_51gtr = @{ t34 = 30; t70 = 14 }; p_ra_54gtr = @{ t34 = 16; t70 = 15 }; p_ra_55gtr = @{ t34 = 20; t70 = 15 }; p_ra_1447sap = @{ su152 = 11 }   # 5 gds MC (0200 12 July): 10 / 11 / 12 gds MBde tank regiments; 1447 SAP = 4 SU-76 + 7 SU-122
    p_ra_53gtr = @{ t34 = 39; t70 = 1 }; p_ra_1529sap = @{ su152 = 11 }; p_ra_1549sap = @{ su152 = 11 }   # army troops; 1529 = 11 SU-152 + 1 KV; 1549 not in the table - same size assumed
    p_ra_148gtr = @{ kv = 0; church = 15 }; p_ra_93gtr = @{ kv = 0; church = 15 }   # 5 gds A separate tank regiments, Churchills (no 11 July return found - unchanged)
    # German: Zetterling / Frankson via Zamulin Table 17 (II SS Pz Corps, 18:35 11 July 1943, operational)
    # II SS Pz Corps at 1905 9 July (Zetterling / Frankson via Zamulin Table 11): the 10 July start
    p_we_lah_tr = @{ t34g = 0; pz4 = 32; pz3 = 4; tiger = 4 }; p_we_lah_stug = @{ stug = 22 }   # LSSAH: 4 Pz II, 4 Pz III, 32 Pz IV, 4 Tiger, 5 command, 22 StuG = 71
    p_we_dr_tr = @{ pz4 = 13; pz3 = 31; t34g = 7; tiger = 1 }; p_we_dr_stug = @{ stug = 26 }   # DR: 31 Pz III, 13 Pz IV, 1 Tiger, 7 T-34, 7 command, 26 StuG = 85
    p_we_tk_tr = @{ pz4 = 27; pz3 = 47; tiger = 2 }; p_we_tk_stug = @{ stug = 12 }   # T: 47 Pz III, 20 Pz IV L43/48 + 7 L24, 2 Tiger, 5 command, 12 StuG = 93
}
foreach ($f in $tanks.Keys) { Say ("  {0,-14} {1}" -f $f, (Set-Vehicles $f $tanks[$f])) }

Say '# removing the Mius formations'

foreach ($root in 'p_ra_5atka', 'p_ra_2ga', 'p_ra_28a', 'p_we_6a', 'p_we_3td') { Delete-Family $root }
foreach ($orphanPool in 'p_wer_3at', 'p_wer_294at', 'p_wer_128at') {   # attached battalions whose pool names no formation struct
    foreach ($p in @($act.kids | Where-Object { (FS $_ 'pool') -eq $orphanPool })) {
        $u = [uint32](FU $p 'uid'); $act.kids.Remove($p) | Out-Null; $plats.Remove($p.name)
        $r = $uidRow[$u]; if ($r) { $pp.rows.Remove($r) | Out-Null }
        Say "  deleted orphan platoon $($p.name) ($orphanPool)"
    }
}
# references to deleted formations in the remaining platoons' pool fields
$blank = 0
foreach ($p in $act.kids) { foreach ($pf in 'pool2', 'pool3', 'pool4') { $v = FS $p $pf; if ($v -and -not $forms.ContainsKey($v)) { SetS $p $pf ''; $blank++ } } }
Say "  $blank stale pool references blanked"
# AI group ids: every formation the script created was cloned with its template's 'ai' fourcc, so all tank brigades
# answered to 'U37', LSSAH to 'DR' etc. The op script pack (tools/ai_orders.py via briefing.py) gives orders by these
# ids each turn, so they must be unique. Division / corps nodes get an id too (the ai_orders HOLD rows list them).
$AI = @{
    p_we_lah = 'LAH'; p_we_lah_1mir = 'L1'; p_we_lah_2mir = 'L2'; p_we_lah_tr = 'LT'; p_we_lah_stug = 'LS'; p_we_lah_1at = 'LA'; p_we_lah_ar = 'LAR'
    p_ra_5gta = 'U5TA'; p_ra_18tc = 'T18'; p_ra_110tbr = 'B110'; p_ra_170tbr = 'B170'; p_ra_181tbr = 'B181'; p_ra_32mrbr = 'M32'; p_ra_36gtr = 'R36'
    p_ra_29tc = 'T29'; p_ra_25tbr = 'B25'; p_ra_31tbr = 'B31'; p_ra_32tbr = 'B32'; p_ra_53mrbr = 'M53'; p_ra_1446sap = 'S146'
    p_ra_2gtc = 'T2G'; p_ra_4gtbr = 'B4G'; p_ra_25gtbr = 'B25G'; p_ra_26gtbr = 'B26G'; p_ra_4gmrbr = 'M4G'; p_ra_47gtr = 'R47'
    p_ra_2tc = 'T2'; p_ra_26tbr = 'B26'; p_ra_99tbr = 'B99'; p_ra_169tbr = 'B169'; p_ra_58mrbr = 'M58'; p_ra_11mrbr = 'M11'; p_ra_15gtr = 'R15'
    p_ra_5gmc = 'M5G'; p_ra_10gmbr = 'B10G'; p_ra_11gmbr = 'B11G'; p_ra_12gmbr = 'B12G'; p_ra_51gtr = 'R51'; p_ra_54gtr = 'R54'; p_ra_55gtr = 'R55'; p_ra_24gtbr = 'B24G'
    p_ra_1529sap = 'S152'; p_ra_1549sap = 'S154'; p_ra_1447sap = 'S147'; p_ra_10iptabr = 'A10'; p_ra_53gtr = 'R53'; p_ra_689iptap = 'A689'
    p_ra_678har = 'H678'; p_ra_27gabr = 'H27'; p_ra_522har = 'H522'; p_ra_1148har = 'H114'; p_ra_76gmr = 'H76'; p_ra_16gmr = 'H16'; p_ra_80gmr = 'H80'
    p_ra_5ga = 'U5GA'; p_ra_33grc = 'C33'; p_ra_9gabd = 'D9'; p_ra_23gabr = 'R23'; p_ra_26gabr = 'R26'; p_ra_28gabr = 'R28'; p_ra_7gabar = 'H7'
    p_ra_95grd = 'D95'; p_ra_284grr = 'R284'; p_ra_287grr = 'R287'; p_ra_290grr = 'R290'; p_ra_233gar = 'H233'
    p_ra_42grd = 'D42'; p_ra_127grr = 'R127'; p_ra_132grr = 'R132'; p_ra_136grr = 'R136'; p_ra_91gar = 'H91'
    p_ra_97grd = 'D97'; p_ra_13grd = 'D13'; p_ra_32gar = 'H32'; p_ra_232gar = 'H232'; p_ra_148gtr = 'R148'; p_ra_93gtr = 'R93'; p_ra_1510iptap = 'A151'; p_ra_301iptap = 'A301'
    p_ra_52grd = 'D52'; p_ra_151grr = 'R151'; p_ra_153grr = 'R153'; p_ra_155grr = 'R155'; p_ra_124gar = 'H124'; p_ra_245otp = 'R245'
    p_ra_48rc = 'C48'; p_ra_183rd = 'D183'; p_ra_227rr = 'R227'; p_ra_285rr = 'R285'; p_ra_295rr_183 = 'R295'; p_ra_623ar = 'H623'; p_ra_27iptabr = 'A27'; p_ra_29iptabr = 'A29'
}
function Fourcc-U32([string]$s) { [uint32]$v = 0; for ($i = 0; $i -lt $s.Length -and $i -lt 4; $i++) { $v = $v -bor ([uint32][byte][char]$s[$i] -shl (8 * $i)) }; $v }
$nAi = 0; $nHold = 0
$holdIds = @{}; if ($aiO) { foreach ($r in $aiO.rows) { $holdIds[[uint32]$r.c[1].v[0]] = 1 } }
foreach ($k in $AI.Keys) {
    if (-not $forms.ContainsKey($k)) { continue }
    $F = $forms[$k]; $id = Fourcc-U32 $AI[$k]; SetU $F 'ai' $id; $nAi++
    if ($aiO -and -not $holdIds.ContainsKey($id)) {   # standing order row: HOLD | id;1;side  (the vanilla table has one per AI group)
        $side = [uint32](FU $F 'side'); $v = New-Object uint32[] 4; $v[0] = $id; $v[1] = 1; $v[2] = $side
        $h = New-Object uint32[] 4; $h[0] = Fourcc-U32 'HOLD'   # the table's cells are int arrays ('aa'), the fourcc sits in the first element
        $aiO.rows.Add(@{ name = $null; c = @(@{ k = 6; v = $h; s = $null }, @{ k = 6; v = $v; s = $null }) }); $holdIds[$id] = 1; $nHold++
    }
}
Say "  AI group ids set on $nAi formations, $nHold HOLD rows added to ai_orders"
# command: a formation whose 'ai' field is USER is under the player's command; any other code hands it to an AI group
# (vanilla: 13 RC / 3 gds RD are AI allies in the Soviet op, SS-TK 6 MIR in the German one). Every formation of the
# player's side becomes USER, so all units can be moved; the enemy keeps its AI group codes (the templates' orders apply).
$cg = $D.root.kids | Where-Object { $_.name -eq 'i_campgen:campgen' } | Select-Object -First 1
if ($cg) {
    $userSide = [uint32](FU $cg 'user_side'); $USER = [uint32]1380275029   # 'USER'
    $nUser = 0
    foreach ($f in $res.kids) { if ([uint32](FU $f 'side') -eq $userSide -and [uint32](FU $f 'ai') -ne $USER) { SetU $f 'ai' $USER; $nUser++ } }
    Say "  $nUser formations of the player's side ($(Azcf-Fourcc $userSide)) put under the player's command (ai = USER)"
}
# SS panzergrenadier battle groups: a tank-support slot (STR) and a second support slot for an assault gun, as the
# Totenkopf battle groups have in the vanilla desc (LSSAH / DR were built without them). The STR slot is filled with a
# line platoon of the division's tank regiment, the SUP slot with a StuG platoon, each platoon used once.
$ROLE = @{}; foreach ($p in $act.kids) { $sl = Kid $p 'slots'; if ($sl) { foreach ($r in $sl.rows) { $ROLE[[uint32]$r.c[1].v[0]] = $r.c[1] } } }
[uint32]$STR = 5395539; [uint32]$SUP = 5264723; [uint32]$SCT = 5522259
if ($ROLE.ContainsKey($STR) -and $ROLE.ContainsKey($SUP)) {
    $nSlots = 0
    foreach ($div in 'lah', 'dr') {
        $tanks = New-Object Collections.Generic.List[string]; $stugs = New-Object Collections.Generic.List[string]
        foreach ($p in $act.kids) {
            $pool = FS $p 'pool'; $pk = Kid $p 'pool'
            if (-not $pk -or (FU $p 'bg') -ne 0) { continue }
            if ($pool -eq "p_we_${div}_tr" -and $p.name -match '_\dc_\dp$') { $tanks.Add($p.name) }
            if ($pool -eq "p_we_${div}_stug" -and $p.name -match '_\dp$') { $stugs.Add($p.name) }
        }
        $used = @{}; foreach ($p in $act.kids) { $sl = Kid $p 'slots'; if ($sl) { foreach ($r in $sl.rows) { if ($r.c[0].s) { $used[$r.c[0].s] = 1 } } } }
        $ti = 0; $si = 0
        foreach ($p in @($act.kids | Where-Object { (FS $_ 'pool') -match "^p_we_${div}_\dmir$" -and (FU $_ 'bg') -ne 0 })) {
            $sl = Kid $p 'slots'; if (-not $sl) { continue }
            if (@($sl.rows | Where-Object { [uint32]$_.c[1].v[0] -eq $STR }).Count -eq 0) {
                $tn = ''; while ($ti -lt $tanks.Count) { if (-not $used.ContainsKey($tanks[$ti])) { $tn = $tanks[$ti]; $used[$tn] = 1; $ti++; break }; $ti++ }
                $ix = 1; for ($i = 0; $i -lt $sl.rows.Count; $i++) { if ([uint32]$sl.rows[$i].c[1].v[0] -eq $SCT) { $ix = $i + 1 } }
                $sl.rows.Insert($ix, @{ name = $null; c = @(@{ k = 2; v = (New-Object uint32[] 4); s = $tn }, (Clone-Cell $ROLE[$STR])) }); $nSlots++
            }
            if (@($sl.rows | Where-Object { [uint32]$_.c[1].v[0] -eq $SUP }).Count -lt 3) {
                $sn = ''; while ($si -lt $stugs.Count) { if (-not $used.ContainsKey($stugs[$si])) { $sn = $stugs[$si]; $used[$sn] = 1; $si++; break }; $si++ }
                $sl.rows.Add(@{ name = $null; c = @(@{ k = 2; v = (New-Object uint32[] 4); s = $sn }, (Clone-Cell $ROLE[$SUP])) }); $nSlots++
            }
        }
    }
    Say "  $nSlots tank / assault-gun support slots added to the SS panzergrenadier battle groups"
}
# 25 Oct (user: "can't add a tank or SPG to the LSSAH 2 MIR battle groups"): the deployment screen offers a battle group the
# platoons of its pool, pool2, pool3 and pool4 formations (vanilla Totenkopf: own regiment, division, artillery regiment,
# StuG battalion / panzer regiment). The LSSAH and Das Reich clones came with pool3 / pool4 blank, so no armour could be
# attached. Panzergrenadier battle groups: pool3 = the division's assault guns, pool4 = its panzer regiment; tank and
# StuG battle groups: pool3 = a panzergrenadier regiment, pool4 = the division. Soviet rifle regiments get the tank
# brigade that fought beside them (285 RR - 169 TBde, 295 RR - 26 TBde, 227 RR - 4 gds TBde) and 2 TC's brigades the 285 RR.
$POOLS = @{
    '^p_we_lah_\dmir$' = @('p_we_lah_stug', 'p_we_lah_tr'); '^p_we_dr_\dmir$' = @('p_we_dr_stug', 'p_we_dr_tr'); '^p_we_tk_\dmir$' = @('p_we_tk_stug', 'p_we_tk_tr')
    '^p_we_(lah|dr|tk)_tr$' = @('{div}_2mir', '{div}'); '^p_we_(lah|dr|tk)_stug$' = @('{div}_2mir', '{div}')
    '^p_ra_285rr(_183)?$' = @('p_ra_623ar', 'p_ra_169tbr'); '^p_ra_295rr_183$' = @('p_ra_623ar', 'p_ra_26tbr'); '^p_ra_227rr$' = @('p_ra_623ar', 'p_ra_4gtbr')
    '^p_ra_(26|99|169)tbr$' = @('p_ra_58mrbr', 'p_ra_285rr')
}
$nPools = 0
foreach ($p in $act.kids) {
    if ((FU $p 'bg') -eq 0) { continue }
    $own = FS $p 'pool'
    foreach ($rx in $POOLS.Keys) {
        if ($own -notmatch $rx) { continue }
        $div = $own -replace '_(tr|stug|\dmir)$', ''
        $want = @($POOLS[$rx] | ForEach-Object { $_.Replace('{div}', $div) })
        if ($want[0] -eq 'p_we_tk_2mir') { $want[0] = 'p_we_tk_6mir' }   # Totenkopf's regiments are 5 and 6
        $i = 3
        foreach ($w in $want) { if ($forms.ContainsKey($w) -and $w -ne $own) { SetS $p "pool$i" $w; $nPools++ }; $i++ }
        break
    }
}
Say "  $nPools attachment pools set on the battle groups (armour for the panzergrenadiers, tanks for the rifle regiments)"
# 25 Oct (user): 1/285 and 2/285 RR each split into two battle groups side by side - the second one built from the
# battalion's reserve companies (2 and 5/6 coy, the MG and mortar platoons, the AT rifles / 45 mm guns)
function Split-BattleGroup([string]$bg, [string]$new, [string[]]$members, [string]$nameE, [string]$shortE, [string]$nameR, [string]$shortR) {
    $src = $plats[$bg]; if (-not $src) { Say "  split: battle group $bg not found"; return }
    foreach ($m in $members) { if ($m -and -not $plats.ContainsKey($m)) { Say "  split: platoon $m not found"; return } }
    $Q = Clone-Node $src; $Q.name = $new
    $code = [uint32](FU $src 'code'); $form = FS $src 'pool'
    $taken = @{}; foreach ($x in $act.kids) { if ((FS $x 'pool') -eq $form) { $taken[[int](FU $x 'code')] = 1 } }
    while ($taken.ContainsKey([int]$code)) { $code++ }
    $uid = ([uint32](FU $src 'uid') -band 0xFFFFF000) -bor ($code -band 0xFFF); while ($uids.ContainsKey($uid)) { $uid += 0x1000 }; $uids[$uid] = 1
    SetU $Q 'code' $code; SetU $Q 'uid' $uid; SetS $Q 'name' ('op_' + $new)
    $script:newText.eng['op_' + $new] = [string[]]@($nameE, $shortE); $script:newText.rus['op_' + $new] = [string[]]@($nameR, $shortR)
    $sl = Kid $Q 'slots'
    for ($i = 0; $i -lt $sl.rows.Count; $i++) { $m = if ($i -lt $members.Count) { $members[$i] } else { '' }; $sl.rows[$i].c[0] = @{ k = 2; v = (New-Object uint32[] 4); s = $m } }
    $ix = $act.kids.IndexOf($src); $act.kids.Insert($ix + 1, $Q); $plats[$new] = $Q
    $pp.rows.Add(@{ name = $null; c = @((Cell-Decode "a:$uid;-1;-1;-1"), (Cell-Decode 'a:1')) })
    Say ("  split {0} -> {1} (code {2}, uid 0x{3:x}): {4}" -f $bg, $new, $code, $uid, ($members -join ' '))
}
Split-BattleGroup 'ra_285_1' 'ra_285_1b' @('ra_285_2c_com', 'ra_285_1b_ac82mt', 'ra_285_2c_1p', 'ra_285_2c_2p', 'ra_285_1mg_1p', 'ra_285_1mt_1p', 'ra_285_atrc_1p') '183 RD, 1/285 RR, 2 coy' '1/285 (2c)' '183 СД, 1/285 СП, 2 рота' '1/285 (2р)'
Split-BattleGroup 'ra_285_2' 'ra_285_2b' @('ra_285_5c_com', 'ra_285_2b_ac82mt', 'ra_285_5c_1p', 'ra_285_6c_1p', 'ra_285_2mg_1p', 'ra_285_2mt_1p', 'ra_285_2b_atg') '183 RD, 2/285 RR, 5 coy' '2/285 (5c)' '183 СД, 2/285 СП, 5 рота' '2/285 (5р)'
# slot tables: references to platoons of other formations (artillery observers, corps assets) -> their clones, or blank
$fixed = 0; $blanked = 0
foreach ($p in $act.kids) { $sl = Kid $p 'slots'; if (-not $sl) { continue }
    foreach ($r in $sl.rows) { $s = $r.c[0].s; if (-not $s -or $plats.ContainsKey($s)) { continue }
        if ($platMap.ContainsKey($s) -and $plats.ContainsKey($platMap[$s])) { $r.c[0] = @{ k = 2; v = (New-Object uint32[] 4); s = $platMap[$s] }; $fixed++ } else { $r.c[0] = @{ k = 2; v = (New-Object uint32[] 4); s = '' }; $blanked++ } } }
Say "  slot references: $fixed remapped to clones, $blanked blanked"
# a platoon may stand in ONE battle group only (the tactical placer crashes on a platoon shared by two groups; the
# 30 July file has none): clones of a template battle group that kept the template's corps / divisional support platoon
# (744 AT bn sections, artillery observers of the template division) get the matching platoon of their own formation,
# parent or sister formation - the one with the same name tail first, else any free one with the same role tail - or
# an empty slot
$formOf = @{}; foreach ($p in $act.kids) { $formOf[$p.name] = FS $p 'pool' }
$parentOf = @{}; foreach ($f in $res.kids) { $parentOf[$f.name] = FS $f 'parent' }
function Tail-Of([string]$n, [int]$k) { $t = $n.Split('_'); if ($t.Count -le $k) { return $n }; ($t[($t.Count - $k)..($t.Count - 1)] -join '_') }
$owner = @{}; $dupFixed = 0; $dupBlank = 0; $dupNote = New-Object Collections.Generic.List[string]
$bgs = @($act.kids | Where-Object { Kid $_ 'slots' })
foreach ($pass in 1, 2) {
    foreach ($p in $bgs) {
        $sl = Kid $p 'slots'; $bgForm = FS $p 'pool'; $par = $parentOf[$bgForm]
        $scopes = @($bgForm, $par) + @($res.kids | Where-Object { $par -and (FS $_ 'parent') -eq $par } | ForEach-Object { $_.name })
        foreach ($r in $sl.rows) {
            $s = $r.c[0].s; if (-not $s) { continue }
            $legit = $scopes -contains $formOf[$s]
            if (($pass -eq 1) -ne $legit) { continue }
            if (-not $owner.ContainsKey($s)) { $owner[$s] = $p.name; continue }
            $tail3 = Tail-Of $s 3; $rx = '_' + ([regex]::Escape($tail3) -replace '\d', '\d') + '$'; $exact = '_' + [regex]::Escape($tail3) + '$'
            $pick = ''
            foreach ($scope in @($bgForm, $par) + @($scopes | Select-Object -Skip 2)) {
                if (-not $scope) { continue }
                $c = @($act.kids | Where-Object { (FS $_ 'pool') -eq $scope -and (FU $_ 'bg') -eq 0 -and $_.name -match $rx -and -not $owner.ContainsKey($_.name) } | ForEach-Object { $_.name })
                if ($c.Count) { $pick = @($c | Where-Object { $_ -match $exact })[0]; if (-not $pick) { $pick = $c[0] }; break }
            }
            if ($pick) { $r.c[0] = @{ k = 2; v = (New-Object uint32[] 4); s = $pick }; $owner[$pick] = $p.name; $dupFixed++; $dupNote.Add("$($p.name): $s -> $pick") }
            else { $r.c[0] = @{ k = 2; v = (New-Object uint32[] 4); s = '' }; $dupBlank++; $dupNote.Add("$($p.name): $s -> (empty)") }
        }
    }
}
Say "  shared platoons: $dupFixed slots re-pointed, $dupBlank emptied"
foreach ($n in $dupNote) { Say "    $n" }

# ---------------------------------------------------------------- write
$gen = "$descPath"
Azcf-Save $D $gen | Out-Null; Say ("  descriptor written {0}" -f (Get-Date))
$delta = Join-Path $OpDir 'oob_12jul.delta'
Cmd-Diff $orig $gen $delta | Out-Null; Say ("  delta written {0}" -f (Get-Date))
foreach ($l in 'eng', 'rus') {
    if (-not $text.ContainsKey($l)) { continue }
    $keys = New-Object Collections.Generic.List[object]
    foreach ($k in $text[$l].Keys) { $keys.Add([pscustomobject]@{ key = $k; items = [string[]]$text[$l][$k] }) }
    foreach ($k in $newText[$l].Keys) { if (-not $text[$l].Contains($k)) { $keys.Add([pscustomobject]@{ key = $k; items = [string[]]$newText[$l][$k] }) } }
    Write-Aztx (Join-Path $OpDir "text.text.loc_$l.bin") "loc_$l" $keys.ToArray()
}
$csv = New-Object Collections.Generic.List[string]; $csv.Add('node,uid,side,bg,code')
foreach ($p in $act.kids) { $csv.Add(('{0},{1},{2},{3},{4}' -f $p.name, (FU $p 'uid'), (Azcf-Fourcc (FU $p 'side')), (FU $p 'bg'), (FU $p 'code'))) }
[IO.File]::WriteAllLines((Join-Path $OpDir 'uids.csv'), $csv.ToArray())
Say ("done: {0} formations created, {1} formations and {2} platoons in the file, {3} new text keys; delta {4}" -f $created.Count, $res.kids.Count, $act.kids.Count, $newText.eng.Count, $delta)
[IO.File]::WriteAllLines((Join-Path $OpDir 'oob_12jul_log.txt'), $log.ToArray())
