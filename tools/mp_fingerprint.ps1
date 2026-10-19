<#
.SYNOPSIS
  Fingerprints the data a Mius-Front install will bring into a MiusPlayer match, so two players can compare
  one short code before pressing READY. MiusPlayer simulates the whole battle on both PCs with each PC's own
  data and never checks that the data matches; a mismatch gives silently different battles.

  Covers: game build (starter_x64.exe), MiusPlayer's five files, every registered add-on (paths.cfgpack order)
  with its descriptor version and the SHA-256 of each shared\packed_data\*.flatdata it holds.

.EXAMPLE
  .\mp_fingerprint.ps1                       # uses GTMF_ROOT
  .\mp_fingerprint.ps1 -GameRoot "D:\Games\Graviteam Tactics Mius-Front" -Detail
  Compare the CODE line with the other player's. -Detail lists per-add-on codes so you can see which one differs.
#>
param(
    [string]$GameRoot = $env:GTMF_ROOT,
    [switch]$Detail
)
$ErrorActionPreference = 'Stop'
if (-not $GameRoot -or -not (Test-Path (Join-Path $GameRoot 'starter_x64.exe'))) { throw 'GameRoot (or GTMF_ROOT) must point at the folder containing starter_x64.exe' }
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
function Sha([string]$p) { if (Test-Path $p) { (Get-FileHash $p -Algorithm SHA256).Hash } else { 'MISSING' } }
function Short([string]$text) { ([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::ASCII.GetBytes($text))) -replace '-', '').Substring(0, 6) }

$lines = New-Object Collections.Generic.List[string]
$lines.Add('game starter_x64.exe ' + (Sha (Join-Path $GameRoot 'starter_x64.exe')))
foreach ($f in 'bin\rel\x64\basic_network.codelib', 'root\programs\opgame.progpack', 'root\programs\tacgame.progpack', 'steam_appid.txt', 'mp_join.exe') {
    $lines.Add("miusplayer $f " + (Sha (Join-Path $GameRoot $f)))
}

# registered add-ons, in registry order (first wins on a same-name entry)
$reg = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $gt3 azcf (Join-Path $GameRoot 'data\common\shared\config\paths.cfgpack') |
    Where-Object { $_ -match '^\s+(\S+)\s*\|' } | ForEach-Object { $Matches[1] })
$perAddon = @()
foreach ($r in $reg) {
    $dir = Join-Path $GameRoot "data\common\$r"
    $desc = Join-Path $dir 'desc.addpack'
    $ver = ''; $dname = ''
    if (Test-Path $desc) {
        $d = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $gt3 azcf $desc) -join "`n"
        if ($d -match 'version\s*=\s*u:(\d+)') { $ver = $Matches[1] }
        if ($d -match '(?m)^[ \t]*desc[ \t]*=[ \t]*([^\r\n]+)') { $dname = $Matches[1].Trim() }
    }
    $arcs = @(Get-ChildItem (Join-Path $dir 'shared\packed_data') -Filter *.flatdata -ErrorAction SilentlyContinue | Sort-Object Name)
    $sub = New-Object Collections.Generic.List[string]
    foreach ($a in $arcs) { $sub.Add("$($a.Name) " + (Sha $a.FullName)) }
    $code = Short (($sub -join "`n"))
    $perAddon += [pscustomobject]@{ addon = $r; name = $dname; version = $ver; archives = $arcs.Count; code = $code }
    $lines.Add("addon $r v$ver $code")
    foreach ($s in $sub) { $lines.Add("  $s") }
}

$all = Short (($lines -join "`n"))
"CODE $all   (game build + MiusPlayer + $($reg.Count) registered add-ons)"
if ($Detail) {
    ''
    $perAddon | Format-Table -AutoSize addon, version, archives, code, name | Out-String
    $lines | Select-Object -First 6
}
'Compare CODE with the other player. Different? run both with -Detail and compare the per-add-on codes.'
