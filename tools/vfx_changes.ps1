<#
.SYNOPSIS
  Side-by-side of every particle value the overhaul changes: pristine vanilla parts table vs the current merged build.
  Writes docs\vfx_changes.md and prints the table.
.EXAMPLE
  tools\vfx_changes.ps1    (needs GTMF_ROOT, and a prior build.ps1 run for build\merge\mfo_vfx\parts.config.loc_def.bin)
#>
param(
    [string]$GameRoot = $env:GTMF_ROOT
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
$van = Join-Path $GameRoot 'users\modwork\_orig\3598\tabs\parts.config.loc_def.bin'
$cur = Join-Path $repo 'build\merge\mfo_vfx\parts.config.loc_def.bin'
$tmp = Join-Path $repo 'build\tp\vfx_all.delta'
& powershell -NoProfile -ExecutionPolicy Bypass -File $gt3 diff $van $cur $tmp | Out-Null

$names = @{
    'pgens_desc' = @{ 'c1' = 'ground flag'; 'c2' = 'generator type'; 'c5' = 'particles per burst'; 'c6' = 'particle used' }
    'parts_desc' = @{ 'c6' = 'vertical accel (neg = down)'; 'c7' = 'sprite cell (never touch)'; 'c9' = 'start size (m)'; 'c10' = 'end size (m)'; 'c11' = 'birth colour keyframes ARGB'; 'c12' = 'end colour keyframes ARGB'; 'c13' = 'life s; fade-in s; spin tau; velocity tau'; 'c14' = 'variation amplitude (max 0.75)'; 'c22' = 'ease-out exponent'; 'c23' = 'spin rate deg/s'; 'c24' = 'draw/motion mode'; 'c26' = 'wetness gate (-1 = none)' }
}
function Hex([string]$v) {
    ($v -split ';' | ForEach-Object { $n = [int64]$_; if ($n -lt 0) { $n += 4294967296 }; '0x{0:X8}' -f $n }) -join ';'
}
function Dec([string]$v) {
    if ($v -match '^a:(.*)$') { return Hex $Matches[1] }
    if ($v -match "^u:'(.*)'$") { return $Matches[1] }
    $v -replace '^[a-z]:', ''
}
$cache = @{}
function Vals([string]$file, [string]$node, [string]$row) {
    $key = "$file|$node"
    if (-not $cache.ContainsKey($key)) {
        $csv = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $gt3 csv $file $node)
        $hdr = ($csv[0] -split ',') | ForEach-Object { ($_ -split ':')[0] }
        $tbl = @{}
        foreach ($line in ($csv | Select-Object -Skip 1)) {
            $cells = New-Object Collections.Generic.List[string]
            foreach ($m in [regex]::Matches($line, '("([^"]*)"|[^,]*)(,|$)')) { if ($m.Groups[2].Success) { $cells.Add($m.Groups[2].Value) } else { $cells.Add($m.Groups[1].Value) } }
            $h = @{}
            for ($i = 0; $i -lt $hdr.Count -and $i -lt $cells.Count; $i++) { $h[$hdr[$i]] = $cells[$i] }
            $tbl[$cells[0]] = $h
        }
        $cache[$key] = $tbl
    }
    $cache[$key][$row]
}
# who touched each row: Toni's delta (tag *_rbvfx2) vs every other delta of the module
$toni = @{}; $ours = @{}
foreach ($f in Get-ChildItem (Join-Path $repo 'src\m8_vfx\mfo_vfx') -Filter 'parts.config.loc_def.*.delta') {
    $isToni = $f.Name -match '_rbvfx2\.delta$'
    foreach ($l in Get-Content $f.FullName) {
        if ($l -match '^row[~+]\|([^|]+)\|([^|]+)\|') { $k = "$($Matches[1])|$($Matches[2])"; if ($isToni) { $toni[$k] = 1 } else { $ours[$k] = 1 } }
    }
}
$rows = New-Object Collections.Generic.List[string]
$rows.Add('| table | row | value | vanilla | now | who |')
$rows.Add('|---|---|---|---|---|---|')
foreach ($l in Get-Content $tmp) {
    if ($l -notmatch '^row~\|([^|]+)\|([^|]+)\|(.*)$') { continue }
    $node = $Matches[1]; $row = $Matches[2]; $cells = $Matches[3] -split '\|'
    $vv = Vals $van $node $row
    foreach ($c in $cells) {
        if ($c -notmatch '^(c\d+)=(.*)$') { continue }
        $col = $Matches[1]; $newv = Dec $Matches[2]
        $old = if ($vv) { $vv[$col] } else { '?' }
        if ($names[$node][$col] -match 'colour' -and $old -match '^-?\d+(;-?\d+)*$') { $old = Hex $old }
        $k = "$node|$row"
        $who = if ($toni[$k] -and $ours[$k]) { 'Toni + overhaul' } elseif ($toni[$k]) { 'Toni' } else { 'overhaul' }
        $label = if ($names[$node][$col]) { "$col $($names[$node][$col])" } else { $col }
        $rows.Add("| $node | $row | $label | $old | $newv | $who |")
    }
}
$ver = (Select-String -Path (Join-Path $repo 'manifest.txt') -Pattern '^version=(.*)').Matches[0].Groups[1].Value
$doc = @('# VFX changes, vanilla vs current build', '',
    "Generated $(Get-Date -Format 'yyyy-MM-dd HH:mm') from the pristine 3598 parts table and build\merge\mfo_vfx\parts (version $ver).",
    'Rows Toni (RBVFX Part 2) also changed are marked; his changes to rows the overhaul never touched are not listed.',
    'Column meanings marked (hyp.) are inferred from vanilla usage, not documented. Colours are ARGB; alpha 0x00 = invisible.', '') + $rows
[IO.File]::WriteAllLines((Join-Path $repo 'docs\vfx_changes.md'), $doc, (New-Object Text.UTF8Encoding $false))
$doc | Select-Object -Skip 5
