<#
.SYNOPSIS
  MF Overhaul archive tool for Graviteam Tactics: Mius-Front 6.00 build 3598.
  Replaces starter.exe unflat / mkflat, which do not exist on this build (programs.flatdata ships only
  pack_default, tacgame, opgame, updater, encycl).

.DESCRIPTION
  Formats (verified in milestone 0 against the game's own files and three installed community add-ons):

  AZP3 ".flatdata" pack
    0x00  'AZP3'            0x04 u32 entry count      0x08 u32 hash bucket count (0 allowed, see below)
    0x10  u64 data start    0x20 'GRAVITECH3 pack system v3.0' (or GRAVITECH2 in mod archives)
    0x40  bucket table, buckets*8 bytes: u32 (0x80000000|home slot), u32 entry index   (linear probing)
    then  entry table, count*0x80 bytes per entry:
          u32 9, u32 name-hash?, u64 offset, u64 size, u64 0, name[0x20], kind[0x20], loc[0x20], 0x20 pad
    then  entry bodies, each 4096-aligned; first body at 0x10000 in every archive seen.
    Bucket table: B = smallest power of two >= 3*count for count >= 4 (archives with fewer entries have none), slots
    {0x80000000|home, entry index} filled in entry order with linear probing, home = Azp3-Hash(name, kind, loc, B).
    The engine's lookups scan linearly when B = 0, so the table is written for faithfulness (unpack + pack reproduces
    sounds.flatdata, tabs.flatdata, text_loc.flatdata and music.flatdata byte for byte), not because loading needs it.
    The second u32 of an entry is the byte sum of the entry body mod 2^32 (verified on every entry of
    programs.flatdata and rvfxmod.flatdata); this tool computes it. The file is padded to a 0x10000 boundary.

  AZCF ".cfgpack/.addpack" binary config: see MiusPlayer _mp_research/tools/azcf.py (ported below).
  AZTX text pack: 0x30-byte records (u32 2, u32 value offset, u32 ?, u32 0, key[0x20]); values are
    NUL-terminated strings in 32-byte slots. Same-slot in-place edits are safe.
  .gt3ext add-on: a ZIP with core/desc.addpack and core/<files>; the game's updater (base_updater.codelib)
    installs it into data\common\<path from desc.addpack>\ and registers it in data\common\shared\config\paths.cfgpack.

.EXAMPLE
  .\gt3.ps1 list   <archive.flatdata>
  .\gt3.ps1 unpack <archive.flatdata> <out dir>            # writes <name>.<kind>.<loc>.bin + !flatlist
  .\gt3.ps1 pack   <out.flatdata> <dir with !flatlist>      # rebuilds from a !flatlist
  .\gt3.ps1 azcf   <file.addpack|cfgpack>                    # dump (cells prefixed u:/a:/v:/f:/b: by kind)
  .\gt3.ps1 nodes  <file.config.loc_def.bin> [sample rows]   # node list with type strings
  .\gt3.ps1 csv    <file.config.loc_def.bin> <node|#index|*> [out.csv|out dir]   # export a node (docs/tables.md)
  .\gt3.ps1 text   <file.text.loc_eng.bin> [out.csv]         # AZTX dump: key,short name,long name
  .\gt3.ps1 desc   <template.addpack> <out.addpack> path=<id> desc=<text> authors=<text> version=<n>
  .\gt3.ps1 gt3ext <out.gt3ext> <core dir>                   # zips <core dir>\* under core/
  .\gt3.ps1 diff    <base.bin> <target.bin> [out.delta]       # row-level AZCF delta (nodes/rows added, removed, changed)
  .\gt3.ps1 apply   <base.bin> <delta> <out.bin>              # rebuild a table from base + delta (grows tables, adds nodes)
  .\gt3.ps1 rewrite <in.bin> <out.bin>                        # parse + serialize (writer self-test)
  .\gt3.ps1 same    <a.bin> <b.bin>                           # node/cell-level comparison of two AZCF files
#>
param(
    [Parameter(Position = 0)][string]$Cmd,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)][string[]]$Args
)
Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
$ENTRY = 0x80; $ALIGN = 0x1000; $FIRST = 0x10000

# cp1251, not ASCII: two platoon nodes of the 30 July 1943 operation carry a Cyrillic letter in their name
function Read-Str([byte[]]$b, [int]$off, [int]$len) { [Text.Encoding]::GetEncoding(1251).GetString($b, $off, $len).Split([char]0)[0] }

function Read-Azp3([string]$path) {
    $b = [IO.File]::ReadAllBytes($path)
    if ([Text.Encoding]::ASCII.GetString($b, 0, 4) -ne 'AZP3') { throw "$path is not an AZP3 pack" }
    $cnt = [BitConverter]::ToUInt32($b, 4); $bk = [BitConverter]::ToUInt32($b, 8); $tbl = 0x40 + $bk * 8
    $entries = @()
    for ($i = 0; $i -lt $cnt; $i++) {
        $o = $tbl + $i * $ENTRY
        $entries += [pscustomobject]@{
            index = $i; lo = [BitConverter]::ToUInt32($b, $o); hi = [BitConverter]::ToUInt32($b, $o + 4)
            offset = [BitConverter]::ToUInt64($b, $o + 8); size = [BitConverter]::ToUInt64($b, $o + 16)
            name = Read-Str $b ($o + 0x20) 0x20; kind = Read-Str $b ($o + 0x40) 0x20; loc = Read-Str $b ($o + 0x60) 0x20
        }
    }
    [pscustomobject]@{ path = $path; bytes = $b; count = $cnt; buckets = $bk; sig = (Read-Str $b 0x20 0x20); entries = $entries }
}

function Azp3-Hash([string]$name, [string]$kind, [string]$loc, [uint32]$N) {
    # The pack system's entry hash (base_shell.codelib 0x180007030): the three strings are hashed in sequence with the
    # same h = (a*h + c) mod N, a = (a*0x6a2f) mod (N-1) step as Azcf-Hash, a restarting at 0x7e9f for each string
    # while h carries over. Reproduces every bucket table of the 34 hashed vanilla and DataBase archives byte for byte.
    [uint64]$h = 0; [uint64]$M = 4294967296
    foreach ($s in $name, $kind, $loc) {
        [uint64]$a = 0x7e9f
        foreach ($ch in $Cp1251.GetBytes([string]$s)) {
            [int64]$c = $ch; if ($c -ge 128) { $c -= 256 }
            [int64]$t = [int64](($a * $h) % $M) + $c
            if ($t -lt 0) { $t += $M }
            $h = ([uint64]$t % $M) % $N
            $a = (($a * 0x6a2f) % $M) % ($N - 1)
        }
    }
    [uint32]$h
}
function Write-Azp3([string]$out, [object[]]$items, [string]$sig = 'GRAVITECH3 pack system v3.0', [bool]$forceTable = $false) {
    # $items: objects with name, kind, loc, data (byte[]). Writes the bucket table exactly as the engine's writer does
    # (its lookups scan linearly when the table is absent, so it is a faithfulness feature, not a requirement):
    # B = smallest power of two >= 3*count buckets for count >= 4, entries inserted in order with linear probing. The engine's own writer leaves
    # archives with fewer than 4 entries without a table; $forceTable writes one anyway (16 buckets minimum), which
    # the reader accepts (it only masks with B-1), for add-ons that ship one or two sounds or textures.
    $n = $items.Count
    $nbk = if ($n -lt 4 -and -not $forceTable) { 0 } else { $p = 16; while ($p -lt 3 * $n) { $p *= 2 }; $p }   # not $B: it would alias $b below
    $tbl = 0x40 + $nbk * 8
    $hdr = $tbl + $n * $ENTRY
    $pos = [Math]::Max($FIRST, (($hdr + $ALIGN - 1) -band (-bnot ($ALIGN - 1))))
    $offsets = @()
    foreach ($it in $items) { $offsets += $pos; $pos = ($pos + $it.data.Length + $ALIGN - 1) -band (-bnot ($ALIGN - 1)) }
    $total = ($pos + $FIRST - 1) -band (-bnot ($FIRST - 1))   # the engine's writer pads the file to a 0x10000 boundary
    $b = New-Object byte[] $total
    [Text.Encoding]::ASCII.GetBytes('AZP3').CopyTo($b, 0)
    [BitConverter]::GetBytes([uint32]$n).CopyTo($b, 4)
    [BitConverter]::GetBytes([uint32]$nbk).CopyTo($b, 8)
    [BitConverter]::GetBytes([uint64]$hdr).CopyTo($b, 0x10)
    [Text.Encoding]::ASCII.GetBytes($sig).CopyTo($b, 0x20)
    if ($nbk) {
        $slots = New-Object uint32[] ($nbk * 2)
        for ($i = 0; $i -lt $n; $i++) {
            $h = Azp3-Hash $items[$i].name $items[$i].kind $items[$i].loc $nbk; $s = $h
            for ($t = 0; $t -lt $nbk; $t++) { if (($slots[$s * 2] -band 0x80000000) -eq 0) { break }; $s = ($s + 1) % $nbk }
            $slots[$s * 2] = 0x80000000 -bor $h; $slots[$s * 2 + 1] = [uint32]$i
        }
        for ($s = 0; $s -lt $nbk * 2; $s++) { [BitConverter]::GetBytes([uint32]$slots[$s]).CopyTo($b, 0x40 + $s * 4) }
    }
    for ($i = 0; $i -lt $n; $i++) {
        $it = $items[$i]; $o = $tbl + $i * $ENTRY
        [uint64]$sum = 0; foreach ($byte in $it.data) { $sum += $byte }
        [BitConverter]::GetBytes([uint32]9).CopyTo($b, $o)
        [BitConverter]::GetBytes([uint32]($sum % 4294967296)).CopyTo($b, $o + 4)
        [BitConverter]::GetBytes([uint64]$offsets[$i]).CopyTo($b, $o + 8)
        [BitConverter]::GetBytes([uint64]$it.data.Length).CopyTo($b, $o + 16)
        foreach ($p in @(@($it.name, 0x20), @($it.kind, 0x40), @($it.loc, 0x60))) {
            $s = [Text.Encoding]::ASCII.GetBytes([string]$p[0]); if ($s.Length -gt 0x1f) { throw "name too long: $($p[0])" }
            $s.CopyTo($b, $o + $p[1])
        }
        [Array]::Copy($it.data, 0, $b, $offsets[$i], $it.data.Length)
    }
    [IO.File]::WriteAllBytes($out, $b)
    "wrote $out : $n entries, $total bytes"
}

function Cmd-List([string]$path) {
    $p = Read-Azp3 $path
    "$path : $($p.count) entries, $($p.buckets) buckets, sig '$($p.sig)'"
    $p.entries | ForEach-Object { '{0,3} {1,-30} {2,-10} {3,-8} off=0x{4:x} size={5} hi=0x{6:x8}' -f $_.index, $_.name, $_.kind, $_.loc, $_.offset, $_.size, $_.hi }
}

function Cmd-Unpack([string]$path, [string]$outDir) {
    $p = Read-Azp3 $path
    New-Item -ItemType Directory -Force $outDir | Out-Null
    $list = @("i_unflat:unflat()", "{")
    foreach ($e in $p.entries) {
        $blob = New-Object byte[] $e.size
        [Array]::Copy($p.bytes, [int64]$e.offset, $blob, 0, [int64]$e.size)
        $file = '{0}.{1}.{2}.bin' -f $e.name, $e.kind, $e.loc
        [IO.File]::WriteAllBytes((Join-Path $outDir $file), $blob)
        $list += ("`t{0,-30}, {1,-16}, {2} ;" -f $e.name, $e.kind, $e.loc)
    }
    $list += "}"
    [IO.File]::WriteAllLines((Join-Path $outDir '!flatlist'), $list, [Text.Encoding]::ASCII)
    "unpacked $($p.count) entries into $outDir (template: !flatlist)"
}

function Cmd-Pack([string]$out, [string]$dir, [string]$opt = '') {
    # pack <out.flatdata> <dir> [hash]   'hash' forces a bucket table even for fewer than 4 entries
    $listPath = Join-Path $dir '!flatlist'
    if (-not (Test-Path $listPath)) { throw "missing $listPath" }
    $items = @()
    foreach ($line in Get-Content $listPath) {
        if ($line -notmatch '^\s*([^,;\s]+)\s*,\s*([^,;\s]+)\s*,\s*([^,;\s]+)\s*;') { continue }
        $name = $Matches[1]; $kind = $Matches[2]; $loc = $Matches[3]
        $file = Join-Path $dir ('{0}.{1}.{2}.bin' -f $name, $kind, $loc)
        if (-not (Test-Path $file)) { throw "missing $file" }
        $items += [pscustomobject]@{ name = $name; kind = $kind; loc = $loc; data = [IO.File]::ReadAllBytes($file) }
    }
    if ($items.Count -eq 0) { throw "no entries in $listPath" }
    Write-Azp3 $out $items 'GRAVITECH3 pack system v3.0' ($opt -eq 'hash')
}

# ---- AZCF (port of MiusPlayer azcf.py) ----
function Read-Azcf([byte[]]$b) {
    if ([Text.Encoding]::ASCII.GetString($b, 0, 4) -ne 'AZCF') { throw 'not AZCF' }
    $count = [BitConverter]::ToUInt32($b, 4); $table = [BitConverter]::ToUInt32($b, 8)
    $nodes = @()
    for ($i = 0; $i -lt $count; $i++) {
        $o = $table + $i * 0x80
        $f = 0..9 | ForEach-Object { [BitConverter]::ToUInt32($b, $o + 0x20 + $_ * 4) }
        $nodes += [pscustomobject]@{ index = $i; pos = $o; name = (Read-Str $b $o 0x20); type = $f[0]; cols = $f[1]; rows = $f[2]; types = $f[3]; data = $f[4]; kids = $f[5]; nkids = $f[6] }
    }
    [pscustomobject]@{ bytes = $b; count = $count; table = $table; nodes = $nodes }
}
function Azcf-CStr([byte[]]$b, [int]$off) { $e = [Array]::IndexOf($b, [byte]0, $off); [Text.Encoding]::GetEncoding(1251).GetString($b, $off, $e - $off) }
# A cell is 0x20 bytes: four u32 value slots, u32 kind at +16, three zero u32.
#   kind 2 's' string   : slot0 = length, slot1 = offset of a NUL-terminated cp1251 string
#   kind 4 'u' u32      : slot0 = number, fourcc ('INF', 'USSR') or date 0xYYYYMMDD
#   kind 6 'a' int[1-4] : slot0..3 = signed components (a scalar int is a 1-component vector)
#   kind 1 'v' float[1-4]: slot0..3 = IEEE floats
#   kind 0 'f' float    : slot0 = one IEEE float
#   kind 5 'b' bool     : slot0 = 0/1
# The node's type string (one char per column, see `nodes`) tells the column type; a cell is
# decoded from its own kind field, so the type string is only informational.
$Inv = [Globalization.CultureInfo]::InvariantCulture
function Azcf-Fourcc([uint32]$v) {
    # 3 or 4 printable ASCII bytes, little-endian, NUL-padded: 'INF' = 0x00464E49.
    # Two-letter codes ('MT' mortar, 'MG', 'SS', 'MR') are accepted only when both bytes are capital letters.
    if ($v -lt 0x10000) {
        $lo = $v -band 0xff; $hi = ($v -shr 8) -band 0xff
        if ($lo -ge 0x41 -and $lo -le 0x5a -and $hi -ge 0x41 -and $hi -le 0x5a) { return [string][char]$lo + [char]$hi }
        return $null
    }
    $s = ''
    for ($i = 0; $i -lt 4; $i++) {
        $c = ($v -shr (8 * $i)) -band 0xff
        if ($c -eq 0) { if ($i -lt 3) { return $null } else { break } }
        if ($c -lt 0x21 -or $c -gt 0x7e) { return $null }
        $s += [char]$c
    }
    $s
}
function Azcf-Decode([byte[]]$b, [int]$off) {
    # Text form of a cell, used by csv/azcf/nodes. Vectors are joined with ';', trailing zero components dropped.
    $kind = [BitConverter]::ToUInt32($b, $off + 16)
    $s = 0..3 | ForEach-Object { [BitConverter]::ToUInt32($b, $off + $_ * 4) }
    switch ($kind) {
        2 { if ($s[1]) { Azcf-CStr $b $s[1] } else { '' } }
        4 {
            $fc = Azcf-Fourcc $s[0]
            if ($fc) { $fc }
            elseif ((($s[0] -shr 24) -ge 0x19) -and (($s[0] -shr 24) -le 0x20) -and ((($s[0] -shr 16) -band 0xff) -le 0x99)) { '0x{0:x8}' -f $s[0] }
            else { [string]$s[0] }
        }
        6 { $n = 3; while ($n -gt 0 -and $s[$n] -eq 0) { $n-- }; (0..$n | ForEach-Object { [string][BitConverter]::ToInt32($b, $off + $_ * 4) }) -join ';' }
        1 { $n = 3; while ($n -gt 0 -and $s[$n] -eq 0) { $n-- }; (0..$n | ForEach-Object { [BitConverter]::ToSingle($b, $off + $_ * 4).ToString('R', $Inv) }) -join ';' }
        0 { [BitConverter]::ToSingle($b, $off).ToString('R', $Inv) }
        5 { if ($s[0]) { '1' } else { '0' } }
        default { 'kind{0}:{1:x8};{2:x8};{3:x8};{4:x8}' -f $kind, $s[0], $s[1], $s[2], $s[3] }
    }
}
function Azcf-Cell([byte[]]$b, [int]$off) {
    $kind = [BitConverter]::ToUInt32($b, $off + 16)
    $t = switch ($kind) { 2 { '' } 4 { 'u:' } 6 { 'a:' } 1 { 'v:' } 0 { 'f:' } 5 { 'b:' } default { '' } }
    $t + (Azcf-Decode $b $off)
}
function Csv-Quote([string]$s) { if ($s -match '[,"\r\n]') { '"' + $s.Replace('"', '""') + '"' } else { $s } }
function Cmd-Csv([string]$path, [string]$which, [string]$out) {
    # csv <file> <node name | #index | *> [out.csv | out dir]
    # Table node: header row c0:<type>,c1:<type>,... (type char from the node's type string), one row per table row.
    # Struct node: header field,type,value; one row per field.
    # '*' writes every node to <out dir>\<index>_<name>.csv (struct nodes too), which keeps qbattle's
    # repeated 'pool' nodes apart and next to the p_<pool> struct they belong to.
    $c = Read-Azcf ([IO.File]::ReadAllBytes($path))
    $targets = @()
    if ($which -eq '*') { $targets = $c.nodes | Where-Object { $_.type -eq 1 -or $_.type -eq 2 } }
    elseif ($which -match '^#(\d+)$') { $targets = @($c.nodes[[int]$Matches[1]]) }
    else { $targets = @($c.nodes | Where-Object { $_.name -eq $which }) }
    if ($targets.Count -eq 0) { throw "node '$which' not found in $path" }
    if ($which -ne '*' -and $targets.Count -gt 1) { throw "node name '$which' is not unique ($($targets.Count) nodes); use #<index>" }
    if ($which -eq '*') { if (-not $out) { throw 'csv <file> * needs an output directory' }; New-Item -ItemType Directory -Force $out | Out-Null }
    foreach ($n in $targets) {
        $types = Azcf-CStr $c.bytes $n.types
        $lines = New-Object Collections.Generic.List[string]
        if ($n.type -eq 1) {
            $lines.Add('field,type,value')
            for ($r = 0; $r -lt $n.rows; $r++) {
                $o = $n.data + $r * 0x40
                $t = if ($r -lt $types.Length) { $types[$r] } else { '?' }
                $lines.Add((Csv-Quote (Read-Str $c.bytes ($o + 0x20) 0x20)) + ',' + $t + ',' + (Csv-Quote (Azcf-Decode $c.bytes $o)))
            }
        } else {
            $lines.Add(((0..($n.cols - 1) | ForEach-Object { 'c{0}:{1}' -f $_, $(if ($_ -lt $types.Length) { $types[$_] } else { '?' }) }) -join ','))
            for ($r = 0; $r -lt $n.rows; $r++) {
                $o = $n.data + $r * 0x20 * $n.cols
                $lines.Add(((0..($n.cols - 1) | ForEach-Object { Csv-Quote (Azcf-Decode $c.bytes ($o + $_ * 0x20)) }) -join ','))
            }
        }
        if ($which -eq '*') {
            # node names may hold characters a file name cannot (operation desc: 'i_campgen:campgen'); map them to '_'
            $safe = $(if ($n.name) { $n.name } else { 'root' }) -replace '[\\/:*?"<>|]', '_'
            $f = Join-Path $out ('{0:d4}_{1}.csv' -f $n.index, $safe)
            [IO.File]::WriteAllLines($f, $lines, (New-Object Text.UTF8Encoding $false))
        } elseif ($out) {
            [IO.File]::WriteAllLines($out, $lines, (New-Object Text.UTF8Encoding $false)); "wrote $out : $($n.rows) rows"
        } else { $lines }
    }
    if ($which -eq '*') { "wrote $($targets.Count) nodes into $out" }
}

# ---- AZTX text pack ----
function Read-Aztx([byte[]]$b) {
    # 'AZTX', loc name at 0x20; 0x40 u32 key count, 0x44 offset of key records, 0x48 bucket count, 0x4c bucket table offset.
    # Key record 0x30: char[0x20] key, u32 item count, u32 items offset, u32 hash?, u32 0.
    # Item 0x10: u32 length, u32 string offset, u64 0. Strings are NUL-terminated cp1251.
    if ([Text.Encoding]::ASCII.GetString($b, 0, 4) -ne 'AZTX') { throw 'not AZTX' }
    $n = [BitConverter]::ToUInt32($b, 0x40); $kr = [BitConverter]::ToUInt32($b, 0x44)
    $keys = @()
    for ($i = 0; $i -lt $n; $i++) {
        $o = $kr + $i * 0x30
        $cnt = [BitConverter]::ToUInt32($b, $o + 0x20); $ip = [BitConverter]::ToUInt32($b, $o + 0x24)
        $items = @()
        for ($j = 0; $j -lt $cnt; $j++) {
            $len = [BitConverter]::ToUInt32($b, $ip + $j * 0x10); $so = [BitConverter]::ToUInt32($b, $ip + $j * 0x10 + 4)
            $items += [Text.Encoding]::GetEncoding(1251).GetString($b, $so, $len)
        }
        $keys += [pscustomobject]@{ key = (Read-Str $b $o 0x20); items = $items }
    }
    [pscustomobject]@{ loc = (Read-Str $b 0x20 0x20); keys = $keys }
}
function Cmd-Text([string]$path, [string]$out) {
    # text <file.text.loc_xxx.bin> [out.csv]   -> key,item1,item2,...   (unit keys: short name, long name)
    $t = Read-Aztx ([IO.File]::ReadAllBytes($path))
    $lines = foreach ($k in $t.keys) { (@($k.key) + $k.items | ForEach-Object { Csv-Quote $_ }) -join ',' }
    if ($out) { [IO.File]::WriteAllLines($out, [string[]]$lines, (New-Object Text.UTF8Encoding $false)); "wrote $out : $($t.keys.Count) keys ($($t.loc))" } else { $lines }
}
function Cmd-Azcf([string]$path) {
    $c = Read-Azcf ([IO.File]::ReadAllBytes($path))
    foreach ($n in $c.nodes) {
        "[{0}] {1}  type={2} cols={3} rows={4} types='{5}'" -f $n.index, $n.name, $n.type, $n.cols, $n.rows, (Azcf-CStr $c.bytes $n.types)
        for ($r = 0; $r -lt $n.rows; $r++) {
            if ($n.type -eq 1) { $o = $n.data + $r * 0x40; "      {0,-16} = {1}" -f (Read-Str $c.bytes ($o + 0x20) 0x20), (Azcf-Cell $c.bytes $o) }
            else { $o = $n.data + $r * 0x20 * $n.cols; "      " + ((0..($n.cols - 1) | ForEach-Object { Azcf-Cell $c.bytes ($o + $_ * 0x20) }) -join ' | ') }
        }
    }
}
function Cmd-Nodes([string]$path, [int]$sample = 2) {
    # Node names with row counts and the first $sample rows: the quick way to see what a table holds.
    $c = Read-Azcf ([IO.File]::ReadAllBytes($path))
    "$path : $($c.count) nodes"
    foreach ($n in $c.nodes) {
        $first = @()
        for ($r = 0; $r -lt [Math]::Min($n.rows, $sample); $r++) {
            if ($n.type -eq 1) { $o = $n.data + $r * 0x40; $first += ('{0}={1}' -f (Read-Str $c.bytes ($o + 0x20) 0x20), (Azcf-Cell $c.bytes $o)) }
            else { $o = $n.data + $r * 0x20 * $n.cols; $first += ((0..([Math]::Min($n.cols, 6) - 1) | ForEach-Object { Azcf-Cell $c.bytes ($o + $_ * 0x20) }) -join '|') }
        }
        '  [{0,4}] {1,-32} type={2} cols={3,-3} rows={4,-5} {5}' -f $n.index, $n.name, $n.type, $n.cols, $n.rows, ($first -join '  //  ')
    }
}
function Set-AzcfStringField([ref]$bytesRef, [string]$node, [string]$field, [string]$text) {
    # Relocate: append the new string at the end, point the cell at it. Keeps all other offsets valid.
    $c = Read-Azcf $bytesRef.Value
    $n = $c.nodes | Where-Object { $_.name -eq $node } | Select-Object -First 1
    if (-not $n -or $n.type -ne 1) { throw "struct node $node not found" }
    for ($r = 0; $r -lt $n.rows; $r++) {
        $o = $n.data + $r * 0x40
        if ((Read-Str $c.bytes ($o + 0x20) 0x20) -ne $field) { continue }
        if ([BitConverter]::ToUInt32($c.bytes, $o + 16) -ne 2) { throw "$field is not a string cell" }
        $raw = [Text.Encoding]::GetEncoding(1251).GetBytes($text)
        $b = $c.bytes
        $pad = (16 - ($b.Length % 16)) % 16
        $nb = New-Object byte[] ($b.Length + $pad + $raw.Length + 1 + 16)
        [Array]::Copy($b, $nb, $b.Length)
        $soff = $b.Length + $pad
        [Array]::Copy($raw, 0, $nb, $soff, $raw.Length)
        [BitConverter]::GetBytes([uint32]$raw.Length).CopyTo($nb, $o)
        [BitConverter]::GetBytes([uint32]$soff).CopyTo($nb, $o + 4)
        $bytesRef.Value = $nb
        return
    }
    throw "field $field not found in $node"
}
function Set-AzcfUIntField([ref]$bytesRef, [string]$node, [string]$field, [uint32]$value) {
    $c = Read-Azcf $bytesRef.Value
    $n = $c.nodes | Where-Object { $_.name -eq $node } | Select-Object -First 1
    for ($r = 0; $r -lt $n.rows; $r++) {
        $o = $n.data + $r * 0x40
        if ((Read-Str $c.bytes ($o + 0x20) 0x20) -ne $field) { continue }
        [BitConverter]::GetBytes($value).CopyTo($bytesRef.Value, $o); return
    }
    throw "field $field not found in $node"
}
function Cmd-Desc([string]$template, [string]$out, [string[]]$kv) {
    $b = [IO.File]::ReadAllBytes($template)
    foreach ($pair in $kv) {
        $k, $v = $pair.Split('=', 2)
        if ($k -eq 'version') { Set-AzcfUIntField ([ref]$b) 'i_updater:updater' $k ([uint32]$v) }
        else { Set-AzcfStringField ([ref]$b) 'i_updater:updater' $k $v }
    }
    [IO.File]::WriteAllBytes($out, $b)
    "wrote $out"
}

function Cmd-Gt3ext([string]$out, [string]$coreDir) {
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path $out) { Remove-Item $out -Force }
    $z = [IO.Compression.ZipFile]::Open($out, [IO.Compression.ZipArchiveMode]::Create)
    $root = (Resolve-Path $coreDir).Path.TrimEnd('\')
    foreach ($f in Get-ChildItem $root -File -Recurse) {
        $rel = 'core/' + $f.FullName.Substring($root.Length + 1).Replace('\', '/')
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($z, $f.FullName, $rel, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
        "  + $rel"
    }
    $z.Dispose()
    "wrote $out"
}

# ---- AZCF document model: load / save / diff / apply (milestone 0b) ----
# Full layout (verified 2026-10-15 on every config entry of tabs.flatdata and tabs_oprum.flatdata, 3598):
#   0x00 'AZCF'  0x04 u32 node count  0x08 u32 node table offset (0x40)  0x0c u32 root hash buckets
#   0x10 u32 root hash offset  0x14..0x1f zero  0x20 char[0x20] name
#   node record 0x80: char[0x20] name; u32 type (0 root, 1 struct, 2 table), cols, rows, type-string offset,
#     data offset, kids offset, kid count, field-hash buckets, field-hash offset, kid-hash buckets, kid-hash offset, zeros.
#   Regions, in this order and without padding: cell data of every node in node order (struct row = cell + char[0x20]
#   field name, table row = cols cells); per node in node order its kid-name hash table then its field-name hash table
#   (when it has them); the kid-index array of every node that has kids (leaves point their kids offset at the first
#   array); per node its type string and its strings, NUL-terminated cp1251. Node order is a pre-order walk of the tree.
#   Hash tables: N = smallest power of two >= 3n buckets of {u32 0x80000000|home, u32 index}, filled in order with
#   linear probing; a node gets a kid table for n >= 4 kids (index = kid node number) and a struct gets a field table
#   for n >= 5 fields (index = row number). home = Azcf-Hash(name, N), recovered from base_encycl.codelib (the same
#   routine is linked into every codelib) and checked against all 7 415 kid names and 1 418 field tables of the
#   vanilla tables. A struct without its field table crashes the engine as soon as it looks a field up (0.2.6/0.2.7).
#   The engine's own writer orders a node's string pool by allocation time, which a table does not record, so a
#   rewritten file is node- and cell-identical to its source, not byte-identical (the strings move, nothing else).
$Cp1251 = [Text.Encoding]::GetEncoding(1251)

function Azcf-Hash([string]$name, [uint32]$N) {
    # h = (a*h + c) mod N; a = (a*0x6a2f) mod (N-1); a starts at 0x7e9f, h at 0; c is a signed char.
    [uint64]$h = 0; [uint64]$a = 0x7e9f; [uint64]$M = 4294967296
    foreach ($ch in $Cp1251.GetBytes($name)) {
        [int64]$c = $ch; if ($c -ge 128) { $c -= 256 }
        [int64]$t = [int64](($a * $h) % $M) + $c
        if ($t -lt 0) { $t += $M }
        $h = ([uint64]$t % $M) % $N
        $a = (($a * 0x6a2f) % $M) % ($N - 1)
    }
    [uint32]$h
}
function Azcf-Buckets([int]$n, [int]$min = 4) { if ($n -lt $min) { return 0 }; $x = 3 * $n; $p = 1; while ($p -lt $x) { $p *= 2 }; $p }
function Azcf-HashTable([string[]]$names, [int]$nbk) {
    # {0x80000000|home, index} slots, names inserted in order with linear probing (what the engine's writer does)
    $slots = New-Object uint32[] ($nbk * 2)
    for ($i = 0; $i -lt $names.Count; $i++) {
        $h = Azcf-Hash $names[$i] $nbk; $s = $h
        for ($t = 0; $t -lt $nbk; $t++) { if (($slots[$s * 2] -band 0x80000000) -eq 0) { break }; $s = ($s + 1) % $nbk }
        $slots[$s * 2] = 0x80000000 -bor $h; $slots[$s * 2 + 1] = [uint32]$i
    }
    ,$slots
}

function Azcf-ReadCell([byte[]]$b, [int]$off) {
    $v = New-Object uint32[] 4
    for ($i = 0; $i -lt 4; $i++) { $v[$i] = [BitConverter]::ToUInt32($b, $off + $i * 4) }
    $k = [BitConverter]::ToUInt32($b, $off + 16)
    $s = $null
    if ($k -eq 2) { $s = if ($v[1]) { Azcf-CStr $b $v[1] } else { '' } }
    @{ k = $k; v = $v; s = $s }
}
function Azcf-NewNode([string]$name, [int]$type, [int]$cols, [string]$types) {
    [pscustomobject]@{ name = $name; type = $type; cols = $cols; types = $types
        rows = New-Object Collections.Generic.List[object]; kids = New-Object Collections.Generic.List[object] }
}
function Azcf-Load([string]$path) {
    $b = [IO.File]::ReadAllBytes($path)
    $c = Read-Azcf $b
    $nodes = New-Object object[] $c.count
    for ($i = 0; $i -lt $c.count; $i++) {
        $n = $c.nodes[$i]
        $node = Azcf-NewNode $n.name $n.type $n.cols (Azcf-CStr $b $n.types)
        if ($n.type -eq 1) {
            for ($r = 0; $r -lt $n.rows; $r++) {
                $o = $n.data + $r * 0x40
                $node.rows.Add(@{ name = (Read-Str $b ($o + 0x20) 0x20); c = @(Azcf-ReadCell $b $o) })
            }
        } elseif ($n.type -eq 2) {
            for ($r = 0; $r -lt $n.rows; $r++) {
                $o = $n.data + $r * 0x20 * $n.cols
                $cells = New-Object object[] $n.cols
                for ($j = 0; $j -lt $n.cols; $j++) { $cells[$j] = Azcf-ReadCell $b ($o + $j * 0x20) }
                $node.rows.Add(@{ name = $null; c = $cells })
            }
        }
        $nodes[$i] = $node
    }
    for ($i = 0; $i -lt $c.count; $i++) {
        $n = $c.nodes[$i]
        for ($k = 0; $k -lt $n.nkids; $k++) { $nodes[$i].kids.Add($nodes[[BitConverter]::ToUInt32($b, $n.kids + $k * 4)]) }
    }
    [pscustomobject]@{ name = (Read-Str $b 0x20 0x20); root = $nodes[0]; path = $path }
}
function Azcf-Order([object]$root) {
    # pre-order list of nodes (the on-disk node order)
    $out = New-Object Collections.Generic.List[object]
    $stack = New-Object Collections.Generic.Stack[object]; $stack.Push($root)
    while ($stack.Count) {
        $n = $stack.Pop(); $out.Add($n)
        for ($i = $n.kids.Count - 1; $i -ge 0; $i--) { $stack.Push($n.kids[$i]) }
    }
    ,$out   # the comma keeps a 0- or 1-element list from being unrolled by the pipeline
}
$KindChar = @{ 2 = 's'; 4 = 'u'; 6 = 'a'; 1 = 'v'; 0 = 'f'; 5 = 'b' }
function Azcf-Save([object]$doc, [string]$out) {
    $order = Azcf-Order $doc.root
    $count = $order.Count
    # Type strings: in every vanilla table a struct's type string is exactly the kinds of its fields and a table's
    # is the kinds of its columns (checked over all 78 entries of tabs/tabs_oprum). Structs are regenerated here so
    # that added or removed fields stay consistent; a table row whose kinds disagree with the columns is an error.
    foreach ($n in $order) {
        if ($n.type -eq 1) {
            $gen = (($n.rows | ForEach-Object { $k = [int]$_.c[0].k; if ($KindChar.ContainsKey($k)) { $KindChar[$k] } else { '?' } }) -join '')
            if (-not $gen.Contains('?')) { $n.types = $gen }   # unknown kinds (junk rows in some community tables): keep the stored string
        }
        elseif ($n.type -eq 2 -and $n.rows.Count) {
            $want = $n.types.Substring(0, [Math]::Min($n.cols, $n.types.Length))
            foreach ($row in $n.rows) {
                $have = (($row.c | ForEach-Object { $k = [int]$_.k; if ($KindChar.ContainsKey($k)) { $KindChar[$k] } else { '?' } }) -join '')
                if ($have -ne $want) { throw "node '$($n.name)': row '$(Cell-Encode $row.c[0])' has kinds '$have', table columns are '$want'" }
            }
        }
    }
    # node -> node number. Stamped on the node object itself: an identity-hash keyed table collided on a 3 600-node
    # operation table (two nodes, one hash) and wrote a kid index pointing at the wrong node (found 2026-10-16).
    for ($i = 0; $i -lt $count; $i++) { $order[$i] | Add-Member -NotePropertyName _ix -NotePropertyValue $i -Force }
    # layout pass
    $pos = 0x40 + $count * 0x80
    $dataOff = New-Object int[] $count; $hsz = New-Object int[] $count; $hoff = New-Object int[] $count
    $kidsOff = New-Object int[] $count; $typesOff = New-Object int[] $count
    for ($i = 0; $i -lt $count; $i++) {
        $n = $order[$i]; $dataOff[$i] = $pos
        if ($n.type -eq 1) { $pos += $n.rows.Count * 0x40 } elseif ($n.type -eq 2) { $pos += $n.rows.Count * $n.cols * 0x20 }
    }
    # per node, in node order: the kid-name hash table, then (structs) the field-name hash table (node fields 7/8)
    $fsz = New-Object int[] $count; $foff = New-Object int[] $count
    for ($i = 0; $i -lt $count; $i++) {
        $n = $order[$i]; $hsz[$i] = Azcf-Buckets $n.kids.Count
        if ($hsz[$i]) { $hoff[$i] = $pos; $pos += $hsz[$i] * 8 } else { $hoff[$i] = 0 }
        $fsz[$i] = if ($n.type -eq 1) { Azcf-Buckets $n.rows.Count 5 } else { 0 }
        if ($fsz[$i]) { $foff[$i] = $pos; $pos += $fsz[$i] * 8 } else { $foff[$i] = 0 }
    }
    $kidsStart = $pos
    for ($i = 0; $i -lt $count; $i++) {
        $n = $order[$i]
        if ($n.kids.Count) { $kidsOff[$i] = $pos; $pos += $n.kids.Count * 4 } else { $kidsOff[$i] = $kidsStart }
    }
    # one string pool for the whole file (the engine shares identical strings across nodes); each node's type string
    # is followed by the strings that first appear in that node
    $pool = New-Object Collections.Specialized.OrderedDictionary
    for ($i = 0; $i -lt $count; $i++) {
        $n = $order[$i]; $typesOff[$i] = $pos; $pos += $Cp1251.GetByteCount($n.types) + 1
        foreach ($row in $n.rows) { foreach ($cell in $row.c) {
            if ($cell.k -eq 2 -and -not $pool.Contains($cell.s)) { $pool.Add($cell.s, $pos); $pos += $Cp1251.GetByteCount($cell.s) + 1 }
        } }
    }
    # write pass
    $buf = New-Object byte[] $pos
    $w = New-Object IO.BinaryWriter (New-Object IO.MemoryStream (,$buf))
    [Text.Encoding]::ASCII.GetBytes('AZCF').CopyTo($buf, 0)
    [BitConverter]::GetBytes([uint32]$count).CopyTo($buf, 4)
    [BitConverter]::GetBytes([uint32]0x40).CopyTo($buf, 8)
    [BitConverter]::GetBytes([uint32]$hsz[0]).CopyTo($buf, 0xc)
    [BitConverter]::GetBytes([uint32]$hoff[0]).CopyTo($buf, 0x10)
    $nm = [Text.Encoding]::ASCII.GetBytes([string]$doc.name); if ($nm.Length -gt 0x1f) { throw "header name too long: $($doc.name)" }
    $nm.CopyTo($buf, 0x20)
    for ($i = 0; $i -lt $count; $i++) {
        $n = $order[$i]; $o = 0x40 + $i * 0x80
        $nm = $Cp1251.GetBytes([string]$n.name); if ($nm.Length -gt 0x1f) { throw "node name too long: $($n.name)" }
        $nm.CopyTo($buf, $o)
        $f = @([uint32]$n.type, [uint32]$n.cols, [uint32]$n.rows.Count, [uint32]$typesOff[$i], [uint32]$dataOff[$i], [uint32]$kidsOff[$i], [uint32]$n.kids.Count, [uint32]$fsz[$i], [uint32]$foff[$i], [uint32]$hsz[$i], [uint32]$hoff[$i])
        for ($j = 0; $j -lt $f.Count; $j++) { [BitConverter]::GetBytes([uint32]$f[$j]).CopyTo($buf, $o + 0x20 + $j * 4) }
    }
    for ($i = 0; $i -lt $count; $i++) {
        $n = $order[$i]; $w.BaseStream.Position = $dataOff[$i]
        foreach ($row in $n.rows) {
            foreach ($cell in $row.c) {
                if ($cell.k -eq 2) { $w.Write([uint32]$Cp1251.GetByteCount($cell.s)); $w.Write([uint32]$pool[$cell.s]); $w.Write([uint32]0); $w.Write([uint32]0) }
                else { $w.Write([uint32]$cell.v[0]); $w.Write([uint32]$cell.v[1]); $w.Write([uint32]$cell.v[2]); $w.Write([uint32]$cell.v[3]) }
                $w.Write([uint32]$cell.k); $w.Write([uint32]0); $w.Write([uint32]0); $w.Write([uint32]0)
            }
            if ($n.type -eq 1) { $p = $w.BaseStream.Position; $nm = $Cp1251.GetBytes([string]$row.name); $nm.CopyTo($buf, $p); $w.BaseStream.Position = $p + 0x20 }
        }
    }
    for ($i = 0; $i -lt $count; $i++) {
        $n = $order[$i]
        if ($hsz[$i]) {
            # kid-name table: the index stored is the kid's node number, so insert by name and map afterwards
            $slots = Azcf-HashTable ([string[]]($n.kids | ForEach-Object { $_.name })) $hsz[$i]
            for ($s = 0; $s -lt $hsz[$i]; $s++) { if ($slots[$s * 2] -band 0x80000000) { $slots[$s * 2 + 1] = [uint32]$n.kids[[int]$slots[$s * 2 + 1]]._ix } }
            $w.BaseStream.Position = $hoff[$i]; foreach ($x in $slots) { $w.Write([uint32]$x) }
        }
        if ($fsz[$i]) {
            # field-name table of a struct: index = row number
            $slots = Azcf-HashTable ([string[]]($n.rows | ForEach-Object { [string]$_.name })) $fsz[$i]
            $w.BaseStream.Position = $foff[$i]; foreach ($x in $slots) { $w.Write([uint32]$x) }
        }
        if ($n.kids.Count) {
            $w.BaseStream.Position = $kidsOff[$i]
            foreach ($kid in $n.kids) { $w.Write([uint32]$kid._ix) }
        }
    }
    for ($i = 0; $i -lt $count; $i++) { $n = $order[$i]; $Cp1251.GetBytes([string]$n.types).CopyTo($buf, $typesOff[$i]) }
    foreach ($key in $pool.Keys) { $Cp1251.GetBytes([string]$key).CopyTo($buf, $pool[$key]) }
    $w.Flush()
    [IO.File]::WriteAllBytes($out, $buf)
    "wrote $out : $count nodes, $($buf.Length) bytes"
}

# ---- delta text format ----
# One operation per line, fields separated by '|' ('\|', '\\', '\n', '\r' escape inside a field):
#   node+|<path>|<type>|<cols>|<type string>|<after>      new node under the parent of <path>; <after> = sibling path, @top or @end
#   node-|<path>
#   types~|<path>|<type string>
#   shape~|<path>|<type>|<cols>|<type string>               node type or column count changed: rows are cleared and re-added, kids kept
#   row+|<path>|<after>|<key>|<cell>|<cell>...             <after> = key of the row to insert behind, @top or @end
#   row-|<path>|<key>
#   row~|<path>|<key>|c<i>=<cell>|c<j>=<cell>...
#   order|<path>|<key>|<key>...                             final row order of a node whose rows the target reorders
#   kids|<path>|<kid path>|<kid path>...                    final kid order of a node whose kids the target reorders
#   name~|<header name>
# <path> = node names from the root joined by '/'; the 2nd, 3rd... same-named sibling gets '#1', '#2'... appended.
# <key> = field name of a struct row, or the text of column 0 of a table row; when that text repeats inside the node
#         the key is text#<8 hex of the row's MD5>, and identical rows get a further '#n'.
# <cell> = s:text | u:123 | u:'FCC' | u:0x19430801 | a:1;2;3;4 | v:0.5;1 | f:0.5 | b:1 | k<kind>:hex;hex;hex;hex
function Delta-Esc([string]$s) { $s.Replace('\', '\\').Replace('|', '\|').Replace("`n", '\n').Replace("`r", '\r') }
function Delta-Split([string]$line) {
    $out = New-Object Collections.Generic.List[string]; $sb = New-Object Text.StringBuilder
    for ($i = 0; $i -lt $line.Length; $i++) {
        $ch = $line[$i]
        if ($ch -eq '\' -and $i + 1 -lt $line.Length) {
            $i++; $e = $line[$i]
            [void]$sb.Append($(switch ($e) { 'n' { "`n" } 'r' { "`r" } default { $e } }))
        } elseif ($ch -eq '|') { $out.Add($sb.ToString()); [void]$sb.Clear() }
        else { [void]$sb.Append($ch) }
    }
    $out.Add($sb.ToString()); ,$out
}
function Cell-Encode([hashtable]$cell) {
    $v = $cell.v
    switch ($cell.k) {
        2 { 's:' + (Delta-Esc $cell.s) }
        4 {
            $x = $v[0]
            if ((($x -shr 24) -ge 0x19) -and (($x -shr 24) -le 0x20) -and ((($x -shr 16) -band 0xff) -le 0x99)) { 'u:0x{0:x8}' -f $x }
            else { $fc = Azcf-Fourcc $x; if ($fc) { "u:'$fc'" } else { "u:$x" } }
        }
        6 { $n = 3; while ($n -gt 0 -and $v[$n] -eq 0) { $n-- }; 'a:' + ((0..$n | ForEach-Object { [string][BitConverter]::ToInt32([BitConverter]::GetBytes([uint32]$v[$_]), 0) }) -join ';') }
        1 { $n = 3; while ($n -gt 0 -and $v[$n] -eq 0) { $n-- }; 'v:' + ((0..$n | ForEach-Object { [BitConverter]::ToSingle([BitConverter]::GetBytes([uint32]$v[$_]), 0).ToString('R', $Inv) }) -join ';') }
        0 { 'f:' + [BitConverter]::ToSingle([BitConverter]::GetBytes([uint32]$v[0]), 0).ToString('R', $Inv) }
        5 { 'b:' + $(if ($v[0]) { '1' } else { '0' }) }
        default { 'k{0}:{1:x8};{2:x8};{3:x8};{4:x8}' -f $cell.k, $v[0], $v[1], $v[2], $v[3] }
    }
}
function Cell-Decode([string]$text) {
    $v = New-Object uint32[] 4
    if ($text -notmatch '^(s|u|a|v|f|b|k\d+):(.*)$') { throw "bad cell '$text'" }
    $t = $Matches[1]; $rest = $Matches[2]
    switch -Regex ($t) {
        '^s$' { return @{ k = 2; v = $v; s = $rest } }
        '^u$' {
            if ($rest -match "^'(.{2,4})'$") { $fc = $Matches[1]; for ($i = 0; $i -lt $fc.Length; $i++) { $v[0] = $v[0] -bor ([uint32][byte][char]$fc[$i] -shl (8 * $i)) } }
            elseif ($rest -match '^0x([0-9a-fA-F]+)$') { $v[0] = [Convert]::ToUInt32($Matches[1], 16) }
            else { $v[0] = [uint32]$rest }
            return @{ k = 4; v = $v; s = $null }
        }
        '^a$' { $p = $rest.Split(';'); for ($i = 0; $i -lt $p.Count; $i++) { $v[$i] = [BitConverter]::ToUInt32([BitConverter]::GetBytes([int32]$p[$i]), 0) }; return @{ k = 6; v = $v; s = $null } }
        '^v$' { $p = $rest.Split(';'); for ($i = 0; $i -lt $p.Count; $i++) { $v[$i] = [BitConverter]::ToUInt32([BitConverter]::GetBytes([single]::Parse($p[$i], $Inv)), 0) }; return @{ k = 1; v = $v; s = $null } }
        '^f$' { $v[0] = [BitConverter]::ToUInt32([BitConverter]::GetBytes([single]::Parse($rest, $Inv)), 0); return @{ k = 0; v = $v; s = $null } }
        '^b$' { $v[0] = [uint32]$rest; return @{ k = 5; v = $v; s = $null } }
        '^k(\d+)$' { $k = [uint32]$Matches[1]; $p = $rest.Split(';'); for ($i = 0; $i -lt 4; $i++) { $v[$i] = [Convert]::ToUInt32($p[$i], 16) }; return @{ k = $k; v = $v; s = $null } }
    }
}
function Azcf-Paths([object]$root) {
    # ordered map path -> @{ node; parent; path }, pre-order; '#n' suffix for repeated sibling names
    $out = New-Object Collections.Specialized.OrderedDictionary
    $stack = New-Object Collections.Generic.Stack[object]
    $stack.Push(@{ node = $root; parent = $null; path = '' })
    while ($stack.Count) {
        $e = $stack.Pop(); $out.Add($e.path, $e)
        $n = $e.node; $counts = @{}
        foreach ($k in $n.kids) { if ($counts.ContainsKey($k.name)) { $counts[$k.name]++ } else { $counts[$k.name] = 1 } }
        $seen = @{}
        $kidEntries = @()
        foreach ($k in $n.kids) {
            $nm = $k.name
            # first occurrence keeps the bare name, later ones get #1, #2 ... (stable when later duplicates come or go)
            if ($counts[$nm] -gt 1) { $ix = if ($seen.ContainsKey($nm)) { $seen[$nm] } else { 0 }; $seen[$nm] = $ix + 1; if ($ix) { $nm = "$nm#$ix" } }
            $kidEntries += @{ node = $k; parent = $n; path = $(if ($e.path) { $e.path + '/' + $nm } else { $nm }) }
        }
        for ($i = $kidEntries.Count - 1; $i -ge 0; $i--) { $stack.Push($kidEntries[$i]) }
    }
    $out
}
$Md5 = [Security.Cryptography.MD5]::Create()
function Azcf-RowKeys([object]$node) {
    # ordered list of row keys: struct = field name, table = column-0 text. When several rows share that text the
    # key gets '#' + 8 hex digits of the MD5 of the whole row, and identical rows get '#n' on top. Content keys stay
    # valid while other rows are inserted or removed; positional ones would not.
    $base = New-Object Collections.Generic.List[string]; $counts = @{}
    foreach ($row in $node.rows) {
        $k = if ($node.type -eq 1) { [string]$row.name } elseif ($row.c.Count -gt 0) { $c0 = $row.c[0]; if ($c0.k -eq 2) { $c0.s } else { Cell-Encode $c0 } } else { '' }
        $base.Add($k); if ($counts.ContainsKey($k)) { $counts[$k]++ } else { $counts[$k] = 1 }
    }
    $keys = New-Object Collections.Generic.List[string]; $seen = @{}
    for ($i = 0; $i -lt $base.Count; $i++) {
        $k = $base[$i]
        if ($counts[$k] -gt 1) {
            $h = $Md5.ComputeHash([Text.Encoding]::UTF8.GetBytes((Row-Line $node $node.rows[$i])))
            $k = $k + '#' + (($h[0..3] | ForEach-Object { '{0:x2}' -f $_ }) -join '')
            if ($seen.ContainsKey($k)) { $n = $seen[$k]; $seen[$k] = $n + 1; $k = "$k#$n" } else { $seen[$k] = 1 }
        }
        $keys.Add($k)
    }
    ,$keys
}
function Row-Hash([object]$node, [object]$row) { $h = $Md5.ComputeHash([Text.Encoding]::UTF8.GetBytes((Row-Line $node $row))); ($h[0..3] | ForEach-Object { '{0:x2}' -f $_ }) -join '' }
function Resolve-RowIndex([object]$node, [string]$key) {
    # Index of the row a delta line names, or -1. A key is matched exactly first; otherwise its bare text is matched
    # against column 0 (field name for structs): one candidate wins, several are told apart by the MD5 in the key.
    # Needed because the '#md5' suffix exists only while the text repeats, and a delta is applied step by step.
    $keys = Azcf-RowKeys $node
    $ix = $keys.IndexOf($key); if ($ix -ge 0) { return $ix }
    $bare = $key; $hash = ''
    if ($key -match '^(.*?)#([0-9a-f]{8})(#\d+)?$') { $bare = $Matches[1]; $hash = $Matches[2] }
    $cand = @()
    for ($i = 0; $i -lt $node.rows.Count; $i++) {
        $row = $node.rows[$i]
        $t = if ($node.type -eq 1) { [string]$row.name } elseif ($row.c.Count -gt 0) { $c0 = $row.c[0]; if ($c0.k -eq 2) { $c0.s } else { Cell-Encode $c0 } } else { '' }
        if ($t -eq $bare) { $cand += $i }
    }
    if ($cand.Count -eq 1) { return $cand[0] }
    if ($cand.Count -gt 1 -and $hash) { foreach ($i in $cand) { if ((Row-Hash $node $node.rows[$i]) -eq $hash) { return $i } } }
    -1
}
function Row-Line([object]$node, [object]$row) {
    if ($node.type -eq 1) { (Delta-Esc $row.name) + '|' + (Cell-Encode $row.c[0]) }
    else { ($row.c | ForEach-Object { Cell-Encode $_ }) -join '|' }
}
function Cmd-Diff([string]$aPath, [string]$bPath, [string]$out) {
    $A = Azcf-Load $aPath; $B = Azcf-Load $bPath
    $pa = Azcf-Paths $A.root; $pb = Azcf-Paths $B.root
    $lines = New-Object Collections.Generic.List[string]
    $lines.Add("# azcf delta  base=$(Split-Path $aPath -Leaf)  target=$(Split-Path $bPath -Leaf)  $(Get-Date -Format s)")
    $stats = @{ 'node+' = 0; 'node-' = 0; 'row+' = 0; 'row-' = 0; 'row~' = 0; 'types~' = 0; 'shape~' = 0; 'order' = 0; 'kids' = 0; 'name~' = 0 }
    foreach ($p in @($pa.Keys)[($pa.Count - 1)..0]) {   # last node first, so removing a duplicate never renames an earlier one
        if ($pb.Contains($p)) { continue }
        $parentPath = if ($p.Contains('/')) { $p.Substring(0, $p.LastIndexOf('/')) } else { '' }
        if ($parentPath -ne '' -and -not $pb.Contains($parentPath)) { continue }   # parent removed as a whole
        $lines.Add('node-|' + (Delta-Esc $p)); $stats['node-']++
    }
    foreach ($p in $pb.Keys) {
        if ($p -eq '') { continue }
        $eb = $pb[$p]; $nb = $eb.node
        $isNew = -not $pa.Contains($p)
        if (-not $isNew) {
            $na = $pa[$p].node
            if ($na.type -ne $nb.type -or $na.cols -ne $nb.cols) {
                # shape change: keep the node (and its kids), replace its rows wholesale
                $lines.Add('shape~|' + (Delta-Esc $p) + "|$($nb.type)|$($nb.cols)|" + (Delta-Esc $nb.types)); $stats['shape~']++
                $keys = Azcf-RowKeys $nb
                for ($r = 0; $r -lt $nb.rows.Count; $r++) { $lines.Add('row+|' + (Delta-Esc $p) + '|@end|' + (Delta-Esc $keys[$r]) + '|' + (Row-Line $nb $nb.rows[$r])); $stats['row+']++ }
                continue
            }
            elseif ($na.types -ne $nb.types) { $lines.Add('types~|' + (Delta-Esc $p) + '|' + (Delta-Esc $nb.types)); $stats['types~']++ }
        }
        if ($isNew) {
            # position among the parent's kids in B
            $parentNode = $eb.parent; $ix = $parentNode.kids.IndexOf($nb)
            $after = '@top'
            if ($ix -gt 0) {
                $parentPath = if ($p.Contains('/')) { $p.Substring(0, $p.LastIndexOf('/')) } else { '' }
                $sibPaths = @($pb.Keys | Where-Object { $_ -ne '' -and $(if ($_.Contains('/')) { $_.Substring(0, $_.LastIndexOf('/')) } else { '' }) -eq $parentPath })
                $after = $sibPaths[$ix - 1]
            }
            $lines.Add('node+|' + (Delta-Esc $p) + "|$($nb.type)|$($nb.cols)|" + (Delta-Esc $nb.types) + '|' + (Delta-Esc $after)); $stats['node+']++
            $keys = Azcf-RowKeys $nb
            for ($r = 0; $r -lt $nb.rows.Count; $r++) {
                $lines.Add('row+|' + (Delta-Esc $p) + '|@end|' + (Delta-Esc $keys[$r]) + '|' + (Row-Line $nb $nb.rows[$r])); $stats['row+']++
            }
            continue
        }
        $na = $pa[$p].node
        $ka = Azcf-RowKeys $na; $kb = Azcf-RowKeys $nb
        $ia = @{}; for ($r = 0; $r -lt $ka.Count; $r++) { $ia[$ka[$r]] = $r }
        $ib = @{}; for ($r = 0; $r -lt $kb.Count; $r++) { $ib[$kb[$r]] = $r }
        for ($r = $ka.Count - 1; $r -ge 0; $r--) { $k = $ka[$r]; if (-not $ib.ContainsKey($k)) { $lines.Add('row-|' + (Delta-Esc $p) + '|' + (Delta-Esc $k)); $stats['row-']++ } }
        $prevCommon = @(); foreach ($k in $ka) { if ($ib.ContainsKey($k)) { $prevCommon += $k } }
        $commonB = @(); foreach ($k in $kb) { if ($ia.ContainsKey($k)) { $commonB += $k } }
        $reorder = (($prevCommon -join "`0") -ne ($commonB -join "`0"))
        for ($r = 0; $r -lt $kb.Count; $r++) {
            $k = $kb[$r]; $rb = $nb.rows[$r]
            if (-not $ia.ContainsKey($k)) {
                $after = if ($r -eq 0) { '@top' } else { $kb[$r - 1] }
                $lines.Add('row+|' + (Delta-Esc $p) + '|' + (Delta-Esc $after) + '|' + (Delta-Esc $k) + '|' + (Row-Line $nb $rb)); $stats['row+']++
                continue
            }
            $ra = $na.rows[$ia[$k]]
            $ch = @()
            for ($j = 0; $j -lt $rb.c.Count; $j++) {
                $ea = Cell-Encode $ra.c[$j]; $ebb = Cell-Encode $rb.c[$j]
                if ($ea -ne $ebb) { $ch += "c$j=" + $ebb }
            }
            if ($ch.Count) { $lines.Add('row~|' + (Delta-Esc $p) + '|' + (Delta-Esc $k) + '|' + ($ch -join '|')); $stats['row~']++ }
        }
        if ($reorder) { $lines.Add('order|' + (Delta-Esc $p) + '|' + (($kb | ForEach-Object { Delta-Esc $_ }) -join '|')); $stats['order']++ }
    }
    # sibling order: for every node present in both files, compare the order of the kids they share
    foreach ($p in $pb.Keys) {
        if (-not $pa.Contains($p)) { continue }
        $kb = @($pb.Keys | Where-Object { $_ -ne '' -and $(if ($_.Contains('/')) { $_.Substring(0, $_.LastIndexOf('/')) } else { '' }) -eq $p })
        $ka = @($pa.Keys | Where-Object { $_ -ne '' -and $(if ($_.Contains('/')) { $_.Substring(0, $_.LastIndexOf('/')) } else { '' }) -eq $p })
        $cb = @($kb | Where-Object { $pa.Contains($_) }); $ca = @($ka | Where-Object { $pb.Contains($_) })
        if (($cb -join "`0") -ne ($ca -join "`0")) { $lines.Add('kids|' + (Delta-Esc $p) + '|' + (($kb | ForEach-Object { Delta-Esc $_ }) -join '|')); $stats['kids']++ }
    }
    if ($A.name -ne $B.name) { $lines.Add('name~|' + (Delta-Esc $B.name)); $stats['name~']++ }
    $summary = ($stats.Keys | Sort-Object | ForEach-Object { "$_=$($stats[$_])" }) -join ' '
    $lines.Insert(1, "# $summary")
    if ($out) { [IO.File]::WriteAllLines($out, $lines, (New-Object Text.UTF8Encoding $false)); "wrote $out : $summary" } else { $lines }
}
function Cmd-Apply([string]$basePath, [string]$deltaPath, [string]$out) {
    $doc = Azcf-Load $basePath
    $paths = Azcf-Paths $doc.root
    $n = 0
    foreach ($line in [IO.File]::ReadAllLines($deltaPath, (New-Object Text.UTF8Encoding $false))) {
        if ($line -eq '' -or $line.StartsWith('#')) { continue }
        $f = Delta-Split $line; $op = $f[0]
        if ($f.Count -lt 2) { throw "line $($n + 1): malformed '$line'" }
        $p = $f[1]
        if ($op -ne 'node+' -and $op -ne 'name~' -and -not $paths.Contains($p)) { throw "line $($n + 1): node '$p' not found" }
        try {
        switch ($op) {
            'name~' { $doc.name = $p }
            'kids' {
                $parent = $paths[$p].node
                $rank = New-Object int[] $parent.kids.Count
                for ($j = 0; $j -lt $rank.Count; $j++) { $rank[$j] = 1000000 + $j }
                for ($j = 2; $j -lt $f.Count; $j++) { if ($paths.Contains($f[$j])) { $ix = $parent.kids.IndexOf($paths[$f[$j]].node); if ($ix -ge 0) { $rank[$ix] = $j } } }
                $kids = New-Object Collections.Generic.List[object]
                foreach ($j in (0..($rank.Count - 1) | Sort-Object { $rank[$_] })) { $kids.Add($parent.kids[$j]) }
                $parent.kids.Clear(); $parent.kids.AddRange($kids)
                $paths = Azcf-Paths $doc.root
            }
            'order' {
                $node = $paths[$p].node
                $rank = New-Object int[] $node.rows.Count
                for ($j = 0; $j -lt $rank.Count; $j++) { $rank[$j] = 1000000 + $j }
                for ($j = 2; $j -lt $f.Count; $j++) { $ix = Resolve-RowIndex $node $f[$j]; if ($ix -ge 0) { $rank[$ix] = $j } }
                $rows = New-Object Collections.Generic.List[object]
                foreach ($j in (0..($rank.Count - 1) | Sort-Object { $rank[$_] })) { $rows.Add($node.rows[$j]) }
                $node.rows = $rows
            }
            'node+' {
                $parentPath = if ($p.Contains('/')) { $p.Substring(0, $p.LastIndexOf('/')) } else { '' }
                if (-not $paths.Contains($parentPath)) { throw "parent '$parentPath' not found for $p" }
                $parent = $paths[$parentPath].node
                $leaf = $p.Substring($parentPath.Length + $(if ($parentPath) { 1 } else { 0 })) -replace '#\d+$', ''
                $node = Azcf-NewNode $leaf ([int]$f[2]) ([int]$f[3]) $f[4]
                $after = $f[5]
                if ($after -eq '@top') { $parent.kids.Insert(0, $node) }
                elseif ($after -eq '@end') { $parent.kids.Add($node) }
                else { if (-not $paths.Contains($after)) { throw "sibling '$after' not found" }; $parent.kids.Insert($parent.kids.IndexOf($paths[$after].node) + 1, $node) }
                $paths = Azcf-Paths $doc.root
            }
            'node-' { $e = $paths[$p]; [void]$e.parent.kids.Remove($e.node); $paths = Azcf-Paths $doc.root }
            'types~' { $paths[$p].node.types = $f[2] }
            'shape~' { $node = $paths[$p].node; $node.type = [int]$f[2]; $node.cols = [int]$f[3]; $node.types = $f[4]; $node.rows.Clear() }
            'row+' {
                $node = $paths[$p].node; $after = $f[2]; $key = $f[3]
                $cells = @(); for ($j = 4; $j -lt $f.Count; $j++) { $cells += $f[$j] }
                if ($node.type -eq 1) { $row = @{ name = $cells[0]; c = @(Cell-Decode $cells[1]) } }
                else {
                    if ($cells.Count -ne $node.cols) { throw "line $($n + 1): $($cells.Count) cells for a $($node.cols)-column table" }
                    $row = @{ name = $null; c = @($cells | ForEach-Object { Cell-Decode $_ }) }
                }
                if ($after -eq '@end') { $node.rows.Add($row) }
                elseif ($after -eq '@top') { $node.rows.Insert(0, $row) }
                else { $ix = Resolve-RowIndex $node $after; if ($ix -lt 0) { throw "line $($n + 1): row '$after' not found in $p" }; $node.rows.Insert($ix + 1, $row) }
            }
            'row-' { $node = $paths[$p].node; $ix = Resolve-RowIndex $node $f[2]; if ($ix -lt 0) { throw "line $($n + 1): row '$($f[2])' not found in $p" }; $node.rows.RemoveAt($ix) }
            'row~' {
                $node = $paths[$p].node; $ix = Resolve-RowIndex $node $f[2]; if ($ix -lt 0) { throw "line $($n + 1): row '$($f[2])' not found in $p" }
                $row = $node.rows[$ix]
                for ($j = 3; $j -lt $f.Count; $j++) {
                    if ($f[$j] -notmatch '^c(\d+)=(.*)$') { throw "line $($n + 1): bad change '$($f[$j])'" }
                    $row.c[[int]$Matches[1]] = Cell-Decode $Matches[2]
                }
            }
            default { throw "line $($n + 1): unknown op '$op'" }
        }
        } catch { throw "delta line $($n + 1) ($op $p): $($_.Exception.Message)" }
        $n++
    }
    "applied $n operations"
    Azcf-Save $doc $out
}
function Cmd-Same([string]$aPath, [string]$bPath) {
    # node- and cell-level comparison; prints the first differences and a verdict
    $A = Azcf-Load $aPath; $B = Azcf-Load $bPath
    $pa = Azcf-Paths $A.root; $pb = Azcf-Paths $B.root
    $diff = New-Object Collections.Generic.List[string]
    foreach ($p in $pa.Keys) { if (-not $pb.Contains($p)) { $diff.Add("only in A: $p") } }
    foreach ($p in $pb.Keys) {
        if (-not $pa.Contains($p)) { $diff.Add("only in B: $p"); continue }
        $na = $pa[$p].node; $nb = $pb[$p].node
        if ($na.type -ne $nb.type -or $na.cols -ne $nb.cols -or $na.types -ne $nb.types) { $diff.Add("$p : shape differs"); continue }
        if ($na.rows.Count -ne $nb.rows.Count) { $diff.Add("$p : $($na.rows.Count) vs $($nb.rows.Count) rows"); continue }
        if ($na.kids.Count -ne $nb.kids.Count) { $diff.Add("$p : $($na.kids.Count) vs $($nb.kids.Count) kids") }
        for ($r = 0; $r -lt $na.rows.Count; $r++) {
            if ((Row-Line $na $na.rows[$r]) -ne (Row-Line $nb $nb.rows[$r])) { $diff.Add("$p row $r differs") }
        }
    }
    if ($A.name -ne $B.name) { $diff.Add("header name '$($A.name)' vs '$($B.name)'") }
    $diff | Select-Object -First 20
    if ($diff.Count) { "DIFFERENT: $($diff.Count) differences ($($pa.Count) vs $($pb.Count) nodes)" } else { "SAME: $($pa.Count) nodes, all rows and cells equal" }
}

switch ($Cmd) {
    'list'   { Cmd-List $Args[0] }
    'diff'   { Cmd-Diff $Args[0] $Args[1] $(if ($Args.Count -gt 2) { $Args[2] } else { '' }) }
    'apply'  { Cmd-Apply $Args[0] $Args[1] $Args[2] }
    'rewrite' { Azcf-Save (Azcf-Load $Args[0]) $Args[1] }
    'same'   { Cmd-Same $Args[0] $Args[1] }
    'unpack' { Cmd-Unpack $Args[0] $Args[1] }
    'pack'   { Cmd-Pack $Args[0] $Args[1] $(if ($Args.Count -gt 2) { $Args[2] } else { '' }) }
    'azcf'   { Cmd-Azcf $Args[0] }
    'nodes'  { if ($Args.Count -gt 1) { Cmd-Nodes $Args[0] ([int]$Args[1]) } else { Cmd-Nodes $Args[0] } }
    'csv'    { Cmd-Csv $Args[0] $Args[1] $(if ($Args.Count -gt 2) { $Args[2] } else { '' }) }
    'text'   { Cmd-Text $Args[0] $(if ($Args.Count -gt 1) { $Args[1] } else { '' }) }
    'desc'   { Cmd-Desc $Args[0] $Args[1] ($Args | Select-Object -Skip 2) }
    'gt3ext' { Cmd-Gt3ext $Args[0] $Args[1] }
    'lib'    { }   # dot-source the functions only:  . tools\gt3.ps1 lib   (used by tools\oob_17jul.ps1)
    default  { Get-Help $PSCommandPath -Detailed }
}
