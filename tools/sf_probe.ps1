<#
.SYNOPSIS
  M10 probe: can Steel Fury - Kharkov 1942 assets (T-34-85) be read with our tools, and what does a Mius-Front vehicle
  consist of? Writes docs\m10_t3485\probe_report.txt and a few listings next to it. Read-only: touches no game file.

.DESCRIPTION
  Part A  Steel Fury: finds the install (-SfRoot, else Steam library folders), lists every *.flatdata with its magic
          bytes, tries gt3.ps1 list on each (AZP3 or not), counts entry kinds, and reports every entry or loose file
          whose name mentions t34 / 85. Also counts loose-file extensions under data\ so we see what is packed and what
          is not (Steel Fury keeps .engcfg text configs loose).
  Part B  Mius-Front reference: entries of the T-34 (1942, UTZ) in gos_techn*/tex_techn* (mesh, texture, armor), and
          every config table under users\modwork\_orig\3598 whose bytes contain 't34_42_utz' or 'arm_t34', with the
          matching rows exported through gt3.ps1 csv. That is the list of things a new vehicle must provide.

.EXAMPLE
  tools\sf_probe.ps1                                  # auto-detect both games
  tools\sf_probe.ps1 -SfRoot "D:\Games\Steel Fury - Kharkov 1942"
#>
param(
    [string]$SfRoot = '',
    [string]$GameRoot = $env:GTMF_ROOT,
    [string]$VehicleId = 't34_42_utz'
)
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
$outDir = Join-Path $repo 'docs\m10_t3485'
New-Item -ItemType Directory -Force $outDir | Out-Null
$reportPath = Join-Path $outDir 'probe_report.txt'
$Collected = New-Object Collections.Generic.List[string]
function Say([string]$s) { $s; $Collected.Add($s) }

if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
Say "# M10 probe  $(Get-Date -Format s)"
Say "GameRoot = $GameRoot"

# ---------- locate Steel Fury ----------
function Find-SteamLibraries {
    $libs = @()
    foreach ($steam in @('C:\Program Files (x86)\Steam', 'C:\Program Files\Steam', "$env:ProgramFiles\Steam")) {
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path $vdf) {
            $libs += $steam
            foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) { $libs += $m.Groups[1].Value.Replace('\\', '\') }
        }
    }
    $libs | Select-Object -Unique
}
if (-not $SfRoot) {
    foreach ($lib in Find-SteamLibraries) {
        foreach ($name in @('Steel Fury - Kharkov 1942', 'Steel Fury Kharkov 1942', 'Steel Fury')) {
            $p = Join-Path $lib "steamapps\common\$name"
            if (Test-Path $p) { $SfRoot = $p; break }
        }
        if ($SfRoot) { break }
    }
}
Say "SfRoot   = $(if ($SfRoot) { $SfRoot } else { '(not found: pass -SfRoot <folder>)' })"
Say ''

# ---------- Part A: Steel Fury ----------
Say '## A. Steel Fury - Kharkov 1942'
if ($SfRoot -and (Test-Path $SfRoot)) {
    $exe = Get-ChildItem $SfRoot -Filter *.exe -File | Select-Object -ExpandProperty Name
    Say "exe: $($exe -join ', ')"
    $top = Get-ChildItem $SfRoot -Directory | Select-Object -ExpandProperty Name
    Say "top-level folders: $($top -join ', ')"

    # loose files: extension histogram under data\ (or the whole root when there is no data\)
    $dataDir = if (Test-Path (Join-Path $SfRoot 'data')) { Join-Path $SfRoot 'data' } else { $SfRoot }
    $all = Get-ChildItem $dataDir -Recurse -File -ErrorAction SilentlyContinue
    Say "loose files under $dataDir : $($all.Count)"
    $hist = $all | Group-Object Extension | Sort-Object Count -Descending | Select-Object -First 25
    foreach ($g in $hist) { Say ("  {0,-12} {1,7}   {2,12:n0} bytes" -f $g.Name, $g.Count, ($g.Group | Measure-Object Length -Sum).Sum) }

    # files whose name mentions the T-34 or an 85 mm gun
    $hits = $all | Where-Object { $_.Name -match 't[-_]?34|85' } | Sort-Object FullName
    Say "files named like t34 / 85: $($hits.Count) (full list in sf_files_t34.txt)"
    $hits | ForEach-Object { "{0,12:n0}  {1}" -f $_.Length, $_.FullName.Substring($SfRoot.Length + 1) } | Set-Content (Join-Path $outDir 'sf_files_t34.txt')
    foreach ($h in ($hits | Select-Object -First 40)) { Say ("  {0,12:n0}  {1}" -f $h.Length, $h.FullName.Substring($SfRoot.Length + 1)) }

    # packs: magic + gt3 list
    Say ''
    Say '### packs'
    $packs = Get-ChildItem $SfRoot -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in '.flatdata', '.flatpack', '.pak', '.pack', '.dat' } | Sort-Object FullName
    Say "pack-like files: $($packs.Count)"
    $sfList = New-Object Collections.Generic.List[string]
    foreach ($p in $packs) {
        $fs = [IO.File]::OpenRead($p.FullName); $hdr = New-Object byte[] 64; $n = $fs.Read($hdr, 0, 64); $fs.Close()
        $magic = ([Text.Encoding]::ASCII.GetString($hdr, 0, $n) -replace '[^\x20-\x7e]', '.')
        Say ("- {0}  ({1:n0} bytes)  magic: {2}" -f $p.FullName.Substring($SfRoot.Length + 1), $p.Length, $magic.Substring(0, [Math]::Min(48, $magic.Length)))
        try {
            $lines = @(& $gt3 list $p.FullName 2>&1)
            $sfList.Add("## $($p.FullName)"); $sfList.AddRange([string[]]$lines)
            $kinds = @{}
            $t34 = @()
            foreach ($l in $lines) {
                if ($l -match '^\s*\d+\s+(\S+)\s+(\S+)\s+(\S+)\s+off=') {
                    $k = $Matches[2]; if ($kinds.ContainsKey($k)) { $kinds[$k]++ } else { $kinds[$k] = 1 }
                    if ($Matches[1] -match 't[-_]?34|85') { $t34 += $l.Trim() }
                }
            }
            $ks = ($kinds.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ', '
            Say "    gt3 list OK: $ks"
            foreach ($t in $t34) { Say "    $t" }
        } catch { Say "    gt3 list FAILED: $($_.Exception.Message)" }
    }
    [IO.File]::WriteAllLines((Join-Path $outDir 'sf_pack_listings.txt'), [string[]]$sfList)

    # text configs mentioning the T-34-85
    Say ''
    Say '### .engcfg / text files mentioning t34_85 / t-34-85 (first 60)'
    $cfgs = $all | Where-Object { $_.Extension -in '.engcfg', '.cfg', '.txt', '.ini', '.engdat' -and $_.Length -lt 5MB }
    $k = 0
    foreach ($c in $cfgs) {
        $m = Select-String -Path $c.FullName -Pattern 't34[-_]?85|t-34-85|t_34_85' -SimpleMatch:$false -ErrorAction SilentlyContinue | Select-Object -First 3
        if ($m) { $k++; if ($k -le 60) { Say "  $($c.FullName.Substring($SfRoot.Length + 1))"; foreach ($mm in $m) { Say ("      {0}: {1}" -f $mm.LineNumber, $mm.Line.Trim().Substring(0, [Math]::Min(140, $mm.Line.Trim().Length))) } } }
    }
    Say "text files mentioning the T-34-85: $k"
} else { Say 'Steel Fury not found; Part A skipped.' }

# ---------- Part B: Mius-Front reference vehicle ----------
Say ''
Say "## B. Mius-Front reference: $VehicleId"
if (Test-Path $GameRoot) {
    $pd = Join-Path $GameRoot 'data\common\shared\packed_data'
    foreach ($arch in (Get-ChildItem $pd -Filter '*techn*.flatdata' | Sort-Object Name)) {
        try {
            $lines = @(& $gt3 list $arch.FullName 2>&1)
            $hit = $lines | Where-Object { $_ -match '^\s*\d+\s+\S*t34' }
            if ($hit) { Say "### $($arch.Name)"; foreach ($h in $hit) { Say "  $($h.Trim())" } }
        } catch { Say "  $($arch.Name): gt3 list FAILED: $($_.Exception.Message)" }
    }
    $orig = Join-Path $GameRoot 'users\modwork\_orig\3598'
    Say ''
    Say "### config tables under $orig containing '$VehicleId' / 'arm_t34' / 't34_42'"
    if (Test-Path $orig) {
        $csvDir = Join-Path $outDir 'mf_rows'; New-Item -ItemType Directory -Force $csvDir | Out-Null
        $needles = @($VehicleId, 'arm_t34', 't34_42')
        foreach ($t in (Get-ChildItem $orig -Recurse -Filter '*.config.*.bin' | Sort-Object Name)) {
            $txt = [Text.Encoding]::GetEncoding(1251).GetString([IO.File]::ReadAllBytes($t.FullName))
            $found = @($needles | Where-Object { $txt.IndexOf($_, [StringComparison]::OrdinalIgnoreCase) -ge 0 })
            if (-not $found.Count) { continue }
            Say "- $($t.Name): $($found -join ', ')"
            try {
                $d = Join-Path $csvDir ($t.Name -replace '\.config\..*$', '')
                New-Item -ItemType Directory -Force $d | Out-Null
                & $gt3 csv $t.FullName '*' $d 2>&1 | Out-Null
                foreach ($csv in (Get-ChildItem $d -Filter *.csv)) {
                    $rows = Select-String -Path $csv.FullName -Pattern ($needles -join '|') | Select-Object -First 12
                    if ($rows) { Say "    node $($csv.BaseName): $($rows.Count)+ rows"; foreach ($row in $rows) { Say ("      {0}" -f $row.Line.Substring(0, [Math]::Min(220, $r.Line.Length))) } }
                }
            } catch { Say "    csv export failed: $($_.Exception.Message)" }
        }
    } else { Say "  (no $orig - run tools\build_install_here.cmd once to unpack the vanilla tables)" }
} else { Say "Mius-Front not found at $GameRoot" }

[IO.File]::WriteAllLines($reportPath, [string[]]$Collected, [Text.Encoding]::UTF8)
''
"report: $reportPath"
