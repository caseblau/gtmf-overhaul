<#
.SYNOPSIS
  Copies a few named entries (textures / meshes) out of the game's packs into a folder OUTSIDE the repository, for the
  offline previews of tools\m13 (the repo is public: game data must never be committed).
.EXAMPLE
  powershell -File extract_refs.ps1 -Out "$env:USERPROFILE\Downloads\m3c\gameref"
#>
param(
    [string]$GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front',
    [string]$Out = (Join-Path $env:USERPROFILE 'Downloads\m3c\gameref'),
    [string[]]$Packs = @('tex_techn_01', 'tex_techn'),
    [string[]]$Names = @('reg_m4a2_sherman_dift', 'reg_m4_wheels_dift', 'reg_m34_dift', 'reg_m4_turret_dift', 'reg_m3a1_stuart_dift', 'reg_m4tr_dift', 'reg_m4a2_ostov_dift')
)
$ErrorActionPreference = 'Stop'
$Names = @($Names | ForEach-Object { $_ -split ',' } | Where-Object { $_ }); $Packs = @($Packs | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
if ($Out.StartsWith((Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path, [StringComparison]::OrdinalIgnoreCase)) { throw "-Out must be outside the repository (game data must not be committed)" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$enc = [Text.Encoding]::GetEncoding(1251)
$found = @{}
foreach ($p in $Packs) {
    $path = Join-Path $GameRoot "data\common\shared\packed_data\$p.flatdata"
    if (-not (Test-Path $path)) { "  (no $p.flatdata)"; continue }
    $fs = [IO.File]::OpenRead($path)
    try {
        $h = New-Object byte[] 0x40; [void]$fs.Read($h, 0, 0x40)
        if ($enc.GetString($h, 0, 4) -ne 'AZP3') { throw "$path is not an AZP3 pack" }
        $cnt = [BitConverter]::ToUInt32($h, 4); $bk = [BitConverter]::ToUInt32($h, 8)
        $tbl = New-Object byte[] ($cnt * 0x80); $fs.Position = 0x40 + $bk * 8; [void]$fs.Read($tbl, 0, $tbl.Length)
        for ($i = 0; $i -lt $cnt; $i++) {
            $o = $i * 0x80
            $name = $enc.GetString($tbl, $o + 0x20, 0x20).Split([char]0)[0]
            if ($Names -notcontains $name -or $found.ContainsKey($name)) { continue }
            $kind = $enc.GetString($tbl, $o + 0x40, 0x20).Split([char]0)[0]; $loc = $enc.GetString($tbl, $o + 0x60, 0x20).Split([char]0)[0]
            $off = [BitConverter]::ToUInt64($tbl, $o + 8); $size = [BitConverter]::ToUInt64($tbl, $o + 16)
            $buf = New-Object byte[] $size; $fs.Position = [long]$off; $n = 0
            while ($n -lt $size) { $r = $fs.Read($buf, $n, [int]($size - $n)); if ($r -le 0) { throw 'short read' }; $n += $r }
            $dst = Join-Path $Out "$name.$kind.$loc.bin"; [IO.File]::WriteAllBytes($dst, $buf); $found[$name] = $dst
            "  $p : $name ($size bytes) -> $dst"
        }
    } finally { $fs.Close() }
}
$missing = $Names | Where-Object { -not $found.ContainsKey($_) }
if ($missing) { "not found: $($missing -join ', ')" }
"done: $($found.Count) of $($Names.Count) entries in $Out"
