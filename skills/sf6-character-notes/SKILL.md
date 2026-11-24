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

## Baselines from sf6.db (2026-11-21)
Per round, all players of that character in the database. **Caveats:** most characters have few rounds and players; Cammy is mostly .shog. Special counts depend on the analyzer's move-name tables and are unreliable for characters whose specials aren't named yet (e.g. Yasmine, Jamie, Zangief, Arjun, Elena show very low counts). Throw presses include throw techs and whiffed throws. Recompute these as the database grows.

| Character | Rounds | Players | Forward jumps | Neutral jumps | Back jumps | Drive Rush | Drive Impact | Drive Parry | Throw presses |
|---|---|---|---|---|---|---|---|---|---|
| Cammy | 198 | 6 | 2.74 | 0.16 | 0.27 | 2.23 | 0.16 | 0.99 | 1.46 |
| Juri | 67 | 4 | 1.49 | 0.42 | 0.13 | 2.39 | 0.07 | 2.42 | 1.73 |
| Mai | 64 | 3 | 1.53 | 0.75 | 0.25 | 2.59 | 0.06 | 2.59 | 1.20 |
| Sagat | 48 | 1 | 0.48 | 0.90 | 0.12 | 2.50 | 0.19 | 2.04 | 0.92 |
| Yasmine | 44 | 3 | 0.64 | 0.16 | 0.25 | 3.05 | 0.11 | 2.93 | 1.36 |
| Ken | 39 | 4 | 1.13 | 0.54 | 0.08 | 3.26 | 0.49 | 3.08 | 1.33 |
| Blanka | 37 | 2 | 1.46 | 0.11 | 0.95 | 1.95 | 0.43 | 1.22 | 1.35 |
| Marisa | 36 | 2 | 1.08 | 0.36 | 0.14 | 2.67 | 0.06 | 3.58 | 1.31 |
| Dee Jay | 28 | 4 | 0.68 | 0.46 | 0.25 | 2.07 | 0.25 | 2.46 | 1.29 |
| Guile | 25 | 4 | 0.76 | 2.12 | 1.28 | 2.52 | 0.04 | 2.84 | 0.92 |
| Terry | 25 | 2 | 0.52 | 0.08 | 0.20 | 2.60 | 0.20 | 2.00 | 1.56 |
| Akuma | 25 | 3 | 0.72 | 0.12 | 0.00 | 1.44 | 0.08 | 1.24 | 1.08 |
| Luke | 17 | 3 | 0.76 | 0.29 | 0.18 | 2.76 | 0.06 | 2.76 | 2.18 |
| JP | 16 | 2 | 1.38 | 1.88 | 0.62 | 3.06 | 0.50 | 3.00 | 1.94 |
| Manon | 15 | 3 | 0.80 | 0.53 | 0.13 | 2.60 | 0.20 | 2.47 | 0.80 |
| Jamie | 14 | 2 | 2.36 | 0.14 | 0.07 | 2.21 | 0.57 | 3.43 | 0.86 |
| Ryu | 14 | 3 | 1.43 | 0.71 | 0.50 | 2.36 | 0.14 | 1.43 | 1.36 |
| Zangief | 12 | 2 | 0.83 | 0.42 | 0.17 | 1.75 | 0.08 | 1.58 | 0.83 |
| AKI | 10 | 2 | 0.80 | 0.10 | 0.10 | 2.20 | 0.30 | 3.30 | 1.90 |
| Dhalsim | 9 | 2 | 1.44 | 1.11 | 2.78 | 1.44 | 0.56 | 2.44 | 0.67 |

Characters with fewer than 9 rounds (Arjun, C. Viper, E. Honda, Elena, Lily, Kimberly, Alex, Ingrid) aren't listed: too little data.

Across the database, forward jumps average roughly 1.2 per round; Cammy jumps more than twice that.

## Character notes

### Cammy
- **Strong aerial game:** Cannon Strike (dive kick) from forward jumps makes jumping part of her neutral, not a leak by itself. Baseline is about 2.7 forward jumps a round. Judge her jumps by what they were meant to land on and the dive kick's height and spacing, not by the count.
- (suggested) Her dive kick works as a whiff punish over mid-range buttons (see coach DoctaAfrikan's "scam artist" notes). A defender who keeps pressing 2MK at her jump range is the leak, not her jumping.
- (suggested) Spiral Arrow is very minus on block: on wake-up it's almost always an input error (coach .shog's wake-up rule).
- **Low Drive Parry count** (about 1 a round in the data), likely for two reasons: the data is mostly .shog, whose own tendency is to parry less, and Cammy's raw Drive Rush is on the weaker side of the cast, so fewer raw Drive Rushes start with a Drive Parry tap. Treat the number as partly a player habit, not purely a Cammy norm.

### Juri
- (suggested) Fuha stocks (Fuhajin) are a resource: judge where and when she stocks (full screen or after a knockdown vs inside the opponent's range), not just how many.
- **Fast Drive Rush:** Juri's Drive Rush is very fast, so raw Drive Rush is an effective tool for her and Juri players use it a lot. Her high Drive Parry count (about 2.4 a round) mostly comes from this: a raw Drive Rush is started with a Drive Parry tap, so many of those "parries" are really Drive Rush starts, not defensive parries.

### Fast Drive Rush characters (Juri, Yasmine, Mai, Dee Jay)
- These characters have very fast Drive Rushes, so raw Drive Rush tends to be effective for them and their players use it often. Expect high raw Drive Rush counts and high Drive Parry counts (each raw Drive Rush starts with a Drive Parry tap). Separate parries that went into a Drive Rush (the parries table's "raw drive rush" outcome, or the raw drive rush events) from defensive parries before judging Drive Parry habits.
- Baselines in the data fit this: Yasmine (about 3.1 Drive Rush and 2.9 Drive Parry a round), Mai (2.6 and 2.6), Juri (2.4 and 2.4), Dee Jay (2.1 and 2.5).

### Aerial / dive kick characters (Cammy, Jamie, C. Viper)
- **Short dive kick bait:** they can deliberately whiff a dive kick (or Viper's Burn Kick) short, landing in front of the opponent to bait an anti-air attempt (DP, anti-air normal), then punish the whiffed anti-air. A dive kick that lands short and doesn't hit is not automatically a mistake: check what the opponent did next. If they whiffed an anti-air and got punished, it was a bait; if they just walked up and pressed, it was a miss.
- For the defender, the answer to the bait is to block or step back instead of throwing the anti-air early, and to anti-air only dive kicks that will actually reach (see `sf6-dps-and-divekicks-exdojo`).

### Fireball Drive Rush characters (Ken, AKI, Mai, Guile, Ingrid, Chun-Li)
- These characters can throw a fireball (often OD) and Drive Rush behind it to start offense safely. Expect fireball > Drive Rush sequences as a normal way in, not a reckless one; judge whether the opponent had an answer (parry the fireball, Drive Impact, jump) and whether the follow-up was gapped.
- **Juri, to a lesser degree:** with a stocked Fuhajin she can start offense behind the fireball, but she usually walks behind it rather than Drive Rushing.

### C. Viper
- **Aerial character, like Cammy:** her Burn Kick gives her a strong air game, so frequent jumps are part of her game plan rather than a leak by themselves. Judge the jumps by what they were meant to land on and how the Burn Kicks were spaced. (Baseline: too few rounds in the database so far.)

### Terry
- (suggested) Few jumps (about 0.5 forward a round): Terry players stay grounded.
- (suggested) Burning Knuckle, Power Charge, Crack Shoot and Quick Burn are committal; many are punishable on block. Count blocked specials as a separate leak from neutral pressing.
- (suggested) Rising Tackle (charge) is his invincible reversal; Buster Wolf is a super reversal option.

### Guile
- (suggested) Neutral and back jumps are high (about 2.1 and 1.3 a round) because they keep charge; they are not a leak by themselves. Forward jumps are low.
- (suggested) Special counts are naturally high (Sonic Booms). Judge boom spacing and recovery, not count.

### Dhalsim
- (suggested) Back jumps and floating are part of his zoning (about 2.8 back jumps a round). High special counts are normal.

### Blanka
- (suggested) Blanka Balls are unsafe at many spacings; the analyzer labels the bounce "Backstep Rolling". Back jumps are higher than most.

### Ken
- **Aggressive by design:** Ken has a strong fireball Drive Rush (an OD fireball with a Drive Rush behind it starts offense safely) and a good raw Drive Rush (Drive Rush jab is a frequent tool). The most Drive Rush in the data (about 3.3 a round) is normal for him; judge whether the rushes are checked.
- His Drive Impact rate in the data (about 0.5 a round) is more likely the habits of the few Ken players reviewed than something about the character. Don't treat it as a Ken norm.

### JP
- (suggested) Zoner: high neutral jumps, Drive Impact use above average, high special counts.

### Marisa
- (suggested) Highest Drive Parry rate in the data (about 3.6 a round).

### Jamie
- (suggested) Jumps a lot (about 2.4 forward a round) and has a dive kick; treat jumps like Cammy's.

### Ryu
- (suggested) A grounded fireball and Shoryuken character: around 1.4 forward jumps a round in limited data. A Ryu jumping far more than that is probably a weakness.

### M. Bison
- Scissor Kicks are about -3 to -5 on block depending on spacing, but the Bison player usually knows the spacing better than the defender (coach .shog Theory #3).

### Grapplers (Zangief, Manon, Lily)
- (suggested) Their threat is the command grab; count command grabs separately from normal throws when judging throw habits.