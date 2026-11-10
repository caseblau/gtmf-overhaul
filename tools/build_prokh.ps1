<#
.SYNOPSIS
  Builds the Prokh polygon (9 x 9 cells since 2026-11-01 - the Prokhorovka core block plus two cells W, N and S: Vasilyevka / the Psel bend - Prokhorovka station,
  Belenikhino - Hill 226.6) from the generated cell layers and installs it together with the operation into the
  installed overhaul add-on folder.

  What it writes (under <GameRoot>\data\common\mfo_overhaul\shared\):
    polygons\Prokh\Prokh.cfgpack, Prokh_cells.cfgpack, local\Prokh_text.loc_eng/loc_rus.textpack
    polygons\Prokh\<cell>_Prokh.polypack2 (35) + <cell>_prokh_ao.aomap (35)
    camps\1943_07_Kursk\07_10_Prokhorovka_GER.campack2 and _RUS.campack2 (the 30 July 1943 Stepanovka operation re-pointed
      at polygons\Prokh\Prokh.cfgpack with camp_area 1;1;9;9 (11 x 11 cells table) - and date 10 July 1943)
  Cell packs come from build\prokhorovka\cellsrc\<cell> (tools\gen_prokh.cmd); a cell without generated layers gets our
  hei_map + the Mius template layers as a placeholder.  The heightmaps in build\prokhorovka\cells keep the names of the
  11 x 12 DEM lattice: block cell (i, j) = lattice cell (i + 2, j + 4), e.g. MxD1 = MgF5, MgE2 = MgG6.
  -Clean removes everything it installed.  -Placeholders builds every cell from the Mius template layers + its heightmap
  (a block-size / loading test, no generated terrain; parks build\prokhorovka\cellsrc as cellsrc_parked).
#>
param([string]$GameRoot = $env:GTMF_ROOT, [switch]$Clean, [string]$TemplateCell = 'MgG3', [int]$MaxCells = 999, [switch]$NoAo, [switch]$OpOnly, [switch]$KeepOob, [switch]$CellsOnly, [switch]$ReuseOob, [switch]$Placeholders)
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$gt3 = Join-Path $PSScriptRoot 'gt3.ps1'
if (-not $GameRoot) { $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front' }
$build = Join-Path $repo 'build\prokhorovka'
New-Item -ItemType Directory -Force $build | Out-Null
$tname = if ($CellsOnly) { 'build_prokh_cells_transcript.txt' } elseif ($OpOnly) { 'build_prokh_op_transcript.txt' } else { 'build_prokh_transcript.txt' }
try { Start-Transcript -Path (Join-Path $build $tname) -Force | Out-Null } catch { "(no transcript: $($_.Exception.Message))" }
trap { "!! ERROR: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"; continue }
$addon = Join-Path $GameRoot 'data\common\mfo_overhaul\shared'
$polyOut = Join-Path $addon 'polygons\Prokh'
$campOut = Join-Path $addon 'camps\1943_07_Kursk'
# the shorter operations built beside the 24-turn campaign (07_10): tag = op dir suffix (build\prokhorovka\op<tag>_<side>), layout = docs\m11_prokhorovka file
$extraOps = @(@{ id = '07_10_Komsomolets'; tag = '1011'; layout = 'layout_1011jul.json'; date = '10' }, @{ id = '07_12'; tag = '12'; layout = 'layout_12jul.json'; date = '12' })
# op ids: 07_10_Prokhorovka = the 24-turn campaign, 07_10_Komsomolets_<side> = 10-11 July (12 turns), 07_12_Prokhorovka_<side> = 12-13 July (12 turns)
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
if ($Placeholders) {   # block-size test: every cell from the template layers + its heightmap, ignoring build\prokhorovka\cellsrc and the installed packs
    Get-ChildItem $polyOut -File | Where-Object { $_.Name -match '_prokh(_ao\.aomap|\.polypack2)$' } | Remove-Item -Force
    $srcDir = Join-Path $build 'cellsrc'; $parked = Join-Path $build 'cellsrc_parked'
    if ((Test-Path $srcDir) -and -not (Test-Path $parked)) { Rename-Item $srcDir $parked; "-Placeholders: build\prokhorovka\cellsrc parked as cellsrc_parked (rename it back for the real cells)" }
    "-Placeholders: installed cell packs removed; all cells are built from the template layers + heightmaps"
}
$cols = 9; $rows = 9; $letters = @('D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L')   # the 9 x 9 block (2026-11-01)
$oldLetters = @('D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N'); $blockI0 = 0; $blockJ0 = 2   # DEM lattice (11 x 12) indices of the block's NW cell
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
          "row~|i_polygen:polygen|cell_x|c0=u:$(1 + $i)",
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
# stale packs of an earlier block (names outside the 9 x 9 table) would only waste disk: remove them
$valid = @{}; foreach ($jj in 0..($rows - 1)) { foreach ($ii in 0..($cols - 1)) { $b = ($ii -eq 0 -or $jj -eq 0 -or $ii -eq $cols - 1 -or $jj -eq $rows - 1); $valid[($(if ($b) { 'Mx' } else { 'Mg' }) + $letters[$ii] + ($jj + 1)).ToLower()] = 1 } }
$stale = 0
foreach ($f in Get-ChildItem $polyOut -File) { if ($f.Name -match '^(M[gx][A-Z]\d+)_prokh(_ao\.aomap|\.polypack2)$' -and -not $valid.ContainsKey($Matches[1].ToLower())) { Remove-Item $f.FullName -Force; $stale++ } }
if ($stale) { "$stale stale cell files of the old block removed" }

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
        # the saved descriptor carries the camp_area of the block it was made for: re-point it at the current block (the
        # 8 x 8 test crashed on load with the 7 x 5 area 3;1;9;5 still in it, 1 Nov)
        $delta = Join-Path $w 'area.delta'
        @("row~|i_campgen:campgen|polygon|c0=s:polygons\\Prokh\\Prokh.cfgpack", "row~|i_campgen:campgen|camp_area|c0=a:1;1;9;9") | Set-Content $delta -Encoding ASCII
        & $gt3 apply $d $delta "$d.new" | Out-Null
        Move-Item "$d.new" $d -Force
    } else {
    if (Test-Path $w) { Remove-Item $w -Recurse -Force }
    & $gt3 unpack $vp $w | Out-Null
    $delta = Join-Path $w 'desc.delta'
    @("row~|i_campgen:campgen|chap_id|c0=s:1943_07_Kursk",
      "row~|i_campgen:campgen|polygon|c0=s:polygons\\Prokh\\Prokh.cfgpack",
      "row~|i_campgen:campgen|camp_area|c0=a:1;1;9;9",
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
    foreach ($c in @(@('python'), @('py', '-3.12'), @('py', '-3'))) { try { $v = & $c[0] ($c[1..9] + @('-c', 'import numpy; print(1)')) 2>$null; if ("$v" -eq '1') { $py = $c; break } } catch {} }   # prokh_op.py needs numpy; the py launcher's default may lack it
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
            "  operation body regenerated (18 x 18 squares)"
        } else { "  !! prokh_op.py wrote no op_body.delta - the Stepanovka graph stays (battles only in the north-west)" }
    } else { "  (no Python 3 or no docs\m12_terrain\osm\prokh.osm.json: the Stepanovka operation body stays, battles only in the north-west)" }
    $outOp = Join-Path $campOut "07_10_Prokhorovka_$side.campack2"
    & $gt3 pack $outOp $w | Out-Null
    "  operation $side -> $outOp"
    # 4c. the shorter operations on the same map (docs\m11_prokhorovka\layout_<op>.json). date '10': the campaign's own OOB
    # (desc.*.oob) with the operation's id; date '12' (3 Nov): its own OOB step with the 06:00 12 July strengths
    # (oob_12jul.ps1 -Date 12, ~5-10 min, kept as op<tag>_<side>\desc.*.oob for -ReuseOob)
    if ($py -and (Test-Path $osm) -and (Test-Path "$d.oob")) {
        foreach ($op in $extraOps) {
            $w2 = Join-Path $build "op$($op.tag)_$side"; $d2 = Join-Path $w2 'desc.config.loc_def.bin'
            $opId = if ($op.id -match '_[A-Za-z]+$') { "$($op.id)_$side" } else { "$($op.id)_Prokhorovka_$side" }
            if ($op.date -eq '12') {
                if ($ReuseOob -and (Test-Path "$d2.oob")) { Copy-Item "$d2.oob" $d2 -Force; "  $opId : 12 July OOB taken from op$($op.tag)_$side\desc.config.loc_def.bin.oob" }
                else {
                    if (Test-Path $w2) { Remove-Item $w2 -Recurse -Force }
                    & $gt3 unpack $vp $w2 | Out-Null
                    $delta = Join-Path $w2 'desc.delta'
                    @("row~|i_campgen:campgen|chap_id|c0=s:1943_07_Kursk", "row~|i_campgen:campgen|polygon|c0=s:polygons\\Prokh\\Prokh.cfgpack",
                      "row~|i_campgen:campgen|camp_area|c0=a:1;1;9;9", "row~|i_campgen:campgen|date_beg|c0=u:0x19430712", "row~|i_campgen:campgen|time_beg|c0=u:1536",
                      "row~|i_campgen:campgen|block_user_ctrl|c0=b:0") | Set-Content $delta -Encoding ASCII
                    & $gt3 apply $d2 $delta "$d2.new" | Out-Null; Move-Item "$d2.new" $d2 -Force
                    $t1 = Get-Date
                    & (Join-Path $PSScriptRoot 'oob_12jul.ps1') -OpDir $w2 -Quiet -Date 12
                    if (Test-Path (Join-Path $w2 'oob_12jul_log.txt')) { "  $opId : 12 July OOB with the 12 July strengths written ($([int]((Get-Date) - $t1).TotalSeconds)s)" }
                    else { "  !! oob_12jul.ps1 -Date 12 did not finish - see op$($op.tag)_$side\oob_12jul_live.txt"; continue }
                    Copy-Item $d2 "$d2.oob" -Force
                }
            } else {
                if (Test-Path $w2) { Remove-Item $w2 -Recurse -Force }
                New-Item -ItemType Directory $w2 | Out-Null
                foreach ($f in Get-ChildItem $w -File) {   # text packs (their .orig), uids.csv, the script pack original
                    if ($f.Name -match '^(desc\.config\.loc_def\.bin.*|op_body\.delta|op_unassigned\.txt|.*\.delta|.*\.csv)$' -and $f.Name -ne 'uids.csv') { continue }
                    Copy-Item $f.FullName (Join-Path $w2 $f.Name) -Force
                }
                foreach ($f in Get-ChildItem $w2 -File -Filter 'text.text.*.bin.orig') { Copy-Item $f.FullName ($f.FullName -replace '\.orig$', '') -Force }
                if (Test-Path (Join-Path $w2 'scripts.script.loc_def.bin.orig30')) { Copy-Item (Join-Path $w2 'scripts.script.loc_def.bin.orig30') (Join-Path $w2 'scripts.script.loc_def.bin') -Force }
                Copy-Item "$d.oob" $d2 -Force
            }
            $delta = Join-Path $w2 'id.delta'
            @("row~|i_campgen:campgen|polygon|c0=s:polygons\\Prokh\\Prokh.cfgpack", "row~|i_campgen:campgen|camp_area|c0=a:1;1;9;9",
              "row~|i_campgen:campgen|op_id|c0=s:$opId", "row~|i_campgen:campgen|shared|c0=s:$opId") | Set-Content $delta -Encoding ASCII
            & $gt3 apply $d2 $delta "$d2.new" | Out-Null; Move-Item "$d2.new" $d2 -Force
            foreach ($t in @('mg_nodes', 'plat_pos', 'tac_markers')) { & $gt3 csv $d2 $t (Join-Path $w2 "$t.csv") | Out-Null }
            $layout2 = Join-Path $repo "docs\m11_prokhorovka\$($op.layout)"
            & $py[0] ($py[1..9] + @((Join-Path $PSScriptRoot 'prokh_op.py'), '--osm', $osm, '--cells', $cells, '--opdir', $w2, '--layout', $layout2))
            $body2 = Join-Path $w2 'op_body.delta'
            if (Test-Path $body2) {
                & $gt3 apply $d2 $body2 "$d2.new" | Out-Null; Move-Item "$d2.new" $d2 -Force
                $outOp2 = Join-Path $campOut "$opId.campack2"
                & $gt3 pack $outOp2 $w2 | Out-Null
                "  operation $opId -> $outOp2"
            } else { "  !! prokh_op.py wrote no op_body.delta for $opId - operation skipped" }
        }
    }
}
"done. Start the game and look for the chapter '1943_07_Kursk' / operations 07_10_Prokhorovka (10-13 July), 07_10_Komsomolets (10-11 July) and 07_12_Prokhorovka (12-13 July) in the operations list; if the game logs errors, out\common_engine.log and out\*.log under the game folder are the place to look. Run tools\build_prokh_clean.cmd to remove it all."
try { Stop-Transcript | Out-Null } catch {}
