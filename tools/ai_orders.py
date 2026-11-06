r"""Operational AI orders of the Prokhorovka operation, one list per turn (4 h turns from 06:00 10 July 1943).

The engine runs the turn_NN script function at the start of each turn and executes order(kind, ai_id, x, y) for every
formation whose desc 'ai' field is that fourcc id and is not USER (the player's side is USER, so the same pack serves
the German and the Soviet operation - orders for the player's own formations are ignored). kind: 'attack' - the AI
group pushes on the square, 'recon' - probes / holds the line facing it, 'move' - relocates. x, y = op-map square
(1024 m), x east from the west edge, y south from the north edge of the old 7 x 5 frame (0..13, 0..9; briefing.py adds SQ_DX, SQ_DY = 4, 4 for the 9 x 9 block, so -4..13 / -4..13 are valid) - the vanilla Stepanovka pack uses the
same frame (G128 west of the Mius attacking east to x 7). Ids are set in tools/oob_12jul.ps1 ($AI table).

Squares: Kozlovka / Krasny Oktyabr crossing (1,2), Vasilyevka (2,3), Andreyevka - Mikhailovka (4-5,2), 226.6 (2,1),
Prelestnoye (6,2), Oktyabrsky sovkhoz (8,4), 252.2 (8-9,3), Komsomolets sovkhoz (4,7), 241.6 (5,6), Storozhevoye
(7,7), Ivanovsky Vyselok (4,9), 258.2 (2,9), Teterevino (1,9), Yasnaya Polyana (5,9), Prokhorovka station (11,2); 9 x 9 block: Belenikhino (5,12), Vinogradovka (7,10), Kalinin (-2,12), Krasny Oktyabr (-1,2), Veselyi (-1,-1), Polezhayev (4,0), Petrovka (6,0).
Sources: Zamulin ch. 5-9 (10-13 July), Lawrence ch. 7-9, the II SS Pz Corps / 5 gds TA orders quoted there.
"""

# ---- German ids (LSSAH set by oob_12jul.ps1; DR / TK keep the vanilla ones)
L2, L1, LT, LS, LA, LAR = 'L2', 'L1', 'LT', 'LS', 'LA', 'LAR'      # 2 / 1 PzGr Rgt, Pz Rgt, StuG, Pz Jg, AR
DL, DF, DRT, ST2 = 'DL', 'DF', 'DRT', 'ST2'                                   # DR Deutschland, Der Fuehrer, Pz Rgt, StuG
EIC, TUL, TKT, ST3 = 'EIC', 'TUL', 'TKT', 'ST3'                               # TK 6 MIR Eicke, 5 MIR Thule, Pz Rgt, StuG
# ---- Soviet ids
B99, B26, B169, M58, M11, R15 = 'B99', 'B26', 'B169', 'M58', 'M11', 'R15'     # 2 TC
R227, R285, R295 = 'R227', 'R285', 'R295'                                     # 183 RD (285 / 295 RR get no orders on 10 July: the standing HOLD keeps them in their trenches - user, 26 Oct)
R151, R153, R155, R245 = 'R151', 'R153', 'R155', 'R245'                       # 52 gds RD, 245 TR
R23, R26, R28 = 'R23', 'R26', 'R28'                                           # 9 gds AB Div
R284, R287, R290 = 'R284', 'R287', 'R290'                                     # 95 gds RD
R127, R132, R136 = 'R127', 'R132', 'R136'                                     # 42 gds RD
B110, B170, B181, M32, R36 = 'B110', 'B170', 'B181', 'M32', 'R36'             # 18 TC
B25, B31, B32, M53, S146 = 'B25', 'B31', 'B32', 'M53', 'S146'                 # 29 TC
B4G, B25G, B26G, M4G, R47 = 'B4G', 'B25G', 'B26G', 'M4G', 'R47'               # 2 gds TC
B10G, R51, B24G, S147 = 'B10G', 'R51', 'B24G', 'S147'   # 5 gds MC (11 / 12 gds MBde left out - sent south on 12 July)
D97 = 'D97'
D93, R278, R281, R28G = 'D93', 'R278', 'R281', 'R28G'                         # 93 gds RD (69 A) - Leski / Shakhovo from the night of 11/12 July
R15, M58, R47, R245, R155 = 'R15', 'M58', 'R47', 'R245', 'R155'
S146, S152, R36, M32, R53, R148 = 'S146', 'S152', 'R36', 'M32', 'R53', 'R148'

A, R, M = 'attack', 'recon', 'move'

ORDERS = {
    # ---------------- 10 July
    1: [  # 06:00 LSSAH on Komsomolets, Deutschland on Ivanovsky Vyselok, Totenkopf at Kozlovka
        (A, L2, 4, 7), (A, LT, 4, 7), (A, LS, 4, 6), (A, DL, 4, 9), (A, ST2, 4, 9), (A, EIC, 2, 3), (A, TKT, 2, 4), (A, TUL, 1, 2),
        (A, B99, 2, 3), (R, B26, 6, 5), (R, B169, 7, 6), (R, R151, 1, 1), (R, R153, 2, 1), (R, M11, 4, 1)],
    2: [  # 10:00 the Komsomolets attack (10:45), Kozlovka assault group thrown back by 99 TBde
        (A, L2, 5, 6), (A, LT, 5, 6), (A, LS, 5, 7), (A, DL, 5, 8), (A, DRT, 5, 9), (A, EIC, 2, 3), (A, TKT, 2, 3), (A, TUL, 1, 2),
        (A, B99, 2, 3), (A, B169, 5, 7), (R, B26, 6, 5)],
    3: [  # 14:00 Komsomolets taken, 285 RR back to Ivanovsky Vyselok - Storozhevoye wood, 169 TBde counter-attacks
        (A, L2, 6, 5), (A, LT, 6, 5), (A, LS, 5, 6), (A, DL, 5, 8), (A, DRT, 6, 8), (A, EIC, 2, 2), (A, TKT, 2, 3), (A, TUL, 1, 1),
        (A, B169, 5, 7), (A, B26, 6, 5), (R, B99, 2, 3), (R, R151, 1, 1)],
    4: [  # 18:00 LSSAH at 241.6, Totenkopf bridgehead at Klyuchi
        (A, L2, 6, 4), (A, LT, 6, 5), (A, LS, 6, 5), (A, DL, 6, 7), (A, DRT, 6, 8), (A, EIC, 3, 2), (A, TKT, 2, 2), (A, TUL, 2, 1),
        (R, B169, 7, 6), (R, B26, 7, 5), (A, B99, 2, 2), (R, R151, 2, 1), (R, R153, 3, 1)],
    5: [(R, L2, 6, 4), (R, DL, 6, 7), (R, TUL, 2, 1), (R, EIC, 3, 2), (R, B169, 7, 6), (R, R227, 7, 10)],   # 22:00
    6: [(R, L2, 6, 4), (R, DL, 6, 7), (R, TUL, 2, 1), (R, EIC, 3, 2), (R, R227, 7, 10), (R, R23, 9, 3), (R, R26, 9, 4), (R, R28, 8, 5)],   # 02:00
    # ---------------- 11 July
    7: [  # 06:00 LSSAH on Oktyabrsky and 252.2 (9 gds AB Div), DR on Storozhevoye, Totenkopf on 226.6
        (A, L2, 8, 4), (A, LT, 8, 4), (A, LS, 7, 4), (A, L1, 7, 5), (A, DL, 7, 7), (A, DRT, 7, 7), (A, DF, 5, 11), (A, ST2, 7, 8), (A, TUL, 3, 1), (A, EIC, 3, 2), (A, TKT, 3, 1),
        (R, R23, 9, 3), (R, R26, 9, 4), (R, R28, 8, 5), (A, B169, 7, 6), (A, B26, 8, 6), (R, R227, 7, 10), (R, R285, 7, 8), (A, R284, 3, 1), (A, R287, 4, 1), (R, R151, 2, 1), (R, R153, 3, 1)],
    8: [(A, L2, 9, 4), (A, LT, 9, 4), (A, LS, 8, 4), (A, L1, 8, 5), (A, DL, 7, 7), (A, DRT, 8, 7), (A, DF, 5, 11), (A, TUL, 4, 1), (A, TKT, 4, 1), (A, EIC, 4, 2),   # 10:00
        (R, R23, 9, 3), (R, R26, 9, 4), (A, B169, 7, 6), (A, B26, 8, 6), (R, R227, 7, 10), (A, R284, 3, 1), (A, R287, 4, 1), (A, R290, 4, 1)],
    9: [(A, L2, 9, 3), (A, LT, 10, 3), (A, LS, 9, 3), (A, L1, 8, 5), (A, DL, 8, 6), (A, DRT, 8, 7), (A, DF, 5, 11), (A, TUL, 5, 1), (A, TKT, 5, 1), (A, EIC, 4, 2),   # 14:00 252.2 and the sovkhoz fall
        (R, R23, 10, 3), (R, R26, 10, 4), (R, R28, 9, 5), (A, B169, 8, 6), (R, B26, 8, 6), (R, R227, 7, 10), (A, R284, 4, 1), (A, R290, 4, 1), (R, R127, 7, 2)],
    10: [(R, L2, 10, 3), (R, LT, 10, 3), (R, L1, 8, 5), (A, DL, 8, 6), (A, DRT, 8, 7), (A, DF, 5, 11), (A, TUL, 5, 1), (A, TKT, 5, 1), (R, EIC, 4, 2),   # 18:00
         (R, R23, 10, 3), (R, R26, 10, 4), (R, R28, 9, 5), (R, B169, 8, 6), (R, R227, 7, 10), (R, R284, 4, 1), (R, R127, 7, 2), (R, R132, 8, 2)],
    11: [(R, L2, 10, 3), (R, L1, 8, 5), (R, DL, 8, 6), (R, DF, 5, 11), (R, TUL, 6, 1), (M, ST3, 3, 2), (R, R23, 10, 3), (R, R28, 9, 5), (M, B181, 7, 2), (M, B170, 8, 2), (M, B32, 10, 4), (M, B31, 10, 4), (M, B25, 9, 6)],   # 22:00
    12: [(R, L2, 10, 3), (R, L1, 8, 5), (R, DL, 8, 6), (R, DF, 5, 11), (R, TUL, 6, 1), (R, EIC, 5, 2), (R, R23, 10, 3), (R, R26, 10, 4), (R, B4G, 5, 12), (R, B25G, 6, 11), (R, B26G, 7, 12), (M, B24G, 11, 6), (M, B10G, 11, 7)],   # 02:00
    # ---------------- 12 July
    13: [  # 06:00 (the Soviet counter-attack opens 08:30): 18 TC along the Psel, 29 TC on 252.2 - Oktyabrsky, 2 gds TC on Yasnaya Polyana; Totenkopf out of the bridgehead
        (R, L2, 10, 3), (R, LT, 10, 3), (R, LS, 9, 3), (A, L1, 7, 7), (A, DL, 8, 7), (A, DF, 7, 10), (A, DRT, 8, 8), (A, ST2, 8, 8), (A, TKT, 6, 1), (A, TUL, 6, 1), (A, EIC, 5, 1), (A, ST3, 6, 1),
        (A, B181, 6, 2), (A, B170, 7, 3), (A, B110, 8, 3), (A, R36, 8, 2), (A, M32, 7, 3), (A, B32, 9, 4), (A, B31, 8, 4), (A, B25, 7, 6), (A, S146, 9, 4), (A, M53, 8, 5),
        (A, B4G, 5, 11), (A, B25G, 4, 11), (A, B26G, 5, 12), (A, M4G, 5, 11), (A, B169, 7, 7), (A, B26, 7, 6), (A, R127, 8, 3), (A, R132, 8, 3), (A, R136, 9, 4), (A, R23, 9, 3), (A, R26, 9, 4), (A, R28, 8, 5),
        (A, R284, 4, 1), (A, R287, 4, 1), (A, R290, 5, 1), (A, R151, 3, 1), (R, B24G, 11, 6), (R, B10G, 11, 7)],
    14: [  # 10:00 the field between the sovkhoz and the ditch; LSSAH panzers counter-attack at midday
        (A, LT, 10, 3), (A, L2, 10, 3), (A, LS, 9, 4), (A, L1, 7, 7), (A, DL, 8, 7), (A, DF, 7, 10), (A, DRT, 8, 8), (A, TKT, 7, 1), (A, TUL, 7, 1), (A, EIC, 6, 1), (A, ST3, 7, 1),
        (A, B181, 5, 2), (A, B170, 6, 2), (A, B110, 7, 3), (A, R36, 7, 2), (A, B32, 8, 4), (A, B31, 7, 4), (A, B25, 6, 7), (A, S146, 8, 4), (A, M53, 8, 5),
        (A, B4G, 4, 11), (A, B25G, 4, 11), (A, B26G, 5, 12), (A, B169, 7, 7), (A, B26, 7, 6), (A, R127, 8, 3), (A, R132, 7, 3), (A, R23, 9, 3), (A, R26, 9, 4), (A, R284, 4, 1), (A, R290, 5, 1), (A, D97, 5, 1)],
    15: [  # 14:00 Storozhevoye lost, Totenkopf on the Kartashevka road; thunderstorm
        (R, L2, 10, 3), (A, LT, 10, 4), (R, L1, 7, 7), (A, DL, 8, 7), (A, DF, 7, 10), (A, DRT, 8, 8), (A, TKT, 8, 1), (A, TUL, 8, 1), (A, EIC, 6, 1),
        (A, B181, 5, 2), (A, B170, 6, 2), (R, B110, 7, 3), (A, B32, 8, 4), (R, B31, 8, 4), (A, B25, 7, 7), (A, M53, 8, 6), (A, B4G, 5, 11), (A, B26G, 5, 12), (A, B169, 7, 7), (A, R51, 7, 7), (A, R51, 7, 6), (A, B24G, 7, 2), (A, B10G, 7, 1), (A, R284, 5, 1), (A, D97, 5, 1)],
    16: [(R, L2, 10, 3), (R, LT, 10, 4), (R, DL, 8, 7), (R, DF, 7, 10), (R, TKT, 8, 1), (R, TUL, 8, 1), (R, EIC, 6, 1),   # 18:00 both sides dig in
         (R, B181, 5, 2), (R, B170, 6, 2), (R, B32, 9, 4), (R, B31, 9, 4), (R, B25, 7, 7), (R, B4G, 5, 12), (R, B26G, 6, 12), (R, B169, 7, 7), (A, B24G, 7, 1), (A, B10G, 7, 1), (R, R284, 5, 1), (R, D97, 5, 1)],
    17: [(R, L2, 10, 3), (R, DL, 8, 7), (R, TUL, 8, 1), (R, B181, 5, 2), (R, B32, 9, 4), (R, B25, 7, 7), (R, B4G, 5, 12), (R, B24G, 7, 1)],   # 22:00
    18: [(R, L2, 10, 3), (R, DL, 8, 7), (R, TUL, 8, 1), (R, B181, 5, 2), (R, B32, 9, 4), (R, B25, 7, 7), (R, B4G, 5, 12), (R, B24G, 7, 1), (R, B10G, 7, 1)],   # 02:00
    # ---------------- 13 July: Totenkopf gives up the Kartashevka road, Das Reich pushes south on Belenikhino, the Soviets hold
    19: [(R, L2, 10, 3), (R, LT, 10, 4), (A, DL, 8, 8), (A, DF, 6, 12), (A, DRT, 8, 9), (M, TKT, 5, 1), (R, TUL, 6, 1), (R, EIC, 5, 1),
         (R, B181, 5, 2), (R, B170, 6, 2), (R, B32, 9, 4), (R, B31, 9, 4), (R, B25, 7, 7), (R, B4G, 5, 12), (R, B26G, 6, 12), (A, B169, 7, 7), (A, B24G, 6, 1), (A, B10G, 6, 1), (A, R284, 5, 1), (A, R290, 5, 1), (A, D97, 5, 1)],
    20: [(R, L2, 10, 3), (A, DL, 8, 8), (A, DF, 6, 12), (A, DRT, 8, 9), (M, TKT, 3, 2), (M, TUL, 4, 1), (R, EIC, 4, 2),
         (R, B181, 5, 2), (R, B32, 9, 4), (R, B25, 7, 7), (R, B4G, 5, 12), (R, B26G, 6, 12), (A, B24G, 5, 1), (A, B10G, 5, 1), (A, R284, 4, 1), (A, D97, 4, 1)],
    21: [(R, L2, 10, 3), (R, DL, 8, 8), (R, DF, 6, 12), (M, TKT, 2, 2), (M, TUL, 3, 1), (R, EIC, 3, 2), (R, B181, 5, 2), (R, B32, 9, 4), (R, B25, 7, 7), (R, B4G, 5, 12), (A, B24G, 4, 1), (A, R284, 4, 1)],
    22: [(R, L2, 10, 3), (R, DL, 8, 8), (R, DF, 6, 12), (R, TKT, 2, 2), (R, TUL, 2, 1), (R, EIC, 3, 2), (R, B181, 5, 2), (R, B32, 9, 4), (R, B25, 7, 7), (R, B4G, 5, 12), (R, B24G, 4, 1), (R, R284, 4, 1)],
    23: [(R, L2, 10, 3), (R, DL, 8, 8), (R, DF, 6, 12), (R, TUL, 2, 1), (R, B181, 5, 2), (R, B32, 9, 4), (R, B25, 7, 7), (R, B24G, 4, 1)],
    24: [(R, L2, 10, 3), (R, DL, 8, 8), (R, DF, 6, 12), (R, TUL, 2, 1), (R, B181, 5, 2), (R, B32, 9, 4), (R, B25, 7, 7), (R, B24G, 4, 1)],
}


# ---------------------------------------------------------------- 3 Nov (user: "fill the gaps in the AI orders")
# Every manoeuvre formation on the map now has an order in every turn it is there; where the sources give no move, a
# 'recon' on the ground it held (= hold and probe there). Positions are the 10 July / 12 July layout positions in squares
# of the old 7 x 5 frame (briefing.py adds SQ_DX / SQ_DY). Only turns without an order for that formation are filled.
# 1 SS-PzGr (L1) re-aimed: along the railway to svkh. Stalinskoye on 11 July (7-9), Storozhevoye on the morning of 12 July
# (13-14) - Zamulin ch. 7 / 9; the earlier rows sent it to the Psel at Prelestnoye, where 2 SS-PzGr and the recon bn fought.
FILL = [   # (ai id, first turn, last turn, kind, x, y, note)
    (M11, 2, 3, R, 2, 1, '11 MRBr: 3 bn on 226.6, 1 / 2 bns Vasilyevka'), (M11, 4, 4, A, 0, 1, '21:00 10 July counter-attack on the Klyuchi bridgehead with 52 gds RD'),
    (M11, 5, 24, R, 2, 1, '226.6 and the Andreyevka bridges until 12 July'),
    (R155, 1, 3, R, 1, 1, '155 gds RR between 226.6 and the grove SE of Klyuchi'), (R155, 4, 4, A, 0, 1, '21:00 counter-attack (training bn + 245 TR company)'),
    (R155, 5, 24, R, 2, 0, 'north of 226.6 after the bridgehead grew'),
    (R245, 1, 3, R, 2, 0, '245 TR tank company with 52 gds RD'), (R245, 4, 4, A, 0, 1, '21:00 counter-attack on the bridgehead'), (R245, 5, 24, R, 2, 0, ''),
    (R151, 1, 24, R, 0, 0, '151 gds RR at Veselyi'), (R153, 1, 24, R, 3, 0, '153 gds RR 226.6 - Polezhayev'),
    (R15, 2, 3, A, 5, 6, '13:30 10 July: 15 gds hvy TR counter-attacks from Storozhevoye towards 241.6'), (R15, 4, 24, R, 7, 7, 'Storozhevoye'),
    (M58, 1, 24, R, 7, 7, '58 MRBr: Storozhevoye - Yamki'),
    (B99, 5, 12, R, 3, 2, '99 TBr dug in at Vasilyevka - Andreyevka'), (B99, 13, 13, M, 13, 8, '12 July: ordered to Pravorot'), (B99, 14, 24, R, 13, 8, ''),
    (B26, 15, 24, R, 7, 6, ''), (B169, 20, 24, R, 7, 7, ''),
    (R227, 11, 24, R, 6, 12, '227 RR Belenikhino - Ivanovka'), (R295, 7, 24, R, 7, 13, '295 RR Leski - Shakhovo'),
    (B4G, 1, 11, R, 5, 12, '2 gds TC on the Belenikhino line'), (B25G, 1, 11, R, 6, 11, 'Vinogradovka'), (B26G, 1, 11, R, 7, 13, 'Shakhovo - Leski'),
    (M4G, 1, 12, R, 6, 11, ''), (M4G, 14, 24, R, 6, 11, ''), (R47, 1, 12, R, 5, 12, '47 gds hvy TR at Belenikhino'), (R47, 13, 13, A, 5, 11, 'with 4 gds TBr on 12 July'), (R47, 14, 24, R, 5, 12, ''),
    (B25G, 15, 24, R, 6, 11, ''), (B26G, 21, 24, R, 7, 13, ''), (B4G, 23, 24, R, 5, 12, ''),
    (R23, 15, 24, R, 9, 3, ''), (R26, 15, 24, R, 10, 4, ''), (R28, 14, 24, R, 9, 5, ''),
    (R287, 14, 24, R, 5, 2, '287 gds RR Mikhailovka - Prelestnoye'), (R290, 20, 24, R, 4, 1, ''), (R284, 23, 24, R, 4, 1, ''),
    (R127, 15, 24, R, 7, 2, ''), (R132, 15, 24, R, 8, 2, ''), (R136, 14, 24, R, 8, 1, '136 gds RR north bank east of Petrovka'),
    (B110, 16, 24, R, 7, 3, ''), (B170, 20, 24, R, 6, 2, ''), (M32, 14, 24, R, 9, 2, '32 MRBr north of the station'), (R36, 15, 24, R, 7, 2, ''),
    (M53, 16, 24, R, 9, 5, ''), (B31, 20, 24, R, 9, 4, ''),
    (S146, 15, 24, R, 9, 4, '1446 SAP with 32 TBr'), (S152, 13, 13, A, 9, 4, '1529 SAP (SU-152) with 29 TC'), (S152, 14, 24, R, 10, 4, ''),
    (B10G, 21, 24, R, 7, 1, ''), (R51, 12, 14, M, 11, 6, '51 gds TR with 10 gds MBde'), (R51, 16, 24, R, 7, 1, ''),
    (S147, 12, 24, R, 11, 6, '1447 SAP with 5 gds MC'),
    (R148, 8, 24, R, 4, 0, '148 gds TR (Churchills) with 95 gds RD'), (R53, 11, 24, R, 12, 3, '53 gds TR army reserve east of the station'),
    (D93, 11, 24, R, 7, 13, '93 gds RD Leski - Shakhovo'), (R278, 11, 24, R, 7, 13, ''), (R281, 11, 24, R, 8, 13, ''), (R28G, 11, 24, R, 6, 13, ''),
    (D97, 7, 13, R, 1, -2, '97 gds RD second echelon Srednyaya Olshanka - Veselyi'), (D97, 21, 24, R, 2, -1, ''),
    (L1, 16, 24, R, 7, 7, '1 SS-PzGr holds Storozhevoye - Stalinskoye'), (LS, 15, 24, R, 9, 4, ''), (LT, 20, 24, R, 9, 4, ''),
]
for _i, _t0, _t1, _k, _x, _y, _n in FILL:
    for _t in range(_t0, _t1 + 1):
        if not any(o[1] == _i for o in ORDERS.setdefault(_t, [])): ORDERS[_t].append((_k, _i, _x, _y))
