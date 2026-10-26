<#
.SYNOPSIS
  Builds the Prokh polygon (7 x 5 cells, the Prokhorovka core block: Vasilyevka / the Psel bend - Prokhorovka station,
  Belenikhino - Hill 226.6) from the generated cell layers and installs it together with the operation into the
  installed overhaul add-on folder.

  What it writes (under <GameRoot>\data\common\mfo_overhaul\shared\):
    polygons\Prokh\Prokh.cfgpack, Prokh_cells.cfgpack, local\Prokh_text.loc_eng/loc_rus.textpack
    polygons\Prokh\<cell>_Prokh.polypack2 (35) + <cell>_prokh_ao.aomap (35)
    camps\1943_07_Kursk\07_10_Prokhorovka_GER.campack2 and _RUS.campack2 (the 30 July 1943 Stepanovka operation re-pointed
      at polygons\Prokh\Prokh.cfgpack with camp_area 3;1;9;5 - the vanilla Mius block geometry - and date 10 July 1943)
  Cell packs come from build\prokhorovka\cellsrc\<cell> (tools\gen_prokh.cmd); a cell without generated layers gets our
  hei_map + the Mius template layers as a placeholder.  The heightmaps in build\prokhorovka\cells keep the names of the
  11 x 12 DEM lattice: block cell (i, j) = lattice cell (i + 2, j + 4), e.g. MxD1 = MgF5, MgE2 = MgG6.
  -Clean removes everything it installed.
#>
param([string]$GameRoot = $env:GTMF_ROOT, [switch]$Clean, [string]$TemplateCell = 'MgG3', [int]$MaxCells = 999, [switch]$NoAo, [switch]$OpOnly, [switch]$KeepOob, [switch]$CellsOnly, [switch]$ReuseOob)
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
$build = Join-Path $repo 'build\prokhorovka'
New-Item -ItemType Directory -Force $build | Out-Null
Start-Transcript -Path (Join-Path $build 'build_prokh_transcript.txt') -Force | Out-Null
trap { "!! ERROR: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"; continue }
$addon = Join-Path $GameRoot 'data\common\mfo_overhaul\shared'
$polyOut = Join-Path $addon 'polygons\Prokh'
$campOut = Join-Path $addon 'camps\1943_07_Kursk'
if ($Clean) {
    if (Test-Path $polyOut) { Remove-Item $polyOut -Recurse -Force; "removed $polyOut" }
    if (Test-Path $campOut) { Remove-Item $campOut -Recurse -Force; "removed $campOut" }
    try { Stop-Transcript | Out-Null } catch {}; return
}
if (-not (Test-Path (Join-Path $GameRoot 'data\common\mfo_overhaul'))) { "!! the overhaul add-on is not installed under data\common\mfo_overhaul (install 0.5.13 first)"; try { Stop-Transcript | Out-Null } catch {}; return }
$src = Join-Path $repo 'docs\m12_terrain\prokh'          # descriptor, cells table, deltas (committed)
$cells = Join-Path $build 'cells'                          # generated hei_map files
New-Item -ItemType Directory -Force $polyOut, (Join-Path $polyOut 'local'), $campOut | Out-Null

# 1. descriptor, cells table, text packs
Copy-Item (Join-Path $src 'Prokh.cfgpack') (Join-Path $polyOut 'Prokh.cfgpack') -Force
Copy-Item (Join-Path $src 'Prokh_cells.cfgpack') (Join-Path $polyOut 'Prokh_cells.cfgpack') -Force
$miusPoly = Join-Path $GameRoot 'data\oprum\shared\polygons\6m_mius'
$genText = Join-Path $build 'cellsrc\Prokh_text.loc_eng.textpack'
if (Test-Path $genText) {
    Copy-Item $genText (Join-Path $polyOut 'local\Prokh_text.loc_eng.textpack') -Force
    Copy-Item (Join-Path $build 'cellsrc\Prokh_text.loc_rus.textpack') (Join-Path $polyOut 'local\Prokh_text.loc_rus.textpack') -Force
    "text packs: generated (place names from OSM)"
} else {
    Copy-Item (Join-Path $miusPoly 'local\6m_mius_text.loc_eng.textpack') (Join-Path $polyOut 'local\Prokh_text.loc_eng.textpack') -Force
    Copy-Item (Join-Path $miusPoly 'local\6m_mius_text.loc_rus.textpack') (Join-Path $polyOut 'local\Prokh_text.loc_rus.textpack') -Force
}
"descriptor, cells table and text packs installed"

# 2. template cell (placeholder layers)
$tplPack = Join-Path $GameRoot "users\modwork\_orig\polygons\6m_mius\${TemplateCell}_Mius.polypack2"
if (-not (Test-Path $tplPack)) { $tplPack = Join-Path $miusPoly "${TemplateCell}_Mius.polypack2" }
$tpl = Join-Path $build 'template'
if (-not (Test-Path (Join-Path $tpl '!flatlist'))) { & $gt3 unpack $tplPack $tpl }
$tplAo = Join-Path $miusPoly "$($TemplateCell.ToLower())_mius_ao.aomap"

# 3. one pack per cell
if ($OpOnly) { $MaxCells = 0; "-OpOnly: cell packs left as installed" }
$cols = 7; $rows = 5; $letters = @('D', 'E', 'F', 'G', 'H', 'I', 'J')
$oldLetters = @('D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N'); $blockI0 = 2; $blockJ0 = 4   # DEM lattice (11 x 12) indices of the block's NW cell
$n = 0; $t0 = Get-Date
for ($j = 0; $j -lt $rows; $j++) {
    for ($i = 0; $i -lt $cols; $i++) {
        if ($n -ge $MaxCells) { break }
        $border = ($i -eq 0 -or $j -eq 0 -or $i -eq $cols - 1 -or $j -eq $rows - 1)
        $cell = $(if ($border) { 'Mx' } else { 'Mg' }) + $letters[$i] + ($j + 1)
        $outPack = Join-Path $polyOut "${cell}_Prokh.polypack2"
        $genFlat = Join-Path $build "cellsrc\$cell\!flatlist"
        if ((Test-Path $outPack) -and -not ((Test-Path $genFlat) -and (Get-Item $genFlat).LastWriteTime -gt (Get-Item $outPack).LastWriteTime)) { $n++; continue }   # up to date
        $oi = $i + $blockI0; $oj = $j + $blockJ0
        $oldBorder = ($oi -eq 0 -or $oj -eq 0 -or $oi -eq 10 -or $oj -eq 11)
        $heiCell = $(if ($oldBorder) { 'Mx' } else { 'Mg' }) + $oldLetters[$oi] + ($oj + 1)
        $hei = Join-Path $cells "${heiCell}_hei_map.cell.loc_def.bin"
        if (-not (Test-Path $hei)) { $alt = Join-Path $cells ("$(if ($heiCell.StartsWith('Mx')) { 'Mg' } else { 'Mx' })$($heiCell.Substring(2))_hei_map.cell.loc_def.bin"); if (Test-Path $alt) { $hei = $alt } }
        if (-not (Test-Path $hei)) { "  missing $hei - skipped"; continue }
        $gen = Join-Path $build "cellsrc\$cell"      # full cell generated by tools\prokh_gen.py (all layers)
        if (Test-Path (Join-Path $gen '!flatlist')) { $work = $gen; $src = 'generated' }
        else {
            $work = Join-Path $build 'work'; $src = 'template+hei'
            if (Test-Path $work) { Remove-Item $work -Recurse -Force }
            New-Item -ItemType Directory -Force $work | Out-Null
            Copy-Item (Join-Path $tpl '*') $work -Force
            Copy-Item $hei (Join-Path $work 'hei_map.cell.loc_def.bin') -Force
        }
        $delta = Join-Path $work 'cell_desc.delta'
        $seed = Get-Random -Minimum 1000000 -Maximum 2000000000
        @("name~|${cell}_Prokh",
          "row~|i_polygen:polygen|is_cell_cap|c0=b:$(if ($border) { 1 } else { 0 })",
          "row~|i_polygen:polygen|arc|c0=s:${cell}_Prokh.polypack2",
          "row~|i_polygen:polygen|dist_desc|c0=s:..\\Prokh.cfgpack",
          "row~|i_polygen:polygen|cell_x|c0=u:$(3 + $i)",
          "row~|i_polygen:polygen|cell_y|c0=u:$(1 + $j)",
          "row~|i_polygen:polygen|seed|c0=u:$seed") | Set-Content $delta -Encoding ASCII
        & $gt3 apply (Join-Path $tpl 'cell_desc.cell.loc_def.bin') $delta (Join-Path $work 'cell_desc.cell.loc_def.bin') | Out-Null
        & $gt3 pack $outPack $work | Out-Null
        $genAo = Join-Path $gen 'ao.aomap'    # shadow map computed by tools\aomap.py for this cell; the template's only as a fallback
        if (Test-Path $genAo) { Copy-Item $genAo (Join-Path $polyOut "$($cell.ToLower())_prokh_ao.aomap") -Force }
        elseif (-not $NoAo) { Copy-Item $tplAo (Join-Path $polyOut "$($cell.ToLower())_prokh_ao.aomap") -Force }
        $n++
        "  $cell ($src) -> $outPack ($([Math]::Round((Get-Item $outPack).Length / 1MB)) MB)  $([int]((Get-Date) - $t0).TotalSeconds)s"
    }
}
if ($OpOnly) { "cell packs: untouched (-OpOnly), $((Get-ChildItem $polyOut -Filter *_Prokh.polypack2).Count) installed in $polyOut" } else { "$n cell packs installed in $polyOut" }
# stale packs of the earlier 11 x 12 block (names outside the 7 x 5 table) would only waste disk: remove them
$valid = @{}; foreach ($jj in 0..($rows - 1)) { foreach ($ii in 0..($cols - 1)) { $b = ($ii -eq 0 -or $jj -eq 0 -or $ii -eq $cols - 1 -or $jj -eq $rows - 1); $valid[($(if ($b) { 'Mx' } else { 'Mg' }) + $letters[$ii] + ($jj + 1)).ToLower()] = 1 } }
$stale = 0
foreach ($f in Get-ChildItem $polyOut -File) { if ($f.Name -match '^(M[gx][A-Z]\d+)_prokh(_ao\.aomap|\.polypack2)$' -and -not $valid.ContainsKey($Matches[1].ToLower())) { Remove-Item $f.FullName -Force; $stale++ } }
if ($stale) { "$stale stale cell files of the old 11 x 12 block removed" }

# 4. test operation: 30 July 1943 Stepanovka re-pointed at the new polygon
foreach ($side in @('GER', 'RUS')) {
    if ($CellsOnly) { '-CellsOnly: operation packs left as installed'; break }
    $vp = Join-Path $GameRoot "data\oprum\shared\camps\1943_07_Mius\07_30_Stepanovka_$side.campack2"
    if (-not (Test-Path $vp)) { "  missing $vp"; continue }
    $w = Join-Path $build "op_$side"
    $d = Join-Path $w 'desc.config.loc_def.bin'
    if ($ReuseOob -and ((Test-Path "$d.oob") -or ((Test-Path "$d.orig30") -and (Test-Path (Join-Path $w 'oob_12jul.delta'))))) {
        # -ReuseOob: keep the unpacked op dir and the 12 July OOB already computed there (desc.*.oob = the descriptor right
        # after the OOB step, else desc.*.orig30 + oob_12jul.delta (~30 min to re-apply), text packs, uids.csv); only the
        # operation body (prokh_op.py) is regenerated
        $t1 = Get-Date
        if (Test-Path "$d.oob") { Copy-Item "$d.oob" $d -Force; "  12 July OOB taken from op_$side\desc.config.loc_def.bin.oob" }
        else {
            & $gt3 apply "$d.orig30" (Join-Path $w 'oob_12jul.delta') "$d.new" | Out-Null
            Move-Item "$d.new" $d -Force; Copy-Item $d "$d.oob" -Force
            "  12 July OOB re-applied from op_$side\oob_12jul.delta ($([int]((Get-Date) - $t1).TotalSeconds)s)"
        }
        $KeepOob = $true
    } else {
    if (Test-Path $w) { Remove-Item $w -Recurse -Force }
    & $gt3 unpack $vp $w | Out-Null
    $delta = Join-Path $w 'desc.delta'
    @("row~|i_campgen:campgen|chap_id|c0=s:1943_07_Kursk",
      "row~|i_campgen:campgen|polygon|c0=s:polygons\\Prokh\\Prokh.cfgpack",
      "row~|i_campgen:campgen|camp_area|c0=a:3;1;9;5",
      "row~|i_campgen:campgen|date_beg|c0=u:0x19430710",
      "row~|i_campgen:campgen|time_beg|c0=u:1536",
      "row~|i_campgen:campgen|block_user_ctrl|c0=b:0",
      "row~|i_campgen:campgen|op_id|c0=s:07_10_Prokhorovka_$side",
      "row~|i_campgen:campgen|shared|c0=s:07_10_Prokhorovka_$side") | Set-Content $delta -Encoding ASCII
    & $gt3 apply $d $delta "$d.new" | Out-Null
    Move-Item "$d.new" $d -Force
    }
    # 4a. 12 July 1943 order of battle: formations cloned from the 30 July ones, Mius formations removed (tools\oob_12jul.ps1, ~5-10 min)
    if (-not $KeepOob) {
        $t1 = Get-Date
        & (Join-Path $PSScriptRoot 'oob_12jul.ps1') -OpDir $w -Quiet
        if (Test-Path (Join-Path $w 'oob_12jul_log.txt')) { "  12 July OOB written ($([int]((Get-Date) - $t1).TotalSeconds)s): $(Get-Content (Join-Path $w 'oob_12jul_log.txt') | Select-Object -Last 1)" }
        else { "  !! oob_12jul.ps1 did not finish - see op_$side\oob_12jul_live.txt:"; Get-Content (Join-Path $w 'oob_12jul_live.txt') -ErrorAction SilentlyContinue | Select-Object -Last 5 | ForEach-Object { "     $_" } }
        Copy-Item $d "$d.oob" -Force   # descriptor right after the OOB step: build_prokh_op_fast.cmd (-ReuseOob) starts from it
    }
    # 4b. operation body (movement graph, deployment, markers) regenerated for the 22 x 24 square area by tools\prokh_op.py
    $py = $null
    foreach ($c in @(@('py', '-3'), @('python'))) { try { $v = & $c[0] ($c[1..9] + @('-c', 'print(1)')) 2>$null; if ("$v" -eq '1') { $py = $c; break } } catch {} }
    $osm = Join-Path $repo 'docs\m12_terrain\osm\prokh.osm.json'
    if ($py -and (Test-Path $osm)) {
        foreach ($t in @('mg_nodes', 'plat_pos', 'tac_markers')) { & $gt3 csv $d $t (Join-Path $w "$t.csv") | Out-Null }
        $layout = Join-Path $repo 'docs\m11_prokhorovka\layout_10jul.json'
        if (-not (Test-Path (Join-Path $w 'uids.csv'))) { Copy-Item (Join-Path $repo 'docs\m11_prokhorovka\uids_07_30.csv') (Join-Path $w 'uids.csv') -Force }   # platoon name -> uid (30 July table when the OOB step was skipped)
        & $py[0] ($py[1..9] + @((Join-Path $PSScriptRoot 'prokh_op.py'), '--osm', $osm, '--cells', $cells, '--opdir', $w, '--layout', $layout))
        $body = Join-Path $w 'op_body.delta'
        if (Test-Path $body) {
            & $gt3 apply $d $body "$d.new" | Out-Null
            Move-Item "$d.new" $d -Force
            "  operation body regenerated (14 x 10 squares)"
        } else { "  !! prokh_op.py wrote no op_body.delta - the Stepanovka graph stays (battles only in the north-west)" }
    } else { "  (no Python 3 or no docs\m12_terrain\osm\prokh.osm.json: the Stepanovka operation body stays, battles only in the north-west)" }
    Get-ChildItem $campOut -Filter "07_1*_Prokhorovka_$side.campack2" -ErrorAction SilentlyContinue | Remove-Item -Force   # earlier names (07_12_...)
    $outOp = Join-Path $campOut "07_10_Prokhorovka_$side.campack2"
    & $gt3 pack $outOp $w | Out-Null
    "  operation $side -> $outOp"
}
"done. Start the game and look for a chapter '1943_07_Kursk' / operation 07_10_Prokhorovka in the operations list; if the game logs errors, out\common_engine.log and out\*.log under the game folder are the place to look. Run tools\build_prokh_clean.cmd to remove it all."
try { Stop-Transcript | Out-Null } catch {}
