---
name: "sf6-character-notes"
description: "Character-specific SF6 notes and baselines (how often each character jumps, Drive Rushes, parries, throws) so replay reviews judge a player's habits against what is normal for their character. Load during every SF6 replay review."
---

# SF6 character notes

> **Installed skills only.** This plugin ships the analysis, prediction, dashboard, glossary, character notes, Drive efficiency, Juzzy and Maj skills, and .shog's coaching rules as an example. Other coaching skills named in this text (E.X. Dojo, Coosco, DoctaAfrikan) aren't included: load them only if the player has installed them, otherwise skip those checks.


What is a habit for one character is a game plan for another. A Ryu jumping 5 times a round is probably a weakness; a Cammy jumping 5 times a round is close to normal, because her dive kick gives her a strong aerial game. Before calling a rate high or low, compare it with what that character usually does.

The player adds and corrects notes here by hand. Claude suggests new ones when a review shows something character-specific, marked **(suggested)** until the player confirms or edits them. Kit facts (frame data, what's unsafe) still come from the SuperCombo wiki at review time; these notes are about how characters are played.

## How to use it in a review
1. For each player, compare their per-round rates (jumps, Drive Rushes, Drive Parries, Drive Impacts, throws, specials) with **both** the all-character average and their character's baseline below.
2. Only call something a habit or leak when it is unusual **for that character**, or when it is normal for the character but is being punished in this set.
3. Say which baseline you used and how big its sample is. Small samples (under about 20 rounds, or one player) are a hint, not a norm.
4. When a review shows a new character-specific pattern, suggest a note for this file.

## Baselines from sf6.db (2026-11-24, without .shog)
Per round, every player of that character in the database **except the configured player (.shog)**, so a character he plays isn't described by his own habits. Recompute with `tools\character_baselines.py DB` (`--include-player` to include him). **Caveats:** most characters have few rounds and players. Special counts depend on the analyzer's move-name tables and are unreliable for characters whose specials aren't named yet. Throw presses include throw techs and whiffed throws. *C.Viper: her jumps are mostly super jumps (not counted here) and her Drive Rush isn't labelled yet, so her row is unreliable.

| Character | Rounds | Players | Forward jumps | Neutral jumps | Back jumps | Drive Rush | Drive Impact | Drive Parry | Throw presses |
|---|---|---|---|---|---|---|---|---|---|
| Cammy | 313 | 10 | 2.12 | 0.57 | 0.18 | 1.94 | 0.15 | 1.53 | 1.37 |
| Juri | 146 | 7 | 1.23 | 0.32 | 0.12 | 2.72 | 0.12 | 2.71 | 1.75 |
| Terry | 98 | 8 | 0.63 | 0.18 | 0.17 | 2.49 | 0.13 | 1.91 | 1.96 |
| Ken | 78 | 6 | 1.13 | 0.54 | 0.05 | 2.77 | 0.36 | 2.41 | 1.73 |
| Mai | 72 | 4 | 1.51 | 0.81 | 0.31 | 2.49 | 0.08 | 2.49 | 1.19 |
| Sagat | 68 | 2 | 0.57 | 0.76 | 0.28 | 2.76 | 0.16 | 1.99 | 1.16 |
| Blanka | 67 | 3 | 0.99 | 0.09 | 1.12 | 1.87 | 0.33 | 1.33 | 1.57 |
| Marisa | 66 | 6 | 1.06 | 0.45 | 0.47 | 2.48 | 0.08 | 2.86 | 1.26 |
| Ryu | 53 | 6 | 1.04 | 0.43 | 0.40 | 2.19 | 0.09 | 1.70 | 1.38 |
| Yasmine | 51 | 4 | 0.67 | 0.25 | 0.27 | 3.16 | 0.10 | 3.00 | 1.49 |
| Luke | 47 | 7 | 1.13 | 0.70 | 0.19 | 2.98 | 0.04 | 2.43 | 2.04 |
| C.Viper* | 41 | 4 | 1.07 | 0.12 | 0.12 | 0.00* | 0.12 | 2.00 | 1.78 |
| Guile | 40 | 7 | 0.85 | 1.77 | 1.18 | 2.45 | 0.03 | 2.77 | 0.88 |
| Arjun | 31 | 5 | 0.87 | 0.23 | 0.19 | 1.90 | 0.06 | 1.00 | 1.48 |
| Elena | 30 | 3 | 0.57 | 0.27 | 0.00 | 2.43 | 0.00 | 2.07 | 2.27 |
| Dee Jay | 28 | 4 | 0.68 | 0.46 | 0.25 | 2.07 | 0.25 | 2.46 | 1.29 |
| Dhalsim | 28 | 4 | 0.93 | 0.71 | 3.96 | 2.18 | 0.25 | 1.79 | 1.79 |
| JP | 27 | 5 | 1.00 | 1.33 | 0.44 | 2.74 | 0.33 | 2.70 | 1.70 |
| Akuma | 25 | 3 | 0.72 | 0.12 | 0.00 | 1.44 | 0.08 | 1.24 | 1.08 |
| Zangief | 25 | 4 | 1.32 | 0.64 | 0.32 | 2.00 | 0.12 | 1.96 | 0.96 |
| M Bison | 22 | 2 | 1.50 | 0.14 | 0.18 | 2.82 | 0.18 | 2.55 | 1.95 |
| Jamie | 21 | 3 | 2.33 | 0.14 | 0.05 | 2.19 | 0.38 | 3.33 | 1.48 |
| Kimberly | 18 | 3 | 1.72 | 0.11 | 0.17 | 1.89 | 0.17 | 1.83 | 1.78 |
| Ingrid | 17 | 4 | 0.71 | 1.24 | 0.06 | 1.53 | 0.06 | 2.18 | 1.71 |
| Manon | 15 | 3 | 0.80 | 0.53 | 0.13 | 2.60 | 0.20 | 2.47 | 0.80 |
| AKI | 12 | 3 | 0.67 | 0.17 | 0.08 | 1.92 | 0.42 | 2.92 | 2.25 |
| Lily | 9 | 2 | 0.78 | 0.78 | 0.56 | 2.11 | 0.11 | 1.56 | 2.67 |

Characters with fewer than 9 rounds (Alex, Chun-Li, E. Honda) aren't listed: too little data.

Across the database (without .shog), players average about 1.25 forward jumps, 2.3 Drive Rushes and 2.1 Drive Parries a round; Cammy players jump almost twice as often as average.

**.shog against other Cammys** (his 342 rounds): about 2.5 forward jumps, 2.5 Drive Rushes and 1.1 Drive Parries a round, against 2.1, 1.9 and 1.5 for the other Cammys. He jumps and rushes more and parries less than the Cammy norm.

## Character notes

### Cammy
- **Strong aerial game:** Cannon Strike (dive kick) from forward jumps makes jumping part of her neutral, not a leak by itself. Baseline is about 2.1 forward jumps a round (other Cammys; .shog about 2.5). Judge her jumps by what they were meant to land on and the dive kick's height and spacing, not by the count.
- (suggested) Her dive kick works as a whiff punish over mid-range buttons (see coach DoctaAfrikan's "scam artist" notes). A defender who keeps pressing 2MK at her jump range is the leak, not her jumping.
- (suggested) Spiral Arrow is very minus on block: on wake-up it's almost always an input error (coach .shog's wake-up rule).
- **Low Drive Parry count:** about 1.5 a round for other Cammys (.shog about 1.1), against about 2.1 across all characters. Cammy's raw Drive Rush is on the weaker side of the cast, so fewer raw Drive Rushes start with a Drive Parry tap; .shog's lower number is partly his own habit.

### Juri
- (suggested) Fuha stocks (Fuhajin) are a resource: judge where and when she stocks (full screen or after a knockdown vs inside the opponent's range), not just how many.
- **Fast Drive Rush:** Juri's Drive Rush is very fast, so raw Drive Rush is an effective tool for her and Juri players use it a lot. Her high Drive Parry count (about 2.7 a round) mostly comes from this: a raw Drive Rush is started with a Drive Parry tap, so many of those "parries" are really Drive Rush starts, not defensive parries.

### Fast Drive Rush characters (Juri, Yasmine, Mai, Dee Jay)
- These characters have very fast Drive Rushes, so raw Drive Rush tends to be effective for them and their players use it often. Expect high raw Drive Rush counts and high Drive Parry counts (each raw Drive Rush starts with a Drive Parry tap). Separate parries that went into a Drive Rush (the parries table's "raw drive rush" outcome, or the raw drive rush events) from defensive parries before judging Drive Parry habits.
- Baselines in the data fit this: Yasmine (about 3.2 Drive Rush and 3.0 Drive Parry a round), Juri (2.7 and 2.7), Mai (2.5 and 2.5), Dee Jay (2.1 and 2.5).

### Aerial / dive kick characters (Cammy, Jamie, C. Viper)
- **Short dive kick bait:** they can deliberately whiff a dive kick (or Viper's Burn Kick) short, landing in front of the opponent to bait an anti-air attempt (DP, anti-air normal), then punish the whiffed anti-air. A dive kick that lands short and doesn't hit is not automatically a mistake: check what the opponent did next. If they whiffed an anti-air and got punished, it was a bait; if they just walked up and pressed, it was a miss.
- For the defender, the answer to the bait is to block or step back instead of throwing the anti-air early, and to anti-air only dive kicks that will actually reach (see `sf6-dps-and-divekicks-exdojo`).

### Fireball Drive Rush characters (Ken, AKI, Mai, Guile, Ingrid, Chun-Li)
- These characters can throw a fireball (often OD) and Drive Rush behind it to start offense safely. Expect fireball > Drive Rush sequences as a normal way in, not a reckless one; judge whether the opponent had an answer (parry the fireball, Drive Impact, jump) and whether the follow-up was gapped.
- **Juri, to a lesser degree:** with a stocked Fuhajin she can start offense behind the fireball, but she usually walks behind it rather than Drive Rushing.

### C. Viper
- **Aerial character, like Cammy:** her Burn Kick gives her a strong air game, so frequent jumps are part of her game plan rather than a leak by themselves. Judge the jumps by what they were meant to land on and how the Burn Kicks were spaced. (Baseline: too few rounds in the database so far.)

### Terry
- (suggested) Few jumps (about 0.6 forward a round): Terry players stay grounded.
- (suggested) Burning Knuckle, Power Charge, Crack Shoot and Quick Burn are committal; many are punishable on block. Count blocked specials as a separate leak from neutral pressing.
- (suggested) Rising Tackle (charge) is his invincible reversal; Buster Wolf is a super reversal option.

### Guile
- (suggested) Neutral and back jumps are high (about 1.8 and 1.2 a round) because they keep charge; they are not a leak by themselves. Forward jumps are low.
- (suggested) Special counts are naturally high (Sonic Booms). Judge boom spacing and recovery, not count.

### Dhalsim
- (suggested) Back jumps and floating are part of his zoning (about 4 back jumps a round). High special counts are normal.

### Blanka
- (suggested) Blanka Balls are unsafe at many spacings; the analyzer labels the bounce "Backstep Rolling". Back jumps are higher than most.

### Ken
- **Aggressive by design:** Ken has a strong fireball Drive Rush (an OD fireball with a Drive Rush behind it starts offense safely) and a good raw Drive Rush (Drive Rush jab is a frequent tool). A high Drive Rush rate (about 2.8 a round) is normal for him; judge whether the rushes are checked.
- His Drive Impact rate in the data (about 0.4 a round, among the highest) is more likely the habits of the few Ken players reviewed than something about the character. Don't treat it as a Ken norm.

### JP
- (suggested) Zoner: high neutral jumps, Drive Impact use above average, high special counts.

### Marisa
- (suggested) High Drive Parry rate (about 2.9 a round across 6 players). BadTango (2026-11-24) parried far less (about 1.6 a round), so it varies by player.
- **Gladius (236P) armor loses to lows**, in every version: L/M/H, OD (236PP) and charged (SuperCombo notes, checked 2026-11-24). Answer it with a low (Cammy's 2MK or 2LK), not a mid button or a dive kick, which the armor absorbs. Uncharged Gladius is -5 on block (punishable); charged is +4. In the BadTango set Gladius started 12 hits for 23,480 and its armor absorbed 11 of .shog's hits (4 dive kicks, a j.HP, 6 mids). The replay had no low into an OD Gladius, so the OD case rests on the wiki.
- **Scutum (214K) counter-throw** (214K~LPLK: 8+5f, 2,500, 2,875 on Punish Counter) catches anything that lands in front of her without attacking. Cammy's Hooligan > Silent Step was grabbed 4 times out of 4 (video-checked). Scutum's armor doesn't cover the lower body, so against it end Hooligan with Razor's Edge Slicer (a low, +2 on block) or don't follow up.
- Charged normals are plus on block (5[HP] +5, 4[HP] +4, 6[HK] +3): block after the long glow instead of pressing.

### Jamie
- (suggested) Jumps a lot (about 2.3 forward a round) and has a dive kick; treat jumps like Cammy's.

### Ryu
- (suggested) A grounded fireball and Shoryuken character: around 1.0 forward jumps a round in limited data. A Ryu jumping far more than that is probably a weakness.

### M. Bison
- Scissor Kicks are about -3 to -5 on block depending on spacing, but the Bison player usually knows the spacing better than the defender (coach .shog Theory #3).

### Grapplers (Zangief, Manon, Lily)
- (suggested) Their threat is the command grab; count command grabs separately from normal throws when judging throw habits.