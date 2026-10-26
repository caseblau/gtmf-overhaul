<#
.SYNOPSIS
  M10 probe 2: Steel Fury's .datapack / .polypack containers. Dumps each pack's header (hex + ascii), scans the packs
  for the strings that would name a T-34-85, copies Steel Fury's loose text configs (.engcfg, .text, .engscr) into
  docs\m10_t3485\sf_cfg\ and lists its docs\, root\ and bin\ folders. Read-only on the game.
#>
param(
    [string]$SfRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Steel Fury Kharkov 1942'
)
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$outDir = Join-Path $repo 'docs\m10_t3485'
New-Item -ItemType Directory -Force $outDir | Out-Null
$reportPath = Join-Path $outDir 'probe2_report.txt'
$Writer = New-Object IO.StreamWriter($reportPath, $false, (New-Object Text.UTF8Encoding $true)); $Writer.AutoFlush = $true
function Say([string]$s) { $s; $Writer.WriteLine($s) }
trap { Say "!! ERROR: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"; continue }

Say "# M10 probe 2  $(Get-Date -Format s)"
Say "SfRoot = $SfRoot"
if (-not (Test-Path $SfRoot)) { Say 'Steel Fury folder not found'; $Writer.Close(); exit 1 }

function Hex([byte[]]$b, [int]$n) { (($b[0..($n - 1)] | ForEach-Object { '{0:x2}' -f $_ }) -join ' ') }
function Asc([byte[]]$b, [int]$n) { ([Text.Encoding]::ASCII.GetString($b, 0, $n) -replace '[^\x20-\x7e]', '.') }

# ---------- folder listings ----------
foreach ($sub in @('docs', 'root', 'bin', 'users', 'MODS', 'data', 'data\k42', 'data\k42\loc_rus')) {
    $p = Join-Path $SfRoot $sub
    if (-not (Test-Path $p)) { continue }
    Say ''
    Say "## $sub\"
    foreach ($e in (Get-ChildItem $p -ErrorAction SilentlyContinue | Sort-Object { -not $_.PSIsContainer }, Name)) {
        if ($e.PSIsContainer) { Say "  [dir]  $($e.Name)" } else { Say ("  {0,13:n0}  {1}" -f $e.Length, $e.Name) }
    }
}

# ---------- copy loose text configs ----------
$cfgOut = Join-Path $outDir 'sf_cfg'
New-Item -ItemType Directory -Force $cfgOut | Out-Null
$n = 0
foreach ($f in (Get-ChildItem (Join-Path $SfRoot 'data') -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in '.engcfg', '.text', '.engscr', '.txt', '.cfg' -and $_.Length -lt 20MB })) {
    $rel = $f.FullName.Substring($SfRoot.Length + 1)
    $dst = Join-Path $cfgOut $rel
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    Copy-Item $f.FullName $dst -Force; $n++
}
foreach ($f in (Get-ChildItem (Join-Path $SfRoot 'docs') -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in '.txt', '.htm', '.html', '.rtf', '.md' -and $_.Length -lt 5MB })) {
    $rel = $f.FullName.Substring($SfRoot.Length + 1)
    $dst = Join-Path $cfgOut $rel
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    Copy-Item $f.FullName $dst -Force; $n++
}
Say ''
Say "copied $n text files into $cfgOut"

# ---------- pack headers and string scan ----------
Say ''
Say '## packs (.datapack / .polypack / .raw): header, then string scan'
$needles = @('t34_85', 't34-85', 't-34-85', 't3485', 't34_m44', 't34_44', 'zis_s53', 'zis-s-53', 's53', 'd5t', 'd-5t', '85mm', 'br_365', 'br-365')
$packs = Get-ChildItem (Join-Path $SfRoot 'data') -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in '.datapack', '.polypack', '.raw' } | Sort-Object Extension, Name
foreach ($p in $packs) {
    $fs = [IO.File]::OpenRead($p.FullName)
    $hdr = New-Object byte[] 256; $got = $fs.Read($hdr, 0, 256)
    Say ''
    Say ("### {0}  ({1:n0} bytes)" -f $p.FullName.Substring($SfRoot.Length + 1), $p.Length)
    for ($o = 0; $o -lt [Math]::Min($got, 128); $o += 32) {
        $slice = $hdr[$o..([Math]::Min($got, $o + 32) - 1)]
        Say ("  {0:x4}  {1,-96} {2}" -f $o, (Hex $slice $slice.Count), (Asc $slice $slice.Count))
    }
    if ($p.Extension -eq '.raw') { $fs.Close(); continue }
    # string scan: ascii view of 8 MB chunks, overlap 64 bytes
    $fs.Position = 0
    $chunk = New-Object byte[] (8MB); $pos = [long]0; $hits = @{}; $names = @{}
    while (($r = $fs.Read($chunk, 0, $chunk.Length)) -gt 0) {
        $txt = [Text.Encoding]::ASCII.GetString($chunk, 0, $r)
        foreach ($nd in $needles) {
            $i = $txt.IndexOf($nd, [StringComparison]::OrdinalIgnoreCase)
            if ($i -ge 0) {
                if (-not $hits.ContainsKey($nd)) { $hits[$nd] = @() }
                while ($i -ge 0 -and $hits[$nd].Count -lt 12) {
                    $a = [Math]::Max(0, $i - 24); $b = [Math]::Min($txt.Length, $i + 40)
                    $hits[$nd] += ('0x{0:x} {1}' -f ($pos + $i), ($txt.Substring($a, $b - $a) -replace '[^\x20-\x7e]', '.'))
                    $i = $txt.IndexOf($nd, $i + 1, [StringComparison]::OrdinalIgnoreCase)
                }
            }
        }
        # generic: names that look like t34 identifiers in this chunk
        foreach ($m in [regex]::Matches($txt, '[A-Za-z0-9_\-]{0,12}t[-_]?34[A-Za-z0-9_\-]{0,16}', 'IgnoreCase')) { $names[$m.Value.ToLowerInvariant()] = 1 }
        if ($r -lt $chunk.Length) { break }
        $pos += $r - 64; $fs.Position = $pos
    }
    $fs.Close()
    foreach ($k in ($hits.Keys | Sort-Object)) { Say "  '$k': $($hits[$k].Count)+ hits"; foreach ($h in $hits[$k]) { Say "     $h" } }
    if ($names.Count) { Say "  t34-like identifiers ($($names.Count)): $(($names.Keys | Sort-Object | Select-Object -First 80) -join ', ')" }
}
Say ''
Say 'done'
$Writer.Close()
"report: $reportPath"
