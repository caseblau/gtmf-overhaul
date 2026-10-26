<#
.SYNOPSIS
  M10 probe 3: Graviteam Tactics: Operation Star. Which of its packs open with gt3.ps1, which T-34 variants it has
  (looking for a T-34-85), and samples of its mesh / texture / armor entries next to Mius-Front's for format comparison.
  Writes docs\m10_t3485\probe3_report.txt and docs\m10_t3485\gtos_samples\. Read-only on both games.
#>
param(
    [string]$GtosRoot = '',
    [string]$GameRoot = $env:GTMF_ROOT
)
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
. $gt3 lib
$outDir = Join-Path $repo 'docs\m10_t3485'
$samples = Join-Path $outDir 'gtos_samples'
New-Item -ItemType Directory -Force $outDir, $samples | Out-Null
$reportPath = Join-Path $outDir 'probe3_report.txt'
$Writer = New-Object IO.StreamWriter($reportPath, $false, (New-Object Text.UTF8Encoding $true)); $Writer.AutoFlush = $true
function Say([string]$s) { $s; $Writer.WriteLine($s) }
trap { Say "!! ERROR: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"; continue }
function Hex([byte[]]$b, [int]$off, [int]$n) { (($b[$off..($off + $n - 1)] | ForEach-Object { '{0:x2}' -f $_ }) -join ' ') }
function Asc([byte[]]$b, [int]$off, [int]$n) { ([Text.Encoding]::ASCII.GetString($b, $off, $n) -replace '[^\x20-\x7e]', '.') }
function Dump-Head([byte[]]$b, [int]$n) { for ($o = 0; $o -lt [Math]::Min($b.Length, $n); $o += 32) { $len = [Math]::Min(32, $b.Length - $o); Say ("    {0:x4}  {1,-96} {2}" -f $o, (Hex $b $o $len), (Asc $b $o $len)) } }
function Save-Entry($pack, $e, [string]$dir) {
    New-Item -ItemType Directory -Force $dir | Out-Null
    $blob = New-Object byte[] $e.size; [Array]::Copy($pack.bytes, [int64]$e.offset, $blob, 0, [int64]$e.size)
    $file = Join-Path $dir ('{0}.{1}.{2}.bin' -f $e.name, $e.kind, $e.loc)
    [IO.File]::WriteAllBytes($file, $blob); $file
}

if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
function Find-SteamLibraries {
    $libs = @()
    foreach ($steam in @('C:\Program Files (x86)\Steam', 'C:\Program Files\Steam')) {
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path $vdf) { $libs += $steam; foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) { $libs += $m.Groups[1].Value.Replace('\\', '\') } }
    }
    $libs | Select-Object -Unique
}
if (-not $GtosRoot) {
    foreach ($lib in Find-SteamLibraries) {
        $common = Join-Path $lib 'steamapps\common'
        if (-not (Test-Path $common)) { continue }
        $cand = Get-ChildItem $common -Directory | Where-Object { $_.Name -match 'Operation Star' } | Select-Object -First 1
        if ($cand) { $GtosRoot = $cand.FullName; break }
    }
}
Say "# M10 probe 3  $(Get-Date -Format s)"
Say "GtosRoot = $(if ($GtosRoot) { $GtosRoot } else { '(not found: pass -GtosRoot <folder>)' })"
Say "GameRoot = $GameRoot"
if (-not ($GtosRoot -and (Test-Path $GtosRoot))) { $Writer.Close(); exit 1 }

Say ''
Say '## top level'
foreach ($e in (Get-ChildItem $GtosRoot | Sort-Object { -not $_.PSIsContainer }, Name)) { if ($e.PSIsContainer) { Say "  [dir] $($e.Name)" } else { Say ("  {0,13:n0}  {1}" -f $e.Length, $e.Name) } }
$dataDirs = Get-ChildItem (Join-Path $GtosRoot 'data') -Directory -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
Say "data\ folders: $($dataDirs -join ', ')"

# ---------- every pack ----------
Say ''
Say '## packs'
$packs = Get-ChildItem $GtosRoot -Recurse -File -Filter *.flatdata | Sort-Object FullName
$t34 = @(); $meshPack = $null; $meshEntry = $null; $tabsHits = @()
foreach ($pf in $packs) {
    $rel = $pf.FullName.Substring($GtosRoot.Length + 1)
    try {
        $p = Read-Azp3 $pf.FullName
        $kinds = @{}; foreach ($e in $p.entries) { if ($kinds.ContainsKey($e.kind)) { $kinds[$e.kind]++ } else { $kinds[$e.kind] = 1 } }
        $ks = ($kinds.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ', '
        Say ("- {0}  ({1:n0} bytes) sig '{2}': {3} entries: {4}" -f $rel, $pf.Length, $p.sig, $p.count, $ks)
        foreach ($e in $p.entries) {
            if ($e.name -match 't[-_]?34' -or $e.name -match '85') { $t34 += [pscustomobject]@{ archive = $rel; name = $e.name; kind = $e.kind; loc = $e.loc; size = $e.size } }
            if ($e.name -match 't[-_]?34.*(85|m44|_44|1944)' -or $e.name -match 't3485') {
                $f = Save-Entry $p $e (Join-Path $samples ($rel -replace '[\\/:]', '_'))
                Say "    saved $f"
            }
            if ($e.kind -eq 'config' -and $e.name -in 'techn_base', 'ui_params', 'div_units_ussr', 'common_res_mod') { $tabsHits += [pscustomobject]@{ pack = $p; entry = $e; archive = $rel } }
            if ($e.kind -eq 'text') { $tabsHits += [pscustomobject]@{ pack = $p; entry = $e; archive = $rel } }
            if (-not $meshEntry -and $e.kind -eq 'mesh' -and $e.name -match '^t34') { $meshPack = $p; $meshEntry = $e }
        }
    } catch { Say ("- {0}  ({1:n0} bytes): NOT READABLE: {2}" -f $rel, $pf.Length, $_.Exception.Message) }
}

Say ''
Say "## entries named like t34 / 85 ($($t34.Count))"
foreach ($e in ($t34 | Sort-Object name, archive)) { Say ("  {0,-34} {1,-8} {2,-8} {3,10:n0}  {4}" -f $e.name, $e.kind, $e.loc, $e.size, $e.archive) }

# ---------- config and text: vehicle nodes and names ----------
Say ''
Say '## techn_base vehicle nodes mentioning t34 (and 85 mm)'
foreach ($h in ($tabsHits | Where-Object { $_.entry.kind -eq 'config' })) {
    $f = Save-Entry $h.pack $h.entry (Join-Path $samples 'tabs')
    Say "  $($h.archive): $($h.entry.name) -> $f"
    if ($h.entry.name -eq 'techn_base') {
        $c = Read-Azcf ([IO.File]::ReadAllBytes($f))
        for ($i = 0; $i -lt $c.count; $i++) { $n = $c.nodes[$i]; if ($n.name -match 't[-_]?34' -or $n.name -match '85') { Say ("    [{0}] {1}  type={2} rows={3}" -f $i, $n.name, $n.type, $n.rows) } }
        $txt = [Text.Encoding]::GetEncoding(1251).GetString([IO.File]::ReadAllBytes($f))
        foreach ($nd in @('zis_s53', 'zis-s-53', 's53', 'd5t', 'd-5t', '85', 'br_365', 'o_365')) { $k = 0; $ix = $txt.IndexOf($nd, [StringComparison]::OrdinalIgnoreCase); while ($ix -ge 0 -and $k -lt 6) { $a = [Math]::Max(0, $ix - 20); Say ("    '{0}' @0x{1:x}: {2}" -f $nd, $ix, ($txt.Substring($a, [Math]::Min(60, $txt.Length - $a)) -replace '[^\x20-\x7e]', '.')); $k++; $ix = $txt.IndexOf($nd, $ix + 1, [StringComparison]::OrdinalIgnoreCase) } }
    }
}
Say ''
Say '## text entries mentioning T-34-85'
foreach ($h in ($tabsHits | Where-Object { $_.entry.kind -eq 'text' })) {
    $blob = New-Object byte[] $h.entry.size; [Array]::Copy($h.pack.bytes, [int64]$h.entry.offset, $blob, 0, [int64]$h.entry.size)
    $txt = [Text.Encoding]::GetEncoding(1251).GetString($blob)
    $k = 0; $ix = $txt.IndexOf('34-85'); while ($ix -ge 0 -and $k -lt 8) { $a = [Math]::Max(0, $ix - 40); Say ("  {0}/{1} ({2}): {3}" -f $h.archive, $h.entry.name, $h.entry.loc, ($txt.Substring($a, [Math]::Min(100, $txt.Length - $a)) -replace '[^\x20-\x7e]', '.')); $k++; $ix = $txt.IndexOf('34-85', $ix + 1) }
}

# ---------- mesh format comparison ----------
Say ''
Say '## mesh headers: Operation Star vs Mius-Front'
if ($meshEntry) {
    $f = Save-Entry $meshPack $meshEntry (Join-Path $samples 'mesh_compare')
    $b = [IO.File]::ReadAllBytes($f)
    Say "  GTOS $($meshEntry.name) ($($meshEntry.size) bytes) from $($meshPack.path)"
    Dump-Head $b 192
}
$mfPack = Join-Path $GameRoot 'data\common\shared\packed_data\gos_techn_01.flatdata'
if (Test-Path $mfPack) {
    $p = Read-Azp3 $mfPack
    $e = $p.entries | Where-Object { $_.name -eq 't34_42_utz' } | Select-Object -First 1
    if ($e) { $f = Save-Entry $p $e (Join-Path $samples 'mesh_compare'); $b = [IO.File]::ReadAllBytes($f); Say "  MF t34_42_utz ($($e.size) bytes)"; Dump-Head $b 192 }
    foreach ($nm in 't34utz_wheel_va') { $e = $p.entries | Where-Object { $_.name -eq $nm } | Select-Object -First 1; if ($e) { $f = Save-Entry $p $e (Join-Path $samples 'mesh_compare'); Say "  saved MF $nm" } }
}
$mfTex = Join-Path $GameRoot 'data\common\shared\packed_data\tex_techn_01.flatdata'
if (Test-Path $mfTex) {
    $p = Read-Azp3 $mfTex
    foreach ($nm in 'reg_t34_42_utz_dift', 'bump_t34_42_utz_norsp') { $e = $p.entries | Where-Object { $_.name -eq $nm } | Select-Object -First 1; if ($e) { $f = Save-Entry $p $e (Join-Path $samples 'mesh_compare'); $b = [IO.File]::ReadAllBytes($f); Say "  MF texture $nm ($($e.size) bytes)"; Dump-Head $b 64 } }
}
$mfArm = Get-ChildItem (Join-Path $GameRoot 'data\common\shared\packed_data') -Filter '*.flatdata' | ForEach-Object { try { $q = Read-Azp3 $_.FullName; $a = $q.entries | Where-Object { $_.name -eq 'arm_t34_42_utz_dift' } | Select-Object -First 1; if ($a) { [pscustomobject]@{ pack = $q; entry = $a } } } catch {} } | Select-Object -First 1
if ($mfArm) { $f = Save-Entry $mfArm.pack $mfArm.entry (Join-Path $samples 'mesh_compare'); $b = [IO.File]::ReadAllBytes($f); Say "  MF armor arm_t34_42_utz_dift ($($mfArm.entry.size) bytes) from $($mfArm.pack.path)"; Dump-Head $b 96 }

Say ''
Say 'done'
$Writer.Close()
"report: $reportPath"
