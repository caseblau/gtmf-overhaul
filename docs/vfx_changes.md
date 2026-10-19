# VFX changes, vanilla vs current build

Generated 2026-10-15 16:43 from the pristine 3598 parts table and build\merge\mfo_vfx\parts (version 0.3.23).
Rows Toni (RBVFX Part 2) also changed are marked; his changes to rows the overhaul never touched are not listed.
Column meanings marked (hyp.) are inferred from vanilla usage, not documented. Colours are ARGB; alpha 0x00 = invisible.

| table | row | value | vanilla | now | who |
|---|---|---|---|---|---|
| pgens_desc | dust_shot | c5 particles per burst | 15 | 18 | overhaul |
| pgens_desc | smk_flare_black | c5 particles per burst | 1 | 0 | overhaul |
| pgens_desc | smoke_expl | c5 particles per burst | 15 | 12 | overhaul |
| pgens_desc | smoke_expl_big | c5 particles per burst | 20 | 12 | overhaul |
| pgens_desc | dirt_expl_sm | c5 particles per burst | 10 | 15 | overhaul |
| pgens_desc | dirt_expl | c5 particles per burst | 30 | 60 | overhaul |
| pgens_desc | dirt_expl_big | c5 particles per burst | 40 | 45 | overhaul |
| pgens_desc | ext_dirt_med | c5 particles per burst | 40 | 60 | overhaul |
| pgens_desc | ext_dirt_big | c5 particles per burst | 75 | 70 | overhaul |
| pgens_desc | dust_expl_sm | c1 ground flag | 1 | 0 | overhaul |
| pgens_desc | dust_expl_sm | c2 generator type | RND | BROB | overhaul |
| pgens_desc | dust_expl_sm | c5 particles per burst | 20 | 10 | overhaul |
| pgens_desc | dust_expl | c1 ground flag | 1 | 0 | overhaul |
| pgens_desc | dust_expl | c2 generator type | RND | BROB | overhaul |
| pgens_desc | dust_expl | c5 particles per burst | 30 | 14 | overhaul |
| pgens_desc | dust_expl_big | c1 ground flag | 1 | 0 | overhaul |
| pgens_desc | dust_expl_big | c2 generator type | RND | BROB | overhaul |
| pgens_desc | dust_expl_big | c5 particles per burst | 35 | 18 | overhaul |
| pgens_desc | ext_flare_obj | c5 particles per burst | 100 | 300 | Toni |
| pgens_desc | ext_flare_obj_sm | c5 particles per burst | 30 | 200 | Toni |
| pgens_desc | ext_flare_obj_bul | c5 particles per burst | 10 | 50 | Toni |
| parts_desc | flash_shot_sm | c9 start size (m) | 0.1;0.1 | 0.09;0.09 | Toni |
| parts_desc | flash_shot_sm | c10 end size (m) | 0.15;0.15 | 0.12;0.12 | Toni |
| parts_desc | dust_shot | c10 end size (m) | 8;8 | 9;9 | overhaul |
| parts_desc | dust_shot | c11 start colour ARGB | 0xFFF0F0F0;0x40B0B0B0 | 0xFFB8B898 | overhaul |
| parts_desc | dust_shot | c12 end colour ARGB | 0x00D0D0D0;0xFFF0F0F0 | 0x00B8B898 | overhaul |
| parts_desc | smoke_burn_air | c11 start colour ARGB | 0x90444050 | 0x00C0C0C0 | overhaul |
| parts_desc | smoke_burn_air | c12 end colour ARGB | 0x00C0C0C0;0x90545860 | 0x00C0C0C0;0x00C0C0C0 | overhaul |
| parts_desc | smoke_path | c11 start colour ARGB | 0xD0A0A0A0 | 0x00C0C0C0 | overhaul |
| parts_desc | smoke_path_sm | c11 start colour ARGB | 0xB0B0B0B0 | 0x00C0C0C0 | overhaul |
| parts_desc | smoke_path_sm | c12 end colour ARGB | 0x00D0D0D0 | 0x00C0C0C0 | overhaul |
| parts_desc | smoke_flare | c11 start colour ARGB | 0x60C0C0C0 | 0x00C0C0C0 | overhaul |
| parts_desc | smoke_flare | c12 end colour ARGB | 0x00F0F0F0 | 0x00C0C0C0 | overhaul |
| parts_desc | smoke_flare_black | c11 start colour ARGB | 0x80101010 | 0x00C0C0C0 | overhaul |
| parts_desc | smoke_flare_black | c12 end colour ARGB | 0x00303030;0x50202020 | 0x00C0C0C0;0x00C0C0C0 | overhaul |
| parts_desc | smoke_flare_black | c13 lifetime s; fade; ?; ? | 20;0.5;0.3;1.5 | 8;0.5;0.3;1.5 | overhaul |
| parts_desc | smoke_flare_black | c22 animation rate (hyp.) | 3.5 | 2 | overhaul |
| parts_desc | flash_sm | c9 start size (m) | 0.4;0.4 | 1.2;1.2 | overhaul |
| parts_desc | flash_sm | c13 lifetime s; fade; ?; ? | 0.3;0;0.5;2 | 0.12;0;0.5;2 | overhaul |
| parts_desc | flash_med | c9 start size (m) | 0.5;0.5 | 2;2 | overhaul |
| parts_desc | flash_med | c13 lifetime s; fade; ?; ? | 0.3;0;0.5;2 | 0.12;0;0.5;2 | overhaul |
| parts_desc | flash_big | c9 start size (m) | 0.7;0.7 | 4;4 | overhaul |
| parts_desc | flash_big | c13 lifetime s; fade; ?; ? | 0.35;0;0.5;2 | 0.14;0;0.5;2 | overhaul |
| parts_desc | smoke_bomb | c11 start colour ARGB | 0xFFA0A0A0 | 0xFF6A5848 | overhaul |
| parts_desc | ext_dirt | c11 start colour ARGB | 0xFF808080 | 0xFF46382A | overhaul |
| parts_desc | ext_dirt | c12 end colour ARGB | 0xFF606060 | 0xFF46382A | overhaul |
| parts_desc | ext_dirt | c14 speed factor (hyp.) | 0.25 | 0.5 | overhaul |
| parts_desc | dirt_expl | c9 start size (m) | 0.5;0.5 | 1;1 | overhaul |
| parts_desc | dirt_expl | c10 end size (m) | 8;8 | 10;10 | overhaul |
| parts_desc | dirt_expl | c11 start colour ARGB | 0xFF808080 | 0xFF3A2E22 | overhaul |
| parts_desc | dirt_expl | c12 end colour ARGB | 0x00808080 | 0x003A2E22 | overhaul |
| parts_desc | dirt_expl | c14 speed factor (hyp.) | 0.25 | 0.6 | overhaul |
| parts_desc | dirt_expl_big | c9 start size (m) | 1.5;1.5 | 2.5;2.5 | overhaul |
| parts_desc | dirt_expl_big | c10 end size (m) | 14;14 | 15;15 | overhaul |
| parts_desc | dirt_expl_big | c11 start colour ARGB | 0xFF808080 | 0xFF3A2E22 | overhaul |
| parts_desc | dirt_expl_big | c12 end colour ARGB | 0x00808080 | 0x003A2E22 | overhaul |
| parts_desc | dirt_expl_big | c14 speed factor (hyp.) | 0.25 | 0.5 | overhaul |
| parts_desc | dirt_bomb | c11 start colour ARGB | 0xFF808080 | 0xFF3A2E22 | overhaul |
| parts_desc | dirt_bomb | c12 end colour ARGB | 0x00808080 | 0x003A2E22 | overhaul |
| parts_desc | ext_dirt_sm | c11 start colour ARGB | 0xFFA0A0A0 | 0xFF46382A | overhaul |
| parts_desc | ext_dirt_sm | c12 end colour ARGB | 0xFF808080 | 0xFF46382A | overhaul |
| parts_desc | ext_dirt_sm | c14 speed factor (hyp.) | 0.25 | 0.5 | overhaul |
| parts_desc | smoke_expl | c11 start colour ARGB | 0xF0909090 | 0xF0786858 | overhaul |
| parts_desc | smoke_expl | c12 end colour ARGB | 0x00606060 | 0x00504840 | overhaul |
| parts_desc | smoke_expl | c13 lifetime s; fade; ?; ? | 12;0.5;0.05;0.15 | 10;0.5;0.05;0.15 | overhaul |
| parts_desc | smoke_expl_big | c11 start colour ARGB | 0xF0909090 | 0xF06A5848 | overhaul |
| parts_desc | smoke_expl_big | c12 end colour ARGB | 0x00606060 | 0x004A4038 | overhaul |
| parts_desc | smoke_expl_big | c13 lifetime s; fade; ?; ? | 14;0.5;0.05;0.2 | 12;0.5;0.05;0.2 | overhaul |
| parts_desc | dust_expl_rnd_sm | c6 | 0;-0.01 | 0;-0.05 | overhaul |
| parts_desc | dust_expl_rnd_sm | c9 start size (m) | 1;1 | 1.5;1.5 | overhaul |
| parts_desc | dust_expl_rnd_sm | c10 end size (m) | 8;8 | 9;9 | overhaul |
| parts_desc | dust_expl_rnd_sm | c11 start colour ARGB | 0xFFF0F0F0;0xA0B0B0B0 | 0xB0B8B898 | overhaul |
| parts_desc | dust_expl_rnd_sm | c12 end colour ARGB | 0x00D0D0D0 | 0x00B8B898 | overhaul |
| parts_desc | dust_expl_rnd_sm | c13 lifetime s; fade; ?; ? | 10;0.2;0.1;0.15 | 20;0.2;0.1;0.15 | overhaul |
| parts_desc | dust_expl_rnd_sm | c22 animation rate (hyp.) | 4 | 2 | overhaul |
| parts_desc | dust_expl_rnd | c6 | 0;-0.01 | 0;-0.05 | overhaul |
| parts_desc | dust_expl_rnd | c9 start size (m) | 1.5;1.5 | 2.5;2.5 | overhaul |
| parts_desc | dust_expl_rnd | c10 end size (m) | 14;14 | 16;16 | overhaul |
| parts_desc | dust_expl_rnd | c11 start colour ARGB | 0xFFF0F0F0;0xA0B0B0B0 | 0xB0B8B898 | overhaul |
| parts_desc | dust_expl_rnd | c12 end colour ARGB | 0x00D0D0D0 | 0x00B8B898 | overhaul |
| parts_desc | dust_expl_rnd | c13 lifetime s; fade; ?; ? | 12;0.2;0.1;0.3 | 30;0.2;0.1;0.3 | overhaul |
| parts_desc | dust_expl_rnd | c22 animation rate (hyp.) | 4 | 1.6 | overhaul |
| parts_desc | dust_expl_rnd_big | c6 | 0;-0.01 | 0;-0.05 | overhaul |
| parts_desc | dust_expl_rnd_big | c9 start size (m) | 2;2 | 3.5;3.5 | overhaul |
| parts_desc | dust_expl_rnd_big | c10 end size (m) | 18;18 | 20;20 | overhaul |
| parts_desc | dust_expl_rnd_big | c11 start colour ARGB | 0xFFF0F0F0;0xA0B0B0B0 | 0xB0B8B898 | overhaul |
| parts_desc | dust_expl_rnd_big | c12 end colour ARGB | 0x00D0D0D0 | 0x00B8B898 | overhaul |
| parts_desc | dust_expl_rnd_big | c13 lifetime s; fade; ?; ? | 12;0.2;0.1;0.6 | 35;0.2;0.1;0.6 | overhaul |
| parts_desc | dust_expl_rnd_big | c22 animation rate (hyp.) | 4 | 1.4 | overhaul |
| parts_desc | smk_air_red | c9 start size (m) | 2;2 | 1.5;1.5 | Toni |
| parts_desc | smk_air_red | c10 end size (m) | 7;7 | 4;4 | Toni |
| parts_desc | smk_air_red | c13 lifetime s; fade; ?; ? | 25;0;0.03;0.07 | 25;0.2;0.02;0.025 | Toni |
| parts_desc | smk_air_green | c9 start size (m) | 2;2 | 1.5;1.5 | Toni |
| parts_desc | smk_air_green | c10 end size (m) | 7;7 | 4;4 | Toni |
| parts_desc | smk_air_green | c13 lifetime s; fade; ?; ? | 25;0;0.03;0.07 | 25;0.2;0.02;0.025 | Toni |
| parts_desc | smk_air_yellow | c9 start size (m) | 2;2 | 1.5;1.5 | Toni |
| parts_desc | smk_air_yellow | c10 end size (m) | 7;7 | 4;4 | Toni |
| parts_desc | smk_air_yellow | c13 lifetime s; fade; ?; ? | 25;0;0.03;0.07 | 25;0.2;0.02;0.025 | Toni |
| parts_desc | smk_air_magenta | c9 start size (m) | 2;2 | 1.5;1.5 | Toni |
| parts_desc | smk_air_magenta | c10 end size (m) | 7;7 | 4;4 | Toni |
| parts_desc | smk_air_magenta | c13 lifetime s; fade; ?; ? | 25;0;0.03;0.07 | 25;0.2;0.02;0.025 | Toni |
| parts_desc | smk_air_orange | c9 start size (m) | 2;2 | 1.5;1.5 | Toni |
| parts_desc | smk_air_orange | c10 end size (m) | 7;7 | 4;4 | Toni |
| parts_desc | smk_air_orange | c13 lifetime s; fade; ?; ? | 25;0;0.03;0.07 | 25;0.2;0.02;0.025 | Toni |
| parts_desc | smk_air_blue | c9 start size (m) | 2;2 | 1.5;1.5 | Toni |
| parts_desc | smk_air_blue | c10 end size (m) | 7;7 | 4;4 | Toni |
| parts_desc | smk_air_blue | c13 lifetime s; fade; ?; ? | 25;0;0.03;0.07 | 25;0.2;0.02;0.025 | Toni |
| parts_desc | smoke_hit_sm | c13 lifetime s; fade; ?; ? | 8;0.3;0.05;0.1 | 8;0.1;0.05;0.1 | Toni |
| parts_desc | smoke_hit | c13 lifetime s; fade; ?; ? | 8;0.5;0.05;0.1 | 8;0.2;0.05;0.1 | Toni |
| parts_desc | ext_flare_hit | c9 start size (m) | 0.03;0.03 | 0.05;0.05 | Toni |
| parts_desc | ext_flare_hit | c10 end size (m) | 0.06;0.06 | 0.03;0.03 | Toni |
| parts_desc | ext_flare_hit | c11 start colour ARGB | 0xC0C07229;0xFFFFFFFF | 0xA0C07229 | Toni |
