param(
    [string]$GameRoot = $env:GTMF_ROOT,
    [string]$Catalog = (Join-Path $PSScriptRoot '..\docs\archive_catalog.txt'),
    [string]$Out = (Join-Path $PSScriptRoot '..\docs\addon_matrix.txt')
)
# Builds an entry-level override matrix: for every (entry name, kind) that appears in more than one
# source (vanilla archive or installed add-on archive), list all the sources. The engine overrides by
# entry name + kind regardless of archive, so every row here is a real override or a real conflict.

if (-not $GameRoot) { throw 'GTMF_ROOT not set' }
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
$map = @{}   # key "name|kind" -> list of source labels
function Add-Entry([string]$name, [string]$kind, [string]$src) {
    $k = "$name|$kind"
    if (-not $map.ContainsKey($k)) { $map[$k] = New-Object System.Collections.Generic.List[string] }
    if (-not $map[$k].Contains($src)) { $map[$k].Add($src) }
}

# 1. vanilla, from the catalog (only data\common\shared, loc_*, addons, oprum etc. — skip data\common\<addon> folders)
$cur = $null
foreach ($line in Get-Content $Catalog) {
    if ($line -match '^## (.+?)\s+\(') {
        $p = $Matches[1]
        $cur = $null
        if ($p -match '^data\\common\\([^\\]+)\\') {
            $top = $Matches[1]
            if ($top -in @('shared','loc_eng','loc_rus')) { $cur = "vanilla:$([IO.Path]::GetFileNameWithoutExtension($p))" }
        } elseif ($p -match '^(data\\addons|data\\oprum|data\\k42|root)') {
            $cur = "vanilla:$([IO.Path]::GetFileNameWithoutExtension($p))"
        }
        continue
    }
    if ($cur -and $line -match '^\s{4}(\S+)\s+(\S+)\s+(\S+)\s+[\d\s]+$') { Add-Entry $Matches[1] $Matches[2] $cur }
}

# 2. installed add-ons: every data\common\<folder>\**\*.flatdata where <folder> is not vanilla/DLC
$labels = @{}
Get-ChildItem (Join-Path $GameRoot 'data\common') -Directory | Where-Object { $_.Name -notin @('shared','loc_eng','loc_rus') -and $_.Name -notlike 'ma_*' } | ForEach-Object {
    $folder = $_
    $label = $folder.Name
    $desc = Join-Path $folder.FullName 'desc.addpack'
    if (Test-Path $desc) {
        $d = & powershell -NoProfile -ExecutionPolicy Bypass -File $gt3 nodes $desc 2>$null | Out-String
        if ($d -match 'desc=([^\r\n/]+?)\s*(//|$)') { $label = "$($Matches[1].Trim()) [$($folder.Name)]" }
    }
    $labels[$folder.Name] = $label
    Get-ChildItem $folder.FullName -Recurse -Filter *.flatdata | ForEach-Object {
        $arc = $_.BaseName
        Write-Host "listing $label / $arc"
        & powershell -NoProfile -ExecutionPolicy Bypass -File $gt3 list $_.FullName 2>$null | ForEach-Object {
            if ($_ -match '^\s*\d+\s+(\S+)\s+(\S+)\s+(\S+)\s+off=') { Add-Entry $Matches[1] $Matches[2] "$label/$arc" }
        }
    }
}

# 3. report
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("# Add-on override matrix, generated $(Get-Date -Format s)")
[void]$sb.AppendLine("# rows: entries present in more than one source. Sources: vanilla:<archive> or <add-on desc> [<folder>]/<archive>")
[void]$sb.AppendLine()
$multi = $map.GetEnumerator() | Where-Object { $_.Value.Count -gt 1 } | Sort-Object Key
$perSrc = @{}
foreach ($e in $multi) {
    $name, $kind = $e.Key.Split('|')
    [void]$sb.AppendLine(("{0,-34} {1,-10} <- {2}" -f $name, $kind, ($e.Value -join ' ; ')))
    $addons = $e.Value | Where-Object { $_ -notlike 'vanilla:*' }
    foreach ($a in $addons) {
        $top = $a.Split('/')[0]
        if (-not $perSrc.ContainsKey($top)) { $perSrc[$top] = @{ overridesVanilla = 0; collidesAddon = 0 } }
        if ($e.Value | Where-Object { $_ -like 'vanilla:*' }) { $perSrc[$top].overridesVanilla++ }
        if (($addons | ForEach-Object { $_.Split('/')[0] } | Select-Object -Unique).Count -gt 1) { $perSrc[$top].collidesAddon++ }
    }
}
[void]$sb.AppendLine()
[void]$sb.AppendLine('# Summary per add-on: entries overriding vanilla / entries also overridden by another add-on')
foreach ($k in $perSrc.Keys | Sort-Object) { [void]$sb.AppendLine(("{0,-60} vanilla={1,5}  addon-collisions={2,5}" -f $k, $perSrc[$k].overridesVanilla, $perSrc[$k].collidesAddon)) }
[IO.File]::WriteAllText($Out, $sb.ToString(), [Text.UTF8Encoding]::new($false))
Write-Host "wrote $Out ($($multi.Count) shared entries)"
$sb.ToString().Split("`n") | Select-Object -Last ($perSrc.Count + 3)
