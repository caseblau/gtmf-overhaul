<#
.SYNOPSIS
  M12 terrain probe 1: where the Mius-Front terrains ("polygons") live and what files they consist of.
  The operation desc names its terrain as polygon=polygons\6M_Mius\6M_Mius.cfgpack with a camp_area cell rectangle, so
  this lists every polygons\ folder on the install, dumps the header bytes of each file type, decodes every .cfgpack
  there with gt3.ps1 azcf, and copies the small files (< 3 MB) into docs\m12_terrain\samples\ for analysis.
  Read-only on the game.
#>
param([string]$GameRoot = $env:GTMF_ROOT)
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
$outDir = Join-Path $repo 'docs\m12_terrain'
$samples = Join-Path $outDir 'samples'
New-Item -ItemType Directory -Force $outDir, $samples | Out-Null
$reportPath = Join-Path $outDir 'probe1_report.txt'
$Writer = New-Object IO.StreamWriter($reportPath, $false, (New-Object Text.UTF8Encoding $true)); $Writer.AutoFlush = $true
function Say([string]$s) { $s; $Writer.WriteLine($s) }
trap { Say "!! ERROR: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"; continue }
function Hex([byte[]]$b, [int]$off, [int]$n) { (($b[$off..($off + $n - 1)] | ForEach-Object { '{0:x2}' -f $_ }) -join ' ') }
function Asc([byte[]]$b, [int]$off, [int]$n) { ([Text.Encoding]::ASCII.GetString($b, $off, $n) -replace '[^\x20-\x7e]', '.') }
function Dump-Head([string]$path, [int]$n) {
    $fs = [IO.File]::OpenRead($path); $b = New-Object byte[] $n; $got = $fs.Read($b, 0, $n); $fs.Close()
    for ($o = 0; $o -lt $got; $o += 32) { $len = [Math]::Min(32, $got - $o); Say ("    {0:x4}  {1,-96} {2}" -f $o, (Hex $b $o $len), (Asc $b $o $len)) }
}
if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
Say "# M12 terrain probe 1  $(Get-Date -Format s)"
Say "GameRoot = $GameRoot"

# 1. every folder named polygons (or levels) anywhere under data\
$polyDirs = Get-ChildItem (Join-Path $GameRoot 'data') -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -in 'polygons', 'levels', 'maps', 'terrains' }
Say ''
Say "## terrain folders ($($polyDirs.Count))"
foreach ($d in $polyDirs) {
    $files = Get-ChildItem $d.FullName -Recurse -File -ErrorAction SilentlyContinue
    Say ("- {0}: {1} files, {2:n0} bytes" -f $d.FullName.Substring($GameRoot.Length + 1), $files.Count, ($files | Measure-Object Length -Sum).Sum)
    foreach ($sub in (Get-ChildItem $d.FullName -Directory | Sort-Object Name)) {
        $sf = Get-ChildItem $sub.FullName -Recurse -File
        Say ("    {0,-28} {1,4} files {2,14:n0} bytes" -f $sub.Name, $sf.Count, ($sf | Measure-Object Length -Sum).Sum)
    }
}

# 2. one terrain in full: the Mius polygon (or the first one found)
$mius = $polyDirs | ForEach-Object { Get-ChildItem $_.FullName -Directory } | Where-Object { $_.Name -match 'Mius' } | Select-Object -First 1
if (-not $mius) { $mius = $polyDirs | ForEach-Object { Get-ChildItem $_.FullName -Directory } | Select-Object -First 1 }
if ($mius) {
    Say ''
    Say "## files of $($mius.FullName.Substring($GameRoot.Length + 1))"
    $files = Get-ChildItem $mius.FullName -Recurse -File | Sort-Object FullName
    foreach ($f in $files) { Say ("  {0,14:n0}  {1}" -f $f.Length, $f.FullName.Substring($mius.FullName.Length + 1)) }
    Say ''
    Say '## extension histogram over all terrain folders'
    $all = $polyDirs | ForEach-Object { Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue }
    foreach ($g in ($all | Group-Object Extension | Sort-Object Count -Descending)) { Say ("  {0,-14} {1,5} files {2,16:n0} bytes" -f $g.Name, $g.Count, ($g.Group | Measure-Object Length -Sum).Sum) }
    Say ''
    Say '## header bytes, one file per extension (from the Mius terrain)'
    foreach ($g in ($files | Group-Object Extension)) {
        $f = $g.Group | Sort-Object Length | Select-Object -First 1
        Say ("### {0}  ({1:n0} bytes) [{2} files with this extension]" -f $f.FullName.Substring($mius.FullName.Length + 1), $f.Length, $g.Count)
        Dump-Head $f.FullName 160
        $big = $g.Group | Sort-Object Length -Descending | Select-Object -First 1
        if ($big.FullName -ne $f.FullName) { Say ("### {0}  ({1:n0} bytes)" -f $big.FullName.Substring($mius.FullName.Length + 1), $big.Length); Dump-Head $big.FullName 96 }
    }
    # 3. decode every cfgpack / addpack with gt3 azcf, copy small files
    Say ''
    Say '## AZCF configs in the terrain folder'
    foreach ($f in ($files | Where-Object { $_.Extension -in '.cfgpack', '.addpack' })) {
        $rel = $f.FullName.Substring($mius.FullName.Length + 1)
        $dst = Join-Path $samples ($mius.Name + '\' + $rel)
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        Copy-Item $f.FullName $dst -Force
        $dump = "$dst.azcf.txt"
        try { & $gt3 azcf $f.FullName 2>&1 | Set-Content $dump -Encoding UTF8; Say "  $rel -> decoded, $((Get-Content $dump).Count) lines in $dump"; Get-Content $dump | Select-Object -First 40 | ForEach-Object { Say "      $_" } }
        catch { Say "  $rel : azcf FAILED $($_.Exception.Message)" }
    }
    Say ''
    Say '## small files copied to samples\'
    foreach ($f in ($files | Where-Object { $_.Length -lt 3MB -and $_.Extension -notin '.cfgpack', '.addpack' })) {
        $rel = $f.FullName.Substring($mius.FullName.Length + 1)
        $dst = Join-Path $samples ($mius.Name + '\' + $rel)
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        Copy-Item $f.FullName $dst -Force; Say "  $rel"
    }
}

# 4. the loader: which codelib mentions polygon files
Say ''
Say '## codelibs mentioning polygon/terrain strings'
$bin = Join-Path $GameRoot 'bin\rel\x64'
if (Test-Path $bin) {
    foreach ($lib in (Get-ChildItem $bin -Filter *.codelib)) {
        $txt = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($lib.FullName))
        $hits = @()
        foreach ($nd in @('.polypack', 'polygon', 'hmap', 'heightmap', '.hmap', '.lmap', 'land_', 'soils', '.tex_land', 'polygons\')) { $c = ([regex]::Matches($txt, [regex]::Escape($nd))).Count; if ($c) { $hits += "$nd=$c" } }
        if ($hits.Count) { Say "  $($lib.Name): $($hits -join ', ')" }
    }
}
Say ''
Say 'done'
$Writer.Close()
"report: $reportPath"
