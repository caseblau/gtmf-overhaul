<#
.SYNOPSIS
  Lists every battle-group slot reference of an operation descriptor and flags platoons that sit in more than one
  battle group (the engine places such a platoon with an invalid position and crashes when the battle loads).
.EXAMPLE
  tools\slot_report.ps1 build\prokhorovka\op_RUS\desc.config.loc_def.bin  -> build\prokhorovka\op_RUS\slot_report.txt
#>
param([Parameter(Mandatory = $true)][string]$Desc, [string]$Out = '')
. (Join-Path $PSScriptRoot 'gt3.ps1') lib
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
function Fld([object]$node, [string]$name) { foreach ($r in $node.rows) { if ($r.name -eq $name) { return $r } }; $null }
function FS([object]$node, [string]$name) { $r = Fld $node $name; if ($r -and $r.c[0].k -eq 2) { $r.c[0].s } else { '' } }
function FU([object]$node, [string]$name) { $r = Fld $node $name; if ($r) { [uint32]$r.c[0].v[0] } else { 0 } }
function Kid([object]$n, [string]$name) { foreach ($k in $n.kids) { if ($k.name -eq $name) { return $k } }; $null }
if (-not $Out) { $Out = Join-Path (Split-Path $Desc) 'slot_report.txt' }
$D = Azcf-Load $Desc
$act = Kid $D.root 'act_platoons'
$plats = @{}; foreach ($p in $act.kids) { $plats[$p.name] = $p }
$refs = @{}; $lines = New-Object Collections.Generic.List[string]
$nbg = 0
foreach ($p in $act.kids) {
    $sl = Kid $p 'slots'; if (-not $sl) { continue }
    $nbg++
    foreach ($r in $sl.rows) {
        $s = $r.c[0].s; if (-not $s) { continue }
        $role = Azcf-Fourcc ([uint32]$r.c[1].v[0])
        $lines.Add(('{0}|{1}|{2}|{3}' -f $p.name, (FS $p 'pool'), $s, $role))
        if (-not $refs.ContainsKey($s)) { $refs[$s] = New-Object Collections.Generic.List[string] }
        $refs[$s].Add($p.name + ':' + $role)
    }
}
$dups = @(); $missing = @()
foreach ($k in $refs.Keys) { if ($refs[$k].Count -gt 1) { $dups += ('{0} <- {1}' -f $k, ($refs[$k] -join ', ')) }; if (-not $plats.ContainsKey($k)) { $missing += $k } }
$head = @("# slot report for $Desc", "# $nbg battle groups, $($lines.Count) slot references, $($refs.Count) distinct platoons",
          "# SHARED platoons (in more than one battle group): $($dups.Count)") + ($dups | Sort-Object) +
        @("# references to platoons that do not exist: $($missing.Count)") + ($missing | Sort-Object) + @('# bg|pool|platoon|role') + $lines
[IO.File]::WriteAllLines($Out, [string[]]$head)
"$nbg battle groups, $($lines.Count) slot references; $($dups.Count) shared platoons, $($missing.Count) missing -> $Out"
