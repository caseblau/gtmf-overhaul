<# Removes the stand-alone Prokhorovka add-on (data\common\mfo_prokhorovka, installed from the release package
   mfo_prokhorovka_0.1.0.gt3ext). On the development PC it sits ABOVE mfo_overhaul in the add-on list, so the game
   loads its older copies of the 35 Prokh cells and the two operations instead of the ones tools\build_prokh*.cmd
   installs into mfo_overhaul - none of the later fixes show up in game while it is there.
   - backs up data\common\shared\config\paths.cfgpack to build\prokhorovka\paths_before_remove_<time>.cfgpack
   - drops the 'mfo_prokhorovka' row from the add-on registry (gt3.ps1 apply)
   - moves the folder to build\prokhorovka\removed_addon_<time> (delete it yourself later) #>
param([string]$GameRoot = $env:GTMF_ROOT)
$ErrorActionPreference = 'Stop'
if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$work = Join-Path $here '..\build\prokhorovka'; New-Item -ItemType Directory -Force $work | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$addon = Join-Path $GameRoot 'data\common\mfo_prokhorovka'
$paths = Join-Path $GameRoot 'data\common\shared\config\paths.cfgpack'
if (Get-Process -Name 'starter_x64', 'gtmf*' -ErrorAction SilentlyContinue) { throw 'close the game first' }
foreach ($f in Get-ChildItem (Join-Path $GameRoot 'new_updates') -Filter 'mfo_prokhorovka*' -ErrorAction SilentlyContinue) {
    Move-Item $f.FullName (Join-Path $work ($f.Name + '.removed_' + $stamp)); "moved $($f.Name) out of new_updates (it would reinstall itself)"
}
$txt = [Text.Encoding]::GetEncoding(1251).GetString([IO.File]::ReadAllBytes($paths))
if ($txt.Contains('mfo_prokhorovka')) {
    Copy-Item $paths (Join-Path $work "paths_before_remove_$stamp.cfgpack")
    $delta = Join-Path $work "remove_prokh_$stamp.delta"; $tmp = Join-Path $work "paths_new_$stamp.cfgpack"
    $done = $false
    foreach ($p in 'i_objman:objman', 'paths/i_objman:objman') {
        Set-Content -Path $delta -Value "row-|$p|mfo_prokhorovka" -Encoding ASCII
        try { & (Join-Path $here 'gt3.ps1') apply $paths $delta $tmp | Out-Host; if (Test-Path $tmp) { $done = $true; break } } catch { "  ($($p)): $($_.Exception.Message)" }
    }
    if (-not $done) { throw 'could not remove the registry row - nothing was changed' }
    Copy-Item $tmp $paths -Force; Remove-Item $tmp, $delta
    "registry: mfo_prokhorovka removed (backup build\prokhorovka\paths_before_remove_$stamp.cfgpack)"
} else { 'registry: mfo_prokhorovka not listed' }
if (Test-Path $addon) {
    $dst = Join-Path $work "removed_addon_$stamp"
    Move-Item $addon $dst
    "folder moved to build\prokhorovka\removed_addon_$stamp - delete it when you like"
} else { 'folder: not installed' }
'done - next: the operations are rebuilt into mfo_overhaul'
