<#
.SYNOPSIS
  In-place edit of fourcc / u32 cells in an AZCF table node (same-size edit, no offsets move).

.EXAMPLE
  azcf_setcell.ps1 -Path common_res_mod.config.loc_def.bin -Node shells -Col 26 -Set GREN -WhereCol 2 -WhereIs SMK -WhereColB 26 -WhereInB LHE,MORT
    every row whose c2 == SMK and c26 in (LHE, MORT) gets c26 = GREN
  azcf_setcell.ps1 -Path x.bin -Node shells -Col 26 -Set GREN -Rows ND_39,RDG
    named rows (matched on c0) get c26 = GREN
  Add -DryRun to list the rows that would change.
#>
param(
    [Parameter(Mandatory)][string]$Path,
    [Parameter(Mandatory)][string]$Node,
    [Parameter(Mandatory)][int]$Col,
    [Parameter(Mandatory)][string]$Set,
    [string[]]$Rows,
    [int]$WhereCol = -1, [string]$WhereIs,
    [int]$WhereColB = -1, [string[]]$WhereInB,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
# When run via `powershell -File`, "A,B" arrives as one string; split so both call styles work.
if ($Rows) { $Rows = @($Rows | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
if ($WhereInB) { $WhereInB = @($WhereInB | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
$b = [IO.File]::ReadAllBytes($Path)
if ([Text.Encoding]::ASCII.GetString($b, 0, 4) -ne 'AZCF') { throw "$Path is not AZCF" }
$count = [BitConverter]::ToUInt32($b, 4); $table = [BitConverter]::ToUInt32($b, 8)
function CStr([int]$off) { $e = [Array]::IndexOf($b, [byte]0, $off); [Text.Encoding]::GetEncoding(1251).GetString($b, $off, $e - $off) }
function Fourcc([uint32]$v) { $s = ''; for ($i = 0; $i -lt 4; $i++) { $c = ($v -shr (8 * $i)) -band 0xff; if ($c -eq 0) { break }; $s += [char]$c }; $s }
function ToFourcc([string]$s) { if ($s -match '^\d+$') { return [uint32]$s }; if ($s.Length -gt 4) { throw "fourcc '$s' longer than 4" }; $v = [uint32]0; for ($i = 0; $i -lt $s.Length; $i++) { $v = $v -bor ([uint32][byte][char]$s[$i] -shl (8 * $i)) }; $v }
function CellText([int]$off) {
    $kind = [BitConverter]::ToUInt32($b, $off + 16); $s0 = [BitConverter]::ToUInt32($b, $off)
    switch ($kind) { 2 { $p = [BitConverter]::ToUInt32($b, $off + 4); if ($p) { CStr $p } else { '' } } 4 { Fourcc $s0 } default { [string]$s0 } }
}
# PowerShell variable names are case-insensitive: never reuse $Node / $Rows / $Col for locals.
$nodeOff = -1
for ($i = 0; $i -lt $count; $i++) { $o = $table + $i * 0x80; if ((CStr $o) -eq $Node) { $nodeOff = $o; break } }
if ($nodeOff -lt 0) { throw "node '$Node' not found" }
$type = [BitConverter]::ToUInt32($b, $nodeOff + 0x20); $cols = [BitConverter]::ToUInt32($b, $nodeOff + 0x24); $nrows = [BitConverter]::ToUInt32($b, $nodeOff + 0x28); $data = [BitConverter]::ToUInt32($b, $nodeOff + 0x30)
if ($type -ne 2) { throw "node '$Node' is not a table" }
if ($Col -ge $cols) { throw "col $Col out of range (cols=$cols)" }
$newVal = if ($Set -match '^[A-Za-z0-9]{1,4}$') { ToFourcc $Set } else { [uint32]0 }
$changed = 0
for ($r = 0; $r -lt $nrows; $r++) {
    $ro = $data + $r * 0x20 * $cols
    $key = CellText $ro
    $hit = $false
    if ($Rows) { $hit = $Rows -contains $key }
    else {
        $hit = $true
        if ($WhereCol -ge 0) { $hit = $hit -and ((CellText ($ro + $WhereCol * 0x20)) -eq $WhereIs) }
        if ($WhereColB -ge 0) { $hit = $hit -and ($WhereInB -contains (CellText ($ro + $WhereColB * 0x20))) }
    }
    if (-not $hit) { continue }
    $co = $ro + $Col * 0x20
    $kind = [BitConverter]::ToUInt32($b, $co + 16)
    switch ($kind) {
        4 {
            $old = CellText $co
            "{0,-22} c{1}: {2} -> {3}" -f $key, $Col, $old, $Set
            if (-not $DryRun) { [Array]::Copy([BitConverter]::GetBytes($newVal), 0, $b, $co, 4) }
        }
        { $_ -eq 1 -or $_ -eq 0 } {
            # float (kind 0) or float vector (kind 1): -Set "15;250;0.2" writes slots 0..n, zeroes the rest
            $parts = @($Set -split ';' | ForEach-Object { [single]::Parse($_.Trim(), [Globalization.CultureInfo]::InvariantCulture) })
            if ($parts.Count -gt 4) { throw "vector '$Set' has more than 4 components" }
            $old = (0..3 | ForEach-Object { [BitConverter]::ToSingle($b, $co + $_ * 4).ToString('R', [Globalization.CultureInfo]::InvariantCulture) }) -join ';'
            "{0,-22} c{1}: {2} -> {3}" -f $key, $Col, $old, $Set
            if (-not $DryRun) { for ($j = 0; $j -lt 4; $j++) { $val = if ($j -lt $parts.Count) { $parts[$j] } else { [single]0 }; [Array]::Copy([BitConverter]::GetBytes($val), 0, $b, $co + $j * 4, 4) } }
        }
        6 {
            # int vector (kind 6), e.g. ARGB colours: -Set "-2146430960;3158064" writes slots 0..n, zeroes the rest
            $parts = @($Set -split ';' | ForEach-Object { [int]::Parse($_.Trim(), [Globalization.CultureInfo]::InvariantCulture) })
            if ($parts.Count -gt 4) { throw "vector '$Set' has more than 4 components" }
            $old = (0..3 | ForEach-Object { [BitConverter]::ToInt32($b, $co + $_ * 4) }) -join ';'
            "{0,-22} c{1}: {2} -> {3}" -f $key, $Col, $old, $Set
            if (-not $DryRun) { for ($j = 0; $j -lt 4; $j++) { $val = if ($j -lt $parts.Count) { $parts[$j] } else { [int]0 }; [Array]::Copy([BitConverter]::GetBytes($val), 0, $b, $co + $j * 4, 4) } }
        }
        2 {
            # string cell: only a same-length or shorter replacement, written in place over the existing NUL-terminated string
            $p = [BitConverter]::ToUInt32($b, $co + 4)
            $old = if ($p) { CStr $p } else { '' }
            if ($Set.Length -gt $old.Length) { throw "row $key col ${Col}: '$Set' is longer than '$old'; in-place string edits cannot grow" }
            "{0,-22} c{1}: {2} -> {3}" -f $key, $Col, $old, $Set
            if (-not $DryRun) { $nb = [Text.Encoding]::GetEncoding(1251).GetBytes($Set); [Array]::Copy($nb, 0, $b, $p, $nb.Length); for ($j = $nb.Length; $j -le $old.Length; $j++) { $b[$p + $j] = 0 }; [Array]::Copy([BitConverter]::GetBytes([uint32]$nb.Length), 0, $b, $co, 4) }
        }
        5 {
            # bool: -Set 0 or 1
            $nv = if ($Set -in @('1', 'true', 'True')) { [uint32]1 } else { [uint32]0 }
            $old = [BitConverter]::ToUInt32($b, $co)
            "{0,-22} c{1}: {2} -> {3}" -f $key, $Col, $old, $nv
            if (-not $DryRun) { [Array]::Copy([BitConverter]::GetBytes($nv), 0, $b, $co, 4) }
        }
        default { throw "row $key col $Col is kind $kind; supported: u32/fourcc (4), float (0), float vector (1), int vector (6), bool (5), string (2, same length or shorter)" }
    }
    $changed++
}
if (-not $DryRun) { [IO.File]::WriteAllBytes($Path, $b) }
"$changed row(s) $(if ($DryRun) { 'would change' } else { 'changed' }) in $Path"
