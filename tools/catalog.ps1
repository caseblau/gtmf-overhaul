param(
    [Parameter(Mandatory = $true)][string]$GameRoot,
    [string]$Out = (Join-Path $PSScriptRoot '..\docs\archive_catalog.txt')
)
# Lists every entry (name, kind, loc, size) of every .flatdata under the game root without reading entry bodies.
$lines = @("# Entry catalog of all .flatdata archives under $GameRoot", "# generated $(Get-Date -Format s) by tools\catalog.ps1", "")
foreach ($f in Get-ChildItem $GameRoot -Recurse -Filter *.flatdata | Sort-Object FullName) {
    $fs = [IO.File]::OpenRead($f.FullName); $br = New-Object IO.BinaryReader($fs)
    $magic = [Text.Encoding]::ASCII.GetString($br.ReadBytes(4))
    if ($magic -ne 'AZP3') { $lines += "## $($f.FullName.Substring($GameRoot.Length+1))  (not AZP3: $magic)"; $br.Close(); continue }
    $cnt = $br.ReadUInt32(); $bk = $br.ReadUInt32(); $tbl = 0x40 + $bk * 8
    $lines += ("## {0}  ({1} entries, {2} buckets, {3:N0} bytes)" -f $f.FullName.Substring($GameRoot.Length + 1), $cnt, $bk, $f.Length)
    for ($i = 0; $i -lt $cnt; $i++) {
        $fs.Position = $tbl + $i * 0x80; $raw = $br.ReadBytes(0x80)
        $size = [BitConverter]::ToUInt64($raw, 16)
        $name = [Text.Encoding]::ASCII.GetString($raw, 0x20, 0x20).Split([char]0)[0]
        $kind = [Text.Encoding]::ASCII.GetString($raw, 0x40, 0x20).Split([char]0)[0]
        $loc = [Text.Encoding]::ASCII.GetString($raw, 0x60, 0x20).Split([char]0)[0]
        $lines += ("    {0,-34} {1,-12} {2,-8} {3,12:N0}" -f $name, $kind, $loc, $size)
    }
    $lines += ""
    $br.Close()
}
[IO.File]::WriteAllLines($Out, $lines, [Text.Encoding]::UTF8)
"wrote $Out ($($lines.Count) lines)"
