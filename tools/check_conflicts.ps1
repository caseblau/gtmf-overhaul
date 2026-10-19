<#
.SYNOPSIS
  Conflict check and merge plan for src\. Exit 1 on any violation; with -Plan it also prints one line per contribution
  in application order, which build.ps1 turns into the merged entries (DESIGN.md 1.3 and 7.3).

.DESCRIPTION
  src\<module>\<archive>\!flatlist lists the entries the module contributes to that archive. Each listed entry is either
    <name>.<kind>.<loc>.bin                 a whole entry (replaces vanilla; the only form for text, texture, sound entries)
    <name>.<kind>.<loc>[.<tag>].delta       a row-level AZCF delta (tools\gt3.ps1 diff format) on top of what the earlier
                                            modules left; a module may stack several, applied in tag order (number them)
  The engine takes one entry per name from one archive, so for every entry name:
    - it ships in exactly one archive (every module that touches it uses the same archive folder name)
    - at most one module ships it whole, and only the first contributing module may (later modules must send deltas)
    - a module contributes it either whole or as deltas, not both
    - deltas come only from modules named in -MergeOrder (manifest table_merge_order) and only on config entries
    - nothing on the MiusPlayer transport's do-not-touch list is shipped under any name

.EXAMPLE
  tools\check_conflicts.ps1 -SrcRoot src -MergeOrder 'vanilla > m8_vfx > m9_ap_port > m1_core > m2_oob > m3_quickbattle' -Skip m6_sound -Prefix mfo_ -Plan
#>
param(
    [Parameter(Mandatory = $true)][string]$SrcRoot,
    [string]$MergeOrder = '',      # modules whose deltas stack, in application order ('>' or ',' separated; 'vanilla' ignored)
    [string[]]$Skip = @(),         # modules built separately (manifest separate_modules)
    [string]$Prefix = '',          # archive folders must start with it (or be ch_sounds / ch_textures)
    [switch]$Plan                  # emit 'plan|<archive>|<name>|<kind>|<loc>|<module>|whole|delta|<path>' lines
)
$ErrorActionPreference = 'Stop'

# Files owned by the MiusPlayer transport layer. Shipping any of these would break multiplayer.
$transportOwned = @(
    'opgame.progpack', 'tacgame.progpack', 'basic_network.codelib',
    'steam_appid.txt', 'mp_join.exe', 'enable_multiplayer.bat', 'disable_multiplayer.bat'
)
$transportExt = @('.progpack', '.codelib')

$errors = New-Object Collections.Generic.List[string]
$order = @($MergeOrder -split '[,>]' | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -ne 'vanilla' })
$skipList = @($Skip | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$modules = @(Get-ChildItem -Path $SrcRoot -Directory | Where-Object { $skipList -notcontains $_.Name })
# merge-order modules first, in that order; every other module after them, alphabetically (whole entries only)
$ranked = @()
foreach ($name in $order) { $d = $modules | Where-Object { $_.Name -eq $name }; if ($d) { $ranked += $d } }
$ranked += @($modules | Where-Object { $order -notcontains $_.Name } | Sort-Object Name)

# entry key (name.kind.loc, lower case) -> list of contributions in application order
$contrib = New-Object Collections.Specialized.OrderedDictionary
$fileCount = 0
foreach ($module in $ranked) {
    # src\<module>\<archive>\ -> a packed_data archive; src\<module>\camps\<chapter>\<op>\ -> one operation pack
    # (data\common\<addon>\shared\camps\<chapter>\<op>.campack2), treated as an archive named camps/<chapter>/<op>.
    $arcDirs = @()
    foreach ($d in Get-ChildItem -Path $module.FullName -Directory) {
        if ($d.Name -eq 'camps') {
            foreach ($ch in Get-ChildItem -Path $d.FullName -Directory) { foreach ($op in Get-ChildItem -Path $ch.FullName -Directory) { $arcDirs += @{ dir = $op; name = "camps/$($ch.Name)/$($op.Name)" } } }
        } else { $arcDirs += @{ dir = $d; name = $d.Name } }
    }
    foreach ($ad in $arcDirs) {
        $arc = [pscustomobject]@{ FullName = $ad.dir.FullName; Name = $ad.name }
        $flat = Join-Path $arc.FullName '!flatlist'
        $files = @(Get-ChildItem -Path $arc.FullName -File -Recurse | Where-Object { -not $_.Name.StartsWith('.') -and $_.Name -ne '!flatlist' })
        if (-not (Test-Path $flat)) {
            if ($files.Count) { $errors.Add("$($module.Name)\$($arc.Name): has files but no !flatlist, so nothing in it is built") }
            continue
        }
        if ($Prefix -and $arc.Name -notlike "$Prefix*" -and $arc.Name -notlike 'camps/*' -and $arc.Name -notin @('ch_sounds', 'ch_textures')) {
            # ch_sounds / ch_textures are the engine's own add-on override archive names (what the in-game builder writes).
            # Vanilla uses sounds*/tex_* so they shadow nothing. Everything else must carry our prefix.
            $errors.Add("$($module.Name)\$($arc.Name): archive folder must start with $Prefix (or be ch_sounds / ch_textures) so it never shadows a vanilla archive name")
        }
        $listed = New-Object Collections.Specialized.OrderedDictionary
        foreach ($line in Get-Content $flat) {
            if ($line -match '^\s*([^,;\s]+)\s*,\s*([^,;\s]+)\s*,\s*([^,;\s]+)\s*;') { $listed[("$($Matches[1]).$($Matches[2]).$($Matches[3])").ToLowerInvariant()] = @{ name = $Matches[1]; kind = $Matches[2]; loc = $Matches[3] } }
        }
        $here = @{}   # entry key -> @{ whole; deltas }
        foreach ($f in $files) {
            $fileCount++
            $lname = $f.Name.ToLowerInvariant()
            if ($transportOwned -contains $lname -or $transportExt -contains $f.Extension.ToLowerInvariant()) { $errors.Add("$($f.Name) in $($module.Name): owned by the MiusPlayer transport, must not be shipped") }
            if ($f.Name -match '^(.+?)\.(\w+)\.(\w+)\.bin$') { $key = "$($Matches[1]).$($Matches[2]).$($Matches[3])".ToLowerInvariant(); $isDelta = $false; $tag = '' }
            elseif ($f.Name -match '^(.+?)\.(\w+)\.(\w+)(?:\.([^.]+))?\.delta$') { $key = "$($Matches[1]).$($Matches[2]).$($Matches[3])".ToLowerInvariant(); $isDelta = $true; $tag = [string]$Matches[4] }
            else { $errors.Add("$($module.Name)\$($arc.Name)\$($f.Name): not <name>.<kind>.<loc>.bin or <name>.<kind>.<loc>[.<tag>].delta"); continue }
            if (-not $listed.Contains($key)) { $errors.Add("$($module.Name)\$($arc.Name)\$($f.Name): not listed in !flatlist"); continue }
            $lkey = $key
            if ($arc.Name -like 'camps/*') { $key = "$($arc.Name):$key" }   # the same entry names repeat in every operation pack
            if (-not $here.ContainsKey($key)) { $here[$key] = @{ whole = $null; deltas = @() } }
            if ($isDelta) {
                if ($listed[$lkey].kind -ne 'config') { $errors.Add("$($module.Name)\$($arc.Name)\$($f.Name): deltas exist only for config (AZCF) entries") }
                if ($order -notcontains $module.Name) { $errors.Add("$($module.Name)\$($arc.Name)\$($f.Name): module $($module.Name) is not in table_merge_order, it may ship whole entries only") }
                $here[$key].deltas += @{ tag = $tag; path = $f.FullName }
            }
            else { $here[$key].whole = $f.FullName }
        }
        foreach ($lkey in $listed.Keys) {
            $key = $lkey; if ($arc.Name -like 'camps/*') { $key = "$($arc.Name):$lkey" }
            if (-not $here.ContainsKey($key)) { $errors.Add("$($module.Name)\$($arc.Name): $lkey is listed in !flatlist but has no .bin or .delta file"); continue }
            $e = $listed[$lkey]; $h = $here[$key]
            if ($h.whole -and $h.deltas.Count) { $errors.Add("$($module.Name)\$($arc.Name): $key is shipped whole and as a delta by the same module; keep one") }
            if (-not $contrib.Contains($key)) { $contrib[$key] = New-Object Collections.Generic.List[object] }
            if ($h.whole) { $contrib[$key].Add(@{ module = $module.Name; archive = $arc.Name; name = $e.name; kind = $e.kind; loc = $e.loc; whole = $true; path = $h.whole; tag = '' }) }
            foreach ($d in ($h.deltas | Sort-Object { $_.tag })) { $contrib[$key].Add(@{ module = $module.Name; archive = $arc.Name; name = $e.name; kind = $e.kind; loc = $e.loc; whole = $false; path = $d.path; tag = $d.tag }) }
        }
    }
}

$merged = 0
foreach ($key in $contrib.Keys) {
    $list = $contrib[$key]
    $archives = @($list | ForEach-Object { $_.archive.ToLowerInvariant() } | Select-Object -Unique)
    if ($archives.Count -gt 1) { $errors.Add("${key}: shipped in more than one archive ($(($list | ForEach-Object { "$($_.module)\$($_.archive)" } | Select-Object -Unique) -join ', ')); one entry, one archive") }
    $wholes = @($list | Where-Object { $_.whole })
    if ($wholes.Count -gt 1) { $errors.Add("${key}: shipped whole by $(($wholes | ForEach-Object { $_.module }) -join ' and '); only one module may, the others must send deltas") }
    elseif ($wholes.Count -eq 1 -and -not $list[0].whole) { $errors.Add("${key}: $($wholes[0].module) ships it whole but $($list[0].module) comes earlier in table_merge_order and contributes a delta; a whole entry must come from the first contributing module (convert $($wholes[0].module)'s copy to a delta)") }
    if (@($list | ForEach-Object { $_.module } | Select-Object -Unique).Count -gt 1) { $merged++ }
}

if ($errors.Count -gt 0) {
    Write-Host 'Conflicts in src\:'
    $errors | ForEach-Object { Write-Host "  $_" }
    exit 1
}
Write-Host "No conflicts. $($contrib.Count) entries from $fileCount files across $($ranked.Count) modules; $merged entries merged from more than one module (order: $(($ranked | ForEach-Object { $_.Name }) -join ' > '))."
if ($Plan) {
    foreach ($key in $contrib.Keys) {
        foreach ($c in $contrib[$key]) { 'plan|{0}|{1}|{2}|{3}|{4}|{5}|{6}' -f $c.archive, $c.name, $c.kind, $c.loc, $c.module, $(if ($c.whole) { 'whole' } else { 'delta' }), $c.path }
    }
}
exit 0
