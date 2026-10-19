<#
.SYNOPSIS
  Divergence report for a MiusPlayer two-copy battle, from the files MiusPlayer itself writes into <game>\out:
    mp_units_<pid>_<sim ms>.txt   (MP_DUMP=1)  unit name + position at sim 10 ms, 1 s, 5 s, 20 s
    mp_trace_tacgame_<pid>.txt    (MP_DEBUG=1) one line per simulated second: unit count + FNV hash of all positions
    basic_network_tacgame_<pid>.log            "state:" lines with "not loaded" counts and "clock:" drift
  No game process is touched. Our own replacement for MiusPlayer's compare_units.py / compare_traces.py.
.EXAMPLE
  .\mp_compare.ps1 -GameRoot $env:GTMF_ROOT
#>
param([string]$GameRoot = $env:GTMF_ROOT, [double]$FarMeters = 5)
$out = Join-Path $GameRoot 'out'

"== unit position dumps (MP_DUMP)"
$dumps = Get-ChildItem $out -Filter 'mp_units_*.txt' | Where-Object { $_.Name -match 'mp_units_(\d+)_(\d+)\.txt' } |
    ForEach-Object { [pscustomobject]@{ pid = [int]$Matches[1]; sim = [int]$Matches[2]; file = $_.FullName } }
foreach ($sim in ($dumps.sim | Sort-Object -Unique)) {
    $set = @($dumps | Where-Object sim -eq $sim | Sort-Object pid)
    if ($set.Count -lt 2) { "  sim $sim ms: only one instance dumped"; continue }
    $a = @{}; foreach ($l in Get-Content $set[0].file) { $p = $l.Split(' '); $a[$p[0]] = [double[]]($p[1..3]) }
    $b = @{}; foreach ($l in Get-Content $set[1].file) { $p = $l.Split(' '); $b[$p[0]] = [double[]]($p[1..3]) }
    $common = @($a.Keys | Where-Object { $b.ContainsKey($_) })
    $diffs = @()
    foreach ($n in $common) { $d = [Math]::Sqrt(($a[$n][0]-$b[$n][0])*($a[$n][0]-$b[$n][0]) + ($a[$n][1]-$b[$n][1])*($a[$n][1]-$b[$n][1]) + ($a[$n][2]-$b[$n][2])*($a[$n][2]-$b[$n][2])); if ($d -gt 0) { $diffs += [pscustomobject]@{ name = $n; d = $d } } }
    $far = @($diffs | Where-Object d -gt $FarMeters)
    $max = if ($diffs) { ($diffs | Measure-Object d -Maximum).Maximum } else { 0 }
    "  sim {0,6} ms: {1} units in A ({2}), {3} in B ({4}), {5} common, {6} differ, {7} further than {8} m, largest {9:N3} m" -f $sim, $a.Count, $set[0].pid, $b.Count, $set[1].pid, $common.Count, $diffs.Count, $far.Count, $FarMeters, $max
    foreach ($x in ($diffs | Sort-Object d -Descending | Select-Object -First 3)) { "       {0,-28} {1,9:N3} m" -f $x.name, $x.d }
}

"== per-second traces (MP_DEBUG)"
$traces = @(Get-ChildItem $out -Filter 'mp_trace_tacgame_*.txt' | Where-Object Length -gt 0 | Sort-Object Name)
$runs = @()
foreach ($t in $traces) {
    $rows = @{}
    foreach ($l in Get-Content $t.FullName) { $m = @{}; foreach ($kv in $l.Split(' ')) { $k, $v = $kv.Split('=', 2); $m[$k] = $v }; if ($m.hash) { $rows[[int]([long]$m.sim / 1000)] = $m } }
    $runs += [pscustomobject]@{ name = $t.Name; rows = $rows }
    "  {0}: {1} seconds traced" -f $t.Name, $rows.Count
}
if ($runs.Count -ge 2) {
    $common = @($runs[0].rows.Keys | Where-Object { $runs[1].rows.ContainsKey($_) } | Sort-Object)
    $same = 0; $firstDiff = $null; $unitMismatch = 0
    foreach ($s in $common) {
        $r0 = $runs[0].rows[$s]; $r1 = $runs[1].rows[$s]
        if ($r0.units -ne $r1.units) { $unitMismatch++ }
        if ($r0.hash -eq $r1.hash) { $same++ } elseif ($null -eq $firstDiff) { $firstDiff = $s }
    }
    "  common seconds: {0}; identical position hashes: {1}; first differing second: {2}; seconds with different unit counts: {3}" -f $common.Count, $same, ($(if ($null -ne $firstDiff) { $firstDiff } else { 'none' })), $unitMismatch
    foreach ($s in @($common | Select-Object -First 2) + @($common | Select-Object -Last 2)) { "    s{0,5}: A units={1} hash={2}  B units={3} hash={4}" -f $s, $runs[0].rows[$s].units, $runs[0].rows[$s].hash.Substring(8), $runs[1].rows[$s].units, $runs[1].rows[$s].hash.Substring(8) }
}

"== MiusPlayer state/clock log lines"
foreach ($l in Get-ChildItem $out -Filter 'basic_network_tacgame_*.log' | Where-Object Length -gt 5000) {
    $lines = Get-Content $l.FullName
    $state = @($lines | Select-String -Pattern 'state: 5 s:')
    $notLoaded = @($state | ForEach-Object { if ($_.Line -match '(\d+) not loaded') { [int]$Matches[1] } }) | Measure-Object -Sum -Maximum
    $clock = @($lines | Select-String -Pattern 'clock: battle time')
    $drift = @($clock | ForEach-Object { if ($_.Line -match 'time (?:here )?([\d.]+) s, (?:in the other game|on the host) ([\d.]+) s') { [Math]::Abs([double]$Matches[1] - [double]$Matches[2]) } }) | Measure-Object -Maximum -Average
    $last = ($clock | Select-Object -Last 1).Line
    "  {0}: {1} state reports, not-loaded total {2} (max {3}); clock drift max {4:N2} s avg {5:N2} s; last: {6}" -f $l.Name, $state.Count, $notLoaded.Sum, $notLoaded.Maximum, $drift.Maximum, $drift.Average, ($(if ($last) { $last.Substring(13) } else { '' }))
    $lines | Select-String -Pattern 'rejected [1-9]|crash|error|disconnect|lost' | Select-Object -First 5 | ForEach-Object { "    ! " + $_.Line }
}
