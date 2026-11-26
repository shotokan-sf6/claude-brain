"""Turn capture_replay.lua files into review datasets (sf6-review-dashboard schema) plus a report.

usage: shared_core_analyze.py OUTDIR FOCUS_NAME SET_FORMAT capture1.json [capture2.json ...]
  OUTDIR      : where sets/games/hits/events/timings json + report.md go
  FOCUS_NAME  : the player in focus (P1 on the dashboard): their in-game name, as in shotokan.json
  SET_FORMAT  : FT2 / FT3 / FT5 (all captures are treated as one set, in the order given)
"""
import json, os, re, sys, collections as C

BASE_DAMAGE = {  # SuperCombo normals, used to spot counter hits (first hit x1.2)
    'Cammy': {'5LP': 300, '5MP': 600, '5HP': 800, '5LK': 300, '5MK': 700, '5HK': 900, '2LP': 300, '2MP': 600,
              '2HP': 700, '2LK': 200, '2MK': 500, '2HK': 900, '4MP': 500, '4HK': 800},
    'Blanka': {'5LP': 300, '5MP': 700, '5HP': 800, '5LK': 300, '5MK': 600, '5HK': 800, '2LP': 300, '2MP': 600,
               '2HP': 900, '2LK': 200, '2MK': 500, '2HK': 900, '4MK': 600, '6HP': 1100, '3HP': 1000},
    'Luke': {'5LP': 300, '5MP': 600, '5HP': 800, '5LK': 300, '5MK': 700, '5HK': 900, '2LP': 300, '2MP': 600,
             '2HP': 800, '2LK': 200, '2MK': 500, '2HK': 900, '6MP': 600, '4HP': 800, '4HK': 1000, '6HP': 800},
    'Ryu': {'5LP': 300, '5MP': 600, '5HP': 800, '5LK': 300, '5MK': 700, '5HK': 900, '2LP': 300, '2MP': 600,
            '2HP': 800, '2LK': 200, '2MK': 500, '2HK': 900, '4HP': 800, '6HK': 800},
    'Terry': {},
}
# Full roster from the SuperCombo wiki (scripts/base_damage.json, next to this script); overrides the hand-entered table above.
def _norm(c):
    return re.sub(r'[^a-z0-9]', '', (c or '').lower())
_CHAR_ALIAS = {'char33': 'yasmine'}  # capture labels for characters missing from the game's enum export
try:
    _bd = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'base_damage.json')))
    for _k, _v in _bd.items():
        if not _k.startswith('_'):
            BASE_DAMAGE[_k] = _v
except FileNotFoundError:
    pass
_BD_NORM = {_norm(k): v for k, v in BASE_DAMAGE.items()}


def base_damage(char, label):
    c = _norm(char)
    return _BD_NORM.get(_CHAR_ALIAS.get(c, c), {}).get(label)
JUMP_STATES = {'JUMP', 'JUMP_NORM', 'SJUMP', 'SJUMP_NORM', 'WJUMP', 'WSJUMP', 'TJUMP', 'FALL', 'JDEF'}
MOVE_STATES = {'FOOTWORK', 'WALK', 'DASH', 'KDASH', 'DUCK_WALK', 'STAND', 'SIT', 'SITD', 'STAND_TURN', 'SIT_TURN'}
ATTACK_STATES = {'ATCK', 'SPECIAL', 'SUPER', 'CATCH', 'ATCK_LAND'}
# block punish range (distance in capture units between the players when the defender leaves blockstun): calibrated
# on 2026-11-24 ranked sets, where point-blank DP / Tiger Uppercut / Flash Kick blocks were 0.9-1.6 apart and spaced
# -5/-6 pokes 1.8-3.8 apart. Tune as character reach data comes in.
PUNISH_CLOSE, PUNISH_MID = 1.6, 2.6
_FD = {}


def frame_data(char):
    """tools/frame_data/<char>.json: wiki block advantage by input, plus analyzer-label aliases ({} when none)."""
    c = _norm(char)
    if c not in _FD:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frame_data', c + '.json')
        try: _FD[c] = json.load(open(p, encoding='utf-8'))
        except (OSError, ValueError): _FD[c] = {}
    return _FD[c]


def block_adv(char, label):
    """Wiki block advantage for an analyzer move label, or None. Normals match the input directly (5MK, 2HP);
    specials go through the character's aliases ("Shoryuken": "623?P", so "Shoryuken (OD)" -> 623PP)."""
    fd = frame_data(char); adv = fd.get('block_adv', {})
    if not label: return None
    if label in adv: return adv[label]
    al = fd.get('aliases', {})
    m = re.match(r'(.*?) \((L|M|H|OD)\)$', label)
    base, st = (m.group(1), m.group(2)) if m else (label, None)
    t = al.get(label) or al.get(base)
    if not t: return None
    if '?' in t:
        if not st: return None
        t = re.sub(r'\?([PK])', lambda x: x.group(1) * 2, t) if st == 'OD' else t.replace('?', st)
    return adv.get(t)


def mname(names, side, aid):
    return names.get(side, {}).get('%04d' % aid, '_%d' % aid) if aid is not None else ''


SPECIALS = [('SPIRALARROW', 'Spiral Arrow'), ('CANNONSPIKE', 'Cannon Spike'), ('CANNONSTRIKE', 'Cannon Strike (dive kick)'),
            ('QUICKSPIN', 'Quick Spin Knuckle'), ('HOOLIGAN', 'Hooligan Combination'), ('ROLLING_8', 'Vertical Ball'),
            ('ROLLING_B', 'Blanka Ball'), ('ROLLING_F', 'Blanka Ball'), ('ROLLING', 'Blanka Ball'), ('THUNDER', 'Electric Thunder'),
            ('SURPRISE', 'Surprise Forward'), ('ACSELSPINKNUCKLE', 'Quick Spin Knuckle'), ('HADOSHO', 'Rising Uppercut'), ('SYORYU', 'Rising Uppercut'),
            ('RisingUpper', 'Rising Uppercut'), ('HADO', 'Sand Blast'), ('SandBlast', 'Sand Blast'), ('FlashKnuckle_Air', 'Air Flash Knuckle'),
            ('FLASHKNUCKLE', 'Flash Knuckle'), ('Avenger', 'Avenger'), ('SOKUTOU', 'Avenger kick'), ('SHOUT', 'Shout of Earth')]


# character-specific names win over the shared list (Ryu and Luke both use HADO / SYORYU / SOKUTOU)
CHAR_SPECIALS = {
    # Juri: Fuhajin stores a kick stock (214K); Fuha is the stocked 236K release; Shiku-sen is the air dive kick; Tensenrin the 623P DP
    'Juri': [('FUHAJIN', 'Fuhajin (stock)'), ('FUHA_S', 'Fuha (stock release)'), ('FUHA', 'Fuha (stock release)'), ('SHIKKUSEN', 'Shiku-sen (dive kick)'), ('TENSENRIN', 'Tensenrin')],
    # Blanka (names checked against SuperCombo's special list; AERIAL taken to be the 63214K hop, +1 to +3 on block)
    'Blanka': [('ROLLING_8', 'Vertical Rolling'), ('ROLLING_B', 'Backstep Rolling'), ('ROLLING', 'Blanka Ball'), ('THUNDER', 'Electric Thunder'),
               ('AERIAL', 'Rainbow Rolling (63214K)'), ('WILDHUNT', 'Wild Hunt (command grab)'), ('BOMB', 'Blanka-chan Bomb'), ('SURPRISE', 'Surprise Forward/Back')],
    'Ryu': [('HADOSHO', 'Hashogeki'), ('HADO', 'Hadoken'), ('SYORYU', 'Shoryuken'), ('TATSUMAKI_AIR', 'Air Tatsumaki'),
            ('TATSUMAKI', 'Tatsumaki'), ('SOKUTOU', 'High Blade Kick'), ('KIAITAME', 'Denjin Charge')],
    # Luke (2026-11-24, from his move export): the Flash Knuckle family sits together between Sand Blast and Air Flash Knuckle:
    # HADOSHO = L, MOROTE_M / MOROTE_H = M / H, FLASHKNUCKLE_EX = OD (read from the export's order, not a confirmed name).
    # SOKUTOU_L starts Avenger; AvengerImpalar / AvengerNoChaser are its K / P follow-ups.
    'Luke': [('HADOSHO', 'Flash Knuckle (L)'), ('MOROTE', 'Flash Knuckle'), ('SYORYU', 'Rising Uppercut'), ('RisingUpper', 'Rising Uppercut'),
             ('HADO', 'Sand Blast'), ('SandBlast', 'Sand Blast'), ('FlashKnuckle_Air', 'Air Flash Knuckle'), ('FLASHKNUCKLE', 'Flash Knuckle'),
             ('AvengerImpalar', 'Avenger > Impaler'), ('AvengerNoChaser', 'Avenger > No Chaser'), ('Avenger', 'Avenger'), ('SOKUTOU', 'Avenger')],
}
SUBMOVES = {'funkeyslycer': 'Funky Slicer', 'wanningmoon': 'Waning Moon', 'juglinstep': 'Juggling Step', 'juglinsway': 'Juggling Sway'}
CHAR_SPECIALS.update({
    # Mai's specials carry numpad names (236P_Normal_Start, 623K_OD_Start)
    'Mai': [('623K', 'Ryuuenjin (DP)'), ('236K', 'Hissatsu Shinobi Bachi'), ('214P', 'Ryuuenbu'), ('236P', 'Kachousen (fireball)')],
    'Guile': [('SONICBOOM', 'Sonic Boom'), ('SOMERSAULT', 'Flash Kick'), ('Sonicblade', 'Sonic Blade'), ('SONICBLADE', 'Sonic Blade')],
    # A.K.I.: internal Japanese names; Jatoben = Serpent Lash and ShienHou = Nightshade Pulse are solid, the Akidako / Jakeiko labels less so
    # A.K.I. (2026-11-26, checked against SuperCombo inputs from the captures): Akidako is 2PP Sinister Slide (not Snake Step),
    # Jakeiko is 236K Snake Step (not Cruel Fate), Kyosyutotu is 214K Cruel Fate; ShienSen / ShihouSan are 214MP / 214HP.
    'AKI': [('Jatoben', 'Serpent Lash'), ('ShienHou', 'Nightshade Pulse'), ('ShienTui', 'Nightshade Chaser'), ('ShienSen', 'Orchid Spring'),
            ('ShihouSan', 'Toxic Wreath'), ('Akidako_Ganzigarame_Miss', 'Entrapment (whiff)'), ('Akidako_Ganzigarame', 'Entrapment (Sinister Slide grab)'),
            ('Akidako_Jarenko', 'Heel Strike (Sinister Slide)'), ('Akidako_Modokuga', 'Venomous Fang (Sinister Slide)'),
            ('Akidako_END', 'Sinister Slide exit'), ('Akidako', 'Sinister Slide'), ('Jakeiko', 'Snake Step'), ('Kyosyutotu', 'Cruel Fate')],
    # Ken (2026-11-24, from his move export and capture sequences): SPA_JINRAI_1 is the first kick; SPA_JINRAI_L/M/H are the
    # follow-ups (M hit crouch-blockers, so it's the overhead Gorai Axe Kick; L hit standing blockers, the low Kazekama Shin Kick);
    # the _EX follow-ups (after OD Jinrai) are Kasai Thrust Kick. SYORYU_START_FUNJIN is both the OD Shoryuken and the one from Quick Dash
    # (two action ids, one name), so it stays 'Shoryuken' and the Drive-drain check adds (OD).
    'Ken': [('SYORYU', 'Shoryuken'), ('HADO', 'Hadoken'),
            ('JINRAI_1', 'Jinrai Kick'), ('JINRAI_L_EX', 'Kasai Thrust Kick'), ('jinrai_M_EX', 'Kasai Thrust Kick'), ('JINRAI_M_EX', 'Kasai Thrust Kick'),
            ('JINRAI_H_EX', 'Kasai Thrust Kick'), ('JINRAI_L', 'Kazekama Shin Kick'), ('JINRAI_M', 'Gorai Axe Kick'), ('JINRAI_H', 'Senka Snap Kick'),
            ('JINRAI', 'Jinrai Kick'), ('RYUBI', 'Dragonlash Kick'), ('TATSUMAKI_AIR', 'Air Tatsumaki'), ('TATSUMAKI', 'Tatsumaki')],
    # Cammy (2026-11-24, from her move export): FC_* is Hooligan Combination; its follow-ups are Razor's Edge Slicer (no input),
    # Fatal Leg Twister (the throw), Reverse Edge (down + K) and Silent Step (P); Hooligan Cannon Strike already reads as Cannon Strike.
    'Cammy': [('FC_THROW', "Hooligan > Fatal Leg Twister"), ('RAZEREDGE', "Hooligan > Razor's Edge Slicer"), ('REVEDGE', 'Hooligan > Reverse Edge'),
              ('S_STEP', 'Hooligan > Silent Step'), ('FC', 'Hooligan Combination')],
    # M. Bison (2026-11-24): Double Knee Press is the Scissor Kicks; HEADPRESS_* without a button is the Shadow Rise jump, whose
    # follow-ups are Head Press (K, then Somersault Skull Diver with P) and Devil Reverse (P); Backfist Combo plants the Psycho Mine.
    'M Bison': [('DOUBLE_KNEEPRESS_MH', 'Scissor Kicks (M/H)'), ('DOUBLE_KNEEPRESS', 'Scissor Kicks'), ('SOMERSAULT_SKULL_DRIVER', 'Somersault Skull Diver'),
                ('HEADPRESS_P', 'Devil Reverse'), ('HEADPRESS_ODA_K', 'Head Press (OD)'), ('HEADPRESS_ODD_K', 'Head Press (OD)'), ('HEADPRESS_K', 'Head Press'),
                ('HEADPRESS', 'Shadow Rise'), ('BACKFIST_COMBO', 'Backfist Combo'), ('PSYCHO_CRUSHER', 'Psycho Crusher Attack'),
                ('VEGA_WARP', 'Bison Warp'), ('PSYCHO_FIELD', 'Psycho Field')],
    'Dee Jay': [('1_Airslasher', 'Air Slasher'), ('1_AirSlasher', 'Air Slasher'), ('2_JackKnife', 'Jackknife Maximum'),
                ('3_H_DowbleRollingSobat', 'Double Rolling Sobat'), ('3_M_RollingSobat', 'Double Rolling Sobat'),
                ('3_L_FakeRollingstep', 'Double Rolling Sobat (feint)'), ('3_EX_DowbleRollingSobat', 'Double Rolling Sobat'),
                ('5_EX_Joschool', 'Jus Cool (OD)'), ('5_Joschool', 'Jus Cool'), ('4_H_Macinegunapper', 'Machine Gun Upper (H)'), ('4_Macinegunapper', 'Machine Gun Upper'), ('4_MachineGun', 'Machine Gun Upper')],
    'Terry': [('SP0_H', 'Round Wave'), ('SP0_L_M', 'Power Wave'), ('SP0_EX', 'Power Wave (OD)'), ('SP0', 'Power Wave'),
              ('SP5_L', 'Quick Burn'), ('SP5_H', 'Burning Knuckle'), ('SP5', 'Burning Knuckle'),
              ('SP3', 'Power Charge'), ('SP4_EX', 'Power Charge (OD)'), ('SP2_M', 'Crack Shoot'), ('SP2', 'Crack Shoot'),
              ('ATK_SPA_SP1_L', 'Rising Tackle (L)'), ('ATK_SPA_SP1_M_H_EX', 'Rising Tackle'), ('ATK_SPA_SP1_END', 'Rising Tackle'),
              ('ATK_SPA_SP2_M', 'Crack Shoot')],
})
CHAR_SPECIALS.update({
    # Arjun (Oct 2026): numpad names. 236P / 22K / 236K / Throw_Grab / supers are solid; 03 = Divine Pillar and 623P = Cruel Shoulder
    # (SP_Attack = Justice Beyond, the pillar strike) are inferred from move behaviour, not confirmed
    'Arjun': [('236P_6P', 'Arm of Justice follow-up'), ('236P', 'Arm of Justice'), ('236K_LP', 'Breathing Shockwave (forward)'),
              ('236K_MP', 'Breathing Shockwave (diagonal)'), ('236K_HP', 'Breathing Shockwave (up)'), ('236K', 'Breathing Ring'),
              ('22K_Parry', 'Indomitable Defense counter'), ('22K_Attack', 'Moral Breakdown'), ('22K', 'Indomitable Defense (stance)'),
              ('623P_SP_Attack', 'Justice Beyond (pillar strike)'), ('623P_GUARD', 'Cruel Shoulder'), ('623P', 'Cruel Shoulder'),
              ('03', 'Divine Pillar'), ('Throw_Grab_OD', 'Ghastly Interrogation (OD)'), ('Throw_Grab', 'Ghastly Interrogation'),
              ('Throw_START', 'Ghastly Interrogation')],
})
CHAR_SPECIALS.update({
    # Akuma (2026-11-25, internal names checked against SuperCombo's move list): SYORYU = Gou Shoryuken (623P), GOHADO = Gou Hadoken
    # (236P, Full / Half are likely its charge levels), ZANKU = Zanku Hadoken (j.236P), SHAKKA = Adamant Flame (214P, Ex = OD),
    # HYAKKI = Demon Raid (236K) with GOSHO = Demon Guillotine (P), GOZIN = Demon Blade Kick (K), CANCEL = Demon Swoop (2, likely),
    # GORASEN = OD Demon Gou Rasen; ASURA = Ashura Senku teleport, ASURA_NG* = Oboro Throw (its LPLK follow-up);
    # MISOGI (214214K) is a level 2 Super Art though it carries the SPA_ prefix.
    'Akuma': [('SYORYU', 'Gou Shoryuken'), ('GOHADO', 'Gou Hadoken'), ('ZANKU', 'Zanku Hadoken'),
              ('SHAKKA_Ex', 'Adamant Flame (OD)'), ('SHAKKA', 'Adamant Flame'),
              ('HYAKKI_GOSHO', 'Demon Raid > Demon Guillotine'), ('HYAKKI_GOZIN', 'Demon Raid > Demon Blade Kick'),
              ('HYAKKI_GORASEN', 'Demon Raid > Demon Gou Rasen'), ('HYAKKI_CANCEL', 'Demon Raid > Demon Swoop'), ('HYAKKI', 'Demon Raid'),
              ('TATSUMAKI_AIR', 'Aerial Tatsumaki Zanku-Kyaku'), ('TATSUMAKI', 'Tatsumaki Zanku-Kyaku'),
              ('ASURA_NG', 'Ashura Senku > Oboro Throw'), ('ASURA_F', 'Ashura Senku (forward)'), ('ASURA_B', 'Ashura Senku (back)'),
              ('MISOGI', 'Misogi (level 2 super)')],
})
CHAR_SPECIALS.update({
    # Sagat (2026-11-25, checked against SuperCombo's move list): TigerShot_CRH = Low Tiger Shot (236LP), TigerShot_STD = High
    # Tiger Shot (236MP / HP), TigerKnee = Tiger Knee Crush (236K), 03 = Tiger Nexus (214K); 3_x_HIT is likely its connected
    # version (its 6K follow-ups are Mighty / Greedy / Nova Tiger)
    'Sagat': [('TigerUppercut', 'Tiger Uppercut'), ('TigerShot_CRH', 'Low Tiger Shot'), ('TigerShot_STD', 'High Tiger Shot'),
              ('TigerShot', 'Tiger Shot'), ('TigerKnee', 'Tiger Knee Crush'), ('03', 'Tiger Nexus'), ('3_', 'Tiger Nexus')],
    # Ingrid (2026-11-25): 236P = Sun Shot, 236K = Sun Rise, 214P = Sun Flare (_Air = Solar Burst, Stock1/2 = meter stocks),
    # 22P_DAGEKI / 22P_Tama are taken to be Sun Veil (the wiki's 22K counter) catching a strike / a projectile: the wiki has no 22P,
    # and DAGEKI is "strike", Tama "ball" (inferred, not confirmed)
    'Ingrid': [('236P', 'Sun Shot'), ('236K', 'Sun Rise'), ('214P_H_Stock1_Air', 'Solar Burst (H, 1 stock)'), ('214P_H_Stock2_Air', 'Solar Burst (H, 2 stock)'),
               ('214P_H_Stock1', 'Sun Flare (H, 1 stock)'), ('214P_H_Stock2', 'Sun Flare (H, 2 stock)'), ('214P_OD_Air', 'Solar Burst (OD)'),
               ('214P_M_Air', 'Solar Burst (M)'), ('214P_L_Air', 'Solar Burst (L)'), ('214P', 'Sun Flare'),
               ('KKK', 'Vanishing Sun'), ('22P_DAGEKI', 'Sun Veil (counter, strike)'), ('22P_Tama', 'Sun Veil (counter, projectile)'), ('22P', 'Sun Veil')],
})
LINGER = {'Arjun': ('SPA_03', 'SPA_236K')}   # moves whose hitbox stays out after the character moves on
CHAR_SUPERS = {
    'Ryu': [('SAA_HADOUKEN', 'SA1 Shinku Hadoken'), ('SAA_HADOSHO', 'SA2 Shin Hashogeki'), ('SAD_SHINSYORYU', 'Critical Art (Shin Shoryuken)'),
            ('SAA_SHINSYORYU', 'SA3 Shin Shoryuken'), ('CAA', 'Critical Art (Shin Shoryuken)')],
    'Terry': [('SAA_BusterWolf', 'SA1 Buster Wolf'), ('SAA_2', 'SA2'), ('SA3', 'SA3'), ('CA', 'Critical Art')],
    'Juri': [('SAA_SAKKAIFUHAJIN', 'SA1 Sakkai Fuhazan'), ('SAA_FUSUI_ENGINE', 'SA2 Feng Shui Engine'), ('SAA_03', 'SA3'), ('SAD_03', 'SA3'), ('CAA_03', 'Critical Art'), ('CAD_03', 'Critical Art')],
    'Arjun': [('SAA_SA1', 'SA1 Howling Destruction'), ('SAA_SA2', 'SA2 Instant Oblivion'), ('SAD_SA2', 'SA2 Instant Oblivion'), ('SA3', "SA3 Yaksha's Order"), ('CAA', "Critical Art (Yaksha's Order)")],
    'M Bison': [('SAA_KNEEPRESS_NIGHTMARE', 'SA1 Knee Press Nightmare'), ('SAD_KNEEPRESS_NIGHTMARE', 'SA1 Knee Press Nightmare'),
                ('SAA2', 'SA2 Psycho Punisher'), ('SAD2', 'SA2 Psycho Punisher'), ('SAA_FINAL_PSYCHO_CRUSHER', 'SA3 Unlimited Psycho Crusher'),
                ('SAA_START', 'SA3 Unlimited Psycho Crusher'), ('SAA_HIT', 'SA3 Unlimited Psycho Crusher'), ('SAD_HIT', 'SA3 Unlimited Psycho Crusher'),
                ('CAA_HIT', 'Critical Art (Unlimited Psycho Crusher)'), ('CAD_HIT', 'Critical Art (Unlimited Psycho Crusher)')],
    'Ken': [('SAA_RYUBI', 'SA1 Dragonlash Flame'), ('SAA_2_SippuJinrai', 'SA2 Shippu Jinrai-kyaku'), ('SAA_SHINRYUREPPA', 'SA3 Shinryu Reppa'),
            ('SAD_SHINRYUREPPA', 'SA3 Shinryu Reppa'), ('CAA_SHINRYUREPPA', 'Critical Art (Shinryu Reppa)'), ('CAD_SHINRYUREPPA', 'Critical Art (Shinryu Reppa)')],
    'Luke': [('SAA_HADOUKEN', 'SA1 Vulcan Blast'), ('SAA_Ereser', 'SA2 Eraser'), ('SAA_PALERIDER', 'SA3 Pale Rider'), ('SAD_PALERIDER', 'SA3 Pale Rider'),
             ('CAA_PALERIDER', 'Critical Art (Pale Rider)'), ('CAD_PALERIDER', 'Critical Art (Pale Rider)')],
    'Sagat': [('SAA_SA1', 'SA1 Tiger Cannon'), ('SAA2_NGS', 'SA2 Savage Tiger (grab)'), ('SAA2', 'SA2 Savage Tiger'), ('SAD2', 'SA2 Savage Tiger'),
              ('SA3', 'SA3 Tiger Vanquisher'), ('CA_', 'Critical Art (Tiger Vanquisher)')],
    # Ingrid: SAA_01 = SA1 Shining Sun, SAA_02 = SA2 Order of the Sun (both with stock versions), SA3 = Cosmic Ray; SAA_Boss unknown
    'Ingrid': [('SAA_01', 'SA1 Shining Sun'), ('SAD_01', 'SA1 Shining Sun'), ('SAA_02', 'SA2 Order of the Sun'), ('SAD_02', 'SA2 Order of the Sun'),
               ('SA3', 'SA3 Cosmic Ray'), ('CA_', 'Critical Art (Cosmic Ray)')],
    # Akuma: Shun Goku Satsu (Raging Demon) is his alternate Critical Art (CAA2 / CAD2); SHINRA = SA3 Sip of Calamity,
    # HOUTENGOUKA = SA2 Empyrean's End (inferred from the name and the wiki list), KONGO_KOKURETSUZAN = level 2 Super Art
    'Akuma': [('CAA2', 'Critical Art (Shun Goku Satsu)'), ('CAD2', 'Critical Art (Shun Goku Satsu)'),
              ('SAA_GOHADO', 'SA1 Messatsu Gohado'), ('SAA_GOZANKU', 'SA1 Tenma Gozanku'),
              ('SAA_HOUTENGOUKA', "SA2 Empyrean's End"), ('SAD_HOUTENGOUKA', "SA2 Empyrean's End"),
              ('SAA_SHINRA', 'SA3 Sip of Calamity'), ('SAD_SHINRA', 'SA3 Sip of Calamity'),
              ('CAA_SHINRA', 'Critical Art (Sip of Calamity)'), ('CAD_SHINRA', 'Critical Art (Sip of Calamity)'),
              ('SAA_KONGO_KOKURETSUZAN', 'Kongou-Kokuretsuzan (level 2 super)')],
    'Blanka': [('SAA_1_SHOUT', 'SA1'), ('SAA_2_ROLLING_CANON', 'SA2'), ('SAA_3_CANON_BALL', 'SA3'), ('SAD_3_CANON_BALL', 'SA3'), ('CAA_CANON_BALL', 'Critical Art'), ('CAD_CANON_BALL', 'Critical Art')],
}

CHAR_NORMALS = {
    'Cammy': [('ATK_4MP_HK', 'Lift Combination (4MP~HK)'), ('ATK_TC_5HP_5HK', 'Target combo (5HP~HK)'), ('SPD_FC_THROW', 'Hooligan > Fatal Leg Twister')],
    'M Bison': [('ATK_5MPTC_P', '5MP > P target combo'), ('ATK_5MPTC_K', '5MP > K target combo'), ('IMM_VEGA_BOMB', 'Psycho Mine explosion')],
    'Sagat': [('ATK_2MP_HP', 'Tiger Slash (2MP~HP)'), ('ATK_2MP_HK', 'Tiger Rise (2MP~HK)'), ('ATK_5HP_HK', 'Tiger Sting (5HP~HK)'),
              ('ATK_5MK_MK', '5MK~MK target combo'), ('ATK_6HK_HIT', '6HK')],
    'Ingrid': [('ATK_5MP_TC', 'Pretty Heel Kick (5MP~MK)'), ('ATK_4MK_TC', 'Glowing Touch 2 (4MK~HP)'), ('ATK_4HP_TC', 'Luminous Uppercut 2 (4HP~HP)')],
    'Akuma': [('ATK_5MP_MP', 'Viscera Piercer (5MP~MP)'), ('ATK_5MK_HK', 'Bone Crusher Axe Kick (5MK~HK)'),
              ('ATK_6HP_TC_TC', 'Kikoku Combination (6HP~6HP~HK)'), ('ATK_6HP_TC', 'Kikoku Combination (6HP~6HP)'),
              ('ATK_92MK', 'Tenmaku Blade Kick (j.2MK)')],
    'Ken': [('ATK_5MP_HP', 'Chin Buster (5MP~HP)'), ('ATK_5MK_MK_HK', 'Triple Flash Kick (5MK~MK~HK)'), ('ATK_5MK_MK', 'Triple Flash Kick (5MK~MK)'),
            ('ATK_HK_SHIDEN', 'Quick Dash > Thunder Kick'), ('ATK_MK_FUMIKOMI', 'Quick Dash > Forward Step Kick'),
            ('KK_LK_FUNJIN_STOP', 'Quick Dash > Emergency Stop'), ('KK_LK_FUNJIN', 'Quick Dash')],
}


# 2026-11-25 (PhenomTheMoose / CFN Good sets): names read from the move codes. Super slots (SA1/SA2/SA3) follow the SAA number;
# special names are the well-known ones for each code. Codes not listed stay raw (unnamed) until checked.
for _c, _rows in {
    'Mai': [('SAA_1_POWERUP', 'SA1 (powered up)'), ('SAA_1', 'SA1'), ('SAA_2', 'SA2'), ('SA3_HIT', 'SA3'), ('START_HIT', 'SA3'), ('CA_HIT', 'Critical Art')],
    'Jamie': [('SAA3_GETUGASAIHOU', 'SA3 Getsuga Saiho'), ('SAA_GETUGASAIHOU', 'SA3 Getsuga Saiho'), ('SAA2', 'SA2'), ('SAA1', 'SA1'), ('MASIN_MAX', 'SA2 (max)')],
    'Rashid': [('SAA1_G', 'SA1 Super Rashid Kick'), ('SAA1', 'SA1 Super Rashid Kick'), ('SAA2', 'SA2 Ysaar'), ('SAA3', 'SA3 Altair'), ('SA3', 'SA3 Altair')],
    'Dhalsim': [('SAA_YOGAINFERNO', 'SA1 Yoga Inferno'), ('SAA_YOGASUNBURST', 'SA2 Yoga Sunburst'), ('SAA_YOGAGAIA', 'SA3 Yoga Gaia')],
    'Kimberly': [('SAA_Lv1', 'SA1 Bushin Beats'), ('SAA_Lv2', 'SA2 Bushin Scramble'), ('SAA_Lv3', 'SA3 Bushin Ninjastar Cypher')],
    'Marisa': [('SAA1', 'SA1 Javelin of Marisa'), ('SAA2', 'SA2 Phalanx'), ('SAA3', 'SA3 Goddess of the Hunt')],
    'Manon': [('SAA_1', 'SA1'), ('SAA_2', 'SA2'), ('SAA_3', 'SA3')],
    'Sagat': [('START_HIT', 'SA3 Tiger Vanquisher')],   # 3 bars spent with it (2026-11-25)
}.items():
    CHAR_SUPERS.setdefault(_c, [])[:0] = _rows
for _c, _rows in {
    'Jamie': [('SPA2_EX', 'Freeflow Strikes (OD)'), ('SPA2', 'Freeflow Strikes')],
    'Rashid': [('SPINING_MIXER', 'Spinning Mixer'), ('EAGLE_SPIKE', 'Eagle Spike'), ('WHIRLWINDSHOT', 'Whirlwind Shot'), ('ARABIAN_CYCLONE', 'Arabian Cyclone'),
               ('ARABIAN_SKYHIGH', 'Arabian Skyhigh'), ('WING_STROKE', 'Wing Stroke')],
    'Dhalsim': [('YOGAFIRE', 'Yoga Fire'), ('YOGAFRAME', 'Yoga Flame'), ('YOGABLAST', 'Yoga Blast'), ('YOGAARCH', 'Yoga Arch'), ('YOGACOMET', 'Yoga Comet'),
                ('YOGAFLOAT', 'Yoga Float'), ('YOGATELEPORT', 'Yoga Teleport')],
    'Kimberly': [('Hayagake', 'Sprint (Hayagake)'), ('Tengu', 'Tengu Stone')],
    'Marisa': [('Scutum_NGA', 'Scutum (counter-throw)'), ('Gradius_MAX', 'Gladius (charged)')],
}.items():
    CHAR_SPECIALS.setdefault(_c, [])[:0] = _rows
for _c, _rows in {
    'Dhalsim': [('ATK_82K', 'j.2K (drill)'), ('ATK_82P', 'j.2P (drill)')],
    'Mai': [('ATK_4HK_TC', '4HK target combo')],
    'Marisa': [('ATK_5HP_MAX', '5[HP] (charged)'), ('ATK_4HP_MAX', '4[HP] (charged)'), ('ATK_6HK_MAX', '6[HK] (charged)'), ('ATK_5HK_MAX', '5[HK] (charged)'),
               ('ATK_3HP_MAX', '3[HP] (charged)'), ('ATK_2HK_MAX', '2[HK] (charged)')],
}.items():
    CHAR_NORMALS.setdefault(_c, [])[:0] = _rows


# 2026-11-26 (Zastorial / A.K.I. sets): super slots follow the SAA number; specials are the well-known names for each code.
for _c, _rows in {
    'AKI': [('SAA_01', 'SA1'), ('SAA_02', 'SA2'), ('SAA_03', 'SA3')],
    'C.Viper': [('SAA_02', 'SA2'), ('SAA_01', 'SA1'), ('SAA_03', 'SA3')],
    'Dhalsim': [('SAA_LV3', 'SA3 Yoga Gaia')],
    'Yasmine': [('SAA_SA1', 'SA1'), ('SA3_HIT', 'SA3'), ('SA3', 'SA3')],
    'Alex': [('SAA1', 'SA1'), ('SAA2', 'SA2'), ('SAA3', 'SA3')],
    'Ingrid': [('START', 'SA3 Cosmic Ray')],   # bare START spent 3 bars (2026-11-26)
}.items():
    CHAR_SUPERS.setdefault(_c, [])[:0] = _rows
for _c, _rows in {
    'Chun-Li': [('KIKOUKEN', 'Kikoken'), ('TENNSHOU', 'Tenshokyaku'), ('HYAKURETSU', 'Hyakuretsukyaku'), ('SPINNINGBIRD', 'Spinning Bird Kick')],
    'C.Viper': [('THN', 'Thunder Knuckle'), ('BURNING', 'Burning Kick')],
    'Alex': [('AirKneeSmash', 'Air Knee Smash')],
    'Yasmine': [('ATK_SPA_236P', '236P special'), ('236P', '236P special'), ('214P', '214P special'), ('623K', '623K special'), ('236K', '236K special')],
}.items():
    CHAR_SPECIALS.setdefault(_c, [])[:0] = _rows
CHAR_NORMALS.setdefault('Kimberly', [])[:0] = [('ATK_GOKUSA_Kim_5MP_5HP_TC', '5MP~HP target combo')]


# 2026-11-26: names from the SuperCombo wiki move lists, matched to the internal codes by the inputs in the captures
# (motion + button at each move's start, across all captures in replays\).
for _c, _rows in {
    'AKI': [('SAA_01', 'SA1 Deadly Implication'), ('SAA_02', 'SA2 Tainted Talons'), ('SAA_03', 'SA3 Claws of Ya Zi')],
    'Elena': [('SAA_01', 'SA1 Meteor Volley'), ('SAA_02', 'SA2 Revival Dance'), ('SA3', 'SA3 Song of the Grasslands')],
}.items():
    CHAR_SUPERS.setdefault(_c, [])[:0] = _rows
for _c, _rows in {
    # Jamie: SPA1 214P, SPA3 623K, SPA_4 j.214K (air), SPA5 63214K (NGA = the grab part on hit), SPA6 236K
    'Jamie': [('SPA1', 'Swagger Step'), ('SPA3', 'Arrow Kick'), ('4_', 'Luminous Dive Kick'), ('SPA5', 'Tenshin'), ('SPA6', 'Bakkai')],
    # Elena: 00 = 214K, 01 = 236K, 02 = 623K, 03 = 236P and its 6P / 6LK / 6MK / 6HK follow-ups, 04 = 214P
    'Elena': [('00_SPIN_SYTHE', 'Spinning Scythe'), ('01_RHINO_HORN', 'Rhino Horn'), ('02_WHEEL', 'Scratch Wheel'), ('03_MOVE_1', 'Lynx Song'),
              ('03_MOVE', 'Lynx Whirl'), ('03_LP', 'Lynx Song > Leopard Snap'), ('03_MP', 'Lynx Song > Harvest Circle'), ('03_HP', 'Lynx Song > Mallet Smash'),
              ('04_ADD', 'Moon Glider follow-up'), ('04', 'Moon Glider')],
    # Alex: SP0 = 236P (L/M Flash Axe, H/OD Flash Chop), SP1 = 63214P Power Bomb (NGS = the attempt, NGA = the grab on hit)
    'Alex': [('SP0_H', 'Flash Chop'), ('SP0_EX', 'Flash Chop'), ('SP0', 'Flash Axe'), ('SP1_NGA', 'Power Bomb'), ('SP1_NGS', 'Power Bomb (attempt)'),
             ('SP1', 'Power Bomb')],
}.items():
    CHAR_SPECIALS.setdefault(_c, [])[:0] = _rows
for _c, _rows in {
    'Jamie': [('ATK_22P', 'The Devil Inside (drink)')],
    'AKI': [('ATK_82HP', 'j.2HP (Gong Fu)'), ('SPD_Akidako_Ganzigarame_Miss', 'Entrapment (whiff)'), ('SPD_Akidako_Ganzigarame', 'Entrapment (Sinister Slide grab)')],
    # Alex: ATK_S_* are Prowler Stance (2PP) and its follow-ups
    'Alex': [('ATK_S_STD_CRH', 'Prowler Stance'), ('ATK_S_DASH_ATTACK', 'Prowler > Slashing Elbow'), ('ATK_S_DASH_F', 'Prowler > Low Rush'),
             ('ATK_S_DASH_B', 'Prowler > Low Retreat'), ('ATK_S_LP', 'Prowler > Palm Jab'), ('ATK_S_MP', 'Prowler > Shoulder Launcher'),
             ('ATK_S_HP_MAX', 'Prowler > Heavy Lariat (hold)'), ('ATK_S_HP', 'Prowler > Heavy Lariat'), ('ATK_S_LK', 'Prowler > Tactical Hop'),
             ('ATK_S_MK', 'Prowler > Air Stampede'), ('ATK_S_HK', 'Prowler > Sweep Combination'), ('ATK_S_NGA', 'Prowler throw'), ('ATK_S_NGS', 'Prowler throw'),
             ('ATK_5HK_MAX', '5[HK] (hold)'), ('ATK_5HP_MAX', '5[HP] (hold)'), ('ATK_92HP', 'j.2HP (Flying Cross Chop)')],
}.items():
    CHAR_NORMALS.setdefault(_c, [])[:0] = _rows

def pretty(n, char=None):
    """game move name -> readable label"""
    for k, lab in CHAR_NORMALS.get(char, []):   # unique attacks and target combos, which read as plain normals otherwise
        if n == k or n.startswith(k + '_'): return lab
    for k, lab in CHAR_SUPERS.get(char, []):
        if n.startswith(k): return lab
    if n.startswith('SPA_'):
        core = n[4:]
        for k, lab in CHAR_SPECIALS.get(char, []) + SPECIALS:
            if core.startswith(k):
                m = re.search(r'_(L|M|H|EX|OD)(?:_|$)', core[len(k):] + '_')
                return lab + (f" ({'OD' if m.group(1) == 'EX' else m.group(1)})" if m else '')
        return re.sub(r'_(START|Loop|LAND|END|CR)$', '', core)
    for k, lab in CHAR_SPECIALS.get(char, []):   # some characters' specials have no SPA_ prefix (Dee Jay's 1_Airslasher, Ken's JINRAI)
        if n.startswith(k):
            rest = n[len(k):]
            m = re.search(r'_(L|M|H|EX|OD)(?:_|$)', rest + '_')
            extra = ' (feint)' if 'fake' in rest.lower() and 'feint' not in lab else ''
            sub = re.match(r'_\d_([a-z]+)', rest)
            return lab + (f" > {SUBMOVES.get(sub.group(1), sub.group(1).title())}" if sub else '') + extra + (f" ({'OD' if m.group(1) == 'EX' else m.group(1)})" if m else '')
    for k, lab in (('SAA_D-ASSAULT', 'SA3 Delta Red Assault'), ('CAA_D-ASSAULT', 'Critical Art (Delta Red Assault)'),
                   ('SAA_SPIN_DRIVE', 'SA1 Spin Drive Smasher'), ('SA1', 'SA1 Spin Drive Smasher'), ('SAA_KILLERBEE', 'SA2 Killer Bee Spin'),
                   ('SA2_KILLERBEE', 'SA2 Killer Bee Spin'), ('SAA_1_SHOUT', 'SA1 Lightning Beast Ball'), ('SAA_2_ROLLING', 'SA2'),
                   ('SAA_3_CANON', 'SA3 Ground Shave Cannonball'), ('CAA_CANON', 'Critical Art (Ground Shave Cannonball)')):
        if n.startswith(k): return lab
    m = re.match(r'ATK_8([LMH][PK])', n)
    if m: return 'j.' + m.group(1)
    m = re.match(r'ATK_(\d?[jJ]?\d*[LMH][PK].*)$', n)
    if m: return re.sub(r'_(Y\d|B|C|F)$', '', m.group(1))
    for pre, lab in (('SPA_', ''), ('SA1', 'SA1 '), ('SA2', 'SA2 '), ('SAA_', 'Super '), ('CAA_', 'Critical Art '),
                     ('NGA', 'Throw'), ('NGS', 'Throw attempt'), ('DPA', 'Drive Parry'), ('ATK_CTA_4', 'Drive Reversal'),
                     ('ATK_CTA_RUSH', 'Drive Rush'), ('ATK_CTA_DASH', 'Drive Rush'), ('DRIVE_RUSH', 'Drive Rush'), ('ATK_CTA', 'Drive Impact')):
        if n.startswith(pre): return (lab + n[len(pre):]).strip() if lab in ('', 'SA1 ', 'SA2 ', 'Super ', 'Critical Art ') else lab
    return n


def tstr(rnd, timer):
    return f'R{rnd} @{timer}'


def load_capture(path):
    """A capture file, plain (.json) or gzip-compressed (.json.gz)."""
    if path.endswith('.gz'):
        import gzip
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            return json.load(f)
    return json.load(open(path, encoding='utf-8'))


def analyze(path, game_no, focus):
    d = load_capture(path)
    info, fr, names = d['info'], d['frames'], d.get('move_names', {})
    side_name = {'p1': info['p1_name'], 'p2': info['p2_name']}
    side_char = {'p1': info['p1_char'], 'p2': info['p2_char']}
    # per-replay fixes for captures with stale labels (made before capture v3.1), e.g. {"6GNK8JVHX": {"p1": "Cammy", "p2": "Luke"}}
    ov = json.loads(os.environ.get('SF6_CHAR_OVERRIDE') or '{}').get(info.get('replay_id'), {})
    for s_, c_ in ov.items():
        side_char[s_] = c_; info[s_ + '_char'] = c_
    # The capture's character ids can be stale (read before the replay loaded). If the
    # sf6_moves files are available (env SF6_MOVES=dir), pick each side's character by
    # which move list covers the most of its action ids, and re-attach the move names.
    mdir = os.environ.get('SF6_MOVES')
    # names the player typed into Move Export v4 for characters the game doesn't name (sf6_moves/char_names.json: {"33": "Yasmine"})
    cnames = {}
    if mdir and os.path.exists(os.path.join(mdir, 'char_names.json')):
        cnames = json.load(open(os.path.join(mdir, 'char_names.json')))
    for s_ in ('p1', 'p2'):
        m_ = re.match(r'char_(\d+)$', side_char[s_] or '')
        if m_ and m_.group(1) in cnames:
            side_char[s_] = cnames[m_.group(1)]
    if mdir and os.path.isdir(mdir):
        lists = {}
        for fn in os.listdir(mdir):
            m = re.match(r'(\d+)_(.+)\.json$', fn)
            if m:
                mv = json.load(open(os.path.join(mdir, fn))).get('moves', {})
                lists[m.group(2)] = mv
                for alt in (m.group(2).replace('_', ' '), m.group(2).replace('_', '. ')):   # Dee_Jay -> Dee Jay, C_Viper -> C. Viper
                    lists.setdefault(alt, mv)
                cid = str(int(m.group(1)))
                lists.setdefault('char_' + cid, mv)  # old files / labels by id
                if cid in cnames: lists.setdefault(cnames[cid], mv)
        for s in ('p1', 'p2'):
            ids = C.Counter('%04d' % f[s]['action_id'] for f in fr if f.get(s) and f[s].get('action_id') is not None)
            tot = sum(ids.values()) or 1
            cov = {c: sum(n for i, n in ids.items() if i in mv) / tot for c, mv in lists.items()}
            best = max(cov, key=cov.get) if cov else None
            if side_char[s] not in lists:
                # many action ids are shared between characters, so a missing move list can't be guessed from another
                print(f"warning: no sf6_moves file for {s} ({side_char[s]}); keeping the capture's label. "
                      f"Run Move Export with {side_char[s]} loaded for move names.", file=sys.stderr)
                best = None
            elif os.environ.get('SF6_TRUST_LABELS') or (best and cov[best] < cov[side_char[s]] + 0.05):
                # capture v3.1+ re-reads character ids every frame, so its labels can be trusted
                best = side_char[s]
            if best and best != side_char[s]:
                print(f"note: {s} labelled {side_char[s]} in the capture, but its moves match {best} "
                      f"({cov[best]:.0%} vs {cov.get(side_char[s], 0):.0%}); using {best}", file=sys.stderr)
            if best:
                side_char[s] = best
                names[s] = {k: v['name'] for k, v in lists[best].items()}
    # Move names come from animation (motion) names, and the game reuses one motion for several strengths
    # (every Cammy Cannon Spike, OD included, plays SPA_CANNONSPIKE_H). So:
    #  1. OD: a special whose starts take 2 Drive bars (drive drops >= 15000 within 12 frames) is OD, whatever its name says.
    #  2. A strength (L/M/H) is kept only when the move list has more than one strength for that special.
    for s in ('p1', 'p2'):
        nm = names.get(s) or {}
        strengths = C.defaultdict(set)
        for v in nm.values():
            m = re.match(r'SPA_(.+?)_(L|M|H)(_.*)?$', v)
            if m: strengths[m.group(1)].add(m.group(2))
        starts = C.defaultdict(lambda: [0, 0])
        for k in range(1, len(fr)):
            a, b = fr[k].get(s), fr[k - 1].get(s)
            if not a or not b or a['action_id'] == b['action_id']: continue
            n_ = nm.get('%04d' % a['action_id'], '')
            if n_.startswith('SPA_') and b.get('act_st_name') != 'SPECIAL':
                drop = b['drive'] - min(x[s]['drive'] for x in fr[k:k + 12] if x.get(s))
                starts[a['action_id']][0 if drop >= 15000 else 1] += 1
        for aid, (od, no) in starts.items():
            key = '%04d' % aid
            if od and od >= no and not re.search(r'_(EX|OD)(_|$)', nm[key]):
                nm[key] = re.sub(r'_(L|M|H)(?=_|$)', '', nm[key]) + '_OD'
        for key, v in list(nm.items()):
            m = re.match(r'SPA_(.+?)_(L|M|H)(_.*)?$', v)
            if m and len(strengths[m.group(1)]) == 1:
                nm[key] = f'SPA_{m.group(1)}{m.group(3) or ""}'
        # An OD special's later phases (e.g. Cannon Spike's rise and landing) are separate actions that reuse the
        # plain animation names; give them the OD label too, by remapping their ids for the rest of this capture.
        base = lambda n: re.match(r'SPA_([A-Za-z]+)', n).group(1) if re.match(r'SPA_([A-Za-z]+)', n) else None
        chain, prev_id = None, None
        for f in fr:
            a = f.get(s)
            if not a or a.get('action_id') is None: continue
            aid = a['action_id']; n_ = nm.get('%04d' % aid, '')
            b_ = base(n_)
            if aid != prev_id:
                if b_ and re.search(r'_(EX|OD)(_|$)', n_): chain = b_
                elif not (b_ and b_ == chain): chain = None
            if chain and b_ == chain and not re.search(r'_(EX|OD)(_|$)', n_):
                new = 900000 + aid
                nm.setdefault('%04d' % new, re.sub(r'_(L|M|H)(?=_|$)', '', n_) + '_OD')
                a['action_id'] = new; aid_eff = new
            prev_id = aid
        names[s] = nm
    fidx = {f['i']: k for k, f in enumerate(fr)}
    rid = info['replay_id']

    def frame(i):
        return fr[fidx[i]] if i in fidx else None

    def lookback(i, side, n):
        k = fidx.get(i, 0)
        return [fr[j][side] for j in range(max(0, k - n), k)]

    # ---- combos from hits (first hit starts a combo)
    hits = sorted(d['hits'], key=lambda h: h['frame'])
    combos = []
    for h in hits:
        if h['attacker_combo_count'] is None: continue
        if h['attacker_combo_count'] == 1 or not combos or combos[-1]['attacker'] != h['attacker'] or combos[-1]['round'] != h['round']:
            combos.append({'attacker': h['attacker'], 'victim': h['victim'], 'round': h['round'], 'first': h, 'hits': [h]})
        else:
            combos[-1]['hits'].append(h)
    # damage = victim HP drop over the combo (combo damage counter as fallback)
    # Life has two parts: hp (what is left now) and hp_recoverable_cap (the top of the white / recoverable part). Recoverable damage
    # (Arjun's blocked pressure and stance counter, Drive Reversal, chip on some moves) drops hp but not the cap, and regenerates;
    # the next clean hit takes the cap down to hp, so that white health is lost for good. damage = permanent life lost
    # (cap drop over the combo, which includes the white health it cashed); recoverable = white health the combo added;
    # white_cashed = white health that was there before the combo and was lost to it.
    def life_change(v, k0, k1, floor=0, ceil=10 ** 9):
        """(damage, recoverable, white_cashed, hp_drop) for victim v between frame index k0 (first hit) and k1 (last hit).
        floor: never look back before this frame index (the previous combo on the same victim), so two combos don't share damage."""
        j = k0 - 1   # last frame before the combo: walk back past any hitstun / damage state (late-detected first hits)
        while j > max(0, k0 - 30, floor) and ((fr[j][v].get('hitstun') or 0) > 0 or fr[j][v].get('act_st_name') == 'DAMAGE'): j -= 1
        j = max(0, j, floor)
        hp0 = fr[j][v]['hp']; cap0 = fr[j][v].get('hp_recoverable_cap') or hp0
        e = k1   # run on while the victim is still being hit or held (cinematic supers log their last hits late), up to ceil
        while e + 1 < min(len(fr), k1 + 240, ceil) and (fr[e + 1][v].get('act_st_name') in ('DAMAGE', 'HOLD') or (fr[e + 1][v].get('hitstun') or 0) > 0): e += 1
        span = range(k0, min(len(fr), e + 3, ceil))
        hp1 = min(fr[x][v]['hp'] for x in span); cap1 = min((fr[x][v].get('hp_recoverable_cap') or fr[x][v]['hp']) for x in span)
        cap1 = max(cap1, hp1)
        white0, white1 = max(0, cap0 - hp0), max(0, cap1 - hp1)
        return max(0, cap0 - cap1), max(0, white1 - white0), max(0, white0 - white1), max(0, hp0 - hp1)
    last_end = {}
    for n_, c in enumerate(combos):
        v = c['victim']
        k0 = fidx.get(c['first']['frame'], 0); k1 = fidx.get(c['hits'][-1]['frame'], k0)
        nxt = next((fidx.get(c2['first']['frame'], 10 ** 9) for c2 in combos[n_ + 1:] if c2['victim'] == v), 10 ** 9)
        dmg, rec, cashed, hpd = life_change(v, k0, k1, last_end.get((v, c['round']), 0), nxt)
        last_end[(v, c['round'])] = k1
        c['damage'] = dmg if (dmg or rec) else max(h['attacker_combo_damage'] or 0 for h in c['hits'])
        c['recoverable'], c['white_cashed'] = rec, cashed

    # ---- throws from stats (Throw counter increments)
    throw_frames = {'p1': [], 'p2': []}
    tech_events = []
    perfect_events, dr_events, throw_parry_frames = [], [], []
    prev = {'p1': {}, 'p2': {}}
    for s in d['stats']:
        p = s['player']
        for k, v in s['changed'].items():
            old = prev[p].get(k)
            if old is not None and v is not None and v > old:
                if k == 'Throw': throw_frames[p].append(s['frame'])
                if k == 'ThrowTech': tech_events.append((p, s['frame'], s['round'] + 1))
                if k == 'ParryJust': perfect_events.append((p, s['frame'], s['round'] + 1))
                if k == 'DrvRev': dr_events.append((p, s['frame'], s['round'] + 1))
            prev[p][k] = v
            if k == 'ThrowParry' and old is not None and v is not None and v > old:
                throw_parry_frames.append(s['frame'])

    # landed throws are not always in d['hits']: build them from the Throw stat and the victim's HP drop
    for a, lst in throw_frames.items():
        v = 'p2' if a == 'p1' else 'p1'
        for t in lst:
            # a command grab's hits can land well after the Throw stat ticks (Arjun's Ghastly Interrogation: ~145 frames)
            if any(c['attacker'] == a and -10 <= c['first']['frame'] - t <= (240 if 'Throw' in mname(names, a, c['first']['attacker_action_id']) else 90) for c in combos): continue
            if any(tp == v and abs(tf - t) <= 12 for tp, tf, _ in tech_events): continue  # teched
            k = fidx.get(t)
            if k is None: continue
            hp0 = fr[k][v]['hp']; hp1 = min(fr[j][v]['hp'] for j in range(k, min(len(fr), k + 100)))
            if hp0 - hp1 <= 0: continue
            dmg, rec, cashed, _ = life_change(v, k, min(len(fr) - 1, k + 97))
            first = dict(frame=t, attacker=a, victim=v, attacker_action_id=fr[k][a]['action_id'], attacker_combo_damage=hp0 - hp1,
                         victim_damage_info=None, victim_hp=hp1, victim_posY=fr[k][v]['posY'], round=fr[k]['round'])
            combos.append({'attacker': a, 'victim': v, 'round': fr[k]['round'], 'first': first, 'hits': [first],
                           'damage': dmg if (dmg or rec) else hp0 - hp1, 'recoverable': rec, 'white_cashed': cashed,
                           'vs_parry': any(abs(t - x) <= 2 for x in throw_parry_frames)})
    combos.sort(key=lambda c: c['first']['frame'])

    rows = []
    for n, c in enumerate(combos, 1):
        a, v, h = c['attacker'], c['victim'], c['first']
        f = frame(h['frame']) or {}
        rnd = c['round'] + 1
        timer = f.get('round_timer')
        move = mname(names, a, h['attacker_action_id'])
        label = pretty(move, side_char[a])
        trade = not move.startswith(('ATK_', 'SPA_', 'SA', 'CAA', 'NG'))
        char = side_char[a]
        vst = (f.get(v) or {}).get('act_st_name')
        vmove_before = ''
        for x in reversed(lookback(h['frame'], v, 15)):
            if x.get('act_st_name') not in ('DAMAGE',):
                vst = x.get('act_st_name'); vmove_before = pretty(mname(names, v, x.get('action_id')), side_char[v]); break
        if not move.startswith(('ATK_', 'SPA_', 'SA', 'CAA', 'NG')):
            found = False
            for x in reversed(lookback(h['frame'], a, 20)):
                mv2 = mname(names, a, x.get('action_id'))
                if mv2.startswith(('ATK_', 'SPA_', 'SA', 'CAA', 'NG')):
                    move, label = mv2, pretty(mv2, side_char[a]); found = True; break
            # lingering hitboxes set up earlier (Arjun's Divine Pillar and Breathing Ring hit while he walks or jumps)
            if not found and side_char[a] in LINGER:
                for x in reversed(lookback(h['frame'], a, 600)):
                    mv2 = mname(names, a, x.get('action_id'))
                    if mv2.startswith(LINGER[side_char[a]]):
                        move, label = mv2, pretty(mv2, side_char[a]); trade = False; break
        ast_prev = [x.get('act_st_name') for x in lookback(h['frame'], a, 40)]
        vst_prev = [x.get('act_st_name') for x in lookback(h['frame'], v, 40)]
        vhist_prev = [x.get('blockstun') or 0 for x in lookback(h['frame'], v, 25)]
        ahist_prev = [x.get('blockstun') or 0 for x in lookback(h['frame'], a, 35)]
        # a throw pressed while defending (just out of blockstun or getting up) is a throw tech attempt, not an offensive throw
        if vmove_before == 'Throw attempt' and (any(bb > 0 for bb in vhist_prev) or 'GETUP' in vst_prev[-30:]):
            vmove_before = 'Throw tech attempt'
        # kind
        is_throw = move.startswith(('NGA', 'NGS')) or any(abs(t - h['frame']) <= 8 for t in throw_frames[a]) \
            or ('Throw' in move and any(0 <= h['frame'] - t <= 240 for t in throw_frames[a]))   # command grabs
        kind = 'throw' if is_throw else 'clean hit'
        base = base_damage(char, label)
        first_dmg = h['attacker_combo_damage'] or 0
        hstun = (h['victim_damage_info'] or {}).get('time')
        if not is_throw and base and first_dmg >= base * 1.15:
            kind = 'counter hit'
            c['hitstun'] = hstun
        # reversal: attacker was getting up (or in blockstun) just before starting this move
        a_frame_in_move = (f.get(a) or {}).get('action_frame') or 0
        recent_a = [x.get('act_st_name') for x in lookback(h['frame'], a, a_frame_in_move + 4)]
        reversal = 'GETUP' in recent_a[: 6] if recent_a else False
        # also a reversal: a special / super started on reversal timing straight out of blockstun
        if not reversal and move.startswith(('SPA_', 'SA', 'CAA')):
            pre = lookback(h['frame'], a, a_frame_in_move + 4)[: 6]
            reversal = any((x.get('blockstun') or 0) > 0 for x in pre[:3])
        if reversal and not is_throw:
            kind = 'reversal'
        # situation
        v_recent_getup = 'GETUP' in vst_prev[-40:]
        v_recent_block = any(b > 0 for b in vhist_prev)
        a_recent_block = any(b > 0 for b in ahist_prev)
        # was the move that got hit the one that was blocked (unsafe), or a new press after the attacker was free again?
        new_press_after_block = False
        if a_recent_block:
            A_, V_ = lookback(h['frame'], a, 35), lookback(h['frame'], v, 35)
            last_bs = max(j for j, x in enumerate(A_) if (x.get('blockstun') or 0) > 0)
            v_now = next((x for x in reversed(V_) if x.get('act_st_name') != 'DAMAGE'), None)
            if v_now is not None and last_bs < len(V_):
                k_now = len(V_) - 1 - next(j for j, x in enumerate(reversed(V_)) if x is v_now)
                # a new action started after the attacker left blockstun
                # (a special or super changing action id mid-move, e.g. its landing phase, is the same move)
                def _new(j):
                    cur, prv = V_[j].get('act_st_name'), V_[j - 1].get('act_st_name')
                    if cur not in ATTACK_STATES or V_[j].get('action_id') == V_[j - 1].get('action_id'): return False
                    return prv not in ATTACK_STATES or prv != cur or cur == 'ATCK'
                new_press_after_block = any(_new(j) for j in range(last_bs + 1, k_now + 1))
        if reversal: situation = 'defense'
        elif v_recent_getup: situation = 'oki'
        elif v_recent_block: situation = 'pressure'
        elif kind == 'counter hit' and vst in ATTACK_STATES and a_recent_block: situation = 'punish'
        else: situation = 'neutral'
        airborne = vst in JUMP_STATES or (h.get('victim_posY') or 0) > 0.3
        attacker_air = ((f.get(a) or {}).get('posY') or 0) > 0.3
        anti_air = bool(airborne and not attacker_air and not is_throw)
        # what the victim was doing
        if reversal: lens = 'Own offense beaten by a reversal'
        elif airborne and not is_throw: lens = 'Jumped'
        elif attacker_air and not is_throw: lens = 'Jumped in on (no anti-air)'
        elif is_throw: lens = 'Blocking, opened up' if (v_recent_block or v_recent_getup) else 'Walked in'
        elif vst in ATTACK_STATES or vst == 'PARRY':
            vmove = mname(names, v, (f.get(v) or {}).get('action_id'))
            if vmove.startswith('ATK_CTA'): lens = 'Drive Rush / Impact checked'
            elif a_recent_block and new_press_after_block: lens = 'Pressed after turn ended'   # their move was blocked, then they pressed again once the attacker was free
            elif a_recent_block: lens = 'Unsafe move punished'            # their move was blocked, then punished in its recovery
            elif v_recent_getup: lens = 'Challenging okizeme'             # pressed on wake-up into the oki
            elif v_recent_block: lens = 'Challenging pressure'            # pressed in their blockstring / pressure
            elif kind == 'punish counter': lens = 'Whiff punished'        # caught in the recovery of a whiffed move
            else: lens = 'Counter-hit at mid range'                       # pressed in neutral, counter-hit on startup
        elif vst in ('DEF', 'JDEF') or v_recent_block: lens = 'Blocking, opened up'
        elif vst in MOVE_STATES: lens = 'Walked in'
        else: lens = 'Unclear / super'
        rows.append(dict(hit_id=f'{rid[:3]}-{n:02d}', set_id='Set 1', game_id=rid, game_no=game_no, round=rnd,
                         round_timer=timer, frame=h['frame'], attacker=side_name[a], victim=side_name[v],
                         damage=c['damage'], recoverable=c.get('recoverable') or 0, white_cashed=c.get('white_cashed') or 0, hits_in_combo=len(c['hits']), starter=label, starter_raw=move,
                         first_hit_type=None, hit_kind=kind, first_hit_damage=first_dmg, first_hitstun=hstun,
                         anti_air=anti_air, situation=situation, lens=lens if side_name[v] == focus else None,
                         victim_state=vst, victim_move=vmove_before, note='reversal' if reversal else ('throw vs Drive Parry' if c.get('vs_parry') else ('trade' if trade else None))))

    # punish counter = counter hit with +2 hitstun over that move's counter-hit hitstun
    by = C.defaultdict(list)
    for r in rows:
        if r['hit_kind'] == 'counter hit' and r['first_hitstun']: by[(r['attacker'], r['starter'])].append(r['first_hitstun'])
    for r in rows:
        if r['hit_kind'] == 'counter hit' and r['first_hitstun']:
            lo = min(by[(r['attacker'], r['starter'])])
            if r['first_hitstun'] >= lo + 2 and len(set(by[(r['attacker'], r['starter'])])) > 1:
                r['hit_kind'] = 'punish counter'
                if r['situation'] == 'neutral': r['situation'] = 'punish'
                if r['lens'] == 'Counter-hit at mid range': r['lens'] = 'Whiff punished'

    # ---- events
    events = []

    def lethal_burnout(side, n):
        """True when the burnout starts inside the player's own combo and that combo kills (the opponent is in hitstun from
        the burnout until their HP hits 0, in the same round): spending everything for lethal isn't counted as a burnout."""
        o = 'p2' if side == 'p1' else 'p1'
        if not any(fr[j][o].get('act_st_name') == 'DAMAGE' for j in range(n, min(len(fr), n + 10))): return False
        for j in range(n, min(len(fr), n + 360)):
            if fr[j]['round'] != fr[n]['round']: return False
            if fr[j][o]['hp'] <= 0: return True
            if j > n + 10 and fr[j][o].get('act_st_name') != 'DAMAGE' and fr[j][o]['hp'] > 0: return False
        return False
    for side in ('p1', 'p2'):
        start = None
        for n, f in enumerate(fr):
            b = bool(f[side]['burnout'])
            if b and start is None: start, sn = f, n
            if not b and start is not None:
                lethal = lethal_burnout(side, sn)
                events.append(dict(game_id=rid, round=start['round'] + 1, round_timer=start['round_timer'], frame=start['i'],
                                   player=side_name[side], type='lethal burnout' if lethal else 'burnout',
                                   note=f"{(f['i'] - start['i']) / 60:.1f}s" + (' (spent for a combo that killed; not counted as a burnout)' if lethal else '')))
                start = None
    for typ, lst in (('perfect parry', perfect_events), ('throw tech', tech_events), ('drive reversal', dr_events)):
        for p, fi, rnd in lst:
            ff = frame(fi) or {}
            events.append(dict(game_id=rid, round=rnd, round_timer=ff.get('round_timer'), frame=fi, player=side_name[p], type=typ, note=None))

    # ---- Drive Rush types, from the opponent's state on the frame the Drive Rush starts:
    #   'combo drive rush cancel'    - opponent getting hit (DAMAGE state), i.e. cancelled from a confirmed hit
    #   'pressure drive rush cancel' - opponent blocking (DEF state or blockstun), i.e. in a blockstring
    #   'whiff drive rush cancel'    - a 3-bar cancel with the opponent neither hit nor blocking (cancelled from a whiffed button)
    #   'raw drive rush'             - not a cancel (Drive Parry > Drive Rush, 1 bar in all), wherever the opponent is
    # note = the move it came out of, plus damage the opponent took in the next 90 frames
    for side, opp in (('p1', 'p2'), ('p2', 'p1')):
        prev = None
        for k, f in enumerate(fr):
            n = mname(names, side, f[side]['action_id'])
            if n != prev and n.startswith(('ATK_CTA_RUSH', 'ATK_CTA_DASH', 'DRIVE_RUSH')):   # Chun-Li / C. Viper carry a bare DRIVE_RUSH
                o = f[opp]
                st = o.get('act_st_name')
                # a cancel costs 3 bars in one drop (about 10 frames in); Drive Parry > Drive Rush costs 0.5 + 0.5, even in a blockstring
                cancel = any((fr[j - 1][side].get('drive') or 0) - (fr[j][side].get('drive') or 0) >= 25000 for j in range(max(1, k - 5), min(len(fr), k + 25)))
                typ = ('raw drive rush' if not cancel else 'combo drive rush cancel' if st == 'DAMAGE' else
                       'pressure drive rush cancel' if st == 'DEF' or (o.get('blockstun') or 0) > 0 else 'whiff drive rush cancel')
                came = next((mname(names, side, fr[j][side]['action_id']) for j in range(k - 1, max(0, k - 40), -1)
                             if mname(names, side, fr[j][side]['action_id']) != n), None)
                dmg = o['hp'] - min(fr[j][opp]['hp'] for j in range(k, min(len(fr), k + 90)))
                events.append(dict(game_id=rid, round=f['round'] + 1, round_timer=f['round_timer'], frame=f['i'], player=side_name[side], type=typ,
                                   note=f"from {pretty(came, side_char[side]) if came else '?'}; {dmg} damage in the next 1.5s"))
            prev = n

    # ---- rounds & game result
    played = sorted(set(f['round'] for f in fr))
    rr = [r for r in info.get('round_results', []) if r['round'] - 1 in played and r['finish_type']]
    winners = [side_name['p1'] if r['win_player'] == 0 else side_name['p2'] for r in rr]
    if not info.get('round_results'):
        # local / offline captures carry no round results: the first player to reach 0 HP loses the round; on a timeout, more HP wins
        winners = []
        for r_ in played:
            fs = [f for f in fr if f['round'] == r_]
            ko = next((f for f in fs if f['p1']['hp'] <= 0 or f['p2']['hp'] <= 0), None)
            if ko: winners.append(side_name['p2'] if ko['p1']['hp'] <= 0 and ko['p2']['hp'] > 0 else side_name['p1'] if ko['p2']['hp'] <= 0 and ko['p1']['hp'] > 0 else None)
            elif fs and fs[-1]['round_timer'] <= 0 and fs[-1]['p1']['hp'] != fs[-1]['p2']['hp']: winners.append(side_name['p1'] if fs[-1]['p1']['hp'] > fs[-1]['p2']['hp'] else side_name['p2'])
            else: winners.append(None)
        winners = [w for w in winners if w]

    # ---- timings: what each player does after blockstun ends and on wake-up (frames until first action)
    timings = []
    for side in ('p1', 'p2'):
        k = 1
        while k < len(fr):
            was, now = fr[k - 1][side], fr[k][side]
            ev = None
            if (was.get('blockstun') or 0) > 0 and (now.get('blockstun') or 0) == 0 and now.get('act_st_name') not in ('DAMAGE',): ev = 'after block'
            elif was.get('act_st_name') == 'GETUP' and now.get('act_st_name') != 'GETUP': ev = 'wake-up'
            if ev:
                act, wait = 'nothing (30f)', None
                for j in range(k, min(len(fr), k + 30)):
                    st = fr[j][side].get('act_st_name')
                    if (fr[j][side].get('blockstun') or 0) > 0 or st == 'DAMAGE':
                        act, wait = 'blocked/hit again', j - k; break
                    if st in ATTACK_STATES | JUMP_STATES | {'PARRY', 'DASH', 'KDASH'}:
                        mv = pretty(mname(names, side, fr[j][side].get('action_id')), side_char[side])
                        act, wait = (st.lower() + ': ' + mv), j - k; break
                timings.append(dict(game_id=rid, round=fr[k]['round'] + 1, round_timer=fr[k]['round_timer'], player=side_name[side],
                                    event=ev, action=act, frames_until=wait))
            k += 1

    # ---- move usage
    usage = {}
    for side in ('p1', 'p2'):
        cnt, prev, plab = C.Counter(), None, None
        for f in fr:
            a = f[side]['action_id']
            if a != prev:
                lab = pretty(mname(names, side, a), side_char[side])
                core = re.sub(r' \((L|M|H|OD)\)$', '', lab).split(' > ')[0]
                # count a move once per use: its later phases (another action id, same move) don't count again
                if (f[side]['action_frame'] or 0) <= 1 and core != plab:
                    n = mname(names, side, a)
                    if n.startswith(('ATK_', 'SPA_', 'SA', 'CAA', 'NGS', 'DPA')) or 'JUMP_F_START' in n or 'JUMP_B_START' in n or 'JUMP_N' in n or any(n.startswith(k) for k, _ in CHAR_SPECIALS.get(side_char[side], [])):
                        cnt[lab] += 1
                plab = core
            prev = a
        usage[side_name[side]] = cnt.most_common()

    # ---- resource log: Drive and super spent per round, by what it was spent on
    #   Drive drops are counted while the player isn't being hit or blocking (so chip and Drive Impact on block don't count);
    #   super spends are each drop of the super gauge (1 bar = 10,000), labelled with the move being performed.
    resources = []
    STUN_ST = {'DAMAGE', 'DEF', 'GETUP', 'NOKI', 'UKEMI', 'HOLD', 'DOWN'}
    def drive_cat(lab):
        for k in ('Drive Rush', 'Drive Parry', 'Drive Impact', 'Drive Reversal'):
            if lab.startswith(k): return k
        if '(OD)' in lab or lab.endswith('_OD') or '_EX' in lab: return 'OD specials'
        return 'other'
    for side in ('p1', 'p2'):
        per = {}
        for k in range(1, len(fr)):
            a, pa = fr[k][side], fr[k - 1][side]
            rnd = fr[k]['round'] + 1
            R = per.setdefault(rnd, dict(game_id=rid, round=rnd, player=side_name[side], drive={c: 0 for c in ('Drive Rush', 'Drive Parry', 'Drive Impact', 'Drive Reversal', 'OD specials', 'other')},
                                          supers=[], burnouts=0, drive_end=None, super_end=None, drc=0))
            st_ = a.get('act_st_name')
            stunned = st_ in STUN_ST or (a.get('blockstun') or 0) > 0 or (a.get('hitstun') or 0) > 0
            dd = (pa.get('drive') or 0) - (a.get('drive') or 0)
            if dd > 0 and not stunned and not pa.get('burnout'):   # (the drop that empties the gauge starts burnout on the same frame)
                lab = pretty(mname(names, side, a.get('action_id')), side_char[side])
                cat = drive_cat(lab)
                if cat == 'other' and dd >= 15000: cat = 'OD specials'   # a 2-bar drop at once is an OD move
                R['drive'][cat] += dd
                if cat == 'Drive Rush' and dd >= 25000: R['drc'] += dd      # the 3-bar drop of a Drive Rush cancel
            ds = (pa.get('super') or 0) - (a.get('super') or 0)
            in_super = st_ == 'SUPER'
            if ds >= 5000:
                raw_ = mname(names, side, a.get('action_id')); lab = pretty(raw_, side_char[side])
                last = R['supers'][-1] if R['supers'] else None
                # one super, not two, when the player never left the super animation since the last drain and this drain isn't
                # a fresh super start: e.g. Terry's SA2 takes a 3rd bar after it starts (and a 3rd hit for 1 Drive bar)
                cont = last is not None and all(fr[j][side].get('act_st_name') == 'SUPER' for j in range(last['_k'], k + 1))
                if cont and not re.search(r'_start$', raw_, re.I):
                    last['bars'] = round(last['bars'] + ds / 10000, 1); last['_k'] = k
                    if last['bars'] > last['level']: last['extended'] = True
                else:
                    R['supers'].append(dict(round_timer=fr[k]['round_timer'], bars=round(ds / 10000, 1), move=lab, _k=k,
                                            level=min(3, max(1, round(ds / 10000))), extended=False, drive=0))
            # Drive spent while a super is running (Terry's SA2 3rd hit) goes on that super too
            if in_super and dd > 0 and not pa.get('burnout') and R['supers'] and all(fr[j][side].get('act_st_name') == 'SUPER' for j in range(R['supers'][-1]['_k'], k + 1)):
                R['supers'][-1]['drive'] = round(R['supers'][-1]['drive'] + dd / 10000, 2)
            R['drive_end'] = a.get('drive'); R['super_end'] = a.get('super')
        burn_ev = C.Counter(e['round'] for e in events if e['player'] == side_name[side] and e['type'] == 'burnout')
        for R in per.values():
            for x in R['supers']:
                x.pop('_k', None)
                if x['extended']: x['move'] += ' extended'
            R['burnouts'] = burn_ev.get(R['round'], 0)
            R['drive_bars'] = {c: round(v / 10000, 2) for c, v in R['drive'].items()}; del R['drive']
            R['drive_total_bars'] = round(sum(R['drive_bars'].values()), 2)
            R['drive_rush_cancel_bars'] = round(R.pop('drc') / 10000, 2)   # part of drive_bars['Drive Rush'] spent on cancels (rest = raw)
            R['super_bars'] = round(sum(x['bars'] for x in R['supers']), 1)
            resources.append(R)

    # ---- Drive efficiency: per-combo spend / gain, knockdown advantage, contact gains and losses, parries
    STAGE_EDGE = 7.65            # |posX| at the corner (largest seen in captures ~7.70)
    REGEN = 60                   # per-frame rises up to this are passive regen (40, or 60-100 walking forward)
    VICTIM_BUSY = {'DAMAGE', 'DOWN', 'NOKI', 'GETUP', 'UKEMI', 'HOLD'}
    other = {'p1': 'p2', 'p2': 'p1'}
    k_of = lambda fi: fidx.get(fi, 0)
    def fam(n):                  # move family, so a special's _LAND / _END recovery isn't read as a new action
        return re.sub(r'_(START|END|LAND|LAND_EX|Loop|HIT|MISS|AIR|\d+)$', '', n or '')
    for r, c in zip(rows, combos):
        a, v = c['attacker'], c['victim']
        k0 = k_of(c['first']['frame']); kl = k_of(max(h['frame'] for h in c['hits']))
        # victim actionable again: first frame after the last hit out of hitstun / knockdown / wake-up
        # (a knocked-down victim is free on the first frame out of the knockdown / wake-up states, even if that frame
        #  blocks a meaty or gets hit by one; otherwise on the first frame out of hitstun)
        kv, knocked = None, False
        for j in range(kl + 1, min(len(fr), kl + 400)):
            if fr[j]['round'] != fr[kl]['round']: break
            st_ = fr[j][v].get('act_st_name')
            if st_ in ('DOWN', 'NOKI', 'GETUP', 'UKEMI'): knocked = True; continue
            if knocked or (st_ not in ('DAMAGE', 'HOLD') and not (fr[j][v].get('hitstun') or 0)): kv = j; break
        rise = None
        if knocked:
            for j in range(kl, kv or kl):
                n_ = mname(names, v, fr[j][v].get('action_id'))
                if 'TECH_BR' in n_: rise = 'back recovery'; break
                if 'TECH_FN' in n_: rise = 'normal recovery'; break
                if 'DN_STD' in n_: rise = 'hard knockdown'
        # attacker free: first frame after the last hit in a movement state, or starting a new (non-recovery) action
        ender = fam(mname(names, a, fr[kl][a].get('action_id'))); ka = None
        for j in range(kl + 1, min(len(fr), kl + 400)):
            x, px = fr[j][a], fr[j - 1][a]
            if x.get('act_st_name') in MOVE_STATES: ka = j; break
            if x.get('action_id') != px.get('action_id'):
                n_ = mname(names, a, x.get('action_id'))
                if n_.startswith(('ATK_', 'SPA_', 'SA', 'CAA', 'NG', 'DPA', 'BAS_JUMP', 'BAS_DASH')) and fam(n_) != ender and not n_.endswith(('_LAND', '_END')):
                    ka = j; break
        r['kd_adv'] = (kv - ka) if (kv is not None and ka is not None) else None
        # the victim never got free before the attacker hit again (a split combo / juggle reset): no advantage to measure
        nxt = [k_of(c2['first']['frame']) for c2 in combos if c2['attacker'] == a and k_of(c2['first']['frame']) > kl]
        if nxt and kv is not None and min(nxt) <= kv: r['kd_adv'] = None
        # outside knockdowns this is plain frame advantage after the combo; very large values come from crumples / Drive Impact
        # clashes the rules above don't model, so they're left out
        if r['kd_adv'] is not None and not knocked and abs(r['kd_adv']) > 60: r['kd_adv'] = None
        r['knockdown'] = rise or ('knockdown' if knocked else None)
        # spend inside the combo: from 20 frames before the first hit (raw Drive Rush / Drive Impact in) to the attacker being free
        ke = ka or min(len(fr) - 1, kl + 60)
        spend = gain = vdd = sup = 0
        for j in range(max(1, k0 - 20), ke + 1):
            x, px, y, py = fr[j][a], fr[j - 1][a], fr[j][v], fr[j - 1][v]
            dd = (x.get('drive') or 0) - (px.get('drive') or 0)
            if dd < 0 and not px.get('burnout'): spend -= dd
            elif dd > REGEN: gain += dd
            if j >= k0 - 1:
                vd = (y.get('drive') or 0) - (py.get('drive') or 0)
                if vd < 0 and not py.get('burnout'): vdd -= vd
            ds = (px.get('super') or 0) - (x.get('super') or 0)
            if ds > 0 and j >= k0 - 20: sup += ds
        r['drive_spent'] = round(spend / 10000, 2); r['drive_gained'] = round(gain / 10000, 2)
        r['drive_damage'] = round(vdd / 10000, 2); r['super_spent'] = round(sup / 10000, 2)
        px_ = fr[min(len(fr) - 1, kv or ke)][v].get('posX')
        r['corner_dist'] = round(STAGE_EDGE - abs(px_), 2) if px_ is not None else None
        r['victim_drive_after'] = round((fr[min(len(fr) - 1, kv or ke)][v].get('drive') or 0) / 10000, 2)

    # contact gains / losses and parry regain, per player per round (added to the resource rows)
    contact = {}
    for side in ('p1', 'p2'):
        o = other[side]
        for k in range(1, len(fr)):
            x, px, y = fr[k][side], fr[k - 1][side], fr[k][o]
            if px.get('burnout') or fr[k]['round'] != fr[k - 1]['round']: continue   # (the drop that empties the gauge still counts)
            dd = (x.get('drive') or 0) - (px.get('drive') or 0)
            if not dd: continue
            Rr = contact.setdefault((side, fr[k]['round'] + 1), C.Counter())
            st_ = x.get('act_st_name')
            if st_ == 'PARRY' or px.get('act_st_name') == 'PARRY':
                if dd > REGEN: Rr['parry_regain'] += dd
            elif dd > REGEN:
                if y.get('act_st_name') == 'DEF' or (y.get('blockstun') or 0) > 0: Rr['gain_block'] += dd
                elif y.get('act_st_name') == 'DAMAGE' or (y.get('hitstun') or 0) > 0: Rr['gain_hit'] += dd
            elif dd < 0:
                if st_ == 'DEF' or (x.get('blockstun') or 0) > 0: Rr['loss_block'] -= dd
                elif st_ in ('DAMAGE', 'HOLD') or (x.get('hitstun') or 0) > 0: Rr['loss_hit'] -= dd
    for R in resources:
        side = 'p1' if R['player'] == side_name['p1'] else 'p2'
        cc = contact.get((side, R['round']), C.Counter())
        for kk in ('gain_hit', 'gain_block', 'parry_regain', 'loss_block', 'loss_hit'):
            R[kk] = round(cc.get(kk, 0) / 10000, 2)
        # Drive lost to Drive Impact hits and punish counters (from this round's combos against this player)
        mine = [r for r in rows if r['round'] == R['round'] and r['victim'] == R['player']]
        R['loss_hit_drive_impact'] = round(sum(r['drive_damage'] or 0 for r in mine if (r['starter'] or '').startswith('Drive Impact')), 2)
        R['loss_hit_punish_counter'] = round(sum(r['drive_damage'] or 0 for r in mine if r['hit_kind'] == 'punish counter'), 2)

    # parry episodes: cost, hits parried, Drive regained, perfect parry, what happened next
    parries = []
    for side in ('p1', 'p2'):
        o = other[side]; k = 1
        while k < len(fr):
            if fr[k][side].get('act_st_name') == 'PARRY' and fr[k - 1][side].get('act_st_name') != 'PARRY':
                k0 = k; d0 = fr[k - 1][side].get('drive') or 0
                while k < len(fr) and fr[k][side].get('act_st_name') == 'PARRY': k += 1
                k1 = min(k, len(fr) - 1)
                ups = [(fr[j][side].get('drive') or 0) - (fr[j - 1][side].get('drive') or 0) for j in range(k0, k1 + 1)]
                regain = sum(u for u in ups if u > REGEN); cost = -sum(u for u in ups if u < 0)
                fi0, fi1 = fr[k0]['i'], fr[k1]['i']
                perfect = any(p_ == side and fi0 - 2 <= f_ <= fi1 + 2 for p_, f_, _ in perfect_events)
                nxt = 'nothing'
                for j in range(k0, min(len(fr), k1 + 40)):
                    st_ = fr[j][side].get('act_st_name')
                    if st_ == 'HOLD': nxt = 'thrown'; break
                    if st_ == 'DAMAGE': nxt = 'hit'; break
                    n_ = mname(names, side, fr[j][side].get('action_id'))
                    if j > k1 and n_.startswith(('ATK_CTA_RUSH', 'DRIVE_RUSH')): nxt = 'raw drive rush'; break
                    if j > k1 and fr[j][o].get('act_st_name') == 'DAMAGE': nxt = 'punished them'; break
                parries.append(dict(game_id=rid, round=fr[k0]['round'] + 1, round_timer=fr[k0]['round_timer'], player=side_name[side],
                                    frames=k1 - k0, drive_before=round(d0 / 10000, 2), cost=round(cost / 10000, 2), hits_parried=sum(1 for u in ups if u > REGEN),
                                    regained=round(regain / 10000, 2), net=round((regain - cost) / 10000, 2), perfect=perfect, next=nxt))
            k += 1

    # ---- block punish windows: each time a player leaves blockstun while the attacker is still recovering from the move
    # they blocked, by 5 frames or more (frames measured from the capture: blockstun end -> attacker free / new action).
    # A move restarted before the blockstun ended (5MK into 5MK, chained jabs) is a frame trap, not a window. Range is the
    # distance between the players when the defender is free: 'close' is in reach of a 4-5f button, 'mid' needs a long
    # button, 'far' (fireballs, spaced limbs) isn't a block punish at all. frame_data/<char>.json (move label -> wiki block
    # advantage, filled during Full reviews) confirms the measured value when it has the move.
    punish_windows = []
    FREE_ST = MOVE_STATES | JUMP_STATES | {'PARRY', 'DEF'}
    for side in ('p1', 'p2'):
        o = other[side]; s0 = None
        for k in range(1, len(fr)):
            if fr[k].get('fight_st') != 4: s0 = None; continue
            b0, b1 = fr[k - 1][side].get('blockstun') or 0, fr[k][side].get('blockstun') or 0
            if b1 > 0 and b0 == 0: s0 = k
            if not (b0 > 0 and b1 == 0) or s0 is None or fr[k][side].get('act_st_name') == 'DAMAGE': continue
            x = fr[k][o]; aid = x.get('action_id'); ost = x.get('act_st_name')
            if ost in FREE_ST or ost in ('DAMAGE', 'HOLD', 'GETUP', 'DOWN') or ost in JUMP_STATES: continue
            if any(fr[j][o].get('action_id') != aid or (fr[j][o].get('action_frame') or 0) < (fr[j - 1][o].get('action_frame') or 0) for j in range(s0 + 1, k + 1)):
                continue   # cancelled or restarted during the blockstun
            e = None; hit = False
            for j in range(k, min(len(fr), k + 150)):
                y = fr[j][o]; st = y.get('act_st_name')
                if st == 'DAMAGE' or (y.get('hitstun') or 0) > 0: e = j; hit = True; break
                if (fr[j][side].get('blockstun') or 0) > 0: break   # blocked something again (a projectile, a second hit)
                if st in FREE_ST or y.get('action_id') != aid or (j > k and (y.get('action_frame') or 0) < (fr[j - 1][o].get('action_frame') or 0)):
                    e = j; break
            if e is None: continue
            adv = None if hit else -(e - k)
            if adv is not None and adv > -5: continue
            res, act = ('punished', None) if hit else (None, None)
            if not hit:
                for j in range(k, e + 1):
                    st = fr[j][side].get('act_st_name')
                    if st == 'DAMAGE': res = 'got hit'; break
                    if st in ('ATCK', 'SPECIAL', 'SUPER', 'THROW'):
                        res = 'pressed, no hit'; act = pretty(mname(names, side, fr[j][side].get('action_id')), side_char[side]); break
                    if st == 'PARRY': res = 'drive parry'; break
                    if st in JUMP_STATES: res = 'jumped'; break
                    if st in ('DASH', 'KDASH'): res = 'dashed'; break
                res = res or 'held / walked'
            dist = abs((fr[k][side].get('posX') or 0) - (x.get('posX') or 0))
            move = pretty(mname(names, o, aid), side_char[o]); wiki = block_adv(side_char[o], move)
            if wiki is None: check = 'unverified'
            elif adv is None: check = 'wiki %+d' % wiki
            # multi-hit / late-blocked moves (DPs, OD specials) measure less minus than the wiki's first-hit value; the window is still real
            else: check = ('ok' if abs(wiki - adv) <= 3 else 'later hit blocked' if wiki < adv else 'wiki disagrees') + ' (wiki %+d)' % wiki
            if hit and wiki is not None and wiki > -5: continue
            punish_windows.append(dict(game_id=rid, round=fr[k]['round'] + 1, round_timer=fr[k]['round_timer'], defender=side_name[side], attacker=side_name[o],
                                       move=move, adv=adv, distance=round(dist, 2), range=('close' if dist <= PUNISH_CLOSE else 'mid' if dist <= PUNISH_MID else 'far'),
                                       result=res, action=act, wiki_adv=wiki, check=check))

    # button economy (Theory #4): new attack / special / super / throw states per player per round. A press is a
    # "decision press" when the opponent isn't being hit, knocked down or getting up, so combo and oki presses
    # (which the winning player gets more of) don't inflate the count. Chained buttons in one combo count once.
    ACT_ST, BUSY_ST = ('ATCK', 'SPECIAL', 'SUPER', 'THROW'), ('DAMAGE', 'GETUP', 'DOWN', 'NOKI')
    pc = C.defaultdict(C.Counter)
    for side in ('p1', 'p2'):
        o = other[side]
        for k in range(1, len(fr)):
            st_, pst = fr[k][side].get('act_st_name'), fr[k - 1][side].get('act_st_name')
            if st_ in ACT_ST and pst not in ACT_ST and fr[k]['round'] == fr[k - 1]['round']:
                key_ = (side_name[side], fr[k]['round'] + 1)
                pc[key_]['presses'] += 1
                if fr[k][o].get('act_st_name') not in BUSY_ST: pc[key_]['decision_presses'] += 1
    presses = [dict(game_id=rid, round=r_, player=p_, presses=c_['presses'], decision_presses=c_['decision_presses']) for (p_, r_), c_ in sorted(pc.items(), key=lambda x: (x[0][1], x[0][0]))]

    # ---- decision presses in detail (tools/full_review_decision_presses.py): for each decision press, the situation (from the
    # 20 frames before: air button, vs a jump, wake-up, after blocking, own pressure, oki, after a hit, or neutral by
    # distance), what the opponent was doing, and the first thing that happened within ~70 frames.
    decisions = []
    MOVE_ST = ('ATCK', 'SPECIAL', 'SUPER', 'THROW')
    by_att = C.defaultdict(dict)
    for r_ in rows: by_att[r_['attacker']].setdefault(r_['frame'], r_)
    for side in ('p1', 'p2'):
        o = other[side]
        for k in range(1, len(fr)):
            a_, pa_ = fr[k][side], fr[k - 1][side]
            if not (a_.get('act_st_name') in MOVE_ST and pa_.get('act_st_name') not in MOVE_ST and fr[k]['round'] == fr[k - 1]['round']): continue
            ob = fr[k][o]
            if ob.get('act_st_name') in BUSY_ST: continue
            mv = pretty(mname(names, side, a_.get('action_id')), side_char[side])
            dist = abs((a_.get('posX') or 0) - (ob.get('posX') or 0))
            prev = [fr[j][side] for j in range(max(0, k - 20), k)]
            oprev = [fr[j][o] for j in range(max(0, k - 20), k)]
            if (a_.get('posY') or 0) > 0.3 or a_.get('act_st_name') in JUMP_STATES: ctx = 'air button'
            elif (ob.get('posY') or 0) > 0.3 or ob.get('act_st_name') in JUMP_STATES: ctx = 'vs a jump'
            elif any(x.get('act_st_name') == 'GETUP' for x in prev): ctx = 'wake-up'
            elif any((x.get('blockstun') or 0) > 0 for x in prev): ctx = 'after blocking'
            elif any((x.get('blockstun') or 0) > 0 for x in oprev): ctx = 'own pressure'
            elif any(x.get('act_st_name') == 'GETUP' for x in oprev): ctx = 'oki'
            elif any(x.get('act_st_name') == 'DAMAGE' for x in oprev): ctx = 'after a hit'
            elif dist < 1.3: ctx = 'neutral close'
            elif dist < 2.6: ctx = 'neutral mid'
            else: ctx = 'neutral far'
            ost = ob.get('act_st_name')
            opp_doing = 'pressing' if ost in MOVE_ST else ('blocking' if ost == 'DEF' or (ob.get('blockstun') or 0) > 0 else ('parrying' if ost == 'PARRY' else ('rushing/dashing' if ost in ('DASH', 'KDASH') or 'RUSH' in mname(names, o, ob.get('action_id')) else 'other')))
            out_, dmg = 'whiffed / nothing', 0
            done = None
            for j in range(k, min(len(fr), k + 70)):
                fi = fr[j]['i']
                if fr[j]['round'] != fr[k]['round']: break
                r1 = by_att[side_name[side]].get(fi)
                if r1: out_, dmg = r1['hit_kind'], r1['damage']; break
                r2 = by_att[side_name[o]].get(fi)
                if r2:
                    out_ = ('got ' + r2['hit_kind']) if done is None else ('whiff punished' if r2['hit_kind'] in ('counter hit', 'punish counter') else 'got hit after')
                    dmg = -r2['damage']; break
                if fr[j][o].get('act_st_name') == 'HOLD': out_ = 'throw'; break   # being thrown (long throws deal damage after the window)
                if (fr[j][o].get('blockstun') or 0) > 0 and fr[j][o].get('act_st_name') != 'DAMAGE': out_ = 'blocked'; break
                if fr[j][o].get('act_st_name') == 'PARRY' and j > k: out_ = 'parried'; break
                if done is None and fr[j][side].get('act_st_name') not in MOVE_ST: done = j
                if done is not None and j - done > 25: break
            decisions.append(dict(game_id=rid, round=fr[k]['round'] + 1, round_timer=fr[k]['round_timer'], side=side, player=side_name[side],
                                  move=mv, ctx=ctx, dist=round(dist, 2), opp=opp_doing, outcome=out_, damage=dmg))
    return dict(decisions=decisions, info=info, rows=rows, events=events, winners=winners, timings=timings, usage=usage, side_name=side_name, side_char=side_char, resources=resources, parries=parries, presses=presses, punish_windows=punish_windows)


def main():
    out, focus, fmt, paths = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
    os.makedirs(out, exist_ok=True)
    games, hits, events, timings, report, resources, parries, presses, pwin = [], [], [], [], [], [], [], [], []
    score = C.Counter(); opp = None
    for g, p in enumerate(paths, 1):
        A = analyze(p, g, focus)
        names = list(A['side_name'].values()); opp = [n for n in names if n != focus][0]
        rs = C.Counter(A['winners']); winner = max(rs, key=rs.get)
        score[winner] += 1
        games.append(dict(game_id=A['info']['replay_id'], set_id='Set 1', game_no=g, winner=winner,
                          round_score=f"{rs[focus]}-{rs[opp]}", round_winners=', '.join(A['winners']),
                          set_score_after=f"{score[focus]}-{score[opp]}"))
        hits += A['rows']; events += A['events']; timings += A['timings']; resources += [dict(r, set_id='Set 1') for r in A['resources']]; parries += [dict(x, set_id='Set 1') for x in A['parries']]; presses += [dict(x, set_id='Set 1') for x in A['presses']]; pwin += [dict(x, set_id='Set 1') for x in A['punish_windows']]
        report.append((A, g))
    key = lambda n: re.sub(r'[^a-z0-9]', '', n.lower())
    winner = max(score, key=score.get)
    sets = [dict(set_id='Set 1', order=1, format=fmt, games=', '.join(x['game_id'] for x in games),
                 **{key(focus) + '_games': score[focus], key(opp) + '_games': score[opp]}, winner=winner,
                 progression=', '.join(x['set_score_after'] for x in games), max_deficit_overcome=None, note=None)]
    for i, e in enumerate(events, 1): e['event_id'] = f'E{i:02d}'; e['set_id'] = 'Set 1'
    for n, obj in (('sets', sets), ('games', games), ('hits', hits), ('events', events), ('timings', timings), ('resources', resources), ('parries', parries), ('presses', presses), ('punish_windows', pwin)):
        json.dump(obj, open(f'{out}/{n}.json', 'w'), indent=1, ensure_ascii=False)
    # ---- report for writing the story
    L = []
    for A, g in report:
        L.append(f"# Game {g} {A['info']['replay_id']}: {A['side_name']['p1']} ({A['side_char']['p1']}) vs {A['side_name']['p2']} ({A['side_char']['p2']}); round winners {A['winners']}")
        for e in A['events']: L.append(f"  event R{e['round']} @{e['round_timer']}: {e['player']} {e['type']} {e['note'] or ''}")
        for r in A['rows']:
            L.append(f"  {r['hit_id']} R{r['round']} @{r['round_timer']} {r['attacker']:>7} {r['damage']:>5} {r['starter']:<22} {r['hit_kind']:<14} {r['situation']:<8} aa={int(r['anti_air'])} victim:{r['victim_state']} lens={r['lens']} | victim was: {r['victim_move']}")
        for p, u in A['usage'].items(): L.append(f"  usage {p}: {u[:30]}")
        for r in A['resources']:
            spent = ', '.join(f"{k} {v}" for k, v in r['drive_bars'].items() if v)
            sup = '; '.join(f"L{x.get('level') or min(3, max(1, round(x['bars'])))} {x['move']} ({x['bars']:g} bars{', +%g Drive' % x['drive'] if x.get('drive') else ''}) @{x['round_timer']}" for x in r['supers'])
            L.append(f"  resources R{r['round']} {r['player']}: Drive {r['drive_total_bars']} bars ({spent or 'none'}); super {r['super_bars']} bars ({sup or 'none'}); burnouts {r['burnouts']}; ended with {round((r['drive_end'] or 0) / 10000, 1)} Drive, {round((r['super_end'] or 0) / 10000, 1)} super")
            L.append(f"    contact R{r['round']} {r['player']}: gained {r['gain_hit']} on hit, {r['gain_block']} on block, {r['parry_regain']} from parries; lost {r['loss_block']} blocking, {r['loss_hit']} getting hit (Drive Impact {r['loss_hit_drive_impact']}, punish counters {r['loss_hit_punish_counter']})")
    L.append('# Drive efficiency: combos that spent Drive or super, knockdown advantage (+ = attacker free first)')
    for r in hits:
        if r.get('drive_spent') or r.get('super_spent') or r.get('knockdown'):
            L.append(f"  {r['hit_id']} R{r['round']} @{r['round_timer']} {r['attacker']:>7} {r['damage']:>5} {r['starter']:<22} spent Drive {r['drive_spent']} super {r['super_spent']}, gained {r['drive_gained']}, Drive damage {r['drive_damage']}; "
                     f"{r['knockdown'] or 'no knockdown'} kd_adv={r['kd_adv']} corner_dist={r['corner_dist']}")
    L.append('# Drive Parries (cost, hits parried, Drive regained, net, what happened next)')
    for x in parries:
        L.append(f"  {x['game_id'][:3]} R{x['round']} @{x['round_timer']} {x['player']}: {x['frames']}f, cost {x['cost']}, parried {x['hits_parried']} (+{x['regained']}), net {x['net']}{' PERFECT' if x['perfect'] else ''} -> {x['next']}")
    L.append('# Block punish windows (attacker -5 or worse when the defender left blockstun; range close <= %g, mid <= %g)' % (PUNISH_CLOSE, PUNISH_MID))
    for p in sorted(set(x['defender'] for x in pwin)):
        xs = [x for x in pwin if x['defender'] == p]
        for rg in ('close', 'mid', 'far'):
            ys = [x for x in xs if x['range'] == rg]
            ys = [x for x in ys if not x['check'].startswith('wiki disagrees')]
            if ys: L.append(f"  {p} {rg}: {len(ys)} windows, punished {sum(x['result'] == 'punished' for x in ys)}, missed {sum(x['result'] != 'punished' for x in ys)} ({dict(C.Counter(x['result'] for x in ys if x['result'] != 'punished'))})")
    for x in pwin:
        if x['range'] != 'far':
            L.append(f"  {x['game_id'][:3]} R{x['round']} @{x['round_timer']} {x['defender']} blocked {x['attacker']}'s {x['move']}: "
                     f"{'hit before recovering' if x['adv'] is None else '%d' % x['adv']} at {x['distance']} ({x['range']}) -> {x['result']}{' ' + x['action'] if x['action'] else ''} [{x['check']}]")
    L.append('# Timings (frames until first action after blockstun ends / on wake-up)')
    for p in set(t['player'] for t in timings):
        for ev in ('after block', 'wake-up'):
            xs = [t for t in timings if t['player'] == p and t['event'] == ev]
            acts = C.Counter(t['action'].split(':')[0] for t in xs)
            waits = sorted(t['frames_until'] for t in xs if t['frames_until'] is not None and not t['action'].startswith('blocked'))
            L.append(f"  {p} {ev}: n={len(xs)} actions={dict(acts)} frames={waits}")
            L.append('     detail: ' + '; '.join(f"{t['game_id'][:3]} R{t['round']}@{t['round_timer']} {t['action']} ({t['frames_until']})" for t in xs[:60]))
    open(f'{out}/report.md', 'w').write('\n'.join(L))
    print('\n'.join(L[:400]))


if __name__ == '__main__':
    main()
