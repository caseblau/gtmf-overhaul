<#
.SYNOPSIS
  Mirrors PHA6 heightmaps (hei_map entries) north-south (-Rows, default) or east-west (-Cols) in place, byte-exactly:
  block rows/columns are reversed and the 2-bit sample indices inside every 4x4 block are reordered, so the decoded
  heights are exactly flipped. Used to fix the orientation of generated cells without re-sampling the DEM.
  A marker file <dir>\flipped_<rows|cols>.txt prevents a second run from flipping back.
.EXAMPLE
  pha6_flip.ps1 -Dir ..\build\prokhorovka\cells            # flip all *_hei_map.cell.loc_def.bin rows
  pha6_flip.ps1 -Path x.bin -Cols -Force
#>
param([string]$Dir, [string]$Path, [switch]$Rows, [switch]$Cols, [switch]$Force)
$ErrorActionPreference = 'Stop'
if (-not $Cols) { $Rows = $true }
Add-Type -TypeDefinition @'
public static class Pha6Flip {
    // file: 0x430 header bytes, then 1024 x 1024 blocks of 8 bytes: u16 base, u16 pr, u32 idx (byte y = sample row, bits 2x..2x+1 = sample column)
    public static void FlipRows(byte[] b) {
        const int H = 0x430, N = 1024, BS = 8;
        byte[] tmp = new byte[N * BS];
        for (int y = 0; y < N / 2; y++) {
            int a = H + y * N * BS, c = H + (N - 1 - y) * N * BS;
            System.Buffer.BlockCopy(b, a, tmp, 0, N * BS);
            System.Buffer.BlockCopy(b, c, b, a, N * BS);
            System.Buffer.BlockCopy(tmp, 0, b, c, N * BS);
        }
        for (int i = H; i < b.Length; i += BS) { // reverse the 4 index bytes (sample rows 0..3 -> 3..0)
            byte t = b[i + 4]; b[i + 4] = b[i + 7]; b[i + 7] = t; t = b[i + 5]; b[i + 5] = b[i + 6]; b[i + 6] = t;
        }
    }
    public static void FlipCols(byte[] b) {
        const int H = 0x430, N = 1024, BS = 8;
        byte[] blk = new byte[BS];
        for (int y = 0; y < N; y++) {
            int row = H + y * N * BS;
            for (int x = 0; x < N / 2; x++) {
                int a = row + x * BS, c = row + (N - 1 - x) * BS;
                System.Buffer.BlockCopy(b, a, blk, 0, BS); System.Buffer.BlockCopy(b, c, b, a, BS); System.Buffer.BlockCopy(blk, 0, b, c, BS);
            }
        }
        for (int i = H; i < b.Length; i += BS) { // reverse the 2-bit fields inside each index byte (sample cols 0..3 -> 3..0)
            for (int k = 4; k < 8; k++) { int v = b[i + k]; b[i + k] = (byte)(((v & 3) << 6) | ((v & 12) << 2) | ((v & 48) >> 2) | ((v & 192) >> 6)); }
        }
    }
}
'@
$files = @()
if ($Path) { $files += Get-Item $Path }
if ($Dir) { $files += Get-ChildItem $Dir -Filter '*hei_map*.bin' }
if (-not $files) { throw 'nothing to flip: give -Dir or -Path' }
$marker = if ($Dir) { Join-Path $Dir $(if ($Cols) { 'flipped_cols.txt' } else { 'flipped_rows.txt' }) } else { $null }
if ($marker -and (Test-Path $marker) -and -not $Force) { "already flipped ($marker) - use -Force to flip again"; return }
$n = 0
foreach ($f in $files) {
    $b = [IO.File]::ReadAllBytes($f.FullName)
    if ($b.Length -ne 0x430 + 1024 * 1024 * 8 -or [Text.Encoding]::ASCII.GetString($b, 8, 4) -ne 'PHA6') { "  skip $($f.Name): not a 4096x4096 PHA6 heightmap"; continue }
    if ($Cols) { [Pha6Flip]::FlipCols($b) } else { [Pha6Flip]::FlipRows($b) }
    [IO.File]::WriteAllBytes($f.FullName, $b); $n++
    "  flipped $($f.Name)"
}
if ($marker) { "$(Get-Date -Format s) $n files" | Set-Content $marker }
"$n files flipped ($(if ($Cols) { 'east-west' } else { 'north-south' }))"
