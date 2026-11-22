<#
.SYNOPSIS
  22 Nov 2026 (user: "any battle after the first or second turn has only one unit involved for both sides"): gives every
  platoon of a Prokhorovka operation the AI group id of its own formation.

  tools\oob_12jul.ps1 set the unique AI ids of its $AI table (L1, L2, LT ... B110, B170 ...) on the FORMATION records only.
  The cloned platoons kept their template's 'ai' fourcc, and the engine builds its AI groups from the platoons (op_ais /
  plats<ID>): all of LSSAH sat in the Das Reich groups (DL 187, DF 175, DR 161 platoons against 94 / 88 / 83 in the vanilla
  07_30 operation), the cloned Soviet brigades in their template brigade's group. When such a doubled group attacks, every
  platoon of it is busy (group state >= 3) and adv_opgame leaves busy AI platoons out of every other battle - from turn 2
  on most battles got the attacker and the defender only. The orders of tools\ai_orders.py for L1 / L2 / LT ... went to
  groups without platoons.

.EXAMPLE
  tools\prokh_ai_fix.ps1 -Desc build\prokhorovka\op_RUS\desc.config.loc_def.bin      # in place
#>
param([Parameter(Mandatory = $true)][string]$Desc)
. (Join-Path $PSScriptRoot 'gt3.ps1') lib
$ErrorActionPreference = 'Stop'
function Fcc([uint32]$v) { -join (0..3 | ForEach-Object { $c = ($v -shr (8 * $_)) -band 255; if ($c -ge 32) { [char]$c } }) }
$USER = [uint32]1380275029   # 'USER'
$D = Azcf-Load $Desc
$root = $D.root; if (-not $root) { $root = $D }
$res = $root.kids | Where-Object { $_.name -eq 'reserves' } | Select-Object -First 1
$act = $root.kids | Where-Object { $_.name -eq 'act_platoons' } | Select-Object -First 1
# formation -> ai id, for every formation (reserves/p_*) whose id differs from what its platoons carry
$fai = @{}
$stack = New-Object Collections.Stack; foreach ($k in $res.kids) { $stack.Push($k) }
while ($stack.Count) {
    $n = $stack.Pop(); foreach ($k in $n.kids) { $stack.Push($k) }
    if ($n.type -ne 1 -or $n.name -notlike 'p_*') { continue }
    foreach ($r in $n.rows) { if ($r.name -eq 'ai' -and $r.c[0].v) { $fai[$n.name] = [uint32]$r.c[0].v[0] } }
}
$changed = 0; $byId = @{}
foreach ($p in $act.kids) {
    $ai = $null; $pool = $null
    foreach ($r in $p.rows) { if ($r.name -eq 'ai') { $ai = $r } elseif ($r.name -eq 'pool') { $pool = $r.c[0].s } }
    if (-not $ai -or -not $pool -or -not $fai.ContainsKey($pool)) { continue }
    $want = $fai[$pool]; $have = [uint32]$ai.c[0].v[0]
    if ($want -eq 0 -or $want -eq $have -or $have -eq $USER -or $want -eq $USER) { continue }
    $v = New-Object uint32[] 4; $v[0] = $want; $ai.c[0] = @{ k = 4; v = $v; s = $null }
    $changed++; $id = Fcc $want; $byId[$id] = 1 + [int]$byId[$id]
}
if ($changed) { Azcf-Save $D $Desc | Out-Null }
"{0}: {1} platoons moved to their formation's AI group ({2})" -f $Desc, $changed, (($byId.GetEnumerator() | Sort-Object Name | ForEach-Object { '{0} {1}' -f $_.Key, $_.Value }) -join ', ')
