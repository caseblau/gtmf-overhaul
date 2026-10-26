<#
.SYNOPSIS
  M12 terrain probe 3: copies the tables the terrain layers index into (season_ua_summer, materials, builds, fences,
  flora_sum, objects, structs, posts, ai_plans) from the unpacked vanilla tables into docs\m12_terrain\samples\tabs\
  and decodes them with gt3.ps1 csv; also copies the MgG3 ambient-occlusion map. Read-only on the game.
#>
param([string]$GameRoot = $env:GTMF_ROOT)
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
$orig = Join-Path $GameRoot 'users\modwork\_orig\3598'
$out = Join-Path $repo 'docs\m12_terrain\samples\tabs'
New-Item -ItemType Directory -Force $out | Out-Null
Start-Transcript -Path (Join-Path $repo 'docs\m12_terrain\probe3_report.txt') -Force | Out-Null
trap { "!! ERROR: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"; continue }
"# M12 probe 3  $(Get-Date -Format s)"
foreach ($name in @('season_ua_summer', 'materials', 'builds', 'fences', 'flora_sum', 'objects', 'structs', 'posts', 'ai_plans', 'mil_fences', 'builds_wood')) {
    $f = Get-ChildItem $orig -Recurse -Filter "$name.config.loc_def.bin" | Select-Object -First 1
    if (-not $f) { "  $name : not found under $orig"; continue }
    Copy-Item $f.FullName (Join-Path $out $f.Name) -Force
    $dir = Join-Path $out $name
    & $gt3 csv $f.FullName '*' $dir 2>&1 | Out-Null
    $n = @(Get-ChildItem $dir -Filter *.csv).Count
    "  $name : $($f.Length) bytes, $n nodes exported -> samples\tabs\$name\"
    & $gt3 nodes $f.FullName 2>&1 | Select-Object -First 25 | ForEach-Object { "      $_" }
}
$ao = Join-Path $GameRoot 'data\oprum\shared\polygons\6m_mius\mgg3_mius_ao.aomap'
if (Test-Path $ao) { Copy-Item $ao (Join-Path $repo 'docs\m12_terrain\samples\cells\MgG3\mgg3_mius_ao.aomap') -Force; "  copied aomap" }
"done"
Stop-Transcript | Out-Null
