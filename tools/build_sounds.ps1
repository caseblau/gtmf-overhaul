<#
.SYNOPSIS
  Builds the sound module as a SEPARATE add-on shaped exactly like the in-game builder's output
  (RukiSoundMod, Kuli Kraut Fix): a GUID-named folder holding only core\desc.addpack and
  core\shared\packed_data\ch_sounds.flatdata. The main add-on (build.ps1) skips the modules
  listed in manifest.txt separate_modules.
.EXAMPLE
  .\build_sounds.ps1 -Install
#>
param(
    [string]$GameRoot = $env:GTMF_ROOT,
    [switch]$Install
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
$m = @{}
foreach ($line in Get-Content (Join-Path $repo 'manifest.txt')) { if ($line -match '^\s*([^#=]+?)\s*=\s*(.*?)\s*$') { $m[$Matches[1]] = $Matches[2] } }
$ver = $m['version']; $guid = $m['sounds_addon_path']; $name = "$($m['name']) Sounds"
if (-not $guid) { throw 'manifest.txt needs sounds_addon_path=<GUID folder name>' }
$verNum = [uint32](($ver.Split('.') | ForEach-Object { [int]$_ }) | ForEach-Object -Begin { $v = 0 } -Process { $v = $v * 100 + $_ } -End { $v })

$srcDir = Join-Path $repo 'src\m6_sound\ch_sounds'
if (-not (Test-Path (Join-Path $srcDir '!flatlist'))) { throw "missing $srcDir\!flatlist" }
$core = Join-Path $repo 'build\sounds_core'
if (Test-Path $core) { Remove-Item $core -Recurse -Force }
$packed = Join-Path $core 'shared\packed_data'
New-Item -ItemType Directory -Force $packed | Out-Null
& $gt3 pack (Join-Path $packed 'ch_sounds.flatdata') $srcDir
& $gt3 desc (Join-Path $PSScriptRoot 'templates\desc_template.addpack') (Join-Path $core 'desc.addpack') `
    "path=$guid" "desc=$name $ver" "authors=$($m['authors'])" "version=$verNum"
& $gt3 azcf (Join-Path $core 'desc.addpack') | Select-Object -Skip 1
$out = Join-Path $repo ('build\mfo_sounds_{0}.gt3ext' -f $ver)
& $gt3 gt3ext $out $core
"built $out ($([Math]::Round((Get-Item $out).Length / 1KB)) KB)"
if ($Install) {
    if (-not $GameRoot -or -not (Test-Path (Join-Path $GameRoot 'starter_x64.exe'))) { throw 'GameRoot (or GTMF_ROOT) must point at the folder containing starter_x64.exe' }
    $dst = Join-Path $GameRoot 'new_updates'
    Get-ChildItem $dst -Filter 'mfo_sounds_*.gt3ext' -ErrorAction SilentlyContinue | Remove-Item -Force
    Copy-Item $out $dst
    "installed into $dst - start the game once"
}
