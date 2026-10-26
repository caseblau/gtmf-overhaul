<#
.SYNOPSIS
  M12 heightmap write test. Replaces the hei_map entry of the Mius terrain cell MgG3 (centre of the Stepanovka map)
  with docs\m12_terrain\test\hei_map.cell.loc_def.bin (the vanilla heights plus a 40 m hill, 600 m wide, in the cell
  centre) and installs the rebuilt MgG3_Mius.polypack2 into the game. The original is backed up to
  <game>\users\modwork\_orig\polygons\6m_mius\ first; run with -Restore to put it back.
  Only the heights change: normals, ambient occlusion and passability maps stay vanilla, so the hill will look flat-lit.
#>
param([string]$GameRoot = $env:GTMF_ROOT, [switch]$Restore, [string]$Cell = 'MgG3')
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
New-Item -ItemType Directory -Force (Join-Path $repo 'build\m12_test') | Out-Null
Start-Transcript -Path (Join-Path $repo 'build\m12_test\transcript.txt') -Force | Out-Null
trap { "!! ERROR: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"; continue }
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
$poly = Join-Path $GameRoot 'data\oprum\shared\polygons\6m_mius'
$file = "${Cell}_Mius.polypack2"
$live = Join-Path $poly $file
$bak = Join-Path $GameRoot "users\modwork\_orig\polygons\6m_mius\$file"
if ($Restore) {
    if (-not (Test-Path $bak)) { throw "no backup at $bak" }
    Copy-Item $bak $live -Force; "restored $live from backup"; Stop-Transcript | Out-Null; return
}
if (-not (Test-Path $bak)) { New-Item -ItemType Directory -Force (Split-Path $bak) | Out-Null; Copy-Item $live $bak; "backed up original to $bak" }
else { "backup already present: $bak (not overwritten)" }
$work = Join-Path $repo "build\m12_test\$Cell"
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
& $gt3 unpack $bak $work
# round-trip proof first: repack the untouched entries and compare with the original
$rt = Join-Path $repo "build\m12_test\${Cell}_roundtrip.polypack2"
& $gt3 pack $rt $work | Out-Null
$h1 = (Get-FileHash $bak -Algorithm SHA256).Hash; $h2 = (Get-FileHash $rt -Algorithm SHA256).Hash
if ($h1 -eq $h2) { "round trip: repacked cell is byte-identical to the original" } else { "round trip: repacked cell DIFFERS from the original ($((Get-Item $bak).Length) vs $((Get-Item $rt).Length) bytes) - continuing anyway, report this" }
$src = Join-Path $repo 'docs\m12_terrain\test\hei_map.cell.loc_def.bin'
if (-not (Test-Path $src)) { throw "missing $src" }
Copy-Item $src (Join-Path $work 'hei_map.cell.loc_def.bin') -Force
$out = Join-Path $repo "build\m12_test\$file"
& $gt3 pack $out $work
Copy-Item $out $live -Force
"installed $live ($((Get-Item $live).Length) bytes). Start the game, open the 17 July Stepanovka operation (or a quick battle on the map centre) and look for a round 40 m hill in the middle of the map. Run tools\terrain_hill_test.cmd restore to undo."
Stop-Transcript | Out-Null
