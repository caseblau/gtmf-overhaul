<#
.SYNOPSIS
  M12 terrain probe 2: open two Mius cells (MgG3 centre, MxD1 border) with gt3.ps1, list their entries, and copy every
  entry up to 12 MB (hei_map, max_map, mat_map, vars_map, det_map, water_map, nor_map, grass_map, flora/obj quads, opmap)
  into docs\m12_terrain\samples\cells\<cell>\. Also decodes the 6m_mius_a descriptor and dumps the .aomap header.
  Read-only on the game.
#>
param([string]$GameRoot = $env:GTMF_ROOT, [string[]]$Cells = @('MgG3', 'MxD1'))
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
. $gt3 lib
$outDir = Join-Path $repo 'docs\m12_terrain'
$reportPath = Join-Path $outDir 'probe2_report.txt'
$Writer = New-Object IO.StreamWriter($reportPath, $false, (New-Object Text.UTF8Encoding $true)); $Writer.AutoFlush = $true
function Say([string]$s) { $s; $Writer.WriteLine($s) }
function Asc-Head([byte[]]$b, [int64]$off, [int]$n) { ([Text.Encoding]::ASCII.GetString($b, [int]$off, $n) -replace '[^\x20-\x7e]', '.') }
trap { Say "!! ERROR: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"; continue }
if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
$poly = Join-Path $GameRoot 'data\oprum\shared\polygons\6m_mius'
Say "# M12 terrain probe 2  $(Get-Date -Format s)"
Say "polygon folder = $poly"

foreach ($cell in $Cells) {
    $pack = Join-Path $poly "${cell}_mius.polypack2"
    if (-not (Test-Path $pack)) { Say "missing $pack"; continue }
    $p = Read-Azp3 $pack
    Say ''
    Say "## $cell : $($p.count) entries, sig '$($p.sig)'"
    $dir = Join-Path $outDir "samples\cells\$cell"
    New-Item -ItemType Directory -Force $dir | Out-Null
    foreach ($e in $p.entries) {
        $copied = ''
        if ($e.size -le 12MB) {
            $blob = New-Object byte[] $e.size; [Array]::Copy($p.bytes, [int64]$e.offset, $blob, 0, [int64]$e.size)
            [IO.File]::WriteAllBytes((Join-Path $dir ('{0}.{1}.{2}.bin' -f $e.name, $e.kind, $e.loc)), $blob); $copied = 'copied'
        }
        $hdr = Asc-Head $p.bytes ([int64]$e.offset) 16
        Say ("  {0,3} {1,-24} {2,-10} {3,-8} {4,12:n0}  {5,-18} {6}" -f $e.index, $e.name, $e.kind, $e.loc, $e.size, $hdr, $copied)
    }
}

# the autumn/alternate polygon descriptor
$alt = Join-Path $GameRoot 'data\oprum\shared\polygons\6m_mius_a\6m_mius_a.cfgpack'
if (Test-Path $alt) {
    $dst = Join-Path $outDir 'samples\6m_mius_a.cfgpack'; Copy-Item $alt $dst -Force
    & $gt3 azcf $alt 2>&1 | Set-Content "$dst.azcf.txt" -Encoding UTF8
    Say ''
    Say "## 6m_mius_a descriptor decoded -> $dst.azcf.txt"
    Get-Content "$dst.azcf.txt" | Select-Object -First 30 | ForEach-Object { Say "    $_" }
}
# aomap header
$ao = Join-Path $poly 'mgg3_mius_ao.aomap'
if (Test-Path $ao) {
    $fs = [IO.File]::OpenRead($ao); $b = New-Object byte[] 64; $n = $fs.Read($b, 0, 64); $fs.Close()
    Say ''
    Say "## aomap header (mgg3): $((($b[0..63] | ForEach-Object { '{0:x2}' -f $_ }) -join ' '))"
}
Say ''
Say 'done'
$Writer.Close()
"report: $reportPath"
