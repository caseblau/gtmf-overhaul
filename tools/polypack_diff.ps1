# Compare the backed-up original cell with the repacked round-trip and print the first differing regions.
param([string]$GameRoot = $env:GTMF_ROOT, [string]$Cell = 'MgG3')
if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$a = [IO.File]::ReadAllBytes((Join-Path $GameRoot "users\modwork\_orig\polygons\6m_mius\${Cell}_Mius.polypack2"))
$b = [IO.File]::ReadAllBytes((Join-Path $repo "build\m12_test\${Cell}_roundtrip.polypack2"))
$out = New-Object Collections.Generic.List[string]
$out.Add("sizes $($a.Length) $($b.Length)")
$n = [Math]::Min($a.Length, $b.Length); $diffs = 0; $i = 0
while ($i -lt $n -and $diffs -lt 40) {
    if ($a[$i] -ne $b[$i]) {
        $s = [Math]::Max(0, $i - 8); $e = [Math]::Min($n - 1, $i + 23)
        $ha = ($a[$s..$e] | ForEach-Object { '{0:x2}' -f $_ }) -join ' '
        $hb = ($b[$s..$e] | ForEach-Object { '{0:x2}' -f $_ }) -join ' '
        $out.Add(('0x{0:x8}  orig {1}' -f $s, $ha)); $out.Add(('            new  {0}' -f $hb))
        $diffs++; $i = $e + 1
    } else { $i++ }
}
$total = 0; for ($j = 0; $j -lt $n; $j++) { if ($a[$j] -ne $b[$j]) { $total++ } }
$out.Add("total differing bytes: $total")
$out | Set-Content (Join-Path $repo 'build\m12_test\roundtrip_diff.txt')
$out
