<#
.SYNOPSIS
  Packages the Prokhorovka polygon and the two 10 July 1943 operations as a STANDALONE add-on that other players install
  like any Graviteam add-on: drop the .gt3ext into <game>\new_updates\ and start the game once.

  Input:  the files tools\build_prokh.ps1 installed into <GameRoot>\data\common\mfo_overhaul\shared\
            polygons\Prokh\*  (Prokh.cfgpack, Prokh_cells.cfgpack, local\Prokh_text.*, 35 x <cell>_Prokh.polypack2 + *_ao.aomap)
            camps\1943_07_Kursk\07_10_Prokhorovka_GER.campack2 and _RUS.campack2
  Output: build\release\mfo_prokhorovka_<version>.gt3ext  (+ README_Prokhorovka.txt beside it, and inside the package)

  The package carries NOTHING from the other overhaul modules (no third-party content: docs\third_party.md rule 2), only
  our own polygon, operations and texts. It needs the vanilla game 6.00 build 3598 and, for the Churchill regiments,
  the Stalingrad-Donets DLC (the rkka_church3 squads use its models).
.EXAMPLE
  .\release_prokh.ps1 -Version 0.1.0
#>
param([string]$GameRoot = $env:GTMF_ROOT, [string]$Version = '0.1.0', [string]$Authors = 'MF Overhaul team', [switch]$Install)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
$src = Join-Path $GameRoot 'data\common\mfo_overhaul\shared'
$poly = Join-Path $src 'polygons\Prokh'; $camps = Join-Path $src 'camps\1943_07_Kursk'
if (-not (Test-Path (Join-Path $poly 'Prokh.cfgpack'))) { throw "no installed polygon at $poly - run tools\build_prokh_cells.cmd first" }
$packs = @(Get-ChildItem $poly -Filter '*_Prokh.polypack2')
if ($packs.Count -ne 35) { throw "expected 35 cell packs in $poly, found $($packs.Count) - run tools\gen_prokh_fresh.cmd + build_prokh_cells.cmd" }
$ops = @(Get-ChildItem $camps -Filter '07_10_Prokhorovka_*.campack2')
if ($ops.Count -ne 2) { throw "expected 07_10_Prokhorovka_GER and _RUS campack2 in $camps, found $($ops.Count) - run tools\build_prokh_op.cmd" }

$rel = Join-Path $repo 'build\release'; $core = Join-Path $rel 'core'
if (Test-Path $core) { Remove-Item $core -Recurse -Force }
New-Item -ItemType Directory -Force (Join-Path $core 'shared\polygons\Prokh\local'), (Join-Path $core 'shared\camps\1943_07_Kursk') | Out-Null
Copy-Item (Join-Path $poly '*.cfgpack') (Join-Path $core 'shared\polygons\Prokh') -Force
Copy-Item (Join-Path $poly '*.polypack2') (Join-Path $core 'shared\polygons\Prokh') -Force
Copy-Item (Join-Path $poly '*.aomap') (Join-Path $core 'shared\polygons\Prokh') -Force
Copy-Item (Join-Path $poly 'local\*') (Join-Path $core 'shared\polygons\Prokh\local') -Force
foreach ($o in $ops) { Copy-Item $o.FullName (Join-Path $core 'shared\camps\1943_07_Kursk') -Force }

# the add-on descriptor: its own path under data\common, so it installs beside (not inside) the overhaul and can be
# removed on its own; the version number is what the updater compares
$verNum = [uint32](($Version.Split('.') | ForEach-Object { [int]$_ }) | ForEach-Object -Begin { $v = 0 } -Process { $v = $v * 100 + $_ } -End { $v })
& $gt3 desc (Join-Path $PSScriptRoot 'templates\desc_template.addpack') (Join-Path $core 'desc.addpack') `
    "path=mfo_prokhorovka" "desc=Prokhorovka 10-13 July 1943 $Version" "authors=$Authors" "version=$verNum" | Out-Null

$readme = Join-Path $repo 'docs\m11_prokhorovka\README_Prokhorovka.txt'
if (Test-Path $readme) { Copy-Item $readme (Join-Path $core 'README_Prokhorovka.txt') -Force; Copy-Item $readme $rel -Force }

$out = Join-Path $rel ('mfo_prokhorovka_{0}.gt3ext' -f $Version)
& $gt3 gt3ext $out $core | Where-Object { $_ -notlike '  +*' }
$mb = [Math]::Round((Get-Item $out).Length / 1MB)
"package: $out ($mb MB; $($packs.Count) cells, $($ops.Count) operations)"
"sha256:  $((Get-FileHash $out -Algorithm SHA256).Hash)"
if ($Install) {
    $dst = Join-Path $GameRoot 'new_updates'; New-Item -ItemType Directory -Force $dst | Out-Null
    Get-ChildItem $dst -Filter 'mfo_prokhorovka*.gt3ext' -ErrorAction SilentlyContinue | Remove-Item -Force
    Copy-Item $out $dst; "copied into $dst - start the game once to install"
}
