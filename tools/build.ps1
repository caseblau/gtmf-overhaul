<#
.SYNOPSIS
  MF Overhaul build: src\<module>\<archive>\!flatlist  ->  build\core\shared\packed_data\<archive>.flatdata
                     tools\templates\desc_template.addpack + manifest.txt -> build\core\desc.addpack
                     build\core\** -> build\<name>_<version>.gt3ext      (-Install copies it into <GameRoot>\new_updates\)
  No starter.exe involved: build 3598 has no unflat/mkflat programs. tools\gt3.ps1 writes the archives.

.DESCRIPTION
  Merge stage (DESIGN.md 1.3, 7.3): the engine takes one entry per name from one archive, so an entry several modules
  change is assembled here, not layered by the engine. tools\check_conflicts.ps1 turns src\ into a plan: for every entry
  the contributions in table_merge_order (manifest: vanilla > m8_vfx > m9_ap_port > m1_core > m2_oob > m3_quickbattle).
  A contribution is a whole entry (<name>.<kind>.<loc>.bin, allowed only from the first contributing module) or a
  row-level delta (<name>.<kind>.<loc>[.<tag>].delta, tools\gt3.ps1 diff format). An entry whose first contribution is
  a delta starts from the pristine vanilla table (-VanillaRoot, default <GameRoot>\users\modwork\_orig\3598). The deltas
  are applied in order with tools\gt3.ps1 apply; every intermediate table is kept in build\merge\_steps\ for inspection
  and the final entries are staged in build\merge\<archive>\ and packed from there.

.EXAMPLE
  .\build.ps1                      # build only (needs GTMF_ROOT or -VanillaRoot as soon as any module ships a delta)
  .\build.ps1 -Install             # build and drop into new_updates (GTMF_ROOT or -GameRoot)
  .\build.ps1 -BuildDir C:\tmp\b   # build somewhere else (verification builds; build\ stays untouched)
#>
param(
    [string]$GameRoot = $env:GTMF_ROOT,
    [string]$VanillaRoot = $env:GTMF_VANILLA,   # pristine unpacked 3598 tables (tabs\, tabs_oprum\, text_loc\ subfolders)
    [string]$BuildDir = '',
    [switch]$Install
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
if (-not $BuildDir) { $BuildDir = Join-Path $repo 'build' }
if (-not $VanillaRoot -and $GameRoot) { $VanillaRoot = Join-Path $GameRoot 'users\modwork\_orig\3598' }

# manifest
$m = @{}
foreach ($line in Get-Content (Join-Path $repo 'manifest.txt')) { if ($line -match '^\s*([^#=]+?)\s*=\s*(.*?)\s*$') { $m[$Matches[1]] = $Matches[2] } }
$name = $m['name']; $ver = $m['version']; $addonPath = $m['addon_path']; $authors = $m['authors']
if (-not $addonPath) { throw 'manifest.txt needs addon_path=<folder name under data\common>' }
if (-not $m['table_merge_order']) { throw 'manifest.txt needs table_merge_order=vanilla > <module> > <module> ...' }
$verNum = [uint32](($ver.Split('.') | ForEach-Object { [int]$_ }) | ForEach-Object -Begin { $v = 0 } -Process { $v = $v * 100 + $_ } -End { $v })
$separate = @(); if ($m['separate_modules']) { $separate = @($m['separate_modules'] -split ',' | ForEach-Object { $_.Trim() }) }

# conflict check + merge plan (one line per contribution, in application order)
$plan = @(& (Join-Path $PSScriptRoot 'check_conflicts.ps1') -SrcRoot (Join-Path $repo 'src') -MergeOrder $m['table_merge_order'] -Skip $separate -Prefix $m['prefix'] -Plan)
if ($LASTEXITCODE -ne 0) { throw 'conflict check failed' }
foreach ($s in $separate) { "[$s] built separately (see tools\build_sounds.ps1)" }

# archive -> ordered entries -> contributions   (archives named camps/<chapter>/<op> are operation packs, see below)
$archives = New-Object Collections.Specialized.OrderedDictionary
$camps = New-Object Collections.Specialized.OrderedDictionary
foreach ($line in $plan) {
    if ($line -notmatch '^plan\|') { continue }
    $f = $line.Split('|')
    $c = @{ archive = $f[1]; name = $f[2]; kind = $f[3]; loc = $f[4]; module = $f[5]; whole = ($f[6] -eq 'whole'); path = $f[7] }
    $key = ("$($c.name).$($c.kind).$($c.loc)").ToLowerInvariant()
    $dict = $archives; if ($c.archive -like 'camps/*') { $dict = $camps }
    if (-not $dict.Contains($c.archive)) { $dict[$c.archive] = New-Object Collections.Specialized.OrderedDictionary }
    if (-not $dict[$c.archive].Contains($key)) { $dict[$c.archive][$key] = New-Object Collections.Generic.List[object] }
    $dict[$c.archive][$key].Add($c)
}
if ($archives.Count -eq 0 -and $camps.Count -eq 0) { throw 'nothing to build: no src\<module>\<archive>\!flatlist found' }

function Vanilla-Entry([string]$file) {
    if (-not $VanillaRoot) { throw "$file is built from deltas and needs the pristine vanilla tables: set GTMF_ROOT (uses <GameRoot>\users\modwork\_orig\3598), GTMF_VANILLA or -VanillaRoot" }
    $hit = @(Get-ChildItem -Path $VanillaRoot -Recurse -File -Filter $file | Select-Object -First 1)
    if (-not $hit.Count) { throw "no vanilla $file under $VanillaRoot (unpack the vanilla archive there with tools\gt3.ps1 unpack)" }
    $hit[0].FullName
}

$core = Join-Path $BuildDir 'core'
if (Test-Path $core) { Remove-Item $core -Recurse -Force }
$packed = Join-Path $core 'shared\packed_data'
New-Item -ItemType Directory -Force $packed | Out-Null
$merge = Join-Path $BuildDir 'merge'
if (Test-Path $merge) { Remove-Item $merge -Recurse -Force }

foreach ($archive in $archives.Keys) {
    $stage = Join-Path $merge $archive
    $steps = Join-Path $merge "_steps\$archive"
    New-Item -ItemType Directory -Force $stage, $steps | Out-Null
    $list = @('i_unflat:unflat()', '{')
    foreach ($key in $archives[$archive].Keys) {
        $cs = $archives[$archive][$key]
        $file = '{0}.{1}.{2}.bin' -f $cs[0].name, $cs[0].kind, $cs[0].loc
        $final = Join-Path $stage $file
        $cur = $null; $trail = @(); $n = 0
        foreach ($c in $cs) {
            if ($c.whole) { Copy-Item $c.path $final -Force; $cur = $final; $trail += "$($c.module) (whole)" }
            else {
                if (-not $cur) { $cur = Vanilla-Entry $file; $trail += 'vanilla' }
                $n++
                $step = Join-Path $steps ('{0}.{1}.{2}.{3}_{4}.bin' -f $c.name, $c.kind, $c.loc, $n, $c.module)
                $r = @(& $gt3 apply $cur $c.path $step)
                $trail += "$($c.module) $(Split-Path $c.path -Leaf) ($($r[0]))"
                $cur = $step
            }
        }
        if ($cur -ne $final) { Copy-Item $cur $final -Force }
        "[$archive] $($cs[0].name) <- $($trail -join ' + ')"
        $list += ("`t{0,-30}, {1,-16}, {2} ;" -f $cs[0].name, $cs[0].kind, $cs[0].loc)
    }
    $list += '}'
    [IO.File]::WriteAllLines((Join-Path $stage '!flatlist'), [string[]]$list, [Text.Encoding]::ASCII)
    & $gt3 pack (Join-Path $packed "$archive.flatdata") $stage
}

# Operation packs (M2): src\<module>\camps\<chapter>\<op>\ holds deltas/whole entries for the six entries of the vanilla
# data\oprum\shared\camps\<chapter>\<op>.campack2 (desc, div_pool, scripts, text x2, op_image). The vanilla pack is
# unpacked, every entry merged like a table entry (untouched ones copied), and the pack is rebuilt under
# core\shared\camps\<chapter>\<op>.campack2, which the updater installs as data\common\<addon>\shared\camps\... (the DLC layout).
foreach ($arc in $camps.Keys) {
    $parts = $arc.Split('/'); $chapter = $parts[1]; $op = $parts[2]
    $vpack = $null
    if ($VanillaRoot -and (Test-Path (Join-Path $VanillaRoot "camps\$chapter\$op.campack2"))) { $vpack = Join-Path $VanillaRoot "camps\$chapter\$op.campack2" }
    elseif ($GameRoot) { $vpack = Join-Path $GameRoot "data\oprum\shared\camps\$chapter\$op.campack2" }
    if (-not $vpack -or -not (Test-Path $vpack)) { throw "operation pack $chapter\$op.campack2 not found under <VanillaRoot>\camps\ or <GameRoot>\data\oprum\shared\camps\" }
    $vdir = Join-Path $merge "_vanilla_camps\$chapter\$op"
    New-Item -ItemType Directory -Force $vdir | Out-Null
    & $gt3 unpack $vpack $vdir | Out-Null
    $stage = Join-Path $merge "camps\$chapter\$op"
    $steps = Join-Path $merge "_steps\camps_${chapter}_$op"
    New-Item -ItemType Directory -Force $stage, $steps | Out-Null
    $list = @('i_unflat:unflat()', '{')
    foreach ($vl in Get-Content (Join-Path $vdir '!flatlist')) {
        if ($vl -notmatch '^\s*([^,;\s]+)\s*,\s*([^,;\s]+)\s*,\s*([^,;\s]+)\s*;') { continue }
        $ename = $Matches[1]; $ekind = $Matches[2]; $eloc = $Matches[3]   # not $name: that is the add-on name from the manifest
        $file = "$ename.$ekind.$eloc.bin"; $key = $file.Substring(0, $file.Length - 4).ToLowerInvariant()
        $final = Join-Path $stage $file
        $cur = Join-Path $vdir $file; $trail = @('vanilla'); $n = 0
        if ($camps[$arc].Contains($key)) {
            foreach ($c in $camps[$arc][$key]) {
                if ($c.whole) { Copy-Item $c.path $final -Force; $cur = $final; $trail = @("$($c.module) (whole)") }
                else {
                    $n++
                    $step = Join-Path $steps ('{0}.{1}_{2}.bin' -f $file.Substring(0, $file.Length - 4), $n, $c.module)
                    $r = @(& $gt3 apply $cur $c.path $step)
                    $trail += "$($c.module) $(Split-Path $c.path -Leaf) ($($r[0]))"
                    $cur = $step
                }
            }
        }
        if ($cur -ne $final) { Copy-Item $cur $final -Force }
        "[$arc] $ename.$ekind.$eloc <- $($trail -join ' + ')"
        $list += ("`t{0,-30}, {1,-16}, {2} ;" -f $ename, $ekind, $eloc)
    }
    $list += '}'
    [IO.File]::WriteAllLines((Join-Path $stage '!flatlist'), [string[]]$list, [Text.Encoding]::ASCII)
    $outPack = Join-Path $core "shared\camps\$chapter\$op.campack2"
    New-Item -ItemType Directory -Force (Split-Path $outPack) | Out-Null
    & $gt3 pack $outPack $stage
}

# data fingerprint: SHA-256 over the sorted list of "<archive> <sha256 of the packed archive>" lines, first 6 hex digits.
# It changes whenever any shipped entry changes, so two players comparing it (Version menu, lobby tag, tools\mp_fingerprint.ps1)
# know they run the same data. MiusPlayer simulates the whole battle on both PCs and never checks this itself.
$fpLines = Get-ChildItem $core -Recurse -Include *.flatdata, *.campack2 | Sort-Object Name | ForEach-Object { '{0} {1}' -f $_.Name, (Get-FileHash $_.FullName -Algorithm SHA256).Hash }
$fpBytes = [Text.Encoding]::ASCII.GetBytes(($fpLines -join "`n"))
$fingerprint = ([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($fpBytes)) -replace '-', '').Substring(0, 6)
[IO.File]::WriteAllLines((Join-Path $BuildDir 'fingerprint.txt'), [string[]](@("$name $ver fingerprint $fingerprint") + $fpLines), [Text.Encoding]::ASCII)
"data fingerprint $fingerprint (build\fingerprint.txt)"

# descriptor: the fingerprint rides in the add-on name so it shows in the game's Version menu
& $gt3 desc (Join-Path $PSScriptRoot 'templates\desc_template.addpack') (Join-Path $core 'desc.addpack') `
    "path=$addonPath" "desc=$name $ver [$fingerprint]" "authors=$authors" "version=$verNum"
& $gt3 azcf (Join-Path $core 'desc.addpack') | Select-Object -Skip 1

# package
$outName = ('{0}_{1}.gt3ext' -f ($addonPath), $ver)
$out = Join-Path $BuildDir $outName
& $gt3 gt3ext $out $core
"built $out ($([Math]::Round((Get-Item $out).Length / 1KB)) KB)"

if ($Install) {
    if (-not $GameRoot -or -not (Test-Path (Join-Path $GameRoot 'starter_x64.exe'))) { throw 'GameRoot (or GTMF_ROOT) must point at the folder containing starter_x64.exe' }
    $dst = Join-Path $GameRoot 'new_updates'
    Get-ChildItem $dst -Filter "$addonPath*.gt3ext" -ErrorAction SilentlyContinue | Remove-Item -Force
    Copy-Item $out $dst
    "installed into $dst - start the game once; the updater installs it into data\common\$addonPath and registers it in data\common\shared\config\paths.cfgpack"
}
