---
name: "quick-review-report"
description: "Second tier of every SF6 replay review: the stats-based Quick review built from the capture data after shared-core-review: generated player reads and habits in sf6.db, and the Quick reply (what cost, what worked, lessons held). A Full review runs it too, as its starting draft. Loaded by sf6-replay-analysis."
---

# Quick review: the stats layer

Runs after `shared-core-review` (prediction stored, analyzer run, set ingested). For a **Quick** review it is the whole review. For a **Full** or **Tournament** review it runs first and its output is the draft that `full-review-report` builds on.

Everything here comes from the capture data in sf6.db and the analyzer output. Nothing is hand-written, and no video is needed unless a row looks wrong.

## 1. Generated reads and habits
`python tools\quick_review_reads.py DB OUTDIR --write-reads --set SET_KEY` (on the `$HOME` copy of sf6.db, then copy it back; no `-journal` left).
- **Quick set:** writes one read per player (archetype from pool-calibrated cut points, `toolsrchetype_calibrate.py`, see `shared-core-player-spectra.md`; lean, confidence, evidence, counter note, risk tolerance, temperament) and the habits (kind Strength / Leak / Pattern, area, seen, times, fix), with source "generated from capture stats". It also refreshes the set's spectra.
- **Full or Tournament set:** the script leaves a set with review docs alone (hand-written reads and habits win). Run it without `--write-reads` and use its `archetypes.json` and `habits.json` in OUTDIR as the draft for `full-review-report`.
- Ignore its other output files (the retired quick-dashboard datasets).
- These reads and habits are what the site shows for a Quick set (set page, player profile habit counts, archetype stats), so the thresholds in `quick_review_reads.py` are where Quick reviews are tuned.

## 2. Character baselines
Load `sf6-character-notes` with the Skill tool. Before calling a rate a habit or a leak (jumps, Drive Rushes, Drive Parries, Drive Impacts, throws, specials), compare it with that character's baseline as well as the all-character average: a rate that is normal for the character is only a leak if it got punished in this set. Say which baseline was used and how big its sample is (under about 20 rounds is a hint, not a norm). When the set shows a new character-specific pattern, suggest a note for that skill.

## 3. Numbers to pull
From the ingested set (sf6.db) and report.md, for the player in focus and the opponent:
- **Result:** games and rounds, the set's progression, and each game's damage either way.
- **Where they got hit:** damage taken by lens (counter-hit at mid range, walked in, jumped, blocking opened up, challenging pressure, Drive Rush checked, unsafe move punished...), with each lens's share of the total and the opponent's top starters.
- **Where they dealt damage:** top starters (damage and count), frame-trap counter hits in pressure, throws and shimmies (throws landed, techs caught), punish counters, combo drive rush cancels.
- **Button economy:** decision presses per round and damage per decision press, against the opponent's (`set_stats`).
- **Defense:** after-block and wake-up choices (held block, pressed on the first free frame, jumped, parried), and damage taken in oki.
- **Block punishes:** report.md's "Block punish windows" section (sf6.db `punish_windows`): windows of -5 or worse by range (close / mid; far isn't a block punish), how many were punished, and what was done instead (Drive Parry, pressed but didn't connect, jumped, held). Name each close miss with its round @ timer. Trust rows marked `ok` or `later hit blocked`; check `unverified` ones on video before calling them misses, and ignore `wiki disagrees`.
- **Whiff punishes:** report.md's "Whiff punishes" section (sf6.db `whiff_windows`, set_stats `whiff_chances` / `whiff_punishes`): whiffed ground normals and throws whose recovery window was at least 15 frames while the punisher was free and in reach (`tools\shared_core_whiffs.py`). Give chances, punished and missed, and name each miss with its round @ timer, the whiffed move and the fastest button in reach. Shorter windows aren't counted as missed: lights can't be whiff punished on reaction (a punish there comes from a spacing trap). Reach is approximate, so call misses "likely".
- **Jump-ins and anti-airs:** report.md's "Jump-ins" section (sf6.db `jump_ins`, set_stats `jump_ins_*`, `tools\shared_core_antiair.py`): every forward or neutral jump at the player, ended as anti-air, air-to-air, trade, parried, landing punished, hit, blocked (and whether the defender was opened up within 2 s after) or empty. Give the **anti-air rate** (anti-aired / jump-ins they were free for) and the stopped rate (adds parries and landing punishes). Jump-ins taken while busy (in their own move or its recovery, blockstun, hitstun, a knockdown) are listed apart and aren't failures to anti-air. Name each free jump-in that hit or was blocked with its round @ timer and the jump attack.
- **Resources:** burnouts (lethal ones not counted), the three Drive Rush classes, Drive Reversals, super spent and left at round ends.
- **Corner time:** seconds each player spent cornered per round (report.md `corner R…` lines; sf6.db `corner_time`, and `cornered_frames` / `cornering_frames` / `active_frames` / `cornered_entries` in `set_stats` and `game_stats`; frames / 60 = seconds). Cornered = within 1.5 of the wall with the opponent on the inner side, live play only (`tools\corner_time.py`). Say who held the corner in each lost round, and for how long.

## 4. Lessons held
Query sf6.db for the player's leaks and habits from their recent sets (and earlier sets against this opponent or matchup). For each lesson in play, say whether it held in this set, with the number (e.g. "attacked on 14 of 53 wake-ups, against 44% in an earlier set"). A habit that wasn't punished this time still counts as not fixed.

## 5. The Quick reply
In this order, short:
1. **Result**, with played order and the prediction grade (and any pattern in the grades).
2. **What cost them:** the top two or three lenses or habits by damage, with the opponent's starter that did it.
3. **What worked:** the top two or three, with numbers.
4. **Lessons held:** from step 4.
5. **Open items:** unnamed moves, analyzer oddities, anything not stored.

Say it's a Quick review (generated from the capture, no hand-written reads). Then, for a Full or Tournament review, continue with `full-review-report`.
